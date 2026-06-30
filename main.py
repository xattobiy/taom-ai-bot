# -*- coding: utf-8 -*-
import asyncio
import logging
import os
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

# ââ CONFIG ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
BOT_TOKEN   = os.environ.get("BOT_TOKEN",   "8163772583:AAFY4g1M8OS4luohuvrMYpqJ6fa32ue8zvc")
ADMIN_ID    = int(os.environ.get("ADMIN_ID",  "956947665"))
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY","AQ.Ab8RN6J_yF03nQqGXE4vivuqZQxW0uOknWRw0cseErYLij5DLw")
DB_PATH     = "taom_ai.db"
TRIAL_DAYS  = 3
CARD_NUMBER = "9860040114589092"
TZ          = pytz.timezone("Asia/Tashkent")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
gemini = genai.Client(api_key=GEMINI_KEY)

# ââ TRANSLATIONS ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
LANGS = {
    "uz": {
        "welcome": "Assalomu alaykum! Men sizning diyeta yordamchingizman ð¥\nTanishishni boshlasak, yoshingizdan boshlaymiz. Yoshingiz nechida?",
        "ask_height": "Bo'yingiz qancha? (masalan: 170 sm) ð",
        "ask_weight": "Vazningiz qancha? (masalan: 60 kg) âï¸",
        "ask_goal": "Maqsadingizni tanlang:",
        "ask_gender": "Jinsingizni tanlang:",
        "goal_lose": "Ozish ð¥",
        "goal_gain": "Vazn qo'shish ðª",
        "goal_keep": "Vaznni ushlab qolish âï¸",
        "gender_male": "Erkak ð§",
        "gender_female": "Ayol ð©",
        "ask_activity": "Kunlik faollik darajangizni tanlang: ð",
        "activity_low": "ð¶ Kam faol (kam harakatlanaman)",
        "activity_medium": "ð´ O'rta faol (ba'zan sport qilaman)",
        "activity_high": "ðï¸ Juda faol (muntazam sport)",
        "reg_done": "ð Ro'yxatdan o'tganingiz bilan tabriklayman!\n\nBu botda siz o'z vazningizni oson nazorat qila olasiz ð\n\nSovg'a sifatida sizga 3 kunlik FREE TRIAL taqdim qilamiz ð\n\nTanishtiruv tugadi â endi botdagi imkoniyatlarga o'tamiz!",
        "main_menu": "Asosiy menyu ð ",
        "btn_ration": "ð½ Kunlik ratsion",
        "btn_food_today": "ð Bugungi ovqatlar",
        "btn_food_week": "ð Haftalik hisobot",
        "btn_food_month": "ð Oylik hisobot",
        "btn_water": "ð§ Suv ratsioni",
        "btn_ai": "ð¤ AI Diyetolog",
        "btn_profile": "ð¤ Profilim",
        "btn_vip": "â­ VIP sotib olish",
        "btn_check": "ð§¾ Chek yuborish",
        "btn_photo_food": "📸 Ovqat rasmi",
        "vip_only": "Bu imkoniyat faqat VIP tarifda mavjud! â­\n\nVIP sotib olish uchun /vip buyrug'ini yuboring.",
        "trial_expired": "Bepul sinov muddati tugadi! â°\n\nBarcha imkoniyatlardan foydalanish uchun VIP obuna oling.",
        "lang_select": "Tilni tanlang / Choose language / ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ·ÑÐº:",
    },
    "ru": {
        "welcome": "ÐÑÑÐ°Ð»Ð¾Ð¼Ñ Ð°Ð»ÐµÐ¹ÐºÑÐ¼! Ð¯ Ð²Ð°Ñ Ð´Ð¸ÐµÑÐ¸ÑÐµÑÐºÐ¸Ð¹ Ð¿Ð¾Ð¼Ð¾ÑÐ½Ð¸Ðº ð¥\nÐÐ°Ð²Ð°Ð¹ÑÐµ Ð¿Ð¾Ð·Ð½Ð°ÐºÐ¾Ð¼Ð¸Ð¼ÑÑ. Ð¡ÐºÐ¾Ð»ÑÐºÐ¾ Ð²Ð°Ð¼ Ð»ÐµÑ?",
        "ask_height": "ÐÐ°ÐºÐ¾Ð¹ Ñ Ð²Ð°Ñ ÑÐ¾ÑÑ? (Ð½Ð°Ð¿ÑÐ¸Ð¼ÐµÑ: 170 ÑÐ¼) ð",
        "ask_weight": "ÐÐ°ÐºÐ¾Ð¹ Ñ Ð²Ð°Ñ Ð²ÐµÑ? (Ð½Ð°Ð¿ÑÐ¸Ð¼ÐµÑ: 60 ÐºÐ³) âï¸",
        "ask_goal": "ÐÑÐ±ÐµÑÐ¸ÑÐµ Ð²Ð°ÑÑ ÑÐµÐ»Ñ:",
        "ask_gender": "ÐÑÐ±ÐµÑÐ¸ÑÐµ Ð²Ð°Ñ Ð¿Ð¾Ð»:",
        "goal_lose": "ÐÐ¾ÑÑÐ´ÐµÑÑ ð¥",
        "goal_gain": "ÐÐ°Ð±ÑÐ°ÑÑ Ð²ÐµÑ ðª",
        "goal_keep": "ÐÐ¾Ð´Ð´ÐµÑÐ¶Ð°ÑÑ Ð²ÐµÑ âï¸",
        "gender_male": "ÐÑÐ¶ÑÐ¸Ð½Ð° ð§",
        "gender_female": "ÐÐµÐ½ÑÐ¸Ð½Ð° ð©",
        "ask_activity": "ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÑÐ¾Ð²ÐµÐ½Ñ Ð°ÐºÑÐ¸Ð²Ð½Ð¾ÑÑÐ¸: ð",
        "activity_low": "ð¶ ÐÐ°Ð»Ð¾Ð°ÐºÑÐ¸Ð²Ð½ÑÐ¹ (Ð¼Ð°Ð»Ð¾ Ð´Ð²Ð¸Ð¶ÐµÐ½Ð¸Ñ)",
        "activity_medium": "ð´ Ð£Ð¼ÐµÑÐµÐ½Ð½Ð¾ Ð°ÐºÑÐ¸Ð²Ð½ÑÐ¹ (Ð¸Ð½Ð¾Ð³Ð´Ð° ÑÐ¿Ð¾ÑÑ)",
        "activity_high": "ðï¸ ÐÑÐµÐ½Ñ Ð°ÐºÑÐ¸Ð²Ð½ÑÐ¹ (ÑÐµÐ³ÑÐ»ÑÑÐ½ÑÐ¹ ÑÐ¿Ð¾ÑÑ)",
        "reg_done": "ð ÐÐ¾Ð·Ð´ÑÐ°Ð²Ð»ÑÑ Ñ ÑÐµÐ³Ð¸ÑÑÑÐ°ÑÐ¸ÐµÐ¹!\n\nÐ ÑÑÐ¾Ð¼ Ð±Ð¾ÑÐµ Ð²Ñ Ð»ÐµÐ³ÐºÐ¾ Ð¼Ð¾Ð¶ÐµÑÐµ ÐºÐ¾Ð½ÑÑÐ¾Ð»Ð¸ÑÐ¾Ð²Ð°ÑÑ ÑÐ²Ð¾Ð¹ Ð²ÐµÑ ð\n\nÐ Ð¿Ð¾Ð´Ð°ÑÐ¾Ðº Ð¿ÑÐµÐ´Ð¾ÑÑÐ°Ð²Ð»ÑÐµÐ¼ 3-Ð´Ð½ÐµÐ²Ð½ÑÐ¹ FREE TRIAL ð\n\nÐÐ½Ð°ÐºÐ¾Ð¼ÑÑÐ²Ð¾ Ð·Ð°Ð²ÐµÑÑÐµÐ½Ð¾ â Ð¿ÐµÑÐµÑÐ¾Ð´Ð¸Ð¼ Ðº Ð²Ð¾Ð·Ð¼Ð¾Ð¶Ð½Ð¾ÑÑÑÐ¼ Ð±Ð¾ÑÐ°!",
        "main_menu": "ÐÐ»Ð°Ð²Ð½Ð¾Ðµ Ð¼ÐµÐ½Ñ ð ",
        "btn_ration": "ð½ ÐÐ½ÐµÐ²Ð½Ð¾Ð¹ ÑÐ°ÑÐ¸Ð¾Ð½",
        "btn_food_today": "ð ÐÐ´Ð° Ð·Ð° ÑÐµÐ³Ð¾Ð´Ð½Ñ",
        "btn_food_week": "ð ÐÐµÐ´ÐµÐ»ÑÐ½ÑÐ¹ Ð¾ÑÑÑÑ",
        "btn_food_month": "ð ÐÐµÑÑÑÐ½ÑÐ¹ Ð¾ÑÑÑÑ",
        "btn_water": "ð§ ÐÐ¾Ð´Ð½ÑÐ¹ ÑÐ°ÑÐ¸Ð¾Ð½",
        "btn_ai": "ð¤ AI ÐÐ¸ÐµÑÐ¾Ð»Ð¾Ð³",
        "btn_profile": "ð¤ ÐÐ¾Ð¹ Ð¿ÑÐ¾ÑÐ¸Ð»Ñ",
        "btn_vip": "â­ ÐÑÐ¿Ð¸ÑÑ VIP",
        "btn_check": "ð§¾ ÐÑÐ¿ÑÐ°Ð²Ð¸ÑÑ ÑÐµÐº",
        "btn_photo_food": "📸 Фото еды",
        "vip_only": "Ð­ÑÐ° ÑÑÐ½ÐºÑÐ¸Ñ Ð´Ð¾ÑÑÑÐ¿Ð½Ð° ÑÐ¾Ð»ÑÐºÐ¾ Ð² VIP ÑÐ°ÑÐ¸ÑÐµ! â­\n\nÐÐ»Ñ Ð¿Ð¾ÐºÑÐ¿ÐºÐ¸ VIP Ð¾ÑÐ¿ÑÐ°Ð²ÑÑÐµ /vip.",
        "trial_expired": "ÐÐµÑÐ¿Ð»Ð°ÑÐ½ÑÐ¹ Ð¿ÑÐ¾Ð±Ð½ÑÐ¹ Ð¿ÐµÑÐ¸Ð¾Ð´ Ð·Ð°ÐºÐ¾Ð½ÑÐ¸Ð»ÑÑ! â°\n\nÐÑÐ¿Ð¸ÑÐµ VIP Ð¿Ð¾Ð´Ð¿Ð¸ÑÐºÑ Ð´Ð»Ñ Ð´Ð¾ÑÑÑÐ¿Ð° ÐºÐ¾ Ð²ÑÐµÐ¼ ÑÑÐ½ÐºÑÐ¸ÑÐ¼.",
        "lang_select": "Tilni tanlang / Choose language / ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ·ÑÐº:",
    },
    "en": {
        "welcome": "Hello! I am your diet assistant ð¥\nLet's get acquainted. How old are you?",
        "ask_height": "What is your height? (e.g. 170 cm) ð",
        "ask_weight": "What is your weight? (e.g. 60 kg) âï¸",
        "ask_goal": "Choose your goal:",
        "ask_gender": "Choose your gender:",
        "goal_lose": "Lose weight ð¥",
        "goal_gain": "Gain weight ðª",
        "goal_keep": "Maintain weight âï¸",
        "gender_male": "Male ð§",
        "gender_female": "Female ð©",
        "ask_activity": "Select your activity level: ð",
        "activity_low": "ð¶ Low active (little movement)",
        "activity_medium": "ð´ Moderately active (some exercise)",
        "activity_high": "ðï¸ Very active (regular exercise)",
        "reg_done": "ð Congratulations on registering!\n\nIn this bot you can easily track your weight ð\n\nAs a gift we give you a 3-day FREE TRIAL ð\n\nIntro done â let's move to bot features!",
        "main_menu": "Main menu ð ",
        "btn_ration": "ð½ Daily Ration",
        "btn_food_today": "ð Today's food",
        "btn_food_week": "ð Weekly report",
        "btn_food_month": "ð Monthly report",
        "btn_water": "ð§ Water ration",
        "btn_ai": "ð¤ AI Dietologist",
        "btn_profile": "ð¤ My profile",
        "btn_vip": "â­ Buy VIP",
        "btn_check": "ð§¾ Send receipt",
        "btn_photo_food": "📸 Food photo",
        "vip_only": "This feature is only available in VIP! â­\n\nSend /vip to purchase.",
        "trial_expired": "Free trial expired! â°\n\nBuy VIP subscription to access all features.",
        "lang_select": "Tilni tanlang / Choose language / ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ·ÑÐº:",
    }
}

