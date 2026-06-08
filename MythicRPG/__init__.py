import MythicRPG.imghdr_shim
import logging
import os
import sys
import time
import json

import telegram.ext as tg
from pyrogram import Client, errors
from telethon import TelegramClient

StartTime = time.time()

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger("telethon").setLevel(logging.ERROR)
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pyrate_limiter").setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)

# if version < 3.6, stop bot.
if sys.version_info[0] < 3 or sys.version_info[1] < 6:
    LOGGER.error(
        "You MUST have a python version of at least 3.6! Multiple features depend on this. Bot quitting."
    )
    quit(1)

ENV = bool(os.environ.get("ENV", False))

if ENV:
    API_ID = int(os.environ.get("API_ID", None))
    API_HASH = os.environ.get("API_HASH", None)
    ALLOW_CHATS = os.environ.get("ALLOW_CHATS", True)
    ALLOW_EXCL = os.environ.get("ALLOW_EXCL", False)
    CASH_API_KEY = os.environ.get("CASH_API_KEY", None)
    DB_URI = os.environ.get("DATABASE_URL")
    DEL_CMDS = bool(os.environ.get("DEL_CMDS", False))
    EVENT_LOGS = os.environ.get("EVENT_LOGS", None)
    INFOPIC = bool(os.environ.get("INFOPIC", "True"))
    LOAD = os.environ.get("LOAD", "").split()
    MONGO_DB_URI = os.environ.get("MONGO_DB_URI", None)
    RANKING_MONGO_URI = os.environ.get("RANKING_MONGO_URI", "mongodb://localhost:27017/")
    NO_LOAD = os.environ.get("NO_LOAD", "").split()
    STRICT_GBAN = bool(os.environ.get("STRICT_GBAN", True))
    SUPPORT_CHAT = os.environ.get("SUPPORT_CHAT", "TSB_Council_Support")
    TEMP_DOWNLOAD_DIRECTORY = os.environ.get("TEMP_DOWNLOAD_DIRECTORY", "./")
    TOKEN = os.environ.get("TOKEN", None)
    WORKERS = int(os.environ.get("WORKERS", 8))

    try:
        VIP_GROUP_IDS = set(int(x) for x in os.environ.get("VIP_GROUP_IDS", "").split())
    except ValueError:
        VIP_GROUP_IDS = set()

    try:
        OWNER_ID = int(os.environ.get("OWNER_ID", None))
    except ValueError:
        raise Exception("Your OWNER_ID env variable is not a valid integer.")

    try:
        BL_CHATS = set(int(x) for x in os.environ.get("BL_CHATS", "").split())
    except ValueError:
        raise Exception("Your blacklisted chats list does not contain valid integers.")

    try:
        DRAGONS = set(int(x) for x in os.environ.get("DRAGONS", "").split())
        DEV_USERS = set(int(x) for x in os.environ.get("DEV_USERS", "").split())
    except ValueError:
        raise Exception("Your sudo or dev users list does not contain valid integers.")

    try:
        DEMONS = set(int(x) for x in os.environ.get("DEMONS", "").split())
    except ValueError:
        raise Exception("Your support users list does not contain valid integers.")

    try:
        TIGERS = set(int(x) for x in os.environ.get("TIGERS", "").split())
    except ValueError:
        raise Exception("Your tiger users list does not contain valid integers.")

    try:
        WOLVES = set(int(x) for x in os.environ.get("WOLVES", "").split())
    except ValueError:
        raise Exception("Your whitelisted users list does not contain valid integers.")

