import math
import random
import html
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import _db, get_empire, get_coins, add_coins, kill_troops

_bosses = _db["world_boss"] if _db is not None else None

def get_active_boss():
    if _bosses is None:
        return None
    return _bosses.find_one({"active": True})

def spawnboss_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    # Hardcoded admin check or allow anyone for testing
    # We will allow anyone to spawn a boss if none is active for now
    if _bosses is None:
        update.effective_message.reply_text("Database offline.")
        return
        
    active = get_active_boss()
    if active:
        update.effective_message.reply_text(f"❌ A World Boss is already active: <b>{active['name']}</b>", parse_mode=ParseMode.HTML)
        return
        
    boss_types = [
        {"name": "The Obsidian Dragon", "health": 5000000},
        {"name": "Titan of the Deep", "health": 8000000},
        {"name": "Corrupted Warlord", "health": 3000000}
    ]
    boss = random.choice(boss_types)
    
    _bosses.insert_one({
        "name": boss["name"],
        "max_health": boss["health"],
        "current_health": boss["health"],
        "phase": 1,
        "active": True,
        "participants": {} # user_id_str -> {"name": name, "damage": dmg}
    })
    
    update.effective_message.reply_text(
        f"🚨 <b>WORLD BOSS SPAWNED!</b> 🚨\n\n"
        f"<b>{boss['name']}</b> has appeared with {boss['health']:,} HP!\n"
        f"<i>All empires must unite to defeat this threat. Use /attackboss to deal damage!</i>",
        parse_mode=ParseMode.HTML
    )

def worldboss_cmd(update: Update, context: CallbackContext):
    boss = get_active_boss()
    if not boss:
        update.effective_message.reply_text("🌍 The world is currently at peace. No World Boss is active.")
        return
        
    health_pct = (boss['current_health'] / boss['max_health']) * 100
    
    phase_text = ""
    if boss['phase'] == 1:
        phase_text = "🟢 Phase 1: Gathering Power"
    elif boss['phase'] == 2:
        phase_text = "🟡 Phase 2: ENRAGED! (Double Retaliation Damage)"
    elif boss['phase'] == 3:
        phase_text = "🔴 Phase 3: DESPERATE! (50% Damage Reduction)"
        
    # Sort participants by damage
    parts = list(boss['participants'].values())
    parts.sort(key=lambda x: x['damage'], reverse=True)
    
    leaderboard = "\n\n<b>Top Damage Dealers:</b>\n"
    for i, p in enumerate(parts[:5], 1):
        leaderboard += f"{i}. <b>{p['name']}</b> - 💥 {p['damage']:,}\n"
        
    if not parts:
        leaderboard += "<i>No one has attacked yet!</i>"
        
    text = (
        f"🐉 <b>WORLD BOSS: {boss['name']}</b> 🐉\n\n"
        f"❤️ <b>Health:</b> {boss['current_health']:,} / {boss['max_health']:,} ({health_pct:.1f}%)\n"
        f"⚡ <b>Status:</b> {phase_text}"
        f"{leaderboard}\n\n"
        f"<i>Use /attackboss <infantry> <cavalry> <archers> to strike!</i>"
    )
    
    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def attackboss_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    args = context.args
    message = update.effective_message
    
    boss = get_active_boss()
    if not boss:
        message.reply_text("❌ No World Boss is currently active.")
        return
        
    if len(args) != 3:
        message.reply_text("ℹ️ <b>Usage:</b> /attackboss <infantry> <cavalry> <archers>\n<i>Example: /attackboss 100 50 20</i>", parse_mode=ParseMode.HTML)
        return
        
    try:
        inf_sent = int(args[0])
        cav_sent = int(args[1])
        arch_sent = int(args[2])
    except:
        message.reply_text("❌ Please provide valid numbers.")
        return
        
    if inf_sent < 0 or cav_sent < 0 or arch_sent < 0:
        message.reply_text("❌ Cannot send negative troops.")
        return
        
    if inf_sent == 0 and cav_sent == 0 and arch_sent == 0:
        message.reply_text("❌ You must send at least one troop.")
        return
        
    emp = get_empire(user.id)
    if emp['infantry'] < inf_sent or emp['cavalry'] < cav_sent or emp['archers'] < arch_sent:
        message.reply_text("❌ You don't have enough troops for this attack!")
        return
        
    # Calculate damage
    base_dmg = (inf_sent * 1) + (cav_sent * 2.5) + (arch_sent * 1.5)
    
    # Hero multiplier
    att_hero = next((h for h in emp.get("heroes", []) if h["id"] == emp.get("active_hero_id")), None)
    multiplier = 1.0
    RARITY_MULTS = {"Common": 1.05, "Rare": 1.10, "Epic": 1.25, "Legendary": 1.50, "Mythic": 2.00}
    if att_hero:
        multiplier *= RARITY_MULTS.get(att_hero.get("rarity", "Common"), 1.0)
        
    total_dmg = int(base_dmg * multiplier)
    
    # Phase specific logic
    if boss['phase'] == 3:
        total_dmg = int(total_dmg * 0.5) # 50% damage reduction
        
    retaliation_mult = 1.0
    if boss['phase'] == 2:
        retaliation_mult = 2.0
        
    # Retaliation kills (Boss kills a percentage of troops sent)
    kill_pct = random.uniform(0.1, 0.3) * retaliation_mult
    cas_inf = int(inf_sent * kill_pct)
    cas_cav = int(cav_sent * kill_pct)
    cas_arch = int(arch_sent * kill_pct)
    
    # Apply damage
    new_health = max(0, boss['current_health'] - total_dmg)
    
    # Update participants
    parts = boss['participants']
    uid_str = str(user.id)
    if uid_str not in parts:
        parts[uid_str] = {"name": user.first_name, "damage": 0}
    parts[uid_str]["damage"] += total_dmg
    
    # Check for phase transitions
    new_phase = boss['phase']
    phase_msg = ""
    if new_health > 0:
        health_pct = new_health / boss['max_health']
        if health_pct <= 0.66 and boss['phase'] == 1:
            new_phase = 2
            phase_msg = "\n\n⚠️ <b>THE BOSS HAS ENRAGED! (Phase 2)</b>\n<i>Retaliation damage is doubled!</i>"
        elif health_pct <= 0.33 and boss['phase'] == 2:
            new_phase = 3
            phase_msg = "\n\n⚠️ <b>THE BOSS GROWS DESPERATE! (Phase 3)</b>\n<i>Boss takes 50% less damage!</i>"
            
    # Update DB
    _bosses.update_one(
        {"_id": boss["_id"]},
        {"$set": {
            "current_health": new_health,
            "phase": new_phase,
            "participants": parts
        }}
    )
    
    # Kill troops
    kill_troops(user.id, infantry=cas_inf, cavalry=cas_cav, archers=cas_arch)
    
    if new_health <= 0:
        # Boss Defeated!
        _bosses.update_one({"_id": boss["_id"]}, {"$set": {"active": False}})
        distribute_boss_loot(boss['name'], parts, context, message.chat_id)
        
        message.reply_text(
            f"🎉 <b>WORLD BOSS DEFEATED!</b> 🎉\n\n"
            f"<b>{user.first_name}</b> delivered the final blow to <b>{boss['name']}</b>!\n"
            f"<i>Loot is being distributed to all participants...</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        message.reply_text(
            f"⚔️ <b>ATTACK SUCCESSFUL</b> ⚔️\n\n"
            f"You dealt 💥 <b>{total_dmg:,}</b> damage to <b>{boss['name']}</b>!\n"
            f"❤️ Boss HP remaining: {new_health:,}\n\n"
            f"<b>Retaliation Casualties:</b>\n"
            f"💀 {cas_inf} Infantry, {cas_cav} Cavalry, {cas_arch} Archers{phase_msg}",
            parse_mode=ParseMode.HTML
        )

def distribute_boss_loot(boss_name, participants_dict, context, chat_id):
    parts = list(participants_dict.items())
    parts.sort(key=lambda x: x[1]['damage'], reverse=True)
    
    from MythicRPG.modules.mongo import add_resources
    
    text = f"🏆 <b>{boss_name} - Loot Distribution</b> 🏆\n\n"
    
    for i, (uid_str, data) in enumerate(parts):
        uid = int(uid_str)
        if i == 0:
            # Rank 1
            coins = 50000
            add_coins(uid, coins)
            add_resources(uid, wood=100000, stone=100000, iron=50000, food=200000)
            text += f"🥇 <b>{data['name']}</b> - 50,000 Coins, Massive Resources\n"
        elif i == 1:
            # Rank 2
            coins = 25000
            add_coins(uid, coins)
            add_resources(uid, wood=50000, stone=50000, iron=25000, food=100000)
            text += f"🥈 <b>{data['name']}</b> - 25,000 Coins, Huge Resources\n"
        elif i == 2:
            # Rank 3
            coins = 10000
            add_coins(uid, coins)
            add_resources(uid, wood=25000, stone=25000, iron=10000, food=50000)
            text += f"🥉 <b>{data['name']}</b> - 10,000 Coins, Large Resources\n"
        else:
            # Participation
            coins = 2000
            add_coins(uid, coins)
            add_resources(uid, wood=5000, stone=5000, iron=2000, food=10000)
            
    if len(parts) > 3:
        text += f"\n<i>...and {len(parts)-3} other participants received 2,000 Coins!</i>"
        
    try:
        context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    except:
        pass


__help__ = """
*Age of Telegram: World Bosses*
 ❍ /spawnboss*:* Force spawn a world boss (Anyone can use if no boss is active).
 ❍ /worldboss*:* View the currently active World Boss and leaderboard.
 ❍ /attackboss <inf> <cav> <arch>*:* Attack the boss with your troops.
"""

__mod_name__ = "Wᴏʀʟᴅ Bᴏssᴇs"

SPAWN_HANDLER = CommandHandler("spawnboss", spawnboss_cmd, run_async=True)
WORLDBOSS_HANDLER = CommandHandler("worldboss", worldboss_cmd, run_async=True)
ATTACKBOSS_HANDLER = CommandHandler("attackboss", attackboss_cmd, run_async=True)

dispatcher.add_handler(SPAWN_HANDLER)
dispatcher.add_handler(WORLDBOSS_HANDLER)
dispatcher.add_handler(ATTACKBOSS_HANDLER)

__handlers__ = [SPAWN_HANDLER, WORLDBOSS_HANDLER, ATTACKBOSS_HANDLER]
