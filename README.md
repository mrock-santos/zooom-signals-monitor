# ZoOom Signals Monitor

Automated monitor for objective signals (domain registration, official site changes, search trends) from football clubs.

## Purpose

Detect factual signals before competition without depending on human sources or AI-generated narratives.

**Alert destination:** Telegram (manual review only)  
**Never integrated into:** Automated publication pipelines (BET/NEWS)

## Architecture

- **Worker:** GitHub Actions (isolated IP, daily schedule)
- **Monitors:** WHOIS, Site Hash, Google Trends (modular, failure-isolated)
- **State:** Git-committed JSON (`state/last_check.json`)
- **Alerts:** Telegram bot

## Signals Tracked

1. **WHOIS** (investigative) - new domains, registrar changes, nameserver updates
2. **Site Monitoring** (investigative) - content changes on official pages (squad, sponsors)
3. **Google Trends** (demand) - search spikes for club/player keywords

## Setup

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Configuration

- `config/clubs.yaml` - list of clubs to monitor (generated via scripts/generate_clubs_list.py)
- `config/sources.yaml` - enable/disable sources, rate limits

## Local Testing

```bash
# Dry-run (no alerts, logs only)
python main.py --dry-run

# Production run (with alerts)
# Note: Commits handled by GitHub Actions workflow
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
python main.py
```

## Deployment

GitHub Actions workflows in `.github/workflows/`:
- `daily-check.yml` - runs monitor daily at 10:00 UTC
- `cleanup-history.yml` - weekly cleanup of logs >90 days

## Spec

See `../ZooomSports/specifications/2026-08-21-signals-monitor-design.md`
