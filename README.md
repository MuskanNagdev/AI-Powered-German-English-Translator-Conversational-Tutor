# Voice Translator with AI German Tutor

A powerful dual-mode application that serves as both a voice translator and a personal language tutor.

## Features

- **Translation Mode**: Bi-directional translation between English and German. It translates your text or voice input directly without any corrections, perfect for quick communication.
- **AI German Tutor Mode**: Dedicated conversational partner.
    - **Conversational**: Remembers context and chat history.
    - **Smart Corrections**: Pauses to correct errors ("Du meinst...") but ignores small mistakes like capitalization or punctuation.
    - **Memory**: Tracks your weak points to personalize future sessions.
- **History Tracking**: Saves translation history with detailed stats.
- **User System**: Secure login, registration, and role-based access (User/Admin).
- **Admin Dashboard**: View all user activities and statistics.
- **Text-to-Speech**: Listen to translated text and corrections.

## Prerequisites

- **Python 3.8+**
- **FFmpeg**: Required for audio processing (used by `pydub` and `SpeechRecognition`).
  - *Windows*: Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add the `bin` folder to your system PATH.
  - *Mac*: `brew install ffmpeg`
  - *Linux*: `sudo apt install ffmpeg`

## Installation

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd foldername
    ```

2.  **Create a virtual environment**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables**
    Create a `.env` file in the root directory:
    ```env
    GROQ_API_KEY=gsk_...
    JIGSAWSTACK_API_KEY=...
    ```

## 📖 User Guide

### 1. Getting Started
1.  **Run the Server**: Open your terminal in the project folder and run:
    ```bash
    python app.py
    ```
2.  **Open Browser**: Go to [http://localhost:5000](http://localhost:5000).
3.  **Login/Register**:
    *   Click **Register** to create an account.
    *   **Note**: The *first* user to ever register is automatically granted **Admin** privileges.

### 2. Using the Voice Translator 🌐
*   **Switch Tab**: Click the "Translater" tab at the top.
*   **Select Language**: Toggle flags to switch between **English → German** or **German → English**.
*   **Record**:
    1.  Click **Start Recording** (Red Button).
    2.  Speak into your microphone.
    3.  Click **Stop Recording** (Amber Button) when finished.
*   **Translate**:
    *   The text appears in the "Original Text" box. You can edit it manually if needed.
    *   Click **Translate** (Blue Button) to process.
*   **Listen**: Click the **Speaker Icon** 🔊 below the translation to hear it spoken aloud.

### 3. Using the AI German Tutor 👨‍🏫
*   **Switch Tab**: Click the "AI German Tutor" tab.
*   **Start Chat**:
    *   Click **Speak German** (Blue Button).
    *   Say a sentence (e.g., "Hallo, wie geht es dir?").
    *   The AI will process your input and reply with audio.
*   **Correction Logic** (Smart Teacher):
    *   **Perfect Grammar**: The AI affirms you ("Genau!", "Das ist richtig!") and asks a follow-up question.
    *   **Mistakes**: The AI pauses and gently corrects you by saying *"Du meinst: [Correct Sentence]"*. It waits for you to repeat it correctly before effectively moving on.
    *   **Ignored Errors**: The AI is programmed to **ignore** trivial mistakes like capitalization (e.g., "hunger" vs "Hunger") or missing punctuation, so you don't get annoyed by false corrections.

### 4. Admin Dashboard 🛠
*   **Access**: Only available if you are the Admin (first registered user).
*   **Location**: Click the "Admin" badge in the top-right header.
*   **Features**:
    *   View all registered users.
    *   See a global log of all translations made by all users.
    *   Clear system-wide history.

### 5. Troubleshooting
*   **Microphone Issue**: Ensure your browser has permission to access the microphone (look for a lock/camera icon in the address bar).
*   **Audio Not Playing**: Check if your system volume is up. Some browsers block auto-play until you interact with the page.
*   **API Errors**: If the AI doesn't respond, check your terminal for error messages. Ensure your `.env` file has valid `GROQ_API_KEY` and `JIGSAWSTACK_API_KEY`.

## Technologies

- **Flask**: Web framework
- **Groq API**: AI-powered language corrections
- **Google Speech Recognition**: Audio-to-text conversion
- **gTTS**: Text-to-Speech generation
- **SQLite**: Database for user and history management
