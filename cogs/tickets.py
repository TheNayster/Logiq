"""
Tickets Cog — StoatMod
Support ticket system backed by Supabase.

Commands:
  !ticket-create <topic>     — Open a new ticket
  !ticket-close  <id>        — Close a ticket (creator or mod)
  !ticket-claim  <id>        — Claim a ticket (Mod)
  !ticket-list               — Your open tickets
  !ticket-all                — All server tickets (Mod)
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
import database.supabase as supa

logger = logging.getLogger(__name__)


class Tickets(AdaptedCog):
    """Support ticket system — Stoat-only, Supabase-backed"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get("modules", {}).get("tickets", {})
        self.max_open      = self.module_config.get("max_open_per_user", 3)

    async def _is_mod(self, server_id: str, user_id: str) -> bool:
        if user_id == os.getenv("BOT_OWNER_ID", ""):
            return True
        try:
            sb  = await supa.get_client()
            res = await (sb.table("server_members")
                           .select("is_mod,is_admin,is_owner")
                           .eq("server_id", server_id)
                           .eq("user_id",   user_id)
                           .maybe_single()
                           .execute())
            if res.data:
                return any([res.data.get("is_mod"),
                             res.data.get("is_admin"),
                             res.data.get("is_owner")])
        except Exception:
            pass
        return False

    # ── create ────────────────────────────────────────────────────────────────

    @app_command(name="ticket-create", description="Open a support ticket",
                 usage="!ticket-create <topic>  e.g. !ticket-create Need help with my account")
    async def ticket_create(self, interaction: Dict[str, Any], topic: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        try:
            sb = await supa.get_client()

            # Count open tickets for this user
            open_res = await (sb.table("tickets")
                                .select("id", count="exact")
                                .eq("server_id",  server_id)
                                .eq("creator_id", user_id)
                                .eq("status",     "open")
                                .execute())
            if (open_res.count or 0) >= self.max_open:
                return await self.send_embed(
                    channel_id, "Too Many Tickets",
                    f"You already have **{self.max_open}** open tickets.\n"
                    "Close one with `!ticket-close <id>` before opening another.",
                    EmbedColor.WARNING
                )

            ticket = await supa.on_ticket_open(server_id, user_id,
                                                "General Support", topic, channel_id)
            ticket_id = ticket["id"] if ticket else "?"

            embed = EmbedFactory.ticket_created(ticket_id[:8], topic)
            embed["fields"] = embed.get("fields", []) + [
                {"name": "Full ID", "value": f"`{ticket_id}`", "inline": False},
                {"name": "Close with", "value": f"`!ticket-close {ticket_id[:8]}`", "inline": False},
            ]
            await self.send_message(channel_id, embed=embed)
            logger.info(f"[ticket] created {ticket_id} by {user_id}")

        except Exception as e:
            logger.error(f"[ticket-create] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── close ─────────────────────────────────────────────────────────────────

    @app_command(name="ticket-close", description="Close a support ticket",
                 usage="!ticket-close <ticket_id>  — the ID shown when ticket was created")
    async def ticket_close(self, interaction: Dict[str, Any], ticket_id: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        try:
            sb = await supa.get_client()
            # Allow partial UUID match (first 8 chars)
            res = await (sb.table("tickets")
                           .select("id,creator_id,status,subject")
                           .eq("server_id", server_id)
                           .ilike("id", f"{ticket_id}%")
                           .limit(1)
                           .execute())

            if not res.data:
                return await self.send_embed(channel_id, "Not Found",
                                              f"No ticket found matching `{ticket_id}`.",
                                              EmbedColor.ERROR)

            ticket    = res.data[0]
            full_id   = ticket["id"]
            is_owner  = ticket["creator_id"] == user_id
            is_mod    = await self._is_mod(server_id, user_id)

            if not is_owner and not is_mod:
                return await self.send_embed(channel_id, "Permission Denied",
                                              "You can only close your own tickets.",
                                              EmbedColor.ERROR)
            if ticket["status"] != "open":
                return await self.send_embed(channel_id, "Already Closed",
                                              "That ticket is already closed.", EmbedColor.WARNING)

            await supa.on_ticket_close(full_id, user_id)
            await self.send_embed(
                channel_id, "🎫 Ticket Closed",
                f"Ticket `{full_id[:8]}` — **{ticket.get('subject','?')}** has been closed.",
                EmbedColor.SUCCESS
            )
            logger.info(f"[ticket] {full_id} closed by {user_id}")

        except Exception as e:
            logger.error(f"[ticket-close] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── claim (mod) ───────────────────────────────────────────────────────────

    @app_command(name="ticket-claim", description="Claim a ticket as the handler (Mod)",
                 usage="!ticket-claim <ticket_id>")
    async def ticket_claim(self, interaction: Dict[str, Any], ticket_id: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_mod(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Moderators** can claim tickets.", EmbedColor.ERROR)
        try:
            sb = await supa.get_client()
            res = await (sb.table("tickets")
                           .update({"claimed_by": user_id})
                           .eq("server_id", server_id)
                           .ilike("id", f"{ticket_id}%")
                           .execute())
            await self.send_embed(channel_id, "✅ Ticket Claimed",
                                   f"You are now handling ticket `{ticket_id}`.",
                                   EmbedColor.SUCCESS)
        except Exception as e:
            logger.error(f"[ticket-claim] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── list (user) ───────────────────────────────────────────────────────────

    @app_command(name="ticket-list", description="View your open tickets")
    async def ticket_list(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        try:
            sb  = await supa.get_client()
            res = await (sb.table("tickets")
                           .select("id,subject,status,created_at")
                           .eq("server_id",  server_id)
                           .eq("creator_id", user_id)
                           .order("created_at", desc=True)
                           .limit(10)
                           .execute())
            rows = res.data or []

            if not rows:
                return await self.send_embed(channel_id, "🎫 Your Tickets",
                                              "You have no tickets.", EmbedColor.INFO)

            lines = []
            for t in rows:
                icon = "🟢" if t["status"] == "open" else "🔴"
                lines.append(
                    f"{icon} `{t['id'][:8]}` — {t.get('subject','?')[:50]} "
                    f"*(created {t['created_at'][:10]})*"
                )

            await self.send_embed(channel_id, "🎫 Your Tickets",
                                   "\n".join(lines), EmbedColor.INFO)

        except Exception as e:
            logger.error(f"[ticket-list] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── all (mod) ─────────────────────────────────────────────────────────────

    @app_command(name="ticket-all", description="View all server tickets (Mod)",
                 usage="!ticket-all [open|closed|all]")
    async def ticket_all(self, interaction: Dict[str, Any], status: str = "open"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_mod(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Moderators** can view all tickets.", EmbedColor.ERROR)
        try:
            sb  = await supa.get_client()
            q   = (sb.table("tickets")
                     .select("id,creator_id,subject,status,created_at,claimed_by")
                     .eq("server_id", server_id)
                     .order("created_at", desc=True)
                     .limit(15))
            if status != "all":
                q = q.eq("status", status)
            res  = await q.execute()
            rows = res.data or []

            if not rows:
                return await self.send_embed(channel_id, f"🎫 Tickets ({status})",
                                              "No tickets found.", EmbedColor.INFO)

            lines = []
            for t in rows:
                icon    = "🟢" if t["status"] == "open" else "🔴"
                claimed = f" (claimed by <@{t['claimed_by']}>)" if t.get("claimed_by") else ""
                lines.append(
                    f"{icon} `{t['id'][:8]}` <@{t['creator_id']}> — "
                    f"{t.get('subject','?')[:40]}{claimed}"
                )

            await self.send_embed(
                channel_id, f"🎫 All Tickets ({status}) — {len(rows)} shown",
                "\n".join(lines), EmbedColor.INFO
            )

        except Exception as e:
            logger.error(f"[ticket-all] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)


async def setup(adapter, db, config):
    return Tickets(adapter, db, config)
