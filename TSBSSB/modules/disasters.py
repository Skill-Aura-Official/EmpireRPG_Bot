import html
import json
import os
from typing import Optional

from telegram import ParseMode, TelegramError, Update
from telegram.ext import CallbackContext, CommandHandler
from telegram.utils.helpers import mention_html

from TSBSSB import (
    DEMONS,
    DEV_USERS,
    DRAGONS,
    OWNER_ID,
    SUPPORT_CHAT,
    TIGERS,
    WOLVES,
    dispatcher,
)
from TSBSSB.modules.helper_funcs.chat_status import (
    dev_plus,
    sudo_plus,
    whitelist_plus,
)
from TSBSSB.modules.helper_funcs.extraction import extract_user
from TSBSSB.modules.log_channel import gloggable

ELEVATED_USERS_FILE = os.path.join(os.getcwd(), "TSBSSB/elevated_users.json")


def check_user_id(user_id: int, context: CallbackContext) -> Optional[str]:
    bot = context.bot
    if not user_id:
        reply = "That...is a chat! baka ka omae?"

    elif user_id == bot.id:
        reply = "This does not work that way."

    else:
        reply = None
    return reply


def load_elevated_users():
    if not os.path.exists(ELEVATED_USERS_FILE):
        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump({"sudos": [], "supports": [], "whitelists": [], "tigers": []}, outfile, indent=4)
        return {"sudos": [], "supports": [], "whitelists": [], "tigers": []}
    
    try:
        with open(ELEVATED_USERS_FILE, "r") as infile:
            return json.load(infile)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"sudos": [], "supports": [], "whitelists": [], "tigers": []}


