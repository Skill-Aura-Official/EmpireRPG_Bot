import random
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import get_coins, remove_coins, _empires

def smuggler_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    
    # 20% chance the smuggler is hiding and not available
    if random.random() < 0.20:
        update.effective_message.reply_text("🕵️ <i>The Smuggler is currently hiding from the Royal Guards. Come back later...</i>", parse_mode=ParseMode.HTML)
        return
        
    from MythicRPG.modules.heroes import HEROES
    # The smuggler only sells Epic and Legendary heroes, but for massive coin prices
    high_tier_heroes = [h for h in HEROES if h['rarity'] in ['Epic', 'Legendary']]
    
    if not high_tier_heroes:
        update.effective_message.reply_text("🕵️ <i>I got nothin' for ya today. Scram.</i>", parse_mode=ParseMode.HTML)
        return
        
    # Pick 2 random heroes
    wares = random.sample(high_tier_heroes, min(2, len(high_tier_heroes)))
    
    text = "🕵️ <b>THE BLACK MARKET SMUGGLER</b> 🕵️\n\n"
    text += "<i>\"Psst... Over here. I've acquired some... unique talent. You got the Coins?\"</i>\n\n"
    
    keyboard = []
    
    for hero in wares:
        cost = 25000 if hero['rarity'] == 'Epic' else 75000
        text += f"🗡️ <b>{hero['name']} ({hero['rarity']} {hero['faction']})</b>\n"
        text += f"💰 Cost: {cost:,} Coins\n\n"
        
        keyboard.append([InlineKeyboardButton(f"Buy {hero['name']} ({cost:,} Coins)", callback_data=f"smuggle_{hero['id']}_{cost}_{user.id}")])
        
    keyboard.append([InlineKeyboardButton("❌ Leave", callback_data="menu_close")])
    
    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

def smuggle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    parts = data.split("_")
    hero_id = int(parts[1])
    cost = int(parts[2])
    owner_id = int(parts[3])
    
    if user.id != owner_id:
        query.answer("Find your own smuggler!", show_alert=True)
        return
        
    coins = get_coins(user.id)
    if coins < cost:
        query.answer("You don't have enough Coins for this transaction.", show_alert=True)
        return
        
    from MythicRPG.modules.heroes import HEROES
    hero = next((h for h in HEROES if h["id"] == hero_id), None)
    if not hero:
        query.answer("Hero not found.", show_alert=True)
        return
        
    # Deduct coins and add hero
    remove_coins(user.id, cost)
    _empires.update_one(
        {"user_id": user.id},
        {"$push": {"heroes": hero}}
    )
    
    query.answer("Transaction complete.", show_alert=True)
    query.message.edit_text(
        f"🕵️ <b>TRANSACTION COMPLETE</b> 🕵️\n\n"
        f"<i>\"Pleasure doing business with ya. Now scram before the guards see us.\"</i>\n\n"
        f"🌟 <b>{hero['name']}</b> has been secretly smuggled into your empire!",
        parse_mode=ParseMode.HTML
    )

__help__ = """
*Age of Telegram: Black Market*
 ❍ /smuggler*:* Visit the Black Market to buy rare Heroes for Coins.
"""

__mod_name__ = "Sᴍᴜɢɢʟᴇʀ"

SMUGGLER_HANDLER = CommandHandler("smuggler", smuggler_cmd, run_async=True)
SMUGGLE_CALLBACK = CallbackQueryHandler(smuggle_callback, pattern=r"^smuggle_", run_async=True)

dispatcher.add_handler(SMUGGLER_HANDLER)
dispatcher.add_handler(SMUGGLE_CALLBACK)

__handlers__ = [SMUGGLER_HANDLER, SMUGGLE_CALLBACK]
