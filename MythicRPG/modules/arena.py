import random
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import (
    get_empire, get_coins, remove_coins, add_coins, add_xp,
    create_battle, get_battle, add_bet, resolve_battle
)
from MythicRPG.modules.warfare import simulate_combat

# In-memory storage for active duel requests before they are accepted
PENDING_DUELS = {}

def arena_menu(update: Update, context: CallbackContext):
    text = (
        "🏟 <b>The Arena</b>\n\n"
        "Welcome to the bloodiest sands in Telegram! Here you can risk your Gold and your life.\n\n"
        "<b>Commands:</b>\n"
        " ❍ /duel : Reply to a user to challenge them to a fight to the death. Winner takes the loser's bet!\n"
        " ❍ /gamble <amount> : Roll a 100-sided die. Roll above 50 to double your bet! Roll a 100 to win the Jackpot!"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu_main")]
    ])
    if update.callback_query:
        update.callback_query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def duel(update: Update, context: CallbackContext):
    user = update.effective_user
    message = update.effective_message
    
    if not message.reply_to_message:
        message.reply_text("⚔️ You must reply to a user's message to challenge them to a duel!")
        return
        
    target = message.reply_to_message.from_user
    if target.id == user.id:
        message.reply_text("❌ You cannot duel yourself!")
        return
    if target.is_bot:
        message.reply_text("❌ You cannot duel a bot!")
        return
        
    att_emp = get_empire(user.id)
    if att_emp['infantry'] == 0 and att_emp['cavalry'] == 0 and att_emp['archers'] == 0:
        message.reply_text("❌ You don't have an army to duel with! Use /train first.")
        return
        
    # Store request
    duel_id = f"{user.id}_{target.id}"
    PENDING_DUELS[duel_id] = {"challenger": user.id, "target": target.id, "chat_id": message.chat_id}
    
    text = (
        f"⚔️ <b>FRIENDLY WAR CHALLENGE</b> ⚔️\n\n"
        f"<b>{user.first_name}</b> has challenged <b>{target.first_name}</b> to a duel!\n\n"
        f"<i>Target must accept within 60 seconds.</i>"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Accept Duel", callback_data=f"accept_duel_{duel_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline_duel_{duel_id}")
        ]
    ])
    
    message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def duel_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    if data.startswith("accept_duel_") or data.startswith("decline_duel_"):
        parts = data.split("_")
        action = parts[0] # accept or decline
        chal_id = int(parts[2])
        target_id = int(parts[3])
        
        if user.id != target_id:
            query.answer("❌ This challenge is not for you!", show_alert=True)
            return
            
        duel_id = f"{chal_id}_{target_id}"
        if duel_id not in PENDING_DUELS:
            query.answer("❌ This challenge has expired or was already answered.", show_alert=True)
            return
            
        del PENDING_DUELS[duel_id]
        
        if action == "decline":
            query.edit_message_text(f"❌ {user.first_name} declined the duel challenge.")
            return
            
        # Accept Duel -> Start Arena Lobby
        chat_id = update.effective_chat.id
        battle_id = create_battle(chat_id, chal_id, target_id)
        
        try:
            chal_info = context.bot.get_chat(chal_id)
            chal_name = chal_info.first_name
        except Exception:
            chal_name = "Challenger"
            
        text = (
            f"🏟 <b>ARENA LOBBY OPEN</b> 🏟\n\n"
            f"⚔️ <b>{chal_name}</b> VS <b>{user.first_name}</b> ⚔️\n\n"
            f"<i>The battle will commence in 60 seconds!</i>\n"
            f"Place your bets now using the buttons below! Winners get 2x Payout!"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"Bet 500 on {chal_name}", callback_data=f"bet_500_{battle_id}_{chal_id}"),
                InlineKeyboardButton(f"Bet 500 on {user.first_name}", callback_data=f"bet_500_{battle_id}_{target_id}")
            ]
        ])
        
        msg = query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
        # Schedule resolution
        context.job_queue.run_once(
            resolve_duel_job,
            60,
            context={
                "battle_id": battle_id,
                "chat_id": chat_id,
                "msg_id": msg.message_id,
                "chal_id": chal_id,
                "target_id": target_id,
                "chal_name": chal_name,
                "target_name": user.first_name
            }
        )

    elif data.startswith("bet_500_"):
        parts = data.split("_")
        amount = 500
        battle_id = parts[2] + "_" + parts[3] + "_" + parts[4] + "_" + parts[5] # Reconstruct battle_id
        bet_on_id = int(parts[6])
        
        battle = get_battle(battle_id)
        if not battle or battle['status'] != "lobby":
            query.answer("❌ Betting is closed for this match!", show_alert=True)
            return
            
        # Check if user is one of the fighters
        if user.id == battle['player1_id'] or user.id == battle['player2_id']:
            query.answer("❌ You cannot bet on your own match!", show_alert=True)
            return
            
        # Check coins
        coins = get_coins(user.id)
        if coins < amount:
            query.answer(f"❌ Not enough coins! Need {amount}.", show_alert=True)
            return
            
        # Check if already bet
        for b in battle['bets']:
            if b['better_id'] == user.id:
                query.answer("❌ You have already placed a bet!", show_alert=True)
                return
                
        # Deduct coins and add bet
        remove_coins(user.id, amount)
        add_bet(battle_id, user.id, amount, bet_on_id)
        
        query.answer(f"✅ Bet {amount} Coins successfully!", show_alert=True)


