"""
Unified MongoDB-based Ranking, Economy, and Game State engine for SSB.
Uses a DEDICATED MongoDB connection separate from the main bot DB.
Optimized for high-throughput atomic updates on a 4GB VM.
"""
from datetime import date, datetime, timedelta

from cachetools import TTLCache
from pymongo import MongoClient, DESCENDING

from MythicRPG import RANKING_MONGO_URI, LOGGER, VIP_GROUP_IDS

# ==================== CONNECTION ====================
try:
    _client = MongoClient(RANKING_MONGO_URI, serverSelectionTimeoutMS=5000)
    _client.server_info()  # Force connection check
    _db = _client["ssb_rankings"]
    LOGGER.info("[RankingDB] Connected to dedicated Ranking MongoDB.")
except Exception as e:
    LOGGER.error(f"[RankingDB] Failed to connect to Ranking MongoDB: {e}")
    _db = None

# Collections
_wallets = _db["wallets"] if _db is not None else None          # user_id, coins, xp, lifetime_messages
_daily = _db["daily_activity"] if _db is not None else None      # user_id, chat_id, date, messages
_trials = _db["group_trials"] if _db is not None else None       # chat_id, premium_until, claims
_atlas_games = _db["atlas_games"] if _db is not None else None   # chat_id, game state
_atlas_stats = _db["atlas_stats"] if _db is not None else None   # user_id, chat_id, valid_words
_trivia_games = _db["trivia_games"] if _db is not None else None # chat_id, game state
_trivia_stats = _db["trivia_stats"] if _db is not None else None # user_id, chat_id, words_solved
_empires = _db["empires"] if _db is not None else None           # user_id, wood, stone, iron, food, age, town_hall_level, barracks_level
_guilds = _db["guilds"] if _db is not None else None             # guild_id, name, leader_id, members, vault, war_status
_battles = _db["battles"] if _db is not None else None           # battle_id, player1_id, player2_id, bets, expires_at

# Ensure indexes for performance
if _wallets is not None:
    _wallets.create_index("user_id", unique=True)
    _daily.create_index([("user_id", 1), ("chat_id", 1), ("date", 1)], unique=True)
    _trials.create_index("chat_id", unique=True)
    _atlas_games.create_index("chat_id", unique=True)
    _atlas_stats.create_index([("user_id", 1), ("chat_id", 1)], unique=True)
    _trivia_games.create_index("chat_id", unique=True)
    _trivia_stats.create_index([("user_id", 1), ("chat_id", 1)], unique=True)
    _empires.create_index("user_id", unique=True)
    _guilds.create_index("guild_id", unique=True)
    _battles.create_index("battle_id", unique=True)

# ==================== CACHES (Performance) ====================
_premium_cache = TTLCache(maxsize=500, ttl=60)      # 60s TTL
_wallet_cache = TTLCache(maxsize=2000, ttl=30)       # 30s TTL


# ==================== WALLET OPERATIONS ====================

def _ensure_wallet(user_id):
    if _wallets is None:
        return
    _wallets.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {"coins": 0, "xp": 0, "lifetime_messages": 0}},
        upsert=True,
    )


def get_wallet(user_id):
    if _wallets is None:
        return {"user_id": user_id, "coins": 0, "xp": 0, "lifetime_messages": 0}
    cached = _wallet_cache.get(user_id)
    if cached:
        return cached
    _ensure_wallet(user_id)
    doc = _wallets.find_one({"user_id": user_id})
    if doc:
        _wallet_cache[user_id] = doc
    return doc or {"user_id": user_id, "coins": 0, "xp": 0, "lifetime_messages": 0}


def add_coins(user_id, amount):
    if _wallets is None:
        return
    _wallets.update_one(
        {"user_id": user_id},
        {"$inc": {"coins": amount}, "$setOnInsert": {"xp": 0, "lifetime_messages": 0}},
        upsert=True,
    )
    _wallet_cache.pop(user_id, None)


