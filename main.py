# -*- coding: utf-8 -*-
# ┌──────────────────────────────────────────────────────────────────────────┐
# │  taom-ai-bot  ·  main.py  ·  Production-ready rewrite                    │
# │  Changes vs original:                                                    │
# │    1. CARD_NUMBER updated                                                │
# │    2. APScheduler (AsyncIOScheduler) integrated                          │
# │    3. 3× daily meal reminders (08:00 / 13:00 / 19:00 Tashkent)          │
# │    4. Strict VIP-only gates on 6 features                                │
# │    5. _analyze_food_photo: locale fix, async Gemini, safe regex parsing  │
# │    6. Weight progress graph via matplotlib (VIP profile)                 │
# │    7. Handler registration order: specific before generic                │
# └──────────────────────────────────────────────────────────────────────────┘

import asyncio
import io
import logging
import os
import re
import time
import sqlite3
from datetime import datetime, timedelta

import pytz
import matplotlib                          # ── NEW (feature 6)
matplotlib.use("Agg")                      # ── NEW: non-interactive backend
import matplotlib.pyplot as plt            # ── NEW

from apscheduler.schedulers.asyncio import AsyncIOScheduler   # ── NEW (feature 2)
from apscheduler.triggers.cron import CronTrigger             # ── NEW

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    BufferedInputFile,                     # ── NEW: for sending matplotlib charts
)

from google import genai
from google.genai import types as genai_types

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN",      "YOUR_BOT_TOKEN")
ADMIN_ID   = int(os.environ.get("ADMIN_ID",   "956947665"))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
DB_PATH    = "taom_ai.db"
TRIAL_DAYS = 3
CARD_NUMBER = "986004011458909NN"           # ── CHANGED (action 1)
TZ = pytz.timezone("Asia/Tashkent")

logging.basicConfig(level=logging.INFO)
bot    = Bot(token=BOT_TOKEN)
dp     = Dispatcher(storage=MemoryStorage())
gemini = genai.Client(api_key=GEMINI_KEY)

# ── TRANSLATIONS ──────────────────────────────────────────────────────────────
LANGS = {
    "uz": {
        "welcome":          "Assalomu alaykum! Men sizning diyeta yordamchingizman 🥗\nTanishishni boshlasak, yoshingizdan boshlaymiz. Yoshingiz nechida?",
        "ask_height":       "Bo'yingiz qancha? (masalan: 170 sm) 📏",
        "ask_weight":       "Vazningiz qancha? (masalan: 60 kg) ⚖️",
        "ask_goal":         "Maqsadingizni tanlang:",
        "ask_gender":       "Jinsingizni tanlang:",
        "goal_lose":        "Ozish 🔥",
        "goal_gain":        "Vazn qo'shish 💪",
        "goal_keep":        "Vaznni ushlab qolish ⚖️",
        "gender_male":      "Erkak 🧑",
        "gender_female":    "Ayol 👩",
        "ask_activity":     "Kunlik faollik darajangizni tanlang: 🏃",
        "activity_low":     "🚶 Kam faol (kam harakatlanaman)",
        "activity_medium":  "🚴 O'rta faol (ba'zan sport qilaman)",
        "activity_high":    "🏋️ Juda faol (muntazam sport)",
        "reg_done":         "🎉 Ro'yxatdan o'tganingiz bilan tabriklayman!\n\nBu botda siz o'z vazningizni oson nazorat qila olasiz 📊\n\nSovg'a sifatida sizga 3 kunlik FREE TRIAL taqdim qilamiz 🎁\n\nTanishtiruv tugadi — endi botdagi imkoniyatlarga o'tamiz!",
        "main_menu":        "Asosiy menyu 🏠",
        "btn_ration":       "🍽 Kunlik ratsion",
        "btn_food_today":   "📋 Bugungi ovqatlar",
        "btn_food_week":    "📅 Haftalik hisobot",
        "btn_food_month":   "📆 Oylik hisobot",
        "btn_water":        "💧 Suv ratsioni",
        "btn_ai":           "🤖 AI Diyetolog",
        "btn_profile":      "👤 Profilim",
        "btn_vip":          "⭐ VIP sotib olish",
        "btn_check":        "🧾 Chek yuborish",
        "btn_photo_food":   "📸 Ovqat rasmi",
        "paywall":          "⚠️ Bu imkoniyat faqat VIP obunachilar uchun mavjud!\n\n📸 Bepul foydalanish uchun ovqat rasmini yuboring.\nBarcha funksiyalar uchun VIP obuna oling ⬇️",
        "vip_only":         "Bu imkoniyat faqat VIP tarifda mavjud! ⭐\n\nVIP sotib olish uchun /vip buyrug'ini yuboring.",
        "trial_expired":    "Bepul sinov muddati tugadi! ⏰\n\nBarcha imkoniyatlardan foydalanish uchun VIP obuna oling.",
        "lang_select":      "Tilni tanlang / Choose language / Выберите язык:",
        # ── NEW: reminder texts ─────────────────────────────────────────────
        "reminder_breakfast": "🌅 Nonushta qilish vaqti bo'ldi! Bugun nima edingiz? Rasmini yuboring. 📸",
        "reminder_lunch":     "☀️ Tushlik vaqti keldi! Ovqatingizni yozing yoki rasmini yuboring. 🍱",
        "reminder_dinner":    "🌙 Kechki ovqat vaqti! Bugun nima yedingiz? Rasmini yuboring. 🥗",
    },
    "ru": {
        "welcome":          "Ассалому алейкум! Я ваш диетический помощник 🥗\nДавайте познакомимся. Сколько вам лет?",
        "ask_height":       "Какой у вас рост? (например: 170 см) 📏",
        "ask_weight":       "Какой у вас вес? (например: 60 кг) ⚖️",
        "ask_goal":         "Выберите вашу цель:",
        "ask_gender":       "Выберите ваш пол:",
        "goal_lose":        "Похудеть 🔥",
        "goal_gain":        "Набрать вес 💪",
        "goal_keep":        "Поддержать вес ⚖️",
        "gender_male":      "Мужчина 🧑",
        "gender_female":    "Женщина 👩",
        "ask_activity":     "Выберите уровень активности: 🏃",
        "activity_low":     "🚶 Малоактивный (мало движения)",
        "activity_medium":  "🚴 Умеренно активный (иногда спорт)",
        "activity_high":    "🏋️ Очень активный (регулярный спорт)",
        "reg_done":         "🎉 Поздравляю с регистрацией!\n\nВ этом боте вы легко можете контролировать свой вес 📊\n\nВ подарок предоставляем 3-дневный FREE TRIAL 🎁\n\nЗнакомство завершено — переходим к возможностям бота!",
        "main_menu":        "Главное меню 🏠",
        "btn_ration":       "🍽 Дневной рацион",
        "btn_food_today":   "📋 Еда за сегодня",
        "btn_food_week":    "📅 Недельный отчёт",
        "btn_food_month":   "📆 Месячный отчёт",
        "btn_water":        "💧 Водный рацион",
        "btn_ai":           "🤖 AI Диетолог",
        "btn_profile":      "👤 Мой профиль",
        "btn_vip":          "⭐ Купить VIP",
        "btn_check":        "🧾 Отправить чек",
        "btn_photo_food":   "📸 Фото еды",
        "paywall":          "⚠️ Эта функция доступна только VIP пользователям!\n\n📸 Бесплатно можно отправить фото еды.\nДля всех функций купите VIP ⬇️",
        "vip_only":         "Эта функция доступна только в VIP тарифе! ⭐\n\nДля покупки VIP отправьте /vip.",
        "trial_expired":    "Бесплатный пробный период закончился! ⏰\n\nКупите VIP подписку для доступа ко всем функциям.",
        "lang_select":      "Tilni tanlang / Choose language / Выберите язык:",
        # ── NEW: reminder texts ─────────────────────────────────────────────
        "reminder_breakfast": "🌅 Время завтрака! Что вы сегодня ели? Отправьте фото! 📸",
        "reminder_lunch":     "☀️ Время обеда! Запишите приём пищи или пришлите фото. 🍱",
        "reminder_dinner":    "🌙 Время ужина! Что вы сегодня ели? Пришлите фото! 🥗",
    },
    "en": {
        "welcome":          "Hello! I am your diet assistant 🥗\nLet's get acquainted. How old are you?",
        "ask_height":       "What is your height? (e.g. 170 cm) 📏",
        "ask_weight":       "What is your weight? (e.g. 60 kg) ⚖️",
        "ask_goal":         "Choose your goal:",
        "ask_gender":       "Choose your gender:",
        "goal_lose":        "Lose weight 🔥",
        "goal_gain":        "Gain weight 💪",
        "goal_keep":        "Maintain weight ⚖️",
        "gender_male":      "Male 🧑",
        "gender_female":    "Female 👩",
        "ask_activity":     "Select your activity level: 🏃",
        "activity_low":     "🚶 Low active (little movement)",
        "activity_medium":  "🚴 Moderately active (some exercise)",
        "activity_high":    "🏋️ Very active (regular exercise)",
        "reg_done":         "🎉 Congratulations on registering!\n\nIn this bot you can easily track your weight 📊\n\nAs a gift we give you a 3-day FREE TRIAL 🎁\n\nIntro done — let's move to bot features!",
        "main_menu":        "Main menu 🏠",
        "btn_ration":       "🍽 Daily Ration",
        "btn_food_today":   "📋 Today's food",
        "btn_food_week":    "📅 Weekly report",
        "btn_food_month":   "📆 Monthly report",
        "btn_water":        "💧 Water ration",
        "btn_ai":           "🤖 AI Dietologist",
        "btn_profile":      "👤 My profile",
        "btn_vip":          "⭐ Buy VIP",
        "btn_check":        "🧾 Send receipt",
        "btn_photo_food":   "📸 Food photo",
        "paywall":          "⚠️ This feature is VIP-only!\n\n📸 Free users can send food photos.\nBuy VIP for all features ⬇️",
        "vip_only":         "This feature is only available in VIP! ⭐\n\nSend /vip to purchase.",
        "trial_expired":    "Free trial expired! ⏰\n\nBuy VIP subscription to access all features.",
        "lang_select":      "Tilni tanlang / Choose language / Выберите язык:",
        # ── NEW: reminder texts ─────────────────────────────────────────────
        "reminder_breakfast": "🌅 Breakfast time! What did you eat today? Send a photo! 📸",
        "reminder_lunch":     "☀️ Lunch time! Log your meal or send a photo. 🍱",
        "reminder_dinner":    "🌙 Dinner time! What did you eat today? Send a photo! 🥗",
    },
}

def t(user_lang: str, key: str, **kwargs) -> str:
    lang = user_lang if user_lang in LANGS else "uz"
    text = LANGS[lang].get(key, LANGS["uz"].get(key, key))
    return text.format(**kwargs) if kwargs else text

# ── DATABASE ──────────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id   INTEGER PRIMARY KEY,
            username      TEXT,
            first_name    TEXT,
            lang          TEXT    DEFAULT 'uz',
            age           INTEGER,
            gender        TEXT,
            activity      TEXT    DEFAULT 'medium',
            height        REAL,
            weight        REAL,
            target        TEXT,
            calories_goal REAL,
            trial_start   TEXT,
            is_vip        INTEGER DEFAULT 0,
            vip_start     TEXT,
            vip_end       TEXT
        );
        CREATE TABLE IF NOT EXISTS food_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            food_name   TEXT,
            calories    REAL,
            protein     REAL DEFAULT 0,
            fat         REAL DEFAULT 0,
            carbs       REAL DEFAULT 0,
            meal_type   TEXT,
            logged_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS water_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            amount_ml   INTEGER DEFAULT 250,
            logged_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payment_requests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER,
            plan         TEXT,
            photo_file_id TEXT,
            status       TEXT DEFAULT 'pending',
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS weight_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            weight      REAL,
            logged_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    # Safe migrations for existing databases
    for col in [
        "ALTER TABLE food_logs ADD COLUMN protein REAL DEFAULT 0",
        "ALTER TABLE food_logs ADD COLUMN fat     REAL DEFAULT 0",
        "ALTER TABLE food_logs ADD COLUMN carbs   REAL DEFAULT 0",
        "ALTER TABLE payment_requests ADD COLUMN plan TEXT",
    ]:
        try:
            conn.execute(col)
            conn.commit()
        except Exception:
            pass
    conn.close()

