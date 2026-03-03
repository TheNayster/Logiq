# Contributing to Logiq

---

## ⚠️ Two-Clone Rule — Read This First

This repo has **two active branches that must never mix**:

| Branch | Purpose | Your local folder |
|--------|---------|-------------------|
| `stoatmod-dashboard-link` | Python bot + FastAPI + token logic | `LogiqBot` |
| `stoatmod-website` | Static Vercel site (HTML/CSS/JS) | `LogiqSite` |

**One folder per branch. Always.**

### Why this matters

If you check out the website branch inside a folder that has bot files, those bot
folders appear as untracked. A careless `git add .` or `git add -A` will commit
`cogs/`, `database/`, `utils/` etc. into the website branch — permanently
contaminating it and breaking the Vercel deployment.

### One-time setup (Windows PowerShell)

```powershell
cd C:\Users\sephi\Documents\GitHub

# Bot clone — only tracks stoatmod-dashboard-link
git clone --branch stoatmod-dashboard-link --single-branch `
    https://github.com/TheNayster/Logiq.git LogiqBot

# Website clone — only tracks stoatmod-website
git clone --branch stoatmod-website --single-branch `
    https://github.com/TheNayster/Logiq.git LogiqSite

# Copy your secrets into the bot clone (never goes in LogiqSite)
Copy-Item Logiq\.env LogiqBot\.env

# Create a fresh venv inside LogiqBot
cd LogiqBot
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### Daily workflow

```powershell
# Bot work
cd C:\Users\sephi\Documents\GitHub\LogiqBot
git pull origin stoatmod-dashboard-link
# ... edit Python files, run bot ...
git add cogs/admin.py web/api.py          # name files explicitly
git commit -m "feat: ..."
git push origin stoatmod-dashboard-link

# Website work
cd C:\Users\sephi\Documents\GitHub\LogiqSite
git pull origin stoatmod-website
# ... edit HTML/CSS/JS ...
git add dashboard/general.html index.html  # name files explicitly
git commit -m "fix: ..."
git push origin stoatmod-website
```

### Pre-commit hook (already installed)

Both clones have a `.git/hooks/pre-commit` script that hard-blocks cross-branch
files. If you accidentally stage a website file in LogiqBot (or vice versa) the
commit will be rejected with a clear message.

### Rules

- **Never** run `git add .` or `git add -A` — always name files explicitly
- **Never** switch branches inside LogiqBot or LogiqSite
- **Never** copy bot folders (`cogs/`, `database/`, `utils/`, `web/`, etc.) into LogiqSite
- **Never** copy HTML files or `vercel.json` into LogiqBot
- The `.env` file lives only in `LogiqBot` — it is git-ignored in both clones

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Logiq.git
cd Logiq
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
pip install -r requirements.txt
pip install black flake8 isort pytest pytest-cov
```

### 4. Setup Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
```

## Code Quality Standards

### Format Code with Black

```bash
black cogs/ adapters/ utils/ database/ main.py healthcheck.py --line-length=120
```

### Sort Imports with isort

```bash
isort cogs/ adapters/ utils/ database/ main.py --line-length=120
```

### Lint with Flake8

```bash
flake8 cogs/ adapters/ utils/ database/ main.py healthcheck.py --max-line-length=120
```

### Run All Checks

```bash
# Format
black cogs/ adapters/ utils/ database/ --line-length=120

# Sort imports
isort cogs/ adapters/ utils/ database/ --line-length=120

# Lint
flake8 cogs/ adapters/ utils/ database/ --max-line-length=120 --statistics
```

## Running Tests Locally

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_adapter.py -v
```

### Run With Coverage Report

```bash
pytest tests/ --cov=adapters --cov=database --cov=utils --cov-report=html
# Open htmlcov/index.html to view coverage
```

### Run Only Unit Tests

```bash
pytest tests/ -m unit -v
```

## Git Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

```bash
# Edit files
# Run tests
pytest tests/ -v

# Format code
black cogs/ adapters/ utils/
isort cogs/ adapters/ utils/
```

### 3. Commit Changes

```bash
git add .
git commit -m "Add: [feature description]"
```

### 4. Push and Create Pull Request

```bash
git push origin feature/my-feature
```

## Pull Request Checklist

- [ ] Code follows black/isort formatting
- [ ] All tests pass locally (`pytest tests/`)
- [ ] Added tests for new functionality
- [ ] Updated documentation if needed
- [ ] No hardcoded secrets or credentials
- [ ] PR description explains the changes

## Branches

- `main` - Production-ready code (requires PR review)
- `develop` - Development branch (for integration)
- `feature/*` - Feature branches (from develop)
- `bugfix/*` - Bug fix branches (from develop)

## Commit Message Guidelines

```
type(scope): brief description

Longer explanation if needed.

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

## Questions?

Open an issue or ask in the [Stoat Community](https://stoat.chat/community).