def remove_coins(user_id, amount):
    if _wallets is None:
        return False
    result = _wallets.update_one(
        {"user_id": user_id, "coins": {"$gte": amount}},
        {"$inc": {"coins": -amount}},
    )
    _wallet_cache.pop(user_id, None)
    return result.modified_count > 0


def add_xp(user_id, amount):
    if _wallets is None:
        return
    _wallets.update_one(
        {"user_id": user_id},
        {"$inc": {"xp": amount}, "$setOnInsert": {"coins": 0, "lifetime_messages": 0}},
        upsert=True,
    )
    _wallet_cache.pop(user_id, None)


def get_xp(user_id):
    return get_wallet(user_id).get("xp", 0)


def get_coins(user_id):
    return get_wallet(user_id).get("coins", 0)


def increment_lifetime_messages(user_id):
    if _wallets is None:
        return 0
    result = _wallets.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"lifetime_messages": 1}, "$setOnInsert": {"coins": 0, "xp": 0}},
        upsert=True,
        return_document=True,
    )
    _wallet_cache.pop(user_id, None)
    return result.get("lifetime_messages", 0) if result else 0


def get_lifetime_messages(user_id):
    return get_wallet(user_id).get("lifetime_messages", 0)


def exchange_xp_to_coins(user_id):
    """Exchange 100,000 XP for 100 Coins. Returns True on success."""
    if _wallets is None:
        return False
    result = _wallets.update_one(
        {"user_id": user_id, "xp": {"$gte": 100000}},
        {"$inc": {"xp": -100000, "coins": 100}},
    )
    _wallet_cache.pop(user_id, None)
    return result.modified_count > 0


def get_top_users(limit=10):
    """Get top users globally by XP."""
    if _wallets is None:
        return []
    return list(_wallets.find().sort("xp", DESCENDING).limit(limit))


def claim_daily_reward(user_id):
    """
    Claims the daily reward for a user.
    Returns (success, amount, msg).
    """
    if _wallets is None:
        return False, 0, "Database unavailable."
        
    today_str = date.today().isoformat()
    
    _ensure_wallet(user_id)
    wallet = _wallets.find_one({"user_id": user_id})
    last_claim = wallet.get("last_daily_claim")
    
    if last_claim == today_str:
        return False, 0, "You have already claimed your daily reward today! Come back tomorrow."
        
    import random
    reward = random.randint(10, 50)
    
    _wallets.update_one(
        {"user_id": user_id},
        {"$inc": {"coins": reward}, "$set": {"last_daily_claim": today_str}}
    )
    _wallet_cache.pop(user_id, None)
    return True, reward, f"You claimed your daily reward of {reward} Coins!"


def get_inventory(user_id):
    """Get a user's cosmetic inventory."""
    if _wallets is None:
        return []
    wallet = get_wallet(user_id)
    return wallet.get("inventory", [])


def add_item_to_inventory(user_id, item_id):
    """Add a cosmetic item to user's inventory."""
    if _wallets is None:
        return False
    _ensure_wallet(user_id)
    result = _wallets.update_one(
        {"user_id": user_id},
        {"$addToSet": {"inventory": item_id}}
    )
    _wallet_cache.pop(user_id, None)
    return result.modified_count > 0


# ==================== DAILY ACTIVITY ====================

def increment_daily_messages(user_id, chat_id):
    if _daily is None:
        return 0
    today = date.today().isoformat()
    result = _daily.find_one_and_update(
        {"user_id": user_id, "chat_id": chat_id, "date": today},
        {"$inc": {"messages": 1}},
        upsert=True,
        return_document=True,
    )
    return result.get("messages", 0) if result else 0


def get_daily_qualifiers(chat_id, target_date, min_messages=200):
    if _daily is None:
        return []
    return list(_daily.find({
        "chat_id": chat_id,
        "date": target_date.isoformat(),
        "messages": {"$gte": min_messages},
    }))


def get_all_active_chats_on_date(target_date):
    if _daily is None:
        return []
    return _daily.distinct("chat_id", {"date": target_date.isoformat()})


