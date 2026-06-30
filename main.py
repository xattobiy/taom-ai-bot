# -*- coding: utf-8 -*-
import asyncio
import logging
import os
import re
import time
import sqlite3
from datetime import datetime, timedelta
import pytz

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

from google import genai
from google.genai import types as genai_types

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("BOT_TOKEN",      "YOUR_BOT_TOKEN")
ADMIN_ID    = int(os.environ.get("ADMIN_ID",   "956947665"))
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
DB_PATH     = "taom_ai.db"
TRIAL_DAYS  = 3
CARD_NUMBER = "8600 **** **** ****"   # ← show masked number to users
TZ          = pytz.timezone("Asia/Tashkent")

logging.basicConfig(level=logging.INFO)
bot    = Bot(token=BOT_TOKEN)
dp     = Dispatcher(storage=MemoryStorage())
gemini = genai.Client(api_key=GEMINI_KEY)

# ── TRANSLATIONS ──────────────────────────────────────────────────────────────
LANGS = {
    "uz": {
        "welcome":        "Assalomu alaykum! Men sizning diyeta yordamchingizman 🥗\nTanishishni boshlasak, yoshingizdan boshlaymiz. Yoshingiz nechida?",
        "ask_height":     "Bo'yingiz qancha? (masalan: 170 sm) 📏",
        "ask_weight":     "Vazningiz qancha? (masalan: 60 kg) ⚖️",
        "ask_goal":       "Maqsadingizni tanlang:",
        "ask_gender":     "Jinsingizni tanlang:",
        "goal_lose":      "Ozish 🔥",
        "goal_gain":      "Vazn qo'shish 💪",
        "goal_keep":      "Vaznni ushlab qolish ⚖️",
        "gender_male":    "Erkak 🧑",
        "gender_female":  "Ayol 👩",
        "ask_activity":   "Kunlik faollik darajangizni tanlang: 🏃",
        "activity_low":   "🚶 Kam faol (kam harakatlanaman)",
        "activity_medium":"🚴 O'rta faol (ba'zan sport qilaman)",
        "activity_high":  "🏋️ Juda faol (muntazam sport)",
        "reg_done":       "🎉 Ro'yxatdan o'tganingiz bilan tabriklayman!\n\nBu botda siz o'z vazningizni oson nazorat qila olasiz 📊\n\nSovg'a sifatida sizga 3 kunlik FREE TRIAL taqdim qilamiz 🎁\n\nTanishtiruv tugadi — endi botdagi imkoniyatlarga o'tamiz!",
        "main_menu":      "Asosiy menyu 🏠",
        "btn_ration":     "🍽 Kunlik ratsion",
        "btn_food_today": "📋 Bugungi ovqatlar",
        "btn_food_week":  "📅 Haftalik hisobot",
        "btn_food_month": "📆 Oylik hisobot",
        "btn_water":      "💧 Suv ratsioni",
        "btn_ai":         "🤖 AI Diyetolog",
        "btn_profile":    "👤 Profilim",
        "btn_vip":        "⭐ VIP sotib olish",
        "btn_check":      "🧾 Chek yuborish",
        "btn_photo_food": "📸 Ovqat rasmi",
        # ── FIXED: unified paywall message ──
        "paywall":        "⚠️ Bu imkoniyat faqat VIP obunachilar uchun mavjud! Barcha funksiyalardan cheksiz foydalanish uchun VIP obunani sotib oling.",
        "vip_only":       "Bu imkoniyat faqat VIP tarifda mavjud! ⭐\n\nVIP sotib olish uchun /vip buyrug'ini yuboring.",
        "trial_expired":  "Bepul sinov muddati tugadi! ⏰\n\nBarcha imkoniyatlardan foydalanish uchun VIP obuna oling.",
        "lang_select":    "Tilni tanlang / Choose language / Выберите язык:",
    },
    "ru": {
        "welcome":        "Ассалому алейкум! Я ваш диетический помощник 🥗\nДавайте познакомимся. Сколько вам лет?",
        "ask_height":     "Какой у вас рост? (например: 170 см) 📏",
        "ask_weight":     "Какой у вас вес? (например: 60 кг) ⚖️",
        "ask_goal":       "Выберите вашу цель:",
        "ask_gender":     "Выберите ваш пол:",
        "goal_lose":      "Похудеть 🔥",
        "goal_gain":      "Набрать вес 💪",
        "goal_keep":      "Поддержать вес ⚖️",
        "gender_male":    "Мужчина 🧑",
        "gender_female":  "Женщина 👩",
        "ask_activity":   "Выберите уровень активности: 🏃",
        "activity_low":   "🚶 Малоактивный (мало движения)",
        "activity_medium":"🚴 Умеренно активный (иногда спорт)",
        "activity_high":  "🏋️ Очень активный (регулярный спорт)",
        "reg_done":       "🎉 Поздравляю с регистрацией!\n\nВ этом боте вы легко можете контролировать свой вес 📊\n\nВ подарок предоставляем 3-дневный FREE TRIAL 🎁\n\nЗнакомство завершено — переходим к возможностям бота!",
        "main_menu":      "Главное меню 🏠",
        "btn_ration":     "🍽 Дневной рацион",
        "btn_food_today": "📋 Еда за сегодня",
        "btn_food_week":  "📅 Недельный отчёт",
        "btn_food_month": "📆 Месячный отчёт",
        "btn_water":      "💧 Водный рацион",
        "btn_ai":         "🤖 AI Диетолог",
        "btn_profile":    "👤 Мой профиль",
        "btn_vip":        "⭐ Купить VIP",
        "btn_check":      "🧾 Отправить чек",
        "btn_photo_food": "📸 Фото еды",
        "paywall":        "⚠️ Bu imkoniyat faqat VIP obunachilar uchun mavjud! Barcha funksiyalardan cheksiz foydalanish uchun VIP obunani sotib oling.",
        "vip_only":       "Эта функция доступна только в VIP тарифе! ⭐\n\nДля покупки VIP отправьте /vip.",
        "trial_expired":  "Бесплатный пробный период закончился! ⏰\n\nКупите VIP подписку для доступа ко всем функциям.",
        "lang_select":    "Tilni tanlang / Choose language / Выберите язык:",
    },
    "en": {
        "welcome":        "Hello! I am your diet assistant 🥗\nLet's get acquainted. How old are you?",
        "ask_height":     "What is your height? (e.g. 170 cm) 📏",
        "ask_weight":     "What is your weight? (e.g. 60 kg) ⚖️",
        "ask_goal":       "Choose your goal:",
        "ask_gender":     "Choose your gender:",
        "goal_lose":      "Lose weight 🔥",
        "goal_gain":      "Gain weight 💪",
        "goal_keep":      "Maintain weight ⚖️",
        "gender_male":    "Male 🧑",
        "gender_female":  "Female 👩",
        "ask_activity":   "Select your activity level: 🏃",
        "activity_low":   "🚶 Low active (little movement)",
        "activity_medium":"🚴 Moderately active (some exercise)",
        "activity_high":  "🏋️ Very active (regular exercise)",
        "reg_done":       "🎉 Congratulations on registering!\n\nIn this bot you can easily track your weight 📊\n\nAs a gift we give you a 3-day FREE TRIAL 🎁\n\nIntro done — let's move to bot features!",
        "main_menu":      "Main menu 🏠",
        "btn_ration":     "🍽 Daily Ration",
        "btn_food_today": "📋 Today's food",
        "btn_food_week":  "📅 Weekly report",
        "btn_food_month": "📆 Monthly report",
        "btn_water":      "💧 Water ration",
        "btn_ai":         "🤖 AI Dietologist",
        "btn_profile":    "👤 My profile",
        "btn_vip":        "⭐ Buy VIP",
        "btn_check":      "🧾 Send receipt",
        "btn_photo_food": "📸 Food photo",
        "paywall":        "⚠️ Bu imkoniyat faqat VIP obunachilar uchun mavjud! Barcha funksiyalardan cheksiz foydalanish uchun VIP obunani sotib oling.",
        "vip_only":       "This feature is only available in VIP! ⭐\n\nSend /vip to purchase.",
        "trial_expired":  "Free trial expired! ⏰\n\nBuy VIP subscription to access all features.",
        "lang_select":    "Tilni tanlang / Choose language / Выберите язык:",
    }
}

