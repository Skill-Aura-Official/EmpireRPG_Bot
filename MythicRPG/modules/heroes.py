import random
import uuid
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import get_empire, get_coins, remove_coins, add_hero, set_active_hero

# Cost to summon a hero
SUMMON_COST = 5000

# Rarity configurations
RARITIES = {
    "Common": {"weight": 60, "multiplier": 1.05},
    "Rare": {"weight": 25, "multiplier": 1.10},
    "Epic": {"weight": 10, "multiplier": 1.25},
    "Legendary": {"weight": 4, "multiplier": 1.50},
    "Mythic": {"weight": 1, "multiplier": 2.00}
}

FACTIONS = ["Fire", "Water", "Earth", "Light", "Dark"]
CLASSES = ["Infantry General", "Cavalry Commander", "Ranger Captain"]

def generate_hero():
    # Roll rarity
    roll = random.uniform(0, 100)
    cumulative = 0
    selected_rarity = "Common"
    for rarity, data in RARITIES.items():
        cumulative += data["weight"]
        if roll <= cumulative:
            selected_rarity = rarity
            break
            
    faction = random.choice(FACTIONS)
    hero_class = random.choice(CLASSES)
    
    # Generate unique ID and name
    hero_id = str(uuid.uuid4())[:8]
    names = ["Arthur", "Lancelot", "Gawain", "Leonidas", "Alexander", "Ghengis", "Joan", "Mulan"]
    titles = ["The Brave", "The Fearless", "The Conqueror", "The Silent", "The Vengeful"]
    hero_name = f"{random.choice(names)} {random.choice(titles)}"
    
    return {
        "id": hero_id,
        "name": hero_name,
        "rarity": selected_rarity,
        "faction": faction,
        "class": hero_class,
        "level": 1,
        "equipment": None
    }


def tavern(update: Update, context: CallbackContext):
    user = update.effective_user
    gold = get_coins(user.id)
    
    text = (
        f"🍻 <b>The Tavern</b>\n\n"
        f"Welcome to the Tavern, commander. For <b>{SUMMON_COST} Coins</b>, you can recruit a Hero to lead your armies.\n\n"
        f"<b>Rarity Drop Rates:</b>\n"
        f"⚪ Common: 60%\n"
        f"🔵 Rare: 25%\n"
        f"🟣 Epic: 10%\n"
        f"🟡 Legendary: 4%\n"
        f"🔴 Mythic: 1%\n\n"
        f"💰 Your Coins: <b>{gold}</b>"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Summon Hero (5,000 Coins)", callback_data="tavern_summon")],
        [InlineKeyboardButton("📜 View My Heroes", callback_data="tavern_view_heroes")],
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu_main")]
    ])
    
    if update.callback_query:
        update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def tavern_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    if data == "tavern_summon":
        gold = get_coins(user.id)
        if gold < SUMMON_COST:
            query.answer("❌ You don't have enough Coins!", show_alert=True)
            return
            
        remove_coins(user.id, SUMMON_COST)
        hero = generate_hero()
        add_hero(user.id, hero)
        
        colors = {"Common": "⚪", "Rare": "🔵", "Epic": "🟣", "Legendary": "🟡", "Mythic": "🔴"}
        icon = colors.get(hero["rarity"], "⚪")
        
        text = (
            f"🎉 <b>HERO SUMMONED!</b> 🎉\n\n"
            f"{icon} <b>{hero['name']}</b> ({hero['rarity']})\n"
            f"⚔️ Class: {hero['class']}\n"
            f"🔮 Faction: {hero['faction']}\n\n"
            f"<i>Go to 'View My Heroes' to equip them!</i>"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Summon Again", callback_data="tavern_summon")],
            [InlineKeyboardButton("🔙 Back to Tavern", callback_data="tavern_main")]
        ])
        query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
    elif data == "tavern_main":
        tavern(update, context)
        
    elif data == "tavern_view_heroes":
        emp = get_empire(user.id)
        heroes = emp.get("heroes", [])
        active_id = emp.get("active_hero_id")
        
        if not heroes:
            query.answer("You don't own any heroes! Summon one first.", show_alert=True)
            return
            
        # Display top 10 heroes for now
        text = "📜 <b>Your Heroes</b>\n\n"
        for h in heroes[:10]:
            status = " [ACTIVE]" if h["id"] == active_id else ""
            text += f"▪️ <b>{h['name']}</b> ({h['rarity']}) - Lvl {h['level']}{status}\n"
            text += f"   <i>{h['faction']} {h['class']}</i> | ID: {h['id']}\n\n"
            
        text += "<i>To equip a hero, reply to any message with /equip [Hero_ID]</i>"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Tavern", callback_data="tavern_main")]
        ])
        query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def equip_hero(update: Update, context: CallbackContext):
    user = update.effective_user
    args = context.args
    
    if not args:
        update.effective_message.reply_text("ℹ️ Usage: /equip <Hero_ID>")
        return
        
    hero_id = args[0]
    emp = get_empire(user.id)
    heroes = emp.get("heroes", [])
    
    found = False
    for h in heroes:
        if h["id"] == hero_id:
            found = True
            break
            
    if not found:
        update.effective_message.reply_text("❌ You don't own a hero with that ID!")
        return
        
    set_active_hero(user.id, hero_id)
    update.effective_message.reply_text(f"✅ Hero <b>{hero_id}</b> has been set as your active commander!", parse_mode=ParseMode.HTML)


__help__ = """
*Age of Telegram: Heroes*
 ❍ /tavern*:* Visit the tavern to summon powerful heroes using Gold.
 ❍ /equip <ID>*:* Equip a specific hero to lead your armies into battle.
"""

__mod_name__ = "Hᴇʀᴏᴇs"

TAVERN_HANDLER = CommandHandler("tavern", tavern, run_async=True)
EQUIP_HANDLER = CommandHandler("equip", equip_hero, run_async=True)
TAVERN_CALLBACK = CallbackQueryHandler(tavern_callback, pattern=r"^tavern_", run_async=True)

dispatcher.add_handler(TAVERN_HANDLER)
dispatcher.add_handler(EQUIP_HANDLER)
dispatcher.add_handler(TAVERN_CALLBACK)

__handlers__ = [TAVERN_HANDLER, EQUIP_HANDLER, TAVERN_CALLBACK]
