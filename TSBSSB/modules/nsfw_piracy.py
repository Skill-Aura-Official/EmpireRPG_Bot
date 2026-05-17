import re
import requests
import os
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, MessageHandler, Filters, CallbackQueryHandler
from telegram.error import BadRequest

from TSBSSB import dispatcher, SIGHTENGINE_API_USER, SIGHTENGINE_API_SECRET, LOGGER, DEV_USERS, OWNER_ID
from TSBSSB.modules.sql import safety_sql as sql
from TSBSSB.modules.helper_funcs.chat_status import user_admin, is_user_admin
from TSBSSB.modules.disable import DisableAbleCommandHandler

# --- PIRACY SIGNATURES ---
PIRACY_KEYWORDS = [
    r"magnet:\?xt=", r"\.torrent", r"RARBG", r"YTS", r"CRACKED", r"WEB-DL", r"DDP5\.1", r"HDRip", 
    r"BluRay", r"x264", r"x265", r"HEVC", r"BrRip", r"DVDRip", r"KORSUB", r"CAMRip", r"HDCAM",
    r"Full-Movie", r"Direct Download", r"ZippyShare", r"Mega\.nz", r"MediaFire", r"RapidGator"
]
PIRACY_REGEX = re.compile("|".join(PIRACY_KEYWORDS), re.IGNORECASE)

# --- NSFW DETECTION ---
def check_nsfw(file_path):
    if not SIGHTENGINE_API_USER or not SIGHTENGINE_API_SECRET:
        return False
        
    params = {
        'models': 'nudity-2.0,wad,offensive',
        'api_user': SIGHTENGINE_API_USER,
        'api_secret': SIGHTENGINE_API_SECRET
    }
    files = {'media': open(file_path, 'rb')}
    
    try:
        response = requests.post('https://api.sightengine.com/1.0/check.json', files=files, data=params)
        output = response.json()
        
        if output.get('status') == 'success':
            # Check for nudity
            nudity = output.get('nudity', {})
            # threshold > 0.85 for definite porn/sexual content
            if nudity.get('sexual_activity', 0) > 0.8 or nudity.get('sexual_display', 0) > 0.8 or nudity.get('erotica', 0) > 0.8:
                return True
        return False
    except Exception as e:
        LOGGER.error(f"Sightengine Error: {e}")
        return False

# --- HANDLERS ---
def safety_monitor(update: Update, context: CallbackContext):
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user

    if not chat or not message or not user:
        return

    # ONLY Devs and Owner are exempt. Everyone else (including promoted admins) is scanned.
    if user.id in DEV_USERS or user.id == OWNER_ID:
        return

    # 1. Anti-Piracy Check
    if sql.is_piracy_enabled(chat.id):
        content = (message.text or "") + (message.caption or "")
        if PIRACY_REGEX.search(content):
            try:
                message.delete()
                chat.kick_member(user.id)
                message.reply_text(f"» 🛡️ **TSB Zero Tolerance**: Piracy detected. {user.mention_markdown()} has been banned.", parse_mode=ParseMode.MARKDOWN)
                return
            except BadRequest:
                pass

    # 2. Anti-NSFW Check
    if sql.is_nsfw_enabled(chat.id):
        if message.photo or message.video or message.sticker or message.animation:
            # ... download logic ...
            # Get the file
            if message.photo:
                file_id = message.photo[-1].file_id
            elif message.video:
                file_id = message.video.file_id
            elif message.sticker:
                file_id = message.sticker.file_id
            elif message.animation:
                file_id = message.animation.file_id
            else:
                return

            try:
                msg_status = message.reply_text("» 🛡️ Scanning media for safety...", quote=True)
                file = context.bot.get_file(file_id)
                fpath = file.download()
                
                is_nsfw = check_nsfw(fpath)
                os.remove(fpath)
                
                if is_nsfw:
                    message.delete()
                    chat.kick_member(user.id)
                    msg_status.edit_text(f"» 🔞 **TSB Zero Tolerance**: NSFW content detected. {user.mention_markdown()} has been banned.", parse_mode=ParseMode.MARKDOWN)
                else:
                    msg_status.delete()
            except Exception as e:
                LOGGER.error(f"Safety Monitor Error: {e}")

