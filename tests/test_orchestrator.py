# -*- coding: utf-8 -*-
"""Tests for the main orchestrator (Task 11)."""

import json
import logging

import pytest
import yaml
from unittest.mock import MagicMock, patch

import main


@pytest.fixture(autouse=True)
def no_sleep():
    """Never actually wait INTER_SOURCE_DELAY during tests."""
    with patch('main.time.sleep'):
        yield


@pytest.fixture
def logger():
    return logging.getLogger('monitor')


@pytest.fixture
def clubs():
    return [{
        'id': 'flamengo',
        'name': 'Flamengo',
        'domains': ['flamengo.com.br'],
        'official_site': {
            'url': 'https://www.flamengo.com.br',
            'monitor_pages': [{'path': '/elenco', 'label': 'Elenco Profissional'}],
        },
        'trends_keywords': ['Flamengo'],
    }]


@pytest.fixture
def sources_all_enabled():
    return {'sources': {
        'whois': {'enabled': True, 'rate_limit_seconds': 0, 'timeout_seconds': 1},
        'site_monitoring': {'enabled': True, 'rate_limit_seconds': 0,
                            'timeout_seconds': 1, 'user_agent': 'test'},
        'google_trends': {'enabled': True, 'rate_limit_seconds': 0},
    }}


@pytest.fixture
def sources_all_disabled():
    return {'sources': {
        'whois': {'enabled': False},
        'site_monitoring': {'enabled': False},
        'google_trends': {'enabled': False},
    }}


# --------------------------------------------------------------------------
# Config / state helpers
# --------------------------------------------------------------------------

def test_main_loads_configs(tmp_path):
    """load_config() parses clubs.yaml and sources.yaml."""
    clubs_yaml = tmp_path / "clubs.yaml"
    sources_yaml = tmp_path / "sources.yaml"

    clubs_yaml.write_text("clubs: []")
    sources_yaml.write_text("sources:\n  whois:\n    enabled: false\n")

    assert main.load_config(str(clubs_yaml)) == {'clubs': []}
    assert main.load_config(str(sources_yaml))['sources']['whois']['enabled'] is False


def test_load_state_returns_empty_skeleton_when_missing(tmp_path):
    """First ever run: no state file yet."""
    assert main.load_state(str(tmp_path / "nope.json")) == {'clubs': {}}


def test_load_state_reads_existing(tmp_path):
    state_file = tmp_path / "last_check.json"
    state_file.write_text(json.dumps({'clubs': {'flamengo': {'whois': {}}}}))

    assert main.load_state(str(state_file))['clubs']['flamengo'] == {'whois': {}}


def test_save_state_creates_parent_dirs(tmp_path):
    target = tmp_path / "state" / "last_check.json"

    main.save_state(str(target), {'clubs': {}, 'last_run': 'x'})

    assert json.loads(target.read_text())['last_run'] == 'x'


# --------------------------------------------------------------------------
# build_state: source-keyed results -> club-keyed state
# --------------------------------------------------------------------------

def test_build_state_pivots_results_to_club_keyed():
    """State must be club-keyed so run_monitors() can read it back next run."""
    results = {
        'whois': {'flamengo': {'flamengo.com.br': {'registrar': 'X'}}},
        'site_monitoring': {'flamengo': {'/elenco': {'hash': 'abc'}}},
    }

    state = main.build_state(results, {'clubs': {}})

    assert state['flamengo']['whois']['flamengo.com.br']['registrar'] == 'X'
    assert state['flamengo']['site_monitoring']['/elenco']['hash'] == 'abc'


def test_build_state_preserves_previous_value_when_new_check_errored():
    """A transient failure must not wipe the baseline (would cause false alerts)."""
    previous = {'clubs': {'flamengo': {'whois': {'flamengo.com.br': {'registrar': 'GOOD'}}}}}
    results = {'whois': {'flamengo': {'flamengo.com.br': {'error': 'timeout'}}}}

    state = main.build_state(results, previous)

    assert state['flamengo']['whois']['flamengo.com.br']['registrar'] == 'GOOD'