# ==================== GROUP TRIAL OPERATIONS ====================

def _ensure_trial(chat_id):
    if _trials is None:
        return
    _trials.update_one(
        {"chat_id": chat_id},
        {"$setOnInsert": {
            "premium_until": None,
            "trial_1d_claimed": 0,
            "trial_3d_claimed": 0,
            "trial_7d_claimed": 0,
        }},
        upsert=True,
    )


def is_premium_active(chat_id):
    if chat_id in VIP_GROUP_IDS:
        return True
    cached = _premium_cache.get(chat_id)
    if cached is not None:
        return cached
    if _trials is None:
        _premium_cache[chat_id] = False
        return False
    trial = _trials.find_one({"chat_id": chat_id})
    if trial and trial.get("premium_until"):
        active = datetime.utcnow() < trial["premium_until"]
        _premium_cache[chat_id] = active
        return active
    _premium_cache[chat_id] = False
    return False


def activate_trial(chat_id, duration_days):
    if _trials is None:
        return False, "Database unavailable."
    _ensure_trial(chat_id)
    trial = _trials.find_one({"chat_id": chat_id})

    claim_key = f"trial_{duration_days}d_claimed"
    if trial.get(claim_key, 0) >= 3:
        return False, f"This group has exhausted all 3 {duration_days}-day trials."

    now = datetime.utcnow()
    current_until = trial.get("premium_until")
    if current_until and current_until > now:
        new_until = current_until + timedelta(days=duration_days)
    else:
        new_until = now + timedelta(days=duration_days)

    _trials.update_one(
        {"chat_id": chat_id},
        {"$inc": {claim_key: 1}, "$set": {"premium_until": new_until}},
    )
    _premium_cache.pop(chat_id, None)
    return True, f"Premium activated for {duration_days} day(s)!"


def get_trial_claims(chat_id):
    if _trials is None:
        return {"1d": 0, "3d": 0, "7d": 0}
    _ensure_trial(chat_id)
    trial = _trials.find_one({"chat_id": chat_id})
    return {
        "1d": trial.get("trial_1d_claimed", 0),
        "3d": trial.get("trial_3d_claimed", 0),
        "7d": trial.get("trial_7d_claimed", 0),
    }


def get_group_trial(chat_id):
    """Returns a dict-like trial object."""
    if _trials is None:
        return {"chat_id": chat_id, "premium_until": None}
    _ensure_trial(chat_id)
    return _trials.find_one({"chat_id": chat_id}) or {"chat_id": chat_id, "premium_until": None}


# ==================== ATLAS GAME OPERATIONS ====================

def atlas_start_game(chat_id, starting_word):
    if _atlas_games is None:
        return
    _atlas_games.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "is_active": True,
            "is_lobby": False,
            "current_word": starting_word.lower(),
            "last_letter": starting_word[-1].lower(),
            "used_words": [starting_word.lower()],
            "last_player_id": None,
            "joined_players": []
        }},
        upsert=True,
    )


def atlas_create_lobby(chat_id, starter_id):
    if _atlas_games is None:
        return
    _atlas_games.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "is_active": False,
            "is_lobby": True,
            "joined_players": [],
            "starter_id": starter_id
        }},
        upsert=True,
    )


def atlas_is_lobby(chat_id):
    if _atlas_games is None:
        return False
    game = _atlas_games.find_one({"chat_id": chat_id})
    return game is not None and game.get("is_lobby", False)


def atlas_join_lobby(chat_id, user_id, name):
    if _atlas_games is None:
        return False, "Database offline."
    game = _atlas_games.find_one({"chat_id": chat_id})
    if not game or not game.get("is_lobby"):
        return False, "No active lobby."
    
    players = game.get("joined_players", [])
    if any(p["user_id"] == user_id for p in players):
        return False, "You have already joined this lobby."
    if len(players) >= 5:
        return False, "Lobby is full (max 5 players)."
        
    _atlas_games.update_one(
        {"chat_id": chat_id},
        {"$push": {"joined_players": {"user_id": user_id, "name": name}}}
    )
    return True, len(players) + 1


