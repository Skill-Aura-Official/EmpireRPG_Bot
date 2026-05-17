class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    API_ID = 6746892
    API_HASH = "cc634ffcf107f2b4fcb7d37ed618de99"

    DATABASE_URL = ""  # A sql database url from elephantsql.com
    MONGO_DB_URI = "mongodb+srv://SSB:TSBSSB001@ssb.jgfimti.mongodb.net/?appName=SSB"
    EVENT_LOGS = -1003928121906
    START_IMG = "https://res.cloudinary.com/dwadwpalt/image/upload/v1778876471/ChatGPT_Image_Mar_26_2026_02_10_08_AM_xhpnyg.png"

    # TSB Links
    SUPPORT_CHAT = "TSB_Council_Support"
    TSB_CHANNEL = "TSB_Council"
    TSB_CHAT = "https://t.me/+adWYXK67LZ4xYmM9"

    TOKEN = "8743383751:AAFxNkHNlV0AflFIBDNQTRBijdVEmSWGSO4"
    GEMINI_API_KEY = "AIzaSyCBiY-280_0pltlTiRvTDeX-vdDDMzpO0s"
    SIGHTENGINE_API_USER = "1812299886"
    SIGHTENGINE_API_SECRET = "M6ghzphTyqnij6z4v6dh3W2aWdJ6Hatn"

    # TSB Hierarchy
    FOUNDER = 5988157836
    GENERAL_SECRETARY = [5673931726, 8219615365, 8330843962]
    CO_FOUNDER = [5673931726, 8219615365]
    SENIOR_ADVISOR = []
    CHIEF_POLICY_MAKER = []
    MANAGER = []

    # Compatibility Aliases (Internal)
    OWNER_ID = FOUNDER
    DRAGONS = GENERAL_SECRETARY
    DEV_USERS = CO_FOUNDER
    DEMONS = SENIOR_ADVISOR
    TIGERS = CHIEF_POLICY_MAKER
    WOLVES = MANAGER

    # Optional fields
    BL_CHATS = []  # List of groups that you want blacklisted.

    ALLOW_CHATS = True
    ALLOW_EXCL = True
    DEL_CMDS = True
    INFOPIC = True
    LOAD = []
    NO_LOAD = ["tagall"]
    STRICT_GBAN = True
    TEMP_DOWNLOAD_DIRECTORY = "./"
    WORKERS = 8


class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
