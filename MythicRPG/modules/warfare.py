import random
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import (
    get_empire, remove_resources, train_troops, get_coins, remove_coins, add_coins, kill_troops,
    get_guild_by_user, add_war_points
)

# --- MARKET PRICES ---
# Simple in-memory prices. In a real scenario, this could fluctuate based on server-wide buys/sells.
MARKET_PRICES = {
    "wood": 2,
    "stone": 4,
    "iron": 10,
    "food": 2
}

def train_menu(update: Update, context: CallbackContext):
    user = update.effective_user
    emp = get_empire(user.id)
    
    text = (
        f"⚔️ <b>Barracks & Stables</b>\n\n"
        f"<i>Current Army:</i>\n"
        f"🗡️ Infantry: {emp['infantry']} | 🐎 Cavalry: {emp['cavalry']} | 🏹 Archers: {emp['archers']}\n\n"
        f"<b>Costs per 10 Troops:</b>\n"
        f"🗡️ Infantry: 100 🍞 Food\n"
        f"🐎 Cavalry: 200 🍞 Food, 50 ⚔️ Iron\n"
        f"🏹 Archers: 150 🪵 Wood, 50 🍞 Food\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗡️ Train 10 Infantry", callback_data="train_infantry"),
            InlineKeyboardButton("🐎 Train 10 Cavalry", callback_data="train_cavalry"),
        ],
        [
            InlineKeyboardButton("🏹 Train 10 Archers", callback_data="train_archers"),
        ]
    ])
    
    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def train_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    emp = get_empire(user.id)
    
    if data == "train_infantry":
        if emp['food'] < 100:
            query.answer("❌ Not enough Food! Need 100.", show_alert=True)
            return
        remove_resources(user.id, food=100)
        train_troops(user.id, "infantry", 10)
        query.answer("✅ 10 Infantry trained successfully!", show_alert=True)
        
    elif data == "train_cavalry":
        if emp['food'] < 200 or emp['iron'] < 50:
            query.answer("❌ Not enough resources! Need 200 Food, 50 Iron.", show_alert=True)
            return
        remove_resources(user.id, food=200, iron=50)
        train_troops(user.id, "cavalry", 10)
        query.answer("✅ 10 Cavalry trained successfully!", show_alert=True)
        
    elif data == "train_archers":
        if emp['wood'] < 150 or emp['food'] < 50:
            query.answer("❌ Not enough resources! Need 150 Wood, 50 Food.", show_alert=True)
            return
        remove_resources(user.id, wood=150, food=50)
        train_troops(user.id, "archers", 10)
        query.answer("✅ 10 Archers trained successfully!", show_alert=True)
    
    # Edit message to reflect new stats
    emp = get_empire(user.id)
    text = (
        f"⚔️ <b>Barracks & Stables</b>\n\n"
        f"<i>Current Army:</i>\n"
        f"🗡️ Infantry: {emp['infantry']} | 🐎 Cavalry: {emp['cavalry']} | 🏹 Archers: {emp['archers']}\n\n"
        f"<b>Costs per 10 Troops:</b>\n"
        f"🗡️ Infantry: 100 🍞 Food\n"
        f"🐎 Cavalry: 200 🍞 Food, 50 ⚔️ Iron\n"
        f"🏹 Archers: 150 🪵 Wood, 50 🍞 Food\n"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗡️ Train 10 Infantry", callback_data="train_infantry"),
            InlineKeyboardButton("🐎 Train 10 Cavalry", callback_data="train_cavalry"),
        ],
        [
            InlineKeyboardButton("🏹 Train 10 Archers", callback_data="train_archers"),
        ]
    ])
    query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def simulate_combat(att_inf, att_cav, att_arch, def_inf, def_cav, def_arch, def_wall_lvl, att_hero=None, def_hero=None):
    # Base power
    att_base = att_inf * 1 + att_cav * 2.5 + att_arch * 1.5
    def_base = def_inf * 1 + def_cav * 2.5 + def_arch * 1.5 + def_wall_lvl * 50
    
    # Hero Rarity & Stat Multipliers
    att_multiplier = 1.0
    def_multiplier = 1.0
    
    RARITY_MULTS = {"Common": 1.05, "Rare": 1.10, "Epic": 1.25, "Legendary": 1.50, "Mythic": 2.00}
    if att_hero:
        att_multiplier *= RARITY_MULTS.get(att_hero.get("rarity", "Common"), 1.0)
    if def_hero:
        def_multiplier *= RARITY_MULTS.get(def_hero.get("rarity", "Common"), 1.0)
        
    # Faction RPS Logic: Fire > Earth > Water > Fire, Light >< Dark
    if att_hero and def_hero:
        af = att_hero.get("faction")
        df = def_hero.get("faction")
        if (af == "Fire" and df == "Earth") or (af == "Earth" and df == "Water") or (af == "Water" and df == "Fire") or (af == "Light" and df == "Dark"):
            att_multiplier *= 1.2
        elif (df == "Fire" and af == "Earth") or (df == "Earth" and af == "Water") or (df == "Water" and af == "Fire") or (df == "Light" and af == "Dark"):
            def_multiplier *= 1.2
    
    # RPS Multipliers
    # Infantry vs Cavalry (Infantry beats Cavalry)
    att_inf_bonus = min(att_inf, def_cav) * 1.0
    def_inf_bonus = min(def_inf, att_cav) * 1.0
    
    # Cavalry vs Archers (Cavalry beats Archers)
    att_cav_bonus = min(att_cav, def_arch) * 1.5
    def_cav_bonus = min(def_cav, att_arch) * 1.5
    
    # Archers vs Infantry (Archers beat Infantry)
    att_arch_bonus = min(att_arch, def_inf) * 1.0
    def_arch_bonus = min(def_arch, att_inf) * 1.0
    
    att_total = (att_base + att_inf_bonus + att_cav_bonus + att_arch_bonus) * att_multiplier
    def_total = (def_base + def_inf_bonus + def_cav_bonus + def_arch_bonus) * def_multiplier
    
    return att_total > def_total, att_total, def_total