def atlas_start_game_from_lobby(chat_id, starting_word):
    if _atlas_games is None:
        return False
    _atlas_games.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "is_active": True,
            "is_lobby": False,
            "current_word": starting_word.lower(),
            "last_letter": starting_word[-1].lower(),
            "used_words": [starting_word.lower()],
            "last_player_id": None,
            "current_player_idx": 0,
        }}
    )
    return True


def atlas_stop_game(chat_id):
    if _atlas_games is None:
        return
    _atlas_games.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "is_active": False,
            "is_lobby": False,
            "current_word": None,
            "last_letter": None,
            "used_words": [],
            "last_player_id": None,
            "joined_players": [],
            "starter_id": None
        }},
    )


def atlas_leave_lobby(chat_id, user_id):
    if _atlas_games is None:
        return False, 0
    game = _atlas_games.find_one({"chat_id": chat_id})
    if not game or not game.get("is_lobby"):
        return False, 0

    players = game.get("joined_players", [])
    new_players = [p for p in players if p["user_id"] != user_id]

    _atlas_games.update_one(
        {"chat_id": chat_id},
        {"$set": {"joined_players": new_players}}
    )
    return True, len(new_players)


def atlas_eliminate_player(chat_id, user_id):
    if _atlas_games is None:
        return False, [], 0, None, ""
    game = _atlas_games.find_one({"chat_id": chat_id})
    if not game or not game.get("is_active"):
        return False, [], 0, None, ""

    players = game.get("joined_players", [])
    current_player_idx = game.get("current_player_idx", 0)

    # Find index of the player to remove
    player_to_remove_idx = -1
    for i, p in enumerate(players):
        if p["user_id"] == user_id:
            player_to_remove_idx = i
            break

    if player_to_remove_idx == -1:
        # User not in game
        return False, players, current_player_idx, None, game.get("last_letter", "")

    # Remove the player
    players.pop(player_to_remove_idx)

    # Adjust current_player_idx
    if len(players) > 0:
        if player_to_remove_idx < current_player_idx:
            # Shift index left
            current_player_idx = current_player_idx - 1
        # Wrap around if index goes out of range
        if current_player_idx >= len(players):
            current_player_idx = 0
    else:
        current_player_idx = 0

    if len(players) <= 1:
        # Game over! Winner is the remaining player (or None if everyone left)
        winner = players[0] if len(players) == 1 else None
        _atlas_games.update_one(
            {"chat_id": chat_id},
            {"$set": {
                "is_active": False,
                "is_lobby": False,
                "joined_players": [],
                "current_word": None,
                "last_letter": None,
                "used_words": [],
                "last_player_id": None,
                "starter_id": None
            }}
        )
        return True, [], 0, winner, ""
    else:
        # Update game state in DB
        _atlas_games.update_one(
            {"chat_id": chat_id},
            {"$set": {
                "joined_players": players,
                "current_player_idx": current_player_idx
            }}
        )
        return False, players, current_player_idx, None, game.get("last_letter", "")


def atlas_get_game(chat_id):
    if _atlas_games is None:
        return None
    return _atlas_games.find_one({"chat_id": chat_id})


def atlas_is_active(chat_id):
    game = atlas_get_game(chat_id)
    return game is not None and game.get("is_active", False)


