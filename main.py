import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from io import BytesIO

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from google import genai
from google.genai import types as genai_types

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DB_PATH = "taom_ai.db"
TRIAL_DAYS = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode="Markdown")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            target TEXT,
            registered_at TEXT DEFAULT (datetime('now')),
            trial_start TEXT DEFAULT (datetime('now')),
            is_premium INTEGER DEFAULT 0,
            scan_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            food_name TEXT,
            portion TEXT,
            calories REAL,
            protein REAL,
            fat REAL,
            carbs REAL,
            logged_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS payment_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            photo_file_id TEXT NOT NULL,
            requested_at TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'pending'
        );
    """)
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# FSM STATES
# ─────────────────────────────────────────────

class Registration(StatesGroup):
    age = State()
    gender = State()
    height = State()
    weight = State()
    target = State()


class PaymentState(StatesGroup):
    waiting_receipt = State()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

PREMIUM_MSG = (
    "🚀 **Taom AI Premium Versiya**\n\n"
    "✨ Barcha VIP funksiyalar to'liq ochiladi:\n"
    "• Cheksiz taom va shirinliklarni foto-skaner qilish\n"
    "• Taomlar donasi va porsiyasini aqlli tizim orqali aniq hisoblash\n"
    "• 7 kunlik haftalik hisobotlarni cheklovsiz ko'rish\n\n"
    "Obuna narxi: 20 000 so'm\n"
    "Karta (Uzcard/Humo): 9860040114589092\n\n"
    "To'lovni amalga oshirib, chek rasmini (skrinshot) shu yerga yuboring. "
    "Admin tezda tasdiqlaydi!"
)


def get_user(telegram_id: int):
    conn = get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()
    return user


def is_trial_active(user) -> bool:
    trial_start = datetime.fromisoformat(user["trial_start"])
    return datetime.utcnow() < trial_start + timedelta(days=TRIAL_DAYS)


def can_use_analysis(user) -> bool:
    return bool(user["is_premium"]) or is_trial_active(user)


def calculate_daily_norm(user) -> int:
    """Mifflin-St Jeor BMR × activity factor, adjusted for target."""
    w = user["weight"] or 70
    h = user["height"] or 170
    a = user["age"] or 25
    gender = user["gender"] or "erkak"
    target = user["target"] or "saqlash"

    if "ayol" in gender.lower() or "female" in gender.lower():
        bmr = 10 * w + 6.25 * h - 5 * a - 161
    else:
        bmr = 10 * w + 6.25 * h - 5 * a + 5

    tdee = bmr * 1.375  # lightly active

    if "yo'qotish" in target.lower() or "ozish" in target.lower() or "lose" in target.lower():
        return int(tdee - 500)
    elif "olish" in target.lower() or "gain" in target.lower() or "semirish" in target.lower():
        return int(tdee + 500)
    else:
        return int(tdee)


def main_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📊 Statistika"),
        KeyboardButton("📅 Haftalik hisobot"),
    )
    kb.add(
        KeyboardButton("📋 Bugungi tarix"),
        KeyboardButton("👤 Profilim"),
    )
    kb.add(KeyboardButton("💎 Premium"))
    return kb


def admin_check(func):
    """Decorator to restrict handler to admin only."""
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id != ADMIN_ID:
            await message.reply("❌ Sizda bu buyruqni ishlatish huquqi yo'q.")
            return
        return await func(message, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# ─────────────────────────────────────────────
# /START — REGISTRATION
# ─────────────────────────────────────────────

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user = get_user(message.from_user.id)

    if user:
        await message.answer(
            f"👋 Xush kelibsiz, *{message.from_user.first_name}*!\n\n"
            "Taom rasmini yuboring yoki quyidagi menyudan tanlang:",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        f"🌟 Assalomu alaykum, *{message.from_user.first_name}*!\n\n"
        "Men *Taom AI* — ovqatlanishingizni tahlil qiluvchi aqlli yordamchiman.\n\n"
        "Boshlash uchun bir necha savol beraman. Yoshingizni kiriting (masalan: *25*):"
    )
    await Registration.age.set()


@dp.message_handler(state=Registration.age)
async def reg_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text.strip())
        if not (5 <= age <= 120):
            raise ValueError
    except ValueError:
        await message.reply("❌ Iltimos, to'g'ri yosh kiriting (masalan: *25*):")
        return

    await state.update_data(age=age)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("👨 Erkak"), KeyboardButton("👩 Ayol"))
    await message.answer("Jinsingizni tanlang:", reply_markup=kb)
    await Registration.gender.set()


@dp.message_handler(state=Registration.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    text = message.text.strip().lower()
    if "erkak" in text:
        gender = "Erkak"
    elif "ayol" in text:
        gender = "Ayol"
    else:
        await message.reply("❌ Iltimos, tugmadan tanlang:")
        return

    await state.update_data(gender=gender)
    await message.answer(
        "Bo'yingizni kiriting (sm da, masalan: *175*):",
        reply_markup=ReplyKeyboardRemove(),
    )
    await Registration.height.set()


@dp.message_handler(state=Registration.height)
async def reg_height(message: types.Message, state: FSMContext):
    try:
        height = float(message.text.strip())
        if not (100 <= height <= 250):
            raise ValueError
    except ValueError:
        await message.reply("❌ Iltimos, to'g'ri bo'y kiriting (masalan: *175*):")
        return

    await state.update_data(height=height)
    await message.answer("Vazningizni kiriting (kg da, masalan: *70*):")
    await Registration.weight.set()


@dp.message_handler(state=Registration.weight)
async def reg_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text.strip())
        if not (20 <= weight <= 400):
            raise ValueError
    except ValueError:
        await message.reply("❌ Iltimos, to'g'ri vazn kiriting (masalan: *70*):")
        return

    await state.update_data(weight=weight)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton("⬇️ Vazn yo'qotish"),
        KeyboardButton("⬆️ Vazn olish"),
        KeyboardButton("⚖️ Vazn saqlash"),
    )
    await message.answer("Maqsadingizni tanlang:", reply_markup=kb)
    await Registration.target.set()


@dp.message_handler(state=Registration.target)
async def reg_target(message: types.Message, state: FSMContext):
    text = message.text.strip()
    valid = ["Vazn yo'qotish", "Vazn olish", "Vazn saqlash"]
    target = None
    for v in valid:
        if v.lower() in text.lower():
            target = v
            break

    if not target:
        await message.reply("❌ Iltimos, tugmadan tanlang:")
        return

    data = await state.get_data()
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO users
           (telegram_id, username, first_name, age, gender, height, weight, target,
            registered_at, trial_start, is_premium, scan_count)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 0, 0)""",
        (
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            data["age"],
            data["gender"],
            data["height"],
            data["weight"],
            target,
        ),
    )
    conn.commit()
    conn.close()
    await state.finish()

    daily_norm = calculate_daily_norm({
        "age": data["age"], "gender": data["gender"],
        "height": data["height"], "weight": data["weight"], "target": target,
    })

    await message.answer(
        f"✅ *Profil muvaffaqiyatli saqlandi!*\n\n"
        f"👤 Ism: {message.from_user.first_name}\n"
        f"🎂 Yosh: {data['age']}\n"
        f"⚧ Jins: {data['gender']}\n"
        f"📏 Bo'y: {data['height']} sm\n"
        f"⚖️ Vazn: {data['weight']} kg\n"
        f"🎯 Maqsad: {target}\n"
        f"🔥 Kunlik norma: *{daily_norm} kkal*\n\n"
        f"🆓 Sizda *{TRIAL_DAYS} kunlik bepul sinov* davri boshlandi!\n"
        f"Taom rasmini yuboring — tahlil qilib beraman 🍽",
        reply_markup=main_menu_keyboard(),
    )


