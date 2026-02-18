# Migration Guide: Discord to Stoat

## For Users 🚀

### Moving Your Server

1. **Create Stoat server**
   - Go to https://stoat.chat
   - Create new server

2. **Invite Logiq bot**
   - Get invite link from bot creator
   - Add to your Stoat server

3. **Configure modules**
   ```
   /setup-verification @Verified #general dm button
   /setup-moderation
   /setup-leveling
   ```

4. **Import members** (if needed)
   - Stoat doesn't have auto-import
   - Share invite link: `https://stoat.chat/invite?server_id=YOUR_SERVER_ID`

## For Developers 🔧

### Logiq is Stoat-Only

**Logiq v1.0+ uses the Stoat adapter exclusively.** No Discord support.

### Creating a Stoat Cog

```python
from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedColor
from database.db_manager import DatabaseManager
from typing import Dict, Any

class MyCog(AdaptedCog):
    """My custom cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)

    @app_command(name="mycommand", description="My command")
    async def mycommand(self, interaction: Dict[str, Any], arg: str):
        """My command"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")
        
        embed = {
            "title": "My Title",
            "description": f"<@{user_id}> used command with: {arg}",
            "color": EmbedColor.INFO
        }
        await self.send_message(channel_id, embed=embed)

async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return MyCog(adapter, db, config)
```

### Bot Token Format (Stoat Only)

```env
STOAT_BOT_TOKEN=your_stoat_bot_token_here
```

Get from: https://developers.stoat.chat/

## Feature Parity ✅

| Feature | Stoat | Status |
|---------|-------|--------|
| Moderation | ✅ | ✅ Working |
| Verification | ✅ | ✅ Working |
| Economy | ✅ | ✅ Working |
| Roles | ✅ | ✅ Working |
| Music Queue | ✅ | ✅ Text-based |
| Voice Chat | ❌ | 🔄 Coming |
| Tickets | ✅ | ✅ Working |
| Giveaways | ✅ | ✅ Working |

## Setup Checklist

- [ ] Create Stoat bot at https://developers.stoat.chat
- [ ] Set `STOAT_BOT_TOKEN` in `.env`
- [ ] Configure `config.yaml` 
- [ ] Test on Stoat test server
- [ ] Deploy on Railway or self-host

## Resources

- 📚 [Stoat Developer Docs](https://developers.stoat.chat/)
- 🔗 [Stoat GitHub](https://github.com/stoatchat)
- 💬 [Stoat Community](https://stoat.chat/community)

---

Questions? Join [Stoat Community](https://stoat.chat/community)!