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

## Fase 1: Generate Clubs List

```bash
# Export data manually:
# - Clarity: Sessions by URL (last 30 days)
# - GSC: Top Queries with clicks (last 30 days)

python scripts/generate_clubs_list.py \
    --clarity exports/clarity_30d.csv \
    --gsc exports/gsc_queries_30d.csv \
    --output config/clubs.yaml

# Manual enrichment required (see clubs.yaml.example):
# 1. Verify each club is protagonist (not just mentioned as adversary)
# 2. Fill in league, country
# 3. Add domains via Google search "club name official website"
# 4. Add official_site.url and monitor_pages (structural pages only)
# 5. Add trends_keywords (club + key players from recent posts)
# 6. Remove 'score' field after validation
```

### Validate robots.txt

Before finalizing clubs.yaml, validate that all official sites allow bot access:

```bash
# Check single URL
python scripts/check_robots_txt.py https://www.flamengo.com.br

# Check all clubs in config
python scripts/check_robots_txt.py --yaml config/clubs.yaml
```

**Action items from validation:**
- **Remove sites with status ❌ BLOCKED** — they explicitly disallow monitoring
- **Manually review sites with status ⚠️ MANUAL REVIEW** — timeout/network error/parse error requires assessment before adding

**Rules:**
- 404 (no robots.txt) → allowed (default permit)
- 200 + parsed → allowed per rules
- Timeout/5xx/network error → manual review required (NOT auto-allowed)

## Fase 2.1: Validate WHOIS

Test WHOIS on real domains before enabling:

```bash
# Run LOCAL (not on server)
python scripts/test_whois_viability.py
```

**Criteria for approval:**
- ✅ All 4 test domains succeed
- ✅ No rate limiting or blocking detected
- ✅ Date formats handled (may be datetime or list)

**If approved:** Set `sources.whois.enabled: true` in config/sources.yaml

**If failed:** Leave disabled, document issue in `docs/incidents/`

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