def test_build_state_keeps_error_when_no_previous_value():
    results = {'whois': {'flamengo': {'flamengo.com.br': {'error': 'timeout'}}}}

    state = main.build_state(results, {'clubs': {}})

    assert state['flamengo']['whois']['flamengo.com.br'] == {'error': 'timeout'}


# --------------------------------------------------------------------------
# run_monitors
# --------------------------------------------------------------------------

def test_run_monitors_skips_disabled_sources(clubs, sources_all_disabled, logger):
    with patch('main.WhoisMonitor') as whois_cls, \
         patch('main.SiteMonitor') as site_cls, \
         patch('main.TrendsMonitor') as trends_cls:

        out = main.run_monitors(clubs, sources_all_disabled, {'clubs': {}}, None, logger)

    whois_cls.assert_not_called()
    site_cls.assert_not_called()
    trends_cls.assert_not_called()
    assert out == {'results': {}, 'errors': [], 'alerts_sent': 0}


def test_orchestrator_isolates_monitor_failures(clubs, sources_all_enabled, logger):
    """If one monitor crashes, the others still run."""
    site_instance = MagicMock()
    site_instance.check.return_value = {
        'success': True,
        'data': {'flamengo': {'/elenco': {'hash': 'newhash'}}},
        'error': None,
    }
    trends_instance = MagicMock()
    trends_instance.check.return_value = {'success': True, 'data': {}, 'error': None}

    with patch('main.WhoisMonitor', side_effect=RuntimeError('boom')), \
         patch('main.SiteMonitor', return_value=site_instance), \
         patch('main.TrendsMonitor', return_value=trends_instance):

        out = main.run_monitors(clubs, sources_all_enabled, {'clubs': {}}, None, logger)

    assert out['errors'][0]['source'] == 'whois'
    assert out['errors'][0]['critical'] is True
    site_instance.check.assert_called_once()
    trends_instance.check.assert_called_once()
    assert out['results']['site_monitoring']['flamengo']['/elenco']['hash'] == 'newhash'


def test_run_monitors_records_unsuccessful_result_as_error(clubs, sources_all_enabled, logger):
    whois_instance = MagicMock()
    whois_instance.check.return_value = {'success': False, 'data': {}, 'error': 'rate limited'}
    ok = MagicMock()
    ok.check.return_value = {'success': True, 'data': {}, 'error': None}

    with patch('main.WhoisMonitor', return_value=whois_instance), \
         patch('main.SiteMonitor', return_value=ok), \
         patch('main.TrendsMonitor', return_value=ok):

        out = main.run_monitors(clubs, sources_all_enabled, {'clubs': {}}, None, logger)

    assert {'source': 'whois', 'error': 'rate limited'} in out['errors']
    assert 'whois' not in out['results']


def test_run_monitors_sends_whois_alert(clubs, sources_all_enabled, logger):
    whois_instance = MagicMock()
    whois_instance.check.return_value = {
        'success': True,
        'data': {'flamengo': {'flamengo.com.br': {'registrar': 'NEW', 'nameservers': []}}},
        'error': None,
    }
    ok = MagicMock()
    ok.check.return_value = {'success': True, 'data': {}, 'error': None}

    telegram = MagicMock()
    telegram.send.return_value = True

    with patch('main.WhoisMonitor', return_value=whois_instance), \
         patch('main.SiteMonitor', return_value=ok), \
         patch('main.TrendsMonitor', return_value=ok):

        out = main.run_monitors(clubs, sources_all_enabled, {'clubs': {}}, telegram, logger)

    # first check of the domain => new_domain alert
    args = telegram.format_whois_alert.call_args[0]
    assert args[0] == 'Flamengo'
    assert args[1]['type'] == 'new_domain'
    assert out['alerts_sent'] == 1


def test_run_monitors_skips_errored_entries(clubs, sources_all_enabled, logger):
    whois_instance = MagicMock()
    whois_instance.check.return_value = {
        'success': True,
        'data': {'flamengo': {'flamengo.com.br': {'error': 'timeout'}}},
        'error': None,
    }
    ok = MagicMock()
    ok.check.return_value = {'success': True, 'data': {}, 'error': None}
    telegram = MagicMock()

    with patch('main.WhoisMonitor', return_value=whois_instance), \
         patch('main.SiteMonitor', return_value=ok), \
         patch('main.TrendsMonitor', return_value=ok):

        out = main.run_monitors(clubs, sources_all_enabled, {'clubs': {}}, telegram, logger)

    telegram.format_whois_alert.assert_not_called()
    assert out['alerts_sent'] == 0


