# app.py
import os
import json
import time
import requests
import streamlit as st

# -------------------------------
# Page Configuration & Theming
# -------------------------------
st.set_page_config(
    page_title="🏡 Apna Ghar Chatbot",
    page_icon="🏡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Minimal, responsive CSS for a clean, chat-like UI
st.markdown("""
<style>
/* Page width tweaks */
.block-container { padding-top: 1.5rem; max-width: 860px; }

/* Chat bubbles */
.chat-bubble { border-radius: 18px; padding: 12px 14px; margin: 6px 0; word-wrap: break-word; }
.user-bubble   { background: #e8f0fe; border: 1px solid #d2e3fc; }
.ai-bubble     { background: #f8f9fa; border: 1px solid #e6e9ef; }

/* Avatars */
.avatar { width: 32px; height: 32px; border-radius: 50%; display: inline-block; margin-right: 10px; }
.user-avatar { background: #1a73e8; }
.ai-avatar   { background: #34a853; }

/* Message row */
.msg-row { display: flex; align-items: flex-start; gap: 10px; }
.msg-wrap { flex: 1; }

/* Input dock */
.input-dock {
  position: sticky; bottom: 0; z-index: 5;
  padding: 12px; background: white; border-top: 1px solid #eee; backdrop-filter: blur(6px);
}

/* Buttons */
button[kind="primary"] { border-radius: 12px; }

/* Small text */
.small { font-size: 12px; color: #6b7280; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# App Header
# -------------------------------
st.title("🏡 Apna Ghar Chatbot")
st.caption("Your friendly AI assistant for home-related queries — powered by OpenRouter’s **openai/gpt-3.5-turbo**.")

# -------------------------------
# Secrets / API Key Handling
# -------------------------------
def resolve_api_key() -> str | None:
    # Preferred: Streamlit secrets
    try:
        return st.secrets["openrouter"]["api_key"]
    except Exception:
        pass
    # Fallback: environment variable
    return os.getenv("OPENROUTER_API_KEY")

with st.expander("🔐 API Settings", expanded=False):
    st.write("For production, store your key in **.streamlit/secrets.toml** or set the **OPENROUTER_API_KEY** environment variable.")
    st.code(
        '[openrouter]\napi_key = "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"',
        language="toml",
    )
    st.code('export OPENROUTER_API_KEY="sk-or-xxxxxxxxxxxxxxxxxxxxxxxx"', language="bash")
    manual_key = st.text_input("Or paste your OpenRouter API key here", type="password")

api_key = manual_key or resolve_api_key()

# -------------------------------
# Session State
# -------------------------------
if "messages" not in st.session_state:
    # Seed with a friendly system prompt for consistent tone
    st.session_state.messages = [
        {"role": "system", "content": "You are Apna Ghar Chatbot, a concise, helpful assistant for home-related queries in India. Keep answers clear, practical, and polite."}
    ]

# Keep only the latest 30 messages (including system)
if len(st.session_state.messages) > 30:
    st.session_state.messages = [st.session_state.messages[0]] + st.session_state.messages[-29:]

# -------------------------------
# OpenRouter Client
# -------------------------------
def ask_openrouter(api_key: str, messages: list[dict]) -> str:
    if not api_key:
        return "Error: Missing OpenRouter API key. Add it via the API Settings panel."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional but recommended for OpenRouter analytics/routing:
        # "HTTP-Referer": "https://your-app-url.com",
        # "X-Title": "Apna Ghar Chatbot",
    }
    # Only send role/content pairs
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
        "temperature": 0.7,
        "max_tokens": 600
    }

    # Robust retries with exponential backoff on transient errors
    retry, max_retries, base = 0, 4, 1.0
    while retry <= max_retries:
        try:
            with st.spinner("Thinking…"):
                resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            if resp.status_code == 200:
                j = resp.json()
                return j["choices"][0]["message"]["content"]
            elif 500 <= resp.status_code < 600:
                # transient server error
                delay = base * (2 ** retry)
                st.info(f"Server is busy (HTTP {resp.status_code}). Retrying in {delay:.0f}s…")
                time.sleep(delay)
                retry += 1
            else:
                # client or non-retryable error
                return f"API Error ({resp.status_code}): {resp.text[:500]}"
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            delay = base * (2 ** retry)
            st.info(f"Network issue. Retrying in {delay:.0f}s…")
            time.sleep(delay)
            retry += 1
        except Exception as e:
            return f"Unexpected error: {e}"
    return "Error: Max retries exceeded. Please try again in a moment."

# -------------------------------
# Chat History Display
# -------------------------------
chat_box = st.container()
with chat_box:
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
        is_user = msg["role"] == "user"
        avatar_cls = "user-avatar" if is_user else "ai-avatar"
        bubble_cls = "user-bubble" if is_user else "ai-bubble"
        with st.container():
            st.markdown(
                f"""
                <div class="msg-row">
                    <span class="avatar {avatar_cls}"></span>
                    <div class="msg-wrap">
                        <div class="chat-bubble {bubble_cls}">{msg["content"]}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# -------------------------------
# Input Dock (Styled input + Send)
# -------------------------------
st.markdown('<div class="input-dock">', unsafe_allow_html=True)
with st.form("prompt_form", clear_on_submit=True):
    user_prompt = st.text_area(
        "Type your message",
        placeholder="Ask anything about buying, renting, maintenance, paperwork, locality insights, budgeting, etc.",
        label_visibility="collapsed",
        height=80,
    )
    cols = st.columns([1, 1, 6])
    with cols[0]:
        send = st.form_submit_button("Send", use_container_width=True)
    with cols[1]:
        reset = st.form_submit_button("Clear", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# Handle Clear
if reset:
    st.session_state.messages = st.session_state.messages[:1]  # keep only system
    st.rerun()

# Handle Send
if send and user_prompt and user_prompt.strip():
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_prompt.strip()})
    # Ask API
    reply = ask_openrouter(api_key, st.session_state.messages)
    # Append assistant reply (even if it's an error string — to show feedback inline)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    # Refresh view after each input (explicit rerun)
    st.rerun()

# Helpful note if key missing
if not api_key:
    st.info("Add your OpenRouter API key via **API Settings** (or set `OPENROUTER_API_KEY`).")
