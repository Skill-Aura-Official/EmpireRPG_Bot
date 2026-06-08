"""
Economy & Premium Shop Module for SSB.
Handles the daily coin minting job, the /shop for Premium Trials,
and the /wallet command.
"""
import html
from datetime import date, timedelta, datetime

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
)

from MythicRPG import dispatcher, LOGGER, OWNER_ID, VIP_GROUP_IDS
import MythicRPG.modules.mongo as econ_sql
from MythicRPG.modules.helper_funcs.chat_status import user_admin


SHOP_ITEMS = [
    {"id": "wood_scroll", "name": "📜 Scroll of the Forest", "cost": 5000, "desc": "A magic scroll that instantly generates 5,000 Wood."},
    {"id": "stone_scroll", "name": "📜 Scroll of the Mountain", "cost": 5000, "desc": "A magic scroll that instantly generates 5,000 Stone."},
    {"id": "iron_scroll", "name": "📜 Scroll of the Mines", "cost": 7500, "desc": "A magic scroll that instantly generates 5,000 Iron."},
    {"id": "food_scroll", "name": "📜 Scroll of the Harvest", "cost": 10000, "desc": "A magic scroll that instantly generates 10,000 Food."},
    {"id": "loot_chest", "name": "🎁 Mystery Loot Chest", "cost": 15000, "desc": "A mysterious chest that can contain massive resources or rare equipment!"}
]


def wallet_command(update: Update, context: CallbackContext):
    """Show a user's wallet (coins, XP)."""
    user = update.effective_user
    if not user:
        return

    if update.effective_message.reply_to_message:
        target = update.effective_message.reply_to_message.from_user
    else:
        target = user

    coins = econ_sql.get_coins(target.id)
    xp = econ_sql.get_xp(target.id)
    lifetime = econ_sql.get_lifetime_messages(target.id)

    text = (
        f"💰 <b>Wallet — {html.escape(target.first_name)}</b>\n\n"
        f"🪙 <b>Coins:</b> {coins:,}\n"
        f"⚡ <b>XP:</b> {xp:,}\n"
        f"💬 <b>Lifetime Messages:</b> {lifetime:,}\n\n"
        f"<i>Earn coins when you send 200+ messages per day in a group.</i>"
    )

    if target.id == user.id:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Claim Daily", callback_data=f"econ_claim_{user.id}"),
             InlineKeyboardButton("🛒 Cosmetic Shop", callback_data=f"econ_items_0_{user.id}")],
            [InlineKeyboardButton("💱 Exchange XP", callback_data=f"econ_exchange_{user.id}")],
            [InlineKeyboardButton("❌ Close", callback_data="econ_close")]
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Tip 100 Coins", callback_data=f"econ_tip_100_{target.id}")],
            [InlineKeyboardButton("❌ Close", callback_data="econ_close")]
        ])

    update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


