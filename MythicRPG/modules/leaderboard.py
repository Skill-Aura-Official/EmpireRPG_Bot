from telegram import Update, ParseMode
from telegram.ext import CallbackContext, CommandHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import (
    get_top_empires, get_top_army, get_top_gold, get_top_guilds
)

def top_empires(update: Update, context: CallbackContext):
    leaders = get_top_empires(10)
    
    text = "🏆 <b>Top Empires (by Town Hall & Age)</b>\n\n"
    for idx, emp in enumerate(leaders):
        user_name = f"User {emp['user_id']}"
        try:
            user_info = context.bot.get_chat(emp['user_id'])
            user_name = user_info.first_name
        except Exception:
            pass
        text += f"{idx + 1}. <b>{user_name}</b> - {emp.get('age', 'Stone Age')} (TH Lv.{emp.get('town_hall_level', 1)})\n"
        
    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def top_army(update: Update, context: CallbackContext):
    leaders = get_top_army(10)
    
    text = "⚔️ <b>Top Militaries (by Total Troops)</b>\n\n"
    for idx, emp in enumerate(leaders):
        user_name = f"User {emp['user_id']}"
        try:
            user_info = context.bot.get_chat(emp['user_id'])
            user_name = user_info.first_name
        except Exception:
            pass
        text += f"{idx + 1}. <b>{user_name}</b> - {emp.get('total_army', 0):,} Troops\n"
        
    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def top_gold(update: Update, context: CallbackContext):
    leaders = get_top_gold(10)
    
    text = "🪙 <b>Wealthiest Players (by Gold)</b>\n\n"
    for idx, wallet in enumerate(leaders):
        user_name = f"User {wallet['user_id']}"
        try:
            user_info = context.bot.get_chat(wallet['user_id'])
            user_name = user_info.first_name
        except Exception:
            pass
        text += f"{idx + 1}. <b>{user_name}</b> - {wallet.get('coins', 0):,} Gold\n"
        
    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def top_guilds(update: Update, context: CallbackContext):
    leaders = get_top_guilds(10)
    
    text = "🏰 <b>Top Guilds (by Victories & Wealth)</b>\n\n"
    for idx, g in enumerate(leaders):
        victories = g.get('war_victories', 0)
        gold = g.get('vault', {}).get('gold', 0)
        text += f"{idx + 1}. <b>{g['name']}</b> - {victories} Wins | {gold:,} Vault Gold\n"
        
    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


__help__ = """
*Age of Telegram: Leaderboards*

*Commands:*
 ❍ /topempires*:* Ranks players by Empire Level and Age.
 ❍ /toparmy*:* Ranks players by total military power (troop count).
 ❍ /topgold*:* Ranks the wealthiest players (Economy).
 ❍ /topguilds*:* Ranks Guilds based on total Guild War victories and Vault wealth.
"""

__mod_name__ = "Lᴇᴀᴅᴇʀʙᴏᴀʀᴅ"

TOP_EMP_HANDLER = CommandHandler("topempires", top_empires, run_async=True)
TOP_ARMY_HANDLER = CommandHandler("toparmy", top_army, run_async=True)
TOP_GOLD_HANDLER = CommandHandler("topgold", top_gold, run_async=True)
TOP_GUILDS_HANDLER = CommandHandler("topguilds", top_guilds, run_async=True)

dispatcher.add_handler(TOP_EMP_HANDLER)
dispatcher.add_handler(TOP_ARMY_HANDLER)
dispatcher.add_handler(TOP_GOLD_HANDLER)
dispatcher.add_handler(TOP_GUILDS_HANDLER)

__handlers__ = [TOP_EMP_HANDLER, TOP_ARMY_HANDLER, TOP_GOLD_HANDLER, TOP_GUILDS_HANDLER]
