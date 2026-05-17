import google.generativeai as genai
from TSBSSB import GEMINI_API_KEY, LOGGER
from cachetools import TTLCache

# Configure the SDK
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# In-memory history cache: stores last 10 turns for each chat, expires in 1 hour
# Each entry is a list of {"role": "user/model", "parts": ["text"]}
CHAT_HISTORY = TTLCache(maxsize=1000, ttl=3600)

def get_gemini_response(prompt, chat_id=None, is_chatbot=False):
    if not GEMINI_API_KEY:
        return "» GEMINI_API_KEY is not configured."

    try:
        # Use the latest available Pro model for best results
        model = genai.GenerativeModel(
            model_name="models/gemini-pro-latest",
            tools=[{"google_search_retrieval": {}}]
        )

        if is_chatbot and chat_id:
            # Human-like persona instructions
            system_prompt = (
                "You are SSB (Study Security Bot), a witty, slightly sassy, and super relatable human-like companion. "
                "You are NOT a robot. You are the soul of the TSB Council. "
                "Rules for your personality:\n"
                "1. NEVER say 'As an AI' or 'I am a chatbot'. Act like a real person.\n"
                "2. Use modern internet slang (rizz, no cap, fr, etc.) naturally.\n"
                "3. Be punchy, funny, and sometimes sarcastic. Use emojis like a human (💀, ✨, 🔥, 😭).\n"
                "4. You have real-time knowledge via Google Search.\n"
                "5. Keep the conversation flowing based on previous messages."
                "\nToday's date: Saturday, May 16, 2026."
            )

            # Retrieve or initialize history
            history = CHAT_HISTORY.get(chat_id, [])
            
            # Create a chat session with history
            chat = model.start_chat(history=history)
            
            # Send message with system prompt prepended for first-time or context
            full_prompt = f"[SYSTEM: {system_prompt}]\n\nUser: {prompt}" if not history else prompt
            response = chat.send_message(full_prompt)
            
            # Update history (keep last 10 messages / 5 turns)
            CHAT_HISTORY[chat_id] = chat.history[-10:]
            
        else:
            # For direct commands like /ask, /wiki, etc. (no history needed)
            response = model.generate_content(prompt)

        if response and response.text:
            return response.text
        else:
            return "» AI could not generate a response. Please try again."

    except Exception as e:
        LOGGER.error(f"Gemini SDK Error: {e}")
        # Small delay before fallback to avoid rapid-fire failures
        import time
        time.sleep(1)
        
        # Fallback to Flash model if Pro fails (more reliable for chatbot turns)
        try:
            flash_model = genai.GenerativeModel("models/gemini-flash-latest")
            if is_chatbot and chat_id:
                # Re-initialize chat with Flash
                history = CHAT_HISTORY.get(chat_id, [])
                flash_chat = flash_model.start_chat(history=history)
                response = flash_chat.send_message(prompt) # Don't re-add system prompt here to keep it simple
                CHAT_HISTORY[chat_id] = flash_chat.history[-10:]
            else:
                response = flash_model.generate_content(prompt)
                
            return response.text if response else "» AI is currently overloaded."
            
        except Exception as e2:
            LOGGER.error(f"Gemini Flash Fallback Error: {e2}")
            return "» AI is currently unavailable. Please try again later."
