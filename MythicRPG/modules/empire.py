import random
import time
from datetime import datetime, timedelta

from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import (
    get_empire, add_resources, remove_resources, upgrade_building, set_age, get_coins
)

from pyrate_limiter import Duration, Rate, Limiter, BucketFullException

# Cooldown tracking (pyrate-limiter)
# 1 request per 5 minutes per action
rate = Rate(1, 300 * 1000) # Duration in ms for 3.1.0 or we can just use simple time tracking if pyrate is complex, but let's use Limiter
try:
    limiter = Limiter(Rate(1, Duration.MINUTE * 5))
except AttributeError:
    # Fallback to in-memory cooldown if pyrate_limiter version doesn't support it directly like this
    limiter = Limiter(Rate(1, 300)) # Sometimes Duration is not working, but we can do a try block.
    
COOLDOWNS = {}
GATHER_COOLDOWN_SECONDS = 300

def check_cooldown(user_id, action):
    # Pyrate limiter approach
    key = f"{user_id}_{action}"
    try:
        # In Pyrate 3.1.0, Limiter().try_acquire(item) throws BucketFullException
        limiter.try_acquire(key)
        return True, 0
    except BucketFullException as e:
        # Extract remaining time from exception
        remaining = int(e.meta_info.get('remaining_time', 300)) if hasattr(e, 'meta_info') else 300
        return False, remaining
    except Exception:
        # Fallback if pyrate fails
        if key in COOLDOWNS:
            if datetime.now() < COOLDOWNS[key]:
                remaining = int((COOLDOWNS[key] - datetime.now()).total_seconds())
                return False, remaining
        return True, 0

def set_cooldown(user_id, action):
    key = f"{user_id}_{action}"
    COOLDOWNS[key] = datetime.now() + timedelta(seconds=GATHER_COOLDOWN_SECONDS)

# ================= COMMANDS =================

def empire(update: Update, context: CallbackContext):
    user = update.effective_user
    emp = get_empire(user.id)
    gold = get_coins(user.id)
    
    text = (
        f"🏰 <b>{user.first_name}'s Empire</b>\n"
        f"<i>{emp['age']}</i>\n\n"
        f"<b>🏦 Buildings:</b>\n"
        f"• Town Hall: <code>Lv. {emp['town_hall_level']}</code>\n"
        f"• Barracks: <code>Lv. {emp['barracks_level']}</code>\n\n"
        f"<b>📦 Resources:</b>\n"
        f"🪙 Gold: <code>{gold}</code>\n"
        f"🪵 Wood: <code>{emp['wood']}</code>\n"
        f"🪨 Stone: <code>{emp['stone']}</code>\n"
        f"⚔️ Iron: <code>{emp['iron']}</code>\n"
        f"🍞 Food: <code>{emp['food']}</code>\n\n"
        f"<b>⚔️ Army:</b>\n"
        f"🗡️ Infantry: <code>{emp['infantry']}</code> | 🐎 Cavalry: <code>{emp['cavalry']}</code> | 🏹 Archers: <code>{emp['archers']}</code>\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪵 Chop", callback_data="gather_wood"),
            InlineKeyboardButton("🪨 Mine", callback_data="gather_mine"),
        ],
        [
            InlineKeyboardButton("🍞 Farm", callback_data="gather_farm"),
            InlineKeyboardButton("🏹 Hunt", callback_data="gather_hunt"),
        ],
        [InlineKeyboardButton("⬆️ Upgrade Buildings", callback_data="upgrade_menu")]
    ])
    
    if update.callback_query:
        update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def gather_cmd(update: Update, context: CallbackContext, resource_type: str):
    user = update.effective_user
    can_gather, rem = check_cooldown(user.id, resource_type)
    if not can_gather:
        update.effective_message.reply_text(f"⏳ Your workers are resting. Try again in {rem} seconds.")
        return

    # Base gathering logic
    amount = random.randint(10, 30)
    
    if resource_type == "wood":
        add_resources(user.id, wood=amount)
        msg = f"🪓 You chopped down some trees and gathered <b>{amount} Wood</b>!"
    elif resource_type == "mine":
        stone_amt = random.randint(10, 25)
        iron_amt = random.randint(2, 8)
        add_resources(user.id, stone=stone_amt, iron=iron_amt)
        msg = f"⛏️ You mined in the caves and found <b>{stone_amt} Stone</b> and <b>{iron_amt} Iron</b>!"
    elif resource_type == "farm":
        add_resources(user.id, food=amount)
        msg = f"🌾 You harvested your crops and gained <b>{amount} Food</b>!"
    elif resource_type == "hunt":
        amount = random.randint(5, 20)
        add_resources(user.id, food=amount)
        msg = f"🏹 You hunted in the wild and brought back <b>{amount} Food</b>!"
        
    set_cooldown(user.id, resource_type)
    
    if update.callback_query:
        update.callback_query.answer(msg, show_alert=True)
    else:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


