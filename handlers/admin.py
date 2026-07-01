# handlers/admin.py — Super Admin private control panel
import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import config
import database as db
from middlewares.i18n import _

router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# FSM
# ─────────────────────────────────────────────────────────────────────────────
class BroadcastState(StatesGroup):
    waiting_message = State()

class TargetUserState(StatesGroup):
    waiting_id = State()
    action     = State()


# ─────────────────────────────────────────────────────────────────────────────
# Guard
# ─────────────────────────────────────────────────────────────────────────────
def _is_super_admin(user_id: int) -> bool:
    return user_id == config.SUPER_ADMIN_ID


# ─────────────────────────────────────────────────────────────────────────────
# /admin command — cockpit
# ─────────────────────────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not _is_super_admin(message.from_user.id):
        await message.answer("❌ Access denied.")
        return

    total   = await db.count_users()
    today   = await db.count_active_today()
    vip     = await db.count_premium_users()
    revenue = vip * config.PRICE_MONTHLY  # rough estimate

    text = _(
        "uz", "admin_panel",
        total=total, today=today, vip=vip, revenue=revenue
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Maqsadli Reklama",    callback_data="admin_broadcast"),
            InlineKeyboardButton(text="👤 ID orqali Boshqarish", callback_data="admin_manage_user"),
        ],
        [
            InlineKeyboardButton(text="📊 Tizim Holati",  callback_data="admin_stats"),
            InlineKeyboardButton(text="📋 So'nggi Cheklar", callback_data="admin_last_payments"),
        ],
    ])
    await message.answer(text, reply_markup=kb, parse_mode=None)


# ─────────────────────────────────────────────────────────────────────────────
# Stats refresh
# ─────────────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery) -> None:
    if not _is_super_admin(call.from_user.id):
        await call.answer("❌ Access denied.", show_alert=True)
        return
    total   = await db.count_users()
    today   = await db.count_active_today()
    vip     = await db.count_premium_users()
    revenue = vip * config.PRICE_MONTHLY
    text = _(
        "uz", "admin_panel",
        total=total, today=today, vip=vip, revenue=revenue
    )
    await call.message.edit_text(text)
    await call.answer("Yangilandi ✅")


# ─────────────────────────────────────────────────────────────────────────────
# Broadcast
# ─────────────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_broadcast")
async def cb_broadcast_start(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_super_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    await call.message.answer("📢 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:")
    await state.set_state(BroadcastState.waiting_message)
    await call.answer()


@router.message(BroadcastState.waiting_message, F.text)
async def do_broadcast(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_super_admin(message.from_user.id):
        await state.clear()
        return
    await state.clear()
    users = await db.get_all_users()
    count = 0
    for u in users:
        try:
            await bot.send_message(u["user_id"], message.text)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"✅ Xabar {count} foydalanuvchiga yuborildi.")


# ─────────────────────────────────────────────────────────────────────────────
# Manage user by ID
# ─────────────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_manage_user")
async def cb_manage_user(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_super_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    await call.message.answer("👤 Boshqarmoqchi bo'lgan foydalanuvchi ID sini kiriting:")
    await state.set_state(TargetUserState.waiting_id)
    await call.answer()


@router.message(TargetUserState.waiting_id, F.text)
async def target_user_id(message: Message, state: FSMContext) -> None:
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID format.")
        return

    user = await db.get_user(uid)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        await state.clear()
        return

    await state.update_data(target_uid=uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 VIP berish", callback_data=f"mgr_vip:{uid}"),
            InlineKeyboardButton(text="🚫 Ban",         callback_data=f"mgr_ban:{uid}"),
        ],
        [
            InlineKeyboardButton(text="✅ Bandan chiqarish", callback_data=f"mgr_unban:{uid}"),
        ],
    ])
    uname = user.get("username") or "—"
    fname = user.get("first_name") or "—"
    lang_u = user.get("language", "uz")
    is_vip = "✅" if db.is_premium_active(user) else "❌"
    banned = "🚫" if user.get("is_banned") else "✅"
    await message.answer(
        f"👤 <b>{fname}</b> (@{uname})\n"
        f"🆔 {uid}\n"
        f"🌐 Lang: {lang_u}\n"
        f"💎 VIP: {is_vip}\n"
        f"🔒 Ban: {banned}",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await state.clear()


@router.callback_query(F.data.startswith("mgr_vip:"))
async def mgr_vip(call: CallbackQuery, bot: Bot) -> None:
    if not _is_super_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    await db.grant_premium(uid, 30)
    user = await db.get_user(uid)
    lang = user.get("language", "uz") if user else "uz"
    await bot.send_message(uid, _(lang, "payment_approved", days=30))
    await call.answer("✅ 30 kun VIP berildi!", show_alert=True)


@router.callback_query(F.data.startswith("mgr_ban:"))
async def mgr_ban(call: CallbackQuery) -> None:
    if not _is_super_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    await db.ban_user(uid)
    await call.answer(f"🚫 {uid} bloklandi!", show_alert=True)


@router.callback_query(F.data.startswith("mgr_unban:"))
async def mgr_unban(call: CallbackQuery) -> None:
    if not _is_super_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    await db.unban_user(uid)
    await call.answer(f"✅ {uid} blokdan chiqarildi!", show_alert=True)


# ─────────────────────────────────────────────────────────────────────────────
# Admin approval callbacks (payment receipt)
# ─────────────────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("admin_approve:"))
async def cb_admin_approve(call: CallbackQuery, bot: Bot) -> None:
    _, uid_str, req_id_str, plan = call.data.split(":")
    uid    = int(uid_str)
    req_id = int(req_id_str)

    days = 30 if plan == "monthly" else 365
    await db.grant_premium(uid, days)
    await db.update_payment_status(req_id, "approved")

    user = await db.get_user(uid)
    lang = user.get("language", "uz") if user else "uz"
    try:
        await bot.send_message(uid, _(lang, "payment_approved", days=days))
    except Exception:
        pass

    await call.message.edit_caption(
        call.message.caption + "\n\n✅ TASDIQLANDI",
        reply_markup=None,
    )
    await call.answer("✅ Tasdiqlandi!", show_alert=True)


@router.callback_query(F.data.startswith("admin_reject:"))
async def cb_admin_reject(call: CallbackQuery, bot: Bot) -> None:
    parts  = call.data.split(":")
    uid    = int(parts[1])
    req_id = int(parts[2])

    await db.update_payment_status(req_id, "rejected")

    # Show reason picker
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="💸 Pul tushmadi",
            callback_data=f"reject_reason:{uid}:{req_id}:no_money",
        ),
        InlineKeyboardButton(
            text="📸 Sifatsiz rasm",
            callback_data=f"reject_reason:{uid}:{req_id}:bad_photo",
        ),
    ]])
    await call.message.reply("❌ Rad etish sababini tanlang:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("reject_reason:"))
async def cb_reject_reason(call: CallbackQuery, bot: Bot) -> None:
    _, uid_str, req_id_str, reason_key = call.data.split(":")
    uid = int(uid_str)

    user = await db.get_user(uid)
    lang = user.get("language", "uz") if user else "uz"
    reason_text = _(lang, f"reject_{reason_key}")

    try:
        await bot.send_message(uid, _(lang, "payment_rejected", reason=reason_text))
    except Exception:
        pass

    await call.message.edit_text(f"❌ Rad etildi: {reason_text}", reply_markup=None)
    await call.answer("❌ Rad etildi!", show_alert=True)
