import asyncio
import logging
import os
import sqlite3
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from google import genai
from google.genai import types as genai_types

# --- CONFIG ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DB_PATH = "taom_ai.db"
TRIAL_DAYS = 3

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# --- DATABASE & HELPERS ---
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, age INTEGER, gender TEXT, height REAL, weight REAL, target TEXT, registered_at TEXT, trial_start TEXT, is_premium INTEGER DEFAULT 0, scan_count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS food_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, food_name TEXT, calories REAL, protein REAL, fat REAL, carbs REAL, logged_at TEXT);
        CREATE TABLE IF NOT EXISTS payment_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, photo_file_id TEXT, status TEXT DEFAULT 'pending', requested_at TEXT);
    """)
    conn.commit()
    conn.close()

# --- FSM ---
class Registration(StatesGroup):
    age = State(); gender = State(); height = State(); weight = State(); target = State()

class PaymentState(StatesGroup):
    waiting_receipt = State()

# --- HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Xush kelibsiz! Yoshingizni kiriting:")
    await state.set_state(Registration.age)

@dp.message(Registration.age)
async def reg_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol")]], resize_keyboard=True)
    await message.answer("Jinsingizni tanlang:", reply_markup=kb)
    await state.set_state(Registration.gender)

@dp.message(Registration.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await message.answer("Bo'yingizni kiriting (sm):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.height)

@dp.message(Registration.height)
async def reg_height(message: types.Message, state: FSMContext):
    await state.update_data(height=message.text)
    await message.answer("Vazningizni kiriting (kg):")
    await state.set_state(Registration.weight)

@dp.message(Registration.weight)
async def reg_weight(message: types.Message, state: FSMContext):
    await state.update_data(weight=message.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Vazn yo'qotish"), KeyboardButton(text="Vazn olish"), KeyboardButton(text="Vazn saqlash")]], resize_keyboard=True)
    await message.answer("Maqsadingizni tanlang:", reply_markup=kb)
    await state.set_state(Registration.target)

@dp.message(Registration.target)
async def reg_target(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # Bazaga saqlash logikasi shu yerda bo'ladi...
    await state.clear()
    await message.answer("Ro'yxatdan o'tdingiz!")

@dp.message(F.photo, PaymentState.waiting_receipt)
async def handle_receipt(message: types.Message, state: FSMContext):
    await message.answer("Chek qabul qilindi.")
    await state.clear()

@dp.message(F.photo)
async def handle_food_photo(message: types.Message):
    try:
        await message.answer("🔍 Rasm tahlil qilinmoqda, iltimos kuting...")
        
        # Rasmning eng katta versiyasini olish
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_path = file.file_path
        
        # Rasmni yuklab olish
        file_bytes = await bot.download_file(file_path)
        image_data = file_bytes.read()
        
        # Gemini API orqali tahlil qilish
        import base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        prompt = """Bu rasmda ko'rsatilgan ovqatni tahlil qilib, quyidagi ma'lumotlarni bering:
1. Ovqat nomi
2. Taxminiy kaloriya miqdori (kcal)
3. Oqsil (g)
4. Yog' (g)
5. Uglevodlar (g)

Javobni quyidagi formatda bering:
🍽 Ovqat: [nom]
🔥 Kaloriya: [miqdor] kcal
💪 Oqsil: [miqdor] g
🧈 Yog': [miqdor] g
🍞 Uglevodlar: [miqdor] g"""
        
        response = gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ]
        )
        
        result_text = response.text
        await message.answer(result_text)
        
    except Exception as e:
        logging.error(f"Rasm tahlilida xatolik: {e}")
        await message.answer("❌ Rasm tahlil qilishda hatolik yuz berdi. Qaytadan urinib ko'ring.")
# --- MAIN ---
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
