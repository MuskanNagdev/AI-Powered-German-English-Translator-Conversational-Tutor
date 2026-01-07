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

@api_bp.route('/api/tutor-correct', methods=['POST'])
@login_required
def tutor_correct():
    """AI tutor using Groq for German corrections"""
    try:
        data = request.json
        student_text = data.get('student_text')
        english_meaning = data.get('english_meaning')
        
        if not student_text:
            return jsonify({'error': 'No text provided'}), 400
        
        print(f"\n{'='*50}")
        print(f"STUDENT: {student_text}")
        print(f"ENGLISH: {english_meaning}")
        
        # Try Groq AI first (best quality)
        if GROQ_API_KEY:
            print("Using Groq AI...")
            response = correct_with_groq(student_text, english_meaning)
            if response:
                print(f"CORRECTION: {response.get('correction', 'None')}")
                print(f"{'='*50}\n")
                return jsonify(response)
        
        # Fallback to pattern matching
        print("Using pattern matching fallback...")
        response = correct_with_patterns(student_text, english_meaning)
        print(f"{'='*50}\n")
        return jsonify(response)
        
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({'error': str(e)}), 500


# --- Helper Functions ---

def correct_with_groq(student_text, english_meaning):
    """Use Groq AI with two-step verification to avoid false positives"""
    if not GROQ_API_KEY:
        return None
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        # STEP 1: First ask if there's actually an error
        check_prompt = f"""You are a strict German grammar checker.

Student sentence: "{student_text}"

CRITICAL: IGNORE ALL PUNCTUATION! Commas, periods, etc. are NOT grammar errors!

Does this have a REAL grammar error?

IGNORE (these are NOT errors):
- Missing commas ✓ OK
- Missing periods ✓ OK  
- Missing quotes ✓ OK
- Capitalization ✓ OK
- Style ✓ OK

ONLY flag these REAL errors:
- Wrong verb conjugation: "ich brauchst" ✗
- Wrong verb position: "ich Hilfe brauche" ✗
- Wrong pronoun: "wie heißt mich" ✗
- Nonsense: "ich bin 20 und 5 Jahre alt" ✗

CORRECT examples (answer NO):
- "hallo ich heiße Mustang wie geht's" ✓ NO ERROR
- "mein Name ist Mustang und was ist dein Name" ✓ NO ERROR
- "ich heiße Anna und wie heißt du" ✓ NO ERROR
- "ich brauche Hilfe danke" ✓ NO ERROR

WRONG examples (answer YES):
- "ich Hilfe brauche" ✗ YES ERROR (verb position)
- "ich brauchst Hilfe" ✗ YES ERROR (conjugation)

If only punctuation is missing, answer: NO

Answer ONLY: YES or NO"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Step 1: Check if there's an error
        payload1 = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": check_prompt}],
            "temperature": 0.0,  # Zero creativity
            "max_tokens": 10
        }
        
        response1 = requests.post(url, headers=headers, json=payload1, timeout=10)
        
        if response1.status_code != 200:
            print(f"Groq API error: {response1.status_code}")
            return None
        
        result1 = response1.json()
        has_error_check = result1['choices'][0]['message']['content'].strip().upper()
        
        print(f"Error check: {has_error_check}")
        
        # If NO error detected, return perfect
        if "NO" in has_error_check or "KEIN" in has_error_check or "CORRECT" in has_error_check:
            return {
                'has_error': False,
                'german_response': "Perfekt, mach weiter.!",
                'english_translation': "Perfect, go ahead!",
                'correction': None
            }
        
        # STEP 2: Only if error found, ask for correction
        correction_prompt = f"""Student said: "{student_text}"

This has a grammar error. Give the correction.

IMPORTANT: Start your German response with "Du meinst:" followed by the correct sentence.

Example:
If student says "ich Hilfe brauche", respond:
GERMAN: Du meinst: "Ich brauche Hilfe"
ENGLISH: You mean: "I need help"
FIX: Verb must be in second position

