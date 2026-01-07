import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

DB_NAME = "translation_history.db"

class User(UserMixin):
    def __init__(self, id, username, role, password_hash):
        self.id = id
        self.username = username
        self.role = role
        self.password_hash = password_hash

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Enable foreign keys
    c.execute("PRAGMA foreign_keys = ON")
    
    # Create Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    ''')
    
    # Create History Table with user_id
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            source_lang TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            original_text TEXT NOT NULL,
            translated_text TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

# --- USER MANAGEMENT ---

def create_user(username, password, role='user'):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if this is the FIRST user ever
    c.execute('SELECT COUNT(*) FROM users')
    count = c.fetchone()[0]
    
    if count == 0:
        role = 'admin'  # First user is ALWAYS admin
    
    password_hash = generate_password_hash(password)
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        c.execute('INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)',
                  (username, password_hash, role, created_at))
        conn.commit()
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return User(row['id'], row['username'], row['role'], row['password_hash'])
    return None

def get_user_by_id(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return User(row['id'], row['username'], row['role'], row['password_hash'])
    return None

def verify_password(user, password):
    return check_password_hash(user.password_hash, password)

def update_password(user_id, new_password):
    conn = get_db_connection()
    c = conn.cursor()
    new_hash = generate_password_hash(new_password)
    c.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user_id))
    conn.commit()
    conn.close()
    return True

def get_all_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, role, created_at FROM users ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_stats():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT u.username, COUNT(h.id) as translation_count 
        FROM users u 
        LEFT JOIN history h ON u.id = h.user_id 
        GROUP BY u.id
    ''')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- HISTORY MANAGEMENT ---

def add_entry(user_id, source_lang, target_lang, original_text, translated_text):
    conn = get_db_connection()
    c = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''
        INSERT INTO history (user_id, timestamp, source_lang, target_lang, original_text, translated_text)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, timestamp, source_lang, target_lang, original_text, translated_text))
    
    entry_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return {
        'id': entry_id,
        'timestamp': timestamp,
        'source_lang': source_lang,
        'target_lang': target_lang,
        'original_text': original_text,
        'translated_text': translated_text
    }

def get_user_history(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM history WHERE user_id = ? ORDER BY id DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            'id': row['id'],
            'timestamp': row['timestamp'],
            'source_lang': row['source_lang'],
            'target_lang': row['target_lang'],
            'original_text': row['original_text'],
            'translated_text': row['translated_text']
        })
    return history

def get_all_history_admin():
    conn = get_db_connection()
    c = conn.cursor()
    # Join with users table to get usernames
    c.execute('''
        SELECT h.*, u.username 
        FROM history h 
        JOIN users u ON h.user_id = u.id 
        ORDER BY h.id DESC
    ''')
    rows = c.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            'id': row['id'],
            'username': row['username'],
            'timestamp': row['timestamp'],
            'source_lang': row['source_lang'],
            'target_lang': row['target_lang'],
            'original_text': row['original_text'],
            'translated_text': row['translated_text']
        })
    return history

def clear_user_history(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM history WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
