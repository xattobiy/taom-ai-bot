# handlers/dashboard.py — Main workspace, food scanner, water, AI chat, VIP paywall
import io
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

import config
import database as db
from middlewares.i18n import _
from services.gemini import analyze_food_photo, chat_with_dietitian

router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# FSM States
# ─────────────────────────────────────────────────────────────────────────────
class ScanState(StatesGroup):
    waiting_photo = State()

class PayState(StatesGroup):
    choosing_plan  = State()
    waiting_receipt = State()

class AIState(StatesGroup):
    chatting = State()


# ─────────────────────────────────────────────────────────────────────────────
# Keyboard builders
# ─────────────────────────────────────────────────────────────────────────────
def main_kb(lang: str) -> ReplyKeyboardMarkup:
    """Full feature keyboard — shown to premium / trial users."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_(lang, "btn_scan")),   KeyboardButton(text=_(lang, "btn_water"))],
            [KeyboardButton(text=_(lang, "btn_ration")), KeyboardButton(text=_(lang, "btn_reports"))],
            [KeyboardButton(text=_(lang, "btn_profile")),KeyboardButton(text=_(lang, "btn_ai"))],
            [KeyboardButton(text=_(lang, "btn_vip"))],
        ],
        resize_keyboard=True,
    )


def locked_kb(lang: str) -> InlineKeyboardMarkup:
    """Paywall keyboard — shown after trial expires."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_(lang, "btn_monthly"), callback_data="vip_plan:monthly")],
        [InlineKeyboardButton(text=_(lang, "btn_yearly"),  callback_data="vip_plan:yearly")],
    ])


def vip_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_(lang, "btn_monthly"), callback_data="vip_plan:monthly")],
        [InlineKeyboardButton(text=_(lang, "btn_yearly"),  callback_data="vip_plan:yearly")],
    ])


def profile_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_(lang, "change_lang"), callback_data="change_language")],
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Water progress bar
# ─────────────────────────────────────────────────────────────────────────────
def _water_bar(ml: int, goal: int = config.WATER_GOAL_ML, size: int = 10) -> str:
    ratio = min(ml / goal, 1.0)
    filled = round(ratio * size)
    return "🟦" * filled + "⬜" * (size - filled)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard builder
# ─────────────────────────────────────────────────────────────────────────────
async def show_dashboard(message: Message, user: dict) -> None:
    lang    = user.get("language", "uz")
    user_id = user["user_id"]

    consumed = await db.get_today_calories(user_id)
    target   = user.get("target_cal") or db.calc_target_calories(user)
    water_ml = await db.get_today_water(user_id)

    # Day number
    ts = user.get("trial_start")
    if ts:
        day = (datetime.utcnow() - datetime.fromisoformat(ts)).days + 1
    else:
        day = 1

    # Meal status
    async def meal_status(mtype: str) -> str:
        done = await db.has_meal_today(user_id, mtype)
        return "✅" if done else "❌"

    breakfast = await meal_status("breakfast")
    lunch     = await meal_status("lunch")
    dinner    = await meal_status("dinner")

    # Account status
    if db.is_premium_active(user):
        pu = user.get("premium_until", "")
        status_text = _(lang, "status_premium", until=pu[:10] if pu else "∞")
    elif db.is_trial_active(user):
        days_left = db.trial_days_left(user)
        status_text = _(lang, "status_trial", days=days_left)
    else:
        status_text = _(lang, "status_expired")

    text = _(
        lang, "dashboard",
        name=user.get("first_name") or "User",
        day=day,
        consumed=round(consumed),
        target=round(target),
        water_bar=_water_bar(water_ml),
        water_ml=water_ml,
        water_goal=config.WATER_GOAL_ML,
        breakfast=breakfast,
        lunch=lunch,
        dinner=dinner,
        status=status_text,
    )

    if db.has_access(user):
        await message.answer(text, reply_markup=main_kb(lang))
    else:
        # Hard lock — strip keyboard, show paywall
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        await message.answer(
            _(lang, "vip_info",
              card=config.PAYMENT_CARD,
              holder=config.PAYMENT_HOLDER),
            reply_markup=locked_kb(lang),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Access guard decorator
# ─────────────────────────────────────────────────────────────────────────────
async def _require_access(message: Message, user: dict, full: bool = True) -> bool:
    """
    full=True  → requires premium OR active trial
    full=False → only the two free-trial actions are allowed
    Returns True if access is granted.
    """
    lang = user.get("language", "uz")
    if db.is_premium_active(user):
        return True
    if db.is_trial_active(user):
        return True  # trial grants everything for now per PRD spec for free funcs
    # Expired
    await message.answer(
        _(lang, "locked_expired"),
        reply_markup=locked_kb(lang),
    )
    return False


# ─────────────────────────────────────────────────────────────────────────────
# /menu command — show dashboard
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.text == "/menu")
async def cmd_menu(message: Message) -> None:
    user = await db.get_user(message.from_user.id)
    if user:
        await show_dashboard(message, user)


