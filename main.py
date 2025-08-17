import streamlit as st
import requests
import json
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="🏡 Apna Ghar Chatbot",
    page_icon="🏡",
    layout="centered" # Changed layout to centered for better visual appeal
)

# --- Title and Description ---
st.title("🏡 Apna Ghar Chatbot")
st.markdown("Your friendly AI assistant for all home-related queries, powered by OpenRouter!")

# --- OpenRouter API Key Input ---
# It's highly recommended to use st.secrets for production, but for demonstration, we'll use a direct input.
openrouter_api_key = st.text_input(
    "Enter your OpenRouter API Key:",
    type="password",
    help="You can get your API key from your OpenRouter dashboard."
)

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add an initial system message to guide the AI's behavior
    st.session_state.messages.append({"role": "system", "content": "You are Apna Ghar Chatbot, a friendly AI assistant focused on home-related queries, home decor, repairs, and general household advice. Provide helpful and practical information."})


# --- Chat Message Display ---
chat_container = st.container()
with chat_container:
    # Filter out the system message for display, as it's not part of the user-AI conversation flow
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

# --- Function to interact with OpenRouter API ---
def get_openrouter_response(api_key, messages):
    """
    Sends messages to the OpenRouter API and retrieves a response.
    Implements exponential backoff for retries.
    """
    if not api_key:
        st.error("Please enter your OpenRouter API Key to chat.")
        return "Error: API key not provided."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://apnaghar-chatbot.streamlit.app", # Optional: Your site URL for OpenRouter rankings
        "X-Title": "Apna Ghar Chatbot", # Optional: Your site title for OpenRouter rankings
    }
    # OpenRouter expects a list of message objects with 'role' and 'content'
    # Ensure messages are in the correct format before sending
    formatted_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    data = {
        "model": "deepseek/deepseek-r1-distill-llama-70b:free", # Changed to the DeepSeek model
        "messages": formatted_messages,
        "temperature": 0.7, # Added temperature for more varied responses
        "max_tokens": 500 # Limit response length
    }

    retry_count = 0
    max_retries = 5
    base_delay = 1 # seconds

    while retry_count < max_retries:
        try:
            with st.spinner("Thinking..."):
                response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30) # Added timeout
                response.raise_for_status() # Raise an exception for HTTP errors
                return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            if 500 <= e.response.status_code < 600: # Server error, retry
                delay = base_delay * (2 ** retry_count)
                st.warning(f"Server error ({e.response.status_code}). Retrying in {delay} seconds...")
                time.sleep(delay)
                retry_count += 1
            else: # Client error or other HTTP error, don't retry
                st.error(f"API Error: {e.response.status_code} - {e.response.text}")
                return "Error: Could not get a response from the API."
        except requests.exceptions.ConnectionError:
            delay = base_delay * (2 ** retry_count)
            st.warning(f"Connection error. Retrying in {delay} seconds...")
            time.sleep(delay)
            retry_count += 1
        except requests.exceptions.Timeout:
            delay = base_delay * (2 ** retry_count)
            st.warning(f"Request timed out. Retrying in {delay} seconds...")
            time.sleep(delay)
            retry_count += 1
        except json.JSONDecodeError:
            st.error("Error: Could not decode JSON response from API.")
            return "Error: Invalid response from API."
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            return "Error: An unexpected issue occurred."
    st.error("Max retries exceeded. Please try again later.")
    return "Error: Max retries exceeded."


# --- User Input and Chat Logic ---
if prompt := st.chat_input("Ask about anything related to 'Apna Ghar'..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

    # Get AI response
    ai_response = get_openrouter_response(openrouter_api_key, st.session_state.messages)

    # Add AI response to chat history
    st.session_state.messages.append({"role": "assistant", "content": ai_response})

    # Display AI response
    with chat_container:
        with st.chat_message("assistant"):
            st.markdown(ai_response)
