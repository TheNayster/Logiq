# 🤖 Logiq - Open Source Stoat.chat Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Stoat.chat](https://img.shields.io/badge/Stoat.chat-Compatible-green.svg)](https://stoat.chat)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Tests & Lint](https://github.com/yourusername/Logiq/workflows/Tests%20%26%20Lint/badge.svg)](https://github.com/yourusername/Logiq/actions)
[![codecov](https://codecov.io/gh/yourusername/Logiq/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/Logiq)

**The Open-Source Alternative to MEE6 – Now for Stoat.chat!**

A feature-rich, fully open-source Stoat bot with all the premium features you need - completely free! Built by **Programmify** and the open-source community for the privacy-focused Stoat platform.

🌟 **Star this repo** if you find it useful!

---

## 🚀 Quick Start (Stoat Edition)

### 1. Create Stoat Bot

1. Go to [Stoat Developer Portal](https://stoat.chat/developers)
2. Create a new application
3. Generate a bot token (save this!)
4. Invite bot to your server: `https://stoat.chat/invite?client_id=YOUR_CLIENT_ID`

### 2. Install Dependencies

```bash
git clone https://github.com/yourusername/Logiq.git
cd Logiq
pip install -r requirements.txt
```

### 3. Setup Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
STOAT_BOT_TOKEN=your_bot_token_from_stoat_portal
MONGODB_URI=your_mongodb_connection_string
ENVIRONMENT=development
```

### 4. Run Bot

```bash
python main.py
```

Bot will connect to Stoat and load all modules! 🎉

---

## ⚙️ Configuration

### config.yaml Structure

**Bot Settings**
```yaml
bot:
  token: "${STOAT_BOT_TOKEN}"  # Stored in .env (never commit!)
  prefix: "!"
```

**Stoat API**
```yaml
stoat:
  api_base: "https://stoat.chat/api"
  ws_url: "wss://stoat.chat/socket"
  # Or use self-hosted Stoat:
  # api_base: "https://your-stoat.com/api"
  # ws_url: "wss://your-stoat.com/socket"
```

**Database**
```yaml
database:
  mongodb_uri: "${MONGODB_URI}"
  database_name: "Logiq"
```

**Modules** (Enable/disable features)
```yaml
modules:
  verification:
    enabled: true
  moderation:
    enabled: true
  leveling:
    enabled: true
  # ... etc
```

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `STOAT_BOT_TOKEN` | Bot authentication token | ✅ Yes |
| `MONGODB_URI` | MongoDB connection string | ✅ Yes |
| `ENVIRONMENT` | dev/staging/production | ✅ Yes |
| `OPENAI_API_KEY` | OpenAI API key (AI chat) | ❌ No |
| `TWITCH_CLIENT_ID` | Twitch integration | ❌ No |
| `YOUTUBE_API_KEY` | YouTube integration | ❌ No |

**Never commit `.env` file!** Use `.gitignore`:

```bash
*.env
.env.local
.env.*.local
```

---

## 🗄️ Database Setup

### MongoDB Atlas (Recommended - Free)

1. Sign up at https://www.mongodb.com/cloud/atlas
2. Create a free M0 cluster
3. Get connection string
4. Add in `.env`:

```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/logiq?retryWrites=true&w=majority
```

### Self-Hosted MongoDB

```env
# Local
MONGODB_URI=mongodb://localhost:27017/logiq

# Remote server
MONGODB_URI=mongodb://username:password@mongo.example.com:27017/logiq
```

**Collections created automatically:**
- `users` — User XP, balance, inventory
- `guilds` — Server configuration
- `members` — Member roles, permissions
- `roles` — Role definitions
- `channels` — Channel metadata
- `moderation_actions` — Ban/kick/timeout logs
- `tickets` — Support tickets
- `giveaways` — Active giveaways

---

## 🚀 Deploy to Railway (Recommended for Stoat)

Railway.app has free tier perfect for Stoat bots!

### 1. Prepare Repository

```bash
git init
git add .
git commit -m "Initial Logiq commit"
git branch -M main
git remote add origin https://github.com/yourusername/Logiq.git
git push -u origin main
```

### 2. Deploy on Railway

1. Go to https://railway.app
2. Sign in with GitHub
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select your `Logiq` repository
5. Add **MongoDB** plugin:
   - Click **"New"** button
   - Select **"Database"** → **"MongoDB"**
   - Railway creates `${{MongoDB.MONGO_URL}}`

### 3. Configure Environment Variables

In Railway dashboard, add variables:

```
STOAT_BOT_TOKEN=your_bot_token_here
MONGODB_URI=${{MongoDB.MONGO_URL}}
ENVIRONMENT=production
OPENAI_API_KEY=sk-... (optional)
```

### 4. Deploy!

- Railway auto-deploys on git push
- Logs visible in dashboard
- Bot stays online 24/7

**Railway Free Tier Includes:**
- 500 hours/month compute
- 5GB MongoDB storage
- Enough for small-medium bots

---

## 🖥️ Self-Host Stoat (Advanced)

To run entire Stoat stack locally:

```bash
# Clone Stoat server
git clone https://github.com/StoatIO/Server.git
cd Server

# Setup MongoDB locally
docker run -d -p 27017:27017 --name stoat-mongo mongo

# Run Stoat server
npm install && npm start
```

Then update bot config:

```yaml
stoat:
  api_base: "http://localhost:3000/api"
  ws_url: "ws://localhost:3000/socket"
```

---

## 📝 Configuration Examples

### Verification Setup

```yaml
modules:
  verification:
    enabled: true
    default_method: "dm"      # Send verification link via DM
    default_type: "button"    # or "captcha"
```

Then in bot:

```
/setup-verification @Verified #welcome dm button
```

### Moderation Setup

```yaml
modules:
  moderation:
    enabled: true
    log_actions: true
    max_warnings: 3
```

### Economy Setup

```yaml
modules:
  economy:
    enabled: true
    currency_symbol: "💎"
    starting_balance: 1000
    daily_reward: 100
```

### Music (Text-Based on Stoat)

```yaml
modules:
  music:
    enabled: true
    voice_enabled: false  # Coming when Stoat adds voice API
    max_queue_size: 100
```

### AI Chat

```yaml
modules:
  ai_chat:
    enabled: true
    provider: "openai"    # or "anthropic"
    model: "gpt-3.5-turbo"
```

Add API key to `.env`:

```env
OPENAI_API_KEY=sk-your-key-here
```

---

## 🐛 Troubleshooting

### Bot Not Starting

```bash
# Check Python version
python --version  # Need 3.11+

# Check .env file
cat .env

# Check logs
tail -f logs/logiq.log
```

### MongoDB Connection Error

```bash
# Test connection
python
>>> from pymongo import MongoClient
>>> client = MongoClient("your_mongodb_uri")
>>> client.admin.command('ping')
{'ok': 1}
```

### Commands Not Showing

Commands may take up to 1 hour to sync. Force sync:

```bash
# In Stoat chat
/sync
```

### Discord Comparison

| Feature | Discord | Stoat |
|---------|---------|-------|
| Open Source | ❌ | ✅ |
| Self-Hostable | ❌ | ✅ |
| Privacy | ⚠️ | ✅ |
| Bot Support | ✅ | ✅ |
| Voice Channels | ✅ | 🔄 Coming |
| API Stability | ✅ | ✅ |

---

## 🔒 Security

### Secrets Management

**DO NOT commit:**
- `.env` file
- `config.local.yaml`
- API keys
- Bot tokens
- Database URLs

**Always use environment variables:**

```python
import os
token = os.getenv('STOAT_BOT_TOKEN')  # Read from .env
```

### Safe Deployment

1. Never hardcode secrets
2. Use Railway/hosting platform secrets
3. Rotate tokens regularly
4. Use strong MongoDB passwords
5. Enable IP whitelist on MongoDB Atlas

---

## 🤝 Contributing to Stoat Version

Want to help? Great! Here's how:

### Setup Development

```bash
# Clone and branch
git clone your-fork
cd Logiq
git checkout -b feature/my-feature

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dev dependencies
pip install -r requirements.txt
pip install pytest black flake8
```

### Development Workflow

```bash
# Make changes
# Test locally
python main.py

# Format code
black cogs/ adapters/ utils/
flake8 cogs/ adapters/ utils/

# Commit
git add .
git commit -m "Add: [feature description]"
git push origin feature/my-feature
```

### Create Pull Request

1. Push to your fork
2. Go to GitHub
3. Click "New Pull Request"
4. Describe your changes
5. Link any related issues

---

## 📚 Architecture (Stoat Adapter Pattern)

```
User Input
    ↓
[Cog - Stoat Adapter]
    ↓
[AdapterInterface]  ← Abstract layer
    ↓
[StoatAdapter]      ← Platform-specific
    ↓
[Stoat.chat API]
```

This allows:
- **Easy switching** between platforms
- **Platform agnostic** cog logic
- **Future Discord support** by adding DiscordAdapter
- **Self-hosted Stoat** with config changes only

---

## 📞 Support & Community

- **Issues**: Report bugs on GitHub
- **Discussions**: Ask questions in GitHub Discussions
- **Stoat Community**: Join [Stoat Discord](https://stoat.chat/community)
- **Email**: support@yourbot.com

---

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

**Key Points:**
- ✅ Free to use, modify, redistribute
- ✅ Open source forever
- ⚠️ No warranty included
- 📝 Keep license and credits

---

## 🙏 Credits

- **Original Concept**: Built for Stoat.chat community
- **Contributors**: See [CONTRIBUTORS.md](CONTRIBUTORS.md)
- **Libraries**: discord.py adapter patterns, aiohttp, motor, FastAPI
- **Community**: You! Help make this better 💙

---

## 🎯 Roadmap

### v1.0 (Current - Stoat Compatible)
- ✅ Full feature parity with Discord version
- ✅ Text-based music queue
- ✅ All moderation tools
- ✅ Economy system

### v1.1 (Next)
- 🔄 Stoat voice API support (when available)
- 🔄 Real-time audio playback
- 🔄 Web dashboard

### v2.0 (Future)
- 🔄 Multi-platform support (Stoat + Discord)
- 🔄 Plugin system
- 🔄 Advanced analytics

---

**Made with ❤️ for the Stoat.chat community**