def t(user_lang, key, **kwargs):
    lang = user_lang if user_lang in LANGS else "uz"
    text = LANGS[lang].get(key, LANGS["uz"].get(key, key))
    return text.format(**kwargs) if kwargs else text

# ── DATABASE ──────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id  INTEGER PRIMARY KEY,
            username     TEXT,
            first_name   TEXT,
            lang         TEXT DEFAULT 'uz',
            age          INTEGER,
            gender       TEXT,
            activity     TEXT DEFAULT 'medium',
            height       REAL,
            weight       REAL,
            target       TEXT,
            calories_goal REAL,
            trial_start  TEXT,
            is_vip       INTEGER DEFAULT 0,
            vip_start    TEXT,
            vip_end      TEXT
        );
        CREATE TABLE IF NOT EXISTS food_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER,
            food_name    TEXT,
            calories     REAL,
            protein      REAL DEFAULT 0,
            fat          REAL DEFAULT 0,
            carbs        REAL DEFAULT 0,
            meal_type    TEXT,
            logged_at    TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS water_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER,
            amount_ml    INTEGER DEFAULT 250,
            logged_at    TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payment_requests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER,
            plan         TEXT,
            photo_file_id TEXT,
            status       TEXT DEFAULT 'pending',
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    # Migrations for existing DBs
    for col in [
        "ALTER TABLE food_logs ADD COLUMN protein REAL DEFAULT 0",
        "ALTER TABLE food_logs ADD COLUMN fat REAL DEFAULT 0",
        "ALTER TABLE food_logs ADD COLUMN carbs REAL DEFAULT 0",
        "ALTER TABLE payment_requests ADD COLUMN plan TEXT",
    ]:
        try:
            conn.execute(col); conn.commit()
        except Exception:
            pass
    conn.close()

