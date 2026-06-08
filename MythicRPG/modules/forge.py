import random
import uuid
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import get_empire, remove_resources, add_inventory_item

FORGE_COST = {"wood": 500, "stone": 500, "iron": 500}

EQUIPMENT_TYPES = ["Sword", "Shield", "Armor", "Ring", "Amulet"]

RARITIES = {
    "Common": {"weight": 60, "stat_range": (1, 5)},
    "Rare": {"weight": 25, "stat_range": (6, 12)},
    "Epic": {"weight": 10, "stat_range": (13, 20)},
    "Legendary": {"weight": 4, "stat_range": (21, 35)},
    "Mythic": {"weight": 1, "stat_range": (36, 50)}
}

STAT_TYPES = ["Infantry Attack", "Cavalry Attack", "Archer Attack", "Defense", "Loot Bonus"]

def generate_equipment():
    roll = random.uniform(0, 100)
    cumulative = 0
    selected_rarity = "Common"
    for rarity, data in RARITIES.items():
        cumulative += data["weight"]
        if roll <= cumulative:
            selected_rarity = rarity
            break
            
    eq_type = random.choice(EQUIPMENT_TYPES)
    stat_type = random.choice(STAT_TYPES)
    
    min_stat, max_stat = RARITIES[selected_rarity]["stat_range"]
    stat_value = random.randint(min_stat, max_stat)
    
    prefixes = ["Cursed", "Blessed", "Ancient", "Gleaming", "Shadowy", "Blood-forged"]
    eq_name = f"{random.choice(prefixes)} {eq_type}"
    eq_id = str(uuid.uuid4())[:8]
    
    return {
        "id": eq_id,
        "name": eq_name,
        "type": eq_type,
        "rarity": selected_rarity,
        "stat_type": stat_type,
        "stat_value": stat_value
    }


def forge_menu(update: Update, context: CallbackContext):
    user = update.effective_user
    emp = get_empire(user.id)
    
    text = (
        f"⚒️ <b>The Forge</b>\n\n"
        f"Strike the anvil and forge powerful equipment for your Heroes. The stats are completely randomized. Can you forge a Mythic God-Roll?\n\n"
        f"<b>Cost per Forge:</b>\n"
        f"🪵 500 Wood\n"
        f"🪨 500 Stone\n"
        f"⚔️ 500 Iron\n\n"
        f"Your Resources:\n"
        f"🪵 {emp['wood']} | 🪨 {emp['stone']} | ⚔️ {emp['iron']}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔨 Forge Equipment", callback_data="forge_craft")],
        [InlineKeyboardButton("🎒 View Inventory", callback_data="forge_inventory")],
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu_main")]
    ])
    
    if update.callback_query:
        update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def forge_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    if data == "forge_craft":
        emp = get_empire(user.id)
        if emp['wood'] < FORGE_COST['wood'] or emp['stone'] < FORGE_COST['stone'] or emp['iron'] < FORGE_COST['iron']:
            query.answer("❌ You do not have enough resources to forge!", show_alert=True)
            return
            
        success = remove_resources(user.id, FORGE_COST['wood'], FORGE_COST['stone'], FORGE_COST['iron'], 0)
        if success:
            equipment = generate_equipment()
            add_inventory_item(user.id, equipment)
            
            colors = {"Common": "⚪", "Rare": "🔵", "Epic": "🟣", "Legendary": "🟡", "Mythic": "🔴"}
            icon = colors.get(equipment["rarity"], "⚪")
            
            text = (
                f"🔥 <b>ITEM FORGED!</b> 🔥\n\n"
                f"{icon} <b>{equipment['name']}</b> ({equipment['rarity']})\n"
                f"🛡️ Type: {equipment['type']}\n"
                f"✨ Stat: +{equipment['stat_value']}% {equipment['stat_type']}\n\n"
                f"<i>Go to 'View Inventory' to see all your forged items!</i>"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔨 Forge Again", callback_data="forge_craft")],
                [InlineKeyboardButton("🔙 Back to Forge", callback_data="forge_main")]
            ])
            query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        else:
            query.answer("❌ Error consuming resources.", show_alert=True)
            
    elif data == "forge_main":
        forge_menu(update, context)
        
    elif data == "forge_inventory":
        emp = get_empire(user.id)
        inventory = emp.get("inventory", [])
        
        if not inventory:
            query.answer("Your inventory is empty! Forge some items first.", show_alert=True)
            return
            
        text = "🎒 <b>Your Inventory</b>\n\n"
        for i, item in enumerate(inventory[:10]):
            text += f"▪️ <b>{item['name']}</b> ({item['rarity']})\n"
            text += f"   <i>+{item['stat_value']}% {item['stat_type']}</i> | ID: {item['id']}\n\n"
            
        text += "<i>Hero Equipment linking is coming in a future update!</i>"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Forge", callback_data="forge_main")]
        ])
        query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


__help__ = """
*Age of Telegram: The Forge*
 ❍ /forge*:* Access the forge to craft randomized equipment for your heroes.
"""

__mod_name__ = "Fᴏʀɢᴇ"

FORGE_HANDLER = CommandHandler("forge", forge_menu, run_async=True)
FORGE_CALLBACK = CallbackQueryHandler(forge_callback, pattern=r"^forge_", run_async=True)

dispatcher.add_handler(FORGE_HANDLER)
dispatcher.add_handler(FORGE_CALLBACK)

__handlers__ = [FORGE_HANDLER, FORGE_CALLBACK]
