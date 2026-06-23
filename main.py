import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

# Render platformasida Environment Variables qismiga BOT_TOKEN qo'shgan bo'lsangiz, 
# u quyidagi qator orqali avtomatik o'qiladi.
BOT_TOKEN = os.getenv("BOT_TOKEN", "8748222511:AAGYGj8EG2LA0BfUwEd_76v0oXjLIwkjTjA")

# Bot va Dispetcher (dp) obyektlarini yaratamiz
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Sizing rasmlarni qabul qiladigan kodingiz
@dp.message(F.photo)
async def handle_photo(message: Message):
    # Bu yerda rasmni qayta ishlaydigan kodingiz (AI funksiyalari) bo'ladi
    await message.reply("Rasm qabul qilindi! Taomni tahlil qilyapman...")

# Botni ishga tushirish funksiyasi
async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
