# Contributing to Logiq

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