# ─────────────────────────────────────────────────────────────────────────────
# Food Scanner
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.func(lambda m: m.text and any(
    m.text == _(lang, "btn_scan") for lang in ("uz", "ru", "en")
)))
async def btn_scan(message: Message, state: FSMContext) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    lang = user.get("language", "uz")
    # Food scanner is available during trial too
    if not db.has_access(user):
        await message.answer(_(lang, "locked_expired"), reply_markup=locked_kb(lang))
        return
    await message.answer(_(lang, "send_food_photo"))
    await state.set_state(ScanState.waiting_photo)


@router.message(ScanState.waiting_photo, F.photo)
async def receive_food_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        await state.clear()
        return
    lang = user.get("language", "uz")
    await message.answer(_(lang, "scanning"))
    await state.clear()

    # Download photo
    photo = message.photo[-1]
    file  = await bot.get_file(photo.file_id)
    data  = await bot.download_file(file.file_path)
    img_bytes = data.read() if hasattr(data, "read") else bytes(data)

    # Analyze
    result = await analyze_food_photo(img_bytes, user_lang=lang)

    if not result.is_food:
        await message.answer(_(lang, "not_food"))
        return

    # Determine meal type
    hour = datetime.utcnow().hour + 5  # Tashkent offset
    if 6 <= hour < 11:
        meal = "breakfast"
    elif 11 <= hour < 16:
        meal = "lunch"
    elif 16 <= hour < 21:
        meal = "dinner"
    else:
        meal = "other"

    await db.log_food(
        user_id=message.from_user.id,
        food_desc=result.description,
        calories=result.calories,
        protein=result.protein,
        fat=result.fat,
        carbs=result.carbs,
        meal_type=meal,
    )

    text = _(lang, "meal_logged",
             food=result.description,
             cal=round(result.calories),
             meal=meal)
    text += f"\n\n📋 {result.raw_text}"
    await message.answer(text[:4000])


# ─────────────────────────────────────────────────────────────────────────────
# Water
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.func(lambda m: m.text and any(
    m.text == _(lang, "btn_water") for lang in ("uz", "ru", "en")
)))
async def btn_water(message: Message) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    lang = user.get("language", "uz")
    if not db.has_access(user):
        await message.answer(_(lang, "locked_expired"), reply_markup=locked_kb(lang))
        return
    await db.log_water(message.from_user.id, config.WATER_GLASS_ML)
    total = await db.get_today_water(message.from_user.id)
    await message.answer(_(lang, "water_added",
                           total=total,
                           goal=config.WATER_GOAL_ML))
    if total >= config.WATER_GOAL_ML:
        await message.answer(_(lang, "water_goal_reached"))


# ─────────────────────────────────────────────────────────────────────────────
# Daily Ration
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.func(lambda m: m.text and any(
    m.text == _(lang, "btn_ration") for lang in ("uz", "ru", "en")
)))
async def btn_ration(message: Message) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    lang = user.get("language", "uz")
    if not await _require_access(message, user):
        return
    logs = await db.get_today_food_logs(message.from_user.id)
    if not logs:
        food_list = _(lang, "no_food_logged")
    else:
        food_list = "\n".join(
            f"  • {r['food_desc']} — {round(r['calories'])} kkal" for r in logs
        )
    consumed = sum(r["calories"] for r in logs)
    target   = user.get("target_cal") or db.calc_target_calories(user)
    water    = await db.get_today_water(message.from_user.id)
    await message.answer(_(lang, "daily_report",
                            consumed=round(consumed),
                            target=round(target),
                            water=water,
                            water_goal=config.WATER_GOAL_ML,
                            food_list=food_list))