# ─────────────────────────────────────────────
# /RESET
# ─────────────────────────────────────────────

@dp.message_handler(commands=["reset"])
async def cmd_reset(message: types.Message, state: FSMContext):
    await state.finish()
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE telegram_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer(
        "🔄 Profilingiz o'chirildi. Qayta ro'yxatdan o'tish uchun /start bosing.",
        reply_markup=ReplyKeyboardRemove(),
    )


# ─────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────

@dp.message_handler(lambda m: m.text == "👤 Profilim")
async def show_profile(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.reply("Siz hali ro'yxatdan o'tmagansiz. /start bosing.")
        return

    daily_norm = calculate_daily_norm(user)
    trial_end = datetime.fromisoformat(user["trial_start"]) + timedelta(days=TRIAL_DAYS)
    if user["is_premium"]:
        status = "💎 Premium"
    elif datetime.utcnow() < trial_end:
        remaining = (trial_end - datetime.utcnow()).days + 1
        status = f"🆓 Sinov ({remaining} kun qoldi)"
    else:
        status = "🔒 Muddat tugagan"

    await message.answer(
        f"👤 *Sizning profilingiz*\n\n"
        f"🏷 Ism: {user['first_name']}\n"
        f"🎂 Yosh: {user['age']}\n"
        f"⚧ Jins: {user['gender']}\n"
        f"📏 Bo'y: {user['height']} sm\n"
        f"⚖️ Vazn: {user['weight']} kg\n"
        f"🎯 Maqsad: {user['target']}\n"
        f"🔥 Kunlik norma: *{daily_norm} kkal*\n"
        f"📸 Jami skanlar: {user['scan_count']}\n"
        f"📋 Holat: {status}\n\n"
        f"Profilni yangilash uchun /reset bosing."
    )


# ─────────────────────────────────────────────
# PREMIUM BUTTON
# ─────────────────────────────────────────────

@dp.message_handler(lambda m: m.text == "💎 Premium")
async def show_premium(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if user and user["is_premium"]:
        await message.reply("✅ Siz allaqachon *Premium* foydalanuvchisiz! Barcha imkoniyatlar ochiq.")
        return

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 To'lovni tasdiqlash", callback_data="send_receipt"))
    await message.answer(PREMIUM_MSG, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "send_receipt")
async def prompt_receipt(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.reply("Avval /start orqali ro'yxatdan o'ting.")
        return

    await callback.message.answer(
        "📸 Iltimos, to'lov cheki rasmini (skrinshot) yuboring.\n"
        "Admin ko'rib chiqadi va tezda tasdiqlaydi!"
    )
    await PaymentState.waiting_receipt.set()


@dp.message_handler(content_types=types.ContentType.PHOTO, state=PaymentState.waiting_receipt)
async def receive_receipt(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_id = photo.file_id
    user_id = message.from_user.id

    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_requests (telegram_id, photo_file_id) VALUES (?, ?)",
        (user_id, file_id),
    )
    req_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    await state.finish()

    # Forward to admin
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"deny_{user_id}"),
    )
    user = get_user(user_id)
    caption = (
        f"💳 *Yangi to'lov so'rovi*\n\n"
        f"👤 Foydalanuvchi: {message.from_user.first_name}\n"
        f"🆔 ID: `{user_id}`\n"
        f"📛 Username: @{message.from_user.username or 'yoq'}\n"
        f"📸 Jami skanlar: {user['scan_count'] if user else 0}\n"
        f"🔢 So'rov ID: {req_id}"
    )
    try:
        await bot.send_photo(ADMIN_ID, photo=file_id, caption=caption, reply_markup=kb)
    except Exception as e:
        logger.error(f"Admin ga chek yuborishda xato: {e}")

    await message.answer(
        "✅ Chekingiz adminga yuborildi!\n"
        "Tez orada hisobingiz Premium ga o'tkaziladi. Kuting..."
    )


@dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("deny_"))
async def handle_payment_decision(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    action, uid = callback.data.split("_", 1)
    uid = int(uid)

    if action == "approve":
        conn = get_conn()
        conn.execute(
            "UPDATE users SET is_premium = 1 WHERE telegram_id = ?", (uid,)
        )
        conn.execute(
            "UPDATE payment_requests SET status = 'approved' WHERE telegram_id = ? AND status = 'pending'",
            (uid,)
        )
        conn.commit()
        conn.close()

        try:
            await bot.send_message(
                uid,
                "🎉 *Tabriklaymiz! Siz Premium foydalanuvchi bo'ldingiz!*\n\n"
                "💎 Barcha VIP funksiyalar to'liq ochildi:\n"
                "• Cheksiz taom skanerlash\n"
                "• Haftalik hisobotlar\n"
                "• Aqlli porsiya hisoblash\n\n"
                "Taom rasmini yuboring — boshlaylik! 🍽",
            )
        except Exception as e:
            logger.error(f"Foydalanuvchiga xabar yuborishda xato: {e}")

        await callback.answer("✅ Premium berildi!", show_alert=True)
        await callback.message.edit_caption(
            callback.message.caption + "\n\n✅ *TASDIQLANDI*",
            reply_markup=None,
        )
    else:
        conn = get_conn()
        conn.execute(
            "UPDATE payment_requests SET status = 'denied' WHERE telegram_id = ? AND status = 'pending'",
            (uid,)
        )
        conn.commit()
        conn.close()

        try:
            await bot.send_message(
                uid,
                "❌ Afsuski, to'lovingiz tasdiqlanmadi.\n"
                "Iltimos, to'g'ri karta raqamiga to'lov qiling va qayta chek yuboring:\n"
                "Karta: *9860040114589092*",
            )
        except Exception as e:
            logger.error(f"Rad etish xabarini yuborishda xato: {e}")

        await callback.answer("❌ Rad etildi!", show_alert=True)
        await callback.message.edit_caption(
            callback.message.caption + "\n\n❌ *RAD ETILDI*",
            reply_markup=None,
        )


# ─────────────────────────────────────────────
# IMAGE ANALYSIS (FOOD PHOTO)
# ─────────────────────────────────────────────

ANALYSIS_PROMPT = """
Sen professional dietolog va ovqatlanish mutaxassisisan.
Ushbu rasm tahlilini O'zbek tilida bering.

Quyidagi formatda javob bering:

🍽 *Taom nomi:* [taom nomi]
🔢 *Porsiya / miqdor:* [gramm yoki dona]
🔥 *Kaloriya:* [son] kkal
💪 *Oqsil:* [son] g
🧈 *Yog':* [son] g
🍞 *Uglevodlar:* [son] g

📝 *Qisqacha tavsif:* [ushbu taomning sog'liq uchun foydasi va zarari haqida 1-2 gap]

Agar rasm taom emas bo'lsa, faqat shunday deng: "❌ Rasm taom emas. Iltimos, taom rasmini yuboring."
"""


async def analyze_food_image(image_bytes: bytes) -> dict | None:
    """Send image to Gemini and parse the result."""
    try:
        image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[image_part, ANALYSIS_PROMPT],
        )
        text = response.text.strip()
        return {"raw": text}
    except Exception as e:
        logger.error(f"Gemini tahlilida xato: {e}")
        return None


