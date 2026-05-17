import requests
import re
import html
from typing import Optional
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Chat, User
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.error import BadRequest
from telegram.utils.helpers import mention_html

from TSBSSB import GEMINI_API_KEY, dispatcher, BOT_USERNAME, BOT_ID
from TSBSSB.modules.disable import DisableAbleCommandHandler
from TSBSSB.modules.helper_funcs.chat_status import user_admin, user_admin_no_reply
from TSBSSB.modules.log_channel import gloggable
import TSBSSB.modules.sql.safety_sql as sql
from TSBSSB.modules.helper_funcs.gemini_helper import get_gemini_response

# get_gemini_response removed, now using central helper

def send_response(message, answer):
    try:
        if len(answer) > 4096:
            for i in range(0, len(answer), 4096):
                message.reply_text(answer[i:i+4096])
        else:
            message.reply_text(answer, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        message.reply_text(answer) # Fallback if markdown parsing fails

def gemini_ask(update: Update, context: CallbackContext):
    message = update.effective_message
    query = " ".join(context.args) if context.args else (message.reply_to_message.text if message.reply_to_message else "")
    if not query:
        return message.reply_text("» ᴩʟᴇᴀsᴇ ᴀsᴋ ᴀ ǫᴜᴇsᴛɪᴏɴ!\nExample: `/ask Write a python script for me.`")
    
    msg = message.reply_text("» ᴛʜɪɴᴋɪɴɢ...")
    answer = get_gemini_response(query)
    msg.delete()
    send_response(message, answer)

def gemini_translate(update: Update, context: CallbackContext):
    message = update.effective_message
    if len(context.args) < 1 and not message.reply_to_message:
        return message.reply_text("» ᴩʟᴇᴀsᴇ sᴩᴇᴄɪғʏ ᴀ ʟᴀɴɢᴜᴀɢᴇ ᴀɴᴅ ᴛᴇxᴛ!\nExample: `/tr spanish Hello world`")
        
    lang = context.args[0] if context.args else "english"
    text = " ".join(context.args[1:]) if len(context.args) > 1 else (message.reply_to_message.text if message.reply_to_message else "")
    
    msg = message.reply_text("» ᴛʀᴀɴsʟᴀᴛɪɴɢ...")
    prompt = f"Translate the following text to {lang}. Only return the translation, nothing else.\n\nText: {text}"
    answer = get_gemini_response(prompt)
    msg.delete()
    send_response(message, answer)

def gemini_ud(update: Update, context: CallbackContext):
    message = update.effective_message
    query = " ".join(context.args)
    if not query:
        return message.reply_text("» ᴩʟᴇᴀsᴇ sᴩᴇᴄɪғʏ ᴀ ᴡᴏʀᴅ!\nExample: `/ud rizz`")
        
    msg = message.reply_text("» sᴇᴀʀᴄʜɪɴɢ...")
    prompt = f"Provide the Urban Dictionary slang definition for the word '{query}'. Keep it concise and include an example sentence."
    answer = get_gemini_response(prompt)
    msg.delete()
    send_response(message, answer)

def gemini_wiki(update: Update, context: CallbackContext):
    message = update.effective_message
    query = " ".join(context.args)
    if not query:
        return message.reply_text("» ᴩʟᴇᴀsᴇ sᴩᴇᴄɪғʏ ᴀ ᴛᴏᴩɪᴄ!\nExample: `/wiki Python`")
        
    msg = message.reply_text("» sᴇᴀʀᴄʜɪɴɢ ᴡɪᴋɪᴩᴇᴅɪᴀ...")
    prompt = f"Provide a brief, factual Wikipedia-style summary of the topic '{query}'. Keep it under 3 paragraphs."
    answer = get_gemini_response(prompt)
    msg.delete()
    send_response(message, answer)

def gemini_cash(update: Update, context: CallbackContext):
    message = update.effective_message
    if len(context.args) < 3:
        return message.reply_text("» Invalid syntax!\nExample: `/cash 50 USD INR`")
        
    amount = context.args[0]
    curr_from = context.args[1]
    curr_to = context.args[2]
    
    msg = message.reply_text("» ᴄᴏɴᴠᴇʀᴛɪɴɢ...")
    prompt = f"What is the current conversion rate and total for {amount} {curr_from} to {curr_to}? Just give me the estimate and the math, keep it short."
    answer = get_gemini_response(prompt)
    msg.delete()
    send_response(message, answer)

def chatbot(update: Update, context: CallbackContext):
    message = update.effective_message
    chat_id = update.effective_chat.id
    
    # Check if chatbot is enabled for this chat (V2 safety check)
    if not sql.is_ai_enabled(chat_id):
        return

    if not message.text:
        return
        
    reply_message = message.reply_to_message
    is_reply_to_bot = reply_message and reply_message.from_user.id == BOT_ID
    is_mentioning_bot = BOT_USERNAME.lower() in message.text.lower()
    is_private = update.effective_chat.type == "private"
    
    if not (is_reply_to_bot or is_mentioning_bot or is_private):
        return
        
    context.bot.send_chat_action(chat_id, action="typing")
    clean_text = message.text.replace(f"@{BOT_USERNAME}", "").strip()
    
    answer = get_gemini_response(clean_text, chat_id=chat_id, is_chatbot=True)
    send_response(message, answer)

@user_admin_no_reply
@gloggable
def tsb_rm(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"rm_chat\((.+?)\)", query.data)
    if match:
        chat: Optional[Chat] = update.effective_chat
        sql.set_ai_status(chat.id, False)
        update.effective_message.edit_text(
            "{} ᴄʜᴀᴛʙᴏᴛ ᴅɪsᴀʙʟᴇᴅ ʙʏ {}.".format(
                dispatcher.bot.first_name, mention_html(user.id, user.first_name)
            ),
            parse_mode=ParseMode.HTML,
        )
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"AI_DISABLED\n"
            f"<b>Admin :</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        )
    return ""

@user_admin_no_reply
@gloggable
def tsb_add(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"add_chat\((.+?)\)", query.data)
    if match:
        chat: Optional[Chat] = update.effective_chat
        sql.set_ai_status(chat.id, True)
        update.effective_message.edit_text(
            "{} ᴄʜᴀᴛʙᴏᴛ ᴇɴᴀʙʟᴇᴅ ʙʏ {}.".format(
                dispatcher.bot.first_name, mention_html(user.id, user.first_name)
            ),
            parse_mode=ParseMode.HTML,
        )
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"AI_ENABLED\n"
            f"<b>Admin :</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        )
    return ""

@user_admin
@gloggable
def tsb(update: Update, context: CallbackContext):
    message = update.effective_message
    msg = "• ᴄʜᴏᴏsᴇ ᴀɴ ᴏᴩᴛɪᴏɴ ᴛᴏ ᴇɴᴀʙʟᴇ/ᴅɪsᴀʙʟᴇ ᴄʜᴀᴛʙᴏᴛ"
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="ᴇɴᴀʙʟᴇ", callback_data="add_chat({})"),
                InlineKeyboardButton(text="ᴅɪsᴀʙʟᴇ", callback_data="rm_chat({})"),
            ],
        ]
    )
    message.reply_text(
        text=msg,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


__help__ = """
*Gemini AI & Assistant Features*
 ❍ /ask <query>*:* Ask any question to the Gemini 1.5 Pro AI model.
 ❍ /tr <lang> <text>*:* Translates text using AI.
 ❍ /ud <word>*:* Gets the slang definition of a word.
 ❍ /wiki <topic>*:* Gets a Wikipedia summary of a topic.
 ❍ /cash <amt> <from> <to>*:* Converts currency.
 ❍ /chatbot*:* Enable/Disable the human-like conversational AI in the group.
"""

__mod_name__ = "A.I Fᴇᴀᴛᴜʀᴇs"

ASK_HANDLER = DisableAbleCommandHandler(["ask", "gemini"], gemini_ask, run_async=True)
TR_HANDLER = DisableAbleCommandHandler("tr", gemini_translate, run_async=True)
UD_HANDLER = DisableAbleCommandHandler("ud", gemini_ud, run_async=True)
WIKI_HANDLER = DisableAbleCommandHandler("wiki", gemini_wiki, run_async=True)
CASH_HANDLER = DisableAbleCommandHandler("cash", gemini_cash, run_async=True)

CHATBOT_MSG_HANDLER = MessageHandler(
    Filters.text & (~Filters.regex(r"^#[^\s]+") & ~Filters.regex(r"^!") & ~Filters.regex(r"^\/")),
    chatbot,
    run_async=True,
)

CHATBOTK_HANDLER = CommandHandler("chatbot", tsb, run_async=True)
ADD_CHAT_HANDLER = CallbackQueryHandler(tsb_add, pattern=r"add_chat", run_async=True)
RM_CHAT_HANDLER = CallbackQueryHandler(tsb_rm, pattern=r"rm_chat", run_async=True)

dispatcher.add_handler(ASK_HANDLER)
dispatcher.add_handler(TR_HANDLER)
dispatcher.add_handler(UD_HANDLER)
dispatcher.add_handler(WIKI_HANDLER)
dispatcher.add_handler(CASH_HANDLER)
dispatcher.add_handler(CHATBOT_MSG_HANDLER)
dispatcher.add_handler(CHATBOTK_HANDLER)
dispatcher.add_handler(ADD_CHAT_HANDLER)
dispatcher.add_handler(RM_CHAT_HANDLER)

__handlers__ = [ASK_HANDLER, TR_HANDLER, UD_HANDLER, WIKI_HANDLER, CASH_HANDLER, CHATBOT_MSG_HANDLER, CHATBOTK_HANDLER, ADD_CHAT_HANDLER, RM_CHAT_HANDLER]
