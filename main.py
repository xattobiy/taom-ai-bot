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
#  HANDLER REGISTRATION ORDER  (specific → generic, registration first)
# ═══════════════════════════════════════════════════════════════════════════════

# ── 1. /start  ───────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(LANGS["uz"]["lang_select"], reply_markup=lang_kb())
    await state.set_state(Reg.lang)

# ── 2. /menu  ────────────────────────────────────────────────────────────────
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    await state.clear()
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang", "uz") if user else "uz"
    await message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))

# ── 3. /vip  ─────────────────────────────────────────────────────────────────
@dp.message(Command("vip"))
async def cmd_vip(message: types.Message, state: FSMContext):
    await state.clear()
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang", "uz") if user else "uz"
    await _show_vip_plans(message, lang, state)

# ── 4. REGISTRATION FSM — language choice (inline button, Reg.lang state) ────
@dp.callback_query(F.data.startswith("lang_"), StateFilter(Reg.lang))
async def cb_lang(call: types.CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text(t(lang, "welcome"))
    await state.set_state(Reg.age)
    await call.answer()

@dp.message(StateFilter(Reg.lang))
async def reg_lang_text(message: types.Message, state: FSMContext):
    await message.answer(LANGS["uz"]["lang_select"], reply_markup=lang_kb())

# ── 5. REGISTRATION FSM — age ─────────────────────────────────────────────────
@dp.message(StateFilter(Reg.age))
async def reg_age(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    try:
        age = int(message.text.strip())
        if age < 5 or age > 120:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri yosh kiriting (5-120)!")
        return
    await state.update_data(age=age)
    await message.answer(t(lang, "ask_height"))
    await state.set_state(Reg.height)

# ── 6. REGISTRATION FSM — height ─────────────────────────────────────────────
@dp.message(StateFilter(Reg.height))
async def reg_height(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    txt = message.text.strip().replace("sm","").replace("см","").replace("cm","").strip()
    try:
        height = float(txt)
        if height < 50 or height > 250:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri qiymat kiriting! Masalan: 170")
        return
    await state.update_data(height=height)
    await message.answer(t(lang, "ask_weight"))
    await state.set_state(Reg.weight)

# ── 7. REGISTRATION FSM — weight ────────────────────────────────────────────
@dp.message(StateFilter(Reg.weight))
async def reg_weight(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    txt = message.text.strip().replace("kg","").replace("кг","").strip()
    try:
        weight = float(txt)
        if weight < 20 or weight > 300:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri vazn kiriting! Masalan: 70")
        return
    await state.update_data(weight=weight)
    await message.answer(t(lang, "ask_goal"), reply_markup=goal_kb(lang))
    await state.set_state(Reg.goal)

# ── 8. REGISTRATION FSM — goal ───────────────────────────────────────────────
@dp.message(StateFilter(Reg.goal))
async def reg_goal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    valid = [t(lang, "goal_lose"), t(lang, "goal_gain"), t(lang, "goal_keep")]
    if message.text not in valid:
        await message.answer(t(lang, "ask_goal"), reply_markup=goal_kb(lang))
        return
    await state.update_data(target=message.text)
    await message.answer(t(lang, "ask_gender"), reply_markup=gender_kb(lang))
    await state.set_state(Reg.gender)

# ── 9. REGISTRATION FSM — gender ─────────────────────────────────────────────
@dp.message(StateFilter(Reg.gender))
async def reg_gender(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    valid = [t(lang, "gender_male"), t(lang, "gender_female")]
    if message.text not in valid:
        await message.answer(t(lang, "ask_gender"), reply_markup=gender_kb(lang))
        return
    await state.update_data(gender=message.text)
    await message.answer(t(lang, "ask_activity"), reply_markup=activity_kb(lang))
    await state.set_state(Reg.activity)

# ── 10. REGISTRATION FSM — activity (FINAL STEP) ─────────────────────────────
@dp.message(StateFilter(Reg.activity))
async def reg_activity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    act_map = {
        t(lang, "activity_low"):    "low",
        t(lang, "activity_medium"): "medium",
        t(lang, "activity_high"):   "high",
    }
    if message.text not in act_map:
        await message.answer(t(lang, "ask_activity"), reply_markup=activity_kb(lang))
        return
    activity = act_map[message.text]
    await state.update_data(activity=activity)
    data = await state.get_data()

    tid = message.from_user.id
    uname = message.from_user.username or ""
    fname = message.from_user.first_name or ""

    # Save user to DB
    save_user(
        tid,
        username=uname,
        first_name=fname,
        lang=lang,
        age=data.get("age"),
        height=data.get("height"),
        weight=data.get("weight"),
        target=data.get("target", ""),
        gender=data.get("gender", ""),
        activity=activity,
        trial_start=datetime.now().isoformat(),
        is_vip=0,
    )
    user = get_user(tid)
    cal_goal = calc_calories_goal(user)
    save_user(tid, calories_goal=cal_goal)

    await state.clear()
    await message.answer(t(lang, "reg_done"), reply_markup=ReplyKeyboardRemove())
    await message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))

# ── 11. EDIT PROFILE FSM ────────────────────────────────────────────────────
@dp.message(StateFilter(EditProfile.value))
async def edit_profile_value(message: types.Message, state: FSMContext):
    data  = await state.get_data()
    field = data.get("field")
    tid   = message.from_user.id
    user  = get_user(tid)
    lang  = user.get("lang", "uz") if user else "uz"
    txt   = message.text.strip()

    if field == "height":
        try:
            val = float(txt.replace("sm","").replace("sm","").replace("cm",""))
            save_user(tid, height=val)
        except ValueError:
            await message.answer("❌ To'g'ri qiymat kiriting! Masalan: 170")
            return
    elif field == "weight":
        try:
            val = float(txt.replace("kg","").replace("кг",""))
            save_user(tid, weight=val)
        except ValueError:
            await message.answer("❌ To'g'ri vazn kiriting! Masalan: 70")
            return
    elif field == "age":
        try:
            val = int(txt)
            save_user(tid, age=val)
        except ValueError:
            await message.answer("❌ To'g'ri yosh kiriting!")
            return
    elif field == "target":
        save_user(tid, target=txt)
    elif field == "activity":
        act_map = {"low": "low", "medium": "medium", "high": "high",
                   "kam": "low", "o'rta": "medium", "yuqori": "high"}
        activity = act_map.get(txt.lower(), "medium")
        save_user(tid, activity=activity)

    # Recalculate calories
    user = get_user(tid)
    save_user(tid, calories_goal=calc_calories_goal(user))

    await state.clear()
    labels = {"uz": "✅ Ma'lumot yangilandi!", "ru": "✅ Данные обновлены!", "en": "✅ Updated!"}
    await message.answer(labels.get(lang, labels["uz"]), reply_markup=main_menu_kb(lang))

# ── 12. PAYMENT FSM — waiting for receipt photo ──────────────────────────────
@dp.message(StateFilter(PaymentState.waiting_receipt), F.photo)
async def payment_receipt_photo(message: types.Message, state: FSMContext):
    data   = await state.get_data()
    plan   = data.get("plan", "unknown")
    tid    = message.from_user.id
    user   = get_user(tid)
    lang   = user.get("lang", "uz") if user else "uz"
    fid    = message.photo[-1].file_id

    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_requests (telegram_id, plan, photo_file_id) VALUES (?,?,?)",
        (tid, plan, fid)
    )
    conn.commit()
    req_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    await state.clear()
    labels = {
        "uz": "✅ Chekingiz qabul qilindi! Admin tekshirib, tez orada VIP beriladi.",
        "ru": "✅ Чек принят! Администратор проверит и выдаст VIP.",
        "en": "✅ Receipt received! Admin will verify and grant VIP soon.",
    }
    await message.answer(labels.get(lang, labels["uz"]), reply_markup=main_menu_kb(lang))

    # Notify admin
    plan_label = "Oylik (20,000)" if plan == "monthly" else "Yillik (220,000)"
    uname = message.from_user.username or str(tid)
    fname = message.from_user.first_name or ""
    admin_text = (f"💳 Yangi to'lov so'rovi!\n\n"
                  f"👤 {fname} (@{uname}) — ID: {tid}\n"
                  f"📦 Tarif: {plan_label}\n"
                  f"🆔 Request ID: {req_id}")
    try:
        await bot.send_photo(
            ADMIN_ID, fid,
            caption=admin_text,
            reply_markup=admin_vip_kb(tid, req_id)
        )
    except Exception as e:
        logging.error(f"Admin notify error: {e}")

@dp.message(StateFilter(PaymentState.waiting_receipt))
async def payment_receipt_not_photo(message: types.Message, state: FSMContext):
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang", "uz") if user else "uz"
    labels = {
        "uz": "📸 Iltimos, to'lov chekini RASM sifatida yuboring!",
        "ru": "📸 Пожалуйста, отправьте фото чека!",
        "en": "📸 Please send the payment receipt as a PHOTO!",
    }
    await message.answer(labels.get(lang, labels["uz"]))

# ── 13. VIP PLAN SELECTION callbacks ─────────────────────────────────────────
@dp.callback_query(F.data.startswith("vip_plan_"))
async def cb_vip_plan(call: types.CallbackQuery, state: FSMContext):
    plan = call.data.replace("vip_plan_", "")  # "monthly" or "yearly"
    tid  = call.from_user.id
    user = get_user(tid)
    lang = user.get("lang", "uz") if user else "uz"

    price = "20,000 so'm" if plan == "monthly" else "220,000 so'm"
    labels = {
        "uz": (f"💳 {price} miqdorida {CARD_NUMBER} kartasiga o'tkazing.\n\nTo'lovdan so'ng chekni yuboring:"),
        "ru": (f"💳 Переведите {price} на карту {CARD_NUMBER}.\n\nПосле оплаты отправьте чек:"),
        "en": (f"💳 Transfer {price} to card {CARD_NUMBER}.\n\nAfter payment send the receipt:"),
    }
    await call.message.edit_text(labels.get(lang, labels["uz"]))
    await state.update_data(plan=plan)
    await state.set_state(PaymentState.waiting_receipt)
    await call.answer()

# ── 14. ADMIN APPROVE / REJECT callbacks ─────────────────────────────────────
@dp.callback_query(F.data.startswith("admin_approve_"))
async def cb_admin_approve(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Ruxsat yo'q!")
        return
    _, _, user_id_s, req_id_s = call.data.split("_", 3)
    user_id = int(user_id_s)
    req_id  = int(req_id_s)

    save_user(user_id, is_vip=1,
              vip_start=datetime.now().isoformat(),
              vip_end=(datetime.now() + timedelta(days=365)).isoformat())
    conn = get_conn()
    conn.execute("UPDATE payment_requests SET status='approved' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

    try:
        user = get_user(user_id)
        lang = user.get("lang","uz") if user else "uz"
        labels = {
            "uz": "🎉 VIP obuna faollashtirildi! Endi barcha imkoniyatlardan foydalaning.",
            "ru": "🎉 VIP подписка активирована!",
            "en": "🎉 VIP subscription activated!",
        }
        await bot.send_message(user_id, labels.get(lang, labels["uz"]))
    except Exception as e:
        logging.error(f"VIP notify error: {e}")

    await call.message.edit_caption(call.message.caption + "\n\n✅ TASDIQLANDI")
    await call.answer("✅ VIP berildi!")

@dp.callback_query(F.data.startswith("admin_reject_"))
async def cb_admin_reject(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Ruxsat yo'q!")
        return
    _, _, user_id_s, req_id_s = call.data.split("_", 3)
    user_id = int(user_id_s)
    req_id  = int(req_id_s)

    conn = get_conn()
    conn.execute("UPDATE payment_requests SET status='rejected' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

    try:
        user = get_user(user_id)
        lang = user.get("lang","uz") if user else "uz"
        labels = {
            "uz": "❌ Afsuski, to'lovingiz tasdiqlanmadi. Muammo bo'lsa admin bilan bog'laning.",
            "ru": "❌ Оплата не подтверждена.",
            "en": "❌ Payment not confirmed.",
        }
        await bot.send_message(user_id, labels.get(lang, labels["uz"]))
    except Exception as e:
        logging.error(f"Reject notify error: {e}")

    await call.message.edit_caption(call.message.caption + "\n\n❌ RAD ETILDI")
    await call.answer("❌ Rad etildi")

# ── 15. WATER callbacks ───────────────────────────────────────────────────────
@dp.callback_query(F.data == "water_drank")
async def cb_water_drank(call: types.CallbackQuery):
    tid  = call.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"
    conn = get_conn()
    conn.execute("INSERT INTO water_logs (telegram_id) VALUES (?)", (tid,))
    conn.commit()
    conn.close()
    labels = {"uz": "💧 250 ml suv qo'shildi!", "ru": "💧 250 мл добавлено!", "en": "💧 250 ml added!"}
    await call.answer(labels.get(lang, labels["uz"]))

@dp.callback_query(F.data == "water_today")
async def cb_water_today(call: types.CallbackQuery):
    tid  = call.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    conn  = get_conn()
    rows  = conn.execute(
        "SELECT COUNT(*) as cnt FROM water_logs WHERE telegram_id=? AND date(logged_at)=?",
        (tid, today)
    ).fetchone()
    conn.close()
    total_ml = rows["cnt"] * 250
    labels = {
        "uz": f"💧 Bugun ichgan suvingiz: {total_ml} ml ({rows['cnt']} stakan)",
        "ru": f"💧 Сегодня выпито: {total_ml} мл ({rows['cnt']} стаканов)",
        "en": f"💧 Today you drank: {total_ml} ml ({rows['cnt']} glasses)",
    }
    await call.answer(labels.get(lang, labels["uz"]), show_alert=True)

# ── 16. FOOD LOG callbacks (eat / cancel) ────────────────────────────────────
@dp.callback_query(F.data.startswith("eat_"))
async def cb_eat(call: types.CallbackQuery):
    pend_id = int(call.data.split("_")[1])
    entry   = pending_food.pop(pend_id, None)
    if not entry:
        await call.answer("Vaqt o'tdi yoki allaqachon qo'shilgan!")
        return
    tid  = entry["tid"]
    lang = entry.get("lang","uz")
    conn = get_conn()
    conn.execute(
        "INSERT INTO food_logs (telegram_id, food_name, calories, protein, fat, carbs, meal_type) VALUES (?,?,?,?,?,?,?)",
        (tid, entry["food"], entry["cal"], entry["protein"], entry["fat"], entry["carbs"], entry["meal_type"])
    )
    conn.commit()
    conn.close()
    labels = {
        "uz": f"✅ {entry['food']} — {entry['cal']:.0f} kkal qo'shildi!",
        "ru": f"✅ {entry['food']} — {entry['cal']:.0f} ккал добавлено!",
        "en": f"✅ {entry['food']} — {entry['cal']:.0f} kcal added!",
    }
    await call.answer(labels.get(lang, labels["uz"]))
    try:
        await call.message.delete()
    except Exception:
        pass

@dp.callback_query(F.data.startswith("cancel_food_"))
async def cb_cancel_food(call: types.CallbackQuery):
    pend_id = int(call.data.split("_")[2])
    pending_food.pop(pend_id, None)
    lang = call.from_user.language_code or "uz"
    labels = {"uz": "❌ Bekor qilindi", "ru": "❌ Отменено", "en": "❌ Cancelled"}
    await call.answer(labels.get(lang, labels["uz"]))
    try:
        await call.message.delete()
    except Exception:
        pass

# ── 17. PROFILE callbacks ─────────────────────────────────────────────────────
@dp.callback_query(F.data == "prof_info")
async def cb_prof_info(call: types.CallbackQuery):
    tid  = call.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"
    if not user:
        await call.answer("Avval ro'yxatdan o'ting!")
        return
    w = user.get("weight","?"); h = user.get("height","?"); a = user.get("age","?")
    g = user.get("gender","?"); tgt = user.get("target","?"); act = user.get("activity","?")
    cal = user.get("calories_goal","?")
    labels = {
        "uz": (f"👤 Profil ma'lumotlari:\n\n"
               f"📏 Bo'y: {h} sm\n⚖️ Vazn: {w} kg\n🎂 Yosh: {a}\n"
               f"🧬 Jins: {g}\n🎯 Maqsad: {tgt}\n🏃 Faollik: {act}\n"
               f"🔥 Kunlik kaloriya: {cal} kkal"),
        "ru": (f"👤 Данные профиля:\n\n"
               f"📏 Рост: {h} см\n⚖️ Вес: {w} кг\n🎂 Возраст: {a}\n"
               f"🧬 Пол: {g}\n🎯 Цель: {tgt}\n🏃 Активность: {act}\n"
               f"🔥 Калорий в день: {cal} ккал"),
        "en": (f"👤 Profile info:\n\n"
               f"📏 Height: {h} cm\n⚖️ Weight: {w} kg\n🎂 Age: {a}\n"
               f"🧬 Gender: {g}\n🎯 Goal: {tgt}\n🏃 Activity: {act}\n"
               f"🔥 Daily calories: {cal} kcal"),
    }
    await call.message.edit_text(labels.get(lang, labels["uz"]), reply_markup=profile_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "prof_sub")
async def cb_prof_sub(call: types.CallbackQuery):
    tid  = call.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"
    if is_vip(user):
        vip_end = user.get("vip_end","?")
        labels = {
            "uz": f"⭐ Siz VIP obunachisiz!\nMuddati: {vip_end[:10] if vip_end != '?' else '?'}",
            "ru": f"⭐ У вас VIP подписка!\nДо: {vip_end[:10] if vip_end != '?' else '?'}",
            "en": f"⭐ You have VIP!\nUntil: {vip_end[:10] if vip_end != '?' else '?'}",
        }
    elif is_vip_or_trial(user):
        days = get_trial_remaining(user)
        labels = {
            "uz": f"🎁 Bepul sinov: {days} kun qoldi",
            "ru": f"🎁 Пробный период: осталось {days} дн.",
            "en": f"🎁 Free trial: {days} days left",
        }
    else:
        labels = {
            "uz": "❌ Obuna yo'q. VIP sotib oling!",
            "ru": "❌ Нет подписки. Купите VIP!",
            "en": "❌ No subscription. Buy VIP!",
        }
    await call.message.edit_text(labels.get(lang, labels["uz"]), reply_markup=profile_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "prof_edit")
async def cb_prof_edit(call: types.CallbackQuery):
    tid  = call.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"
    labels = {
        "uz": "✏️ Nima o'zgartirmoqchisiz?",
        "ru": "✏️ Что хотите изменить?",
        "en": "✏️ What would you like to change?",
    }
    await call.message.edit_text(labels.get(lang, labels["uz"]), reply_markup=edit_profile_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "prof_back")
async def cb_prof_back(call: types.CallbackQuery):
    tid  = call.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"
    await call.message.delete()
    await call.answer()

@dp.callback_query(F.data.startswith("edit_"))
async def cb_edit_field(call: types.CallbackQuery, state: FSMContext):
    field = call.data.replace("edit_", "")
    tid   = call.from_user.id
    user  = get_user(tid)
    lang  = user.get("lang","uz") if user else "uz"
    await state.update_data(field=field)
    await state.set_state(EditProfile.value)
    prompts = {
        "uz": {"height": "📏 Yangi bo'yingizni kiriting (sm):", "weight": "⚖️ Yangi vazningizni kiriting (kg):",
               "age": "🎂 Yangi yoshingizni kiriting:", "target": "🎯 Yangi maqsadingiz:", "activity": "🏃 Yangi faollik (low/medium/high):"},
        "ru": {"height": "📏 Введите новый рост (см):", "weight": "⚖️ Введите новый вес (кг):",
               "age": "🎂 Введите новый возраст:", "target": "🎯 Новая цель:", "activity": "🏃 Новая активность (low/medium/high):"},
        "en": {"height": "📏 Enter new height (cm):", "weight": "⚖️ Enter new weight (kg):",
               "age": "🎂 Enter new age:", "target": "🎯 New goal:", "activity": "🏃 New activity (low/medium/high):"},
    }
    prompt = prompts.get(lang, prompts["uz"]).get(field, "Yangi qiymat:")
    await call.message.edit_text(prompt)
    await call.answer()

# ── 18. AI CHAT FSM handlers ──────────────────────────────────────────────────
@dp.message(StateFilter(AIChat.chatting), F.photo)
async def ai_chat_photo(message: types.Message, state: FSMContext):
    """If user sends a photo while in AI chat — treat it as food analysis."""
    await _analyze_food_photo(message)

@dp.message(StateFilter(AIChat.chatting))
async def ai_chat_message(message: types.Message, state: FSMContext):
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"

    if not is_vip_or_trial(user):
        await state.clear()
        await message.answer(t(lang, "trial_expired"), reply_markup=main_menu_kb(lang))
        return

    wait = await message.answer("🤔 ...")
    try:
        user_text = message.text or ""
        system_prompt = (
            f"Sen professional diyetolog va sog'lom ovqatlanish bo'yicha maslahatchisan. "
            f"Foydalanuvchi ma'lumotlari: yosh={user.get('age')}, bo'y={user.get('height')} sm, "
            f"vazn={user.get('weight')} kg, maqsad={user.get('target')}, "
            f"kunlik kaloriya={user.get('calories_goal')} kkal. "
            f"Faqat {lang} tilida javob ber. Qisqa va aniq bo'l."
        )
        response = await asyncio.to_thread(
            gemini.models.generate_content,
            model="gemini-1.5-flash",
            contents=[
                genai_types.Content(parts=[genai_types.Part(text=system_prompt + "\n\nFoydalanuvchi: " + user_text)])
            ]
        )
        await wait.delete()
        await message.answer(response.text.strip())
    except Exception as e:
        logging.error(f"AI chat error: {e}")
        try:
            await wait.delete()
        except Exception:
            pass
        labels = {"uz": "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.", "ru": "❌ Ошибка. Попробуйте позже.", "en": "❌ Error. Try again later."}
        await message.answer(labels.get(lang, labels["uz"]))

# ── 19. MAIN MENU BUTTONS (only outside FSM states) ──────────────────────────
@dp.message(F.text)
async def main_menu_handler(message: types.Message, state: FSMContext):
    """Catch-all for menu buttons. Only fires when no FSM state is active."""
    tid  = message.from_user.id
    user = get_user(tid)

    # If user not registered — redirect to /start
    if not user:
        await message.answer("Salom! Avval /start buyrug'ini yuboring.")
        return

    lang = user.get("lang","uz")
    txt  = message.text

    # ── Daily Ration
    if txt == t(lang, "btn_ration"):
        if not is_vip_or_trial(user):
            await message.answer(t(lang, "paywall"), reply_markup=vip_plans_kb())
            return
        cal = user.get("calories_goal", 2000)
        prompt = (
            f"Foydalanuvchi: yosh={user.get('age')}, bo'y={user.get('height')} sm, "
            f"vazn={user.get('weight')} kg, maqsad={user.get('target')}, "
            f"kaloriya maqsadi={cal} kkal/kun. "
            f"Bugungi {lang} tilida kunlik ratsion tuzib ber: nonushta, tushlik, kechki ovqat."
        )
        wait = await message.answer("⏳ Ratsion tayyorlanmoqda...")
        try:
            resp = await asyncio.to_thread(
                gemini.models.generate_content,
                model="gemini-1.5-flash",
                contents=[genai_types.Content(parts=[genai_types.Part(text=prompt)])]
            )
            await wait.delete()
            await message.answer(resp.text.strip())
        except Exception as e:
            logging.error(f"Ration error: {e}")
            await wait.delete()
            await message.answer("❌ Xatolik. Keyinroq urinib ko'ring.")

    # ── Water ration
    elif txt == t(lang, "btn_water"):
        if not is_vip_or_trial(user):
            await message.answer(t(lang, "paywall"), reply_markup=vip_plans_kb())
            return
        w = user.get("weight", 70)
        rec_ml = int(float(w) * 35)
        labels = {
            "uz": f"💧 Kunlik suv tavsiyasi: {rec_ml} ml (vazningiz {w} kg asosida)",
            "ru": f"💧 Рекомендация по воде: {rec_ml} мл (вес {w} кг)",
            "en": f"💧 Daily water recommendation: {rec_ml} ml (weight {w} kg)",
        }
        await message.answer(labels.get(lang, labels["uz"]), reply_markup=water_kb(lang))

    # ── Today's food log
    elif txt == t(lang, "btn_food_today"):
        if not is_vip_or_trial(user):
            await message.answer(t(lang, "paywall"), reply_markup=vip_plans_kb())
            return
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        conn  = get_conn()
        rows  = conn.execute(
            "SELECT food_name, calories, meal_type FROM food_logs WHERE telegram_id=? AND date(logged_at)=? ORDER BY logged_at",
            (tid, today)
        ).fetchall()
        total = conn.execute(
            "SELECT COALESCE(SUM(calories),0) as s FROM food_logs WHERE telegram_id=? AND date(logged_at)=?",
            (tid, today)
        ).fetchone()["s"]
        conn.close()
        if not rows:
            labels = {"uz": "📋 Bugun hali ovqat qo'shilmagan.", "ru": "📋 Сегодня ничего не добавлено.", "en": "📋 No food logged today."}
            await message.answer(labels.get(lang, labels["uz"]))
            return
        lines = []
        for r in rows:
            lines.append(f"{meal_label(r['meal_type'], lang)}: {r['food_name']} — {r['calories']:.0f} kkal")
        goal = user.get("calories_goal", 2000)
        headers = {"uz": f"📋 Bugungi ovqatlar:\n\n", "ru": "📋 Еда за сегодня:\n\n", "en": "📋 Today's food:\n\n"}
        footers = {
            "uz": f"\n\n🔥 Jami: {total:.0f} / {goal} kkal",
            "ru": f"\n\n🔥 Итого: {total:.0f} / {goal} ккал",
            "en": f"\n\n🔥 Total: {total:.0f} / {goal} kcal",
        }
        await message.answer(headers.get(lang,"") + "\n".join(lines) + footers.get(lang,""))

    # ── Weekly report
    elif txt == t(lang, "btn_food_week"):
        if not is_vip_or_trial(user):
            await message.answer(t(lang, "paywall"), reply_markup=vip_plans_kb())
            return
        week_ago = (datetime.now(TZ) - timedelta(days=7)).strftime("%Y-%m-%d")
        conn = get_conn()
        rows = conn.execute(
            "SELECT date(logged_at) as d, COALESCE(SUM(calories),0) as s FROM food_logs WHERE telegram_id=? AND date(logged_at)>=? GROUP BY d ORDER BY d",
            (tid, week_ago)
        ).fetchall()
        conn.close()
        if not rows:
            labels = {"uz": "📅 So'nggi 7 kunda ma'lumot yo'q.", "ru": "📅 Нет данных за 7 дней.", "en": "📅 No data for last 7 days."}
            await message.answer(labels.get(lang, labels["uz"]))
            return
        lines = [f"{r['d']}: {r['s']:.0f} kkal" for r in rows]
        headers = {"uz": "📅 Haftalik hisobot:\n\n", "ru": "📅 Недельный отчёт:\n\n", "en": "📅 Weekly report:\n\n"}
        await message.answer(headers.get(lang,"") + "\n".join(lines))

    # ── Monthly report
    elif txt == t(lang, "btn_food_month"):
        if not is_vip_or_trial(user):
            await message.answer(t(lang, "paywall"), reply_markup=vip_plans_kb())
            return
        month_ago = (datetime.now(TZ) - timedelta(days=30)).strftime("%Y-%m-%d")
        conn = get_conn()
        rows = conn.execute(
            "SELECT date(logged_at) as d, COALESCE(SUM(calories),0) as s FROM food_logs WHERE telegram_id=? AND date(logged_at)>=? GROUP BY d ORDER BY d",
            (tid, month_ago)
        ).fetchall()
        conn.close()
        if not rows:
            labels = {"uz": "📆 So'nggi 30 kunda ma'lumot yo'q.", "ru": "📆 Нет данных за 30 дней.", "en": "📆 No data for last 30 days."}
            await message.answer(labels.get(lang, labels["uz"]))
            return
        lines = [f"{r['d']}: {r['s']:.0f} kkal" for r in rows]
        total_avg = sum(r['s'] for r in rows) / len(rows)
        headers = {"uz": "📆 Oylik hisobot:\n\n", "ru": "📆 Месячный отчёт:\n\n", "en": "📆 Monthly report:\n\n"}
        footers = {"uz": f"\n\n📊 O'rtacha: {total_avg:.0f} kkal/kun", "ru": f"\n\n📊 Среднее: {total_avg:.0f} ккал/день", "en": f"\n\n📊 Average: {total_avg:.0f} kcal/day"}
        await message.answer(headers.get(lang,"") + "\n".join(lines) + footers.get(lang,""))

    # ── AI Dietologist
    elif txt == t(lang, "btn_ai"):
        if not is_vip_or_trial(user):
            await message.answer(t(lang, "paywall"), reply_markup=vip_plans_kb())
            return
        await state.set_state(AIChat.chatting)
        labels = {
            "uz": "🤖 AI Diyetolog bilan suhbat boshlandi! /menu buyrug'i bilan chiqishingiz mumkin.",
            "ru": "🤖 Чат с AI-диетологом начат! /menu для выхода.",
            "en": "🤖 AI Dietologist chat started! /menu to exit.",
        }
        await message.answer(labels.get(lang, labels["uz"]))

    # ── Profile
    elif txt == t(lang, "btn_profile"):
        labels = {
            "uz": "👤 Profilingiz:",
            "ru": "👤 Ваш профиль:",
            "en": "👤 Your profile:",
        }
        await message.answer(labels.get(lang, labels["uz"]), reply_markup=profile_kb(lang))

    # ── Buy VIP
    elif txt == t(lang, "btn_vip"):
        await _show_vip_plans(message, lang, state)

    # ── Food photo button
    elif txt == t(lang, "btn_photo_food"):
        if not is_vip_or_trial(user):
            await message.answer(t(lang, "paywall"), reply_markup=vip_plans_kb())
            return
        labels = {
            "uz": "📸 Ovqatingizning rasmini yuboring, men tahlil qilaman!",
            "ru": "📸 Пришлите фото еды, я проанализирую!",
            "en": "📸 Send a photo of your food and I'll analyze it!",
        }
        await message.answer(labels.get(lang, labels["uz"]))

    else:
        # Unknown text — show main menu
        await message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))

# ── 20. FOOD PHOTO (default state — outside any FSM) ─────────────────────────
@dp.message(F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    tid  = message.from_user.id
    user = get_user(tid)
    if not user:
        await message.answer("Avval /start buyrug'ini yuboring.")
        return
    if not is_vip_or_trial(user):
        lang = user.get("lang","uz")
        await message.answer(t(lang, "paywall"), reply_markup=vip_plans_kb())
        return
    await _analyze_food_photo(message)

# ── 21. VIP helper (shared) ──────────────────────────────────────────────────
async def _show_vip_plans(message, lang, state):
    """Show VIP plan selection inline keyboard."""
    labels = {
        "uz": ("⭐ VIP Obuna\n\n"
               "📅 Oylik — 20,000 so'm\n"
               "📆 Yillik — 220,000 so'm (2 oy tekin!)\n\n"
               "Tarif tanlang:"),
        "ru": ("⭐ VIP Подписка\n\n"
               "📅 Месячная — 20,000 сум\n"
               "📆 Годовая — 220,000 сум (2 мес. бесплатно!)\n\n"
               "Выберите тариф:"),
        "en": ("⭐ VIP Subscription\n\n"
               "📅 Monthly — 20,000 UZS\n"
               "📆 Yearly — 220,000 UZS (2 months free!)\n\n"
               "Choose a plan:"),
    }
    await message.answer(labels.get(lang, labels["uz"]), reply_markup=vip_plans_kb())

# ── 22. ADMIN BROADCAST ───────────────────────────────────────────────────────
@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(BroadcastState.message)
    await message.answer("📢 Xabar matnini yuboring (barcha foydalanuvchilarga yuboriladi):")

@dp.message(StateFilter(BroadcastState.message))
async def broadcast_message(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    conn = get_conn()
    users = conn.execute("SELECT telegram_id FROM users").fetchall()
    conn.close()
    sent = failed = 0
    for u in users:
        try:
            await bot.send_message(u["telegram_id"], message.text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await message.answer(f"📢 Yuborildi: {sent}, muvaffaqiyatsiz: {failed}")

# ── 23. ADMIN STATS ───────────────────────────────────────────────────────────
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = get_conn()
    total   = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    vip_cnt = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_vip=1").fetchone()["c"]
    trial_cnt = conn.execute(
        "SELECT COUNT(*) as c FROM users WHERE trial_start IS NOT NULL AND is_vip=0"
    ).fetchone()["c"]
    pending = conn.execute(
        "SELECT COUNT(*) as c FROM payment_requests WHERE status='pending'"
    ).fetchone()["c"]
    conn.close()
    await message.answer(
        f"📊 Bot statistikasi:\n\n"
        f"👥 Jami foydalanuvchilar: {total}\n"
        f"⭐ VIP: {vip_cnt}\n"
        f"🎁 Trial: {trial_cnt}\n"
        f"💳 Kutilayotgan to'lovlar: {pending}"
    )

# ── 24. STARTUP & MAIN ────────────────────────────────────────────────────────
async def main():
    init_db()
    logging.info("Bot starting...")
    await dp.start_polling(bot, allowed_updates=["message","callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