def atlas_submit_word(chat_id, word, user_id):
    if _atlas_games is None:
        return False, "Database unavailable."
    game = _atlas_games.find_one({"chat_id": chat_id})
    if not game or not game.get("is_active"):
        return False, "No active game in this chat."

    joined_players = game.get("joined_players", [])
    if not joined_players:
        return False, "No players joined this game."

    current_player_idx = game.get("current_player_idx", 0)
    if current_player_idx >= len(joined_players):
        current_player_idx = 0

    current_player = joined_players[current_player_idx]
    if current_player["user_id"] != user_id:
        return False, f"It is not your turn! It's {current_player['name']}'s turn."

    word_lower = word.lower().strip()

    if word_lower[0] != game["last_letter"]:
        return False, f"Word must start with '{game['last_letter'].upper()}'!"

    if word_lower in game.get("used_words", []):
        return False, f"'{word}' has already been used!"

    # Move to the next player
    next_player_idx = (current_player_idx + 1) % len(joined_players)

    _atlas_games.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "current_word": word_lower,
            "last_letter": word_lower[-1],
            "last_player_id": user_id,
            "current_player_idx": next_player_idx,
        }, "$push": {"used_words": word_lower}},
    )

    # Update player stats
    result = _atlas_stats.find_one_and_update(
        {"user_id": user_id, "chat_id": chat_id},
        {"$inc": {"valid_words": 1}},
        upsert=True,
        return_document=True,
    )
    return True, result.get("valid_words", 1)


def atlas_get_leaderboard(chat_id, limit=10):
    if _atlas_stats is None:
        return []
    return list(
        _atlas_stats.find({"chat_id": chat_id})
        .sort("valid_words", DESCENDING)
        .limit(limit)
    )


# ==================== TRIVIA GAME OPERATIONS ====================

def trivia_start_game(chat_id, word, scrambled):
    if _trivia_games is None:
        return
    _trivia_games.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "is_active": True,
            "word": word.lower(),
            "scrambled": scrambled,
            "started_at": datetime.utcnow(),
        }},
        upsert=True,
    )


def trivia_stop_game(chat_id):
    if _trivia_games is None:
        return
    _trivia_games.update_one(
        {"chat_id": chat_id},
        {"$set": {"is_active": False, "word": None, "scrambled": None}},
    )


def trivia_get_game(chat_id):
    if _trivia_games is None:
        return None
    return _trivia_games.find_one({"chat_id": chat_id})


def trivia_is_active(chat_id):
    game = trivia_get_game(chat_id)
    return game is not None and game.get("is_active", False)


def trivia_record_win(user_id, chat_id):
    if _trivia_stats is None:
        return 0
    result = _trivia_stats.find_one_and_update(
        {"user_id": user_id, "chat_id": chat_id},
        {"$inc": {"words_solved": 1}},
        upsert=True,
        return_document=True,
    )
    return result.get("words_solved", 1)


def trivia_get_leaderboard(chat_id, limit=10):
    if _trivia_stats is None:
        return []
    return list(
        _trivia_stats.find({"chat_id": chat_id})
        .sort("words_solved", DESCENDING)
        .limit(limit)
    )

# ==================== RANK & MILESTONE DEFINITIONS ====================
RANKS = [
    ("Bronze", 1000),
    ("Silver", 2000),
    ("Gold", 4000),
    ("Platinum", 8000),
    ("Diamond", 16000),
    ("Elite", 32000),
    ("Master", 64000),
    ("Elite Master", 128000),
    ("Legend", 256000),
    ("Legendary Master", 512000),
    ("Elite Legendary Master", 1024000),
]

MESSAGE_MILESTONES = {
    1000: 500,      # 1k messages = 500 XP
    10000: 2000,    # 10k messages = 2,000 XP
    25000: 5000,    # 25k messages = 5,000 XP
    50000: 10000,   # 50k messages = 10,000 XP
    75000: 15000,   # 75k messages = 15,000 XP
    100000: 25000,  # 100k messages = 25,000 XP
    250000: 50000,  # 250k messages = 50,000 XP
    500000: 75000,  # 500k messages = 75,000 XP
    750000: 100000, # 750k messages = 100,000 XP
    1000000: 150000,# 1M messages = 150,000 XP
}

DAILY_MILESTONE_XP = 200