def raid(update: Update, context: CallbackContext):
    user = update.effective_user
    message = update.effective_message
    
    if not message.reply_to_message:
        message.reply_text("⚔️ You must reply to a user's message to raid them!")
        return
        
    target = message.reply_to_message.from_user
    if target.id == user.id:
        message.reply_text("❌ You cannot raid yourself!")
        return
    if target.is_bot:
        message.reply_text("❌ You cannot raid a bot!")
        return
        
    att_emp = get_empire(user.id)
    def_emp = get_empire(target.id)
    
    # Check if attacker has troops
    if att_emp['infantry'] == 0 and att_emp['cavalry'] == 0 and att_emp['archers'] == 0:
        message.reply_text("❌ You don't have an army to attack with! Use /train first.")
        return
        
    # Fetch active heroes
    att_hero = next((h for h in att_emp.get("heroes", []) if h["id"] == att_emp.get("active_hero_id")), None)
    def_hero = next((h for h in def_emp.get("heroes", []) if h["id"] == def_emp.get("active_hero_id")), None)

    # Simulate Combat
    attacker_won, att_power, def_power = simulate_combat(
        att_emp['infantry'], att_emp['cavalry'], att_emp['archers'],
        def_emp['infantry'], def_emp['cavalry'], def_emp['archers'],
        def_emp['town_hall_level'], att_hero, def_hero
    )
    
    if attacker_won:
        # Calculate spoils (15% - 25% of unprotected resources)
        steal_pct = random.uniform(0.15, 0.25)
        stolen_wood = int(def_emp['wood'] * steal_pct)
        stolen_stone = int(def_emp['stone'] * steal_pct)
        stolen_iron = int(def_emp['iron'] * steal_pct)
        stolen_food = int(def_emp['food'] * steal_pct)
        
        # Apply casualty
        att_cas_inf = int(att_emp['infantry'] * 0.1)
        att_cas_cav = int(att_emp['cavalry'] * 0.1)
        att_cas_arch = int(att_emp['archers'] * 0.1)
        
        def_cas_inf = int(def_emp['infantry'] * 0.3)
        def_cas_cav = int(def_emp['cavalry'] * 0.3)
        def_cas_arch = int(def_emp['archers'] * 0.3)
        
        from MythicRPG.modules.mongo import add_resources
        
        # Transfer resources
        remove_resources(target.id, wood=stolen_wood, stone=stolen_stone, iron=stolen_iron, food=stolen_food)
        add_resources(user.id, wood=stolen_wood, stone=stolen_stone, iron=stolen_iron, food=stolen_food)
        
        # Kill troops
        kill_troops(user.id, infantry=att_cas_inf, cavalry=att_cas_cav, archers=att_cas_arch)
        kill_troops(target.id, infantry=def_cas_inf, cavalry=def_cas_cav, archers=def_cas_arch)
        
        # Check for Guild War points
        att_guild = get_guild_by_user(message.chat_id, user.id)
        def_guild = get_guild_by_user(message.chat_id, target.id)
        war_msg = ""
        if att_guild and def_guild and att_guild['war_status'] == 'war' and att_guild['war_target'] == def_guild['guild_id']:
            pts = random.randint(10, 30)
            add_war_points(att_guild['guild_id'], pts)
            war_msg = f"\n\n🎖 <b>+{pts} War Points</b> for {att_guild['name']}!"

        # Hero Capture Logic (5% chance)
        capture_msg = ""
        if def_hero and random.random() < 0.05:
            from MythicRPG.modules.mongo import remove_hero, add_hero
            remove_hero(target.id, def_hero['id'])
            add_hero(user.id, def_hero)
            capture_msg = f"\n\n🚨 <b>HERO CAPTURED!</b> You captured <b>{def_hero['name']}</b> ({def_hero['rarity']})!"

        message.reply_text(
            f"🔥 <b>RAID SUCCESSFUL!</b> 🔥\n\n"
            f"⚔️ <b>{user.first_name}</b> crushed <b>{target.first_name}</b>'s defenses!\n"
            f"(Power: {att_power:.1f} vs {def_power:.1f})\n\n"
            f"<b>Loot Stolen:</b>\n"
            f"🪵 Wood: {stolen_wood} | 🪨 Stone: {stolen_stone}\n"
            f"⚔️ Iron: {stolen_iron} | 🍞 Food: {stolen_food}\n\n"
            f"<b>Casualties:</b>\n"
            f"Attacker lost: {att_cas_inf} Inf, {att_cas_cav} Cav, {att_cas_arch} Arch.\n"
            f"Defender lost: {def_cas_inf} Inf, {def_cas_cav} Cav, {def_cas_arch} Arch.{war_msg}{capture_msg}",
            parse_mode=ParseMode.HTML
        )
        
        # Check and claim bounties
        try:
            from MythicRPG.modules.bounty import check_and_claim_bounty
            check_and_claim_bounty(user.id, user.first_name, target.id, update)
        except Exception as e:
            print(f"Error claiming bounty: {e}")
            
    else:
        # Attacker lost
        att_cas_inf = int(att_emp['infantry'] * 0.4)
        att_cas_cav = int(att_emp['cavalry'] * 0.4)
        att_cas_arch = int(att_emp['archers'] * 0.4)
        
        def_cas_inf = int(def_emp['infantry'] * 0.05)
        def_cas_cav = int(def_emp['cavalry'] * 0.05)
        def_cas_arch = int(def_emp['archers'] * 0.05)
        
        kill_troops(user.id, infantry=att_cas_inf, cavalry=att_cas_cav, archers=att_cas_arch)
        kill_troops(target.id, infantry=def_cas_inf, cavalry=def_cas_cav, archers=def_cas_arch)
        
        message.reply_text(
            f"🛡️ <b>RAID FAILED!</b> 🛡️\n\n"
            f"<b>{target.first_name}</b>'s defenses held strong against <b>{user.first_name}</b>!\n"
            f"(Power: {att_power:.1f} vs {def_power:.1f})\n\n"
            f"<b>Casualties:</b>\n"
            f"Attacker lost: {att_cas_inf} Inf, {att_cas_cav} Cav, {att_cas_arch} Arch.\n"
            f"Defender lost: {def_cas_inf} Inf, {def_cas_cav} Cav, {def_cas_arch} Arch.",
            parse_mode=ParseMode.HTML
        )


