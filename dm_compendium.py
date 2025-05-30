import streamlit as st
import google.generativeai as genai
import os
import base64 # For embedding the image
import datetime # For the Nottingham time example
import pytz     # For the Nottingham time example

# --- Helper function to load and encode image to Base64 ---
def get_image_as_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        # This error will now appear in the Streamlit app if the image is missing locally
        st.warning(f"Dragon image not found at '{path}'. Please ensure 'static/my_dragon.png' exists.")
        return None
    except Exception as e:
        st.warning(f"Error loading image at '{path}': {e}")
        return None

# --- Load and Prepare Dragon Banner HTML ---
dragon_banner_html_content = None # Use None to indicate not loaded initially
image_data_url = None

# Construct the path to the image within the 'static' folder
image_filename = "my_dragon.png" # Ensure this matches your image name
image_path = os.path.join("static", image_filename)

# Get the image as a Base64 string
b64_image_data = get_image_as_base64(image_path)
if b64_image_data:
    image_data_url = f"data:image/png;base64,{b64_image_data}"
# else: A warning is already issued by get_image_as_base64 if it fails

try:
    # This assumes 'dragon_banner.html' is in the same directory as this Python script
    with open("dragon_banner.html", "r", encoding="utf-8") as f:
        temp_html_content = f.read()
    
    if image_data_url: # Image data is ready, inject it
        dragon_banner_html_content = temp_html_content.replace(
            "DRAGON_IMAGE_DATA_URL_PLACEHOLDER", image_data_url
        )
    else: # Image data failed to load, but HTML template exists
        dragon_banner_html_content = temp_html_content 
        # The JS in dragon_banner.html (with its onerror handler for the image)
        # will show an error on the canvas if the placeholder isn't replaced.
        # We already warned about the image not loading via get_image_as_base64.
except FileNotFoundError:
    st.warning("dragon_banner.html not found. Banner will not be displayed.")
    # dragon_banner_html_content remains None
except Exception as e:
    st.warning(f"An error occurred while reading dragon_banner.html: {e}")
    # dragon_banner_html_content remains None


# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="The Dungeon Master's Compendium",
    page_icon="📜", 
    layout="wide" 
)

# --- Display the Dragon Banner ---
if dragon_banner_html_content:
    # If image_data_url was not set, the placeholder is still in dragon_banner_html_content.
    # The JavaScript's onerror for the image in dragon_banner.html will then trigger.
    st.components.v1.html(dragon_banner_html_content, height=360) 
# else: No banner HTML was loaded, a warning was already issued.


# --- API Key Configuration ---
# FOR LOCAL TESTING: Paste your API key directly below.
# IMPORTANT: If you use this, DO NOT commit this file with your actual key to GitHub.
# When deploying to Streamlit Cloud, make this an empty string: LOCAL_TEST_API_KEY = ""
# and set your key in st.secrets on Streamlit Cloud.
LOCAL_TEST_API_KEY = "" # <<< PASTE YOUR API KEY HERE FOR LOCAL RUNNING

GEMINI_API_KEY_TO_USE = ""

if LOCAL_TEST_API_KEY: 
    GEMINI_API_KEY_TO_USE = LOCAL_TEST_API_KEY
else:
    try:
        GEMINI_API_KEY_TO_USE = st.secrets["GEMINI_API_KEY"]
    except (KeyError, AttributeError, st.errors.SecretsNotFoundError):
        st.error(
            "GEMINI_API_KEY not found in Streamlit secrets. This app requires an API key to function."
        )

# --- Initialize the Generative AI Model ---
model = None 
if GEMINI_API_KEY_TO_USE:
    try:
        genai.configure(api_key=GEMINI_API_KEY_TO_USE)
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    except Exception as e:
        st.error(f"Error initializing the AI model: {e}. This could be due to an invalid API key or other configuration issues.")
else:
    st.error(
        "Gemini API Key is not configured. The application cannot contact the AI."
    )

# --- Streamlit App UI ---
st.title("📜 The Dungeon Master's Compendium")
st.caption("Your AI assistant for crafting D&D narratives, rumors, NPCs, and more!")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome, Dungeon Master! What lore shall we weave today?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]): 
        st.markdown(message["content"]) 

user_prompt = st.chat_input("Your message or prompt to the AI...")

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    if model: 
        try:
            api_chat_history = []
            for msg in st.session_state.messages:
                role_for_api = "model" if msg["role"] == "assistant" else msg["role"]
                api_chat_history.append({
                    "role": role_for_api,
                    "parts": [{"text": msg["content"]}]
                })
            
            response = model.generate_content(api_chat_history)
            ai_response_text = ""
            if response.parts:
                ai_response_text = response.text
            elif response.text: 
                 ai_response_text = response.text
            elif response.prompt_feedback and response.prompt_feedback.block_reason:
                ai_response_text = (
                    f"Sorry, I couldn't generate a response for that. "
                    f"Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                )
            else:
                ai_response_text = "The AI seems to be pondering... (No text part in response, or unknown issue)"
            
            st.session_state.messages.append({"role": "assistant", "content": ai_response_text})
            with st.chat_message("assistant"):
                st.markdown(ai_response_text)
            
        except Exception as e: 
            st.error(f"Error getting response from AI: {e}")
            st.session_state.messages.append({"role": "assistant", "content": f"Sorry, an error occurred while contacting the AI: {e}"})
            with st.chat_message("assistant"):
                st.markdown(f"Sorry, an error occurred while contacting the AI: {e}")
    else: 
        st.warning("AI model not initialized. Cannot process your request. Please check API key configuration.")

with st.sidebar:
    st.header("Controls")
    if st.button("✨ New Story/Topic"):
        st.session_state.messages = [{"role": "assistant", "content": "Alright, a fresh parchment! What new ideas shall we explore?"}]
        st.rerun() 

    st.markdown("---")
    st.markdown("Built with Gemini & Streamlit")
    
    if 'current_time_nottingham' not in st.session_state: 
        st.session_state.current_time_nottingham = 'Loading...'
    try:
        nottingham_tz = pytz.timezone('Europe/London') 
        nottingham_time = datetime.datetime.now(nottingham_tz).strftime("%H:%M:%S %Z (%Y-%m-%d)")
        st.session_state.current_time_nottingham = nottingham_time
    except Exception as e: 
        st.session_state.current_time_nottingham = "Could not fetch time." # Handles missing pytz too
    
    st.markdown(f"Current time in Nottingham: {st.session_state.current_time_nottingham}", unsafe_allow_html=True)

if 'current_time_nottingham_displayed_once' not in st.session_state:
    st.session_state.current_time_nottingham_displayed_once = True
    if st.session_state.current_time_nottingham not in ['Loading...', "Could not fetch time."]:
         st.rerun()