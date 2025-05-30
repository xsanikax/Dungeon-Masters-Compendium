import streamlit as st
import google.generativeai as genai
import os # Optional: useful for local environment variable fallback

# --- Page Configuration (Sets tab title, icon, and layout) ---
st.set_page_config(
    page_title="The Dungeon Master's Compendium",
    page_icon="📜", # You can use an emoji or a URL to an image
    layout="wide" # Can be "centered" or "wide"
)

# --- API Key Configuration ---
# For Streamlit Community Cloud deployment, set your API key as a "secret"
# in your app's settings on share.streamlit.io. It will be available via st.secrets

GEMINI_API_KEY = "" # Initialize as empty

try:
    # Try to get the API key from Streamlit secrets (for deployed app)
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except (KeyError, AttributeError):
    # This block runs if st.secrets["GEMINI_API_KEY"] is not found.
    # This will be the case when you run locally if you haven't configured local secrets.
    st.warning(
        "GEMINI_API_KEY not found in Streamlit secrets. "
        "If running locally, provide your API key directly in the script for testing "
        "(and ensure it's not committed to GitHub) or set it as an environment variable."
    )
    # FOR LOCAL TESTING ONLY:
    # Option 1: Paste your key here for local testing.
    # IMPORTANT: If you uncomment and use this, DO NOT commit this line with your actual key to GitHub.
    # GEMINI_API_KEY = "YOUR_LOCAL_TEST_API_KEY_HERE"

    # Option 2: Or, try to get it from an environment variable (another good local method)
    # if not GEMINI_API_KEY: # If still empty after trying secrets
    #     GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    pass # GEMINI_API_KEY will remain empty if not found via secrets or set locally

# --- Initialize the Generative AI Model ---
model = None # Initialize model to None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name="gemini-1.5-flash") # Fast and versatile for chat
    except Exception as e:
        st.error(f"Error initializing the AI model: {e}. Check your API key configuration.")
else:
    # This error will show if the app is run without any API key configured
    st.error(
        "Gemini API Key not configured. "
        "For deployed apps, set it in Streamlit Cloud secrets. "
        "For local use, provide it in the script (for testing only) or as an environment variable."
    )

# --- Streamlit App UI ---
st.title("📜 The Dungeon Master's Compendium")
st.caption("Your AI assistant for crafting D&D narratives, rumors, NPCs, and more!")

# --- Initialize chat history in session state (persists across reruns) ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome, Dungeon Master! What lore shall we weave today?"}]

# --- Display existing chat messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]): # "user" or "assistant"
        st.markdown(message["content"]) # Markdown allows for richer text formatting

# --- Chat Input from User ---
# The `key` argument for `st.chat_input` can be used if you need to uniquely identify it,
# but often it's not necessary for a single input.
user_prompt = st.chat_input("Your message or prompt to the AI...")

if user_prompt:
    # Add user message to chat history and display it immediately
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # --- Get AI Response (if model is initialized and there's a user prompt) ---
    if model:
        try:
            # Prepare chat history for the API:
            # The API expects roles "user" and "model". Our "assistant" role maps to "model".
            api_chat_history = []
            for msg in st.session_state.messages:
                role_for_api = "model" if msg["role"] == "assistant" else msg["role"]
                api_chat_history.append({
                    "role": role_for_api,
                    "parts": [{"text": msg["content"]}]
                })
            
            # Generate content using the prepared chat history
            response = model.generate_content(api_chat_history)

            ai_response_text = ""
            if response.parts:
                ai_response_text = response.text
            elif response.text: # Fallback for some cases
                 ai_response_text = response.text
            # Handle cases where the response might be blocked due to safety settings, etc.
            elif response.prompt_feedback and response.prompt_feedback.block_reason:
                ai_response_text = (
                    f"Sorry, I couldn't generate a response for that. "
                    f"Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                )
            else:
                ai_response_text = "The AI seems to be pondering... (No text part in response, or unknown issue)"
            
            # Add AI response to chat history and display it
            st.session_state.messages.append({"role": "assistant", "content": ai_response_text})
            with st.chat_message("assistant"):
                st.markdown(ai_response_text)
            
        except Exception as e:
            st.error(f"Error getting response from AI: {e}")
            # Optionally, add the error to the chat display for the user
            st.session_state.messages.append({"role": "assistant", "content": f"Sorry, an error occurred while contacting the AI: {e}"})
            with st.chat_message("assistant"):
                st.markdown(f"Sorry, an error occurred while contacting the AI: {e}")
    else:
        st.warning("AI model not initialized. Cannot process your request. Please check API key configuration.")

# --- Sidebar Content ---
with st.sidebar:
    st.header("Controls")
    if st.button("✨ New Story/Topic"):
        # Clear chat history and add a fresh welcome message
        st.session_state.messages = [{"role": "assistant", "content": "Alright, a fresh parchment! What new ideas shall we explore?"}]
        st.rerun() # Rerun the app to reflect the cleared state

    st.markdown("---")
    st.markdown("Built with Gemini & Streamlit")
    st.markdown(f"Current time in Nottingham: {st.session_state.get('current_time_nottingham', 'Loading...')}", unsafe_allow_html=True)


# --- Optional: Display current time in Nottingham (as an example of dynamic sidebar content) ---
# This part is just for fun, can be removed if not needed.
# It requires an additional function to fetch time or just display based on server time if deployed.
# For simplicity, let's just put a placeholder in the sidebar that could be updated.
# You could use JavaScript in st.markdown or a more complex setup for live time.
import datetime
import pytz
try:
    nottingham_tz = pytz.timezone('Europe/London')
    nottingham_time = datetime.datetime.now(nottingham_tz).strftime("%H:%M:%S %Z (%Y-%m-%d)")
    st.session_state.current_time_nottingham = nottingham_time
except Exception as e:
    st.session_state.current_time_nottingham = "Could not fetch time."

# To ensure the sidebar updates with time if it's the first run.
if 'current_time_nottingham_displayed_once' not in st.session_state:
    st.session_state.current_time_nottingham_displayed_once = True
    st.rerun()