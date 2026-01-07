from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
import speech_recognition as sr
import requests
from gtts import gTTS
import tempfile
import os
import json
from datetime import datetime
from pydub import AudioSegment
import history_db

api_bp = Blueprint('api', __name__)

# --- Configuration ---
JIGSAWSTACK_API_KEY = os.getenv("JIGSAWSTACK_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

# --- API Routes ---

@api_bp.route('/api/transcribe', methods=['POST'])
@login_required
def transcribe_audio():
    """Transcribe audio from uploaded file"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        source_lang = request.form.get('source_lang', 'en')
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_input:
            audio_file.save(temp_input.name)
            temp_input_path = temp_input.name
        
        temp_wav_path = temp_input_path.replace('.webm', '.wav')
        
        try:
            audio = AudioSegment.from_file(temp_input_path)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(temp_wav_path, format='wav')
            
            with sr.AudioFile(temp_wav_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=source_lang)
                
            return jsonify({'text': text})
            
        finally:
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if os.path.exists(temp_wav_path):
                os.unlink(temp_wav_path)
                
    except sr.UnknownValueError:
        return jsonify({'error': 'Could not understand audio'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/translate', methods=['POST'])
@login_required
def translate_text():
    """Translate text using JigsawStack API"""
    try:
        data = request.json
        text = data.get('text')
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'de')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        url = "https://jigsawstack.com/api/v1/ai/translate"
        
        payload = {
            "text": text,
            "source_language": source_lang,
            "target_language": target_lang
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": JIGSAWSTACK_API_KEY
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        translation = None
        if isinstance(result, dict):
            for key in ["translation", "translated_text", "result"]:
                if key in result:
                    translation = result[key]
                    break
        
        if not translation:
            translation = str(result)
        
        history_entry = history_db.add_entry(
            user_id=current_user.id,
            source_lang=source_lang,
            target_lang=target_lang,
            original_text=text,
            translated_text=translation
        )
        
        return jsonify({
            'translation': translation,
            'history_entry': history_entry
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/text-to-speech', methods=['POST'])
@login_required
def text_to_speech():
    """Convert text to speech"""
    try:
        data = request.json
        text = data.get('text')
        lang = data.get('lang', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        tts = gTTS(text=text, lang=lang, slow=False)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
            tts.save(temp_audio.name)
            temp_audio_path = temp_audio.name
        
        return send_file(
            temp_audio_path,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name='translation.mp3'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/history', methods=['GET'])
@login_required
def get_history():
    return jsonify({'history': history_db.get_user_history(current_user.id)})

@api_bp.route('/api/history/clear', methods=['POST'])
@login_required
def clear_history():
    history_db.clear_user_history(current_user.id)
    return jsonify({'message': 'History cleared'})

import tutor_db

@api_bp.route('/api/tutor/init', methods=['POST'])
@login_required
def init_tutor_session():
    """Initialize or retrieve active session"""
    user_id = current_user.id
    data = request.json
    task_type = data.get('task_type', 'free_chat')
    
    # Check for active session
    session = tutor_db.get_active_session(user_id)
    if not session:
        session_id = tutor_db.create_session(user_id, task_type)
    else:
        session_id = session['id']
        
    # Get profile for personalized greeting
    profile = tutor_db.get_profile(user_id)
    
    return jsonify({
        'session_id': session_id,
        'profile': profile,
        'task_type': task_type
    })

@api_bp.route('/api/tutor/chat', methods=['POST'])
@login_required
def chat_with_tutor():
    """Conversational Tutor with Memory"""
    try:
        data = request.json
        user_message = data.get('message')
        session_id = data.get('session_id')
        
        if not user_message or not session_id:
            desired_task = data.get('task_type', 'free_chat')
            # Auto-create session if missing (fallback)
            session_id = tutor_db.create_session(current_user.id, desired_task)
        
        # 1. Save User Message
        tutor_db.add_message(session_id, 'user', user_message)
        
        # 2. Build Context
        history = tutor_db.get_session_history(session_id, limit=10)
        profile = tutor_db.get_profile(current_user.id)
        
        # 3. Call Groq
        response_data = generate_tutor_response(user_message, history, profile)
        
        # 4. Save Tutor Response
        tutor_db.add_message(
            session_id, 
            'tutor', 
            response_data['german_response'], 
            correction=response_data.get('correction')
        )
        
        # 5. Async: Update Profile (Simple implementation: just check for serious errors)
        # In a real app, this might be a background task
        if response_data.get('has_error'):
            update_user_weaknesses(current_user.id, response_data['correction'])
        
        return jsonify(response_data)

    except Exception as e:
        print(f"Tutor Error: {e}")
        return jsonify({'error': str(e)}), 500

def generate_tutor_response(message, history, profile):
    """
    Generates a response using Groq that:
    1. Acts as a German teacher
    2. Gently corrects mistakes
    3. Maintains conversation flow
    """
    if not GROQ_API_KEY:
        return {
            'german_response': "Entschuldigung, mein Gehirn (API Key) fehlt.",
            'english_translation': "Sorry, my brain (API Key) is missing.",
            'has_error': False
        }

    # Format history for LLM
    conversation_text = ""
    for msg in history:
        role = "Student" if msg['role'] == 'user' else "Teacher"
        conversation_text += f"{role}: {msg['content']}\n"
    
    weaknesses = json.loads(profile['weaknesses']) if profile['weaknesses'] else []
    level = profile['level']
    
    system_prompt = f"""You are a friendly, encouraging German Teacher. 
Student Level: {level}
Student Weaknesses: {', '.join(weaknesses)}

GOALS:
1. CORRECT grammar mistakes gently.
2. KEEP THE CONVERSATION GOING. Ask questions back.
3. Be concise.

CRITICAL RULES (GRAMMAR):
- IGNORE Capitalization errors (e.g. "hunger" instead of "Hunger" is OK).
- IGNORE Punctuation errors (missing commas/periods is OK).
- ONLY correct GRAMMAR (conjugation, word order, wrong words).

INTERACTION FLOW FOR ERRORS:
IF student makes a grammar mistake:
1. Set "has_error": true
2. Set "german_response": "Du meinst: [Corrected Sentence]"
3. STOP. Do NOT ask a follow-up question yet. Allow student to repeat.

IF student speaks correctly (or repeats your correction):
1. Set "has_error": false
2. Respond naturally to the content.

FORMAT YOUR RESPONSE AS JSON:
{{
  "german_response": "Your reply",
  "english_translation": "English meaning",
  "has_error": true/false,
  "correction": "Short explanation of error (if any), otherwise null"
}}

Example (Mistake):
Student: "Ich brauche hilfe in einkaufen"
Teacher JSON:
{{
  "german_response": "Du meinst: Ich brauche Hilfe beim Einkaufen.",
  "english_translation": "You mean: I need help with shopping.",
  "has_error": true,
  "correction": "Use 'beim' (bei dem) for activities, not 'in'."
}}

Example (Correct/Follow-up):
Student: "Ja, ich brauche Hilfe beim Einkaufen."
Teacher JSON:
{{
  "german_response": "Das ist toll! Was möchtest du kaufen?",
  "english_translation": "That is great! What would you like to buy?",
  "has_error": false,
  "correction": null
}}
"""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Conversation History:\n{conversation_text}\n\nStudent says: {message}"}
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        parsed_response = json.loads(content)
        
        # Apply filters
        return refine_tutor_response(parsed_response, message)
        
    except Exception as e:
        print(f"LLM Error: {e}")
        return {
            'german_response': "Entschuldigung, ich habe das nicht verstanden.",
            'english_translation': "Sorry, I didn't understand that.",
            'has_error': False
        }

def normalize_text(text):
    """Remove punctuation and lowercase for comparison"""
    import string
    if not text: return ""
    return text.lower().translate(str.maketrans('', '', string.punctuation)).strip()

def is_same_content(text1, text2):
    return normalize_text(text1) == normalize_text(text2)

def refine_tutor_response(parsed_response, user_message):
    """Pure function to apply filters to logic"""
    # --- FILTER 1: Punctuation/Capitalization Check ---
    if parsed_response.get('has_error') and parsed_response.get('correction'):
        fix = parsed_response['correction'].lower()
        punctuation_keywords = ['comma', 'komma', 'period', 'punkt', 'punctuation', 'satzzeichen', 'capitalization', 'großschreibung']
        grammar_keywords = ['verb', 'conjugation', 'position', 'pronoun', 'order', 'wortstellung', 'konjugation', 'case', 'kasus', 'article', 'artikel', 'gender', 'genus']
        
        is_punctuation_only = any(k in fix for k in punctuation_keywords)
        has_grammar_content = any(k in fix for k in grammar_keywords)
        
        if is_punctuation_only and not has_grammar_content:
            print(f"REJECTED PUNCTUATION CORRECTION: {fix}")
            parsed_response['has_error'] = False
            parsed_response['correction'] = None
            parsed_response['english_translation'] = "That is correct! Tell me more."
    
    # --- FILTER 2: Content Equality Check ---
    if parsed_response.get('has_error') and "Du meinst:" in parsed_response.get('german_response', ''):
        # Extract sentence after "Du meinst:"
        try:
            corrected_part = parsed_response['german_response'].split("Du meinst:", 1)[1].strip()
            if is_same_content(user_message, corrected_part):
                print(f"REJECTED IDENTICAL CONTENT CORRECTION: {corrected_part}")
                parsed_response['has_error'] = False
                parsed_response['correction'] = None
                parsed_response['german_response'] = f"Genau! {corrected_part}" 
                parsed_response['english_translation'] = f"Exactly! {corrected_part}"
        except IndexError:
            pass # Malformed "Du meinst" response, skip check

    return parsed_response

def update_user_weaknesses(user_id, correction):
    """Simple logic to add weakness to profile"""
    if not correction: 
        return
        
    profile = tutor_db.get_profile(user_id)
    weaknesses = json.loads(profile['weaknesses'])
    
    # very basic: just add the correction text if it's short
    # In reality, you'd want to categorize this (e.g. "Dative Case")
    if len(weaknesses) < 5: 
        weaknesses.append(correction[:50]) # keep it short
        tutor_db.update_profile(user_id, weaknesses=weaknesses)
