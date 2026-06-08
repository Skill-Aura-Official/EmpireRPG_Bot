from pymongo import DESCENDING
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import _db, get_coins, remove_coins, add_coins

_bounties = _db["bounties"] if _db is not None else None

def place_bounty_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    message = update.effective_message
    args = context.args
    
    if not message.reply_to_message:
        message.reply_text("🎯 You must reply to a user's message to place a bounty on them!")
        return
        
    target = message.reply_to_message.from_user
    if target.id == user.id:
        message.reply_text("❌ You cannot place a bounty on yourself!")
        return
    if target.is_bot:
        message.reply_text("❌ You cannot place a bounty on a bot!")
        return
        
    if not args or not args[0].isdigit():
        message.reply_text("ℹ️ Usage: /bounty <amount>")
        return
        
    amount = int(args[0])
    if amount < 1000:
        message.reply_text("❌ Minimum bounty amount is 1,000 Coins.")
        return
        
    gold = get_coins(user.id)
    if gold < amount:
        message.reply_text("❌ You don't have enough Coins to place this bounty!")
        return
        
    remove_coins(user.id, amount)
    
    # Add to bounty board
    if _bounties is not None:
        _bounties.update_one(
            {"target_id": target.id},
            {
                "$inc": {"amount": amount},
                "$set": {"target_name": target.first_name, "placed_by_name": user.first_name}
            },
            upsert=True
        )
        
    message.reply_text(
        f"🎯 <b>BOUNTY PLACED!</b> 🎯\n\n"
        f"<b>{user.first_name}</b> has placed a bounty of 💰 <b>{amount} Coins</b> on <b>{target.first_name}</b>'s head!\n\n"
        f"<i>Any player in any group can now raid {target.first_name} to claim this bounty!</i>",
        parse_mode=ParseMode.HTML
    )

def bountyboard(update: Update, context: CallbackContext):
    if _bounties is None:
        update.effective_message.reply_text("Database offline.")
        return
        
    top_bounties = list(_bounties.find().sort("amount", DESCENDING).limit(10))
    
    if not top_bounties:
        update.effective_message.reply_text("📜 The Global Bounty Board is currently empty.")
        return
        
    text = "📜 <b>GLOBAL BOUNTY BOARD</b> 📜\n\n"
    for i, b in enumerate(top_bounties, 1):
        text += f"{i}. <b>{b['target_name']}</b> - 💰 {b['amount']} Coins\n"
        text += f"   <i>(Last boosted by {b['placed_by_name']})</i>\n\n"
        
    text += "<i>Raid a target successfully to claim their bounty!</i>"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu_main")]
    ])
    
    if update.callback_query:
        update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def check_and_claim_bounty(attacker_id, attacker_name, target_id, update: Update):
    """Called from warfare.py when a raid is successful."""
    if _bounties is None:
        return
        
    bounty = _bounties.find_one({"target_id": target_id})
    if bounty:
        amount = bounty["amount"]
        add_coins(attacker_id, amount)
        _bounties.delete_one({"target_id": target_id})
        
        update.effective_message.reply_text(
            f"🚨 <b>BOUNTY CLAIMED!</b> 🚨\n\n"
            f"<b>{attacker_name}</b> has successfully raided the wanted criminal and claimed the bounty of 💰 <b>{amount} Coins</b>!",
            parse_mode=ParseMode.HTML
        )


__help__ = """
*Age of Telegram: Bounty Board*
 ❍ /bounty <amount>*:* Reply to a user to place a global bounty on their head.
 ❍ /bountyboard*:* View the top 10 most wanted players in the game.
"""

__mod_name__ = "Bᴏᴜɴᴛʏ Bᴏᴀʀᴅ"

BOUNTY_HANDLER = CommandHandler("bounty", place_bounty_cmd, run_async=True)
BOUNTYBOARD_HANDLER = CommandHandler("bountyboard", bountyboard, run_async=True)
BOUNTYBOARD_CALLBACK = CallbackQueryHandler(bountyboard, pattern=r"^menu_bountyboard$", run_async=True)

dispatcher.add_handler(BOUNTY_HANDLER)
dispatcher.add_handler(BOUNTYBOARD_HANDLER)
dispatcher.add_handler(BOUNTYBOARD_CALLBACK)

__handlers__ = [BOUNTY_HANDLER, BOUNTYBOARD_HANDLER, BOUNTYBOARD_CALLBACK]
