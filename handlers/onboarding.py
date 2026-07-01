# handlers/onboarding.py — Registration FSM & Language Gate
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
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
from middlewares.i18n import _, TRANSLATIONS

router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# FSM States
# ─────────────────────────────────────────────────────────────────────────────
class Reg(StatesGroup):
    language  = State()
    gender    = State()
    height    = State()
    weight    = State()
    goal      = State()
    activity  = State()


# ─────────────────────────────────────────────────────────────────────────────
# Keyboards
# ─────────────────────────────────────────────────────────────────────────────
def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha",  callback_data="set_lang:uz"),
        InlineKeyboardButton(text="🇷🇺 Русский",    callback_data="set_lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English",    callback_data="set_lang:en"),
    ]])


def gender_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text=_( lang, "gender_male")),
            KeyboardButton(text=_(lang, "gender_female")),
        ]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def goal_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_(lang, "goal_lose"))],
            [KeyboardButton(text=_(lang, "goal_gain"))],
            [KeyboardButton(text=_(lang, "goal_keep"))],
        ],
        resize_keyboard=True, one_time_keyboard=True,
    )


def activity_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_(lang, "activity_low"))],
            [KeyboardButton(text=_(lang, "activity_medium"))],
            [KeyboardButton(text=_(lang, "activity_high"))],
        ],
        resize_keyboard=True, one_time_keyboard=True,
    )


def start_analysis_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=_(lang, "btn_start_analysis"), callback_data="begin_reg"),
    ]])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _goal_key(text: str) -> str:
    text = text.lower()
    if any(k in text for k in ("lose", "🔥", "ozish", "похуд")):
        return "lose"
    if any(k in text for k in ("gain", "💪", "qoshish", "набрать")):
        return "gain"
    return "keep"


def _activity_key(text: str) -> str:
    text = text.lower()
    if any(k in text for k in ("low", "kam", "малоактивный", "🚶")):
        return "low"
    if any(k in text for k in ("high", "juda", "очень", "🏋")):
        return "high"
    return "medium"


def _gender_key(text: str) -> str:
    text = text.lower()
    if any(k in text for k in ("female", "ayol", "женщ", "👩")):
        return "female"
    return "male"


# ─────────────────────────────────────────────────────────────────────────────
# /start — Language Gate
# ─────────────────────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id

    # Check for referral payload: /start ref_<code>
    args = message.text.split() if message.text else []
    ref_code = None
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
    await state.update_data(ref_code=ref_code)

    existing = await db.get_user(user_id)
    if existing and existing.get("language"):
        # Already registered — go to dashboard
        from handlers.dashboard import show_dashboard
        await show_dashboard(message, existing)
        return

    await message.answer(
        "Choose your language / Выберите язык / Tilni tanlang:",
        reply_markup=lang_keyboard(),
    )
    await state.set_state(Reg.language)


# ─────────────────────────────────────────────────────────────────────────────
# Language selection callback
# ─────────────────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("set_lang:"), Reg.language)
async def cb_set_lang(call: CallbackQuery, state: FSMContext) -> None:
    lang = call.data.split(":")[1]
    await state.update_data(language=lang)
    name = call.from_user.first_name or "Friend"
    await call.message.edit_text(
        _(lang, "welcome_intro", name=name),
        reply_markup=start_analysis_keyboard(lang),
    )
    await call.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Begin registration
# ─────────────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "begin_reg")
async def cb_begin_reg(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "uz")
    await call.message.answer(_(lang, "ask_gender"), reply_markup=gender_keyboard(lang))
    await state.set_state(Reg.gender)
    await call.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Gender
# ─────────────────────────────────────────────────────────────────────────────
@router.message(Reg.gender)
async def reg_gender(message: Message, state: FSMContext) -> None:
    data  = await state.get_data()
    lang  = data.get("language", "uz")
    await state.update_data(gender=_gender_key(message.text or ""))
    await message.answer(_(lang, "ask_height"), reply_markup=ReplyKeyboardRemove())
    await state.set_state(Reg.height)