def test_run_monitors_site_alert_uses_label_and_full_url(clubs, sources_all_enabled, logger):
    site_instance = MagicMock()
    site_instance.check.return_value = {
        'success': True,
        'data': {'flamengo': {'/elenco': {'hash': 'b' * 32}}},
        'error': None,
    }
    ok = MagicMock()
    ok.check.return_value = {'success': True, 'data': {}, 'error': None}
    telegram = MagicMock()
    telegram.send.return_value = True

    previous = {'clubs': {'flamengo': {'site_monitoring': {'/elenco': {'hash': 'a' * 32}}}}}

    with patch('main.WhoisMonitor', return_value=ok), \
         patch('main.SiteMonitor', return_value=site_instance), \
         patch('main.TrendsMonitor', return_value=ok):

        out = main.run_monitors(clubs, sources_all_enabled, previous, telegram, logger)

    club_name, label, url, change = telegram.format_site_alert.call_args[0]
    assert club_name == 'Flamengo'
    assert label == 'Elenco Profissional'
    assert url == 'https://www.flamengo.com.br/elenco'
    assert change['type'] == 'content_changed'
    assert out['alerts_sent'] == 1


def test_run_monitors_no_site_alert_on_first_check(clubs, sources_all_enabled, logger):
    site_instance = MagicMock()
    site_instance.check.return_value = {
        'success': True,
        'data': {'flamengo': {'/elenco': {'hash': 'b' * 32}}},
        'error': None,
    }
    ok = MagicMock()
    ok.check.return_value = {'success': True, 'data': {}, 'error': None}
    telegram = MagicMock()

    with patch('main.WhoisMonitor', return_value=ok), \
         patch('main.SiteMonitor', return_value=site_instance), \
         patch('main.TrendsMonitor', return_value=ok):

        out = main.run_monitors(clubs, sources_all_enabled, {'clubs': {}}, telegram, logger)

    telegram.format_site_alert.assert_not_called()
    assert out['alerts_sent'] == 0


def test_run_monitors_sends_trends_spike_alert(clubs, sources_all_enabled, logger):
    trends_instance = MagicMock()
    trends_instance.check.return_value = {
        'success': True,
        'data': {'flamengo': {'Flamengo': {'interest_score': 90, 'avg_7d': 30, 'spike': True}}},
        'error': None,
    }
    ok = MagicMock()
    ok.check.return_value = {'success': True, 'data': {}, 'error': None}
    telegram = MagicMock()
    telegram.send.return_value = True

    with patch('main.WhoisMonitor', return_value=ok), \
         patch('main.SiteMonitor', return_value=ok), \
         patch('main.TrendsMonitor', return_value=trends_instance):

        out = main.run_monitors(clubs, sources_all_enabled, {'clubs': {}}, telegram, logger)

    club_name, keyword, data = telegram.format_trends_alert.call_args[0]
    assert club_name == 'Flamengo'
    assert keyword == 'Flamengo'
    assert data['spike'] is True
    assert out['alerts_sent'] == 1


def test_run_monitors_dry_run_sends_nothing(clubs, sources_all_enabled, logger):
    """telegram=None (dry-run) must not crash and must not count alerts."""
    whois_instance = MagicMock()
    whois_instance.check.return_value = {
        'success': True,
        'data': {'flamengo': {'flamengo.com.br': {'registrar': 'NEW', 'nameservers': []}}},
        'error': None,
    }
    ok = MagicMock()
    ok.check.return_value = {'success': True, 'data': {}, 'error': None}

    with patch('main.WhoisMonitor', return_value=whois_instance), \
         patch('main.SiteMonitor', return_value=ok), \
         patch('main.TrendsMonitor', return_value=ok):

        out = main.run_monitors(clubs, sources_all_enabled, {'clubs': {}}, None, logger)

    assert out['alerts_sent'] == 0
    assert out['errors'] == []


