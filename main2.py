import streamlit as st
import requests
import speech_recognition as sr
import pyttsx3
import tempfile
import os

# 🔑 Your OpenRouter API key
API_KEY = "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"  
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Initialize recognizer and TTS ---
recognizer = sr.Recognizer()
tts = pyttsx3.init()

def speak(text):
    """Convert text to speech and return audio file path"""
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save_to_file(text, tmp_file.name)
    tts.runAndWait()
    return tmp_file.name

def listen():
    """Capture voice input and convert to text"""
    with sr.Microphone() as source:
        st.info("🎤 Listening... Speak now!")
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
    try:
        query = recognizer.recognize_google(audio)
        return query
    except sr.UnknownValueError:
        return "Sorry, I could not understand."
    except sr.RequestError:
        return "Network error."

def ask_api(query):
    """Send query to OpenRouter API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-3.5-turbo",  
        "messages": [{"role": "user", "content": query}]
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

# --- Streamlit UI ---
st.set_page_config(page_title="🎤 Voice Chatbot", page_icon="🤖", layout="centered")
st.title("🎤 Voice Chatbot with OpenRouter")
st.markdown("Talk to the AI using your microphone!")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- User controls ---
col1, col2 = st.columns(2)
with col1:
    if st.button("🎙️ Speak"):
        query = listen()
        st.session_state.chat_history.append(("You", query))

        if query.lower() in ["exit", "quit", "stop", "bye"]:
            st.session_state.chat_history.append(("Bot", "Goodbye!"))
        else:
            response = ask_api(query)
            st.session_state.chat_history.append(("Bot", response))

            # Speak response
            audio_path = speak(response)
            st.audio(audio_path, format="audio/mp3")
            os.remove(audio_path)

with col2:
    user_text = st.text_input("💬 Or type your message:")
    if st.button("Send") and user_text:
        st.session_state.chat_history.append(("You", user_text))
        response = ask_api(user_text)
        st.session_state.chat_history.append(("Bot", response))

        # Speak response
        audio_path = speak(response)
        st.audio(audio_path, format="audio/mp3")
        os.remove(audio_path)

# --- Display chat history ---
st.subheader("📜 Chat History")
for sender, msg in st.session_state.chat_history:
    if sender == "You":
        st.markdown(f"**🧑 You:** {msg}")
    else:
        st.markdown(f"**🤖 Bot:** {msg}")
