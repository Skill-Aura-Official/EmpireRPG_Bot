import time
from telegram import Update
from telegram.error import BadRequest, Unauthorized, TelegramError
from telegram.ext import CallbackContext, CommandHandler
from MythicRPG import dispatcher
from MythicRPG.modules.helper_funcs.chat_status import dev_plus
from MythicRPG.modules.sql.users_sql import get_all_chats, get_all_users

def broadcast_func(msg, targets, target_type):
    broadcast_msg = msg.reply_to_message
    success = 0
    failed = 0
    
    status_msg = msg.reply_text(f"🚀 Broadcasting to {len(targets)} {target_type}...")
    
    for target in targets:
        try:
            target_id = target.chat_id if target_type == "chats" else target.user_id
            broadcast_msg.copy(chat_id=target_id)
            success += 1
        except (BadRequest, Unauthorized):
            failed += 1
        except TelegramError:
            failed += 1
            
        # Avoid flood limits
        time.sleep(0.1)
        
    status_msg.edit_text(
        f"✅ **Broadcast Completed!**\n\n"
        f"🎯 **Target:** `{target_type}`\n"
        f"🟢 **Successful:** `{success}`\n"
        f"🔴 **Failed:** `{failed}`",
        parse_mode="Markdown"
    )

@dev_plus
def broadcast_chats(update: Update, context: CallbackContext):
    msg = update.effective_message
    if not msg.reply_to_message:
        msg.reply_text("You must reply to a message to broadcast it.")
        return
    chats = get_all_chats()
    broadcast_func(msg, chats, "chats")

@dev_plus
def broadcast_users(update: Update, context: CallbackContext):
    msg = update.effective_message
    if not msg.reply_to_message:
        msg.reply_text("You must reply to a message to broadcast it.")
        return
    users = get_all_users()
    broadcast_func(msg, users, "users")

BROADCAST_CHATS_HANDLER = CommandHandler("broadcast", broadcast_chats, run_async=True)
BROADCAST_USERS_HANDLER = CommandHandler("broadcastusers", broadcast_users, run_async=True)

dispatcher.add_handler(BROADCAST_CHATS_HANDLER)
dispatcher.add_handler(BROADCAST_USERS_HANDLER)

__help__ = """
*Empire Broadcaster* (Devs Only)
 ❍ /broadcast <reply>: Broadcast a message to all chats.
 ❍ /broadcastusers <reply>: Broadcast a message to all users.
"""
__mod_name__ = "Bʀᴏᴀᴅᴄᴀsᴛ"
