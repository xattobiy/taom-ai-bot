# handlers/group.py — Admin Group commands (!vip, !ban, !unban, !stat)
import re

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

import config
import database as db
from middlewares.i18n import _

router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Group filter — only process messages from the admin group
# ─────────────────────────────────────────────────────────────────────────────
def _is_admin_group(message: Message) -> bool:
    return message.chat.id == config.ADMIN_GROUP_ID


def _is_authorized(message: Message) -> bool:
    """Authorized if the message is in the admin group."""
    return _is_admin_group(message)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: resolve target user from a reply
# ─────────────────────────────────────────────────────────────────────────────
def _target_uid_from_reply(message: Message) -> int | None:
    """
    If the admin replied to a forwarded message that has a caption with
    '🆔 ID: <id>' or the message itself starts with a user ID, extract it.
    """
    if message.reply_to_message:
        rm = message.reply_to_message
        # Check caption or text
        src = rm.caption or (rm.text or "")
        m = re.search(r"ID[:\s]+<code>?(\d+)</code>?", src)
        if m:
            return int(m.group(1))
        # Also try bare number at start
        m2 = re.match(r"^(\d{5,15})", src.strip())
        if m2:
            return int(m2.group(1))
    return None


# ─────────────────────────────────────────────────────────────────────────────
# !vip {days} — grant VIP days to the replied-to user
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.text.startswith("!vip"), F.func(_is_admin_group))
async def group_vip(message: Message, bot: Bot) -> None:
    if not _is_authorized(message):
        return

    # Parse days
    parts = message.text.split()
    try:
        days = int(parts[1]) if len(parts) > 1 else 30
    except ValueError:
        await message.reply("❌ Format: !vip {days} (masalan: !vip 30)")
        return

    uid = _target_uid_from_reply(message)
    if not uid:
        await message.reply(
            "❌ Foydalanuvchi ID topilmadi.\n"
            "To'lov chekiga javob bering yoki: !vip {days} {user_id}"
        )
        return

    await db.grant_premium(uid, days)

    user = await db.get_user(uid)
    lang = user.get("language", "uz") if user else "uz"

    try:
        await bot.send_message(uid, _(lang, "payment_approved", days=days))
    except Exception:
        pass

    await message.reply(f"✅ {uid} ga {days} kun VIP berildi!")


# ─────────────────────────────────────────────────────────────────────────────
# !ban — blacklist user
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.text.startswith("!ban"), F.func(_is_admin_group))
async def group_ban(message: Message, bot: Bot) -> None:
    if not _is_authorized(message):
        return

    # Allow !ban {uid} or via reply
    parts = message.text.split()
    uid   = None
    if len(parts) > 1:
        try:
            uid = int(parts[1])
        except ValueError:
            pass
    if not uid:
        uid = _target_uid_from_reply(message)

    if not uid:
        await message.reply("❌ Format: !ban {user_id}")
        return

    await db.ban_user(uid)
    await message.reply(f"🚫 {uid} bloklandi!")


# ─────────────────────────────────────────────────────────────────────────────
# !unban — unblacklist user
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.text.startswith("!unban"), F.func(_is_admin_group))
async def group_unban(message: Message, bot: Bot) -> None:
    if not _is_authorized(message):
        return

    parts = message.text.split()
    uid   = None
    if len(parts) > 1:
        try:
            uid = int(parts[1])
        except ValueError:
            pass
    if not uid:
        uid = _target_uid_from_reply(message)

    if not uid:
        await message.reply("❌ Format: !unban {user_id}")
        return

    await db.unban_user(uid)
    await message.reply(f"✅ {uid} blokdan chiqarildi!")


# ─────────────────────────────────────────────────────────────────────────────
# !stat — system health dump
# ─────────────────────────────────────────────────────────────────────────────
@router.message(F.text.startswith("!stat"), F.func(_is_admin_group))
async def group_stat(message: Message) -> None:
    if not _is_authorized(message):
        return

    total   = await db.count_users()
    today   = await db.count_active_today()
    vip     = await db.count_premium_users()
    revenue = vip * config.PRICE_MONTHLY

    text = (
        f"📊 <b>Tizim holati</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"✅ Bugun faol: <b>{today}</b>\n"
        f"💎 VIP foydalanuvchilar: <b>{vip}</b>\n"
        f"💰 Taxminiy daromad: <b>{revenue:,} UZS</b>"
    )
    await message.reply(text, parse_mode="HTML")


# ─────────────────────────────────────────────────────────────────────────────
# Fallthrough: ignore all other group messages silently
# ─────────────────────────────────────────────────────────────────────────────