def t(user_lang, key, **kwargs):
    lang = user_lang if user_lang in LANGS else "uz"
    text = LANGS[lang].get(key, LANGS["uz"].get(key, key))
    return text.format(**kwargs) if kwargs else text


# ââ DATABASE ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            lang TEXT DEFAULT 'uz',
            age INTEGER,
            gender TEXT,
            activity TEXT DEFAULT 'medium',
            height REAL,
            weight REAL,
            target TEXT,
            calories_goal REAL,
            trial_start TEXT,
            is_vip INTEGER DEFAULT 0,
            vip_start TEXT,
            vip_end TEXT
        );
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            food_name TEXT,
            calories REAL,
            protein REAL DEFAULT 0,
            fat REAL DEFAULT 0,
            carbs REAL DEFAULT 0,
            meal_type TEXT,
            logged_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        -- Add columns if they don't exist (for existing databases)
        CREATE TABLE IF NOT EXISTS food_logs_migration_done (id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            amount_ml INTEGER DEFAULT 250,
            logged_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payment_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            photo_file_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    # Migration: add BJU columns if missing (for existing databases)
    try:
        conn.execute("ALTER TABLE food_logs ADD COLUMN protein REAL DEFAULT 0")
        conn.commit()
    except: pass
    try:
        conn.execute("ALTER TABLE food_logs ADD COLUMN fat REAL DEFAULT 0")
        conn.commit()
    except: pass
    try:
        conn.execute("ALTER TABLE food_logs ADD COLUMN carbs REAL DEFAULT 0")
        conn.commit()
    except: pass
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
        w = float(user.get("weight", 70))
        h = float(user.get("height", 170))
        a = int(user.get("age", 30))
        g = user.get("gender", "erkak")
        target = user.get("target", "keep")
        activity = user.get("activity", "medium")

        if "male" in g.lower() or "erkak" in g.lower() or "Ð¼ÑÐ¶ÑÐ¸Ð½Ð°" in g.lower():
            bmr = 10 * w + 6.25 * h - 5 * a + 5
        else:
            bmr = 10 * w + 6.25 * h - 5 * a - 161

        # Activity multiplier (Harris-Benedict)
        act_map = {"low": 1.2, "medium": 1.55, "high": 1.725}
        tdee = bmr * act_map.get(activity, 1.55)

        if "lose" in target or "ozish" in target or "Ð¿Ð¾ÑÑÐ´" in target.lower():
            return round(tdee - 500)
        elif "gain" in target or "qoshish" in target or "Ð½Ð°Ð±ÑÐ°ÑÑ" in target.lower():
            return round(tdee + 500)
        else:
            return round(tdee)
    except:
        return 2000

def get_meal_type():
    now = datetime.now(TZ).hour
    if 6 <= now < 11:
        return "nonushta"
    elif 11 <= now < 16:
        return "tushlik"
    elif 16 <= now < 21:
        return "kechki"
    else:
        return "kechasi"

def meal_label(mt, lang="uz"):
    mapping = {
        "uz": {"nonushta": "ð Nonushta", "tushlik": "âï¸ Tushlik", "kechki": "ð Kechki ovqat", "kechasi": "ð Kechasi"},
        "ru": {"nonushta": "ð ÐÐ°Ð²ÑÑÐ°Ðº", "tushlik": "âï¸ ÐÐ±ÐµÐ´", "kechki": "ð Ð£Ð¶Ð¸Ð½", "kechasi": "ð ÐÐ¾ÑÑ"},
        "en": {"nonushta": "ð Breakfast", "tushlik": "âï¸ Lunch", "kechki": "ð Dinner", "kechasi": "ð Night"},
    }
    return mapping.get(lang, mapping["uz"]).get(mt, mt)



# ââ FSM STATES ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
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

class PaymentState(StatesGroup):
    waiting_receipt = State()

class AIChat(StatesGroup):
    chatting = State()

class BroadcastState(StatesGroup):
    message = State()

# ââ KEYBOARDS âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ðºð¿ O'zbek", callback_data="lang_uz"),
         InlineKeyboardButton(text="ð·ðº Ð ÑÑÑÐºÐ¸Ð¹", callback_data="lang_ru"),
         InlineKeyboardButton(text="ð¬ð§ English", callback_data="lang_en")]
    ])

def goal_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang,"goal_lose"))],
                  [KeyboardButton(text=t(lang,"goal_gain"))],
                  [KeyboardButton(text=t(lang,"goal_keep"))]],
        resize_keyboard=True, one_time_keyboard=True
    )

def gender_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang,"gender_male")),
                   KeyboardButton(text=t(lang,"gender_female"))]],
        resize_keyboard=True, one_time_keyboard=True
    )

def activity_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang,"activity_low"))],
            [KeyboardButton(text=t(lang,"activity_medium"))],
            [KeyboardButton(text=t(lang,"activity_high"))],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def main_menu_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang,"btn_ration")),  KeyboardButton(text=t(lang,"btn_water"))],
            [KeyboardButton(text=t(lang,"btn_food_today")), KeyboardButton(text=t(lang,"btn_food_week"))],
            [KeyboardButton(text=t(lang,"btn_food_month")), KeyboardButton(text=t(lang,"btn_ai"))],
            [KeyboardButton(text=t(lang,"btn_profile")), KeyboardButton(text=t(lang,"btn_vip"))],
            [KeyboardButton(text=t(lang,"btn_photo_food"))],
        ],
        resize_keyboard=True
    )

def photo_food_kb(lang, pending_id):
    labels = {
        "uz": ("Yeyman ð", "Bekor â"),
        "ru": ("Ð¡ÑÐµÐ¼ ð", "ÐÑÐ¼ÐµÐ½Ð° â"),
        "en": ("I'll eat ð", "Cancel â"),
    }
    eat, cancel = labels.get(lang, labels["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=eat,    callback_data=f"eat_{pending_id}"),
         InlineKeyboardButton(text=cancel, callback_data=f"cancel_food_{pending_id}")]
    ])

def profile_kb(lang):
    labels = {
        "uz": ("ð¤ Men haqimda", "ð³ Obunam haqida", "âï¸ Men o'zgardim", "ð  Orqaga"),
        "ru": ("ð¤ ÐÐ±Ð¾ Ð¼Ð½Ðµ", "ð³ Ð Ð¿Ð¾Ð´Ð¿Ð¸ÑÐºÐµ", "âï¸ Ð¯ Ð¸Ð·Ð¼ÐµÐ½Ð¸Ð»ÑÑ", "ð  ÐÐ°Ð·Ð°Ð´"),
        "en": ("ð¤ About me", "ð³ Subscription", "âï¸ I changed", "ð  Back"),
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
        "uz": [("ð Bo'y", "edit_height"), ("âï¸ Vazn", "edit_weight"),
               ("ð Yosh", "edit_age"), ("ð¯ Maqsad", "edit_target"),
               ("ð Faollik", "edit_activity"),
               ("ð Orqaga", "prof_back")],
        "ru": [("ð Ð Ð¾ÑÑ", "edit_height"), ("âï¸ ÐÐµÑ", "edit_weight"),
               ("ð ÐÐ¾Ð·ÑÐ°ÑÑ", "edit_age"), ("ð¯ Ð¦ÐµÐ»Ñ", "edit_target"),
               ("ð ÐÐºÑÐ¸Ð²Ð½Ð¾ÑÑÑ", "edit_activity"),
               ("ð ÐÐ°Ð·Ð°Ð´", "prof_back")],
        "en": [("ð Height", "edit_height"), ("âï¸ Weight", "edit_weight"),
               ("ð Age", "edit_age"), ("ð¯ Goal", "edit_target"),
               ("ð Activity", "edit_activity"),
               ("ð Back", "prof_back")],
    }
    btns = labels.get(lang, labels["uz"])
    rows = [[InlineKeyboardButton(text=b[0], callback_data=b[1])] for b in btns]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def water_kb(lang):
    labels = {
        "uz": ("â Ichdim ð§", "ð Bugungi suv"),
        "ru": ("â ÐÑÐ¿Ð¸Ð» ð§", "ð ÐÐ¾Ð´Ð° Ð·Ð° ÑÐµÐ³Ð¾Ð´Ð½Ñ"),
        "en": ("â Drank ð§",  "ð Today water"),
    }
    a, b = labels.get(lang, labels["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a, callback_data="water_drank")],
        [InlineKeyboardButton(text=b, callback_data="water_today")],
    ])

def admin_approve_kb(user_id, req_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="â VIP berish", callback_data=f"admin_vip_{user_id}_{req_id}"),
         InlineKeyboardButton(text="â Rad etish", callback_data=f"admin_reject_{user_id}_{req_id}")]
    ])



# ââ HANDLERS: /start ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(LANGS["uz"]["lang_select"], reply_markup=lang_kb())
    await state.set_state(Reg.lang)