# ─────────────────────────────────────────────────────────────────────────────
# Reports (VIP only)
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.func(lambda m: m.text and any(
    m.text == _(lang, "btn_reports") for lang in ("uz", "ru", "en")
)))
async def btn_reports(message: Message) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    lang = user.get("language", "uz")
    if not db.is_premium_active(user):
        if db.is_trial_active(user):
            await message.answer(_(lang, "locked_trial"))
        else:
            await message.answer(_(lang, "locked_expired"), reply_markup=locked_kb(lang))
        return
    # Simple weekly summary
    logs = await db.get_today_food_logs(message.from_user.id)
    await message.answer("📈 Reports feature — coming soon with detailed weekly charts!")


# ─────────────────────────────────────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.func(lambda m: m.text and any(
    m.text == _(lang, "btn_profile") for lang in ("uz", "ru", "en")
)))
async def btn_profile(message: Message) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    lang = user.get("language", "uz")
    if not await _require_access(message, user):
        return

    goal_map = {
        "lose": {"uz": "Ozish", "ru": "Похудеть", "en": "Lose weight"},
        "gain": {"uz": "Vazn olish", "ru": "Набрать вес", "en": "Gain weight"},
        "keep": {"uz": "Vaznni saqlash", "ru": "Поддержать", "en": "Maintain"},
    }
    act_map = {
        "low":    {"uz": "Kam faol",   "ru": "Малоактивный", "en": "Low"},
        "medium": {"uz": "O'rta faol", "ru": "Умеренный",    "en": "Medium"},
        "high":   {"uz": "Juda faol",  "ru": "Высокий",      "en": "High"},
    }
    gender_map = {
        "male":   {"uz": "Erkak",  "ru": "Мужчина", "en": "Male"},
        "female": {"uz": "Ayol",   "ru": "Женщина", "en": "Female"},
    }

    goal_str   = goal_map.get(user.get("goal", "keep"), {}).get(lang, "—")
    act_str    = act_map.get(user.get("activity", "medium"), {}).get(lang, "—")
    gender_str = gender_map.get(user.get("gender", "male"), {}).get(lang, "—")
    target     = user.get("target_cal") or db.calc_target_calories(user)

    await message.answer(
        _(lang, "profile_info",
          name=user.get("first_name") or "—",
          gender=gender_str,
          height=user.get("height") or "—",
          weight=user.get("weight") or "—",
          goal=goal_str,
          activity=act_str,
          target=round(target)),
        reply_markup=profile_keyboard(lang),
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI Dietitian Chat
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.func(lambda m: m.text and any(
    m.text == _(lang, "btn_ai") for lang in ("uz", "ru", "en")
)))
async def btn_ai(message: Message, state: FSMContext) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    lang = user.get("language", "uz")
    if not db.is_premium_active(user):
        if db.is_trial_active(user):
            await message.answer(_(lang, "locked_trial"))
        else:
            await message.answer(_(lang, "locked_expired"), reply_markup=locked_kb(lang))
        return
    await message.answer(_(lang, "ai_intro"))
    await state.set_state(AIState.chatting)
    await state.update_data(history=[])


@router.message(AIState.chatting, F.text)
async def ai_chat_message(message: Message, state: FSMContext) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        await state.clear()
        return
    lang = user.get("language", "uz")
    if message.text and message.text.startswith("/"):
        await state.clear()
        return

    await message.answer(_(lang, "ai_thinking"))
    data    = await state.get_data()
    history = data.get("history", [])

    resp = await chat_with_dietitian(message.text, user_lang=lang, history=history)

    # Update history
    history.append({"role": "user",  "parts": [{"text": message.text}]})
    history.append({"role": "model", "parts": [{"text": resp.text}]})
    await state.update_data(history=history[-10:])

    await message.answer(resp.text[:4000])