def market(update: Update, context: CallbackContext):
    user = update.effective_user
    emp = get_empire(user.id)
    gold = get_coins(user.id)
    
    text = (
        f"📈 <b>Global Resource Market</b>\n\n"
        f"<i>Current Prices per 100 units:</i>\n"
        f"🪵 Wood: {MARKET_PRICES['wood'] * 100} Coins\n"
        f"🪨 Stone: {MARKET_PRICES['stone'] * 100} Coins\n"
        f"⚔️ Iron: {MARKET_PRICES['iron'] * 100} Coins\n"
        f"🍞 Food: {MARKET_PRICES['food'] * 100} Coins\n\n"
        f"Your Coins: 🪙 <b>{gold}</b>\n\n"
        f"Use the buttons below to buy or sell resources in bulk (100 units)."
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 Buy Wood", callback_data="buy_wood"),
            InlineKeyboardButton("💰 Sell Wood", callback_data="sell_wood"),
        ],
        [
            InlineKeyboardButton("🛒 Buy Stone", callback_data="buy_stone"),
            InlineKeyboardButton("💰 Sell Stone", callback_data="sell_stone"),
        ],
        [
            InlineKeyboardButton("🛒 Buy Iron", callback_data="buy_iron"),
            InlineKeyboardButton("💰 Sell Iron", callback_data="sell_iron"),
        ],
        [
            InlineKeyboardButton("🛒 Buy Food", callback_data="buy_food"),
            InlineKeyboardButton("💰 Sell Food", callback_data="sell_food"),
        ],
        [
            InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu_main"),
        ]
    ])
    
    if update.callback_query:
        update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def market_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    if data.startswith("buy_") or data.startswith("sell_"):
        action, resource = data.split("_")
        price = MARKET_PRICES[resource] * 100
        
        if action == "buy":
            gold = get_coins(user.id)
            if gold < price:
                query.answer(f"❌ Not enough Coins! Need {price} Coins.", show_alert=True)
                return
            remove_coins(user.id, price)
            
            from MythicRPG.modules.mongo import add_resources
            if resource == "wood": add_resources(user.id, wood=100)
            elif resource == "stone": add_resources(user.id, stone=100)
            elif resource == "iron": add_resources(user.id, iron=100)
            elif resource == "food": add_resources(user.id, food=100)
            
            query.answer(f"✅ Bought 100 {resource.capitalize()} for {price} Coins!", show_alert=True)
            
        elif action == "sell":
            emp = get_empire(user.id)
            if emp[resource] < 100:
                query.answer(f"❌ Not enough {resource.capitalize()}! Need 100.", show_alert=True)
                return
                
            remove_resources(user.id, **{resource: 100})
            add_coins(user.id, price)
            
            query.answer(f"✅ Sold 100 {resource.capitalize()} for {price} Coins!", show_alert=True)
            
        # Refresh market view
        market(update, context)