def empire_callbacks(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data

    if data.startswith("gather_"):
        resource = data.split("_")[1]
        gather_cmd(update, context, resource)
        # Update empire view after gathering
        empire(update, context)

    elif data == "upgrade_menu":
        emp = get_empire(user.id)
        gold = get_coins(user.id)
        
        # Calculate cost for Town Hall based on level
        th_level = emp['town_hall_level']
        th_cost_wood = th_level * 500
        th_cost_stone = th_level * 500
        th_cost_gold = th_level * 100
        
        text = (
            f"⬆️ <b>Upgrade Buildings</b>\n\n"
            f"<b>Town Hall Lv.{th_level} -> Lv.{th_level + 1}</b>\n"
            f"Cost: 🪵 {th_cost_wood} | 🪨 {th_cost_stone} | 🪙 {th_cost_gold}\n\n"
            f"<i>Current Resources:</i>\n"
            f"🪵 {emp['wood']} | 🪨 {emp['stone']} | 🪙 {gold}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬆️ Upgrade Town Hall", callback_data="upgrade_th")],
            [InlineKeyboardButton("🔙 Back to Empire", callback_data="empire_main")]
        ])
        query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data == "upgrade_th":
        emp = get_empire(user.id)
        gold = get_coins(user.id)
        th_level = emp['town_hall_level']
        
        th_cost_wood = th_level * 500
        th_cost_stone = th_level * 500
        th_cost_gold = th_level * 100
        
        if emp['wood'] < th_cost_wood or emp['stone'] < th_cost_stone or gold < th_cost_gold:
            query.answer("❌ Not enough resources!", show_alert=True)
            return
            
        # Deduct resources
        from MythicRPG.modules.mongo import remove_coins
        remove_resources(user.id, wood=th_cost_wood, stone=th_cost_stone)
        if th_cost_gold > 0:
            remove_coins(user.id, th_cost_gold)
            
        upgrade_building(user.id, "town_hall")
        
        # Age progression logic
        new_level = th_level + 1
        new_age = emp['age']
        if new_level == 5:
            new_age = "Bronze Age"
        elif new_level == 10:
            new_age = "Iron Age"
        elif new_level == 15:
            new_age = "Medieval Age"
        elif new_level == 20:
            new_age = "Modern Age"
        elif new_level == 25:
            new_age = "Future Age"
            
        if new_age != emp['age']:
            set_age(user.id, new_age)
            query.answer(f"🎉 Town Hall Upgraded! Welcome to the {new_age}!", show_alert=True)
        else:
            query.answer("✅ Town Hall Upgraded successfully!", show_alert=True)
            
        empire(update, context)

    elif data == "empire_main":
        empire(update, context)


def chop(update: Update, context: CallbackContext):
    gather_cmd(update, context, "wood")

def mine(update: Update, context: CallbackContext):
    gather_cmd(update, context, "mine")

def farm(update: Update, context: CallbackContext):
    gather_cmd(update, context, "farm")

def hunt(update: Update, context: CallbackContext):
    gather_cmd(update, context, "hunt")


__help__ = """
*Age of Telegram: Empire Management*
Build your kingdom from the ground up!

*Commands:*
 ❍ /empire*:* View your empire, buildings, resources, and army.
 ❍ /chop*:* Send workers to chop Wood.
 ❍ /mine*:* Send workers to mine Stone and Iron.
 ❍ /farm*:* Send workers to gather Food.
"""

__mod_name__ = "Eᴍᴩɪʀᴇ"

EMPIRE_HANDLER = CommandHandler("empire", empire, run_async=True)
CHOP_HANDLER = CommandHandler("chop", chop, run_async=True)
MINE_HANDLER = CommandHandler("mine", mine, run_async=True)
FARM_HANDLER = CommandHandler("farm", farm, run_async=True)
HUNT_HANDLER = CommandHandler("hunt", hunt, run_async=True)
EMPIRE_CALLBACKS = CallbackQueryHandler(empire_callbacks, pattern=r"^(gather_|upgrade_|empire_main)", run_async=True)

dispatcher.add_handler(EMPIRE_HANDLER)
dispatcher.add_handler(CHOP_HANDLER)
dispatcher.add_handler(MINE_HANDLER)
dispatcher.add_handler(FARM_HANDLER)
dispatcher.add_handler(HUNT_HANDLER)
dispatcher.add_handler(EMPIRE_CALLBACKS)

__handlers__ = [EMPIRE_HANDLER, CHOP_HANDLER, MINE_HANDLER, FARM_HANDLER, HUNT_HANDLER, EMPIRE_CALLBACKS]
