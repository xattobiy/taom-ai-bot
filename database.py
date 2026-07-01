# database.py — Async SQLite layer for AI Dietitian Bot
import aiosqlite
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import config

# ─────────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT,
    first_name      TEXT,
    language        TEXT    NOT NULL DEFAULT 'uz',
    gender          TEXT,
    height          REAL,
    weight          REAL,
    goal            TEXT    DEFAULT 'keep',
    activity        TEXT    DEFAULT 'medium',
    trial_start     TEXT,
    is_premium      INTEGER DEFAULT 0,
    premium_until   TEXT,
    consumed_cal    REAL    DEFAULT 0,
    target_cal      REAL    DEFAULT 2000,
    water_intake    INTEGER DEFAULT 0,
    referred_by     INTEGER,
    is_banned       INTEGER DEFAULT 0,
    ref_code        TEXT    UNIQUE,
    created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS food_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    food_desc   TEXT,
    calories    REAL    DEFAULT 0,
    protein     REAL    DEFAULT 0,
    fat         REAL    DEFAULT 0,
    carbs       REAL    DEFAULT 0,
    meal_type   TEXT,
    logged_at   TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS water_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount_ml   INTEGER DEFAULT 300,
    logged_at   TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS payment_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    plan            TEXT    NOT NULL,
    photo_file_id   TEXT,
    status          TEXT    DEFAULT 'pending',
    created_at      TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS referrals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER NOT NULL UNIQUE,
    created_at  TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(referrer_id) REFERENCES users(user_id),
    FOREIGN KEY(referred_id) REFERENCES users(user_id)
);
"""

# ─────────────────────────────────────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────────────────────────────────────
async def init_db() -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

# ─────────────────────────────────────────────────────────────────────────────
# User helpers
# ─────────────────────────────────────────────────────────────────────────────
async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def upsert_user(user_id: int, **fields) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        row = await db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        )
        exists = await row.fetchone()
        if exists:
            sets = ", ".join(f"{k} = ?" for k in fields)
            vals = list(fields.values()) + [user_id]
            await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", vals)
        else:
            fields["user_id"] = user_id
            if "ref_code" not in fields:
                fields["ref_code"] = _generate_ref_code(user_id)
            if "trial_start" not in fields:
                fields["trial_start"] = datetime.utcnow().isoformat()
            cols = ", ".join(fields.keys())
            phs  = ", ".join("?" * len(fields))
            await db.execute(f"INSERT INTO users ({cols}) VALUES ({phs})", list(fields.values()))
        await db.commit()


def _generate_ref_code(user_id: int) -> str:
    return hashlib.md5(f"{user_id}{secrets.token_hex(4)}".encode()).hexdigest()[:10]


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_banned = 0") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def count_users() -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def count_active_today() -> int:
    today = datetime.utcnow().date().isoformat()
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM food_logs WHERE date(logged_at) = ?", (today,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def count_premium_users() -> int:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_premium = 1 AND (premium_until IS NULL OR premium_until > ?)",
            (now,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

# ─────────────────────────────────────────────────────────────────────────────
# Trial / Premium helpers
# ─────────────────────────────────────────────────────────────────────────────
def is_trial_active(user: dict) -> bool:
    ts = user.get("trial_start")
    if not ts:
        return False
    start = datetime.fromisoformat(ts)
    return datetime.utcnow() < start + timedelta(days=config.TRIAL_DAYS)


def trial_days_left(user: dict) -> int:
    ts = user.get("trial_start")
    if not ts:
        return 0
    start = datetime.fromisoformat(ts)
    delta = (start + timedelta(days=config.TRIAL_DAYS)) - datetime.utcnow()
    return max(0, delta.days)


def is_premium_active(user: dict) -> bool:
    if not user.get("is_premium"):
        return False
    pu = user.get("premium_until")
    if not pu:
        return True  # lifetime
    return datetime.utcnow() < datetime.fromisoformat(pu)


def has_access(user: dict) -> bool:
    return is_trial_active(user) or is_premium_active(user)


async def grant_premium(user_id: int, days: int) -> None:
    user = await get_user(user_id)
    now = datetime.utcnow()
    if user and user.get("is_premium") and user.get("premium_until"):
        base = datetime.fromisoformat(user["premium_until"])
        base = max(base, now)
    else:
        base = now
    until = (base + timedelta(days=days)).isoformat()
    await upsert_user(user_id, is_premium=1, premium_until=until)


async def ban_user(user_id: int) -> None:
    await upsert_user(user_id, is_banned=1)


async def unban_user(user_id: int) -> None:
    await upsert_user(user_id, is_banned=0)

# ─────────────────────────────────────────────────────────────────────────────
# Food logs
# ─────────────────────────────────────────────────────────────────────────────
async def log_food(
    user_id: int,
    food_desc: str,
    calories: float,
    protein: float = 0,
    fat: float = 0,
    carbs: float = 0,
    meal_type: str = "other",
) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            """INSERT INTO food_logs (user_id, food_desc, calories, protein, fat, carbs, meal_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, food_desc, calories, protein, fat, carbs, meal_type),
        )
        # update daily consumed
        await db.execute(
            "UPDATE users SET consumed_cal = consumed_cal + ? WHERE user_id = ?",
            (calories, user_id),
        )
        await db.commit()