def get_user(tid):
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
    conn.close()
    return dict(user) if user else None

def save_user(tid, **kwargs):
    conn = get_conn()
    user = conn.execute("SELECT telegram_id FROM users WHERE telegram_id=?", (tid,)).fetchone()
    if user:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [tid]
        conn.execute(f"UPDATE users SET {sets} WHERE telegram_id=?", vals)
    else:
        kwargs["telegram_id"] = tid
        cols = ", ".join(kwargs.keys())
        phs  = ", ".join("?" * len(kwargs))
        conn.execute(f"INSERT INTO users ({cols}) VALUES ({phs})", list(kwargs.values()))
    conn.commit()
    conn.close()

def is_vip(user):
    """True only for confirmed VIP users (not trial)."""
    return bool(user and user.get("is_vip"))

def is_vip_or_trial(user):
    if not user:
        return False
    if user.get("is_vip"):
        return True
    ts = user.get("trial_start")
    if ts:
        start = datetime.fromisoformat(ts)
        return datetime.now() < start + timedelta(days=TRIAL_DAYS)
    return False

def get_trial_remaining(user):
    ts = user.get("trial_start")
    if not ts:
        return 0
    start = datetime.fromisoformat(ts)
    remaining = (start + timedelta(days=TRIAL_DAYS) - datetime.now()).days
    return max(0, remaining)

def calc_calories_goal(user):
    try:
        w      = float(user.get("weight", 70))
        h      = float(user.get("height", 170))
        a      = int(user.get("age", 30))
        g      = user.get("gender", "male")
        target = user.get("target", "keep")
        activity = user.get("activity", "medium")
        if "male" in g.lower() or "erkak" in g.lower() or "мужчина" in g.lower():
            bmr = 10 * w + 6.25 * h - 5 * a + 5
        else:
            bmr = 10 * w + 6.25 * h - 5 * a - 161
        act_map = {"low": 1.2, "medium": 1.55, "high": 1.725}
        tdee = bmr * act_map.get(activity, 1.55)
        if "lose" in target or "ozish" in target or "похуд" in target.lower():
            return round(tdee - 500)
        elif "gain" in target or "qoshish" in target or "набрать" in target.lower():
            return round(tdee + 500)
        else:
            return round(tdee)
    except Exception:
        return 2000

def get_meal_type():
    now = datetime.now(TZ).hour
    if 6  <= now < 11: return "nonushta"
    if 11 <= now < 16: return "tushlik"
    if 16 <= now < 21: return "kechki"
    return "kechasi"

def meal_label(mt, lang="uz"):
    mapping = {
        "uz": {"nonushta": "🌅 Nonushta", "tushlik": "☀️ Tushlik",
               "kechki":   "🌙 Kechki ovqat", "kechasi": "🌃 Kechasi"},
        "ru": {"nonushta": "🌅 Завтрак",  "tushlik": "☀️ Обед",
               "kechki":   "🌙 Ужин",     "kechasi": "🌃 Ночь"},
        "en": {"nonushta": "🌅 Breakfast","tushlik": "☀️ Lunch",
               "kechki":   "🌙 Dinner",   "kechasi": "🌃 Night"},
    }
    return mapping.get(lang, mapping["uz"]).get(mt, mt)

