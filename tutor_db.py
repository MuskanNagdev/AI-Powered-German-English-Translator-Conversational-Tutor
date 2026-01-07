import sqlite3
import json
from datetime import datetime

DB_NAME = "tutor.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Enable FK
    c.execute("PRAGMA foreign_keys = ON")
    
    # User Profile (One per user)
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            level TEXT DEFAULT 'A1',
            weaknesses TEXT DEFAULT '[]', -- JSON list of strings
            goals TEXT DEFAULT '[]',      -- JSON list of strings
            last_active TEXT
        )
    ''')
    
    # Tutor Sessions (Threads)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tutor_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            task_type TEXT DEFAULT 'free_chat',
            is_active BOOLEAN DEFAULT 1,
            summary TEXT
        )
    ''')
    
    # Messages
    c.execute('''
        CREATE TABLE IF NOT EXISTS tutor_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL, -- 'user', 'tutor', 'system'
            content TEXT NOT NULL,
            correction_json TEXT, -- JSON if it was a correction
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES tutor_sessions (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# --- Profiles ---

def get_profile(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    else:
        # Create default profile if none exists
        return create_profile(user_id)

def create_profile(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        c.execute('INSERT INTO user_profiles (user_id, last_active) VALUES (?, ?)', (user_id, now))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
    conn.close()
    return {'user_id': user_id, 'level': 'A1', 'weaknesses': '[]', 'goals': '[]', 'last_active': now}

def update_profile(user_id, weaknesses=None, goals=None, level=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    updates = []
    params = []
    
    if weaknesses is not None:
        updates.append("weaknesses = ?")
        params.append(json.dumps(weaknesses) if isinstance(weaknesses, list) else weaknesses)
        
    if goals is not None:
        updates.append("goals = ?")
        params.append(json.dumps(goals) if isinstance(goals, list) else goals)
        
    if level is not None:
        updates.append("level = ?")
        params.append(level)
        
    if updates:
        updates.append("last_active = ?")
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        query = f"UPDATE user_profiles SET {', '.join(updates)} WHERE user_id = ?"
        params.append(user_id)
        
        c.execute(query, params)
        conn.commit()
        
    conn.close()

# --- Sessions ---

def create_session(user_id, task_type='free_chat'):
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Deactivate old sessions (optional, maybe we want multiple threads?)
    # For now, let's keep it simple: just create new one
    
    c.execute('INSERT INTO tutor_sessions (user_id, start_time, task_type) VALUES (?, ?, ?)',
              (user_id, now, task_type))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_active_session(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM tutor_sessions WHERE user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1', (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

# --- Messages ---

def add_message(session_id, role, content, correction=None):
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    correction_json = json.dumps(correction) if correction else None
    
    c.execute('''
        INSERT INTO tutor_messages (session_id, role, content, correction_json, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, role, content, correction_json, now))
    
    conn.commit() 
    conn.close()

def get_session_history(session_id, limit=20):
    conn = get_db_connection()
    c = conn.cursor()
    # Get last N messages
    c.execute('''
        SELECT * FROM (
            SELECT * FROM tutor_messages 
            WHERE session_id = ? 
            ORDER BY id DESC 
            LIMIT ?
        ) ORDER BY id ASC
    ''', (session_id, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    init_db()
    print("Tutor Database Initialized.")