def resolve_duel_job(context: CallbackContext):
    job_context = context.job.context
    battle_id = job_context['battle_id']
    chat_id = job_context['chat_id']
    msg_id = job_context['msg_id']
    chal_id = job_context['chal_id']
    target_id = job_context['target_id']
    chal_name = job_context['chal_name']
    target_name = job_context['target_name']
    
    battle = get_battle(battle_id)
    if not battle: return
    
    resolve_battle(battle_id)
    
    att_emp = get_empire(chal_id)
    def_emp = get_empire(target_id)
    
    attacker_won, att_power, def_power = simulate_combat(
        att_emp['infantry'], att_emp['cavalry'], att_emp['archers'],
        def_emp['infantry'], def_emp['cavalry'], def_emp['archers'],
        def_emp['town_hall_level']
    )
    
    winner_id = chal_id if attacker_won else target_id
    winner_name = chal_name if attacker_won else target_name
    loser_name = target_name if attacker_won else chal_name
    
    # Give XP to winner
    add_xp(winner_id, 1000)
    
    # Process bets
    winners_count = 0
    total_payout = 0
    for b in battle['bets']:
        if b['bet_on'] == winner_id:
            payout = b['amount'] * 2
            add_coins(b['better_id'], payout)
            winners_count += 1
            total_payout += payout
            
    text = (
        f"⚔️ <b>BATTLE RESOLVED</b> ⚔️\n\n"
        f"🏆 <b>{winner_name}</b> defeated <b>{loser_name}</b> in the Arena!\n"
        f"(Power: {att_power:.1f} vs {def_power:.1f})\n\n"
        f"✨ {winner_name} gained 1000 XP!\n\n"
        f"🎲 <b>Betting Results:</b>\n"
        f"{winners_count} spectator(s) won their bets, totaling {total_payout} Coins in payouts!"
    )
    
    try:
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)


def gamble(update: Update, context: CallbackContext):
    user = update.effective_user
    args = context.args
    
    if not args or not args[0].isdigit():
        update.effective_message.reply_text("🎲 Usage: /gamble <amount>")
        return
        
    amount = int(args[0])
    if amount <= 0:
        return
        
    coins = get_coins(user.id)
    if coins < amount:
        update.effective_message.reply_text(f"❌ Not enough coins! You have {coins}.")
        return
        
    remove_coins(user.id, amount)
    
    roll = random.randint(1, 100)
    
    if roll == 100:
        payout = amount * 50
        add_coins(user.id, payout)
        msg = f"🎰 <b>JACKPOT!!!</b> You rolled a 100!\n\nYou won <b>{payout}</b> Coins! (50x)"
    elif roll > 50:
        payout = amount * 2
        add_coins(user.id, payout)
        msg = f"🎲 You rolled a <b>{roll}</b>!\n\nYou won <b>{payout}</b> Coins! (2x)"
    else:
        msg = f"🎲 You rolled a <b>{roll}</b>...\n\nYou lost your {amount} Coins."
        
    update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


__help__ = """
*Age of Telegram: Friendly Wars & Casino*

*Commands:*
 ❍ /duel*:* Challenge a user to a friendly spar (no resource loss).
 ❍ /gamble <amount>*:* Roll a 1-100 die. >50 doubles your money. 100 gives 50x!
"""

__mod_name__ = "Aʀᴇɴᴀ"

DUEL_HANDLER = CommandHandler("duel", duel, run_async=True)
GAMBLE_HANDLER = CommandHandler("gamble", gamble, run_async=True)
DUEL_CALLBACKS = CallbackQueryHandler(duel_callback, pattern=r"^(accept_duel_|decline_duel_|bet_500_)", run_async=True)

dispatcher.add_handler(DUEL_HANDLER)
dispatcher.add_handler(GAMBLE_HANDLER)
dispatcher.add_handler(DUEL_CALLBACKS)

__handlers__ = [DUEL_HANDLER, GAMBLE_HANDLER, DUEL_CALLBACKS]