def get_user(tid: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def save_user(tid: int, **kwargs) -> None:
    conn = get_conn()
    exists = conn.execute(
        "SELECT telegram_id FROM users WHERE telegram_id=?", (tid,)
    ).fetchone()
    if exists:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [tid]
        conn.execute(f"UPDATE users SET {sets} WHERE telegram_id=?", vals)
    else:
        kwargs["telegram_id"] = tid
        cols = ", ".join(kwargs.keys())
        phs  = ", ".join("?" * len(kwargs))
        conn.execute(
            f"INSERT INTO users ({cols}) VALUES ({phs})", list(kwargs.values())
        )
    conn.commit()
    conn.close()

def get_all_active_users() -> list[dict]:
    """Return every registered user (used by the reminder scheduler)."""  # ── NEW
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── SUBSCRIPTION HELPERS ──────────────────────────────────────────────────────
def is_vip(user: dict | None) -> bool:
    """True ONLY for confirmed VIP users — trial does NOT count."""
    return bool(user and user.get("is_vip"))

def is_vip_or_trial(user: dict | None) -> bool:
    """True for VIP or users within the 3-day free trial window."""
    if not user:
        return False
    if user.get("is_vip"):
        return True
    ts = user.get("trial_start")
    if ts:
        start = datetime.fromisoformat(ts)
        return datetime.now() < start + timedelta(days=TRIAL_DAYS)
    return False

def get_trial_remaining(user: dict) -> int:
    ts = user.get("trial_start")
    if not ts:
        return 0
    start = datetime.fromisoformat(ts)
    remaining = (start + timedelta(days=TRIAL_DAYS) - datetime.now()).days
    return max(0, remaining)

# ── NUTRITION / CALORIE HELPERS ───────────────────────────────────────────────
def calc_calories_goal(user: dict) -> int:
    try:
        w      = float(user.get("weight",   70))
        h      = float(user.get("height",  170))
        a      = int(user.get("age",        30))
        g      = user.get("gender",       "male")
        target = user.get("target",       "keep")
        activity = user.get("activity", "medium")

        if any(k in g.lower() for k in ("male", "erkak", "мужчина")):
            bmr = 10 * w + 6.25 * h - 5 * a + 5
        else:
            bmr = 10 * w + 6.25 * h - 5 * a - 161

        act_map = {"low": 1.2, "medium": 1.55, "high": 1.725}
        tdee    = bmr * act_map.get(activity, 1.55)

        if any(k in target.lower() for k in ("lose", "ozish", "похуд")):
            return round(tdee - 500)
        elif any(k in target.lower() for k in ("gain", "qoshish", "набрать")):
            return round(tdee + 500)
        else:
            return round(tdee)
    except Exception:
        return 2000

def get_meal_type() -> str:
    now = datetime.now(TZ).hour
    if  6 <= now < 11: return "nonushta"
    if 11 <= now < 16: return "tushlik"
    if 16 <= now < 21: return "kechki"
    return "kechasi"

def meal_label(mt: str, lang: str = "uz") -> str:
    mapping = {
        "uz": {"nonushta": "🌅 Nonushta",    "tushlik": "☀️ Tushlik",
               "kechki":   "🌙 Kechki ovqat","kechasi": "🌃 Kechasi"},
        "ru": {"nonushta": "🌅 Завтрак",      "tushlik": "☀️ Обед",
               "kechki":   "🌙 Ужин",         "kechasi": "🌃 Ночь"},
        "en": {"nonushta": "🌅 Breakfast",    "tushlik": "☀️ Lunch",
               "kechki":   "🌙 Dinner",       "kechasi": "🌃 Night"},
    }
    return mapping.get(lang, mapping["uz"]).get(mt, mt)

def get_user_lang(tid: int) -> str:
    u = get_user(tid)
    return u.get("lang", "uz") if u else "uz"

# ── FSM STATE GROUPS ──────────────────────────────────────────────────────────
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
    choosing_plan   = State()
    waiting_receipt = State()

class AIChat(StatesGroup):
    chatting = State()

class BroadcastState(StatesGroup):
    message = State()

# ── KEYBOARDS ──────────────────────────────────────────────────────────────────
def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbek",  callback_data="lang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
    ]])

def goal_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "goal_lose"))],
            [KeyboardButton(text=t(lang, "goal_gain"))],
            [KeyboardButton(text=t(lang, "goal_keep"))],
        ],
        resize_keyboard=True, one_time_keyboard=True,
    )

def gender_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text=t(lang, "gender_male")),
            KeyboardButton(text=t(lang, "gender_female")),
        ]],
        resize_keyboard=True, one_time_keyboard=True,
    )

def activity_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "activity_low"))],
            [KeyboardButton(text=t(lang, "activity_medium"))],
            [KeyboardButton(text=t(lang, "activity_high"))],
        ],
        resize_keyboard=True, one_time_keyboard=True,
    )

