# Voice Translator with AI German Tutor

A powerful dual-mode application that serves as both a voice translator and a personal language tutor.

## Features

- **Translation Mode**: Bi-directional translation between English and German. It translates your text or voice input directly without any corrections, perfect for quick communication.
- **AI German Tutor Mode**: Dedicated learning tool that analyzes your German input. verifying it against the intended English meaning. It uses Groq AI to correct grammar, explain mistakes, and suggest native-sounding improvements.
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

## Usage

1.  **Start the application**
    ```bash
    python app.py
    ```

2.  **Access the web interface**
    Open your browser and navigate to `http://localhost:5000`.

3.  **Login/Register**
    - The first user registered becomes the **Admin**.
    - Subsequent users are regular **Users**.

## Technologies

- **Flask**: Web framework
- **Groq API**: AI-powered language corrections
- **Google Speech Recognition**: Audio-to-text conversion
- **gTTS**: Text-to-Speech generation
- **SQLite**: Database for user and history management
