# main.py — Production entry point for AI Dietitian Bot
# Architecture: aiogram 3.x | aiosqlite | APScheduler | Gemini Vision
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

import config
import database as db
from middlewares.i18n import I18nMiddleware, _
from handlers import onboarding, dashboard, admin, group

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TZ = pytz.timezone(config.TIMEZONE)


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler: background reminders
# ─────────────────────────────────────────────────────────────────────────────
async def _send_reminder(bot: Bot, reminder_key: str, meal_type: str | None = None) -> None:
    """Broadcast localized reminder to all non-banned users."""
    users = await db.get_all_users()
    logger.info(f"[Reminder] {reminder_key} → {len(users)} users")
    for u in users:
        uid  = u["user_id"]
        lang = u.get("language", "uz")
        if not db.has_access(u):
            continue
        # Skip if meal already logged today
        if meal_type and await db.has_meal_today(uid, meal_type):
            continue
        # Skip water if already had water today
        if reminder_key == "reminder_water" and await db.had_water_today(uid):
            continue
        try:
            await bot.send_message(uid, _(lang, reminder_key))
            await asyncio.sleep(0.04)
        except Exception as e:
            logger.warning(f"[Reminder] Skip {uid}: {e}")


def _setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TZ)

    # Breakfast reminder at 09:30
    scheduler.add_job(
        _send_reminder,
        CronTrigger(hour=9, minute=30, timezone=TZ),
        args=[bot, "reminder_breakfast", "breakfast"],
        id="breakfast",
        replace_existing=True,
    )
    # Lunch reminder at 13:30
    scheduler.add_job(
        _send_reminder,
        CronTrigger(hour=13, minute=30, timezone=TZ),
        args=[bot, "reminder_lunch", "lunch"],
        id="lunch",
        replace_existing=True,
    )
    # Dinner reminder at 20:00
    scheduler.add_job(
        _send_reminder,
        CronTrigger(hour=20, minute=0, timezone=TZ),
        args=[bot, "reminder_dinner", "dinner"],
        id="dinner",
        replace_existing=True,
    )
    # Water reminder every 2 hours (8:00 → 22:00)
    for h in range(8, 23, 2):
        scheduler.add_job(
            _send_reminder,
            CronTrigger(hour=h, minute=0, timezone=TZ),
            args=[bot, "reminder_water", None],
            id=f"water_{h}",
            replace_existing=True,
        )
    return scheduler


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
async def main() -> None:
    # 1. Init DB
    await db.init_db()
    logger.info("Database initialised ✅")

    # 2. Build bot & dispatcher
    bot = Bot(token=config.BOT_TOKEN, parse_mode=None)
    dp  = Dispatcher(storage=MemoryStorage())

    # 3. Register middleware (order matters — runs before every handler)
    dp.update.middleware(I18nMiddleware())

    # 4. Include routers (specific before generic)
    dp.include_router(onboarding.router)
    dp.include_router(admin.router)
    dp.include_router(group.router)
    dp.include_router(dashboard.router)   # catch-all last

    # 5. Start background scheduler
    scheduler = _setup_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler started ✅")

    # 6. Drop pending updates, start polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot polling started — @AI_Dietitian_Bot ✅")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