Format:
GERMAN: Du meinst: [correct sentence in quotes]
ENGLISH: You mean: [translation]
FIX: [Brief one-line explanation of the error]"""

        payload2 = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": correction_prompt}],
            "temperature": 0.2,
            "max_tokens": 300
        }
        
        response2 = requests.post(url, headers=headers, json=payload2, timeout=15)
        
        if response2.status_code == 200:
            result2 = response2.json()
            content = result2['choices'][0]['message']['content']
            
            # Parse response
            german = extract_line(content, "GERMAN:")
            english = extract_line(content, "ENGLISH:")
            fix = extract_line(content, "FIX:")
            
            # POST-PROCESSING: If correction only mentions punctuation, reject it
            punctuation_keywords = ['comma', 'komma', 'period', 'punkt', 'punctuation', 'satzzeichen', 'capitalization', 'großschreibung']
            if fix:
                fix_lower = fix.lower()
                mentions_punctuation = any(keyword in fix_lower for keyword in punctuation_keywords)
                
                # Check if the ONLY issue is punctuation
                if mentions_punctuation:
                    # Check if there are real grammar words in the fix
                    grammar_keywords = ['verb', 'conjugation', 'position', 'pronoun', 'order', 'wortstellung', 'konjugation']
                    has_grammar_issue = any(keyword in fix_lower for keyword in grammar_keywords)
                    
                    if not has_grammar_issue:
                        # Only punctuation mentioned - reject this correction
                        print("REJECTED: Correction only mentions punctuation")
                        return {
                            'has_error': False,
                            'german_response': "Perfekt mach weiter.!",
                            'english_translation': "Perfect go ahead!",
                            'correction': None
                        }
            
            if german and english:
                return {
                    'has_error': True,
                    'german_response': german,
                    'english_translation': english,
                    'correction': fix if fix else None
                }
        
    except Exception as e:
        print(f"Groq error: {e}")
    
    return None


def extract_line(text, prefix):
    """Extract line starting with prefix"""
    try:
        lines = text.split('\n')
        for line in lines:
            if line.strip().startswith(prefix):
                return line.replace(prefix, '').strip()
        return ""
    except:
        return ""


def correct_with_patterns(student_text, english_meaning):
    """Enhanced fallback pattern matching"""
    
    words = student_text.lower().split()
    verbs = ['bin', 'bist', 'ist', 'sind', 'habe', 'hast', 'hat', 'haben', 
             'brauche', 'brauchst', 'braucht', 'brauchen', 
             'liebe', 'liebst', 'liebt', 'lieben', 'mag', 'magst']
    subjects = ['ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr']
    
    # Check 1: Word order (verb position)
    if len(words) >= 2 and words[0] in subjects:
        subject = words[0]
        verb_pos = None
        verb_word = None
        
        for i, word in enumerate(words):
            if word in verbs:
                verb_pos = i
                verb_word = word
                break
        
        if verb_word and verb_pos != 1:
            return {
                'has_error': True,
                'german_response': f"Falsche Wortstellung! Das Verb '{verb_word}' muss an zweiter Stelle stehen. Richtig: '{subject} {verb_word} ...'",
                'english_translation': f"Wrong word order! The verb '{verb_word}' must be in second position. Correct: '{subject} {verb_word} ...'",
                'correction': f"In German, the verb must be in second position. Say: '{subject} {verb_word} ...' not '{student_text}'"
            }
    
    # Check 2: Multiple pronouns
    if 'mich' in words and 'dich' in words:
        return {
            'has_error': True,
            'german_response': "Zu viele Pronomen! Für 'I love you' sag nur: 'Ich liebe dich' (ohne 'mich').",
            'english_translation': "Too many pronouns! For 'I love you' just say: 'Ich liebe dich' (without 'mich').",
            'correction': "Use 'Ich liebe dich' (I love you) OR 'Du liebst mich' (You love me) - not both pronouns together."
        }
    
    # Check 3: Wrong conjugation
    if "ich brauchst" in student_text.lower():
        return {
            'has_error': True,
            'german_response': "Falsch! Bei 'ich' sagst du 'brauche', nicht 'brauchst'. Richtig: 'ich brauche'.",
            'english_translation': "Wrong! With 'ich' you say 'brauche', not 'brauchst'. Correct: 'ich brauche'.",
            'correction': "Use 'ich brauche' not 'ich brauchst'. The verb ending '-st' is for 'du'."
        }
    
    # Check 4: wie heißt mich
    if "wie heißt mich" in student_text.lower() or "wie heißt mir" in student_text.lower():
        return {
            'has_error': True,
            'german_response': "Du meinst 'wie heißt du?' wenn du jemanden nach seinem Namen fragst. 'Mich' passt hier nicht.",
            'english_translation': "You mean 'what's your name?' when asking someone's name. 'Mich' doesn't fit here.",
            'correction': "Use 'wie heißt du?' to ask someone's name, not 'wie heißt mich'"
        }
    
    # Default: Suggest checking
    return {
        'has_error': False,
        'german_response': "Hmm, die Struktur wirkt ungewöhnlich. Versuch die Reihenfolge: Subjekt + Verb + Objekt.",
        'english_translation': "Hmm, the structure seems unusual. Try the order: Subject + Verb + Object.",
        'correction': "Check German word order rules: Subject-Verb-Object for main clauses."
    }
