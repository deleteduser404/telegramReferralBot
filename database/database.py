import sqlite3

conn = sqlite3.connect('database/database.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    stars INTEGER DEFAULT 0,
    withdrawn INTEGER DEFAULT 0,
    invited_by INTEGER,
    referral_link TEXT,
    captcha_verified BOOLEAN DEFAULT FALSE,
    subscription_verified BOOLEAN DEFAULT FALSE
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests (
    user_id INTEGER PRIMARY KEY,
    stars INTEGER,
    status TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS partners (
    info TEXT,
    contact TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    referral_price_inviter INTEGER DEFAULT 1,
    referral_price_referred INTEGER DEFAULT 1,
    minimum_output INTEGER DEFAULT 50
    
)''')

cursor.execute("INSERT OR IGNORE INTO settings (id, referral_price_inviter, referral_price_referred) VALUES (1, 1, 1)")

cursor.execute('''CREATE TABLE IF NOT EXISTS referrals (
    inviter_id INTEGER,
    referred_id INTEGER
)''')

conn.commit()