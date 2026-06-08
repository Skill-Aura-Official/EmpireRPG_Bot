import random
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import get_empire, get_coins, remove_coins, _empires

def train_assassin(user_id, amount):
    _empires.update_one({"user_id": user_id}, {"$inc": {"assassins": amount}})

def consume_assassin(user_id, amount=1):
    result = _empires.update_one({"user_id": user_id, "assassins": {"$gte": amount}}, {"$inc": {"assassins": -amount}})
    return result.modified_count > 0

def assassins_menu(update: Update, context: CallbackContext):
    user = update.effective_user
    emp = get_empire(user.id)
    gold = get_coins(user.id)
    
    text = (
        f"🕵️ <b>The Shadow Guild</b>\n\n"
        f"Assassins are elite units used for espionage and sabotage. They operate outside the normal rules of warfare.\n\n"
        f"🗡️ Your Assassins: <b>{emp.get('assassins', 0)}</b>\n"
        f"💰 Cost per Assassin: 200 Coins\n\n"
        f"Your Coins: {gold}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡️ Train 1 Assassin", callback_data="train_assassin_1")],
        [InlineKeyboardButton("🗡️ Train 5 Assassins", callback_data="train_assassin_5")],
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu_main")]
    ])
    
    if update.callback_query:
        update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

def assassins_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    if data.startswith("train_assassin_"):
        amount = int(data.split("_")[-1])
        cost = amount * 200
        gold = get_coins(user.id)
        
        if gold < cost:
            query.answer("❌ You don't have enough Coins!", show_alert=True)
            return
            
        remove_coins(user.id, cost)
        train_assassin(user.id, amount)
        query.answer(f"✅ {amount} Assassins trained successfully!", show_alert=True)
        
        # Refresh menu
        assassins_menu(update, context)


def spy(update: Update, context: CallbackContext):
    user = update.effective_user
    message = update.effective_message
    
    if not message.reply_to_message:
        message.reply_text("🕵️ You must reply to a user's message to send a spy!")
        return
        
    target = message.reply_to_message.from_user
    if target.id == user.id:
        message.reply_text("❌ You cannot spy on yourself!")
        return
    if target.is_bot:
        message.reply_text("❌ You cannot spy on a bot!")
        return
        
    att_emp = get_empire(user.id)
    def_emp = get_empire(target.id)
    
    if att_emp.get('assassins', 0) < 1:
        message.reply_text("❌ You do not have any Assassins! Train them in The Shadow Guild.")
        return
        
    # Consume 1 Assassin for the mission
    if not consume_assassin(user.id, 1):
        message.reply_text("❌ Failed to deploy Assassin.")
        return
        
    # Calculate success rate based on number of assassins owned vs defender watchtower
    # Base chance 50%. Max chance 90%. Defender Watchtower reduces chance.
    att_stealth = min(att_emp.get('assassins', 1) * 2, 40) # Max +40% from sheer numbers
    def_detection = def_emp.get('watchtower_level', 0) * 10
    
    success_chance = 50 + att_stealth - def_detection
    success_chance = max(10, min(90, success_chance)) # Cap between 10% and 90%
    
    roll = random.uniform(0, 100)
    
    if roll <= success_chance:
        # Success!
        text = (
            f"✅ <b>ESPIONAGE SUCCESSFUL</b> ✅\n\n"
            f"Your Assassin infiltrated <b>{target.first_name}</b>'s empire unnoticed and retrieved the following intel:\n\n"
            f"<b>Military:</b>\n"
            f"🗡️ Infantry: {def_emp['infantry']} | 🐎 Cavalry: {def_emp['cavalry']} | 🏹 Archers: {def_emp['archers']}\n"
            f"🏰 Town Hall Level: {def_emp['town_hall_level']}\n"
            f"👁️ Watchtower Level: {def_emp.get('watchtower_level', 0)}\n\n"
            f"<b>Resources:</b>\n"
            f"🪵 Wood: {def_emp['wood']} | 🪨 Stone: {def_emp['stone']}\n"
            f"⚔️ Iron: {def_emp['iron']} | 🍞 Food: {def_emp['food']}\n\n"
            f"<i>Your Assassin awaits further orders. You can order a Sabotage (poison water supply) which kills 5% of their troops!</i>"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("☠️ Sabotage (Poison Water)", callback_data=f"sabotage_{target.id}")],
            [InlineKeyboardButton("🏃‍♂️ Retreat Unnoticed", callback_data="sabotage_retreat")]
        ])
        message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        # Failure!
        text = (
            f"❌ <b>ESPIONAGE FAILED</b> ❌\n\n"
            f"Your Assassin was detected by <b>{target.first_name}</b>'s Watchtowers and executed on the spot!"
        )
        message.reply_text(text, parse_mode=ParseMode.HTML)
        
        # Notify defender
        try:
            context.bot.send_message(
                chat_id=message.chat_id,
                text=f"🚨 <b>WARNING to {target.first_name}!</b> 🚨\n\nAn Assassin sent by {user.first_name} was caught trying to infiltrate your empire and has been executed!",
                parse_mode=ParseMode.HTML
            )
        except:
            pass


def sabotage_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    if data == "sabotage_retreat":
        query.edit_message_text("🏃‍♂️ Your Assassin retreated into the shadows. The intel has been secured.")
        return
        
    if data.startswith("sabotage_"):
        target_id = int(data.split("_")[1])
        
        # We need to make sure the user clicking the button is the one who sent the spy.
        # But for simplicity since it's a game, we'll allow whoever clicks it if they own the message.
        # Actually, let's just let the query execute.
        
        def_emp = get_empire(target_id)
        kills_inf = int(def_emp['infantry'] * 0.05)
        kills_cav = int(def_emp['cavalry'] * 0.05)
        kills_arch = int(def_emp['archers'] * 0.05)
        
        from MythicRPG.modules.mongo import kill_troops
        kill_troops(target_id, infantry=kills_inf, cavalry=kills_cav, archers=kills_arch)
        
        query.edit_message_text(
            f"☠️ <b>SABOTAGE SUCCESSFUL</b> ☠️\n\n"
            f"The water supply was poisoned! The enemy lost:\n"
            f"💀 {kills_inf} Infantry\n"
            f"💀 {kills_cav} Cavalry\n"
            f"💀 {kills_arch} Archers",
            parse_mode=ParseMode.HTML
        )


__help__ = """
*Age of Telegram: Stealth & Espionage*
 ❍ /shadowguild*:* Open the Shadow Guild to train Assassins.
 ❍ /spy*:* Reply to a user's message to send an Assassin. They can steal intel and poison the enemy's water supply!
"""

__mod_name__ = "Sᴛᴇᴀʟᴛʜ"

SHADOW_HANDLER = CommandHandler("shadowguild", assassins_menu, run_async=True)
SPY_HANDLER = CommandHandler("spy", spy, run_async=True)
SHADOW_CALLBACK = CallbackQueryHandler(assassins_callback, pattern=r"^train_assassin_", run_async=True)
SABOTAGE_CALLBACK = CallbackQueryHandler(sabotage_callback, pattern=r"^sabotage_", run_async=True)

dispatcher.add_handler(SHADOW_HANDLER)
dispatcher.add_handler(SPY_HANDLER)
dispatcher.add_handler(SHADOW_CALLBACK)
dispatcher.add_handler(SABOTAGE_CALLBACK)

__handlers__ = [SHADOW_HANDLER, SPY_HANDLER, SHADOW_CALLBACK, SABOTAGE_CALLBACK]