# ── FSM STATES ────────────────────────────────────────────────────────────────
class Reg(StatesGroup):
    lang     = State()
    age      = State()
    height   = State()
    weight   = State()
    goal     = State()
    gender   = State()
    activity = State()

class EditProfile(StatesGroup):
    field = State()
    value = State()

# ── FIXED: PaymentState now tracks which plan was selected ──
class PaymentState(StatesGroup):
    choosing_plan    = State()   # waiting for Oylik / Yillik click
    waiting_receipt  = State()   # waiting for receipt photo

class AIChat(StatesGroup):
    chatting = State()

class BroadcastState(StatesGroup):
    message = State()

# ── KEYBOARDS ─────────────────────────────────────────────────────────────────
def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbek",   callback_data="lang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский",  callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English",  callback_data="lang_en"),
    ]])

def goal_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "goal_lose"))],
                  [KeyboardButton(text=t(lang, "goal_gain"))],
                  [KeyboardButton(text=t(lang, "goal_keep"))]],
        resize_keyboard=True, one_time_keyboard=True)

def gender_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "gender_male")),
                   KeyboardButton(text=t(lang, "gender_female"))]],
        resize_keyboard=True, one_time_keyboard=True)

def activity_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "activity_low"))],
                  [KeyboardButton(text=t(lang, "activity_medium"))],
                  [KeyboardButton(text=t(lang, "activity_high"))]],
        resize_keyboard=True, one_time_keyboard=True)

def main_menu_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_ration")),     KeyboardButton(text=t(lang, "btn_water"))],
            [KeyboardButton(text=t(lang, "btn_food_today")), KeyboardButton(text=t(lang, "btn_food_week"))],
            [KeyboardButton(text=t(lang, "btn_food_month")), KeyboardButton(text=t(lang, "btn_ai"))],
            [KeyboardButton(text=t(lang, "btn_profile")),    KeyboardButton(text=t(lang, "btn_vip"))],
            [KeyboardButton(text=t(lang, "btn_photo_food"))],
        ],
        resize_keyboard=True)

def photo_food_kb(lang, pending_id):
    labels = {
        "uz": ("Yeyman 😋", "Bekor ❌"),
        "ru": ("Съем 😋",   "Отмена ❌"),
        "en": ("I'll eat 😋","Cancel ❌"),
    }
    eat, cancel = labels.get(lang, labels["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=eat,    callback_data=f"eat_{pending_id}"),
        InlineKeyboardButton(text=cancel, callback_data=f"cancel_food_{pending_id}"),
    ]])

# ── NEW: VIP plan selection inline keyboard ───────────────────────────────────
def vip_plans_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Oylik — 20,000 so'm",   callback_data="vip_plan_monthly")],
        [InlineKeyboardButton(text="📆 Yillik — 220,000 so'm", callback_data="vip_plan_yearly")],
    ])

# ── NEW: Admin "Make VIP" button ──────────────────────────────────────────────
def admin_vip_kb(user_id: int, req_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ VIP qilish",
            callback_data=f"admin_approve_{user_id}_{req_id}"
        ),
        InlineKeyboardButton(
            text="❌ Rad etish",
            callback_data=f"admin_reject_{user_id}_{req_id}"
        ),
    ]])

def profile_kb(lang):
    labels = {
        "uz": ("👤 Men haqimda", "💳 Obunam haqida", "✏️ Men o'zgardim", "🏠 Orqaga"),
        "ru": ("👤 Обо мне",    "💳 О подписке",    "✏️ Я изменился",   "🏠 Назад"),
        "en": ("👤 About me",   "💳 Subscription",  "✏️ I changed",     "🏠 Back"),
    }
    a, b, c, d = labels.get(lang, labels["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a, callback_data="prof_info"),
         InlineKeyboardButton(text=b, callback_data="prof_sub")],
        [InlineKeyboardButton(text=c, callback_data="prof_edit")],
        [InlineKeyboardButton(text=d, callback_data="prof_back")],
    ])