def econ_callback(update: Update, context: CallbackContext):
    """Handle economy-related callbacks from the wallet view."""
    query = update.callback_query
    user = query.from_user
    data = query.data
    chat = update.effective_chat

    if data == "econ_close":
        query.message.delete()
        return

    # Check TSB group/channel membership
    from MythicRPG.modules.helper_funcs.chat_status import check_user_membership, is_user_admin
    is_joined, missing = check_user_membership(context.bot, user.id)
    if not is_joined:
        query.answer(
            "⚠️ You must join all required TSB groups/channels to use features. Start bot in DM first!",
            show_alert=True
        )
        return

        # Removed premium shop

    elif data.startswith("econ_exchange_"):
        parts = data.split("_")
        owner_id = int(parts[2])
        if user.id != owner_id:
            query.answer("This wallet belongs to someone else!", show_alert=True)
            return

        xp = econ_sql.get_xp(user.id)
        if xp < 100000:
            query.answer(f"❌ You need at least 100,000 XP (Current: {xp:,} XP)", show_alert=True)
            return

        success = econ_sql.exchange_xp_to_coins(user.id)
        if success:
            query.answer("💱 Successfully exchanged 100,000 XP for 100 Coins!", show_alert=True)
            coins = econ_sql.get_coins(user.id)
            xp = econ_sql.get_xp(user.id)
            lifetime = econ_sql.get_lifetime_messages(user.id)

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 Claim Daily", callback_data=f"econ_claim_{user.id}"),
                 InlineKeyboardButton("🛒 Item Shop", callback_data=f"econ_items_0_{user.id}")],
                [InlineKeyboardButton("🛍️ Premium Shop", callback_data=f"econ_shop_{user.id}"),
                 InlineKeyboardButton("💱 Exchange XP", callback_data=f"econ_exchange_{user.id}")],
                [InlineKeyboardButton("❌ Close", callback_data="econ_close")]
            ])

            query.message.edit_text(
                f"💰 <b>Wallet — {html.escape(user.first_name)}</b>\n\n"
                f"🪙 <b>Coins:</b> {coins:,}\n"
                f"⚡ <b>XP:</b> {xp:,}\n"
                f"💬 <b>Lifetime Messages:</b> {lifetime:,}\n\n"
                f"<i>Earn coins when you send 200+ messages per day in a group.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
        else:
            query.answer("❌ Exchange failed.", show_alert=True)

    elif data.startswith("econ_back_"):
        parts = data.split("_")
        owner_id = int(parts[2])
        if user.id != owner_id:
            query.answer("This wallet belongs to someone else!", show_alert=True)
            return

        coins = econ_sql.get_coins(user.id)
        xp = econ_sql.get_xp(user.id)
        lifetime = econ_sql.get_lifetime_messages(user.id)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Claim Daily", callback_data=f"econ_claim_{user.id}"),
             InlineKeyboardButton("🛒 The Grand Bazaar", callback_data=f"econ_items_0_{user.id}")],
            [InlineKeyboardButton("💱 Exchange XP", callback_data=f"econ_exchange_{user.id}")],
            [InlineKeyboardButton("❌ Close", callback_data="econ_close")]
        ])

        query.message.edit_text(
            f"💰 <b>Wallet — {html.escape(user.first_name)}</b>\n\n"
            f"🪙 <b>Coins:</b> {coins:,}\n"
            f"⚡ <b>XP:</b> {xp:,}\n"
            f"💬 <b>Lifetime Messages:</b> {lifetime:,}\n\n"
            f"<i>Earn coins when you send 200+ messages per day in a group.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
    elif data.startswith("econ_claim_"):
        parts = data.split("_")
        owner_id = int(parts[2])
        if user.id != owner_id:
            query.answer("This wallet belongs to someone else!", show_alert=True)
            return
            
        success, amount, msg = econ_sql.claim_daily_reward(user.id)
        if success:
            query.answer(msg, show_alert=True)
            
            coins = econ_sql.get_coins(user.id)
            xp = econ_sql.get_xp(user.id)
            lifetime = econ_sql.get_lifetime_messages(user.id)

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 Claim Daily", callback_data=f"econ_claim_{user.id}"),
                 InlineKeyboardButton("🛒 The Grand Bazaar", callback_data=f"econ_items_0_{user.id}")],
                [InlineKeyboardButton("💱 Exchange XP", callback_data=f"econ_exchange_{user.id}")],
                [InlineKeyboardButton("❌ Close", callback_data="econ_close")]
            ])

            query.message.edit_text(
                f"💰 <b>Wallet — {html.escape(user.first_name)}</b>\n\n"
                f"🪙 <b>Coins:</b> {coins:,}\n"
                f"⚡ <b>XP:</b> {xp:,}\n"
                f"💬 <b>Lifetime Messages:</b> {lifetime:,}\n\n"
                f"<i>Earn coins when you send 200+ messages per day in a group.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
        else:
            query.answer(msg, show_alert=True)

    elif data.startswith("econ_tip_"):
        parts = data.split("_")
        amount = int(parts[2])
        target_id = int(parts[3])

        if user.id == target_id:
            query.answer("You can't tip yourself!", show_alert=True)
            return

        coins = econ_sql.get_coins(user.id)
        if coins < amount:
            query.answer(f"❌ You don't have enough coins! (Balance: {coins})", show_alert=True)
            return

        # Deduct from user, add to target
        econ_sql.remove_coins(user.id, amount)
        econ_sql.add_coins(target_id, amount)

        try:
            target_info = context.bot.get_chat(target_id)
            target_name = html.escape(target_info.first_name)
        except Exception:
            target_name = f"User {target_id}"

        query.answer(f"✅ Successfully tipped {amount} Coins to {target_name}!", show_alert=True)
        query.message.edit_text(
            f"✅ <b>Tip Sent!</b>\n\n"
            f"You successfully tipped <b>{amount} Coins</b> to {target_name}.",
            parse_mode=ParseMode.HTML
        )

    elif data.startswith("econ_items_"):
        parts = data.split("_")
        page = int(parts[2])
        owner_id = int(parts[3])
        if user.id != owner_id:
            query.answer("This wallet belongs to someone else!", show_alert=True)
            return

        total_pages = len(SHOP_ITEMS)
        if page < 0:
            page = total_pages - 1
        elif page >= total_pages:
            page = 0

        item = SHOP_ITEMS[page]
        coins = econ_sql.get_coins(user.id)
        
        text = (
            f"🛒 <b>The Grand Bazaar</b> (Page {page + 1}/{total_pages})\n\n"
            f"🪙 <b>Your Balance:</b> {coins:,} Coins\n\n"
            f"🎁 <b>Item:</b> {item['name']}\n"
            f"💰 <b>Cost:</b> {item['cost']} Coins\n"
            f"📝 <b>Description:</b> {item['desc']}\n\n"
            f"<i>Buy consumables here and use them from your /inventory!</i>"
        )

        buy_button = InlineKeyboardButton("💳 Buy Item", callback_data=f"econ_buy_{page}_{user.id}")

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬅️ Prev", callback_data=f"econ_items_{page - 1}_{user.id}"),
                buy_button,
                InlineKeyboardButton("Next ➡️", callback_data=f"econ_items_{page + 1}_{user.id}")
            ],
            [InlineKeyboardButton("🔙 Back to Wallet", callback_data=f"econ_back_{user.id}")]
        ])
        
        query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data.startswith("econ_buy_"):
        parts = data.split("_")
        page = int(parts[2])
        owner_id = int(parts[3])
        
        if user.id != owner_id:
            query.answer("This wallet belongs to someone else!", show_alert=True)
            return
            
        item = SHOP_ITEMS[page]
        coins = econ_sql.get_coins(user.id)
        
        if coins < item["cost"]:
            query.answer("❌ You don't have enough coins!", show_alert=True)
            return

        econ_sql.remove_coins(user.id, item["cost"])
        econ_sql.add_inventory_item(user.id, item["id"])
        
        query.answer(f"✅ Successfully bought {item['name']}! Use /inventory to open it.", show_alert=True)
        
        # Refresh the shop page
        coins = econ_sql.get_coins(user.id)
        total_pages = len(SHOP_ITEMS)
        
        text = (
            f"🛒 <b>The Grand Bazaar</b> (Page {page + 1}/{total_pages})\n\n"
            f"🪙 <b>Your Balance:</b> {coins:,} Coins\n\n"
            f"🎁 <b>Item:</b> {item['name']}\n"
            f"💰 <b>Cost:</b> {item['cost']} Coins\n"
            f"📝 <b>Description:</b> {item['desc']}\n\n"
            f"<i>Buy consumables here and use them from your /inventory!</i>"
        )

        buy_button = InlineKeyboardButton("💳 Buy Item", callback_data=f"econ_buy_{page}_{user.id}")

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬅️ Prev", callback_data=f"econ_items_{page - 1}_{user.id}"),
                buy_button,
                InlineKeyboardButton("Next ➡️", callback_data=f"econ_items_{page + 1}_{user.id}")
            ],
            [InlineKeyboardButton("🔙 Back to Wallet", callback_data=f"econ_back_{user.id}")]
        ])
        
        query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


