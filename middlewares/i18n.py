# middlewares/i18n.py — Localization middleware for aiogram 3.x
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

import database as db

# ─────────────────────────────────────────────────────────────────────────────
# Translation dictionaries — all 3 locales
# ─────────────────────────────────────────────────────────────────────────────
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ── O'zbek ────────────────────────────────────────────────────────────────
    "uz": {
        # Onboarding
        "choose_lang": "Tilni tanlang / Choose language / Выберите язык:",
        "lang_uz": "🇺🇿 O'zbekcha",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "welcome_intro": (
            "Assalomu alaykum, {name}! 👋\n\n"
            "Men — sizning shaxsiy AI Dietolog yordamchingizman 🥗\n"
            "Ovqatlanishingizni tahlil qilaman, kaloriyani hisoblayman va "
            "sog'lom hayot kechirishga yordam beraman.\n\n"
            "Keling, shaxsiy profilingizni yaratamiz!"
        ),
        "btn_start_analysis": "🚀 Shaxsiy tahlilni boshlash",
        "ask_gender": "Jinsingizni tanlang:",
        "gender_male": "👨 Erkak",
        "gender_female": "👩 Ayol",
        "ask_height": "📏 Bo'yingiz nechchi santimetr? (masalan: 170)",
        "ask_weight": "⚖️ Vazningiz necha kilogramm? (masalan: 70)",
        "height_err": "❌ Iltimos, 50 dan 250 gacha bo'lgan son kiriting.",
        "weight_err": "❌ Iltimos, 20 dan 300 gacha bo'lgan son kiriting.",
        "ask_goal": "🎯 Maqsadingizni tanlang:",
        "goal_lose": "🔥 Ozish",
        "goal_gain": "💪 Vazn olish",
        "goal_keep": "⚖️ Vaznni saqlash",
        "ask_activity": "🏃 Kunlik faollik darajasini tanlang:",
        "activity_low": "🚶 Kam faol",
        "activity_medium": "🚴 O'rta faol",
        "activity_high": "🏋️ Juda faol",
        "reg_done": (
            "🎉 Ajoyib! Profil yaratildi!\n\n"
            "🎁 Sovg'a sifatida sizga 3 kunlik BEPUL sinov taqdim etildi!\n\n"
            "Endi asosiy menyuga o'tamiz 👇"
        ),
        # Dashboard
        "dashboard": (
            "Xush kelibsiz, {name}! Bugun shaxsiy rejangizning {day}-kuni. 🔥\n\n"
            "📊 Bugungi real vaqt hisoboti:\n"
            "🍏 Jami yeyilgan kaloriya: {consumed} / {target} kkal\n"
            "💧 Ichilgan suv: [{water_bar}] {water_ml} ml / {water_goal} ml\n\n"
            "🕒 Ovqatlanish jurnali (Bugun):\n"
            "  • Nonushta: {breakfast} (06:00–10:00)\n"
            "  • Tushlik:  {lunch}    (11:00–14:00)\n"
            "  • Kechki:   {dinner}   (17:00–21:00)\n\n"
            "⏳ Hisob holati: {status}"
        ),
        "status_trial": "Bepul sinov (Qoldi: {days} kun)",
        "status_premium": "💎 VIP (Tugaydi: {until})",
        "status_expired": "⌛ Muddati tugadi — VIP oling!",
        # Buttons
        "btn_scan": "📸 Ovqatni Skaner Qilish",
        "btn_water": "💧 +1 Stakan Suv (0.3L)",
        "btn_ration": "📊 Kunlik Ratsion",
        "btn_reports": "📈 Davriy Hisobotlar",
        "btn_profile": "👤 Profilim",
        "btn_ai": "🤖 AI Dietolog",
        "btn_vip": "💎 VIP Obuna & Sovg'alar",
        # Scan
        "send_food_photo": "📸 Ovqat rasmini yuboring, tahlil qilaman:",
        "scanning": "🔍 Tahlil qilinmoqda...",
        "not_food": "❌ Rasmda ovqat ko'rinmadi. Iltimos, ovqat rasmini yuboring.",
        # Water
        "water_added": "💧 +1 stakan (300 ml) qo'shildi!\n💧 Bugun jami: {total} ml / {goal} ml",
        "water_goal_reached": "🎉 Kun suv normasiga erishdingiz!",
        # VIP / Paywall
        "locked_trial": "🔒 Bu funksiya sinov davrida mavjud emas.\n💎 VIP obunaga o'ting!",
        "locked_expired": "⌛ Sinov muddati tugadi!\n💎 VIP obunaga o'ting!",
        "vip_info": (
            "💎 VIP Obuna\n\n"
            "📅 Oylik — 20,000 so'm\n"
            "📆 Yillik — 220,000 so'm\n\n"
            "💳 Karta: {card}\n"
            "👤 Egasi: {holder}\n\n"
            "To'lovni amalga oshiring va chek rasmini yuboring. ✅"
        ),
        "btn_monthly": "📅 Oylik — 20,000 so'm",
        "btn_yearly": "📆 Yillik — 220,000 so'm",
        "btn_send_receipt": "🧾 Chek rasmini yuborish",
        "choose_plan": "💳 Tarifni tanlang:",
        "send_receipt_photo": "📸 Iltimos, to'lov cheki rasmini yuboring:",
        "receipt_sent": "✅ Chekingiz adminga yuborildi. Tez orada ko'rib chiqiladi!",
        "payment_approved": "🎉 To'lov tasdiqlandi! {days} kunlik VIP faollashtirildi!",
        "payment_rejected": "❌ To'lov rad etildi: {reason}\n\nQayta urinib ko'ring.",
        "reject_no_money": "💸 Pul tushmadi",
        "reject_bad_photo": "📸 Sifatsiz rasm",
        # Referral
        "referral_info": (
            "👥 Referal dasturi\n\n"
            "Sizning referal havolangiz:\n{link}\n\n"
            "Taklif qilinganlar: {count}/{required}\n"
            "3 ta do'stingizni taklif qiling — {bonus} kun VIP sovg'a!"
        ),
        # Profile
        "profile_info": (
            "👤 Profilingiz:\n\n"
            "📛 Ism: {name}\n"
            "⚧ Jins: {gender}\n"
            "📏 Bo'y: {height} sm\n"
            "⚖️ Vazn: {weight} kg\n"
            "🎯 Maqsad: {goal}\n"
            "🏃 Faollik: {activity}\n"
            "🔥 Kun norma: {target} kkal"
        ),
        "change_lang": "🌐 Tilni o'zgartirish",
        "lang_changed": "✅ Til o'zgartirildi!",
        # Reminders
        "reminder_breakfast": "🌅 Nonushta vaqti! Bugun nima edingiz? Rasmini yuboring 📸",
        "reminder_lunch": "☀️ Tushlik vaqti! Ovqatni yozing yoki rasmini yuboring 🍱",
        "reminder_dinner": "🌙 Kechki ovqat vaqti! Nima yedingiz? Rasm yuboring 🥗",
        "reminder_water": "💧 Suv iching! 2 soatdan beri suv ichmadingiz.",
        # AI Chat
        "ai_intro": "🤖 AI Dietolog bilan suhbat. Savolingizni yozing:",
        "ai_thinking": "🤔 Javob tayyorlanmoqda...",
        # Admin
        "admin_panel": (
            "👨‍💻 Admin Paneli\n\n"
            "👥 Jami foydalanuvchilar: {total}\n"
            "✅ Bugun faol: {today}\n"
            "💎 VIP foydalanuvchilar: {vip}\n"
            "💰 Taxminiy daromad: {revenue:,} so'm"
        ),
        "broadcast_prompt": "📢 Barcha foydalanuvchilarga xabar kiriting:",
        "broadcast_done": "✅ Xabar {count} foydalanuvchiga yuborildi.",
        "user_banned": "🚫 Foydalanuvchi bloklandi.",
        "user_unbanned": "✅ Foydalanuvchi blokdan chiqarildi.",
        "vip_granted": "✅ {user_id} ga {days} kun VIP berildi.",
        "not_admin": "❌ Siz admin emassiz.",
        "user_not_found": "❌ Foydalanuvchi topilmadi.",
        # Reports
        "daily_report": (
            "📊 Bugungi hisobot:\n\n"
            "🍏 Kaloriya: {consumed} / {target} kkal\n"
            "💧 Suv: {water} ml / {water_goal} ml\n\n"
            "🥗 Ovqatlar:\n{food_list}"
        ),
        "no_food_logged": "Bugun hech narsa yeyilmadi.",
        "meal_logged": "✅ {food} — {cal} kkal ({meal}) qo'shildi!",
    },

    # ── Русский ───────────────────────────────────────────────────────────────
    "ru": {
        "choose_lang": "Tilni tanlang / Choose language / Выберите язык:",
        "lang_uz": "🇺🇿 O'zbekcha",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "welcome_intro": (
            "Привет, {name}! 👋\n\n"
            "Я — ваш персональный AI Диетолог 🥗\n"
            "Анализирую ваше питание, считаю калории и помогаю "
            "вести здоровый образ жизни.\n\n"
            "Давайте создадим ваш личный профиль!"
        ),
        "btn_start_analysis": "🚀 Начать анализ",
        "ask_gender": "Выберите ваш пол:",
        "gender_male": "👨 Мужчина",
        "gender_female": "👩 Женщина",
        "ask_height": "📏 Ваш рост в сантиметрах? (например: 170)",
        "ask_weight": "⚖️ Ваш вес в килограммах? (например: 70)",
        "height_err": "❌ Пожалуйста, введите число от 50 до 250.",
        "weight_err": "❌ Пожалуйста, введите число от 20 до 300.",
        "ask_goal": "🎯 Выберите вашу цель:",
        "goal_lose": "🔥 Похудеть",
        "goal_gain": "💪 Набрать вес",
        "goal_keep": "⚖️ Поддержать вес",
        "ask_activity": "🏃 Выберите уровень активности:",
        "activity_low": "🚶 Малоактивный",
        "activity_medium": "🚴 Умеренно активный",
        "activity_high": "🏋️ Очень активный",
        "reg_done": (
            "🎉 Отлично! Профиль создан!\n\n"
            "🎁 В подарок вам предоставлен 3-дневный БЕСПЛАТНЫЙ пробный период!\n\n"
            "Переходим в главное меню 👇"
        ),
        "dashboard": (
            "Добро пожаловать, {name}! Сегодня {day}-й день вашей программы. 🔥\n\n"
            "📊 Текущий отчёт за сегодня:\n"
            "🍏 Всего потреблено калорий: {consumed} / {target} ккал\n"
            "💧 Выпито воды: [{water_bar}] {water_ml} мл / {water_goal} мл\n\n"
            "🕒 Дневник питания (Сегодня):\n"
            "  • Завтрак: {breakfast} (06:00–10:00)\n"
            "  • Обед:    {lunch}    (11:00–14:00)\n"
            "  • Ужин:    {dinner}   (17:00–21:00)\n\n"
            "⏳ Статус аккаунта: {status}"
        ),
        "status_trial": "Пробный период (Осталось: {days} дн.)",
        "status_premium": "💎 VIP (До: {until})",
        "status_expired": "⌛ Период истёк — купите VIP!",
        "btn_scan": "📸 Сканировать Еду",
        "btn_water": "💧 +1 Стакан Воды (0.3Л)",
        "btn_ration": "📊 Рацион на День",
        "btn_reports": "📈 Периодические Отчёты",
        "btn_profile": "👤 Мой Профиль",
        "btn_ai": "🤖 AI Диетолог",
        "btn_vip": "💎 VIP Подписка & Подарки",
        "send_food_photo": "📸 Отправьте фото еды, я проанализирую:",
        "scanning": "🔍 Анализируется...",
        "not_food": "❌ На фото не видно еды. Пожалуйста, пришлите фото еды.",
        "water_added": "💧 +1 стакан (300 мл) добавлен!\n💧 Сегодня итого: {total} мл / {goal} мл",
        "water_goal_reached": "🎉 Вы достигли дневной нормы воды!",
        "locked_trial": "🔒 Эта функция недоступна в пробном периоде.\n💎 Перейдите на VIP!",
        "locked_expired": "⌛ Пробный период истёк!\n💎 Купите VIP подписку!",
        "vip_info": (
            "💎 VIP Подписка\n\n"
            "📅 Месячная — 20,000 сум\n"
            "📆 Годовая  — 220,000 сум\n\n"
            "💳 Карта: {card}\n"
            "👤 Владелец: {holder}\n\n"
            "Совершите оплату и пришлите фото чека. ✅"
        ),
        "btn_monthly": "📅 Месячная — 20,000 сум",
        "btn_yearly": "📆 Годовая — 220,000 сум",
        "btn_send_receipt": "🧾 Отправить чек",
        "choose_plan": "💳 Выберите тариф:",
        "send_receipt_photo": "📸 Пожалуйста, отправьте фото чека оплаты:",
        "receipt_sent": "✅ Чек отправлен администратору. Ожидайте проверки!",
        "payment_approved": "🎉 Оплата подтверждена! VIP активирован на {days} дней!",
        "payment_rejected": "❌ Оплата отклонена: {reason}\n\nПопробуйте снова.",
        "reject_no_money": "💸 Деньги не поступили",
        "reject_bad_photo": "📸 Плохое качество фото",
        "referral_info": (
            "👥 Реферальная программа\n\n"
            "Ваша реферальная ссылка:\n{link}\n\n"
            "Приглашено: {count}/{required}\n"
            "Пригласите 3 друзей — получите {bonus} дней VIP в подарок!"
        ),
        "profile_info": (
            "👤 Ваш профиль:\n\n"
            "📛 Имя: {name}\n"
            "⚧ Пол: {gender}\n"
            "📏 Рост: {height} см\n"
            "⚖️ Вес: {weight} кг\n"
            "🎯 Цель: {goal}\n"
            "🏃 Активность: {activity}\n"
            "🔥 Норма: {target} ккал"
        ),
        "change_lang": "🌐 Изменить язык",
        "lang_changed": "✅ Язык изменён!",
        "reminder_breakfast": "🌅 Время завтрака! Что вы ели? Отправьте фото 📸",
        "reminder_lunch": "☀️ Время обеда! Запишите приём пищи 🍱",
        "reminder_dinner": "🌙 Время ужина! Что ели сегодня? Пришлите фото 🥗",
        "reminder_water": "💧 Выпейте воды! Вы не пили уже 2 часа.",
        "ai_intro": "🤖 Чат с AI Диетологом. Задайте ваш вопрос:",
        "ai_thinking": "🤔 Готовлю ответ...",
        "admin_panel": (
            "👨‍💻 Панель Администратора\n\n"
            "👥 Всего пользователей: {total}\n"
            "✅ Активных сегодня: {today}\n"
            "💎 VIP пользователей: {vip}\n"
            "💰 Прим. доход: {revenue:,} сум"
        ),
        "broadcast_prompt": "📢 Введите сообщение для всех пользователей:",
        "broadcast_done": "✅ Сообщение отправлено {count} пользователям.",
        "user_banned": "🚫 Пользователь заблокирован.",
        "user_unbanned": "✅ Пользователь разблокирован.",
        "vip_granted": "✅ Пользователю {user_id} выдано {days} дней VIP.",
        "not_admin": "❌ У вас нет прав администратора.",
        "user_not_found": "❌ Пользователь не найден.",
        "daily_report": (
            "📊 Отчёт за сегодня:\n\n"
            "🍏 Калории: {consumed} / {target} ккал\n"
            "💧 Вода: {water} мл / {water_goal} мл\n\n"
            "🥗 Приёмы пищи:\n{food_list}"
        ),
        "no_food_logged": "Сегодня ничего не записано.",
        "meal_logged": "✅ {food} — {cal} ккал ({meal}) добавлено!",
    },

    # ── English ────────────────────────────────────────────────────────────────
    "en": {
        "choose_lang": "Tilni tanlang / Choose language / Выберите язык:",
        "lang_uz": "🇺🇿 O'zbekcha",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "welcome_intro": (
            "Hello, {name}! 👋\n\n"
            "I'm your personal AI Dietitian assistant 🥗\n"
            "I analyze your meals, count calories and help you "
            "live a healthier life.\n\n"
            "Let's create your personal profile!"
        ),
        "btn_start_analysis": "🚀 Start Analysis",
        "ask_gender": "Choose your gender:",
        "gender_male": "👨 Male",
        "gender_female": "👩 Female",
        "ask_height": "📏 Your height in centimeters? (e.g. 170)",
        "ask_weight": "⚖️ Your weight in kilograms? (e.g. 70)",
        "height_err": "❌ Please enter a number between 50 and 250.",
        "weight_err": "❌ Please enter a number between 20 and 300.",
        "ask_goal": "🎯 Choose your goal:",
        "goal_lose": "🔥 Lose weight",
        "goal_gain": "💪 Gain weight",
        "goal_keep": "⚖️ Maintain weight",
        "ask_activity": "🏃 Select your activity level:",
        "activity_low": "🚶 Low active",
        "activity_medium": "🚴 Moderately active",
        "activity_high": "🏋️ Very active",
        "reg_done": (
            "🎉 Great! Profile created!\n\n"
            "🎁 As a gift you get a 3-day FREE trial!\n\n"
            "Let's go to the main menu 👇"
        ),
        "dashboard": (
            "Welcome, {name}! Today is Day {day} of your personal plan. 🔥\n\n"
            "📊 Today's Real-Time Report:\n"
            "🍏 Total Calories Eaten: {consumed} / {target} kcal\n"
            "💧 Water Intake: [{water_bar}] {water_ml} ml / {water_goal} ml\n\n"
            "🕒 Food Log (Today):\n"
            "  • Breakfast: {breakfast} (06:00–10:00)\n"
            "  • Lunch:     {lunch}    (11:00–14:00)\n"
            "  • Dinner:    {dinner}   (17:00–21:00)\n\n"
            "⏳ Account Status: {status}"
        ),
        "status_trial": "Free Trial (Left: {days} days)",
        "status_premium": "💎 VIP (Until: {until})",
        "status_expired": "⌛ Expired — get VIP!",
        "btn_scan": "📸 Scan My Food",
        "btn_water": "💧 +1 Glass of Water (0.3L)",
        "btn_ration": "📊 Daily Ration",
        "btn_reports": "📈 Periodic Reports",
        "btn_profile": "👤 My Profile",
        "btn_ai": "🤖 AI Dietitian",
        "btn_vip": "💎 VIP Subscription & Gifts",
        "send_food_photo": "📸 Send a photo of your food, I'll analyze it:",
        "scanning": "🔍 Analyzing...",
        "not_food": "❌ No food detected in the photo. Please send a food photo.",
        "water_added": "💧 +1 glass (300 ml) added!\n💧 Today total: {total} ml / {goal} ml",
        "water_goal_reached": "🎉 You reached your daily water goal!",
        "locked_trial": "🔒 This feature is not available during the trial.\n💎 Upgrade to VIP!",
        "locked_expired": "⌛ Trial expired!\n💎 Get a VIP subscription!",
        "vip_info": (
            "💎 VIP Subscription\n\n"
            "📅 Monthly — 20,000 UZS\n"
            "📆 Yearly  — 220,000 UZS\n\n"
            "💳 Card: {card}\n"
            "👤 Holder: {holder}\n\n"
            "Complete the payment and send a photo of the receipt. ✅"
        ),
        "btn_monthly": "📅 Monthly — 20,000 UZS",
        "btn_yearly": "📆 Yearly — 220,000 UZS",
        "btn_send_receipt": "🧾 Send Receipt",
        "choose_plan": "💳 Choose a plan:",
        "send_receipt_photo": "📸 Please send a photo of your payment receipt:",
        "receipt_sent": "✅ Receipt sent to admin. Please wait for confirmation!",
        "payment_approved": "🎉 Payment confirmed! VIP activated for {days} days!",
        "payment_rejected": "❌ Payment rejected: {reason}\n\nPlease try again.",
        "reject_no_money": "💸 Payment not received",
        "reject_bad_photo": "📸 Poor quality photo",
        "referral_info": (
            "👥 Referral Program\n\n"
            "Your referral link:\n{link}\n\n"
            "Referred: {count}/{required}\n"
            "Invite 3 friends — get {bonus} days VIP as a gift!"
        ),
        "profile_info": (
            "👤 Your Profile:\n\n"
            "📛 Name: {name}\n"
            "⚧ Gender: {gender}\n"
            "📏 Height: {height} cm\n"
            "⚖️ Weight: {weight} kg\n"
            "🎯 Goal: {goal}\n"
            "🏃 Activity: {activity}\n"
            "🔥 Daily target: {target} kcal"
        ),
        "change_lang": "🌐 Change Language",
        "lang_changed": "✅ Language changed!",
        "reminder_breakfast": "🌅 Breakfast time! What did you eat? Send a photo 📸",
        "reminder_lunch": "☀️ Lunch time! Log your meal 🍱",
        "reminder_dinner": "🌙 Dinner time! What did you eat? Send a photo 🥗",
        "reminder_water": "💧 Drink some water! You haven't had any in 2 hours.",
        "ai_intro": "🤖 Chat with AI Dietitian. Type your question:",
        "ai_thinking": "🤔 Preparing answer...",
        "admin_panel": (
            "👨‍💻 Admin Panel\n\n"
            "👥 Total users: {total}\n"
            "✅ Active today: {today}\n"
            "💎 VIP users: {vip}\n"
            "💰 Est. revenue: {revenue:,} UZS"
        ),
        "broadcast_prompt": "📢 Enter a message for all users:",
        "broadcast_done": "✅ Message sent to {count} users.",
        "user_banned": "🚫 User banned.",
        "user_unbanned": "✅ User unbanned.",
        "vip_granted": "✅ {user_id} granted {days} days of VIP.",
        "not_admin": "❌ You are not an admin.",
        "user_not_found": "❌ User not found.",
        "daily_report": (
            "📊 Today's Report:\n\n"
            "🍏 Calories: {consumed} / {target} kcal\n"
            "💧 Water: {water} ml / {water_goal} ml\n\n"
            "🥗 Meals:\n{food_list}"
        ),
        "no_food_logged": "Nothing logged today.",
        "meal_logged": "✅ {food} — {cal} kcal ({meal}) added!",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper: translate
# ─────────────────────────────────────────────────────────────────────────────
def _(lang: str, key: str, **kwargs: Any) -> str:
    """Return the localized string for *key* in *lang*, with optional format args."""
    lang = lang if lang in TRANSLATIONS else "uz"
    text = TRANSLATIONS[lang].get(key) or TRANSLATIONS["uz"].get(key) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────
class I18nMiddleware(BaseMiddleware):
    """
    Fetches the user's language from the database for every update and
    injects a bound `t(key, **kwargs)` helper into handler data so
    every handler can call `data["t"]("some_key")` without needing
    to know the language explicitly.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        lang = "uz"
        if user:
            db_user = await db.get_user(user.id)
            if db_user:
                lang = db_user.get("language", "uz")

        # Inject helpers
        data["lang"] = lang
        data["t"] = lambda key, **kw: _(lang, key, **kw)
        data["db_user"] = data.get("db_user")  # may be filled by other middlewares

        return await handler(event, data)
