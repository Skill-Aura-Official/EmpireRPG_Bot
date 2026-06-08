import datetime
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher
from MythicRPG.modules.mongo import (
    create_guild, get_guild, get_guild_by_user, get_guilds_by_chat, join_guild, donate_vault, set_war_status,
    get_empire, remove_resources, get_coins, remove_coins, resolve_guild_war
)

def create_guild_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat
    args = context.args
    
    if chat.type == "private":
        update.effective_message.reply_text("❌ Guilds are group-exclusive! Create one inside a group.")
        return
        
    if not args:
        update.effective_message.reply_text("ℹ️ Usage: /createguild <Name of Guild>")
        return
        
    guild_name = " ".join(args)
    
    success, result = create_guild(chat.id, guild_name, user.id)
    if not success:
        update.effective_message.reply_text(f"❌ {result}")
    else:
        update.effective_message.reply_text(f"🏰 <b>Guild Created!</b>\n\n<b>{user.first_name}</b> has founded the guild <b>{guild_name}</b> in this group!", parse_mode=ParseMode.HTML)


def guild_info(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat
    
    guild = get_guild_by_user(chat.id, user.id)
    if not guild:
        # Check if there are guilds they can join
        guilds = get_guilds_by_chat(chat.id)
        if not guilds:
            update.effective_message.reply_text("❌ You are not in a guild, and there are no guilds in this group to join! Use /createguild <Name>")
            return
            
        text = "🏰 <b>Group Guilds</b>\nYou are not in a guild. Click below to join one!"
        buttons = []
        for g in guilds:
            buttons.append([InlineKeyboardButton(f"Join {g['name']}", callback_data=f"join_guild_{g['guild_id']}")])
        
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
        return

    # User is in a guild
    v = guild['vault']
    text = (
        f"🏰 <b>{guild['name']}</b>\n\n"
        f"👑 Leader: {guild['leader_id']}\n"
        f"👥 Members: {len(guild['members'])}\n\n"
        f"🛡️ <b>War Status:</b> {guild['war_status'].capitalize()}\n"
        f"🏆 <b>Victories:</b> {guild['war_victories']}\n\n"
        f"🏦 <b>Guild Vault:</b>\n"
        f"🪙 Gold: {v['gold']} | 🪵 Wood: {v['wood']} | 🪨 Stone: {v['stone']}\n"
        f"⚔️ Iron: {v['iron']} | 🍞 Food: {v['food']}\n"
    )
    
    buttons = [
        [InlineKeyboardButton("🏦 Donate to Vault", callback_data=f"guild_donate_{guild['guild_id']}")],
        [InlineKeyboardButton("⚔️ Declare War", callback_data=f"guild_war_{guild['guild_id']}")]
    ]
    
    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


def guild_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    chat = update.effective_chat
    data = query.data
    
    if data.startswith("join_guild_"):
        guild_id = data.replace("join_guild_", "")
        guild = get_guild(guild_id)
        if not guild:
            query.answer("Guild not found!", show_alert=True)
            return
            
        success = join_guild(guild_id, user.id)
        if success:
            query.answer(f"✅ You joined {guild['name']}!", show_alert=True)
            guild_info(update, context) # refresh
        else:
            query.answer("❌ Could not join guild.", show_alert=True)
            
    elif data.startswith("guild_donate_"):
        guild_id = data.replace("guild_donate_", "")
        text = "🏦 <b>Donate Resources</b>\nSelect what you want to donate to the Vault (100 units):"
        buttons = [
            [
                InlineKeyboardButton("🪵 Donate Wood", callback_data=f"donatesrc_{guild_id}_wood"),
                InlineKeyboardButton("🪨 Donate Stone", callback_data=f"donatesrc_{guild_id}_stone"),
            ],
            [
                InlineKeyboardButton("⚔️ Donate Iron", callback_data=f"donatesrc_{guild_id}_iron"),
                InlineKeyboardButton("🍞 Donate Food", callback_data=f"donatesrc_{guild_id}_food"),
            ],
            [
                InlineKeyboardButton("🪙 Donate Gold", callback_data=f"donatesrc_{guild_id}_gold"),
                InlineKeyboardButton("🔙 Back", callback_data="guild_back")
            ]
        ]
        query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("donatesrc_"):
        parts = data.split("_")
        guild_id = parts[1] + "_" + parts[2]
        res_type = parts[3]
        
        emp = get_empire(user.id)
        gold = get_coins(user.id)
        
        if res_type == "gold":
            if gold < 100:
                query.answer("Not enough Gold!", show_alert=True)
                return
            remove_coins(user.id, 100)
            donate_vault(guild_id, gold=100)
        else:
            if emp[res_type] < 100:
                query.answer(f"Not enough {res_type}!", show_alert=True)
                return
            remove_resources(user.id, **{res_type: 100})
            donate_vault(guild_id, **{res_type: 100})
            
        query.answer(f"✅ Donated 100 {res_type} to the Vault!", show_alert=True)
        # Update text if possible, but answer is enough to show success

    elif data.startswith("guild_war_"):
        guild_id = data.replace("guild_war_", "")
        guild = get_guild(guild_id)
        
        if guild['leader_id'] != user.id and user.id not in guild['co_leaders']:
            query.answer("❌ Only Leaders can declare war!", show_alert=True)
            return
            
        if guild['war_status'] != "peace":
            query.answer("❌ Your guild is already in a war state!", show_alert=True)
            return
            
        guilds = get_guilds_by_chat(chat.id)
        target = None
        for g in guilds:
            if g['guild_id'] != guild_id:
                target = g
                break
                
        if not target:
            query.answer("❌ There are no other guilds in this group to declare war on!", show_alert=True)
            return
            
        # Declare War (starts 24h phase)
        end_time = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        set_war_status(guild_id, "war", target_id=target['guild_id'], end_time=end_time)
        set_war_status(target['guild_id'], "war", target_id=guild_id, end_time=end_time)
        
        # Schedule Resolution
        context.job_queue.run_once(
            resolve_war_job,
            86400, # 24 hours
            context={
                "g1_id": guild_id,
                "g2_id": target['guild_id'],
                "chat_id": chat.id
            }
        )
        
        text = (
            f"🚨 <b>WAR DECLARED!</b> 🚨\n\n"
            f"<b>{guild['name']}</b> has declared war on <b>{target['name']}</b>!\n"
            f"All members of both guilds can now earn War Points by raiding each other for the next 24 hours!\n\n"
            f"<i>The winning guild will steal 30% of the loser's Vault!</i>"
        )
        query.message.reply_text(text, parse_mode=ParseMode.HTML)
        query.answer("War Declared!")

    elif data == "guild_back":
        guild_info(update, context)


def resolve_war_job(context: CallbackContext):
    job_context = context.job.context
    g1_id = job_context['g1_id']
    g2_id = job_context['g2_id']
    chat_id = job_context['chat_id']
    
    g1 = get_guild(g1_id)
    g2 = get_guild(g2_id)
    
    if not g1 or not g2: return
    
    # Compare War Points
    if g1['war_points'] > g2['war_points']:
        winner = g1
        loser = g2
    elif g2['war_points'] > g1['war_points']:
        winner = g2
        loser = g1
    else:
        # Tie
        set_war_status(g1_id, "peace")
        set_war_status(g2_id, "peace")
        context.bot.send_message(chat_id, "🏳️ <b>War Ended in a Tie!</b> Both guilds maintained their vaults.", parse_mode=ParseMode.HTML)
        return
        
    stolen = resolve_guild_war(winner['guild_id'], loser['guild_id'])
    
    text = (
        f"🏆 <b>WAR CONCLUDED!</b> 🏆\n\n"
        f"<b>{winner['name']}</b> has crushed <b>{loser['name']}</b> with {winner['war_points']} vs {loser['war_points']} War Points!\n\n"
        f"<b>Loot Secured:</b>\n"
        f"🪙 {stolen['gold']} Gold | 🪵 {stolen['wood']} Wood | 🪨 {stolen['stone']} Stone\n"
        f"⚔️ {stolen['iron']} Iron | 🍞 {stolen['food']} Food"
    )
    context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)


__help__ = """
*Age of Telegram: Guilds*

*Commands:*
 ❍ /createguild <name>*:* Start a guild in your current group (Max 2 per group).
 ❍ /guild*:* Open the guild dashboard, donate to Vault, or declare war.
"""

__mod_name__ = "Gᴜɪʟᴅꜱ"

CREATE_GUILD_HANDLER = CommandHandler("createguild", create_guild_cmd, run_async=True)
GUILD_HANDLER = CommandHandler("guild", guild_info, run_async=True)
GUILD_CALLBACKS = CallbackQueryHandler(guild_callback, pattern=r"^(join_guild_|guild_donate_|donatesrc_|guild_war_|guild_back)", run_async=True)

dispatcher.add_handler(CREATE_GUILD_HANDLER)
dispatcher.add_handler(GUILD_HANDLER)
dispatcher.add_handler(GUILD_CALLBACKS)

__handlers__ = [CREATE_GUILD_HANDLER, GUILD_HANDLER, GUILD_CALLBACKS]
