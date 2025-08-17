import streamlit as st
import requests
import json
import streamlit.components.v1 as components

# --- Streamlit Secrets for API Key ---
# Instructions will be provided below on how to set this up.
# For local testing, create a .streamlit/secrets.toml file in your project directory
# with openrouter_api_key = "sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE"
API_KEY = st.secrets.get("openrouter_api_key")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- HTML/JavaScript for Browser-based Speech-to-Text and Text-to-Speech ---
# This JavaScript component runs in the user's browser.
# It uses the Web Speech API for microphone input and audio output.
# - It sends recognized speech text to Streamlit using `Streamlit.setComponentValue`.
# - It receives text to speak from Streamlit via `args` and speaks it automatically.
# - A unique ID (timestamp) is sent with each speech input to prevent reprocessing on Streamlit's side.
speech_component_html = """
<script src="https://cdn.jsdelivr.net/npm/@streamlit/streamlit-component-lib/dist/streamlit-component-lib.js"></script>
<div style="text-align: center; padding: 10px;">
    <button id="listenButton" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; border-radius: 8px; border: none;">
        🎤 Listen
    </button>
    <button id="speakButton" style="background-color: #008CBA; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; border-radius: 8px; border: none;">
        🔊 Speak Response
    </button>
    <div id="status" style="margin-top: 10px; font-style: italic;">Ready</div>
    <!-- Hidden div to receive text from Streamlit for speech synthesis -->
    <div id="textToSpeakHidden" style="display: none;"></div>
</div>

<script>
    const listenButton = document.getElementById('listenButton');
    const speakButton = document.getElementById('speakButton');
    const statusDiv = document.getElementById('status');
    const textToSpeakHidden = document.getElementById('textToSpeakHidden');

    let recognition;
    let speaking = false;
    let currentSpeechText = ""; // Stores the text currently being spoken or received from Streamlit

    // Helper function to send data back to Streamlit
    function sendToStreamlit(value) {
        if (window.Streamlit) {
            window.Streamlit.setComponentValue(value);
        }
    }

    // --- Speech Recognition (Microphone Input) ---
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
        recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.continuous = false; // Listen for a single utterance
        recognition.lang = 'en-US'; // Set recognition language
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = function() {
            statusDiv.textContent = '🎤 Listening... Say something!';
            listenButton.disabled = true; // Disable button while listening
        };

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            statusDiv.textContent = '👉 You said: ' + transcript;
            // Send recognized text with a unique timestamp ID to Streamlit
            sendToStreamlit({ type: 'speech_input', text: transcript, id: Date.now() });
        };

        recognition.onerror = function(event) {
            statusDiv.textContent = 'Error: ' + event.error;
            console.error('Speech recognition error', event.error);
            sendToStreamlit({ type: 'error', message: event.error, id: Date.now() }); // Send error back
        };

        recognition.onend = function() {
            statusDiv.textContent = 'Ready';
            listenButton.disabled = false; // Re-enable button after listening ends
        };

        listenButton.addEventListener('click', function() {
            if (!speaking) { // Prevent listening while TTS is active
                recognition.start();
            }
        });

    } else {
        statusDiv.textContent = 'Speech Recognition not supported in this browser.';
        listenButton.disabled = true;
    }

    // --- Speech Synthesis (Text-to-Speech Output) ---
    if ('speechSynthesis' in window) {
        function speakCurrentText() {
            if (currentSpeechText && !speaking) {
                const utterance = new SpeechSynthesisUtterance(currentSpeechText);
                utterance.lang = 'en-US'; // Set speech language
                utterance.onstart = () => {
                    speaking = true;
                    speakButton.disabled = true;
                    listenButton.disabled = true; // Disable listen while speaking
                    statusDiv.textContent = '🔊 Speaking...';
                };
                utterance.onend = () => {
                    speaking = false;
                    speakButton.disabled = false;
                    listenButton.disabled = false;
                    statusDiv.textContent = 'Ready';
                    currentSpeechText = ""; // Clear text after speaking is done
                };
                utterance.onerror = (event) => {
                    speaking = false;
                    speakButton.disabled = false;
                    listenButton.disabled = false;
                    statusDiv.textContent = 'Speech synthesis error.';
                    console.error('Speech synthesis error', event);
                };
                window.speechSynthesis.speak(utterance);
            } else if (speaking) {
                // If already speaking, cancel the current speech
                window.speechSynthesis.cancel();
                speaking = false;
                speakButton.disabled = false;
                listenButton.disabled = false;
                statusDiv.textContent = 'Ready';
                currentSpeechText = ""; // Clear text on cancel
            }
        }

        speakButton.addEventListener('click', speakCurrentText);

        // This function is called by Streamlit when component arguments change
        function onRender(event) {
            const data = event.detail;
            if (data && data.args && data.args.text_to_speak) {
                const newText = data.args.text_to_speak;
                // Only speak if the text is new and not empty
                if (newText && newText !== currentSpeechText) {
                    currentSpeechText = newText;
                    speakCurrentText(); // Trigger speech automatically
                }
            }
            // Inform Streamlit that the component has rendered and its height
            window.Streamlit.setFrameHeight();
        }

        // Add event listener for Streamlit's render event
        Streamlit.events.addEventListener(Streamlit.RenderEvent, onRender);

        // Initially inform Streamlit that the component is ready to receive data
        Streamlit.setComponentReady();
    } else {
        statusDiv.textContent = 'Text-to-Speech not supported in this browser.';
        speakButton.disabled = true;
    }
</script>
"""