def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_ration")),     KeyboardButton(text=t(lang, "btn_water"))],
            [KeyboardButton(text=t(lang, "btn_food_today")), KeyboardButton(text=t(lang, "btn_food_week"))],
            [KeyboardButton(text=t(lang, "btn_food_month")), KeyboardButton(text=t(lang, "btn_ai"))],
            [KeyboardButton(text=t(lang, "btn_profile")),    KeyboardButton(text=t(lang, "btn_vip"))],
            [KeyboardButton(text=t(lang, "btn_photo_food"))],
        ],
        resize_keyboard=True,
    )

def photo_food_kb(lang: str, pending_id: int) -> InlineKeyboardMarkup:
    labels = {
        "uz": ("Yeyman 😋",   "Bekor ❌"),
        "ru": ("Съем 😋",     "Отмена ❌"),
        "en": ("I'll eat 😋", "Cancel ❌"),
    }
    eat, cancel = labels.get(lang, labels["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=eat,    callback_data=f"eat_{pending_id}"),
        InlineKeyboardButton(text=cancel, callback_data=f"cancel_food_{pending_id}"),
    ]])

def vip_plans_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Oylik — 20,000 so'm",    callback_data="vip_plan_monthly")],
        [InlineKeyboardButton(text="📆 Yillik — 220,000 so'm",  callback_data="vip_plan_yearly")],
    ])

def admin_vip_kb(user_id: int, req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ VIP qilish", callback_data=f"admin_approve_{user_id}_{req_id}"),
        InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"admin_reject_{user_id}_{req_id}"),
    ]])

def profile_kb(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "uz": ("👤 Men haqimda", "💳 Obunam haqida", "✏️ Men o'zgardim", "🏠 Orqaga"),
        "ru": ("👤 Обо мне",     "💳 О подписке",    "✏️ Я изменился",   "🏠 Назад"),
        "en": ("👤 About me",    "💳 Subscription",  "✏️ I changed",     "🏠 Back"),
    }
    a, b, c, d = labels.get(lang, labels["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a, callback_data="prof_info"),
         InlineKeyboardButton(text=b, callback_data="prof_sub")],
        [InlineKeyboardButton(text=c, callback_data="prof_edit")],
        [InlineKeyboardButton(text=d, callback_data="prof_back")],
    ])

def edit_profile_kb(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "uz": [("📏 Bo'y",     "edit_height"), ("⚖️ Vazn",    "edit_weight"),
               ("🎂 Yosh",     "edit_age"),    ("🎯 Maqsad",  "edit_target"),
               ("🏃 Faollik",  "edit_activity"),("🔙 Orqaga", "prof_back")],
        "ru": [("📏 Рост",     "edit_height"), ("⚖️ Вес",     "edit_weight"),
               ("🎂 Возраст",  "edit_age"),    ("🎯 Цель",    "edit_target"),
               ("🏃 Активность","edit_activity"),("🔙 Назад", "prof_back")],
        "en": [("📏 Height",   "edit_height"), ("⚖️ Weight",  "edit_weight"),
               ("🎂 Age",      "edit_age"),    ("🎯 Goal",    "edit_target"),
               ("🏃 Activity", "edit_activity"),("🔙 Back",   "prof_back")],
    }
    rows = [[InlineKeyboardButton(text=b[0], callback_data=b[1])]
            for b in labels.get(lang, labels["uz"])]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def water_kb(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "uz": ("✅ Ichdim 💧", "📊 Bugungi suv"),
        "ru": ("✅ Выпил 💧",  "📊 Вода за сегодня"),
        "en": ("✅ Drank 💧",  "📊 Today water"),
    }
    a, b = labels.get(lang, labels["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a, callback_data="water_drank")],
        [InlineKeyboardButton(text=b, callback_data="water_today")],
    ])

# ── IN-MEMORY PENDING FOOD STORE ──────────────────────────────────────────────
pending_food: dict[int, dict] = {}

# ══════════════════════════════════════════════════════════════════════════════
#  ── NEW (feature 3): 3× DAILY MEAL REMINDERS ────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
async def send_meal_reminder(meal_key: str) -> None:
    """
    Scheduled coroutine — called at 08:00, 13:00, 19:00 Tashkent time.
    Fetches every registered user and sends a localized reminder.
    meal_key: "reminder_breakfast" | "reminder_lunch" | "reminder_dinner"
    """
    users = get_all_active_users()
    logging.info(f"[Reminder] {meal_key} — sending to {len(users)} users")
    for user in users:
        tid  = user.get("telegram_id")
        lang = user.get("lang", "uz")
        try:
            await bot.send_message(tid, t(lang, meal_key))
            await asyncio.sleep(0.05)   # rate-limit guard
        except Exception as exc:
            logging.warning(f"[Reminder] Could not send to {tid}: {exc}")