@dev_plus
@gloggable
def addsudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    data = load_elevated_users()

    if user_id in DRAGONS:
        message.reply_text("This member is already a 🔱 General Secretary.")
        return ""

    if user_id in DEMONS:
        rt += "Promoting Senior Advisor to General Secretary."
        data["supports"].remove(user_id)
        DEMONS.remove(user_id)

    if user_id in WOLVES:
        rt += "Promoting Manager to General Secretary."
        data["whitelists"].remove(user_id)
        WOLVES.remove(user_id)

    data["sudos"].append(user_id)
    DRAGONS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt
        + "\nSuccessfully promoted {} to 🔱 General Secretary!".format(
            user_member.first_name
        )
    )

    log_message = (
        f"#SUDO\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@sudo_plus
@gloggable
def addsupport(
    update: Update,
    context: CallbackContext,
) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    data = load_elevated_users()

    if user_id in DRAGONS:
        rt += "Demoting General Secretary to Senior Advisor."
        data["sudos"].remove(user_id)
        DRAGONS.remove(user_id)

    if user_id in DEMONS:
        message.reply_text("This user is already a ⚜️ Senior Advisor.")
        return ""

    if user_id in WOLVES:
        rt += "Promoting Manager to Senior Advisor."
        data["whitelists"].remove(user_id)
        WOLVES.remove(user_id)

    data["supports"].append(user_id)
    DEMONS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + f"\n{user_member.first_name} was added as a ⚜️ Senior Advisor!"
    )

    log_message = (
        f"#SUPPORT\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@sudo_plus
@gloggable
def addwhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    data = load_elevated_users()

    if user_id in DRAGONS:
        rt += "This member is a 🔱 General Secretary — Demoting to ⚜️ Manager."
        data["sudos"].remove(user_id)
        DRAGONS.remove(user_id)

    if user_id in DEMONS:
        rt += "This user is a ⚜️ Senior Advisor — Demoting to ⚜️ Manager."
        data["supports"].remove(user_id)
        DEMONS.remove(user_id)

    if user_id in WOLVES:
        message.reply_text("This user is already a ⚜️ Manager.")
        return ""

    data["whitelists"].append(user_id)
    WOLVES.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + f"\nSuccessfully promoted {user_member.first_name} to ⚜️ Manager!"
    )

    log_message = (
        f"#WHITELIST\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@sudo_plus
@gloggable
def addtiger(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    data = load_elevated_users()

    if user_id in DRAGONS:
        rt += "This member is a 🔱 General Secretary — Demoting to ⚜️ Chief Policy Maker."
        data["sudos"].remove(user_id)
        DRAGONS.remove(user_id)

    if user_id in DEMONS:
        rt += "This user is a ⚜️ Senior Advisor — Demoting to ⚜️ Chief Policy Maker."
        data["supports"].remove(user_id)
        DEMONS.remove(user_id)

    if user_id in WOLVES:
        rt += "This user is a ⚜️ Manager — Demoting to ⚜️ Chief Policy Maker."
        data["whitelists"].remove(user_id)
        WOLVES.remove(user_id)

    if user_id in TIGERS:
        message.reply_text("This user is already a ⚜️ Chief Policy Maker.")
        return ""

    data["tigers"].append(user_id)
    TIGERS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + f"\nSuccessfully promoted {user_member.first_name} to ⚜️ Chief Policy Maker!"
    )

    log_message = (
        f"#TIGER\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@dev_plus
@gloggable
def removesudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    data = load_elevated_users()

    if user_id in DRAGONS:
        message.reply_text("Demoting this user to civilian rank.")
        DRAGONS.remove(user_id)
        data["sudos"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNSUDO\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = "<b>{}:</b>\n".format(html.escape(chat.title)) + log_message

        return log_message

    else:
        message.reply_text("This user is not a 🔱 General Secretary!")
        return ""


@sudo_plus
@gloggable
def removesupport(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    data = load_elevated_users()

    if user_id in DEMONS:
        message.reply_text("Demoting user to civilian rank.")
        DEMONS.remove(user_id)
        data["supports"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNSUPPORT\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message

    else:
        message.reply_text("This user is not a ⚜️ Senior Advisor!")
        return ""


@sudo_plus
@gloggable
def removewhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    data = load_elevated_users()

    if user_id in WOLVES:
        message.reply_text("Demoting to normal user")
        WOLVES.remove(user_id)
        data["whitelists"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNWHITELIST\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("This user is not a ⚜️ Manager!")
        return ""


@sudo_plus
@gloggable
def removetiger(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    data = load_elevated_users()

    if user_id in TIGERS:
        message.reply_text("Demoting to normal user")
        TIGERS.remove(user_id)
        data["tigers"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNTIGER\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("This user is not a ⚜️ Chief Policy Maker!")
        return ""


@whitelist_plus
def whitelistlist(update: Update, context: CallbackContext):
    reply = "<b>⚜️ TSB Managers:</b>\n"
    m = update.effective_message.reply_text(
        "<code>Gathering info..</code>", parse_mode=ParseMode.HTML
    )
    bot = context.bot
    for each_user in WOLVES:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)

            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
def tigerlist(update: Update, context: CallbackContext):
    reply = "<b>⚜️ TSB Chief Policy Makers:</b>\n"
    m = update.effective_message.reply_text(
        "<code>Gathering info..</code>", parse_mode=ParseMode.HTML
    )
    bot = context.bot
    for each_user in TIGERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
def supportlist(update: Update, context: CallbackContext):
    bot = context.bot
    m = update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML
    )
    reply = "<b>⚜️ Senior Advisors:</b>\n"
    for each_user in DEMONS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
def sudolist(update: Update, context: CallbackContext):
    bot = context.bot
    m = update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML
    )
    true_sudo = list(set(DRAGONS) - set(DEV_USERS))
    reply = "<b>⚜️ General Secretaries:</b>\n"
    for each_user in true_sudo:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
def devlist(update: Update, context: CallbackContext):
    bot = context.bot
    m = update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML
    )
    true_dev = list(set(DEV_USERS) - {OWNER_ID})
    reply = "✨ <b>TSB Co-Founders:</b>\n"
    for each_user in true_dev:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


__help__ = """
    # Special Users
    ❍ /sudolist*:* List all General Secretaries.
    ❍ /supportlist*:* List all Senior Advisors.
    ❍ /tigers*:* List all Chief Policy Makers.
    ❍ /wolves*:* List all Managers.
    ❍ /devlist*:* List all Founders.
    ❍ /addsudo*:* Add user to General Secretaries.
    ❍ /adddemon*:* Add user to Senior Advisors.
    ❍ /addtiger*:* Add user to Chief Policy Makers.
    ❍ /addwolf*:* Add user to Managers.

    # Broadcast (Owner Only)
    ❍ /broadcastall*:* Everywhere.
    ❍ /broadcastusers*:* Users only.
    ❍ /broadcastgroups*:* Groups only.

    # Group Management
    ❍ /groups*:* Export group list (.txt).
    ❍ /leave <ID>*:* Bot leaves group.
    ❍ /stats*:* Overall bot statistics.
    ❍ /ginfo <link/ID>*:* Detailed group info.

    # Access Control
    ❍ /ignore*:* Blacklist a user.
    ❍ /notice*:* Remove from blacklist.
    ❍ /ignoredlist*:* List of ignored users.
    ❍ /lockdown <on/off>*:* Toggle group additions.

    # System & Debug
    ❍ /speedtest*:* Check server speed.
    ❍ /listmodules*:* List all modules.
    ❍ /load/unload*:* Manage modules.
    ❍ /reboot/gitpull*:* Restart/Update bot.
    ❍ /debug <on/off>*:* Command logging.
    ❍ /eval/sh/py*:* Execute code/commands.
    ❍ /dbcleanup*:* Database maintenance.
    
    # Global Bans
    ❍ /gban <id> <reason>*:* Gbans the user.
    ❍ /ungban*:* Ungbans the user.
    ❍ /gbanlist*:* List of gbanned users.
    
    # Global Blue Text
    ❍ /gignoreblue <word>*:* Ignore bluetext globally.
    ❍ /ungignoreblue <word>*:* Remove from ignore list.
    
    # Heroku (Owner Only)
    ❍ /usage*:* Check dyno hours.
    ❍ /see var <var>*:* Get environment variables.
    ❍ /set var <key> <val>*:* Set environment variables.
    ❍ /del var <var>*:* Delete environment variables.
    ❍ /logs*:* Get Heroku logs.

    Visit @TSB\_Council\_Support for more information.
"""

SUDO_HANDLER = CommandHandler("addsudo", addsudo, run_async=True)
SUPPORT_HANDLER = CommandHandler(("addsupport", "adddemon"), addsupport, run_async=True)
TIGER_HANDLER = CommandHandler(("addtiger"), addtiger, run_async=True)
WHITELIST_HANDLER = CommandHandler(
    ("addwhitelist", "addwolf"), addwhitelist, run_async=True
)
UNSUDO_HANDLER = CommandHandler(("removesudo", "rmsudo"), removesudo, run_async=True)
UNSUPPORT_HANDLER = CommandHandler(
    ("removesupport", "removedemon"), removesupport, run_async=True
)
UNTIGER_HANDLER = CommandHandler(("removetiger"), removetiger, run_async=True)
UNWHITELIST_HANDLER = CommandHandler(
    ("removewhitelist", "removewolf"), removewhitelist, run_async=True
)
WHITELISTLIST_HANDLER = CommandHandler(
    ["whitelistlist", "wolves"], whitelistlist, run_async=True
)
TIGERLIST_HANDLER = CommandHandler(["tigers"], tigerlist, run_async=True)
SUPPORTLIST_HANDLER = CommandHandler("supportlist", supportlist, run_async=True)
SUDOLIST_HANDLER = CommandHandler("sudolist", sudolist, run_async=True)
DEVLIST_HANDLER = CommandHandler("devlist", devlist, run_async=True)

dispatcher.add_handler(SUDO_HANDLER)
dispatcher.add_handler(SUPPORT_HANDLER)
dispatcher.add_handler(TIGER_HANDLER)
dispatcher.add_handler(WHITELIST_HANDLER)
dispatcher.add_handler(UNSUDO_HANDLER)
dispatcher.add_handler(UNSUPPORT_HANDLER)
dispatcher.add_handler(UNTIGER_HANDLER)
dispatcher.add_handler(UNWHITELIST_HANDLER)
dispatcher.add_handler(WHITELISTLIST_HANDLER)
dispatcher.add_handler(TIGERLIST_HANDLER)
dispatcher.add_handler(SUPPORTLIST_HANDLER)
dispatcher.add_handler(SUDOLIST_HANDLER)
dispatcher.add_handler(DEVLIST_HANDLER)

__mod_name__ = "Dᴇᴠs"
__handlers__ = [
    SUDO_HANDLER,
    SUPPORT_HANDLER,
    TIGER_HANDLER,
    WHITELIST_HANDLER,
    UNSUDO_HANDLER,
    UNSUPPORT_HANDLER,
    UNTIGER_HANDLER,
    UNWHITELIST_HANDLER,
    WHITELISTLIST_HANDLER,
    TIGERLIST_HANDLER,
    SUPPORTLIST_HANDLER,
    SUDOLIST_HANDLER,
    DEVLIST_HANDLER,
]