# Removed unused shop commands


def claim_command(update: Update, context: CallbackContext):
    """Claim the daily reward of coins."""
    user = update.effective_user
    if not user:
        return
        
    success, amount, msg = econ_sql.claim_daily_reward(user.id)
    if success:
        coins = econ_sql.get_coins(user.id)
        update.effective_message.reply_text(
            f"🎁 <b>Daily Reward Claimed!</b>\n\n"
            f"✅ {msg}\n"
            f"💰 Total Coins: <b>{coins:,}</b>",
            parse_mode=ParseMode.HTML,
        )
    else:
        update.effective_message.reply_text(f"❌ {msg}")


def daily_coin_mint(context: CallbackContext):
    """
    Daily cron job: At 00:00 UTC, check all chats.
    For every member who sent >= 200 messages yesterday:
    - Member gets 1 coin
    - Group owner gets 1 coin
    """
    yesterday = date.today() - timedelta(days=1)
    active_chats = econ_sql.get_all_active_chats_on_date(yesterday)

    total_minted = 0
    for chat_id in active_chats:
        qualifiers = econ_sql.get_daily_qualifiers(chat_id, yesterday, min_messages=200)
        if not qualifiers:
            continue

        # Try to get the chat owner
        try:
            chat_info = context.bot.get_chat(chat_id)
            # For supergroups, we can try to get the owner from administrators
            admins = context.bot.get_chat_administrators(chat_id)
            owner_id = None
            for admin in admins:
                if admin.status == "creator":
                    owner_id = admin.user.id
                    break
        except Exception:
            continue

        for record in qualifiers:
            # Award 1 coin to the member
            econ_sql.add_coins(record.user_id, 1)
            total_minted += 1

            # Award 1 coin to the owner
            if owner_id:
                econ_sql.add_coins(owner_id, 1)
                total_minted += 1

    LOGGER.info(f"[Economy] Daily mint complete. {total_minted} coins minted for {yesterday}.")