def edit_profile_kb(lang):
    labels = {
        "uz": [("📏 Bo'y","edit_height"),("⚖️ Vazn","edit_weight"),
               ("🎂 Yosh","edit_age"),  ("🎯 Maqsad","edit_target"),
               ("🏃 Faollik","edit_activity"),("🔙 Orqaga","prof_back")],
        "ru": [("📏 Рост","edit_height"),("⚖️ Вес","edit_weight"),
               ("🎂 Возраст","edit_age"),("🎯 Цель","edit_target"),
               ("🏃 Активность","edit_activity"),("🔙 Назад","prof_back")],
        "en": [("📏 Height","edit_height"),("⚖️ Weight","edit_weight"),
               ("🎂 Age","edit_age"),    ("🎯 Goal","edit_target"),
               ("🏃 Activity","edit_activity"),("🔙 Back","prof_back")],
    }
    rows = [[InlineKeyboardButton(text=b[0], callback_data=b[1])]
            for b in labels.get(lang, labels["uz"])]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def water_kb(lang):
    labels = {
        "uz": ("✅ Ichdim 💧",   "📊 Bugungi suv"),
        "ru": ("✅ Выпил 💧",    "📊 Вода за сегодня"),
        "en": ("✅ Drank 💧",    "📊 Today water"),
    }
    a, b = labels.get(lang, labels["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a, callback_data="water_drank")],
        [InlineKeyboardButton(text=b, callback_data="water_today")],
    ])

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_user_lang(tid):
    u = get_user(tid)
    return u.get("lang", "uz") if u else "uz"

pending_food: dict = {}   # pend_id -> {tid, cal, food, protein, fat, carbs, meal_type, lang}

# ── FOOD PHOTO ANALYSIS (shared helper) ──────────────────────────────────────
# ── FIXED: extracted into a standalone coroutine so it can be called from
#    both the default_state photo handler AND the AIChat photo handler ─────────
async def _analyze_food_photo(message: types.Message):
    """Download the photo, send it to Gemini, return formatted result."""
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang", "uz") if user else "uz"

    # Acknowledge while processing
    if lang == "ru":
        wait_msg = await message.answer("⏳ Tahlil qilinmoqda...")
    elif lang == "en":
        wait_msg = await message.answer("⏳ Analyzing...")
    else:
        wait_msg = await message.answer("⏳ Tahlil qilinmoqda...")

    try:
        photo   = message.photo[-1]                       # highest resolution
        file    = await bot.get_file(photo.file_id)
        dl      = await bot.download_file(file.file_path) # returns BytesIO
        img_bytes = dl.read()

        meal_t = get_meal_type()

        if lang == "ru":
            prompt = (
                "На этом фото — еда? Если нет — напиши только 'НЕ ЕДА'.\n"
                "Если да — определи блюдо, реалистично оцени порцию и рассчитай:\n\n"
                "Блюдо: [название]\n"
                "Граммы: [число] г\n"
                "Калории: [число] ккал\n"
                "Белки: [число] г\n"
                "Жиры: [число] г\n"
                "Углеводы: [число] г\n\n"
                "Только эти строки, без лишних слов."
            )
        elif lang == "en":
            prompt = (
                "Is this food? If not — write only 'NOT FOOD'.\n"
                "If yes — identify the dish, estimate realistic portion and calculate:\n\n"
                "Dish: [name]\n"
                "Grams: [number] g\n"
                "Calories: [number] kcal\n"
                "Protein: [number] g\n"
                "Fat: [number] g\n"
                "Carbs: [number] g\n\n"
                "Only these lines, nothing extra."
            )
        else:  # uz
            prompt = (
                "Bu rasmdagi narsa ovqatmi? Agar yo'q bo'lsa — faqat 'OVQAT EMAS' deb yoz.\n"
                "Agar ha bo'lsa — taomni aniqlang, real porsiyani baholang va hisoblang:\n\n"
                "Taom: [nom]\n"
                "Gramm: [son] g\n"
                "Kaloriya: [son] kkal\n"
                "Oqsillar: [son] g\n"
                "Yog'lar: [son] g\n"
                "Uglevodlar: [son] g\n\n"
                "Faqat shu satrlar, ortiqcha so'zsiz."
            )

        resp = await asyncio.to_thread(
            gemini.models.generate_content,
            model="gemini-1.5-flash",
            contents=[genai_types.Content(parts=[
                genai_types.Part(inline_data=genai_types.Blob(
                    mime_type="image/jpeg",
                    data=img_bytes
                )),
                genai_types.Part(text=prompt),
            ])]
        )
        result = resp.text.strip()

        # Try to delete "processing" message
        try:
            await wait_msg.delete()
        except Exception:
            pass

        if any(x in result.upper() for x in ["NET", "НЕ ЕДА", "NOT FOOD", "OVQAT EMAS"]):
            if lang == "ru":
                await message.answer("🤔 Это не похоже на еду. Отправьте фото блюда!")
            elif lang == "en":
                await message.answer("🤔 That doesn't look like food. Send a photo of a dish!")
            else:
                await message.answer("🤔 Bu ovqat emas. Ovqat rasmini yuboring!")
            return

        # Parse result
        cal = protein = fat = carbs = 0.0
        food_name = "Noma'lum taom"

        for line in result.split("\n"):
            lo = line.lower()
            nums = re.findall(r'\d+\.?\d*', line)
            if any(k in lo for k in ["taom:", "dish:", "блюдо:"]):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    food_name = parts[1].strip()
            elif any(k in lo for k in ["kaloriya", "калории", "calories", "ккал", "kkal", "kcal"]):
                if nums: cal = float(nums[0])
            elif any(k in lo for k in ["oqsil", "белки", "protein"]):
                if nums: protein = float(nums[0])
            elif any(k in lo for k in ["yog'", "жиры", "fat", "жир"]):
                if nums: fat = float(nums[0])
            elif any(k in lo for k in ["uglevodlar", "углеводы", "carbs"]):
                if nums: carbs = float(nums[0])

        pend_id = int(time.time() * 1000) % 10_000_000
        pending_food[pend_id] = {
            "tid": tid, "cal": cal, "food": food_name,
            "protein": protein, "fat": fat, "carbs": carbs,
            "meal_type": meal_t, "lang": lang,
        }

        if lang == "ru":
            header = f"🍽 Анализ ({meal_label(meal_t,'ru')}):\n\n"
        elif lang == "en":
            header = f"🍽 Analysis ({meal_label(meal_t,'en')}):\n\n"
        else:
            header = f"🍽 Tahlil ({meal_label(meal_t,'uz')}):\n\n"

        await message.answer(header + result, reply_markup=photo_food_kb(lang, pend_id))

    except Exception as e:
        logging.error(f"Food photo analysis error: {e}")
        try:
            await wait_msg.delete()
        except Exception:
            pass
        if lang == "ru":
            await message.answer("❌ Tahlil xatoligi. Keyinroq urinib ko'ring.")
        elif lang == "en":
            await message.answer("❌ Analysis error. Try again later.")
        else:
            await message.answer("❌ Tahlil xatoligi. Keyinroq urinib ko'ring.")