# ─────────────────────────────────────────────────────────────────────────────
# Height
# ─────────────────────────────────────────────────────────────────────────────
@router.message(Reg.height)
async def reg_height(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "uz")
    try:
        h = float((message.text or "").replace(",", "."))
        assert 50 <= h <= 250
    except (ValueError, AssertionError):
        await message.answer(_(lang, "height_err"))
        return
    await state.update_data(height=h)
    await message.answer(_(lang, "ask_weight"))
    await state.set_state(Reg.weight)


# ─────────────────────────────────────────────────────────────────────────────
# Weight
# ─────────────────────────────────────────────────────────────────────────────
@router.message(Reg.weight)
async def reg_weight(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "uz")
    try:
        w = float((message.text or "").replace(",", "."))
        assert 20 <= w <= 300
    except (ValueError, AssertionError):
        await message.answer(_(lang, "weight_err"))
        return
    await state.update_data(weight=w)
    await message.answer(_(lang, "ask_goal"), reply_markup=goal_keyboard(lang))
    await state.set_state(Reg.goal)


# ─────────────────────────────────────────────────────────────────────────────
# Goal
# ─────────────────────────────────────────────────────────────────────────────
@router.message(Reg.goal)
async def reg_goal(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "uz")
    await state.update_data(goal=_goal_key(message.text or ""))
    await message.answer(_(lang, "ask_activity"), reply_markup=activity_keyboard(lang))
    await state.set_state(Reg.activity)


# ─────────────────────────────────────────────────────────────────────────────
# Activity — finalize registration
# ─────────────────────────────────────────────────────────────────────────────
@router.message(Reg.activity)
async def reg_activity(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "uz")
    user_id = message.from_user.id
    activity = _activity_key(message.text or "")

    # Build user record
    user_fields = {
        "username":   message.from_user.username,
        "first_name": message.from_user.first_name,
        "language":   lang,
        "gender":     data.get("gender", "male"),
        "height":     data.get("height"),
        "weight":     data.get("weight"),
        "goal":       data.get("goal", "keep"),
        "activity":   activity,
    }
    await db.upsert_user(user_id, **user_fields)

    # Handle referral
    ref_code = data.get("ref_code")
    if ref_code:
        referrer = await db.get_user_by_ref_code(ref_code)
        if referrer and referrer["user_id"] != user_id:
            await db.record_referral(referrer["user_id"], user_id)
            await db.upsert_user(user_id, referred_by=referrer["user_id"])
            # Check if referral milestone reached
            count = await db.count_referrals(referrer["user_id"])
            if count > 0 and count % config.REFERRAL_REQUIRED == 0:
                await db.grant_premium(referrer["user_id"], config.REFERRAL_BONUS_DAYS)

    # Compute target calories
    user = await db.get_user(user_id)
    target_cal = db.calc_target_calories(user)
    await db.upsert_user(user_id, target_cal=target_cal)

    await state.clear()
    await message.answer(_(lang, "reg_done"), reply_markup=ReplyKeyboardRemove())

    # Show dashboard
    from handlers.dashboard import show_dashboard
    user = await db.get_user(user_id)
    await show_dashboard(message, user)


# ─────────────────────────────────────────────────────────────────────────────
# Language change (from profile)
# ─────────────────────────────────────────────────────────────────────────────
class ChangeLang(StatesGroup):
    choosing = State()


@router.callback_query(F.data == "change_language")
async def cb_change_language(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.answer(
        "Choose your language / Выберите язык / Tilni tanlang:",
        reply_markup=lang_keyboard(),
    )
    await state.set_state(ChangeLang.choosing)
    await call.answer()


@router.callback_query(F.data.startswith("set_lang:"), ChangeLang.choosing)
async def cb_change_lang_confirm(call: CallbackQuery, state: FSMContext) -> None:
    lang = call.data.split(":")[1]
    await db.upsert_user(call.from_user.id, language=lang)
    await state.clear()
    await call.message.answer(_(lang, "lang_changed"))
    user = await db.get_user(call.from_user.id)
    from handlers.dashboard import show_dashboard
    await show_dashboard(call.message, user)
    await call.answer()
