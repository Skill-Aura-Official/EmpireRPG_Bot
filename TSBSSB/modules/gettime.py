import requests
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from TSBSSB import GEMINI_API_KEY, dispatcher
from TSBSSB.modules.disable import DisableAbleCommandHandler
from TSBSSB.modules.helper_funcs.gemini_helper import get_gemini_response

# get_gemini_response removed, now using central helper

def gettime(update: Update, context: CallbackContext):
    message = update.effective_message
    try:
        query = message.text.strip().split(" ", 1)[1]
    except IndexError:
        return message.reply_text("» ᴩʟᴇᴀsᴇ sᴩᴇᴄɪғʏ ᴀ ʟᴏᴄᴀᴛɪᴏɴ!\nExample: `/time India`")

    msg = message.reply_text(f"» Fetching time for <b>{query}</b>...", parse_mode=ParseMode.HTML)
    prompt = f"What is the current local time and date in {query}? Format the output cleanly with Country, Timezone, Time, and Date. Be concise."
    answer = get_gemini_response(prompt)
    msg.edit_text(answer, parse_mode=ParseMode.MARKDOWN)

__help__ = """
*Time Features*
 ❍ /time <location>*:* Get the current local time and date for any location globally via AI.
"""

TIME_HANDLER = DisableAbleCommandHandler("time", gettime, run_async=True)
dispatcher.add_handler(TIME_HANDLER)

__mod_name__ = "Tɪᴍᴇ"
__handlers__ = [TIME_HANDLER]

