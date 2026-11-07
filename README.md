<h1 align="center">
    🏰 Age of Telegram: Empire RPG 🏰
</h1>

<p align="center">
  <img src="MythicRPG/assets/start.png" width="600">
</p>

<p align="center">
  <b>The Ultimate Empire-Building RPG Bot for Telegram Groups!</b>
</p>

<p align="center">
<a href="https://github.com/Skill-Aura-Official/EmpireRPG_Bot/stargazers"><img src="https://img.shields.io/github/stars/Skill-Aura-Official/EmpireRPG_Bot?color=FFD700&logo=github&style=for-the-badge" alt="Stars"/></a>
<a href="https://github.com/Skill-Aura-Official/EmpireRPG_Bot/blob/main/LICENSE"> <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/></a>
<a href="https://www.python.org/"> <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python" alt="Python"/></a>
</p>

---

## 🛡️ Welcome to the Age of Telegram
Age of Telegram is a fully-featured text-based RPG bot that transforms your Telegram groups into vast empires! Gather resources, train armies, summon heroes, and wage war!

### 👑 Empire Management
- **Resource Gathering**: Produce Wood, Stone, Iron, and Food over time.
- **City Building**: Upgrade your Castle, Barracks, Stables, and Archery Ranges.
- **Resource Market**: Buy and sell resources on the global market to optimize your economy.

### ⚔️ Warfare & Stealth
- **PVP Raids**: Train troops and raid other players' empires to steal their resources!
- **Stealth Assassins**: Hire assassins from the Shadows to sabotage enemy resource production.
- **Bounty Board**: Place global coin bounties on your enemies, allowing mercenaries to hunt them down.

### 🦸 Hero Tavern & Colosseum
- **Summoning**: Visit the Tavern to summon heroes of varying rarities (Common, Rare, Epic, Legendary, Mythic).
- **The Colosseum**: Watch massive automated tournaments and bet your coins on the outcomes!
- **Black Market Smuggler**: Find the hidden smuggler to buy rare heroes directly.

### 🐉 World Bosses
- **Raid Bosses**: Team up with your entire Telegram group to fight multi-phase world bosses like the Ancient Dragon or the Lich King.
- **Epic Loot**: Deal damage to earn massive rewards and exclusive titles!

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.9+
- A Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- MongoDB Database URI
- PostgreSQL Database URI

### Local Setup
```bash
# Clone the repository
git clone https://github.com/Skill-Aura-Official/EmpireRPG_Bot.git
cd EmpireRPG_Bot

# Install dependencies
pip install -r requirements.txt

# Run the bot
python -m MythicRPG
```

---

## 📸 Previews

### Ping Response
<img src="MythicRPG/assets/ping.png" width="300">

### Bot Alive Check
<img src="MythicRPG/assets/alive.png" width="300">

---

## 📜 Credits
- 💠 **[Me](https://github.com/Skill-Aura-Official)** — Lead Developer
- 🚀 **[Antigravity AI](https://github.com/google-deepmind)** — AI Co-Pilot

<p align="center">
  <b>Built for the glory of the Empire!</b>
</p>

## Source-reviewed startup limits

The checked-in module is `MythicRPG`; run from the repository root. `MythicRPG/__init__.py` selects environment configuration when `ENV` is non-empty; otherwise it imports `Development` from `MythicRPG.config`. Configure the appropriate API_ID, API_HASH, TOKEN, OWNER_ID, DATABASE_URL, MONGO_DB_URI and RANKING_MONGO_URI privately before startup. Do not reuse stored sessions, databases or credentials from another deployment. A local SQLite fallback in code does not eliminate MongoDB-dependent features.

`runtime.txt` selects Python 3.10.13; the README's broader version badge is not a tested compatibility matrix. The Dockerfile invokes requirements installation before copying the requirements/source into the image, so it is not a verified working image recipe. No Telegram, database, game action or hosted deployment was exercised. Existing credits and the MIT notice in [LICENSE](LICENSE), including TSB Council & Hunter attribution, remain unchanged.

Python syntax was inspected without importing or running modules; results do not establish dependency compatibility or authenticated runtime behavior.