# ─────────────────────────────────────────────────────────────────────────────
# VIP Subscription / Paywall
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.func(lambda m: m.text and any(
    m.text == _(lang, "btn_vip") for lang in ("uz", "ru", "en")
)))
async def btn_vip(message: Message, state: FSMContext) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    lang = user.get("language", "uz")
    # Show referral info too
    ref_code = user.get("ref_code", "")
    bot_username = (await message.bot.me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{ref_code}"
    ref_count = await db.count_referrals(message.from_user.id)

    vip_text = _(lang, "vip_info",
                  card=config.PAYMENT_CARD,
                  holder=config.PAYMENT_HOLDER)
    ref_text = _(lang, "referral_info",
                  link=ref_link,
                  count=ref_count,
                  required=config.REFERRAL_REQUIRED,
                  bonus=config.REFERRAL_BONUS_DAYS)

    await message.answer(vip_text, reply_markup=vip_keyboard(lang))
    await message.answer(ref_text)
    await state.set_state(PayState.choosing_plan)


@router.callback_query(F.data.startswith("vip_plan:"))
async def cb_vip_plan(call: CallbackQuery, state: FSMContext) -> None:
    plan = call.data.split(":")[1]  # monthly | yearly
    user = await db.get_user(call.from_user.id)
    if not user:
        await call.answer()
        return
    lang = user.get("language", "uz")
    await state.update_data(vip_plan=plan)
    await call.message.answer(_(lang, "send_receipt_photo"))
    await state.set_state(PayState.waiting_receipt)
    await call.answer()


@router.message(PayState.waiting_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        await state.clear()
        return
    lang = user.get("language", "uz")
    data = await state.get_data()
    plan = data.get("vip_plan", "monthly")
    await state.clear()

    photo_id = message.photo[-1].file_id
    req_id   = await db.create_payment_request(message.from_user.id, plan, photo_id)

    await message.answer(_(lang, "receipt_sent"))

    # Forward to admin group
    plan_label = "Oylik (1 oy)" if plan == "monthly" else "Yillik (1 yil)"
    price = config.PRICE_MONTHLY if plan == "monthly" else config.PRICE_YEARLY

    admin_text = (
        f"📥 <b>YANGI TO'LOV KELDI!</b>\n\n"
        f"👤 Foydalanuvchi: {user.get('first_name')} (@{user.get('username') or '—'})\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"📅 Tarif: {plan_label} — {price:,} UZS\n"
        f"🕒 Vaqti: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
        f"🔑 Req ID: {req_id}"
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ 1 Oylikni Tasdiqlash" if plan == "monthly" else "✅ Yillikni Tasdiqlash",
            callback_data=f"admin_approve:{message.from_user.id}:{req_id}:{plan}",
        ),
        InlineKeyboardButton(
            text="❌ Rad etish",
            callback_data=f"admin_reject:{message.from_user.id}:{req_id}",
        ),
    ]])
    try:
        await bot.send_photo(
            config.ADMIN_GROUP_ID,
            photo=photo_id,
            caption=admin_text,
            reply_markup=admin_kb,
            parse_mode="HTML",
        )
    except Exception:
        await bot.send_message(
            config.SUPER_ADMIN_ID,
            admin_text + f"\n\n[Photo: {photo_id}]",
            reply_markup=admin_kb,
            parse_mode="HTML",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Catch-all for expired users (any text/photo triggers paywall)
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.text | F.photo)
async def catch_all(message: Message, state: FSMContext) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        # Not registered — redirect to /start
        await message.answer("Please send /start to register.")
        return
    lang = user.get("language", "uz")
    if db.has_access(user):
        await show_dashboard(message, user)
    else:
        # Full paywall mode
        await message.answer(_(lang, "locked_expired"), reply_markup=ReplyKeyboardRemove())
        await message.answer(
            _(lang, "vip_info",
              card=config.PAYMENT_CARD,
              holder=config.PAYMENT_HOLDER),
            reply_markup=locked_kb(lang),
        )
