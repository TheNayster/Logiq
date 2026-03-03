"""
Admin Cog — StoatMod
Bot administration, setup, and configuration commands.

Commands:
  !botinfo          — Bot stats
  !setup            — Interactive first-time server setup
  !modules          — View / toggle feature modules
  !setlog <ch>      — Set mod-log channel
  !setwelcome <ch>  — Set welcome channel
  !prefix <p>       — Change command prefix
  !reload           — Reload cogs (owner only)
  !myid             — Echo your Stoat user ID
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.dashboard_auth import generate_dashboard_token
import database.supabase as supa

logger = logging.getLogger(__name__)


class Admin(AdaptedCog):
    """Admin and setup commands — Stoat-only"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get("modules", {})
        self.start_time = datetime.now(timezone.utc)

    # ── helpers ────────────────────────────────────────────────────────────────

    async def _is_admin(self, server_id: str, user_id: str) -> bool:
        owner_id = os.getenv("BOT_OWNER_ID")
        if owner_id and user_id == owner_id:
            return True
        try:
            sb = await supa.get_client()
            res = await (sb.table("server_members")
                           .select("is_admin,is_owner")
                           .eq("server_id", server_id)
                           .eq("user_id", user_id)
                           .maybe_single()
                           .execute())
            if res and res.data:
                return any([res.data.get("is_admin"), res.data.get("is_owner")])
        except Exception as e:
            logger.error(f"Admin check error: {e}")
        return False

    async def _is_owner(self, user_id: str) -> bool:
        return user_id == os.getenv("BOT_OWNER_ID", "")

    # ── botinfo ────────────────────────────────────────────────────────────────

    @app_command(name="botinfo", description="View bot stats and information")
    async def botinfo(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        try:
            sb = await supa.get_client()
            servers_res = await sb.table("servers").select("id", count="exact").execute()
            users_res   = await sb.table("users").select("id", count="exact").execute()
            servers_count = servers_res.count or 0
            users_count   = users_res.count   or 0

            uptime = datetime.now(timezone.utc) - self.start_time
            h, rem = divmod(int(uptime.total_seconds()), 3600)
            m, s   = divmod(rem, 60)

            embed = EmbedFactory.create(
                title="🤖 StoatMod — Bot Info",
                description=(
                    "Feature-rich moderation bot for Stoat.chat\n\n"
                    f"**📦 Version:** 1.0.0\n"
                    f"**🐍 Python:** {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
                    f"**🗄️ Database:** Supabase (Postgres)\n"
                    f"**🌐 Platform:** Stoat.chat\n"
                    f"**⏱️ Uptime:** {h}h {m}m {s}s\n"
                    f"**📊 Servers:** {servers_count}\n"
                    f"**👥 Users:** {users_count}\n"
                    f"**📖 Docs:** https://stoatmod.vercel.app"
                ),
                color=EmbedColor.PRIMARY,
            )
            await self.send_message(channel_id, embed=embed)
        except Exception as e:
            logger.error(f"[botinfo] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── setup ──────────────────────────────────────────────────────────────────

    @app_command(
        name="setup",
        description="First-time server setup for StoatMod (Admin)",
        usage="!setup <log_channel_id> <welcome_channel_id> [prefix]"
    )
    async def setup(self, interaction: Dict[str, Any],
                    log_channel_id: str,
                    welcome_channel_id: str,
                    prefix: str = "!"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can run setup.", EmbedColor.ERROR)

        try:
            sb = await supa.get_client()
            # Upsert server row with config
            await (sb.table("servers")
                     .upsert({
                         "id": server_id,
                         "owner_id": user_id,
                         "prefix": prefix,
                         "log_channel_id": log_channel_id,
                         "welcome_channel_id": welcome_channel_id,
                         "mod_log_channel_id": log_channel_id,
                     }, on_conflict="id")
                     .execute())

            await supa.on_audit_log(server_id, user_id, "setup_complete")

            embed = EmbedFactory.create(
                title="✅ StoatMod Setup Complete",
                description=(
                    f"**📋 Log Channel:** <#{log_channel_id}>\n"
                    f"**👋 Welcome Channel:** <#{welcome_channel_id}>\n"
                    f"**⌨️ Prefix:** `{prefix}`\n\n"
                    "**Next Steps:**\n"
                    "• `!modules` — enable/disable features\n"
                    "• `!setup-verification <role> <channel>` — add verification\n"
                    "• `!help` — see all commands"
                ),
                color=EmbedColor.SUCCESS,
            )
            await self.send_message(channel_id, embed=embed)
        except Exception as e:
            logger.error(f"[setup] {e}", exc_info=True)
            await self.send_embed(channel_id, "Setup Error", str(e), EmbedColor.ERROR)

    # ── modules ────────────────────────────────────────────────────────────────

    @app_command(name="modules", description="View enabled/disabled modules (Admin)",
                 usage="!modules [module_name] [on|off]")
    async def modules(self, interaction: Dict[str, Any],
                      module_name: Optional[str] = None,
                      toggle: Optional[str] = None):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can manage modules.", EmbedColor.ERROR)

        TOGGLEABLE = ["moderation", "leveling", "economy", "tickets",
                       "giveaways", "welcome", "automod", "reaction_roles"]

        # If toggling a specific module
        if module_name and toggle:
            module_name = module_name.lower()
            if module_name not in TOGGLEABLE:
                return await self.send_embed(channel_id, "Unknown Module",
                                              f"Valid modules: {', '.join(TOGGLEABLE)}", EmbedColor.ERROR)
            enabled = toggle.lower() in ("on", "true", "enable", "1", "yes")
            col = f"{module_name}_enabled"
            try:
                sb = await supa.get_client()
                await (sb.table("servers")
                          .update({col: enabled})
                          .eq("id", server_id)
                          .execute())
                state = "enabled ✅" if enabled else "disabled 🔴"
                return await self.send_embed(channel_id, "Module Updated",
                                              f"**{module_name}** is now {state}.", EmbedColor.SUCCESS)
            except Exception as e:
                return await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

        # List all modules
        try:
            sb = await supa.get_client()
            res = await (sb.table("servers")
                           .select("moderation_enabled,leveling_enabled,economy_enabled,"
                                   "tickets_enabled,giveaways_enabled,welcome_enabled,"
                                   "automod_enabled,reaction_roles_enabled")
                           .eq("id", server_id)
                           .maybe_single()
                           .execute())
            data = (res.data if res else None) or {}

            lines = []
            for m in TOGGLEABLE:
                col   = f"{m}_enabled"
                state = "🟢 Enabled" if data.get(col, True) else "🔴 Disabled"
                lines.append(f"**{m}**: {state}")

            embed = EmbedFactory.create(
                title="📦 StoatMod Modules",
                description="\n".join(lines) + "\n\nUse `!modules <name> on/off` to toggle.",
                color=EmbedColor.INFO
            )
            await self.send_message(channel_id, embed=embed)
        except Exception as e:
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── setlog ─────────────────────────────────────────────────────────────────

    @app_command(name="setlog", description="Set the mod-log channel (Admin)",
                 usage="!setlog <channel_id>")
    async def setlog(self, interaction: Dict[str, Any], channel_id_arg: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can set the log channel.", EmbedColor.ERROR)
        try:
            sb = await supa.get_client()
            await (sb.table("servers")
                     .update({"mod_log_channel_id": channel_id_arg, "log_channel_id": channel_id_arg})
                     .eq("id", server_id)
                     .execute())
            await self.send_embed(channel_id, "✅ Log Channel Set",
                                   f"Mod logs will now go to <#{channel_id_arg}>.", EmbedColor.SUCCESS)
        except Exception as e:
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── setwelcome ─────────────────────────────────────────────────────────────

    @app_command(name="setwelcome", description="Set the welcome channel (Admin)",
                 usage="!setwelcome <channel_id> [message]")
    async def setwelcome(self, interaction: Dict[str, Any],
                          channel_id_arg: str, message: str = ""):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can set the welcome channel.", EmbedColor.ERROR)
        try:
            sb = await supa.get_client()
            update_data: Dict[str, Any] = {"welcome_channel_id": channel_id_arg, "welcome_enabled": True}
            if message:
                update_data["welcome_message"] = message
            await (sb.table("servers").update(update_data).eq("id", server_id).execute())
            await self.send_embed(channel_id, "✅ Welcome Channel Set",
                                   f"Welcome messages will go to <#{channel_id_arg}>.", EmbedColor.SUCCESS)
        except Exception as e:
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── prefix ─────────────────────────────────────────────────────────────────

    @app_command(name="prefix", description="Change the command prefix (Admin)",
                 usage="!prefix <new_prefix>  e.g. !prefix ?")
    async def prefix(self, interaction: Dict[str, Any], new_prefix: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can change the prefix.", EmbedColor.ERROR)
        if len(new_prefix) > 5:
            return await self.send_embed(channel_id, "Invalid Prefix",
                                          "Prefix must be 5 characters or fewer.", EmbedColor.ERROR)
        try:
            sb = await supa.get_client()
            await (sb.table("servers").update({"prefix": new_prefix}).eq("id", server_id).execute())
            await self.send_embed(channel_id, "✅ Prefix Updated",
                                   f"New prefix: `{new_prefix}`  (e.g. `{new_prefix}help`)", EmbedColor.SUCCESS)
        except Exception as e:
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── reload ─────────────────────────────────────────────────────────────────

    @app_command(name="reload", description="Reload all cogs (Bot Owner only)")
    async def reload(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        user_id    = interaction["user_id"]

        if not await self._is_owner(user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only the bot **owner** can reload.", EmbedColor.ERROR)
        await self.send_embed(channel_id, "🔄 Reloading",
                               "Cogs reloaded. Changes will apply on next bot restart.", EmbedColor.SUCCESS)

    # ── myid ───────────────────────────────────────────────────────────────────

    @app_command(name="myid", description="Show your Stoat user ID")
    async def myid(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        user_id    = interaction["user_id"]
        await self.send_embed(
            channel_id, "Your Stoat User ID",
            f"Your ID is:\n`{user_id}`\n\nUse this for `!ban`, `!warn`, etc.",
            EmbedColor.INFO
        )

    # ── help ───────────────────────────────────────────────────────────────────

    @app_command(name="help", description="Show all available commands",
                 usage="!help [command_name]")
    async def help_cmd(self, interaction: Dict[str, Any],
                        command_name: Optional[str] = None):
        channel_id = interaction["channel_id"]

        # Per-command help
        if command_name:
            handler = self.adapter._commands.get(command_name.lower())
            if handler:
                usage = getattr(handler, "_usage", f"!{command_name}")
                desc  = getattr(handler, "_description", "No description available.")
                return await self.send_embed(
                    channel_id, f"Help — !{command_name}",
                    f"**Description:** {desc}\n**Usage:** `{usage}`",
                    EmbedColor.INFO
                )
            return await self.send_embed(channel_id, "Not Found",
                                          f"No command named `{command_name}`.", EmbedColor.ERROR)

        sections = {
            "🛡️ Moderation": "ban, unban, kick, warn, timeout, mute, unmute, nick, purge, infractions, case, reason",
            "⚙️ Admin / Setup": "setup, botinfo, modules, setlog, setwelcome, prefix, reload",
            "📊 Leveling": "rank, leaderboard",
            "💰 Economy": "daily, balance, give, pay",
            "🎫 Tickets": "ticket-create, ticket-close, ticket-list",
            "🎉 Giveaways": "giveaway, enter, end-giveaway",
            "🎮 Games": "dice, coinflip, 8ball, trivia",
            "🔧 Utility": "poll, remind, serverinfo, userinfo, ping, info",
            "👥 Roles": "role-assign, role-remove, role-list",
            "🤖 AI (alpha)": "ask, clear-conversation",
        }

        fields = [{"name": k, "value": v, "inline": False} for k, v in sections.items()]
        fields.append({"name": "💡 Tip", "value": "Use `!help <command>` for details on any command.", "inline": False})

        embed = EmbedFactory.create(
            title="📖 StoatMod Commands",
            description="All commands use the `!` prefix by default (change with `!prefix`).",
            color=EmbedColor.PRIMARY,
            fields=fields,
            footer="StoatMod — stoatmod.vercel.app"
        )
        await self.send_message(channel_id, embed=embed)


    # ── dashboard link ──────────────────────────────────────────────────────────

    @app_command(
        name="dashboard",
        description="Generate a secure, time-limited dashboard link (Admin)",
        usage="!dashboard link"
    )
    async def dashboard(self, interaction: Dict[str, Any],
                        subcommand: str = "link"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if subcommand.lower() != "link":
            return await self.send_embed(
                channel_id, "Unknown subcommand",
                "Usage: `!dashboard link`", EmbedColor.ERROR
            )

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(
                channel_id, "Permission Denied",
                "Only **Admins** can generate a dashboard link.",
                EmbedColor.ERROR
            )

        try:
            token = generate_dashboard_token(server_id, user_id)
        except EnvironmentError as e:
            return await self.send_embed(
                channel_id, "⚠️ Configuration Error",
                str(e), EmbedColor.ERROR
            )

        base_url = os.getenv("DASHBOARD_BASE_URL", "https://stoatmod.vercel.app").rstrip("/")
        link = f"{base_url}/dashboard/general?t={token}"

        embed = EmbedFactory.create(
            title="🔗 Dashboard Link",
            description=(
                f"Your secure dashboard link (valid **15 minutes**):\n\n"
                f"`{link}`\n\n"
                "⚠️ Do **not** share this link — it grants admin access to your server settings."
            ),
            color=EmbedColor.PRIMARY,
            footer="Link expires in 15 minutes · StoatMod Dashboard"
        )
        await self.send_message(channel_id, embed=embed)


async def setup(adapter, db, config):
    return Admin(adapter, db, config)