__help__ = """
*Age of Telegram: Economy*
 ❍ /wallet*:* Check your coins, XP, and message count.
 ❍ /exchange*:* Convert 100,000 XP into 100 Coins.
 ❍ /claim*:* Claim your daily coin reward.

*How Coins Work:*
Every day, if you send 200+ messages in a group:
• You earn 1 Coin
• The group owner also earns 1 Coin
"""

__mod_name__ = "Eᴄᴏɴᴏᴍʏ"

WALLET_HANDLER = CommandHandler("wallet", wallet_command, run_async=True)
CLAIM_HANDLER = CommandHandler("claim", claim_command, run_async=True)
ECON_CALLBACK = CallbackQueryHandler(econ_callback, pattern=r"econ_", run_async=True)

dispatcher.add_handler(WALLET_HANDLER)
dispatcher.add_handler(CLAIM_HANDLER)
dispatcher.add_handler(ECON_CALLBACK)

# Schedule daily coin minting at 00:00 UTC
job_queue = dispatcher.job_queue
if job_queue:
    from datetime import time as dt_time
    job_queue.run_daily(daily_coin_mint, time=dt_time(hour=0, minute=0, second=0), name="daily_coin_mint")
    LOGGER.info("[Economy] Daily coin minting job scheduled for 00:00 UTC.")

__handlers__ = [WALLET_HANDLER, CLAIM_HANDLER, ECON_CALLBACK]

