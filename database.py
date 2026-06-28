# -*- coding: utf-8 -*-
import sqlite3
import datetime
from config import DB_PATH, TRIAL_DAYS, VIP_DAYS

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
          activity TEXT,
          goal TEXT,
          created_at TEXT,
          trial_end TEXT,
          vip_end TEXT,
          is_banned INTEGER DEFAULT 0,
          water_goal REAL DEFAULT 2.0
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
          logged_at TEXT,
          photo_file_id TEXT
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
          amount INTEGER,
          status TEXT,
          check_photo_id TEXT,
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
      import math
      weight_kg = weight
      height_m = height / 100
      bmi = weight_kg / (height_m ** 2)
      # Su normasini hisoblash
      if goal == 'lose':
                water = round(weight_kg * 0.035 + 0.5, 1)
elif goal == 'gain':
        water = round(weight_kg * 0.04, 1)
else:
        water = round(weight_kg * 0.033, 1)
      water = max(1.5, min(water, 4.0))
    conn = get_conn()
    c = conn.cursor()
    c.execute('''UPDATE users SET age=?, height=?, weight=?, gender=?, goal=?, water_goal=?
            WHERE user_id=?''', (age, height, weight, gender, goal, water, user_id))
    conn.commit()
    conn.close()

def is_trial_active(user_id):
      user = get_user(user_id)
      if not user:
                return False
            if user.get('vip_end'):
                      try:
                                    if datetime.datetime.fromisoformat(user['vip_end']) > datetime.datetime.now():
                                                      return True
                                              except:
                                    pass
                  if user.get('trial_end'):
                            try:
                                          if datetime.datetime.fromisoformat(user['trial_end']) > datetime.datetime.now():
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

def activate_vip(user_id):
      vip_end = (datetime.datetime.now() + datetime.timedelta(days=VIP_DAYS)).isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET vip_end=? WHERE user_id=?", (vip_end, user_id))
    conn.commit()
    conn.close()
    return vip_end

def log_meal(user_id, meal_type, food_name, calories=0, protein=0, fat=0, carbs=0, photo_file_id=None):
      now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO meals (user_id, meal_type, food_name, calories, protein, fat, carbs, logged_at, photo_file_id)
            VALUES (?,?,?,?,?,?,?,?,?)''',
                      (user_id, meal_type, food_name, calories, protein, fat, carbs, now, photo_file_id))
    conn.commit()
    conn.close()

def get_meals_by_period(user_id, days=1):
      since = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM meals WHERE user_id=? AND logged_at>=? ORDER BY logged_at DESC',
                      (user_id, since))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_today_meals(user_id):
      today = datetime.date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM meals WHERE user_id=? AND logged_at LIKE ? ORDER BY logged_at",
                      (user_id, f"{today}%"))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_water(user_id, amount):
      now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO water_log (user_id, amount, logged_at) VALUES (?,?,?)",
                      (user_id, amount, now))
    conn.commit()
    conn.close()

def get_today_water(user_id):
      today = datetime.date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) as total FROM water_log WHERE user_id=? AND logged_at LIKE ?",
                      (user_id, f"{today}%"))
    row = c.fetchone()
    conn.close()
    return row['total'] or 0.0

def create_payment(user_id, amount, check_photo_id):
      now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO payments (user_id, amount, status, check_photo_id, created_at) VALUES (?,?,?,?,?)",
                      (user_id, amount, 'pending', check_photo_id, now))
    pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid

def confirm_payment(payment_id):
      now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM payments WHERE id=?", (payment_id,))
    row = c.fetchone()
    if row:
              c.execute("UPDATE payments SET status='confirmed', confirmed_at=? WHERE id=?", (now, payment_id))
        conn.commit()
        conn.close()
        return row['user_id']
    conn.close()
    return None

def get_all_users():
      conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE is_banned=0")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats():
      conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as n FROM users")
    total = c.fetchone()['n']
    now = datetime.datetime.now().isoformat()
    c.execute("SELECT COUNT(*) as n FROM users WHERE vip_end > ?", (now,))
    vip = c.fetchone()['n']
    c.execute("SELECT COUNT(*) as n FROM users WHERE trial_end > ? AND (vip_end IS NULL OR vip_end <= ?)", (now, now))
    trial = c.fetchone()['n']
    c.execute("SELECT COUNT(*) as n FROM users WHERE is_banned=1")
    banned = c.fetchone()['n']
    conn.close()
    return {'total': total, 'vip': vip, 'trial': trial, 'banned': banned}

def get_vip_expiring_soon(days=5):
      target = (datetime.datetime.now() + datetime.timedelta(days=days)).date().isoformat()
    today = datetime.date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE vip_end LIKE ? AND is_banned=0", (f"{target}%",))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_users_without_meal_today(meal_window_name):
      today = datetime.date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    # Bugun shu meal_type kiritmaganlar
    c.execute('''SELECT u.* FROM users u
            WHERE u.is_banned=0
                    AND (u.vip_end > datetime('now') OR u.trial_end > datetime('now'))
                            AND u.user_id NOT IN (
                                        SELECT DISTINCT m.user_id FROM meals m
                                                    WHERE m.logged_at LIKE ? AND m.meal_type=?
                                                            )''', (f"{today}%", meal_window_name))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def ban_user(user_id):
      conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_vip_users():
      now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE vip_end > ? AND is_banned=0", (now,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_trial_users():
      now = datetime.datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE trial_end > ? AND (vip_end IS NULL OR vip_end <= ?) AND is_banned=0",
                            (now, now))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
