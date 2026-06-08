import random
import html
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import get_empire, _empires, add_resources

# Mapping item IDs to their usable logic
def use_scroll(user_id, resource_type, amount, message):
    add_resources(user_id, **{resource_type: amount})
    message.reply_text(
        f"✨ <b>Scroll Activated!</b> ✨\n\n"
        f"The magic fades, and your stockpiles instantly swell with <b>{amount:,} {resource_type.capitalize()}</b>!",
        parse_mode=ParseMode.HTML
    )

def use_loot_chest(user_id, message):
    roll = random.random()
    if roll < 0.10: # 10% chance for a Legendary Hero!
        from MythicRPG.modules.heroes import HEROES
        legendaries = [h for h in HEROES if h["rarity"] == "Legendary"]
        if legendaries:
            hero = random.choice(legendaries)
            _empires.update_one(
                {"user_id": user_id},
                {"$push": {"heroes": hero}}
            )
            message.reply_text(
                f"🎁 <b>LOOT CHEST OPENED!</b> 🎁\n\n"
                f"A blinding golden light emerges from the chest!\n"
                f"🌟 <b>LEGENDARY HERO FOUND!</b> 🌟\n\n"
                f"<b>{hero['name']}</b> has joined your empire!",
                parse_mode=ParseMode.HTML
            )
            return
            
    # Otherwise, huge resources
    w = random.randint(10000, 50000)
    s = random.randint(10000, 50000)
    i = random.randint(5000, 25000)
    f = random.randint(20000, 100000)
    
    add_resources(user_id, wood=w, stone=s, iron=i, food=f)
    
    message.reply_text(
        f"🎁 <b>LOOT CHEST OPENED!</b> 🎁\n\n"
        f"You found massive resources inside:\n"
        f"🌲 Wood: {w:,}\n"
        f"🪨 Stone: {s:,}\n"
        f"⛏️ Iron: {i:,}\n"
        f"🍖 Food: {f:,}",
        parse_mode=ParseMode.HTML
    )

CONSUMABLE_LOGIC = {
    "wood_scroll": lambda uid, msg: use_scroll(uid, "wood", 5000, msg),
    "stone_scroll": lambda uid, msg: use_scroll(uid, "stone", 5000, msg),
    "iron_scroll": lambda uid, msg: use_scroll(uid, "iron", 5000, msg),
    "food_scroll": lambda uid, msg: use_scroll(uid, "food", 10000, msg),
    "loot_chest": lambda uid, msg: use_loot_chest(uid, msg)
}

def inventory_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    emp = get_empire(user.id)
    inv = emp.get("inventory", [])
    
    if not inv:
        update.effective_message.reply_text("🎒 Your inventory is completely empty. Visit The Grand Bazaar in your /wallet to buy items!")
        return
        
    # Group items
    counts = {}
    for item in inv:
        counts[item] = counts.get(item, 0) + 1
        
    keyboard = []
    text = "🎒 <b>YOUR INVENTORY</b> 🎒\n\nClick an item below to consume it:\n\n"
    
    from MythicRPG.modules.economy import SHOP_ITEMS
    shop_dict = {item["id"]: item["name"] for item in SHOP_ITEMS}
    
    for item_id, count in counts.items():
        name = shop_dict.get(item_id, item_id)
        text += f"🔹 {count}x <b>{name}</b>\n"
        keyboard.append([InlineKeyboardButton(f"Use {name}", callback_data=f"inv_use_{item_id}_{user.id}")])
        
    keyboard.append([InlineKeyboardButton("❌ Close Inventory", callback_data="menu_close")])
    
    update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def use_item_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    parts = data.split("_")
    item_id = parts[2]
    owner_id = int(parts[3])
    
    if user.id != owner_id:
        query.answer("This is not your inventory!", show_alert=True)
        return
        
    emp = get_empire(user.id)
    inv = emp.get("inventory", [])
    
    if item_id not in inv:
        query.answer("You don't have this item anymore!", show_alert=True)
        return
        
    # Remove one instance of the item
    inv.remove(item_id)
    _empires.update_one({"user_id": user.id}, {"$set": {"inventory": inv}})
    
    query.answer("Consuming item...")
    query.message.delete()
    
    logic = CONSUMABLE_LOGIC.get(item_id)
    if logic:
        logic(user.id, update.effective_message)
    else:
        update.effective_message.reply_text("This item has no usable effect.")


__help__ = """
*Age of Telegram: Inventory & Consumables*
 ❍ /inventory*:* View your purchased items and consume them.
"""

__mod_name__ = "Iɴᴠᴇɴᴛᴏʀʏ"

INV_HANDLER = CommandHandler("inventory", inventory_cmd, run_async=True)
USE_CALLBACK = CallbackQueryHandler(use_item_callback, pattern=r"^inv_use_", run_async=True)

dispatcher.add_handler(INV_HANDLER)
dispatcher.add_handler(USE_CALLBACK)

__handlers__ = [INV_HANDLER, USE_CALLBACK]
