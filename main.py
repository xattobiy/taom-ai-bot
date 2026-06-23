from aiogram import F
from PIL import Image
import io

@dp.message(F.photo)
async def handle_photo(message: Message):
    # Telegram'dan rasm yuklab olish
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    
    # Rasm bytes holatiga o‘tkaziladi
    buffer = io.BytesIO()
    await bot.download_file(file_path, buffer)
    buffer.seek(0)
    
    # Rasm ochiladi
    img = Image.open(buffer)
    
    # BU YERDA: Gemini API orqali tahlil qilish kodini qo‘shishingiz kerak
    # Hozircha oddiy javob qaytaramiz:
    await message.answer("Rasm qabul qilindi, tahlil qilinmoqda...")
