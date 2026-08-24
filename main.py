#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZoOom Signals Monitor - Main Orchestrator

Runs all enabled monitors, compares against previous state, sends Telegram
alerts and persists the new state.

Usage:
    python main.py            # full run (requires TELEGRAM_* env vars)
    python main.py --dry-run  # run monitors, log only, no alerts
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from utils.logger import setup_logger
from utils.telegram import TelegramAlert
from monitors.whois import WhoisMonitor, detect_whois_changes
from monitors.site_hash import SiteMonitor, detect_site_changes
from monitors.trends import TrendsMonitor, detect_trends_spikes


# Paths (module-level so tests can monkeypatch them)
CLUBS_CONFIG = 'config/clubs.yaml'
SOURCES_CONFIG = 'config/sources.yaml'
STATE_FILE = 'state/last_check.json'

# Delay between two different sources (seconds)
INTER_SOURCE_DELAY = 5


def load_config(path: str) -> dict:
    """Load YAML config file."""
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_state(path: str) -> dict:
    """Load previous state JSON (empty skeleton if it does not exist yet)."""
    if not os.path.exists(path):
        return {'clubs': {}}

    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_state(path: str, state: dict) -> None:
    """Save state JSON (creates parent directories)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _is_error_entry(data) -> bool:
    """True if a monitor entry represents a failed check rather than real data."""
    return isinstance(data, dict) and 'error' in data


def build_state(results: dict, previous_state: dict) -> dict:
    """
    Merge source-keyed monitor results into the club-keyed state layout.

    Monitors return {source: {club_id: {key: data}}}, but change detection
    reads state['clubs'][club_id][source][key]. This function performs that
    inversion so the next run can actually compare against this run.

    The previous state is the starting point and is only ever *overwritten*,
    never rebuilt. Baselines must survive every kind of absence:
      - monitor crashed  -> its source key is missing from `results`
      - source disabled  -> same
      - club disabled    -> club key missing from that source's results
    Losing any of those would re-emit `new_domain` for every domain on the
    next successful run.

    Two further rules:
      - an entry that failed this run ({'error': ...}) never overwrites a
        healthy previous value;
      - an error entry with no previous value is dropped entirely, because
        detect_whois_changes() treats any non-None old_data as a real record
        and would emit registrar/nameserver/updated changes instead of one
        new_domain.
    """
    previous_clubs = previous_state.get('clubs', {}) or {}
    clubs_state = copy.deepcopy(previous_clubs)

    for source, per_club in (results or {}).items():
        for club_id, entries in (per_club or {}).items():
            source_bucket = clubs_state.setdefault(club_id, {}).setdefault(source, {})

            for key, data in (entries or {}).items():
                if _is_error_entry(data):
                    continue  # keep whatever baseline exists; never store an error
                source_bucket[key] = data

    return clubs_state


def _previous(previous_state: dict, club_id: str, source: str) -> dict:
    """Read the previous entries dict for one club/source."""
    return previous_state.get('clubs', {}).get(club_id, {}).get(source, {}) or {}


def _run_whois(clubs, config, previous_state, telegram, logger, out) -> None:
    logger.info("Running WHOIS monitor...")
    monitor = WhoisMonitor(config)
    result = monitor.check(clubs)

    if not result['success']:
        out['errors'].append({'source': 'whois', 'error': result['error']})
        return

    for club in clubs:
        club_id = club['id']
        if club_id not in result['data']:
            continue

        for domain, new_data in result['data'][club_id].items():
            if _is_error_entry(new_data):
                continue

            old_data = _previous(previous_state, club_id, 'whois').get(domain)
            # A legacy/error-only baseline is not a real record: treat it as a
            # first check (one new_domain) instead of diffing against None
            # fields and emitting three bogus "changed" alerts.
            if _is_error_entry(old_data):
                old_data = None

            for change in detect_whois_changes(old_data, new_data, domain):
                logger.info("WHOIS change detected: %s - %s", club['name'], change['type'])
                if telegram:
                    msg = telegram.format_whois_alert(club['name'], change)
                    if telegram.send(msg):
                        out['alerts_sent'] += 1

    out['results']['whois'] = result['data']

    # Collect domain-level errors for observability
    if 'errors' in result and result['errors']:
        out['errors'].extend(result['errors'])


def _run_site(clubs, config, previous_state, telegram, logger, out) -> None:
    logger.info("Running Site Monitoring...")
    monitor = SiteMonitor(config)
    result = monitor.check(clubs)

    if not result['success']:
        out['errors'].append({'source': 'site_monitoring', 'error': result['error']})
        return

    for club in clubs:
        club_id = club['id']
        if club_id not in result['data']:
            continue

        for page_path, new_data in result['data'][club_id].items():
            if _is_error_entry(new_data):
                continue

            old_entry = _previous(previous_state, club_id, 'site_monitoring').get(page_path, {})
            change = detect_site_changes(old_entry.get('hash'), new_data['hash'])
            if not change:
                continue

            logger.info("Site change detected: %s - %s", club['name'], page_path)
            if telegram:
                pages = club.get('official_site', {}).get('monitor_pages', [])
                page_label = next(
                    (p['label'] for p in pages if p['path'] == page_path),
                    page_path
                )
                page_url = club.get('official_site', {}).get('url', '') + page_path
                msg = telegram.format_site_alert(club['name'], page_label, page_url, change)
                if telegram.send(msg):
                    out['alerts_sent'] += 1

    out['results']['site_monitoring'] = result['data']

    # Collect page-level errors for observability
    if 'errors' in result and result['errors']:
        out['errors'].extend(result['errors'])


def _run_trends(clubs, config, previous_state, telegram, logger, out) -> None:
    logger.info("Running Google Trends...")
    monitor = TrendsMonitor(config)
    result = monitor.check(clubs)

    if not result['success']:
        out['errors'].append({'source': 'google_trends', 'error': result['error']})
        return

    for spike in detect_trends_spikes(result['data']):
        club = next((c for c in clubs if c['id'] == spike['club_id']), None)
        if not club:
            continue

        logger.info("Trends spike detected: %s - %s", club['name'], spike['keyword'])
        if telegram:
            msg = telegram.format_trends_alert(club['name'], spike['keyword'], spike['data'])
            if telegram.send(msg):
                out['alerts_sent'] += 1

    out['results']['google_trends'] = result['data']


# (source key, config key, runner)
_SOURCES = (
    ('whois', 'whois', _run_whois),
    ('site_monitoring', 'site_monitoring', _run_site),
    ('google_trends', 'google_trends', _run_trends),
)


def run_monitors(clubs: list, sources_config: dict, previous_state: dict,
                 telegram: TelegramAlert | None, logger) -> dict:
    """
    Run all enabled monitors, isolated from each other.

    A crash in one monitor is logged and recorded in 'errors' but never stops
    the remaining monitors.

    Returns:
        {'results': {source: data}, 'errors': [...], 'alerts_sent': int,
         'sources_enabled': int}
    """
    out = {'results': {}, 'errors': [], 'alerts_sent': 0, 'sources_enabled': 0}
    sources = sources_config.get('sources', {}) or {}
    ran_any = False

    for name, config_key, runner in _SOURCES:
        config = sources.get(config_key, {}) or {}
        if not config.get('enabled', False):
            continue

        out['sources_enabled'] += 1

        # Delay only between sources that actually run
        if ran_any:
            time.sleep(INTER_SOURCE_DELAY)
        ran_any = True

        try:
            runner(clubs, config, previous_state, telegram, logger, out)
        except Exception as e:
            logger.error("%s monitor crashed: %s", name, e, exc_info=True)
            out['errors'].append({'source': name, 'error': str(e), 'critical': True})

    return out


def main():
    parser = argparse.ArgumentParser(description='ZoOom Signals Monitor')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run monitors but do not send Telegram alerts')
    args = parser.parse_args()

    logger = setup_logger()

    if args.dry_run:
        logger.info("DRY RUN MODE - no alerts will be sent")

    # Load configs
    try:
        clubs_data = load_config(CLUBS_CONFIG) or {}
        sources_config = load_config(SOURCES_CONFIG) or {}
    except (IOError, OSError) as e:
        logger.error("Failed to load config: %s", e)
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error("Invalid YAML in config: %s", e)
        sys.exit(1)

    clubs = clubs_data.get('clubs') or []

    # Load previous state
    previous_state = load_state(STATE_FILE)

    # Initialize Telegram (unless dry-run)
    telegram = None
    if not args.dry_run:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')

        if not bot_token or not chat_id:
            logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set!")
            sys.exit(1)

        telegram = TelegramAlert(bot_token, chat_id)

    logger.info("Loaded %d clubs from config", len(clubs))

    run_result = run_monitors(clubs, sources_config, previous_state, telegram, logger)

    new_state = {
        'last_run': datetime.utcnow().isoformat(),
        'clubs': build_state(run_result['results'], previous_state),
        'errors': run_result['errors'],
    }
    save_state(STATE_FILE, new_state)

    # Separate critical (monitor crash) vs non-critical (page/domain) errors
    critical_errors = [e for e in run_result['errors'] if e.get('critical', True)]
    page_errors = [e for e in run_result['errors'] if not e.get('critical', True)]

    logger.info(
        "Run completed - %d alerts sent, %d monitor crashes, %d page/domain errors",
        run_result['alerts_sent'], len(critical_errors), len(page_errors)
    )

    # Note: git commit of state/ and logs/ is handled by the GitHub Actions
    # workflow (daily-check.yml). main.py only writes files.

    # Fail the job when nothing worked, so a fully broken run is not green in CI.
    # State is already persisted above, so the baseline is never lost.
    enabled = run_result.get('sources_enabled', 0)
    failed_sources = {e['source'] for e in run_result['errors']}
    if enabled and len(failed_sources) >= enabled:
        logger.error(
            "All %d enabled source(s) failed: %s",
            enabled, ', '.join(sorted(failed_sources))
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