def get_rank(xp):
    """Get the current rank name and next rank info for given XP."""
    current_rank = ("Unranked", 0)
    next_rank = RANKS[0]

    for name, threshold in RANKS:
        if xp >= threshold:
            current_rank = (name, threshold)
        else:
            break

    # Find next rank
    if current_rank[0] == "Unranked":
        next_rank = RANKS[0]
    else:
        try:
            current_index = [r[0] for r in RANKS].index(current_rank[0])
            if current_index + 1 < len(RANKS):
                next_rank = RANKS[current_index + 1]
            else:
                next_rank = None
        except ValueError:
            next_rank = RANKS[0]

    return {
        "rank_name": current_rank[0],
        "rank_threshold": current_rank[1],
        "next_rank_name": next_rank[0] if next_rank else None,
        "next_rank_threshold": next_rank[1] if next_rank else None,
        "xp": xp,
    }


def get_rank_emoji(rank_name):
    """Get emoji badge for a rank."""
    emojis = {
        "Unranked": "🔰",
        "Bronze": "🥉",
        "Silver": "🥈",
        "Gold": "🥇",
        "Platinum": "💎",
        "Diamond": "💠",
        "Elite": "⚡",
        "Master": "🔥",
        "Elite Master": "👑",
        "Legend": "🏆",
        "Legendary Master": "⭐",
        "Elite Legendary Master": "🌟",
    }
    return emojis.get(rank_name, "🎖")

def check_message_milestone(lifetime_messages):
    """Check if a lifetime message count hits a milestone. Returns XP to award or 0."""
    return MESSAGE_MILESTONES.get(lifetime_messages, 0)

# ==================== EMPIRE OPERATIONS ====================

def _ensure_empire(user_id):
    if _empires is None:
        return
    _empires.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {
            "wood": 0, "stone": 0, "iron": 0, "food": 0,
            "age": "Stone Age", "town_hall_level": 1,
            "barracks_level": 0, "infantry": 0, "cavalry": 0, "archers": 0,
            "heroes": [], "active_hero_id": None, "inventory": [],
            "assassins": 0, "watchtower_level": 0
        }},
        upsert=True,
    )

def get_empire(user_id):
    if _empires is None:
        return {"user_id": user_id, "wood": 0, "stone": 0, "iron": 0, "food": 0, "age": "Stone Age", "town_hall_level": 1, "barracks_level": 0, "infantry": 0, "cavalry": 0, "archers": 0, "heroes": [], "active_hero_id": None, "inventory": [], "assassins": 0, "watchtower_level": 0}
    _ensure_empire(user_id)
    doc = _empires.find_one({"user_id": user_id})
    return doc or {"user_id": user_id, "wood": 0, "stone": 0, "iron": 0, "food": 0, "age": "Stone Age", "town_hall_level": 1, "barracks_level": 0, "infantry": 0, "cavalry": 0, "archers": 0, "heroes": [], "active_hero_id": None, "inventory": [], "assassins": 0, "watchtower_level": 0}

def add_resources(user_id, wood=0, stone=0, iron=0, food=0):
    if _empires is None:
        return
    _ensure_empire(user_id)
    _empires.update_one(
        {"user_id": user_id},
        {"$inc": {"wood": wood, "stone": stone, "iron": iron, "food": food}}
    )

def remove_resources(user_id, wood=0, stone=0, iron=0, food=0):
    if _empires is None:
        return False
    _ensure_empire(user_id)
    result = _empires.update_one(
        {
            "user_id": user_id,
            "wood": {"$gte": wood},
            "stone": {"$gte": stone},
            "iron": {"$gte": iron},
            "food": {"$gte": food}
        },
        {"$inc": {"wood": -wood, "stone": -stone, "iron": -iron, "food": -food}}
    )
    return result.modified_count > 0

def upgrade_building(user_id, building_name):
    if _empires is None:
        return
    _ensure_empire(user_id)
    _empires.update_one(
        {"user_id": user_id},
        {"$inc": {f"{building_name}_level": 1}}
    )

