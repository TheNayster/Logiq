# StoatMod — AUP & Discover Compliance

This document outlines how StoatMod complies with Stoat's
[Acceptable Use Policy](https://stoat.chat/legal/community-guidelines) and
[Discover Guidelines](https://support.revolt.chat/kb/safety/discover-guidelines).

---

## Discover Listing Requirements ✅

| Requirement | Status | Implementation |
|---|---|---|
| Enforce AUP within served servers | ✅ | `utils/compliance.py` — content filter runs on every message |
| Accurate bot description | ✅ | Profile bio describes features honestly, no false server-count claims |
| Not listed solely to promote external service | ✅ | Bot provides genuine moderation functionality |
| Respond to moderation reports | ✅ | All mod actions logged to MongoDB audit trail |
| No manipulation of Discover ranking | ✅ | No artificial inflation of any metrics |

---

## AUP Compliance ✅

### No PII Scraping
- `utils/compliance.py` → `contains_pii()` detects and blocks PII in user messages
- `utils/compliance.py` → `redact_pii()` strips PII from all log output
- AI chat (`cogs/ai_chat.py`) refuses to process messages containing PII
- Member list fetching (`fetch_guild_members`) is restricted to mod-only commands
- No automated scraping of profiles, member lists, or message history for data collection

### No Automated User-Account Activity
- Bot only acts on **explicit command invocations** by real users
- Bot ignores its own messages (`stoat_adapter.py` self-message guard)
- No user-account impersonation or masquerade abuse

### Rate Limiting (No DoS / API Abuse)
- Per-user command rate limit: **5 commands / 60 seconds** (`command_limiter`)
- Per-user message rate limit: **10 messages / 10 seconds** (`message_limiter`)
- Global API call limit: **50 calls / 10 seconds** (`api_limiter`)
- All limits defined in `utils/compliance.py` and enforced in `adapters/stoat_adapter.py`

### Content Moderation
- AUP content filter (`check_content_aup`) runs on **every incoming message**
- Blocks: hate speech, slurs, CSAM indicators, doxxing attempts, phishing patterns, self-harm promotion, mass-ping abuse
- Violations are logged (with PII redacted) and the message is rejected with a user-facing notice

### No Prohibited Content Distribution
- Bot does not generate, store, or distribute: NSFW content, extremist content, malware links, piracy links
- AI chat system prompt explicitly scopes the bot to community assistance only

### Legal Compliance
- Bot operates within Stoat's API terms — uses official WebSocket and REST endpoints only
- No circumvention of platform moderation actions
- No collection of data beyond what is necessary for bot features (minimisation principle)

---

## Bot Profile for Discover Submission

**Display Name:** StoatMod  
**Tags:** `moderation`, `automod`, `leveling`, `utility`, `stoat`, `bot`  
**Website:** https://stoatmod.vercel.app  
**Description:**
> StoatMod is a community moderation and management bot for Stoat.chat.
> Features: automated moderation, AI automod, custom commands, XP leveling,
> welcome messages, audit logs, tickets, and giveaways.
> All data handling complies with Stoat's Acceptable Use Policy.

---

## What To Do Before Submitting to Discover

1. **Rename bot** from "Test" → "StoatMod" in `stoat.chat/settings/bots`
2. **Add bot avatar** (the StoatMod logo)
3. **Add profile bio** (copy the description above)
4. **Create a support server** on Stoat and add the invite link to the bot profile
5. **Ensure bot is running** — Discover reviewers may test it
6. Click **"Submit to Discover"** in bot settings

---

*Last updated: 2026-02-23 | AUP version referenced: 2025-02-05*
