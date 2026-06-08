from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler
from MythicRPG import dispatcher

def alive_cmd(update: Update, context: CallbackContext):
    with open("MythicRPG/assets/alive.png", "rb") as photo:
        update.effective_message.reply_photo(
            photo=photo,
            caption=(
                "🔮 <b>I am ALIVE, Commander!</b>\n\n"
                "The empire awaits your orders. Build your kingdom, summon heroes, "
                "and conquer the world bosses!\n\n"
                "<i>Use /help or /start to explore the realm.</i>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Support Group", url="https://t.me/TSB_Council")]
            ])
        )

__help__ = """
*Age of Telegram: Alive*
 ❍ /alive*:* Check if the bot is awake and ready for battle.
"""

__mod_name__ = "Aʟɪᴠᴇ"

ALIVE_HANDLER = CommandHandler("alive", alive_cmd, run_async=True)
dispatcher.add_handler(ALIVE_HANDLER)
__handlers__ = [ALIVE_HANDLER]