def set_age(user_id, new_age):
    if _empires is None:
        return
    _ensure_empire(user_id)
    _empires.update_one(
        {"user_id": user_id},
        {"$set": {"age": new_age}}
    )


def train_troops(user_id, troop_type, amount):
    if _empires is None:
        return
    _ensure_empire(user_id)
    _empires.update_one(
        {"user_id": user_id},
        {"$inc": {troop_type: amount}}
    )


def kill_troops(user_id, infantry=0, cavalry=0, archers=0):
    if _empires is None:
        return
    _ensure_empire(user_id)
    _empires.update_one(
        {"user_id": user_id},
        {"$inc": {"infantry": -infantry, "cavalry": -cavalry, "archers": -archers}}
    )


def add_hero(user_id, hero_dict):
    if _empires is None:
        return
    _ensure_empire(user_id)
    _empires.update_one(
        {"user_id": user_id},
        {"$push": {"heroes": hero_dict}}
    )


def remove_hero(user_id, hero_id):
    if _empires is None:
        return
    _ensure_empire(user_id)
    # Remove from heroes array
    _empires.update_one(
        {"user_id": user_id},
        {"$pull": {"heroes": {"id": hero_id}}}
    )
    # If the removed hero was active, clear active_hero_id
    emp = _empires.find_one({"user_id": user_id})
    if emp and emp.get("active_hero_id") == hero_id:
        _empires.update_one({"user_id": user_id}, {"$set": {"active_hero_id": None}})


def set_active_hero(user_id, hero_id):
    if _empires is None:
        return
    _ensure_empire(user_id)
    _empires.update_one(
        {"user_id": user_id},
        {"$set": {"active_hero_id": hero_id}}
    )


def add_inventory_item(user_id, item_dict):
    if _empires is None:
        return
    _ensure_empire(user_id)
    _empires.update_one(
        {"user_id": user_id},
        {"$push": {"inventory": item_dict}}
    )


# ==================== ARENA BATTLES OPERATIONS ====================

def create_battle(chat_id, player1_id, player2_id):
    if _battles is None:
        return None
    battle_id = f"{chat_id}_{player1_id}_{player2_id}_{int(datetime.utcnow().timestamp())}"
    _battles.insert_one({
        "battle_id": battle_id,
        "chat_id": chat_id,
        "player1_id": player1_id,
        "player2_id": player2_id,
        "bets": [], # { "better_id": int, "amount": int, "bet_on": player_id }
        "status": "lobby",
        "created_at": datetime.utcnow()
    })
    return battle_id

def get_battle(battle_id):
    if _battles is None:
        return None
    return _battles.find_one({"battle_id": battle_id})
def add_bet(battle_id, better_id, amount, bet_on_id):
    if _battles is None:
        return False
    result = _battles.update_one(
        {"battle_id": battle_id},
        {"$push": {"bets": {"better_id": better_id, "amount": amount, "bet_on": bet_on_id}}}
    )
    return result.modified_count > 0

def resolve_battle(battle_id):
    if _battles is None:
        return
    _battles.update_one(
        {"battle_id": battle_id},
        {"$set": {"status": "resolved"}}
    )

# ==================== GUILD OPERATIONS ====================

def create_guild(chat_id, guild_name, leader_id):
    if _guilds is None:
        return False, "Database offline."
    
    # Check max 2 guilds per chat
    count = _guilds.count_documents({"chat_id": chat_id})
    if count >= 2:
        return False, "This group already has the maximum of 2 Guilds!"
        
    # Check if user already in a guild in this chat
    existing = _guilds.find_one({"chat_id": chat_id, "members": leader_id})
    if existing:
        return False, "You are already in a guild in this group!"
        
    guild_id = f"guild_{chat_id}_{int(datetime.utcnow().timestamp())}"
    _guilds.insert_one({
        "guild_id": guild_id,
        "chat_id": chat_id,
        "name": guild_name,
        "leader_id": leader_id,
        "co_leaders": [],
        "members": [leader_id],
        "vault": {"wood": 0, "stone": 0, "iron": 0, "food": 0, "gold": 0},
        "war_status": "peace",
        "war_points": 0,
        "war_target": None,
        "war_end_time": None,
        "war_victories": 0
    })
    return True, guild_id