async def get_today_food_logs(user_id: int) -> list[dict]:
    today = datetime.utcnow().date().isoformat()
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM food_logs WHERE user_id = ? AND date(logged_at) = ?",
            (user_id, today),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_today_calories(user_id: int) -> float:
    logs = await get_today_food_logs(user_id)
    return sum(r["calories"] for r in logs)


async def has_meal_today(user_id: int, meal_type: str) -> bool:
    today = datetime.utcnow().date().isoformat()
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM food_logs WHERE user_id = ? AND meal_type = ? AND date(logged_at) = ?",
            (user_id, meal_type, today),
        ) as cur:
            row = await cur.fetchone()
            return row is not None

# ─────────────────────────────────────────────────────────────────────────────
# Water logs
# ─────────────────────────────────────────────────────────────────────────────
async def log_water(user_id: int, amount_ml: int = 300) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT INTO water_logs (user_id, amount_ml) VALUES (?, ?)",
            (user_id, amount_ml),
        )
        await db.execute(
            "UPDATE users SET water_intake = water_intake + ? WHERE user_id = ?",
            (amount_ml, user_id),
        )
        await db.commit()


async def get_today_water(user_id: int) -> int:
    today = datetime.utcnow().date().isoformat()
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT COALESCE(SUM(amount_ml), 0) FROM water_logs WHERE user_id = ? AND date(logged_at) = ?",
            (user_id, today),
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def had_water_today(user_id: int) -> bool:
    return (await get_today_water(user_id)) > 0

# ─────────────────────────────────────────────────────────────────────────────
# Payment requests
# ─────────────────────────────────────────────────────────────────────────────
async def create_payment_request(user_id: int, plan: str, photo_file_id: str) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO payment_requests (user_id, plan, photo_file_id) VALUES (?, ?, ?)",
            (user_id, plan, photo_file_id),
        )
        await db.commit()
        return cur.lastrowid


async def get_payment_request(req_id: int) -> Optional[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payment_requests WHERE id = ?", (req_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_payment_status(req_id: int, status: str) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE payment_requests SET status = ? WHERE id = ?", (status, req_id)
        )
        await db.commit()

# ─────────────────────────────────────────────────────────────────────────────
# Referrals
# ─────────────────────────────────────────────────────────────────────────────
async def record_referral(referrer_id: int, referred_id: int) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                (referrer_id, referred_id),
            )
            await db.commit()
        except Exception:
            pass


async def count_referrals(user_id: int) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_user_by_ref_code(ref_code: str) -> Optional[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE ref_code = ?", (ref_code,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

# ─────────────────────────────────────────────────────────────────────────────
# Calorie calculations (Mifflin-St Jeor)
# ─────────────────────────────────────────────────────────────────────────────
def calc_target_calories(user: dict) -> int:
    w = float(user.get("weight") or 70)
    h = float(user.get("height") or 170)
    age = 25  # default; not stored separately in this schema
    gender  = (user.get("gender") or "male").lower()
    goal    = (user.get("goal")   or "keep").lower()
    activity = (user.get("activity") or "medium").lower()

    if "female" in gender or "ayol" in gender or "женщ" in gender:
        bmr = 10 * w + 6.25 * h - 5 * age - 161
    else:
        bmr = 10 * w + 6.25 * h - 5 * age + 5

    act_map = {"low": 1.2, "medium": 1.55, "high": 1.725}
    tdee = bmr * act_map.get(activity, 1.55)

    if any(k in goal for k in ("lose", "ozish", "похуд")):
        return max(1200, round(tdee - 500))
    if any(k in goal for k in ("gain", "qoshish", "набрать")):
        return round(tdee + 500)
    return round(tdee)
