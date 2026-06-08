import html
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from MythicRPG import dispatcher

def play_menu(update: Update, context: CallbackContext):
    user = update.effective_user
    
    text = (
        f"👑 <b>Welcome to Age of Telegram, {html.escape(user.first_name)}!</b>\n\n"
        f"<i>Build your empire, train massive armies, and conquer your enemies.</i>\n\n"
        f"Select a destination from the dashboard below to manage your kingdom."
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏰 My Empire", callback_data="menu_empire"),
            InlineKeyboardButton("⚔️ Warfare & Raids", callback_data="menu_warfare"),
        ],
        [
            InlineKeyboardButton("📈 Global Market", callback_data="menu_market"),
            InlineKeyboardButton("💰 My Wallet", callback_data="menu_wallet"),
        ],
        [
            InlineKeyboardButton("🍻 The Tavern (Heroes)", callback_data="menu_tavern"),
            InlineKeyboardButton("⚒️ The Forge", callback_data="menu_forge"),
        ],
        [
            InlineKeyboardButton("🕵️ The Shadow Guild", callback_data="menu_shadow"),
            InlineKeyboardButton("🏟 The Arena", callback_data="menu_arena"),
        ],
        [
            InlineKeyboardButton("🛡️ Guilds", callback_data="menu_guilds"),
            InlineKeyboardButton("🎯 Bounty Board", callback_data="menu_bountyboard"),
        ],
        [
            InlineKeyboardButton("🏆 Leaderboards", callback_data="menu_leaderboards"),
        ],
        [
            InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main"),
            InlineKeyboardButton("❌ Close Dashboard", callback_data="menu_close"),
        ]
    ])
    
    if update.callback_query:
        update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def menu_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    user = update.effective_user

    if data == "menu_close":
        query.message.delete()
        return

    # To avoid circular imports, we import the functions here
    if data == "menu_empire":
        from MythicRPG.modules.empire import empire_status
        empire_status(update, context)
        
    elif data == "menu_warfare":
        from MythicRPG.modules.warfare import train_menu
        train_menu(update, context)
        
    elif data == "menu_market":
        from MythicRPG.modules.warfare import market
        market(update, context)
        
    elif data == "menu_wallet":
        from MythicRPG.modules.economy import wallet_command
        wallet_command(update, context)
        
    elif data == "menu_tavern":
        from MythicRPG.modules.heroes import tavern
        tavern(update, context)
        
    elif data == "menu_forge":
        from MythicRPG.modules.forge import forge_menu
        forge_menu(update, context)
        
    elif data == "menu_shadow":
        from MythicRPG.modules.stealth import assassins_menu
        assassins_menu(update, context)
        
    elif data == "menu_arena":
        from MythicRPG.modules.arena import arena_menu
        arena_menu(update, context)
        
    elif data == "menu_guilds":
        from MythicRPG.modules.guilds import guild_info
        guild_info(update, context)
        
    elif data == "menu_bountyboard":
        from MythicRPG.modules.bounty import bountyboard
        bountyboard(update, context)
        
    elif data == "menu_leaderboards":
        # Leaderboards don't have a central menu yet, just send the help string
        text = (
            "🏆 <b>Leaderboards</b>\n\n"
            "Use the following commands to check the rankings:\n"
            " ❍ /topempires: Ranks players by Empire Level\n"
            " ❍ /toparmy: Ranks players by military power\n"
            " ❍ /topgold: Ranks wealthiest players\n"
            " ❍ /topguilds: Ranks top Guilds\n\n"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu_main")]
        ])
        query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
    elif data == "menu_main":
        play_menu(update, context)


__help__ = """
*Age of Telegram: Dashboard*
 ❍ /play*:* Open the interactive dashboard to manage your empire without typing commands.
"""

__mod_name__ = "Dᴀsʜʙᴏᴀʀᴅ"

PLAY_HANDLER = CommandHandler("play", play_menu, run_async=True)
MENU_CALLBACK = CallbackQueryHandler(menu_callback, pattern=r"^menu_", run_async=True)

dispatcher.add_handler(PLAY_HANDLER)
dispatcher.add_handler(MENU_CALLBACK)

__handlers__ = [PLAY_HANDLER, MENU_CALLBACK]