def get_guild(guild_id):
    if _guilds is None: return None
    return _guilds.find_one({"guild_id": guild_id})

def get_guild_by_user(chat_id, user_id):
    if _guilds is None: return None
    return _guilds.find_one({"chat_id": chat_id, "members": user_id})

def get_guilds_by_chat(chat_id):
    if _guilds is None: return []
    return list(_guilds.find({"chat_id": chat_id}))

def join_guild(guild_id, user_id):
    if _guilds is None: return False
    res = _guilds.update_one(
        {"guild_id": guild_id},
        {"$addToSet": {"members": user_id}}
    )
    return res.modified_count > 0

def donate_vault(guild_id, wood=0, stone=0, iron=0, food=0, gold=0):
    if _guilds is None: return
    _guilds.update_one(
        {"guild_id": guild_id},
        {"$inc": {
            "vault.wood": wood,
            "vault.stone": stone,
            "vault.iron": iron,
            "vault.food": food,
            "vault.gold": gold
        }}
    )

def set_war_status(guild_id, status, target_id=None, end_time=None):
    if _guilds is None: return
    _guilds.update_one(
        {"guild_id": guild_id},
        {"$set": {
            "war_status": status,
            "war_target": target_id,
            "war_end_time": end_time,
            "war_points": 0
        }}
    )

def add_war_points(guild_id, points):
    if _guilds is None: return
    _guilds.update_one(
        {"guild_id": guild_id},
        {"$inc": {"war_points": points}}
    )

def resolve_guild_war(winner_id, loser_id):
    if _guilds is None: return
    
    loser = get_guild(loser_id)
    if not loser: return
    
    # Steal 30% of vault
    stolen = {
        "wood": int(loser["vault"]["wood"] * 0.3),
        "stone": int(loser["vault"]["stone"] * 0.3),
        "iron": int(loser["vault"]["iron"] * 0.3),
        "food": int(loser["vault"]["food"] * 0.3),
        "gold": int(loser["vault"]["gold"] * 0.3)
    }
    
    # Deduct from loser
    _guilds.update_one(
        {"guild_id": loser_id},
        {"$inc": {
            "vault.wood": -stolen["wood"],
            "vault.stone": -stolen["stone"],
            "vault.iron": -stolen["iron"],
            "vault.food": -stolen["food"],
            "vault.gold": -stolen["gold"]
        }}
    )
    
    # Add to winner
    _guilds.update_one(
        {"guild_id": winner_id},
        {"$inc": {
            "vault.wood": stolen["wood"],
            "vault.stone": stolen["stone"],
            "vault.iron": stolen["iron"],
            "vault.food": stolen["food"],
            "vault.gold": stolen["gold"],
            "war_victories": 1
        }}
    )
    
    # Reset status
    set_war_status(winner_id, "peace")
    set_war_status(loser_id, "peace")
    
    return stolen


# ==================== LEADERBOARD OPERATIONS ====================

def get_top_empires(limit=10):
    if _empires is None: return []
    # Rank by town_hall_level primarily
    return list(_empires.find().sort("town_hall_level", DESCENDING).limit(limit))

def get_top_army(limit=10):
    if _empires is None: return []
    pipeline = [
        {"$addFields": {"total_army": {"$add": ["$infantry", "$cavalry", "$archers"]}}},
        {"$sort": {"total_army": -1}},
        {"$limit": limit}
    ]
    return list(_empires.aggregate(pipeline))

def get_top_gold(limit=10):
    if _wallets is None: return []
    return list(_wallets.find().sort("coins", DESCENDING).limit(limit))

def get_top_guilds(limit=10):
    if _guilds is None: return []
    return list(_guilds.find().sort([("war_victories", DESCENDING), ("vault.gold", DESCENDING)]).limit(limit))