def parse_nutrient(text: str, keyword: str) -> float:
    """Extract numeric value from Gemini response."""
    import re
    for line in text.splitlines():
        if keyword.lower() in line.lower():
            match = re.search(r"[\d]+(?:[.,]\d+)?", line)
            if match:
                return float(match.group().replace(",", "."))
    return 0.0


@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_food_photo(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        await message.reply("Avval /start orqali ro'yxatdan o'ting.")
        return

    current_state = await state.get_state()
    if current_state == PaymentState.waiting_receipt.state:
        return

    if not can_use_analysis(user):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("💳 Premium sotib olish", callback_data="send_receipt"))
        await message.answer(PREMIUM_MSG, reply_markup=kb)
        return

    processing_msg = await message.reply("🔍 *Tahlil qilinmoqda... Iltimos, kuting...*")

    photo = message.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        downloaded = await bot.download_file(file.file_path)
        image_bytes = downloaded.read()
    except Exception as e:
        logger.error(f"Rasm yuklashda xato: {e}")
        await processing_msg.edit_text("❌ Rasmni yuklashda xato yuz berdi. Qayta urinib ko'ring.")
        return

    result = await analyze_food_image(image_bytes)

    if not result:
        await processing_msg.edit_text("❌ Tahlil qilishda xato yuz berdi. Qayta urinib ko'ring.")
        return

    raw_text = result["raw"]

    if "rasm taom emas" in raw_text.lower() or "taom emas" in raw_text.lower():
        await processing_msg.edit_text(raw_text)
        return

    calories = parse_nutrient(raw_text, "kaloriya")
    protein = parse_nutrient(raw_text, "oqsil")
    fat = parse_nutrient(raw_text, "yog")
    carbs = parse_nutrient(raw_text, "uglevodlar")

    food_name_line = ""
    for line in raw_text.splitlines():
        if "taom nomi" in line.lower():
            food_name_line = line.split(":")[-1].strip()
            break

    conn = get_conn()
    conn.execute(
        """INSERT INTO food_logs (telegram_id, food_name, calories, protein, fat, carbs, logged_at)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
        (message.from_user.id, food_name_line, calories, protein, fat, carbs),
    )
    conn.execute(
        "UPDATE users SET scan_count = scan_count + 1 WHERE telegram_id = ?",
        (message.from_user.id,),
    )
    conn.commit()

    today_calories = conn.execute(
        """SELECT COALESCE(SUM(calories), 0) FROM food_logs
           WHERE telegram_id = ? AND date(logged_at) = date('now')""",
        (message.from_user.id,),
    ).fetchone()[0]
    conn.close()

    daily_norm = calculate_daily_norm(user)
    remaining = daily_norm - today_calories
    progress_pct = min(int(today_calories / daily_norm * 100), 100) if daily_norm else 0

    bar_filled = int(progress_pct / 10)
    bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)

    status_line = ""
    if today_calories >= daily_norm:
        status_line = "⚠️ *Kunlik norma oshib ketdi!* Bugun ko'proq yemang."
    elif remaining <= 200:
        status_line = "🟡 Kunlik normaga yaqinlashyapsiz!"
    else:
        status_line = f"✅ Yana *{int(remaining)} kkal* iste'mol qilishingiz mumkin."

    await processing_msg.edit_text(
        f"{raw_text}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 *Bugungi statistika:*\n"
        f"🔥 Jami: *{int(today_calories)} / {daily_norm} kkal*\n"
        f"{bar} {progress_pct}%\n"
        f"{status_line}"
    )


# ─────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────

@dp.message_handler(commands=["history"])
@dp.message_handler(lambda m: m.text == "📋 Bugungi tarix")
async def cmd_history(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.reply("Avval /start orqali ro'yxatdan o'ting.")
        return

    conn = get_conn()
    logs = conn.execute(
        """SELECT food_name, calories, protein, fat, carbs, logged_at FROM food_logs
           WHERE telegram_id = ? AND date(logged_at) = date('now')
           ORDER BY logged_at""",
        (message.from_user.id,),
    ).fetchall()
    conn.close()

    if not logs:
        await message.reply("📋 Bugun hech qanday taom qayd etilmagan.\n\nTaom rasmini yuboring!")
        return

    total_cal = sum(r["calories"] for r in logs)
    total_pro = sum(r["protein"] for r in logs)
    total_fat = sum(r["fat"] for r in logs)
    total_carb = sum(r["carbs"] for r in logs)
    daily_norm = calculate_daily_norm(user)

    lines = [f"📋 *Bugungi tarix ({datetime.utcnow().strftime('%d.%m.%Y')})*\n"]
    for i, log in enumerate(logs, 1):
        t = datetime.fromisoformat(log["logged_at"]).strftime("%H:%M")
        lines.append(
            f"{i}. 🕐 {t} — *{log['food_name'] or 'Nomaʼlum taom'}*\n"
            f"   🔥 {int(log['calories'])} kkal | 💪 {int(log['protein'])}g | "
            f"🧈 {int(log['fat'])}g | 🍞 {int(log['carbs'])}g"
        )

    lines.append(
        f"\n━━━━━━━━━━━━━━━━\n"
        f"📊 *Jami:*\n"
        f"🔥 Kaloriya: *{int(total_cal)} / {daily_norm} kkal*\n"
        f"💪 Oqsil: {int(total_pro)}g | 🧈 Yog': {int(total_fat)}g | 🍞 Uglevodlar: {int(total_carb)}g"
    )

    await message.answer("\n".join(lines))


# ─────────────────────────────────────────────
# STATISTICS
# ─────────────────────────────────────────────

@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def cmd_statistics(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.reply("Avval /start orqali ro'yxatdan o'ting.")
        return

    conn = get_conn()
    last_7_days = conn.execute(
        """SELECT date(logged_at) as day, SUM(calories) as total_cal
           FROM food_logs
           WHERE telegram_id = ? AND date(logged_at) >= date('now', '-6 days')
           GROUP BY day ORDER BY day""",
        (message.from_user.id,),
    ).fetchall()

    total_scans = conn.execute(
        "SELECT COUNT(*) FROM food_logs WHERE telegram_id = ?",
        (message.from_user.id,),
    ).fetchone()[0]
    conn.close()

    daily_norm = calculate_daily_norm(user)

    lines = [f"📊 *7 kunlik statistika*\n"]
    for row in last_7_days:
        day = row["day"]
        cal = int(row["total_cal"])
        pct = min(int(cal / daily_norm * 100), 100) if daily_norm else 0
        bar = "🟩" * int(pct / 10) + "⬜" * (10 - int(pct / 10))
        lines.append(f"📅 {day}: {bar} {cal} kkal ({pct}%)")

    lines.append(
        f"\n━━━━━━━━━━━━━━━━\n"
        f"📸 Jami skanlar: *{total_scans}*\n"
        f"🎯 Kunlik norma: *{daily_norm} kkal*"
    )

    await message.answer("\n".join(lines) if len(lines) > 2 else "📊 Hali statistika yo'q. Taom rasmini yuboring!")


# ─────────────────────────────────────────────
# WEEKLY REPORT
# ─────────────────────────────────────────────

@dp.message_handler(lambda m: m.text == "📅 Haftalik hisobot")
async def cmd_weekly_report(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.reply("Avval /start orqali ro'yxatdan o'ting.")
        return

    if not can_use_analysis(user):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("💳 Premium sotib olish", callback_data="send_receipt"))
        await message.answer(PREMIUM_MSG, reply_markup=kb)
        return

    conn = get_conn()
    rows = conn.execute(
        """SELECT date(logged_at) as day,
                  SUM(calories) as total_cal,
                  SUM(protein) as total_pro,
                  SUM(fat) as total_fat,
                  SUM(carbs) as total_carb,
                  COUNT(*) as meals
           FROM food_logs
           WHERE telegram_id = ? AND date(logged_at) >= date('now', '-6 days')
           GROUP BY day ORDER BY day""",
        (message.from_user.id,),
    ).fetchall()
    conn.close()

    if not rows:
        await message.reply("📅 Hafta uchun ma'lumot yo'q. Taom rasmini yuboring!")
        return

    daily_norm = calculate_daily_norm(user)
    days_uz = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]

    total_cal_week = sum(r["total_cal"] for r in rows)
    avg_cal = int(total_cal_week / len(rows))

    lines = [f"📅 *7 Kunlik Hisobot*\n"]
    for row in rows:
        day_dt = datetime.strptime(row["day"], "%Y-%m-%d")
        day_name = days_uz[day_dt.weekday()]
        cal = int(row["total_cal"])
        pct = min(int(cal / daily_norm * 100), 100) if daily_norm else 0
        status = "✅" if cal <= daily_norm else "⚠️"
        lines.append(
            f"{status} *{day_name}* ({row['day']}):\n"
            f"   🔥 {cal} kkal ({pct}%) | 🍽 {row['meals']} ta ovqat\n"
            f"   💪 Oqsil: {int(row['total_pro'])}g | "
            f"🧈 Yog': {int(row['total_fat'])}g | "
            f"🍞 Uglevodlar: {int(row['total_carb'])}g"
        )

    lines.append(
        f"\n━━━━━━━━━━━━━━━━\n"
        f"📊 *Haftalik xulosa:*\n"
        f"🔥 Jami kaloriya: *{int(total_cal_week)} kkal*\n"
        f"📈 O'rtacha kunlik: *{avg_cal} kkal* (norma: {daily_norm})\n"
    )

    if avg_cal > daily_norm:
        lines.append("⚠️ *Diqqat:* O'rtacha kunlik kaloriya normadan yuqori!")
    elif avg_cal < daily_norm * 0.7:
        lines.append("⚠️ *Diqqat:* O'rtacha kaloriya juda past. Ko'proq ovqatlaning!")
    else:
        lines.append("✅ *Ajoyib!* Hafta davomida norma yaxshi saqlangan.")

    await message.answer("\n".join(lines))


# ─────────────────────────────────────────────
# /MYRECEIPT — USER PAYMENT STATUS
# ─────────────────────────────────────────────

@dp.message_handler(commands=["myreceipt"])
async def cmd_myreceipt(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.reply("Avval /start orqali ro'yxatdan o'ting.")
        return

    if user["is_premium"]:
        await message.answer(
            "💎 *Siz allaqachon Premium foydalanuvchisiz!*\n\n"
            "Barcha VIP funksiyalar to'liq ochiq. Taom rasmini yuboring 🍽"
        )
        return

    conn = get_conn()
    requests_list = conn.execute(
        """SELECT status, requested_at FROM payment_requests
           WHERE telegram_id = ?
           ORDER BY requested_at DESC LIMIT 5""",
        (message.from_user.id,),
    ).fetchall()
    conn.close()

    if not requests_list:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("💳 Premium sotib olish", callback_data="send_receipt"))
        await message.answer(
            "📋 *To'lov so'rovlari topilmadi.*\n\n"
            "Premium obuna uchun to'lov qiling va chekni yuboring:",
            reply_markup=kb,
        )
        return

    status_icons = {
        "pending":  "⏳ Ko'rib chiqilmoqda",
        "approved": "✅ Tasdiqlangan",
        "denied":   "❌ Rad etilgan",
    }

    lines = ["📋 *Sizning to'lov so'rovlaringiz:*\n"]
    for i, req in enumerate(requests_list, 1):
        status_text = status_icons.get(req["status"], req["status"])
        date_str = req["requested_at"][:16].replace("T", " ")
        lines.append(f"{i}. {status_text}\n   📅 {date_str}")

    latest_status = requests_list[0]["status"]
    if latest_status == "pending":
        lines.append(
            "\n⏳ *So'rovingiz admin tomonidan ko'rib chiqilmoqda.*\n"
            "Tasdiqlangandan so'ng sizga xabar yuboriladi!"
        )
    elif latest_status == "denied":
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔄 Qayta chek yuborish", callback_data="send_receipt"))
        await message.answer("\n".join(lines), reply_markup=kb)
        return

    await message.answer("\n".join(lines))


# ─────────────────────────────────────────────
# ADMIN COMMANDS
# ─────────────────────────────────────────────

@dp.message_handler(commands=["admin"])
@admin_check
async def cmd_admin(message: types.Message):
    conn = get_conn()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_premium = conn.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
    total_scans = conn.execute("SELECT COALESCE(SUM(scan_count), 0) FROM users").fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM payment_requests WHERE status = 'pending'"
    ).fetchone()[0]
    conn.close()

    await message.answer(
        f"🛠 *Admin Panel*\n\n"
        f"👥 Jami foydalanuvchilar: *{total_users}*\n"
        f"💎 Premium foydalanuvchilar: *{total_premium}*\n"
        f"📸 Jami skanlar: *{total_scans}*\n"
        f"⏳ Kutayotgan to'lovlar: *{pending}*"
    )


@dp.message_handler(commands=["users"])
@admin_check
async def cmd_users(message: types.Message):
    conn = get_conn()
    users = conn.execute(
        "SELECT telegram_id, first_name, username, registered_at, scan_count, is_premium FROM users ORDER BY registered_at DESC LIMIT 50"
    ).fetchall()
    conn.close()

    if not users:
        await message.answer("Hali foydalanuvchilar yo'q.")
        return

    lines = [f"👥 *Foydalanuvchilar ro'yxati* (so'nggi 50)\n"]
    for u in users:
        premium = "💎" if u["is_premium"] else "🆓"
        username = f"@{u['username']}" if u["username"] else "—"
        lines.append(
            f"{premium} *{u['first_name']}* ({username})\n"
            f"   🆔 `{u['telegram_id']}` | 📸 {u['scan_count']} skan | 📅 {u['registered_at'][:10]}"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n...va boshqalar"
    await message.answer(text)


@dp.message_handler(commands=["premium_list"])
@admin_check
async def cmd_premium_list(message: types.Message):
    conn = get_conn()
    users = conn.execute(
        """SELECT telegram_id, first_name, username, registered_at, scan_count
           FROM users WHERE is_premium = 1 ORDER BY registered_at DESC"""
    ).fetchall()
    conn.close()

    if not users:
        await message.answer("Hali premium foydalanuvchilar yo'q.")
        return

    lines = [f"💎 *Premium foydalanuvchilar*\n"]
    for u in users:
        username = f"@{u['username']}" if u["username"] else "—"
        lines.append(
            f"• *{u['first_name']}* ({username})\n"
            f"  🆔 `{u['telegram_id']}` | 📸 {u['scan_count']} skan | 📅 {u['registered_at'][:10]}"
        )

    await message.answer("\n".join(lines))


@dp.message_handler(commands=["broadcast"])
@admin_check
async def cmd_broadcast(message: types.Message):
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply("Ishlatish: /broadcast [xabar matni]")
        return

    text = parts[1]
    conn = get_conn()
    users = conn.execute("SELECT telegram_id FROM users").fetchall()
    conn.close()

    sent, failed = 0, 0
    for u in users:
        try:
            await bot.send_message(u["telegram_id"], f"📢 *Admin xabari:*\n\n{text}")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await message.reply(
        f"📢 *Xabar tarqatildi!*\n\n"
        f"✅ Yuborildi: {sent}\n"
        f"❌ Yuborilmadi: {failed}"
    )


# ─────────────────────────────────────────────
# FALLBACK
# ─────────────────────────────────────────────

@dp.message_handler(content_types=types.ContentType.ANY)
async def fallback(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return

    user = get_user(message.from_user.id)
    if not user:
        await message.reply("Iltimos /start bosing va ro'yxatdan o'ting.")
        return

    await message.reply(
        "📸 Taom rasmini yuboring — tahlil qilib beraman!\n"
        "Yoki quyidagi menyudan tanlang:",
        reply_markup=main_menu_keyboard(),
    )


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    logger.info("Taom AI bot ishga tushmoqda...")
    executor.start_polling(dp, skip_updates=True)