__help__ = """
*Age of Telegram: Warfare & Economy*

*Commands:*
 ❍ /train*:* Train troops for your army.
 ❍ /raid*:* Reply to a user to raid their empire.
 ❍ /market*:* Buy and sell resources using Gold.
"""

__mod_name__ = "Wᴀʀꜰᴀʀᴇ"

TRAIN_HANDLER = CommandHandler("train", train_menu, run_async=True)
RAID_HANDLER = CommandHandler("raid", raid, run_async=True)
MARKET_HANDLER = CommandHandler("market", market, run_async=True)

TRAIN_CALLBACKS = CallbackQueryHandler(train_callback, pattern=r"^train_", run_async=True)
MARKET_CALLBACKS = CallbackQueryHandler(market_callback, pattern=r"^(buy_|sell_)", run_async=True)

dispatcher.add_handler(TRAIN_HANDLER)
dispatcher.add_handler(RAID_HANDLER)
dispatcher.add_handler(MARKET_HANDLER)
dispatcher.add_handler(TRAIN_CALLBACKS)
dispatcher.add_handler(MARKET_CALLBACKS)

__handlers__ = [TRAIN_HANDLER, RAID_HANDLER, MARKET_HANDLER, TRAIN_CALLBACKS, MARKET_CALLBACKS]
