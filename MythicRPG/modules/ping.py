import time
from telegram import Update, ParseMode, InputMediaPhoto
from telegram.ext import CallbackContext, CommandHandler
from MythicRPG import dispatcher

def ping_cmd(update: Update, context: CallbackContext):
    start_time = time.time()
    message = update.effective_message.reply_text("⚔️ Striking the anvil...")
    end_time = time.time()
    
    ping_time = round((end_time - start_time) * 1000, 3)
    
    with open("MythicRPG/assets/ping.png", "rb") as photo:
        update.effective_message.reply_photo(
            photo=photo,
            caption=f"⚡ <b>PONG!</b>\n\n🛡️ <b>Response Time:</b> <code>{ping_time} ms</code>",
            parse_mode=ParseMode.HTML
        )
    message.delete()

__help__ = """
*Age of Telegram: Ping*
 ❍ /ping*:* Check the bot's response time to the server.
"""

__mod_name__ = "Pɪɴɢ"

PING_HANDLER = CommandHandler("ping", ping_cmd, run_async=True)
dispatcher.add_handler(PING_HANDLER)
__handlers__ = [PING_HANDLER]
