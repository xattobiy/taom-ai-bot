# config.py — Central configuration for AI Dietitian Bot
import os

# ── BOT CREDENTIALS ──────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8163772583:AAFY4g1M8OS4luohuvrMYpqJ6fa32ue8zvc")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6JXBvlwv-G2sCPbrhbYEJTSA3dz8wnP8yGbfxz8kDrfNg")

# ── ADMIN & GROUP ─────────────────────────────────────────────────────────────
SUPER_ADMIN_ID: int = 956947665
SUPER_ADMIN_USERNAME: str = "@hattobiy"
ADMIN_GROUP_ID: int = -1003173602605

# ── PAYMENT ───────────────────────────────────────────────────────────────────
PAYMENT_CARD: str = "9860040114589092"
PAYMENT_HOLDER: str = "N/N"
PRICE_MONTHLY: int = 20_000   # UZS
PRICE_YEARLY: int  = 220_000  # UZS

# ── DATABASE ──────────────────────────────────────────────────────────────────
DB_PATH: str = "dietitian.db"

# ── TRIAL ────────────────────────────────────────────────────────────────────
TRIAL_DAYS: int = 3

# ── TIMEZONE ─────────────────────────────────────────────────────────────────
TIMEZONE: str = "Asia/Tashkent"

# ── SUPPORTED LANGUAGES ───────────────────────────────────────────────────────
SUPPORTED_LANGS: list[str] = ["uz", "ru", "en"]
DEFAULT_LANG: str = "uz"

# ── WATER GOAL (ml) ───────────────────────────────────────────────────────────
WATER_GOAL_ML: int = 2500
WATER_GLASS_ML: int = 300

# ── REFERRAL ─────────────────────────────────────────────────────────────────
REFERRAL_REQUIRED: int = 3        # referrals needed to unlock bonus
REFERRAL_BONUS_DAYS: int = 2      # bonus VIP days granted