def ask_api(query):
    """Sends query to OpenRouter API and returns the AI's response."""
    if not API_KEY:
        st.error("OpenRouter API key not found. Please set it in Streamlit secrets.")
        return "Please set your OpenRouter API key in Streamlit secrets to enable AI responses."

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-3.5-turbo",  # You can change this to other models supported by OpenRouter
        "messages": [{"role": "user", "content": query}]
    }
    try:
        # Show a spinner while waiting for the API response
        with st.spinner("Thinking..."):
            response = requests.post(API_URL, headers=headers, json=data)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        st.error(f"API Request Error: {e}")
        return "Sorry, I'm having trouble connecting to the AI. Please try again later."
    except KeyError:
        st.error("Unexpected API response format. Check the model name or API documentation.")
        return "Sorry, I received an unexpected response from the AI."

# --- Streamlit App Layout and Logic ---
st.set_page_config(page_title="Voice Chatbot with OpenRouter", layout="centered")

st.title("🗣️ Voice Chatbot with OpenRouter AI")

st.markdown(
    """
    This application allows you to interact with an AI model via voice or text.
    It leverages your browser's built-in Speech-to-Text and Text-to-Speech capabilities.

    **Instructions:**
    1.  **Set your OpenRouter API Key:**
        If deploying on Streamlit Cloud, use their secret management. Locally,
        create a file named `.streamlit/secrets.toml` in your project's root directory
        and add your API key like this:
        ```toml
        openrouter_api_key = "sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE"
        ```
    2.  Click the "🎤 Listen" button and speak your query.
    3.  The bot's response will appear in the chat and will be automatically spoken aloud.
    4.  Click "🔊 Speak Response" if you want to hear the last bot response again.
    5.  You can also type your message in the text input field below.
    """
)

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = []
if "text_to_speak" not in st.session_state:
    st.session_state.text_to_speak = ""
if "last_processed_speech_id" not in st.session_state:
    st.session_state.last_processed_speech_id = None

# Display previous chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Render the custom HTML/JavaScript component for voice interaction
# We pass the `text_to_speak` from Streamlit's session state to the JavaScript component
# so it knows what to speak.
speech_input_result = components.html(
    speech_component_html,
    height=150, # Adjust height as needed to fit buttons and status
    key="speech_input_component", # Unique key for this component to receive its value
    args={"text_to_speak": st.session_state.text_to_speak} # Pass data to JS
)

# Retrieve the value sent back by the JavaScript component
# This value contains the recognized speech input (if any).
speech_data = st.session_state.get("speech_input_component")

# Process speech input if available and it's a new, unprocessed input
if speech_data and isinstance(speech_data, dict) and speech_data.get("type") == "speech_input":
    current_speech_id = speech_data.get("id")
    # Check if this speech input has already been processed to avoid loops
    if current_speech_id and current_speech_id != st.session_state.last_processed_speech_id:
        user_query = speech_data["text"]
        if user_query:
            # Append user's message to chat history and display
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            # Get AI response from OpenRouter API
            ai_response = ask_api(user_query)
            
            # Append AI's response to chat history and display
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.markdown(ai_response)
            
            # Set the AI response to be spoken by the JavaScript component
            st.session_state.text_to_speak = ai_response
            # Mark this speech input as processed
            st.session_state.last_processed_speech_id = current_speech_id
            # Rerun the app to update the `text_to_speak` argument passed to the component
            st.experimental_rerun()

# Fallback text input for manual typing
manual_query = st.chat_input("Type your message here:", key="manual_text_input")

if manual_query:
    # Append user's manual message to chat history and display
    st.session_state.messages.append({"role": "user", "content": manual_query})
    with st.chat_message("user"):
        st.markdown(manual_query)

    # Get AI response from OpenRouter API
    ai_response = ask_api(manual_query)
    
    # Append AI's response to chat history and display
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.markdown(ai_response)
    
    # Set the AI response to be spoken by the JavaScript component
    st.session_state.text_to_speak = ai_response
    # Rerun the app to ensure the component updates and speaks the new text
    st.experimental_rerun()