@user_admin
def safety_menu(update: Update, context: CallbackContext):
    chat = update.effective_chat
    nsfw = "Enabled ✅" if sql.is_nsfw_enabled(chat.id) else "Disabled ❌"
    piracy = "Enabled ✅" if sql.is_piracy_enabled(chat.id) else "Disabled ❌"
    ai = "Enabled ✅" if sql.is_ai_enabled(chat.id) else "Disabled ❌"
    
    text = (
        f"🛡️ **TSB Safety Dashboard**\n"
        f"━━━━━━━━━━━━━━\n"
        f"**Chat:** `{chat.title}`\n\n"
        f"• **Anti-NSFW:** {nsfw}\n"
        f"• **Anti-Piracy:** {piracy}\n"
        f"• **AI Chatbot:** {ai}\n\n"
        f"Use the buttons below to toggle advanced protections for this group."
    )
    
    buttons = [
        [InlineKeyboardButton(f"Toggle Anti-NSFW", callback_data="safety_nsfw")],
        [InlineKeyboardButton(f"Toggle Anti-Piracy", callback_data="safety_piracy")],
        [InlineKeyboardButton(f"Toggle AI Chatbot", callback_data="safety_ai")],
        [InlineKeyboardButton(f"Close", callback_data="safety_close")]
    ]
    
    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

def safety_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user

    if not is_user_admin(chat, user.id):
        query.answer("You are not an admin!", show_alert=True)
        return

    if query.data == "safety_nsfw":
        curr = sql.is_nsfw_enabled(chat.id)
        sql.set_nsfw_status(chat.id, not curr)
        query.answer(f"Anti-NSFW {'Disabled' if curr else 'Enabled'}")
    elif query.data == "safety_piracy":
        curr = sql.is_piracy_enabled(chat.id)
        sql.set_piracy_status(chat.id, not curr)
        query.answer(f"Anti-Piracy {'Disabled' if curr else 'Enabled'}")
    elif query.data == "safety_ai":
        curr = sql.is_ai_enabled(chat.id)
        sql.set_ai_status(chat.id, not curr)
        query.answer(f"AI Chatbot {'Disabled' if curr else 'Enabled'}")
    elif query.data == "safety_close":
        query.message.delete()
        return

    # Update menu
    nsfw = "Enabled ✅" if sql.is_nsfw_enabled(chat.id) else "Disabled ❌"
    piracy = "Enabled ✅" if sql.is_piracy_enabled(chat.id) else "Disabled ❌"
    ai = "Enabled ✅" if sql.is_ai_enabled(chat.id) else "Disabled ❌"
    
    text = (
        f"🛡️ **TSB Safety Dashboard**\n"
        f"━━━━━━━━━━━━━━\n"
        f"**Chat:** `{chat.title}`\n\n"
        f"• **Anti-NSFW:** {nsfw}\n"
        f"• **Anti-Piracy:** {piracy}\n"
        f"• **AI Chatbot:** {ai}\n\n"
        f"Use the buttons below to toggle advanced protections for this group."
    )
    buttons = [
        [InlineKeyboardButton(f"Toggle Anti-NSFW", callback_data="safety_nsfw")],
        [InlineKeyboardButton(f"Toggle Anti-Piracy", callback_data="safety_piracy")],
        [InlineKeyboardButton(f"Toggle AI Chatbot", callback_data="safety_ai")],
        [InlineKeyboardButton(f"Close", callback_data="safety_close")]
    ]
    query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

SAFETY_HANDLER = DisableAbleCommandHandler("safety", safety_menu, run_async=True)
SAFETY_MONITOR_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.chat_type.groups, safety_monitor, run_async=True)
SAFETY_CALLBACK_HANDLER = CallbackQueryHandler(safety_callback, pattern=r"safety_.*", run_async=True)

dispatcher.add_handler(SAFETY_HANDLER)
dispatcher.add_handler(SAFETY_MONITOR_HANDLER, group=9) # High priority group
dispatcher.add_handler(SAFETY_CALLBACK_HANDLER)

__mod_name__ = "Sᴀғᴇᴛʏ"
__help__ = """
*TSB Safety Shield*
Protect your group from NSFW content and Piracy links using specialized AI.

 ❍ /safety*:* Open the safety dashboard to toggle features.

*Features:*
• **Anti-NSFW**: Scans photos, videos, and stickers using Sightengine AI.
• **Anti-Piracy**: Scans for torrent links, magnet links, and illegal file signatures.
"""
