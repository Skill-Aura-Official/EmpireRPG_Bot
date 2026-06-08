import os

file_path = "MythicRPG/modules/mongo/__init__.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

bad_chunk = """    return list(
        _trivia_stats.find({"chat_id": chat_id})
        .sort("words_solved", DESCENDING)
    ("Legendary Master", 512000),
    ("Elite Legendary Master", 1024000),
]

MESSAGE_MILESTONES = {"""

good_chunk = """    return list(
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

MESSAGE_MILESTONES = {"""

if bad_chunk in content:
    content = content.replace(bad_chunk, good_chunk)
    
bad_chunk_2 = """def get_rank_emoji(rank_name):
    \"\"\"Get emoji badge for a rank.\"\"\"
        return
    _ensure_empire(user_id)
    _empires.update_one(
        {"user_id": user_id},
        {"$inc": {f"{building_name}_level": 1}}
    )

def set_age(user_id, new_age):"""

good_chunk_2 = """def get_rank_emoji(rank_name):
    \"\"\"Get emoji badge for a rank.\"\"\"
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
    \"\"\"Check if a lifetime message count hits a milestone. Returns XP to award or 0.\"\"\"
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

def set_age(user_id, new_age):"""

if bad_chunk_2 in content:
    content = content.replace(bad_chunk_2, good_chunk_2)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done fixing mongo/__init__.py")
