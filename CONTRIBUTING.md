# Contributing to StoatMod Website

---

## ⚠️ Two-Clone Rule — Read This First

This repo has **two active branches that must never mix**:

| Branch | Purpose | Your local folder |
|--------|---------|-------------------|
| `stoatmod-website` | Static Vercel site (HTML/CSS/JS) | `LogiqSite` |
| `stoatmod-dashboard-link` | Python bot + FastAPI + token logic | `LogiqBot` |

**This folder (LogiqSite) is for website work only.**

### What belongs here

```
index.html
setup.html
docs.html
status.html
vercel.json
dashboard/        ← HTML dashboard pages
onboarding/       ← Onboarding flow pages
```

### What must NEVER be committed here

```
cogs/             ← bot commands
adapters/         ← bot platform adapters
utils/            ← bot utilities
database/         ← bot database layer
web/              ← FastAPI server
scripts/          ← bot scripts
tests/            ← bot tests
main.py           ← bot entrypoint
.env              ← secrets
.venv/            ← Python venv
__pycache__/
```

If you see any of the above in `git status`, **do not run `git add .`**.
You are looking at leftover files from the bot. They are ignored by `.gitignore`
but you should not be editing them here. Use `LogiqBot` for all bot work.

---

## Daily Workflow

```powershell
cd C:\Users\sephi\Documents\GitHub\LogiqSite
git pull origin stoatmod-website

# Edit HTML/CSS/JS files
# Test locally:
python -m http.server 3000
# or: npx serve . --listen 3000

# Commit only website files — name them explicitly
git add dashboard/general.html index.html
git commit -m "fix: ..."
git push origin stoatmod-website
```

## Testing Locally

```powershell
# Option A — Python (no install needed)
cd C:\Users\sephi\Documents\GitHub\LogiqSite
python -m http.server 3000
# Open: http://localhost:3000

# Option B — Node serve
npx serve . --listen 3000
```

## Pre-commit Hook

A `.git/hooks/pre-commit` script is installed that hard-blocks bot files from
being committed to this branch. If you accidentally stage a bot folder, the
commit will fail with a clear message.