def setup_scheduler() -> AsyncIOScheduler:
    """Configure and return a scheduler with 3 daily reminder jobs."""  # ── NEW
    scheduler = AsyncIOScheduler(timezone=TZ)

    # 08:00 — Breakfast
    scheduler.add_job(
        send_meal_reminder,
        trigger=CronTrigger(hour=8, minute=0, timezone=TZ),
        args=["reminder_breakfast"],
        id="breakfast_reminder",
        replace_existing=True,
    )
    # 13:00 — Lunch
    scheduler.add_job(
        send_meal_reminder,
        trigger=CronTrigger(hour=13, minute=0, timezone=TZ),
        args=["reminder_lunch"],
        id="lunch_reminder",
        replace_existing=True,
    )
    # 19:00 — Dinner
    scheduler.add_job(
        send_meal_reminder,
        trigger=CronTrigger(hour=19, minute=0, timezone=TZ),
        args=["reminder_dinner"],
        id="dinner_reminder",
        replace_existing=True,
    )
    return scheduler

# ══════════════════════════════════════════════════════════════════════════════
#  ── NEW (feature 6): WEIGHT PROGRESS GRAPH helper ────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
def build_weight_chart(tid: int, lang: str) -> io.BytesIO | None:
    """
    Query the last 30 weight_logs for `tid` and produce a clean matplotlib
    line chart.  Returns a BytesIO PNG buffer, or None if < 2 data points.
    """
    conn = get_conn()
    rows = conn.execute(
        """SELECT date(logged_at) AS d, AVG(weight) AS w
           FROM weight_logs
           WHERE telegram_id=?
           ORDER BY logged_at DESC
           LIMIT 30""",
        (tid,),
    ).fetchall()
    conn.close()

    if len(rows) < 2:
        return None

    # Reverse to chronological order
    rows   = list(reversed(rows))
    dates  = [r["d"] for r in rows]
    weights = [r["w"] for r in rows]

    titles = {
        "uz": "Vaznning o'zgarishi (kg)",
        "ru": "Изменение веса (кг)",
        "en": "Weight Progress (kg)",
    }
    y_labels = {"uz": "Vazn (kg)", "ru": "Вес (кг)", "en": "Weight (kg)"}

    fig, ax = plt.subplots(figsize=(9, 4), dpi=120)
    ax.plot(dates, weights, marker="o", linewidth=2.2,
            color="#4CAF50", markerfacecolor="#fff", markeredgecolor="#4CAF50",
            markeredgewidth=2)
    ax.fill_between(dates, weights, alpha=0.12, color="#4CAF50")
    ax.set_title(titles.get(lang, titles["uz"]), fontsize=13, pad=10)
    ax.set_ylabel(y_labels.get(lang, y_labels["uz"]))
    ax.tick_params(axis="x", rotation=35, labelsize=7)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf

# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — registration order: FSM states → specific callbacks → generics
# ══════════════════════════════════════════════════════════════════════════════

# ── /start ────────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(LANGS["uz"]["lang_select"], reply_markup=lang_kb())
    await state.set_state(Reg.lang)

# ── /menu ─────────────────────────────────────────────────────────────────────
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang", "uz") if user else "uz"
    await message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))

# ── /vip ──────────────────────────────────────────────────────────────────────
@dp.message(Command("vip"))
async def cmd_vip(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    tid  = message.from_user.id
    user = get_user(tid)
    lang = user.get("lang", "uz") if user else "uz"
    
    await _show_vip_plans(message, lang, state)

# ── REGISTRATION FSM — language (inline, Reg.lang) ───────────────────────────
@dp.callback_query(F.data.startswith("lang_"), StateFilter(Reg.lang))
async def cb_lang(call: types.CallbackQuery, state: FSMContext) -> None:
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text(t(lang, "welcome"))
    await state.set_state(Reg.age)
    await call.answer()

@dp.message(StateFilter(Reg.lang))
async def reg_lang_text(message: types.Message, state: FSMContext) -> None:
    await message.answer(LANGS["uz"]["lang_select"], reply_markup=lang_kb())

# ── REGISTRATION FSM — age ────────────────────────────────────────────────────
@dp.message(StateFilter(Reg.age))
async def reg_age(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "uz")
    try:
        age = int(