else:
    from MythicRPG.config import Development as Config

    API_ID = Config.API_ID
    API_HASH = Config.API_HASH
    ALLOW_CHATS = Config.ALLOW_CHATS
    ALLOW_EXCL = Config.ALLOW_EXCL
    DB_URI = Config.DATABASE_URL
    DEL_CMDS = Config.DEL_CMDS
    EVENT_LOGS = Config.EVENT_LOGS
    INFOPIC = Config.INFOPIC
    LOAD = Config.LOAD
    MONGO_DB_URI = Config.MONGO_DB_URI
    RANKING_MONGO_URI = getattr(Config, 'RANKING_MONGO_URI', 'mongodb://localhost:27017/')
    if not DB_URI:
        DB_URI = "sqlite:///tsbssb.db"
    NO_LOAD = Config.NO_LOAD
    STRICT_GBAN = Config.STRICT_GBAN
    SUPPORT_CHAT = Config.SUPPORT_CHAT
    TSB_CHANNEL = Config.TSB_CHANNEL
    TSB_CHAT = Config.TSB_CHAT
    TEMP_DOWNLOAD_DIRECTORY = Config.TEMP_DOWNLOAD_DIRECTORY
    TOKEN = Config.TOKEN
    WORKERS = Config.WORKERS
    VIP_GROUP_IDS = set(int(x) for x in Config.VIP_GROUP_IDS) if hasattr(Config, 'VIP_GROUP_IDS') else set()

    try:
        FOUNDER = int(Config.FOUNDER)
        BL_CHATS = set(int(x) for x in Config.BL_CHATS or [])
        GENERAL_SECRETARY = set(int(x) for x in Config.GENERAL_SECRETARY or [])
        CO_FOUNDER = set(int(x) for x in Config.CO_FOUNDER or [])
        SENIOR_ADVISOR = set(int(x) for x in Config.SENIOR_ADVISOR or [])
        CHIEF_POLICY_MAKER = set(int(x) for x in Config.CHIEF_POLICY_MAKER or [])
        MANAGER = set(int(x) for x in Config.MANAGER or [])
        
        # Compatibility Aliases
        OWNER_ID = FOUNDER
        DRAGONS = GENERAL_SECRETARY
        DEV_USERS = CO_FOUNDER
        DEMONS = SENIOR_ADVISOR
        TIGERS = CHIEF_POLICY_MAKER
        WOLVES = MANAGER
    except Exception as e:
        LOGGER.error(f"Error loading hierarchy: {e}")


DRAGONS.add(OWNER_ID)
DEV_USERS.add(OWNER_ID)
# TSB Dev Team: Owner automatically added via OWNER_ID above
ELEVATED_USERS_FILE = os.path.join(os.getcwd(), "MythicRPG/elevated_users.json")
if os.path.exists(ELEVATED_USERS_FILE):
    try:
        with open(ELEVATED_USERS_FILE, "r") as f:
            data = json.load(f)
            DRAGONS.update(set(data.get("sudos", [])))
            DEMONS.update(set(data.get("supports", [])))
            WOLVES.update(set(data.get("whitelists", [])))
            TIGERS.update(set(data.get("tigers", [])))
    except Exception as e:
        LOGGER.error(f"Error loading elevated users from JSON: {e}")


updater = tg.Updater(TOKEN, workers=WORKERS, use_context=True)
telethn = TelegramClient(None, API_ID, API_HASH)

pbot = Client("MythicRPG", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN, in_memory=True, sleep_threshold=10)
dispatcher = updater.dispatcher

print("[INFO]: Getting Bot Info...")
BOT_ID = dispatcher.bot.id
BOT_NAME = dispatcher.bot.first_name
BOT_USERNAME = dispatcher.bot.username

DRAGONS = list(DRAGONS) + list(DEV_USERS)
DEV_USERS = list(DEV_USERS)
WOLVES = list(WOLVES)
DEMONS = list(DEMONS)
TIGERS = list(TIGERS)

# Load at end to ensure all prev variables have been set
from MythicRPG.modules.helper_funcs.handlers import (
    CustomCommandHandler,
    CustomMessageHandler,
    CustomRegexHandler,
)

# make sure the regex handler can take extra kwargs
tg.RegexHandler = CustomRegexHandler
tg.CommandHandler = CustomCommandHandler
tg.MessageHandler = CustomMessageHandler
