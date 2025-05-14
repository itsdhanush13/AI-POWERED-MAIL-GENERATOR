import sqlite3
from datetime import datetime

DB_NAME = "email_app.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    qualification TEXT,
                    experience TEXT,
                    skills TEXT,
                    email TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    subject TEXT,
                    body TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()

def save_user(name, qualification, experience, skills, email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO users (name, qualification, experience, skills, email) VALUES (?, ?, ?, ?, ?)',
              (name, qualification, experience, skills, email))
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return user_id

def update_user(user_id, name, qualification, experience, skills):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''UPDATE users SET name=?, qualification=?, experience=?, skills=? WHERE user_id=?''',
              (name, qualification, experience, skills, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT name, qualification, experience, skills, email FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(zip(["name", "qualification", "experience", "skills", "email"], row))
    return {}

def save_email(user_id, subject, body):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO emails (user_id, subject, body) VALUES (?, ?, ?)',
              (user_id, subject, body))
    conn.commit()
    conn.close()

def get_email_history(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT subject, body, created_at FROM emails WHERE user_id=? ORDER BY created_at DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows