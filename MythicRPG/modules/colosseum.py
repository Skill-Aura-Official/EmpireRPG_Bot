import random
import time
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import get_coins, remove_coins, add_coins

# Global state for the active match
active_match = None
bets = [] # List of {"user_id": int, "gladiator": int, "amount": int, "name": str}

GLADIATORS = [
    {"name": "Spartacus the Undefeated", "power": random.randint(150, 250)},
    {"name": "Grog the Ogre", "power": random.randint(100, 200)},
    {"name": "Elara the Swift", "power": random.randint(120, 180)},
    {"name": "Ignis the Fire Mage", "power": random.randint(130, 220)},
    {"name": "Shadowblade", "power": random.randint(140, 210)},
    {"name": "Ironclad Goliath", "power": random.randint(180, 260)}
]

def calculate_odds(p1_power, p2_power):
    total = p1_power + p2_power
    p1_win_prob = p1_power / total
    p2_win_prob = p2_power / total
    
    # House edge of 5% (Total probability = 1.05)
    # Odds = 1 / implied probability
    p1_odds = round(1 / (p1_win_prob + 0.05), 2)
    p2_odds = round(1 / (p2_win_prob + 0.05), 2)
    
    # Ensure minimum odds of 1.1x
    return max(1.1, p1_odds), max(1.1, p2_odds)

def startmatch_cmd(update: Update, context: CallbackContext):
    global active_match, bets
    if active_match is not None:
        update.effective_message.reply_text("❌ A match is already active! Wait for it to finish.")
        return
        
    g1 = random.choice(GLADIATORS).copy()
    g2 = random.choice(GLADIATORS).copy()
    while g1['name'] == g2['name']:
        g2 = random.choice(GLADIATORS).copy()
        
    # Re-roll power to make it dynamic
    g1['power'] = random.randint(100, 250)
    g2['power'] = random.randint(100, 250)
    
    odds1, odds2 = calculate_odds(g1['power'], g2['power'])
    
    active_match = {
        "g1": g1, "g2": g2,
        "odds1": odds1, "odds2": odds2,
        "status": "betting"
    }
    bets = []
    
    text = (
        f"🏟️ <b>COLOSSEUM MATCH ANNOUNCED!</b> 🏟️\n\n"
        f"<b>Gladiator 1:</b> {g1['name']} (Power: {g1['power']})\n"
        f"<i>Payout Odds: {odds1}x</i>\n\n"
        f"<b>Gladiator 2:</b> {g2['name']} (Power: {g2['power']})\n"
        f"<i>Payout Odds: {odds2}x</i>\n\n"
        f"💰 Use `/bet 1 <amount>` or `/bet 2 <amount>` to place your wagers!\n"
        f"<i>An admin will use /runmatch to start the fight.</i>"
    )
    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)

def bet_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    args = context.args
    
    if active_match is None or active_match["status"] != "betting":
        update.effective_message.reply_text("❌ There is no active match accepting bets right now.")
        return
        
    if len(args) != 2:
        update.effective_message.reply_text("ℹ️ <b>Usage:</b> /bet <1 or 2> <amount>", parse_mode=ParseMode.HTML)
        return
        
    try:
        choice = int(args[0])
        amount = int(args[1])
    except ValueError:
        update.effective_message.reply_text("❌ Invalid numbers.")
        return
        
    if choice not in [1, 2]:
        update.effective_message.reply_text("❌ Choose Gladiator 1 or 2.")
        return
        
    if amount < 100:
        update.effective_message.reply_text("❌ Minimum bet is 100 Coins.")
        return
        
    # Check if already bet
    for b in bets:
        if b["user_id"] == user.id:
            update.effective_message.reply_text("❌ You have already placed a bet on this match.")
            return
            
    gold = get_coins(user.id)
    if gold < amount:
        update.effective_message.reply_text("❌ You don't have enough Coins!")
        return
        
    remove_coins(user.id, amount)
    bets.append({
        "user_id": user.id,
        "name": user.first_name,
        "gladiator": choice,
        "amount": amount
    })
    
    gladiator_name = active_match[f"g{choice}"]["name"]
    odds = active_match[f"odds{choice}"]
    potential_win = int(amount * odds)
    
    update.effective_message.reply_text(
        f"✅ <b>BET PLACED!</b>\n\n"
        f"You wagered 💰 <b>{amount} Coins</b> on <b>{gladiator_name}</b>.\n"
        f"Potential payout: 💰 <b>{potential_win} Coins</b>!",
        parse_mode=ParseMode.HTML
    )

def generate_commentary(g1_name, g2_name, round_num, advantage):
    moves = [
        "delivers a crushing blow to",
        "dodges an attack and counter-strikes",
        "unleashes a special move against",
        "parries the weapon of",
        "finds an opening and slashes"
    ]
    attacker = g1_name if advantage == 1 else g2_name
    defender = g2_name if advantage == 1 else g1_name
    move = random.choice(moves)
    return f"⚔️ <b>Round {round_num}:</b> {attacker} {move} {defender}!"

def runmatch_cmd(update: Update, context: CallbackContext):
    global active_match, bets
    
    if active_match is None:
        update.effective_message.reply_text("❌ No active match to run.")
        return
    if active_match["status"] != "betting":
        update.effective_message.reply_text("❌ Match is already running or finished.")
        return
        
    active_match["status"] = "running"
    g1 = active_match["g1"]
    g2 = active_match["g2"]
    
    msg = update.effective_message.reply_text(f"🏟️ <b>THE MATCH BEGINS!</b>\n\n{g1['name']} VS {g2['name']}...", parse_mode=ParseMode.HTML)
    
    # Run 3 rounds of commentary
    p1_score = 0
    p2_score = 0
    
    for r in range(1, 4):
        time.sleep(2)
        
        # Calculate advantage based on power
        p1_chance = g1['power'] / (g1['power'] + g2['power'])
        if random.random() < p1_chance:
            adv = 1
            p1_score += 1
        else:
            adv = 2
            p2_score += 1
            
        comment = generate_commentary(g1['name'], g2['name'], r, adv)
        msg.edit_text(f"{msg.text}\n\n{comment}", parse_mode=ParseMode.HTML)
        
    time.sleep(2)
    
    # Determine winner
    if p1_score > p2_score:
        winner = 1
        winner_name = g1['name']
        winner_odds = active_match['odds1']
    elif p2_score > p1_score:
        winner = 2
        winner_name = g2['name']
        winner_odds = active_match['odds2']
    else:
        # Tie breaker
        if random.random() < 0.5:
            winner = 1
            winner_name = g1['name']
            winner_odds = active_match['odds1']
        else:
            winner = 2
            winner_name = g2['name']
            winner_odds = active_match['odds2']
            
    final_text = f"{msg.text}\n\n🏆 <b>{winner_name.upper()} WINS THE MATCH!</b> 🏆\n\n<b>Payouts:</b>\n"
    
    # Process payouts
    winners_count = 0
    for b in bets:
        if b['gladiator'] == winner:
            payout = int(b['amount'] * winner_odds)
            add_coins(b['user_id'], payout)
            final_text += f"✅ <b>{b['name']}</b> won 💰 {payout} Coins!\n"
            winners_count += 1
        else:
            final_text += f"❌ <b>{b['name']}</b> lost {b['amount']} Coins.\n"
            
    if winners_count == 0 and not bets:
        final_text += "<i>No bets were placed.</i>"
        
    msg.edit_text(final_text, parse_mode=ParseMode.HTML)
    
    # Reset
    active_match = None
    bets = []


def tournament_cmd(update: Update, context: CallbackContext):
    if active_match is not None:
        update.effective_message.reply_text("❌ Cannot start a tournament while a match is active.")
        return
        
    participants = random.sample(GLADIATORS, 4)
    # Give them fresh power
    for p in participants:
        p['power'] = random.randint(100, 250)
        
    text = "🏆 <b>THE COLOSSEUM TOURNAMENT BEGINS!</b> 🏆\n\n<b>Quarterfinals Bracket:</b>\n"
    text += f"🗡️ {participants[0]['name']} VS {participants[1]['name']}\n"
    text += f"🗡️ {participants[2]['name']} VS {participants[3]['name']}\n\n"
    text += "<i>The matches will run automatically...</i>"
    
    msg = update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    
    # Semi 1
    time.sleep(3)
    p1_chance = participants[0]['power'] / (participants[0]['power'] + participants[1]['power'])
    winner_1 = participants[0] if random.random() < p1_chance else participants[1]
    msg.edit_text(f"{msg.text}\n\n⚔️ <b>Match 1 Winner:</b> {winner_1['name']}!", parse_mode=ParseMode.HTML)
    
    # Semi 2
    time.sleep(3)
    p2_chance = participants[2]['power'] / (participants[2]['power'] + participants[3]['power'])
    winner_2 = participants[2] if random.random() < p2_chance else participants[3]
    msg.edit_text(f"{msg.text}\n⚔️ <b>Match 2 Winner:</b> {winner_2['name']}!", parse_mode=ParseMode.HTML)
    
    # Final
    time.sleep(4)
    msg.edit_text(f"{msg.text}\n\n🔥 <b>GRAND FINALE</b> 🔥\n{winner_1['name']} VS {winner_2['name']}...", parse_mode=ParseMode.HTML)
    
    time.sleep(4)
    final_chance = winner_1['power'] / (winner_1['power'] + winner_2['power'])
    champion = winner_1 if random.random() < final_chance else winner_2
    
    msg.edit_text(f"{msg.text}\n\n👑 <b>THE TOURNAMENT CHAMPION IS {champion['name'].upper()}!</b> 👑", parse_mode=ParseMode.HTML)


__help__ = """
*Age of Telegram: The Colosseum*
 ❍ /startmatch*:* Announce a new NPC gladiator match.
 ❍ /bet <1 or 2> <amount>*:* Bet on Gladiator 1 or 2 using Coins.
 ❍ /runmatch*:* Start the fight and watch the live commentary!
 ❍ /tournament*:* Watch a fully automated 4-gladiator bracket tournament!
"""

__mod_name__ = "Cᴏʟᴏssᴇᴜᴍ"

START_HANDLER = CommandHandler("startmatch", startmatch_cmd, run_async=True)
BET_HANDLER = CommandHandler("bet", bet_cmd, run_async=True)
RUN_HANDLER = CommandHandler("runmatch", runmatch_cmd, run_async=True)
TOURNEY_HANDLER = CommandHandler("tournament", tournament_cmd, run_async=True)

dispatcher.add_handler(START_HANDLER)
dispatcher.add_handler(BET_HANDLER)
dispatcher.add_handler(RUN_HANDLER)
dispatcher.add_handler(TOURNEY_HANDLER)

__handlers__ = [START_HANDLER, BET_HANDLER, RUN_HANDLER, TOURNEY_HANDLER]
