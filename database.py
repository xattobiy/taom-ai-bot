# -*- coding: utf-8 -*-
import sqlite3
import datetime

DB_PATH = "taom_ai.db"
TRIAL_DAYS = 3
VIP_DAYS = 30

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        age INTEGER,
        height REAL,
        weight REAL,
        gender TEXT,
        goal TEXT,
        calories_goal REAL DEFAULT 0,
        water_goal REAL DEFAULT 2.0,
        created_at TEXT,
        trial_end TEXT,
        vip_end TEXT,
        is_banned INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        meal_type TEXT,
        food_name TEXT,
        calories REAL DEFAULT 0,
        protein REAL DEFAULT 0,
        fat REAL DEFAULT 0,
        carbs REAL DEFAULT 0,
        weight_gram REAL DEFAULT 0,
        logged_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS water_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        logged_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        check_photo_id TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        confirmed_at TEXT
    )''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(user_id, username, full_name):
    now = datetime.datetime.now().isoformat()
    trial_end = (datetime.datetime.now() + datetime.timedelta(days=TRIAL_DAYS)).isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users
        (user_id, username, full_name, created_at, trial_end)
        VALUES (?,?,?,?,?)''',
        (user_id, username or "", full_name or "", now, trial_end))
    conn.commit()
    conn.close()

def update_profile(user_id, age, height, weight, gender, goal):
    if gender == 'male':
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    if goal == 'lose':
        calories_goal = bmr * 1.2 - 500
        water = round(weight * 0.035 + 0.5, 1)
    elif goal == 'gain':
        calories_goal = bmr * 1.2 + 500
        water = round(weight * 0.04, 1)
    else:
        calories_goal = bmr * 1.2
        water = round(weight * 0.033, 1)
    water = max(1.5, min(water, 4.0))
    calories_goal = round(calories_goal)
    conn = get_conn()
    c = conn.cursor()
    c.execute('''UPDATE users SET age=?, height=?, weight=?, gender=?, goal=?,
        calories_goal=?, water_goal=? WHERE user_id=?''',
        (age, height, weight, gender, goal, calories_goal, water, user_id))
    conn.commit()
    conn.close()

def is_access_allowed(user_id):
    user = get_user(user_id)
    if not user:
        return False
    now = datetime.datetime.now()
    if user.get('vip_end'):
        try:
            if datetime.datetime.fromisoformat(user['vip_end']) > now:
                return True
        except:
            pass
    if user.get('trial_end'):
        try:
            if datetime.datetime.fromisoformat(user['trial_end']) > now:
                return True
        except:
            pass
    return False

def is_vip(user_id):
    user = get_user(user_id)
    if not user or not user.get('vip_end'):
        return False
    try:
        return datetime.datetime.fromisoformat(user['vip_end']) > datetime.datetime.now()
    except:
        return False

def is_trial_active(user_id):
    user = get_user(user_id)
    if not user or not user.get('trial_end'):
        return False
    try:
        return datetime.datetime.fromisoformat(user['trial_end']) > datetime.datetime.now()
    except:
        return False

def activate_vip(user_id, days=30):
    now = datetime.datetime.now()
    user = get_user(user_id)
    if user and user.get('vip_end'):
        try:
            current_end = datetime.datetime.fromisoformat(user['vip_end'])
            vip_end = current_end + datetime.timedelta(days=days) if current_end > now else now + datetime.timedelta(days=days)
        except:
            vip_end = now + datetime.timedelta(days=days)
    else:
        vip_end = now + datetime.timedelta(days=days)
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET vip_end=? WHERE user_id=?", (vip_end.isoformat(), user_id))
    conn.commit()
    conn.close()

def add_meal(user_id, meal_type, food_name, calories, protein, fat, carbs, weight_gram):
    now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO meals (user_id, meal_type, food_name, calories, protein, fat, carbs, weight_gram, logged_at)
        VALUES (?,?,?,?,?,?,?,?,?)''',
        (user_id, meal_type, food_name, calories, protein, fat, carbs, weight_gram, now))
    conn.commit()
    conn.close()

def get_meals_today(user_id):
    today = datetime.date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT * FROM meals WHERE user_id=? AND logged_at LIKE ?
        ORDER BY logged_at ASC''', (user_id, today + '%'))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_meals_week(user_id):
    week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT * FROM meals WHERE user_id=? AND logged_at >= ?
        ORDER BY logged_at ASC''', (user_id, week_ago))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_meals_month(user_id):
    month_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT * FROM meals WHERE user_id=? AND logged_at >= ?
        ORDER BY logged_at ASC''', (user_id, month_ago))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_water(user_id, amount):
    now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO water_log (user_id, amount, logged_at) VALUES (?,?,?)",
        (user_id, amount, now))
    conn.commit()
    conn.close()

def get_water_today(user_id):
    today = datetime.date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT COALESCE(SUM(amount),0) as total FROM water_log
        WHERE user_id=? AND logged_at LIKE ?''', (user_id, today + '%'))
    row = c.fetchone()
    conn.close()
    return row['total'] if row else 0

def add_payment(user_id, check_photo_id):
    now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO payments (user_id, check_photo_id, status, created_at)
        VALUES (?,?,?,?)''', (user_id, check_photo_id, 'pending', now))
    last_id = c.lastrowid
    conn.commit()
    conn.close()
    return last_id

def confirm_payment(payment_id):
    now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE payments SET status='confirmed', confirmed_at=? WHERE id=?",
        (now, payment_id))
    c.execute("SELECT user_id FROM payments WHERE id=?", (payment_id,))
    row = c.fetchone()
    conn.commit()
    conn.close()
    if row:
        activate_vip(row['user_id'])
        return row['user_id']
    return None

def get_all_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_users_without_meal_today_in_range(start_hour, end_hour):
    today = datetime.date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    all_users = [row['user_id'] for row in c.fetchall()]
    result = []
    for uid in all_users:
        c.execute('''SELECT COUNT(*) as cnt FROM meals
            WHERE user_id=? AND logged_at LIKE ?
            AND CAST(strftime('%H', logged_at) AS INTEGER) >= ?
            AND CAST(strftime('%H', logged_at) AS INTEGER) < ?''',
            (uid, today + '%', start_hour, end_hour))
        row = c.fetchone()
        if row and row['cnt'] == 0:
            result.append(uid)
    conn.close()
    return result

def get_users_vip_expiring_in_days(days=5):
    target_date = (datetime.datetime.now() + datetime.timedelta(days=days)).date().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE vip_end LIKE ?", (target_date + '%',))
    rows = c.fetchall()
    conn.close()
    return [row['user_id'] for row in rows]

def get_meal_type_by_hour(hour):
    if 6 <= hour < 11:
        return 'nonushta'
    elif 11 <= hour < 16:
        return 'tushlik'
    elif 16 <= hour < 22:
        return 'kechki_ovqat'
    else:
        return 'boshqa'