def test_run_monitors_failed_telegram_send_not_counted(clubs, sources_all_enabled, logger):
    whois_instance = MagicMock()
    whois_instance.check.return_value = {
        'success': True,
        'data': {'flamengo': {'flamengo.com.br': {'registrar': 'NEW', 'nameservers': []}}},
        'error': None,
    }
    ok = MagicMock()
    ok.check.return_value = {'success': True, 'data': {}, 'error': None}
    telegram = MagicMock()
    telegram.send.return_value = False

    with patch('main.WhoisMonitor', return_value=whois_instance), \
         patch('main.SiteMonitor', return_value=ok), \
         patch('main.TrendsMonitor', return_value=ok):

        out = main.run_monitors(clubs, sources_all_enabled, {'clubs': {}}, telegram, logger)

    assert out['alerts_sent'] == 0


def test_run_monitors_delay_only_between_sources_that_ran(clubs, sources_all_disabled, logger):
    """No enabled source => no INTER_SOURCE_DELAY sleeps."""
    with patch('main.time.sleep') as sleeper:
        main.run_monitors(clubs, sources_all_disabled, {'clubs': {}}, None, logger)

    sleeper.assert_not_called()


# --------------------------------------------------------------------------
# main()
# --------------------------------------------------------------------------

def _write_configs(tmp_path, sources):
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config' / 'clubs.yaml').write_text(yaml.safe_dump({'clubs': []}))
    (tmp_path / 'config' / 'sources.yaml').write_text(yaml.safe_dump(sources))
    return tmp_path


def test_main_dry_run_writes_state(tmp_path, sources_all_disabled, monkeypatch):
    _write_configs(tmp_path, sources_all_disabled)
    state_file = tmp_path / 'state' / 'last_check.json'

    monkeypatch.setattr(main, 'CLUBS_CONFIG', str(tmp_path / 'config' / 'clubs.yaml'))
    monkeypatch.setattr(main, 'SOURCES_CONFIG', str(tmp_path / 'config' / 'sources.yaml'))
    monkeypatch.setattr(main, 'STATE_FILE', str(state_file))
    monkeypatch.setattr(main, 'setup_logger', lambda *a, **k: logging.getLogger('monitor'))
    monkeypatch.setattr('sys.argv', ['main.py', '--dry-run'])

    with patch('main.TelegramAlert') as tg_cls:
        main.main()

    tg_cls.assert_not_called()
    saved = json.loads(state_file.read_text())
    assert saved['clubs'] == {}
    assert 'last_run' in saved


def test_main_exits_when_telegram_env_missing(tmp_path, sources_all_disabled, monkeypatch):
    _write_configs(tmp_path, sources_all_disabled)

    monkeypatch.setattr(main, 'CLUBS_CONFIG', str(tmp_path / 'config' / 'clubs.yaml'))
    monkeypatch.setattr(main, 'SOURCES_CONFIG', str(tmp_path / 'config' / 'sources.yaml'))
    monkeypatch.setattr(main, 'STATE_FILE', str(tmp_path / 'state' / 'last_check.json'))
    monkeypatch.setattr(main, 'setup_logger', lambda *a, **k: logging.getLogger('monitor'))
    monkeypatch.setattr('sys.argv', ['main.py'])
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
    monkeypatch.delenv('TELEGRAM_CHAT_ID', raising=False)

    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 1


def test_main_exits_when_clubs_config_missing(tmp_path, sources_all_disabled, monkeypatch):
    _write_configs(tmp_path, sources_all_disabled)

    monkeypatch.setattr(main, 'CLUBS_CONFIG', str(tmp_path / 'config' / 'does-not-exist.yaml'))
    monkeypatch.setattr(main, 'SOURCES_CONFIG', str(tmp_path / 'config' / 'sources.yaml'))
    monkeypatch.setattr(main, 'STATE_FILE', str(tmp_path / 'state' / 'last_check.json'))
    monkeypatch.setattr(main, 'setup_logger', lambda *a, **k: logging.getLogger('monitor'))
    monkeypatch.setattr('sys.argv', ['main.py', '--dry-run'])

    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 1