# ═══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION ORDER (most specific → least specific)
# ═══════════════════════════════════════════════════════════════════════════════

# ── /start ────────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(LANGS["uz"]["lang_select"], reply_markup=lang_kb())
    await state.set_state(Reg.lang)


# ── /menu (exit AI chat, etc.) ────────────────────────────────────────────────
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    await state.clear()
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang", "uz") if user else "uz"
    await message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))


# ── /vip command ──────────────────────────────────────────────────────────────
@dp.message(Command("vip"))
async def cmd_vip(message: types.Message, state: FSMContext):
    await state.clear()
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang", "uz") if user else "uz"
    await _show_vip_plans(message, lang, state)


# ── REGISTRATION FLOW ─────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("lang_"), Reg.lang)
async def cb_lang(call: types.CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text(t(lang, "welcome"))
    await state.set_state(Reg.age)
    await call.answer()

@dp.message(Reg.lang)
async def reg_lang_text(message: types.Message, state: FSMContext):
    await message.answer(LANGS["uz"]["lang_select"], reply_markup=lang_kb())

@dp.message(Reg.age)
async def reg_age(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    try:
        age = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting!")
        return
    await state.update_data(age=age)
    await message.answer(t(lang, "ask_height"))
    await state.set_state(Reg.height)

@dp.message(Reg.height)
async def reg_height(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    txt  = message.text.strip().replace("sm","").replace("см","").replace("cm","").strip()
    try:
        height = float(txt)
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri qiymat kiriting! Masalan: 170")
        return
    await state.update_data(height=height)
    await message.answer(t(lang, "ask_weight"))
    await state.set_state(Reg.weight)

@dp.