@dp.callback_query(F.data.startswith("lang_"), Reg.lang)
async def cb_lang(call: types.CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text(t(lang, "welcome"))
    await state.set_state(Reg.age)
    await call.answer()


@dp.message(Reg.lang)
async def reg_lang_text(message: types.Message, state: FSMContext):
    """Handle text input during language selection (remind to use buttons)"""
    await message.answer(LANGS["uz"]["lang_select"], reply_markup=lang_kb())

@dp.message(Reg.age)
async def reg_age(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    try:
        age = int(message.text.strip())
    except:
        await message.answer("â" + (" Iltimos, raqam kiriting!" if lang=="uz" else " ÐÐ¾Ð¶Ð°Ð»ÑÐ¹ÑÑÐ°, Ð²Ð²ÐµÐ´Ð¸ÑÐµ ÑÐ¸ÑÐ»Ð¾!" if lang=="ru" else " Please enter a number!"))
        return
    await state.update_data(age=age)
    await message.answer(t(lang, "ask_height"))
    await state.set_state(Reg.height)

@dp.message(Reg.height)
async def reg_height(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    txt = message.text.strip().replace("sm","").replace("ÑÐ¼","").replace("cm","").strip()
    try:
        height = float(txt)
    except:
        await message.answer("â" + (" Iltimos, to'g'ri qiymat kiriting! Masalan: 170" if lang=="uz" else " ÐÐ²ÐµÐ´Ð¸ÑÐµ ÐºÐ¾ÑÑÐµÐºÑÐ½Ð¾Ðµ Ð·Ð½Ð°ÑÐµÐ½Ð¸Ðµ! ÐÐ°Ð¿ÑÐ¸Ð¼ÐµÑ: 170" if lang=="ru" else " Enter a valid value! E.g. 170"))
        return
    await state.update_data(height=height)
    await message.answer(t(lang, "ask_weight"))
    await state.set_state(Reg.weight)

@dp.message(Reg.weight)
async def reg_weight(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    txt = message.text.strip().replace("kg","").replace("ÐºÐ³","").strip()
    try:
        weight = float(txt)
    except:
        await message.answer("â" + (" Iltimos, to'g'ri qiymat kiriting! Masalan: 60" if lang=="uz" else " ÐÐ²ÐµÐ´Ð¸ÑÐµ ÐºÐ¾ÑÑÐµÐºÑÐ½Ð¾Ðµ Ð·Ð½Ð°ÑÐµÐ½Ð¸Ðµ! ÐÐ°Ð¿ÑÐ¸Ð¼ÐµÑ: 60" if lang=="ru" else " Enter a valid value! E.g. 60"))
        return
    await state.update_data(weight=weight)
    await message.answer(t(lang, "ask_goal"), reply_markup=goal_kb(lang))
    await state.set_state(Reg.goal)

@dp.message(Reg.goal)
async def reg_goal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    txt  = message.text.strip()
    if txt in [t(lang,"goal_lose"), t("uz","goal_lose"), t("ru","goal_lose"), t("en","goal_lose")]:
        goal = "lose"
    elif txt in [t(lang,"goal_gain"), t("uz","goal_gain"), t("ru","goal_gain"), t("en","goal_gain")]:
        goal = "gain"
    else:
        goal = "keep"
    await state.update_data(target=goal)
    await message.answer(t(lang, "ask_gender"), reply_markup=gender_kb(lang))
    await state.set_state(Reg.gender)

@dp.message(Reg.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    txt  = message.text.strip()
    if txt in [t(lang,"gender_male"), t("uz","gender_male"), t("ru","gender_male"), t("en","gender_male")]:
        gender = "male"
    else:
        gender = "female"

    await state.update_data(gender=gender)
    await message.answer(t(lang, "ask_activity"), reply_markup=activity_kb(lang))
    await state.set_state(Reg.activity)


pending_food = {}

async def analyze_food_text(message, user, lang):
    """Analyze text food description with Gemini AI"""
    food_desc = message.text.strip()
    meal_t = get_meal_type()
    if lang=="ru":
        prompt = (
            f"Pol'zovatel' opisal edu: '{food_desc}'.\n"
            "Eto eda? Esli net â otvet' tol'ko 'NET'.\n"
            "Esli da â rasschiytay REALISTICHNOYE kolichestvo gramm na osnove standartnoy portsii:\n"
            "- Tarelka sup = 250-350ml, plov = 300-400g, mansura = 300g\n"
            "- Kusok khleba = 30g, bukhanka = 700g\n"
            "- Yayco = 55g, omllet iz 2 yaits = 120g\n"
            "- Bannan = 120g, yabloko = 150g\n"
            "NIkogda ne ispol'zuy 200g kak shablon!\n\n"
            "Format:\nBlyudo: [nazvanie]\nGramm: [REALISTICHNOYE] g\nKaloriya: [chislo] kkal\nBelki: [chislo] g\nZhiry: [chislo] g\nUglevody: [chislo] g"
        )
    elif lang=="en":
        prompt = (
            f"User described food: '{food_desc}'.\n"
            "Is this food? If not, reply only 'NOT FOOD'.\n"
            "If yes â calculate REALISTIC grams based on standard portions:\n"
            "- Bowl of soup = 250-350ml, rice dish = 300-400g\n"
            "- Slice of bread = 30g, 1 egg = 55g, 2-egg omelette = 120g\n"
            "- Banana = 120g, apple = 150g\n"
            "NEVER use 200g as a template!\n\n"
            "Format:\nDish: [name]\nGrams: [REALISTIC] g\nCalories: [number] kcal\nProtein: [number] g\nFat: [number] g\nCarbs: [number] g"
        )
    else:
        prompt = (
            f"Foydalanuvchi ovqat tasvirlab berdi: '{food_desc}'.\n"
            "Bu ovqatmi? Agar yo'q bo'lsa â faqat 'OVQAT EMAS' deb javob ber.\n"
            "Agar ha bo'lsa â standart porsiya asosida REAL gramm hisoblang:\n"
            "- Bir kosa sho'rva = 250-350ml, plov = 300-400g, manti 3 dona = 300g\n"
            "- Non bo'lagi = 30g, 1 tuxum = 55g, 2 tuxumli omlet = 120g\n"
            "- Banan = 120g, olma = 150g, semichka bir hovuch = 30g\n"
            "HECH QACHON 200g ni shablon qilib ishlatma!\n\n"
            "Format:\nTaom: [nom]\nGramm: [REAL miqdor] g\nKaloriya: [son] kkal\nOqsil: [son] g\nYog': [son] g\nUglevodlar: [son] g"
        )
    try:
        resp = await asyncio.to_thread(gemini.models.generate_content,
            model="gemini-1.5-flash",
            contents=[genai_types.Content(parts=[genai_types.Part(text=prompt)])]
        )
        result = resp.text.strip()
        if any(x in result.upper() for x in ["NET", "NOT FOOD", "OVQAT EMAS"]):
            if lang=="ru": await message.answer("\ud83e\udd14 Eto ne edu. Napiishte nazvanie blyuda ili prishhlite foto!")
            elif lang=="en": await message.answer("\ud83e\udd14 That doesn't look like food. Type a food name or send a photo!")
            else: await message.answer("\ud83e\udd14 Bu ovqat emas. Taom nomini yozing yoki rasm yuboring!")
            return
        # Parse calories and BJU
        cal = 0
        protein = 0
        fat = 0
        carbs = 0
        food_name = food_desc
        import re
        for line in result.split("\n"):
            if any(k in line.lower() for k in ["kaloriya","calories","ÐºÐ°Ð»Ð¾ÑÐ¸"]):
                nums = re.findall(r'\d+\.?\d*', line)
                if nums: cal = float(nums[0])
            if any(k in line.lower() for k in ["taom","dish","blyudo"]):
                parts = line.split(":")
                if len(parts) > 1: food_name = parts[1].strip()
            if any(k in line.lower() for k in ["oqsil","protein","belki"]):
                nums = re.findall(r'\d+\.?\d*', line)
                if nums: protein = float(nums[0])
            if any(k in line.lower() for k in ["yog","fat","zhiry"]):
                nums = re.findall(r'\d+\.?\d*', line)
                if nums: fat = float(nums[0])
            if any(k in line.lower() for k in ["uglevodlar","carbs","uglevody"]):
                nums = re.findall(r'\d+\.?\d*', line)
                if nums: carbs = float(nums[0])
        import time
        pend_id = int(time.time() * 1000) % 1000000
        pending_food[pend_id] = {
            "tid": message.from_user.id, "cal": cal, "food": food_name,
            "protein": protein, "fat": fat, "carbs": carbs,
            "meal_type": meal_t, "lang": lang
        }
        if lang=="ru": header = f"\ud83c\udf7d Analiz ({meal_label(meal_t,'ru')}):"
        elif lang=="en": header = f"\ud83c\udf7d Analysis ({meal_label(meal_t,'en')}):"
        else: header = f"\ud83c\udf7d Tahlil ({meal_label(meal_t,'uz')}):"
        await message.answer(header + "\n\n" + result, reply_markup=photo_food_kb(lang, pend_id))
    except Exception as e:
        logging.error(f"Food text analysis error: {e}")


# ââ HANDLERS: MAIN MENU BUTTONS âââââââââââââââââââââââââââââââââââââââââââââââ
def get_user_lang(tid):
    u = get_user(tid)
    return u.get("lang","uz") if u else "uz"

@dp.message(F.text, StateFilter(default_state))
async def text_router(message: types.Message, state: FSMContext):
    tid  = message.from_user.id
    user = get_user(tid)
    if not user:
        await message.answer("Botdan foydalanish uchun /start buyrug'ini yuboring.")
        return
    lang = user.get("lang","uz")
    txt  = message.text.strip()

    # Check all lang variants for each button
    def matches(key):
        return txt in [t("uz",key), t("ru",key), t("en",key)]

    if matches("btn_ration"):
        await handle_ration(message, user, lang)
    elif matches("btn_water"):
        await handle_water(message, user, lang)
    elif matches("btn_food_today"):
        await handle_food_today(message, tid, lang)
    elif matches("btn_food_week"):
        await handle_food_week(message, tid, lang)
    elif matches("btn_food_month"):
        await handle_food_month(message, tid, lang)
    elif matches("btn_ai"):
        await handle_ai_start(message, user, lang, state)
    elif matches("btn_profile"):
        await handle_profile(message, user, lang)
    elif matches("btn_vip"):
        await handle_vip(message, user, lang)
    elif matches("btn_check"):
        await handle_check_start(message, user, lang, state)
    elif matches("btn_photo_food"):
        if not is_vip_or_trial(user):
            await message.answer(t(lang,"trial_expired"))
            return
        if lang=="ru":
            await message.answer("📸 Otpravte foto blyuda i ya rasschiytayu kaloriya, belki, zhiry i uglevody!")
        elif lang=="en":
            await message.answer("📸 Send a photo of your food and I will calculate calories, protein, fat and carbs!")
        else:
            await message.answer("📸 Ovqatingiz rasmini yuboring — kaloriya, oqsil, yog' va uglevodlarni hisoblab beraman!")
    else:
        # Try to analyze as food text if user is VIP/trial
        if is_vip_or_trial(user) and len(txt) > 2:
            await analyze_food_text(message, user, lang)
        else:
            await message.answer(t(lang,"main_menu"), reply_markup=main_menu_kb(lang))

# ââ RATION ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def handle_ration(message, user, lang):
    if not is_vip_or_trial(user):
        await message.answer(t(lang,"trial_expired"))
        return
    cgoal = user.get("calories_goal") or calc_calories_goal(user)
    target = user.get("target","keep")
    w = user.get("weight",70)
    h = user.get("height",170)
    a = user.get("age",25)
    water_l = round(w * 0.033, 1)

    if lang == "ru":
        if target == "lose":
            direction = "Ð¿Ð¾ÑÑÐ´ÐµÐ½Ð¸Ñ"
            advice = "ÐÑÑÑÐµ Ð¼ÐµÐ½ÑÑÐµ Ð¶Ð¸ÑÐ½Ð¾Ð³Ð¾ Ð¸ ÑÐ»Ð°Ð´ÐºÐ¾Ð³Ð¾, Ð±Ð¾Ð»ÑÑÐµ Ð¾Ð²Ð¾ÑÐµÐ¹ Ð¸ Ð±ÐµÐ»ÐºÐ°."
            foods = "â¢ ÐÑÐµÑÐºÐ°, ÐºÑÑÐ¸Ð½Ð°Ñ Ð³ÑÑÐ´ÐºÐ°, Ð¾Ð²Ð¾ÑÐ½Ð¾Ð¹ ÑÐ°Ð»Ð°Ñ, ÐºÐµÑÐ¸Ñ, ÑÐ¹ÑÐ°, ÑÑÐ±Ð°"
        elif target == "gain":
            direction = "Ð½Ð°Ð±Ð¾ÑÐ° Ð²ÐµÑÐ°"
            advice = "ÐÑÑÑÐµ Ð±Ð¾Ð»ÑÑÐµ ÑÐ³Ð»ÐµÐ²Ð¾Ð´Ð¾Ð² Ð¸ Ð±ÐµÐ»ÐºÐ°, Ð½Ðµ Ð¿ÑÐ¾Ð¿ÑÑÐºÐ°Ð¹ÑÐµ Ð¿ÑÐ¸ÑÐ¼Ñ Ð¿Ð¸ÑÐ¸."
            foods = "â¢ Ð Ð¸Ñ, Ð³Ð¾Ð²ÑÐ´Ð¸Ð½Ð°, Ð¾ÑÐµÑÐ¸, Ð°Ð²Ð¾ÐºÐ°Ð´Ð¾, Ð¼Ð¾Ð»Ð¾ÐºÐ¾, ÑÐ¹ÑÐ°, ÑÐ»ÐµÐ±"
        else:
            direction = "Ð¿Ð¾Ð´Ð´ÐµÑÐ¶Ð°Ð½Ð¸Ñ Ð²ÐµÑÐ°"
            advice = "ÐÑÐ¸Ð´ÐµÑÐ¶Ð¸Ð²Ð°Ð¹ÑÐµÑÑ ÑÐ±Ð°Ð»Ð°Ð½ÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð½Ð¾Ð³Ð¾ Ð¿Ð¸ÑÐ°Ð½Ð¸Ñ."
            foods = "â¢ ÐÑÐ±ÑÐµ ÑÐµÐ»ÑÐ½ÑÐµ Ð¿ÑÐ¾Ð´ÑÐºÑÑ Ð² ÑÐ¼ÐµÑÐµÐ½Ð½Ð¾Ð¼ ÐºÐ¾Ð»Ð¸ÑÐµÑÑÐ²Ðµ"
        txt = (f"ð½ *ÐÐ°Ñ Ð´Ð½ÐµÐ²Ð½Ð¾Ð¹ ÑÐ°ÑÐ¸Ð¾Ð½*\n\n"
               f"ð¯ Ð¦ÐµÐ»Ñ: {direction}\n"
               f"ð¥ Ð ÐµÐºÐ¾Ð¼ÐµÐ½Ð´ÑÐµÐ¼ÑÐµ ÐºÐ°Ð»Ð¾ÑÐ¸Ð¸: *{cgoal} ÐºÐºÐ°Ð»/Ð´ÐµÐ½Ñ*\n"
               f"ð§ ÐÐ¾Ð´Ð°: *{water_l} Ð»/Ð´ÐµÐ½Ñ*\n\n"
               f"ð Ð¡Ð¾Ð²ÐµÑ: {advice}\n\n"
               f"ð¥ Ð ÐµÐºÐ¾Ð¼ÐµÐ½Ð´ÑÐµÐ¼ÑÐµ Ð¿ÑÐ¾Ð´ÑÐºÑÑ:\n{foods}")
    elif lang == "en":
        if target == "lose":
            direction = "weight loss"
            advice = "Eat less fat and sugar, more vegetables and protein."
            foods = "â¢ Buckwheat, chicken breast, vegetable salad, kefir, eggs, fish"
        elif target == "gain":
            direction = "weight gain"
            advice = "Eat more carbs and protein, don't skip meals."
            foods = "â¢ Rice, beef, nuts, avocado, milk, eggs, bread"
        else:
            direction = "weight maintenance"
            advice = "Follow a balanced diet."
            foods = "â¢ Any whole foods in moderate amounts"
        txt = (f"ð½ *Your daily ration*\n\n"
               f"ð¯ Goal: {direction}\n"
               f"ð¥ Recommended calories: *{cgoal} kcal/day*\n"
               f"ð§ Water: *{water_l} L/day*\n\n"
               f"ð Tip: {advice}\n\n"
               f"ð¥ Recommended foods:\n{foods}")
    else:
        if target == "lose":
            direction = "ozish"
            advice = "Kam yog'li, kam shakarli ovqatlar yeng. Ko'proq sabzavot va oqsil iste'mol qiling."
            foods = "â¢ Karavshanur, tovuq ko'kragi, sabzavot salati, kefir, tuxum, baliq"
        elif target == "gain":
            direction = "vazn qo'shish"
            advice = "Ko'proq uglevod va oqsil iste'mol qiling, ovqatni o'tkazib yubormang."
            foods = "â¢ Guruch, mol go'shti, yong'oq, avokado, sut, tuxum, non"
        else:
            direction = "vaznni ushlab qolish"
            advice = "Muvozanatli ovqatlanishga amal qiling."
            foods = "â¢ Har qanday to'liq oziq-ovqat o'rtacha miqdorda"
        txt = (f"ð½ *Kunlik ratsioningiz*\n\n"
               f"ð¯ Maqsad: {direction}\n"
               f"ð¥ Tavsiya etilgan kaloriya: *{cgoal} kkal/kun*\n"
               f"ð§ Suv: *{water_l} l/kun*\n\n"
               f"ð Maslahat: {advice}\n\n"
               f"ð¥ Tavsiya etilgan ovqatlar:\n{foods}")
    await message.answer(txt, parse_mode="Markdown")



# ââ WATER âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def handle_water(message, user, lang):
    if not is_vip_or_trial(user):
        await message.answer(t(lang,"trial_expired"))
        return
    w = user.get("weight",70)
    water_l = round(w * 0.033, 1)
    water_ml = int(water_l * 1000)
    tid = message.from_user.id

    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    drunk = conn.execute(
        "SELECT COALESCE(SUM(amount_ml),0) FROM water_logs WHERE telegram_id=? AND date(logged_at)=?",
        (tid, today)
    ).fetchone()[0]
    conn.close()

    drunk_l = round(drunk / 1000, 2)
    left_l  = round(max(0, water_l - drunk_l), 2)

    if lang == "ru":
        txt = (f"ð§ *ÐÐ¾Ð´Ð½ÑÐ¹ ÑÐ°ÑÐ¸Ð¾Ð½*\n\n"
               f"ð¯ ÐÐ¾ÑÐ¼Ð°: *{water_l} Ð»/Ð´ÐµÐ½Ñ* ({water_ml} Ð¼Ð»)\n"
               f"â ÐÑÐ¿Ð¸ÑÐ¾ ÑÐµÐ³Ð¾Ð´Ð½Ñ: *{drunk_l} Ð»*\n"
               f"â³ ÐÑÑÐ°Ð»Ð¾ÑÑ: *{left_l} Ð»*\n\n"
               f"ÐÐ°Ð¶Ð¼Ð¸ÑÐµ ÐºÐ½Ð¾Ð¿ÐºÑ ÐºÐ°Ð¶Ð´ÑÐ¹ ÑÐ°Ð·, ÐºÐ¾Ð³Ð´Ð° Ð²ÑÐ¿Ð¸Ð²Ð°ÐµÑÐµ ÑÑÐ°ÐºÐ°Ð½ Ð²Ð¾Ð´Ñ (250Ð¼Ð»)")
    elif lang == "en":
        txt = (f"ð§ *Water Ration*\n\n"
               f"ð¯ Norm: *{water_l} L/day* ({water_ml} ml)\n"
               f"â Drunk today: *{drunk_l} L*\n"
               f"â³ Remaining: *{left_l} L*\n\n"
               f"Press the button each time you drink a glass of water (250ml)")
    else:
        txt = (f"ð§ *Suv ratsioni*\n\n"
               f"ð¯ Norma: *{water_l} l/kun* ({water_ml} ml)\n"
               f"â Bugun ichilgan: *{drunk_l} l*\n"
               f"â³ Qoldi: *{left_l} l*\n\n"
               f"Har safar bir stakan suv (250ml) ichganingizda tugmani bosing")
    await message.answer(txt, parse_mode="Markdown", reply_markup=water_kb(lang))

@dp.callback_query(F.data == "water_drank")
async def cb_water_drank(call: types.CallbackQuery):
    tid  = call.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"
    conn = get_conn()
    conn.execute("INSERT INTO water_logs (telegram_id, amount_ml) VALUES (?,?)", (tid, 250))
    conn.commit()
    today = datetime.now().strftime("%Y-%m-%d")
    drunk = conn.execute(
        "SELECT COALESCE(SUM(amount_ml),0) FROM water_logs WHERE telegram_id=? AND date(logged_at)=?",
        (tid, today)
    ).fetchone()[0]
    conn.close()
    drunk_l = round(drunk / 1000, 2)
    if lang == "ru": msg = f"â ÐÐ°Ð¿Ð¸ÑÐ°Ð½Ð¾! Ð¡ÐµÐ³Ð¾Ð´Ð½Ñ Ð²ÑÐ¿Ð¸ÑÐ¾: *{drunk_l} Ð»* ð§"
    elif lang == "en": msg = f"â Logged! Today drank: *{drunk_l} L* ð§"
    else: msg = f"â Yozildi! Bugun ichilgan: *{drunk_l} l* ð§"
    await call.answer()
    await call.message.answer(msg, parse_mode="Markdown")

@dp.callback_query(F.data == "water_today")
async def cb_water_today(call: types.CallbackQuery):
    tid  = call.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT amount_ml, logged_at FROM water_logs WHERE telegram_id=? AND date(logged_at)=? ORDER BY logged_at",
        (tid, today)
    ).fetchall()
    conn.close()
    if not rows:
        if lang=="ru": await call.message.answer("ð§ Ð¡ÐµÐ³Ð¾Ð´Ð½Ñ Ð²Ð¾Ð´Ñ Ð½Ðµ Ð·Ð°ÑÐ¸ÐºÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð¾.")
        elif lang=="en": await call.message.answer("ð§ No water logged today.")
        else: await call.message.answer("ð§ Bugun suv yozilmagan.")
        await call.answer(); return
    total = sum(r[0] for r in rows)
    lines = [f"  â¢ {r[1][11:16]} â {r[0]} ml" for r in rows]
    if lang=="ru": header = f"ð§ *ÐÐ¾Ð´Ð° Ð·Ð° ÑÐµÐ³Ð¾Ð´Ð½Ñ* â {round(total/1000,2)} Ð»\n"
    elif lang=="en": header = f"ð§ *Today's water* â {round(total/1000,2)} L\n"
    else: header = f"ð§ *Bugungi suv* â {round(total/1000,2)} l\n"
    await call.message.answer(header + "\n".join(lines), parse_mode="Markdown")
    await call.answer()

# ââ FOOD LOGS âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def handle_food_today(message, tid, lang):
    user = get_user(tid)
    if not is_vip_or_trial(user):
        await message.answer(t(lang,"trial_expired"))
        return
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT food_name, calories, meal_type, logged_at FROM food_logs WHERE telegram_id=? AND date(logged_at)=? ORDER BY logged_at",
        (tid, today)
    ).fetchall()
    conn.close()
    if not rows:
        if lang=="ru": await message.answer("ð Ð¡ÐµÐ³Ð¾Ð´Ð½Ñ Ð½ÐµÑ Ð·Ð°Ð¿Ð¸ÑÐµÐ¹ Ð¾ ÐµÐ´Ðµ.")
        elif lang=="en": await message.answer("ð No food logged today.")
        else: await message.answer("ð Bugun ovqat yozilmagan.")
        return
    total = sum(r[1] for r in rows)
    lines = [f"  {meal_label(r[2],lang)} {r[3][11:16]} â {r[0]} ({round(r[1])} kkal)" for r in rows]
    if lang=="ru": header = f"ð *ÐÐ´Ð° Ð·Ð° ÑÐµÐ³Ð¾Ð´Ð½Ñ* â Ð¸ÑÐ¾Ð³Ð¾ {round(total)} ÐºÐºÐ°Ð»\n\n"
    elif lang=="en": header = f"ð *Today's food* â total {round(total)} kcal\n\n"
    else: header = f"ð *Bugungi ovqatlar* â jami {round(total)} kkal\n\n"
    await message.answer(header + "\n".join(lines), parse_mode="Markdown")

async def handle_food_week(message, tid, lang):
    user = get_user(tid)
    if not is_vip_or_trial(user):
        await message.answer(t(lang,"trial_expired"))
        return
    conn = get_conn()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT food_name, calories, meal_type, logged_at FROM food_logs WHERE telegram_id=? AND date(logged_at)>=? ORDER BY logged_at",
        (tid, week_ago)
    ).fetchall()
    conn.close()
    if not rows:
        if lang=="ru": await message.answer("ð ÐÐ° Ð½ÐµÐ´ÐµÐ»Ñ Ð½ÐµÑ Ð·Ð°Ð¿Ð¸ÑÐµÐ¹.")
        elif lang=="en": await message.answer("ð No records for the week.")
        else: await message.answer("ð Hafta davomida yozuv yo'q.")
        return
    total = sum(r[1] for r in rows)
    lines = [f"  {r[3][:10]} {meal_label(r[2],lang)} {r[3][11:16]} â {r[0]} ({round(r[1])} kkal)" for r in rows]
    if lang=="ru": header = f"ð *ÐÐ´Ð° Ð·Ð° Ð½ÐµÐ´ÐµÐ»Ñ* â Ð¸ÑÐ¾Ð³Ð¾ {round(total)} ÐºÐºÐ°Ð»\n\n"
    elif lang=="en": header = f"ð *Weekly food* â total {round(total)} kcal\n\n"
    else: header = f"ð *Haftalik ovqatlar* â jami {round(total)} kkal\n\n"
    await message.answer(header + "\n".join(lines), parse_mode="Markdown")

async def handle_food_month(message, tid, lang):
    user = get_user(tid)
    if not is_vip_or_trial(user):
        await message.answer(t(lang,"trial_expired"))
        return
    conn = get_conn()
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT food_name, calories, meal_type, logged_at FROM food_logs WHERE telegram_id=? AND date(logged_at)>=? ORDER BY logged_at",
        (tid, month_ago)
    ).fetchall()
    conn.close()
    if not rows:
        if lang=="ru": await message.answer("ð ÐÐ° Ð¼ÐµÑÑÑ Ð½ÐµÑ Ð·Ð°Ð¿Ð¸ÑÐµÐ¹.")
        elif lang=="en": await message.answer("ð No records for the month.")
        else: await message.answer("ð Oy davomida yozuv yo'q.")
        return
    total = sum(r[1] for r in rows)
    lines = [f"  {r[3][:10]} {meal_label(r[2],lang)} {r[3][11:16]} â {r[0]} ({round(r[1])} kkal)" for r in rows]
    if lang=="ru": header = f"ð *ÐÐ´Ð° Ð·Ð° Ð¼ÐµÑÑÑ* â Ð¸ÑÐ¾Ð³Ð¾ {round(total)} ÐºÐºÐ°Ð»\n\n"
    elif lang=="en": header = f"ð *Monthly food* â total {round(total)} kcal\n\n"
    else: header = f"ð *Oylik ovqatlar* â jami {round(total)} kkal\n\n"
    await message.answer(header + "\n".join(lines[:80]), parse_mode="Markdown")



# ââ AI DIETOLOG âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def handle_ai_start(message, user, lang, state):
    if not is_vip_or_trial(user):
        await message.answer(t(lang,"trial_expired"))
        return
    await state.set_state(AIChat.chatting)
    if lang=="ru": txt = "ð¤ *AI ÐÐ¸ÐµÑÐ¾Ð»Ð¾Ð³* â Ð·Ð°Ð´Ð°Ð¹ÑÐµ Ð²Ð¾Ð¿ÑÐ¾Ñ Ð¾ Ð¿Ð¸ÑÐ°Ð½Ð¸Ð¸ Ð¸Ð»Ð¸ Ð¿Ð¾ÑÑÐ´ÐµÐ½Ð¸Ð¸!\n\nÐÐ»Ñ Ð²ÑÑÐ¾Ð´Ð° Ð¾ÑÐ¿ÑÐ°Ð²ÑÑÐµ /menu"
    elif lang=="en": txt = "ð¤ *AI Dietologist* â ask me about nutrition or weight loss!\n\nSend /menu to exit"
    else: txt = "ð¤ *AI Diyetolog* â oziq-ovqat yoki ozish haqida savol bering!\n\n/menu â chiqish uchun"
    await message.answer(txt, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

@dp.message(AIChat.chatting)
async def handle_ai_message(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        await state.clear(); return
    lang = user.get("lang","uz")
    if message.text and message.text.startswith("/menu"):
        await state.clear()
        await message.answer(t(lang,"main_menu"), reply_markup=main_menu_kb(lang))
        return
    if not user:
        user = get_user(message.from_user.id)
    if not user:
        await state.clear(); return
    lang = user.get("lang","uz")
    target = user.get("target","keep")

    sys_prompt = (
        "Sen faqat ovqat, diyeta, ozish va vazn olish haqida maslahatlashuvchi AI diyetologsan. "
        "Faqat shu mavzularda javob ber. Boshqa mavzularda: "
        "'Bizning maqsadimiz â foydalanuvchining sog\'liqli ovqatlanishiga yordam berish. "
        "Keling, ozish yoki vazn olish haqida gaplashamiz!' â de. "
        f"Foydalanuvchi maqsadi: {target}. "
        f"Javoblarni {lang} tilida ber."
    )
    try:
        resp = await asyncio.to_thread(gemini.models.generate_content,
            model="gemini-1.5-flash",
            contents=[
                genai_types.Content(role="user", parts=[
                    genai_types.Part(text=sys_prompt + "\n\nFoydalanuvchi: " + (message.text or ""))
                ])
            ]
        )
        await message.answer("ð¤ " + resp.text)
    except Exception as e:
        logging.error(f"AI error: {e}")
        if lang=="ru": await message.answer("â ÐÑÐ¸Ð±ÐºÐ° AI. ÐÐ¾Ð¿ÑÐ¾Ð±ÑÐ¹ÑÐµ Ð¿Ð¾Ð·Ð¶Ðµ.")
        elif lang=="en": await message.answer("â AI error. Try again later.")
        else: await message.answer("â AI xatolik. Keyinroq urinib ko'ring.")

@dp.message(Reg.activity)
async def reg_activity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    txt  = message.text.strip()

    # Map button text to activity level
    if txt in [t(l,"activity_low") for l in ["uz","ru","en"]]:
        activity = "low"
    elif txt in [t(l,"activity_high") for l in ["uz","ru","en"]]:
        activity = "high"
    else:
        activity = "medium"

    d = await state.get_data()
    now_str = datetime.now().isoformat()
    gender = d.get("gender", "male")
    cgoal = calc_calories_goal({
        "weight": d.get("weight",70), "height": d.get("height",170),
        "age": d.get("age",30), "gender": gender,
        "target": d.get("target","keep"), "activity": activity
    })
    save_user(
        message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        lang=lang,
        age=d.get("age"),
        height=d.get("height"),
        weight=d.get("weight"),
        target=d.get("target","keep"),
        gender=gender,
        activity=activity,
        calories_goal=cgoal,
        trial_start=now_str,
    )
    await state.clear()
    await message.answer(t(lang, "reg_done"), reply_markup=main_menu_kb(lang))

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    lang = user.get("lang","uz") if user else "uz"
    await message.answer(t(lang,"main_menu"), reply_markup=main_menu_kb(lang))

# ââ PROFILE âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def handle_profile(message, user, lang):
    if lang=="ru": txt = "ð¤ *ÐÐ¾Ð¹ Ð¿ÑÐ¾ÑÐ¸Ð»Ñ*\nÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ°Ð·Ð´ÐµÐ»:"
    elif lang=="en": txt = "ð¤ *My Profile*\nChoose a section:"
    else: txt = "ð¤ *Profilim*\nBo'limni tanlang:"
    await message.answer(txt, parse_mode="Markdown", reply_markup=profile_kb(lang))

@dp.callback_query(F.data == "prof_info")
async def cb_prof_info(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if not user:
        await call.answer("Avval ro'yxatdan o'ting!"); return
    lang = user.get("lang","uz")
    target_map = {
        "lose": {"uz":"Ozish ð¥","ru":"ÐÐ¾ÑÑÐ´ÐµÑÑ ð¥","en":"Lose weight ð¥"},
        "gain": {"uz":"Vazn qo'shish ðª","ru":"ÐÐ°Ð±ÑÐ°ÑÑ Ð²ÐµÑ ðª","en":"Gain weight ðª"},
        "keep": {"uz":"Vaznni saqlash âï¸","ru":"ÐÐ¾Ð´Ð´ÐµÑÐ¶Ð°ÑÑ Ð²ÐµÑ âï¸","en":"Maintain weight âï¸"},
    }
    gender_map = {
        "male": {"uz":"Erkak ð§","ru":"ÐÑÐ¶ÑÐ¸Ð½Ð° ð§","en":"Male ð§"},
        "female": {"uz":"Ayol ð©","ru":"ÐÐµÐ½ÑÐ¸Ð½Ð° ð©","en":"Female ð©"},
    }
    activity_map = {
        "low":    {"uz":"ð¶ Kam faol","ru":"ð¶ ÐÐ°Ð»Ð¾Ð°ÐºÑÐ¸Ð²Ð½ÑÐ¹","en":"ð¶ Low active"},
        "medium": {"uz":"ð´ O'rta faol","ru":"ð´ Ð£Ð¼ÐµÑÐµÐ½Ð½Ð¾ Ð°ÐºÑÐ¸Ð²Ð½ÑÐ¹","en":"ð´ Moderately active"},
        "high":   {"uz":"ðï¸ Juda faol","ru":"ðï¸ ÐÑÐµÐ½Ñ Ð°ÐºÑÐ¸Ð²Ð½ÑÐ¹","en":"ðï¸ Very active"},
    }
    tgt = target_map.get(user.get("target","keep"),{}).get(lang, user.get("target","â"))
    gen = gender_map.get(user.get("gender",""),{}).get(lang, user.get("gender","â"))
    act = activity_map.get(user.get("activity","medium"),{}).get(lang, "â")
    cgoal = user.get("calories_goal") or "â"
    if lang=="ru":
        txt = (f"ð¤ *ÐÐ½ÑÐ¾ÑÐ¼Ð°ÑÐ¸Ñ Ð¾ Ð²Ð°Ñ*\n\n"
               f"ð ÐÐ¾Ð·ÑÐ°ÑÑ: {user.get('age','â')} Ð»ÐµÑ\n"
               f"ð¤ ÐÐ¾Ð»: {gen}\n"
               f"ð ÐÐºÑÐ¸Ð²Ð½Ð¾ÑÑÑ: {act}\n"
               f"ð Ð Ð¾ÑÑ: {user.get('height','â')} ÑÐ¼\n"
               f"âï¸ ÐÐµÑ: {user.get('weight','â')} ÐºÐ³\n"
               f"ð¯ Ð¦ÐµÐ»Ñ: {tgt}\n"
               f"ð¥ ÐÐ¾ÑÐ¼Ð° ÐºÐ°Ð»Ð¾ÑÐ¸Ð¹: {cgoal} ÐºÐºÐ°Ð»/Ð´ÐµÐ½Ñ")
    elif lang=="en":
        txt = (f"ð¤ *Your Information*\n\n"
               f"ð Age: {user.get('age','â')}\n"
               f"ð¤ Gender: {gen}\n"
               f"ð Activity: {act}\n"
               f"ð Height: {user.get('height','â')} cm\n"
               f"âï¸ Weight: {user.get('weight','â')} kg\n"
               f"ð¯ Goal: {tgt}\n"
               f"ð¥ Calorie norm: {cgoal} kcal/day")
    else:
        txt = (f"ð¤ *Siz haqingizda*\n\n"
               f"ð Yosh: {user.get('age','â')} yosh\n"
               f"ð¤ Jins: {gen}\n"
               f"ð Faollik: {act}\n"
               f"ð Bo'y: {user.get('height','â')} sm\n"
               f"âï¸ Vazn: {user.get('weight','â')} kg\n"
               f"ð¯ Maqsad: {tgt}\n"
               f"ð¥ Kaloriya normasi: {cgoal} kkal/kun")
    await call.message.edit_text(txt, parse_mode="Markdown", reply_markup=profile_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "prof_sub")
async def cb_prof_sub(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if not user:
        await call.answer(); return
    lang = user.get("lang","uz")
    if user.get("is_vip"):
        vs = user.get("vip_start","â")
        ve = user.get("vip_end","â")
        try:
            end_dt = datetime.fromisoformat(ve)
            days_left = (end_dt - datetime.now()).days
        except:
            days_left = "â"
        if lang=="ru":
            txt = f"ð³ *ÐÐ°ÑÐ° Ð¿Ð¾Ð´Ð¿Ð¸ÑÐºÐ°*\n\nâ­ Ð¢Ð°ÑÐ¸Ñ: VIP\nð ÐÐ°ÑÐ°Ð»Ð¾: {vs[:10]}\nð ÐÐ¾Ð½ÐµÑ: {ve[:10]}\nâ³ ÐÑÑÐ°Ð»Ð¾ÑÑ: {days_left} Ð´Ð½ÐµÐ¹"
        elif lang=="en":
            txt = f"ð³ *Your Subscription*\n\nâ­ Plan: VIP\nð Start: {vs[:10]}\nð End: {ve[:10]}\nâ³ Remaining: {days_left} days"
        else:
            txt = f"ð³ *Obunangiz*\n\nâ­ Tarif: VIP\nð Boshlangan: {vs[:10]}\nð Tugaydi: {ve[:10]}\nâ³ Qoldi: {days_left} kun"
    else:
        ts = user.get("trial_start","â")
        rem = get_trial_remaining(user)
        if lang=="ru":
            txt = f"ð³ *ÐÐ°ÑÐ° Ð¿Ð¾Ð´Ð¿Ð¸ÑÐºÐ°*\n\nð¦ Ð¢Ð°ÑÐ¸Ñ: FREE TRIAL\nð ÐÐ°ÑÐ°Ð»Ð¾: {ts[:10]}\nâ³ ÐÑÑÐ°Ð»Ð¾ÑÑ: {rem} Ð´Ð½ÐµÐ¹"
        elif lang=="en":
            txt = f"ð³ *Your Subscription*\n\nð¦ Plan: FREE TRIAL\nð Start: {ts[:10]}\nâ³ Remaining: {rem} days"
        else:
            txt = f"ð³ *Obunangiz*\n\nð¦ Tarif: FREE TRIAL\nð Boshlangan: {ts[:10]}\nâ³ Qoldi: {rem} kun"
    await call.message.edit_text(txt, parse_mode="Markdown", reply_markup=profile_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "prof_edit")
async def cb_prof_edit(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    lang = user.get("lang","uz") if user else "uz"
    if lang=="ru": txt = "âï¸ Ð§ÑÐ¾ ÑÐ¾ÑÐ¸ÑÐµ Ð¸Ð·Ð¼ÐµÐ½Ð¸ÑÑ?"
    elif lang=="en": txt = "âï¸ What would you like to change?"
    else: txt = "âï¸ Nimani o'zgartirmoqchisiz?"
    await call.message.edit_text(txt, reply_markup=edit_profile_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "prof_back")
async def cb_prof_back(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    lang = user.get("lang","uz") if user else "uz"
    if lang=="ru": txt = "ð¤ *ÐÐ¾Ð¹ Ð¿ÑÐ¾ÑÐ¸Ð»Ñ*\nÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ°Ð·Ð´ÐµÐ»:"
    elif lang=="en": txt = "ð¤ *My Profile*\nChoose a section:"
    else: txt = "ð¤ *Profilim*\nBo'limni tanlang:"
    await call.message.edit_text(txt, parse_mode="Markdown", reply_markup=profile_kb(lang))
    await call.answer()

@dp.callback_query(F.data.startswith("edit_"))
async def cb_edit_field(call: types.CallbackQuery, state: FSMContext):
    field = call.data.replace("edit_","")
    user  = get_user(call.from_user.id)
    lang  = user.get("lang","uz") if user else "uz"
    prompts = {
        "height":   {"uz":"ð Yangi bo'yingizni kiriting (sm):", "ru":"ð ÐÐ²ÐµÐ´Ð¸ÑÐµ Ð½Ð¾Ð²ÑÐ¹ ÑÐ¾ÑÑ (ÑÐ¼):", "en":"ð Enter new height (cm):"},
        "weight":   {"uz":"âï¸ Yangi vazningizni kiriting (kg):", "ru":"âï¸ ÐÐ²ÐµÐ´Ð¸ÑÐµ Ð½Ð¾Ð²ÑÐ¹ Ð²ÐµÑ (ÐºÐ³):", "en":"âï¸ Enter new weight (kg):"},
        "age":      {"uz":"ð Yangi yoshingizni kiriting:", "ru":"ð ÐÐ²ÐµÐ´Ð¸ÑÐµ Ð½Ð¾Ð²ÑÐ¹ Ð²Ð¾Ð·ÑÐ°ÑÑ:", "en":"ð Enter new age:"},
        "target":   {"uz":"ð¯ Maqsadni tanlang:", "ru":"ð¯ ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐµÐ»Ñ:", "en":"ð¯ Choose goal:"},
        "activity": {"uz":"ð Faollik darajangizni tanlang:", "ru":"ð ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÑÐ¾Ð²ÐµÐ½Ñ Ð°ÐºÑÐ¸Ð²Ð½Ð¾ÑÑÐ¸:", "en":"ð Choose activity level:"},
    }
    await state.update_data(edit_field=field)
    if field == "target":
        await call.message.answer(prompts[field].get(lang,""), reply_markup=goal_kb(lang))
        await state.set_state(EditProfile.value)
    elif field == "activity":
        await call.message.answer(prompts[field].get(lang,""), reply_markup=activity_kb(lang))
        await state.set_state(EditProfile.value)
    else:
        await call.message.answer(prompts.get(field,{}).get(lang,""))
        await state.set_state(EditProfile.value)
    await call.answer()

@dp.message(EditProfile.value)
async def edit_profile_value(message: types.Message, state: FSMContext):
    data  = await state.get_data()
    field = data.get("edit_field","")
    user  = get_user(message.from_user.id)
    lang  = user.get("lang","uz") if user else "uz"
    val   = message.text.strip()
    try:
        if field == "height":   save_user(message.from_user.id, height=float(val.replace("sm","").replace("ÑÐ¼","").replace("cm","").strip()))
        elif field == "weight": save_user(message.from_user.id, weight=float(val.replace("kg","").replace("ÐºÐ³","").strip()))
        elif field == "age":    save_user(message.from_user.id, age=int(val))
        elif field == "target":
            if val in [t(l,"goal_lose") for l in LANGS]: gv="lose"
            elif val in [t(l,"goal_gain") for l in LANGS]: gv="gain"
            else: gv="keep"
            save_user(message.from_user.id, target=gv)
        elif field == "activity":
            if val in [t(l,"activity_low") for l in LANGS]: av="low"
            elif val in [t(l,"activity_high") for l in LANGS]: av="high"
            else: av="medium"
            save_user(message.from_user.id, activity=av)
        # Recalculate calories
        u2 = get_user(message.from_user.id)
        if u2:
            save_user(message.from_user.id, calories_goal=calc_calories_goal(u2))
    except:
        pass
    await state.clear()
    if lang=="ru": txt = "â ÐÐ°Ð½Ð½ÑÐµ Ð¾Ð±Ð½Ð¾Ð²Ð»ÐµÐ½Ñ!"
    elif lang=="en": txt = "â Data updated!"
    else: txt = "â Ma'lumotlar yangilandi!"
    await message.answer(txt, reply_markup=main_menu_kb(lang))



# ââ VIP & PAYMENT âââââââââââââââââââââââââââââââââââââââââââââââ
async def handle_vip(message, user, lang):
    if lang=="ru":
        txt = (
            "\u2b50 *VIP Podpiska â Tarify*\n\n"
            "\ud83d\udcc5 *Ezhemesyachno:* 20 000 sum/mes\n"
            "\ud83c\udf1f *Godovoy:* 220 000 sum/god (2 mes besplatno!)\n\n"
            "\ud83d\udcb3 Karta dlya oplaty:\n"
            "`" + CARD_NUMBER + "`\n\n"
            "\ud83d\udccb Posle oplaty:\n"
            "Nazhmite \ud83e\uddfe *Otpravit chek* i prishhlite skrinshot oplaty."
        )
    elif lang=="en":
        txt = (
            "\u2b50 *VIP Subscription â Plans*\n\n"
            "\ud83d\udcc5 *Monthly:* 20,000 UZS/month\n"
            "\ud83c\udf1f *Yearly:* 220,000 UZS/year (2 months free!)\n\n"
            "\ud83d\udcb3 Payment card:\n"
            "`" + CARD_NUMBER + "`\n\n"
            "\ud83d\udccb After payment:\n"
            "Press \ud83e\uddfe *Send receipt* and send a screenshot."
        )
    else:
        txt = (
            "\u2b50 *VIP Obuna â Tariflar*\n\n"
            "\ud83d\udcc5 *Oylik:* 20 000 so'm/oy\n"
            "\ud83c\udf1f *Yillik:* 220 000 so'm/yil (2 oy bepul!)\n\n"
            "\ud83d\udcb3 To'lov kartasi:\n"
            "`" + CARD_NUMBER + "`\n\n"
            "\ud83d\udccb To'lovdan keyin:\n"
            "\ud83e\uddfe *Chek yuborish* tugmasini bosib, skrinshot yuboring."
        )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\ud83d\udcc5 Oylik â 20 000 so'm", callback_data="vip_monthly"),
         InlineKeyboardButton(text="\ud83c\udf1f Yillik â 220 000 so'm", callback_data="vip_yearly")],
        [InlineKeyboardButton(text="\ud83e\uddfe Chek yuborish", callback_data="vip_send_check")],
    ])
    await message.answer(txt, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data.in_(["vip_monthly","vip_yearly","vip_send_check"]))
async def cb_vip_plan(call: types.CallbackQuery, state: FSMContext):
    user = get_user(call.from_user.id)
    lang = user.get("lang","uz") if user else "uz"
    if call.data == "vip_send_check":
        await call.message.answer(
            "\ud83e\uddfe To'lov chekini (skrinshotini) yuboring:" if lang=="uz"
            else "\ud83e\uddfe Prishhlite skrinshot cheka:" if lang=="ru"
            else "\ud83e\uddfe Send a screenshot of your receipt:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(PaymentState.waiting_receipt)
        await call.answer()
        return
    plan = "yearly" if call.data == "vip_yearly" else "monthly"
    await state.update_data(vip_plan=plan)
    if lang=="ru":
        price = "220 000 sum" if plan=="yearly" else "20 000 sum"
        await call.message.answer(f"\u2705 Vy vybrali: {'Godovoy' if plan=='yearly' else 'Ezhemesyachnyy'} plan â {price}\n\nPerevedite na kartu `{CARD_NUMBER}` i otpravte \ud83e\uddfe *Chek*", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    elif lang=="en":
        price = "220,000 UZS" if plan=="yearly" else "20,000 UZS"
        await call.message.answer(f"\u2705 Selected: {'Yearly' if plan=='yearly' else 'Monthly'} â {price}\n\nTransfer to `{CARD_NUMBER}` and send \ud83e\uddfe *Receipt*", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    else:
        price = "220 000 so'm" if plan=="yearly" else "20 000 so'm"
        await call.message.answer(f"\u2705 Tanlandi: {'Yillik' if plan=='yearly' else 'Oylik'} â {price}\n\nKartaga o'tkazing: `{CARD_NUMBER}`\n\n\ud83e\uddfe *Chek yuborish* tugmasini bosing", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    send_check_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🧾 To'lov chekini yuboring" if lang=="uz" else "🧾 Отправить чек" if lang=="ru" else "🧾 Send receipt",
            callback_data="vip_send_check"
        )]
    ])
    if lang=="ru":
        await call.message.answer("📤 Endi kartaga o'tkazma qiling va quyidagi tugmani bosib chekni yuboring:", reply_markup=send_check_kb)
    elif lang=="en":
        await call.message.answer("📤 Now make the transfer and press the button below to send your receipt:", reply_markup=send_check_kb)
    else:
        await call.message.answer("📤 Endi kartaga o'tkazma qiling va quyidagi tugmani bosib chekni yuboring:", reply_markup=send_check_kb)
    await state.set_state(PaymentState.waiting_receipt)
    await call.answer()


async def handle_check_start(message, user, lang, state):
    if lang=="ru": txt = "\ud83e\uddfe Prishhlite skrinshot cheka ob oplate:"
    elif lang=="en": txt = "\ud83e\uddfe Send a screenshot of your payment receipt:"
    else: txt = "\ud83e\uddfe To'lov chekini (skrinshotini) yuboring:"
    await message.answer(txt, reply_markup=ReplyKeyboardRemove())
    await state.set_state(PaymentState.waiting_receipt)

@dp.message(Command("chek"))
async def cmd_chek(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    lang = user.get("lang","uz") if user else "uz"
    await handle_check_start(message, user, lang, state)

@dp.message(PaymentState.waiting_receipt, F.photo)
async def handle_receipt(message: types.Message, state: FSMContext):
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang","uz") if user else "uz"
    photo_fid = message.photo[-1].file_id
    conn = get_conn()
    conn.execute("INSERT INTO payment_requests (telegram_id, photo_file_id) VALUES (?,?)", (tid, photo_fid))
    req_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    username = message.from_user.username or "---"
    name = message.from_user.first_name or "---"
    admin_txt = (
        f"\ud83d\udcb3 *Yangi to'lov so'rovi!*\n\n"
        f"\ud83d\udc64 Ism: {name}\n"
        f"\ud83d\udd16 Username: @{username}\n"
        f"\ud83c\udd94 ID: {tid}\n"
        f"\ud83d\udccb So'rov #{req_id}"
    )
    try:
        await bot.send_photo(
            ADMIN_ID, photo_fid,
            caption=admin_txt,
            parse_mode="Markdown",
            reply_markup=admin_approve_kb(tid, req_id)
        )
    except Exception as e:
        logging.error(f"Admin send error: {e}")
    if lang=="ru": ack = "\u2705 Chek admin ga yuborildi! Tasdiqlashni kuting."
    elif lang=="en": ack = "\u2705 Receipt sent to admin! Please wait for confirmation."
    else: ack = "\u2705 Chek adminga yuborildi! Tasdiqlashni kuting."
    await state.clear()
    await message.answer(ack, reply_markup=main_menu_kb(lang))

@dp.message(PaymentState.waiting_receipt)
async def receipt_not_photo(message: types.Message):
    user = get_user(message.from_user.id)
    lang = user.get("lang","uz") if user else "uz"
    if lang=="ru": await message.answer("\u274c Pozhaluysta, prishhlite foto cheka.")
    elif lang=="en": await message.answer("\u274c Please send a photo of the receipt.")
    else: await message.answer("\u274c Iltimos, chek rasmini yuboring.")


@dp.callback_query(F.data.startswith("admin_vip_"))
async def cb_admin_vip(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("\u274c Ruxsat yo'q!"); return
    parts  = call.data.split("_")
    user_id = int(parts[2])
    req_id  = int(parts[3])
    now = datetime.now()
    # Check if user selected yearly plan
    conn2 = get_conn()
    user_data = conn2.execute("SELECT telegram_id FROM users WHERE telegram_id=?", (user_id,)).fetchone()
    conn2.close()
    # Default 30 days; admin can see receipt amount to determine plan
    vip_days = 365  # Admin will see payment amount on receipt
    vip_end = (now + timedelta(days=vip_days)).isoformat()
    save_user(user_id, is_vip=1, vip_start=now.isoformat(), vip_end=vip_end)
    conn = get_conn()
    conn.execute("UPDATE payment_requests SET status='approved' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()
    user = get_user(user_id)
    lang = user.get("lang","uz") if user else "uz"
    if lang=="ru": msg = "\ud83c\udf89 Pozdravlyaem! Vasha VIP podpiska aktivirovana na 30 dney! \u2b50"
    elif lang=="en": msg = "\ud83c\udf89 Congratulations! Your VIP subscription is activated for 30 days! \u2b50"
    else: msg = "\ud83c\udf89 Tabriklaymiz! VIP obunangiz 30 kunga faollashtirildi! \u2b50"
    try:
        await bot.send_message(user_id, msg)
    except: pass
    await call.message.edit_caption(call.message.caption + "\n\n\u2705 VIP berildi!")
    await call.answer("\u2705 VIP berildi!")

@dp.callback_query(F.data.startswith("admin_reject_"))
async def cb_admin_reject(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("\u274c Ruxsat yo'q!"); return
    parts  = call.data.split("_")
    user_id = int(parts[2])
    req_id  = int(parts[3])
    conn = get_conn()
    conn.execute("UPDATE payment_requests SET status='rejected' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()
    user = get_user(user_id)
    lang = user.get("lang","uz") if user else "uz"
    if lang=="ru": msg = "\u274c Vash platyozh otkloyon. Svyazhites s @hattobiy."
    elif lang=="en": msg = "\u274c Your payment was rejected. Contact @hattobiy."
    else: msg = "\u274c To'lovingiz rad etildi. @hattobiy bilan bog'laning."
    try:
        await bot.send_message(user_id, msg)
    except: pass
    await call.message.edit_caption(call.message.caption + "\n\n\u274c Rad etildi!")
    await call.answer("\u274c Rad etildi!")


# ââ FOOD PHOTO ANALYSIS ââ
# Store pending analysis results temporarily

@dp.message(F.photo, StateFilter(default_state))
async def handle_food_photo(message: types.Message, state: FSMContext):
    tid  = message.from_user.id
    user = get_user(tid)
    if not user:
        await message.answer("Botdan foydalanish uchun /start buyrug'ini yuboring.")
        return
    lang = user.get("lang","uz")

    # Free trial: only photo analysis allowed
    if not is_vip_or_trial(user):
        if lang=="ru": await message.answer("\u23f0 Besplatnyy period zakonchlsya! Kupite VIP.")
        elif lang=="en": await message.answer("\u23f0 Free trial expired! Buy VIP.")
        else: await message.answer("\u23f0 Bepul muddat tugadi! VIP oling.")
        return

    if lang=="ru": await message.answer("\ud83d\udd0d Rasim tahlil qilinmoqda, iltimos kuting...")
    elif lang=="en": await message.answer("\ud83d\udd0d Analyzing image, please wait...")
    else: await message.answer("\ud83d\udd0d Rasm tahlil qilinmoqda, iltimos kuting...")

    try:
        photo = message.photo[-1]
        file  = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.read()
        meal_t = get_meal_type()

        if lang=="ru":
            prompt = (
                "Ty ekspert-dietolog i vizual'nyy analitik edy. VNIMATEL'NO izuchi eto foto i opredeliy REALISTICHNOYE kolichestvo gramm.\n"
                "VAZHNYE PRAVILA dlya opredeleniya gramm:\n"
                "- Chashka chaya/kofe = 200-250ml\n"
                "- Tarelka s edoy = smotriy na ee razmer i stepen' zapolnenosti\n"
                "- Lozhka sup/sos = 15-20ml, stolovaya lozhka = 20-25g\n"
                "- Kusok khleba = 25-35g\n"
                "- Yayco = 50-60g\n"
                "- Srednyaya porsiya plova = 300-400g\n"
                "- Burger = 150-250g zavisimost ot razm\n"
                "- NIKOGDA ne pishi 200g kak shablon â analiz kazhdyy raz dolzhen byt' unikalnym!\n\n"
                "Formt otvet:\n"
                "Blyudo: [tochnoye nazvanie]\n"
                "Gramm: [REALISTICHNOYE kolichestvo] g\n"
                "Kaloriya: [chislo] kkal\n"
                "Belki: [chislo] g\n"
                "Zhiry: [chislo] g\n"
                "Uglevody: [chislo] g\n"
                "Kommentariy: [kratkoe ob'yasneniye pochemu imenno takoye kolichestvo gramm]"
            )
        elif lang=="en":
            prompt = (
                "You are an expert dietitian and food visual analyst. CAREFULLY examine this photo and determine REALISTIC gram amount.\n"
                "IMPORTANT RULES for gram estimation:\n"
                "- Tea/coffee cup = 200-250ml\n"
                "- Plate: judge by plate size and how full it is\n"
                "- Tablespoon = 20-25g, teaspoon = 5-7g\n"
                "- Slice of bread = 25-35g\n"
                "- 1 egg = 50-60g\n"
                "- Average rice plov portion = 300-400g\n"
                "- Burger = 150-250g depending on size\n"
                "- NEVER default to 200g as a template â every analysis must reflect the actual image!\n\n"
                "Response format:\n"
                "Dish: [exact name]\n"
                "Grams: [REALISTIC amount] g\n"
                "Calories: [number] kcal\n"
                "Protein: [number] g\n"
                "Fat: [number] g\n"
                "Carbs: [number] g\n"
                "Note: [brief explanation of why this gram estimate]"
            )
        else:
            prompt = (
                "Sen mutaxassis diyetolog va ovqat vizual tahlilchisisan. Bu rasmni DIQQAT bilan o'rganib, REAL gramm miqdorini aniqlang.\n"
                "GRAMM ANIQLASH UCHUN MUHIM QOIDALAR:\n"
                "- Choy/qahva piyolasi = 200-250ml\n"
                "- Tarelkadagi ovqat: tarelka o'lchami va to'lganligiga qarab baho ber\n"
                "- Osh qoshiq = 20-25g, choy qoshig'i = 5-7g\n"
                "- Non bo'lagi = 25-35g\n"
                "- 1 ta tuxum = 50-60g\n"
                "- O'rtacha plov porsiyasi = 300-400g\n"
                "- Burger = 150-250g o'lchamiga qarab\n"
                "- HECH QACHON 200g ni shablon sifatida ishlatma â har tahlil rasmga asoslangan REAL son bo'lsin!\n"
                "- Agar rasm 40g ovqat ko'rsatsa, 40g de. Agar 350g bo'lsa, 350g de.\n\n"
                "Javob formati:\n"
                "Taom: [aniq nom]\n"
                "Gramm: [REAL miqdor] g\n"
                "Kaloriya: [son] kkal\n"
                "Oqsil: [son] g\n"
                "Yog': [son] g\n"
                "Uglevodlar: [son] g\n"
                "Izoh: [nega aynan shu gramm miqdori degan qisqacha tushuntirish]"
            )

        response = await asyncio.to_thread(gemini.models.generate_content,
            model="gemini-1.5-flash",
            contents=[
                genai_types.Content(
                    parts=[
                        genai_types.Part(text=prompt),
                        genai_types.Part(
                            inline_data=genai_types.Blob(
                                mime_type="image/jpeg",
                                data=image_data
                            )
                        )
                    ]
                )
            ]
        )
        result = response.text

        # Parse calories, BJU and food name from result
        cal = 0
        protein = 0
        fat = 0
        carbs = 0
        food_name = "Noma'lum taom"
        for line in result.split("\n"):
            if any(k in line.lower() for k in ["kaloriya","calories","ÐºÐ°Ð»Ð¾ÑÐ¸"]):
                import re
                nums = re.findall(r'\d+\.?\d*', line)
                if nums: cal = float(nums[0])
            if any(k in line.lower() for k in ["taom","dish","blyudo","bludo"]):
                parts = line.split(":")
                if len(parts) > 1: food_name = parts[1].strip()
            if any(k in line.lower() for k in ["oqsil","protein","belki"]):
                import re as _re
                nums = _re.findall(r'\d+\.?\d*', line)
                if nums: protein = float(nums[0])
            if any(k in line.lower() for k in ["yog","fat","zhiry"]):
                import re as _re
                nums = _re.findall(r'\d+\.?\d*', line)
                if nums: fat = float(nums[0])
            if any(k in line.lower() for k in ["uglevodlar","carbs","uglevody"]):
                import re as _re
                nums = _re.findall(r'\d+\.?\d*', line)
                if nums: carbs = float(nums[0])

        # Store pending
        import time
        pend_id = int(time.time() * 1000) % 1000000
        pending_food[pend_id] = {
            "tid": tid, "cal": cal, "food": food_name,
            "protein": protein, "fat": fat, "carbs": carbs,
            "meal_type": meal_t, "lang": lang
        }

        if lang=="ru": header = f"\ud83c\udf7d Rezul'tat analiza ({meal_t}):"
        elif lang=="en": header = f"\ud83c\udf7d Analysis result ({meal_t}):"
        else: header = f"\ud83c\udf7d Tahlil natijasi ({meal_label(meal_t, lang)}):"

        await message.answer(
            header + "\n\n" + result,
            reply_markup=photo_food_kb(lang, pend_id)
        )

    except Exception as e:
        logging.error(f"Photo analysis error: {e}")
        if lang=="ru": await message.answer("\u274c Oshibka analiza. Poprobuyte pozzhe.")
        elif lang=="en": await message.answer("\u274c Analysis error. Try again later.")
        else: await message.answer("\u274c Tahlil xatoligi. Keyinroq urinib ko'ring.")

@dp.callback_query(F.data.startswith("eat_"))
async def cb_eat(call: types.CallbackQuery):
    pend_id = int(call.data.split("_")[1])
    if pend_id not in pending_food:
        await call.answer("Vaqt o'tdi!"); return
    item = pending_food.pop(pend_id)
    tid  = item["tid"]
    lang = item["lang"]
    if call.from_user.id != tid:
        await call.answer("Bu siz uchun emas!"); return
    conn = get_conn()
    conn.execute(
        "INSERT INTO food_logs (telegram_id, food_name, calories, protein, fat, carbs, meal_type) VALUES (?,?,?,?,?,?,?)",
        (tid, item["food"], item["cal"], item.get("protein",0), item.get("fat",0), item.get("carbs",0), item["meal_type"])
    )
    conn.commit()
    conn.close()
    p = item.get('protein', 0); f2 = item.get('fat', 0); cb = item.get('carbs', 0)
    if lang=="ru": msg = f"✅ {item['food']} ({round(item['cal'])} kcal)\n🧬 Belki: {p:.0f}g | Zhiry: {f2:.0f}g | Uglevody: {cb:.0f}g"
    elif lang=="en": msg = f"✅ {item['food']} ({round(item['cal'])} kcal)\n🧬 Protein: {p:.0f}g | Fat: {f2:.0f}g | Carbs: {cb:.0f}g"
    else: msg = f"✅ {item['food']} ({round(item['cal'])} kkal)\n🧬 Oqsil: {p:.0f}g | Yog': {f2:.0f}g | Uglevod: {cb:.0f}g"
    await call.message.edit_reply_markup()
    await call.message.answer(msg)
    await call.answer()

@dp.callback_query(F.data.startswith("cancel_food_"))
async def cb_cancel_food(call: types.CallbackQuery):
    pend_id = int(call.data.split("_")[2])
    pending_food.pop(pend_id, None)
    await call.message.edit_reply_markup()
    await call.answer("Bekor qilindi")


# ââ ADMIN COMMANDS ââ
@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    vips  = conn.execute("SELECT COUNT(*),username FROM users WHERE is_vip=1 GROUP BY telegram_id").fetchall()
    free  = conn.execute("SELECT COUNT(*),username FROM users WHERE is_vip=0 GROUP BY telegram_id").fetchall()
    vip_list  = conn.execute("SELECT telegram_id, username, first_name FROM users WHERE is_vip=1").fetchall()
    free_list = conn.execute("SELECT telegram_id, username, first_name FROM users WHERE is_vip=0").fetchall()
    conn.close()
    txt = f"\ud83d\udcca *Bot statistikasi*\n\n"
    txt += f"\ud83d\udc65 Jami obunachlar: *{total}*\n\n"
    txt += f"\u2b50 VIP ({len(vip_list)} ta):\n"
    for u in vip_list[:30]:
        uname = f"@{u[1]}" if u[1] else u[2] or str(u[0])
        txt += f"  â¢ {uname}\n"
    txt += f"\n\ud83d\udcf6 Free ({len(free_list)} ta):\n"
    for u in free_list[:30]:
        uname = f"@{u[1]}" if u[1] else u[2] or str(u[0])
        txt += f"  â¢ {uname}\n"
    await message.answer(txt, parse_mode="Markdown")

@dp.message(Command("reklama"))
async def cmd_reklama(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("\ud83d\udce2 Reklama xabarini yuboring (matn, rasm yoki video):")
    await state.set_state(BroadcastState.message)

@dp.message(BroadcastState.message)
async def do_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear(); return
    conn = get_conn()
    users = conn.execute("SELECT telegram_id FROM users").fetchall()
    conn.close()
    ok = 0; fail = 0
    for (uid,) in users:
        try:
            await message.forward(uid)
            ok += 1
        except:
            fail += 1
    await state.clear()
    await message.answer(f"\u2705 Yuborildi: {ok}\n\u274c Xato: {fail}")


# ââ SMART REMINDERS & VIP EXPIRY WARNINGS ââ
async def send_meal_reminders():
    """Check if user logged food in current meal period, if not send reminder"""
    now = datetime.now(TZ)
    hour = now.hour
    # Nonushta: 8:00, Tushlik: 13:00, Kechki: 19:00
    meal_schedule = [
        (8, 11, "nonushta"),
        (13, 16, "tushlik"),
        (19, 22, "kechki"),
    ]
    current_meal = None
    for start_h, end_h, mtype in meal_schedule:
        if start_h <= hour < end_h:
            current_meal = mtype
            break
    if not current_meal:
        return

    conn = get_conn()
    users = conn.execute("SELECT telegram_id, lang FROM users").fetchall()
    today = now.strftime("%Y-%m-%d")
    for (uid, lang) in users:
        # Check if already logged for this meal today
        logged = conn.execute(
            "SELECT COUNT(*) FROM food_logs WHERE telegram_id=? AND date(logged_at)=? AND meal_type=?",
            (uid, today, current_meal)
        ).fetchone()[0]
        if logged == 0:
            ml = meal_label(current_meal, lang or "uz")
            if lang=="ru":
                msg = f"\u23f0 {ml} â vy eshchye ne zapisali edu! Zakrepite rezul'tat \ud83d\udcf8"
            elif lang=="en":
                msg = f"\u23f0 {ml} â you haven't logged food yet! Track your meal \ud83d\udcf8"
            else:
                msg = f"\u23f0 {ml} â hali ovqat kiritmadingiz! Natijangizni qayd eting \ud83d\udcf8"
            try:
                await bot.send_message(uid, msg)
            except: pass
    conn.close()

async def check_vip_expiry():
    """Warn users whose VIP expires in exactly 5 days"""
    conn = get_conn()
    vip_users = conn.execute(
        "SELECT telegram_id, lang, vip_end FROM users WHERE is_vip=1 AND vip_end IS NOT NULL"
    ).fetchall()
    conn.close()
    now = datetime.now()
    for (uid, lang, vip_end) in vip_users:
        try:
            end_dt = datetime.fromisoformat(vip_end)
            days_left = (end_dt - now).days
            if days_left == 5:
                if lang=="ru":
                    msg = f"\u26a0\ufe0f Vasha VIP podpiska istekaet cherez 5 dney! Prodlite cherez /vip"
                elif lang=="en":
                    msg = f"\u26a0\ufe0f Your VIP subscription expires in 5 days! Renew via /vip"
                else:
                    msg = f"\u26a0\ufe0f VIP obunangiz 5 kunda tugaydi! /vip orqali yangilang"
                await bot.send_message(uid, msg)
        except: pass

async def scheduler():
    """Background scheduler for reminders"""
    while True:
        try:
            now = datetime.now(TZ)
            # Check reminders at meal times: 8:00, 13:00, 19:00
            if now.minute == 0 and now.hour in [8, 13, 19]:
                await send_meal_reminders()
            # Check VIP expiry once per day at 10:00
            if now.hour == 10 and now.minute == 0:
                await check_vip_expiry()
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
        await asyncio.sleep(60)  # Check every minute


# ââ TEXT FOOD INPUT ââ
# Also handle text food descriptions for calorie analysis
# This is handled within the general text_router, but we need AI analysis for food text
# Users can just describe food in text and get calorie estimate

# ââ MAIN âââââââââââââââââââââââââââââââââââââââââââââââ
async def main():
    init_db()
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
