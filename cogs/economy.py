"""
Economy Cog — StoatMod
Virtual currency: daily rewards, balance, transfers, leaderboard.

Commands (all public unless noted):
  !daily          — Claim daily reward
  !bal [user]     — Check balance  (replaces conflicted !balance)
  !balance [user] — Alias for !bal
  !give <user> <amount>  — Give currency (Admin)
  !pay <user> <amount>   — Transfer between users
  !eco-lb         — Economy leaderboard
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.converters import UserConverter
import database.supabase as supa

logger = logging.getLogger(__name__)


class Economy(AdaptedCog):
    """Economy system — Stoat-only, Supabase-backed"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get("modules", {}).get("economy", {})
        self.currency_symbol = self.module_config.get("currency_symbol", "💎")
        self.currency_name   = self.module_config.get("currency_name",   "Coins")
        self.daily_reward    = self.module_config.get("daily_reward",    100)
        self.starting_bal    = self.module_config.get("starting_balance", 1000)

    # ── helpers ────────────────────────────────────────────────────────────────

    async def _ensure_member(self, server_id: str, user_id: str) -> Dict[str, Any]:
        """Upsert member row and return it."""
        sb = await supa.get_client()
        await supa.on_account_create(user_id)
        res = await (sb.table("server_members")
                       .upsert({"server_id": server_id, "user_id": user_id,
                                "balance": self.starting_bal},
                               on_conflict="server_id,user_id")
                       .execute())
        # Fetch fresh row after upsert
        fetch = await (sb.table("server_members")
                         .select("balance,last_daily_at,display_name")
                         .eq("server_id", server_id)
                         .eq("user_id", user_id)
                         .maybe_single()
                         .execute())
        return fetch.data or {"balance": self.starting_bal}

    async def _is_admin(self, server_id: str, user_id: str) -> bool:
        if user_id == os.getenv("BOT_OWNER_ID", ""):
            return True
        try:
            sb = await supa.get_client()
            res = await (sb.table("server_members")
                           .select("is_admin,is_owner")
                           .eq("server_id", server_id)
                           .eq("user_id", user_id)
                           .maybe_single()
                           .execute())
            return bool(res.data and (res.data.get("is_admin") or res.data.get("is_owner")))
        except Exception:
            return False

    # ── daily ──────────────────────────────────────────────────────────────────

    @app_command(name="daily", description="Claim your daily reward")
    async def daily(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        try:
            member = await self._ensure_member(server_id, user_id)
            last   = member.get("last_daily_at")
            now    = datetime.now(timezone.utc)

            if last:
                last_dt = datetime.fromisoformat(last)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                if now - last_dt < timedelta(hours=20):
                    remaining = timedelta(hours=20) - (now - last_dt)
                    h, rem = divmod(int(remaining.total_seconds()), 3600)
                    m = rem // 60
                    return await self.send_embed(
                        channel_id, "⏳ Already Claimed",
                        f"Come back in **{h}h {m}m** for your next daily reward.",
                        EmbedColor.WARNING
                    )

            new_bal = member.get("balance", self.starting_bal) + self.daily_reward
            await on_balance_change_helper(server_id, user_id, self.daily_reward, new_bal, "daily")

            sb = await supa.get_client()
            await (sb.table("server_members")
                     .update({"last_daily_at": now.isoformat()})
                     .eq("server_id", server_id)
                     .eq("user_id", user_id)
                     .execute())

            embed = EmbedFactory.create(
                title="💰 Daily Reward Claimed!",
                description=f"You received **{self.currency_symbol} {self.daily_reward}**!",
                color=EmbedColor.SUCCESS,
                fields=[{"name": "New Balance", "value": f"{self.currency_symbol} {new_bal:,}", "inline": True}]
            )
            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"[daily] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── balance ────────────────────────────────────────────────────────────────

    @app_command(name="bal", description="Check your (or another user's) balance",
                 usage="!bal [user_id]")
    async def bal(self, interaction: Dict[str, Any], user_id: Optional[str] = None):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        target     = UserConverter.parse_user_id(user_id) or user_id or interaction["user_id"]

        try:
            member = await self._ensure_member(server_id, target)
            balance = member.get("balance", 0)
            embed = EmbedFactory.economy_balance(target, target, balance, self.currency_symbol)
            await self.send_message(channel_id, embed=embed)
        except Exception as e:
            logger.error(f"[bal] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    @app_command(name="balance", description="Alias for !bal", usage="!balance [user_id]")
    async def balance(self, interaction: Dict[str, Any], user_id: Optional[str] = None):
        await self.bal(interaction, user_id)

    # ── give (Admin) ───────────────────────────────────────────────────────────

    @app_command(name="give", description="Give currency to a user (Admin)",
                 usage="!give <user_id> <amount>")
    async def give(self, interaction: Dict[str, Any], user_id: str, amount: int):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        admin_id   = interaction["user_id"]
        target     = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_admin(server_id, admin_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can give currency.", EmbedColor.ERROR)
        if amount <= 0:
            return await self.send_embed(channel_id, "Invalid Amount",
                                          "Amount must be positive.", EmbedColor.ERROR)
        try:
            member  = await self._ensure_member(server_id, target)
            new_bal = member.get("balance", 0) + amount
            await on_balance_change_helper(server_id, target, amount, new_bal, "admin",
                                            f"Given by <@{admin_id}>")
            await self.send_embed(
                channel_id, "🎁 Currency Given",
                f"Gave <@{target}> **{self.currency_symbol} {amount:,}**.\nNew balance: {new_bal:,}",
                EmbedColor.SUCCESS
            )
        except Exception as e:
            logger.error(f"[give] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── pay ────────────────────────────────────────────────────────────────────

    @app_command(name="pay", description="Transfer currency to another user",
                 usage="!pay <user_id> <amount>")
    async def pay(self, interaction: Dict[str, Any], user_id: str, amount: int):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        sender_id  = interaction["user_id"]
        target     = UserConverter.parse_user_id(user_id) or user_id

        if target == sender_id:
            return await self.send_embed(channel_id, "Invalid",
                                          "You can't pay yourself.", EmbedColor.ERROR)
        if amount <= 0:
            return await self.send_embed(channel_id, "Invalid Amount",
                                          "Amount must be positive.", EmbedColor.ERROR)
        try:
            sender = await self._ensure_member(server_id, sender_id)
            if sender.get("balance", 0) < amount:
                return await self.send_embed(channel_id, "Insufficient Funds",
                                              f"You only have **{self.currency_symbol} {sender['balance']:,}**.",
                                              EmbedColor.ERROR)

            sender_bal = sender["balance"] - amount
            recip = await self._ensure_member(server_id, target)
            recip_bal  = recip.get("balance", 0) + amount

            await on_balance_change_helper(server_id, sender_id, -amount, sender_bal, "transfer",
                                            f"Paid to <@{target}>")
            await on_balance_change_helper(server_id, target, amount, recip_bal, "transfer",
                                            f"Received from <@{sender_id}>")

            await self.send_embed(
                channel_id, "💸 Transfer Complete",
                f"<@{sender_id}> → <@{target}>: **{self.currency_symbol} {amount:,}**\n"
                f"Your new balance: {self.currency_symbol} {sender_bal:,}",
                EmbedColor.SUCCESS
            )
        except Exception as e:
            logger.error(f"[pay] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── leaderboard ────────────────────────────────────────────────────────────

    @app_command(name="eco-lb", description="Economy leaderboard (top balances)",
                 usage="!eco-lb [limit]")
    async def eco_lb(self, interaction: Dict[str, Any], limit: int = 10):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        limit      = max(1, min(limit, 25))

        try:
            sb  = await supa.get_client()
            res = await sb.rpc("get_economy_leaderboard",
                                {"p_server_id": server_id, "p_limit": limit}).execute()
            rows = res.data or []
            lines = []
            medals = ["🥇", "🥈", "🥉"]
            for i, r in enumerate(rows):
                icon = medals[i] if i < 3 else f"**{i+1}.**"
                lines.append(f"{icon} <@{r['user_id']}> — {self.currency_symbol} {r['balance']:,}")

            embed = EmbedFactory.create(
                title=f"{self.currency_symbol} Economy Leaderboard",
                description="\n".join(lines) or "No data yet.",
                color=EmbedColor.ECONOMY
            )
            await self.send_message(channel_id, embed=embed)
        except Exception as e:
            logger.error(f"[eco-lb] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # leaderboard alias kept for legacy
    @app_command(name="leaderboard", description="Economy leaderboard", usage="!leaderboard")
    async def leaderboard(self, interaction: Dict[str, Any]):
        await self.eco_lb(interaction)


# module-level helper to avoid circular imports when leveling also updates balance
async def on_balance_change_helper(server_id, user_id, amount, new_bal, tx_type, desc=""):
    await supa.on_balance_change(server_id, user_id, amount, new_bal, tx_type, desc)


async def setup(adapter, db, config):
    return Economy(adapter, db, config)
