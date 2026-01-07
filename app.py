#!/usr/bin/env python3
"""
Voice Translator with Groq AI German Tutor
Uses FREE Groq API for 99% accurate German corrections
"""
from dotenv import load_dotenv
from flask import Flask, redirect, url_for
from flask_login import LoginManager
import os
import history_db

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Security: Load secret key from env or fallback (for dev only)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Login Manager Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return history_db.get_user_by_id(user_id)

# Register Blueprints
from routes.auth import auth_bp
from routes.main import main_bp
from routes.api import api_bp

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    history_db.init_db()
    
    print("\n" + "="*60)
    print("🌍 Voice Translator with AI German Tutor")
    print("="*60)
    
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print("✅ Groq AI: CONFIGURED (Best quality!)")
        print("   Model: Llama 3.3 70B")
        print("   Accuracy: ~99%")
    else:
        print("⚠️  Groq AI: NOT CONFIGURED")
        print("   Get FREE API key: https://console.groq.com")
        print("   Current: Using pattern matching (limited accuracy)")
    
    print("\n🚀 Starting server...")
    print("📱 Open: http://localhost:5000\n")
    
    # In production, use a WSGI server instead of app.run
    app.run(debug=True, host='0.0.0.0', port=5000)