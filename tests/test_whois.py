import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from monitors.whois import WhoisMonitor


@pytest.fixture
def whois_config():
    return {
        'rate_limit_seconds': 0.1,  # Fast for tests
        'timeout_seconds': 5
    }


@pytest.fixture
def sample_clubs():
    return [
        {
            'id': 'test-club',
            'name': 'Test Club',
            'domains': ['example.com'],
            'whois_enabled': True
        }
    ]


def test_whois_monitor_skips_disabled_clubs(whois_config):
    """Monitor skips clubs with whois_enabled: False"""
    clubs = [
        {'id': 'disabled', 'domains': ['test.com'], 'whois_enabled': False}
    ]

    monitor = WhoisMonitor(whois_config)
    result = monitor.check(clubs)

    assert result['success'] is True
    assert 'disabled' not in result['data']


@patch('monitors.whois.whois.whois')
def test_whois_monitor_fetches_domain_info(mock_whois, whois_config, sample_clubs):
    """Monitor fetches and normalizes WHOIS data"""
    mock_whois.return_value = MagicMock(
        registrar='Test Registrar',
        updated_date=datetime(2026, 1, 15),
        expiration_date=datetime(2027, 1, 15),
        name_servers=['ns1.example.com', 'ns2.example.com'],
        status=['clientTransferProhibited']
    )

    monitor = WhoisMonitor(whois_config)
    result = monitor.check(sample_clubs)

    assert result['success'] is True
    assert 'test-club' in result['data']
    assert 'example.com' in result['data']['test-club']

    domain_data = result['data']['test-club']['example.com']
    assert domain_data['registrar'] == 'Test Registrar'
    assert domain_data['updated_date'] == '2026-01-15'
    assert domain_data['expiry_date'] == '2027-01-15'
    assert 'ns1.example.com' in domain_data['nameservers']


@patch('monitors.whois.whois.whois')
def test_whois_monitor_handles_date_lists(mock_whois, whois_config, sample_clubs):
    """Monitor handles date returned as list (some TLDs)"""
    mock_whois.return_value = MagicMock(
        registrar='Reg',
        updated_date=[datetime(2026, 1, 15), datetime(2026, 1, 16)],  # List
        expiration_date=datetime(2027, 1, 15),
        name_servers=[],
        status=[]
    )

    monitor = WhoisMonitor(whois_config)
    result = monitor.check(sample_clubs)

    domain_data = result['data']['test-club']['example.com']
    assert domain_data['updated_date'] == '2026-01-15'  # First date


@patch('monitors.whois.whois.whois')
def test_whois_monitor_handles_errors_gracefully(mock_whois, whois_config, sample_clubs):
    """Monitor logs error but doesn't crash on WHOIS failure"""
    mock_whois.side_effect = Exception('Network timeout')

    monitor = WhoisMonitor(whois_config)
    result = monitor.check(sample_clubs)

    assert result['success'] is True  # Overall success
    assert 'test-club' in result['data']
    assert 'error' in result['data']['test-club']['example.com']


def test_detect_whois_changes_new_domain():
    """detect_changes identifies new domain"""
    from monitors.whois import detect_whois_changes

    old_state = None
    new_data = {
        'registrar': 'Test',
        'expiry_date': '2027-01-15'
    }

    changes = detect_whois_changes(old_state, new_data, 'test.com')

    assert len(changes) == 1
    assert changes[0]['type'] == 'new_domain'
    assert changes[0]['domain'] == 'test.com'


def test_detect_whois_changes_registrar_changed():
    """detect_changes identifies registrar change"""
    from monitors.whois import detect_whois_changes

    old_state = {'registrar': 'Old Registrar', 'nameservers': []}
    new_data = {'registrar': 'New Registrar', 'nameservers': []}

    changes = detect_whois_changes(old_state, new_data, 'test.com')

    assert any(c['type'] == 'registrar_changed' for c in changes)
    changed = [c for c in changes if c['type'] == 'registrar_changed'][0]
    assert changed['old'] == 'Old Registrar'
    assert changed['new'] == 'New Registrar'


def test_detect_whois_changes_nameservers_changed():
    """detect_changes identifies nameserver changes"""
    from monitors.whois import detect_whois_changes

    old_state = {
        'registrar': 'Same',
        'nameservers': ['ns1.old.com', 'ns2.old.com']
    }
    new_data = {
        'registrar': 'Same',
        'nameservers': ['ns1.new.com', 'ns2.old.com']
    }

    changes = detect_whois_changes(old_state, new_data, 'test.com')

    assert any(c['type'] == 'nameservers_changed' for c in changes)
    changed = [c for c in changes if c['type'] == 'nameservers_changed'][0]
    assert 'ns1.new.com' in changed['added']
    assert 'ns1.old.com' in changed['removed']


def test_detect_whois_changes_expiring_soon_transition():
    """detect_changes identifies domain crossing into <30 days threshold"""
    from monitors.whois import detect_whois_changes

    # Transition: was 35 days (safe), now 25 days (expiring soon)
    old_state = {'expiry_date': (datetime.now() + timedelta(days=35)).date().isoformat()}
    new_data = {'expiry_date': (datetime.now() + timedelta(days=25)).date().isoformat()}

    changes = detect_whois_changes(old_state, new_data, 'test.com')

    assert any(c['type'] == 'expiring_soon' for c in changes)


def test_detect_whois_changes_expiring_soon_no_duplicate():
    """detect_changes does NOT alert repeatedly while still in <30 days window"""
    from monitors.whois import detect_whois_changes

    # Both checks within <30 days window (no transition)
    old_state = {'expiry_date': (datetime.now() + timedelta(days=25)).date().isoformat()}
    new_data = {'expiry_date': (datetime.now() + timedelta(days=20)).date().isoformat()}

    changes = detect_whois_changes(old_state, new_data, 'test.com')

    # Should NOT alert (already was in <30 days window)
    assert not any(c['type'] == 'expiring_soon' for c in changes)


def test_detect_whois_changes_multiple_simultaneous():
    """detect_changes catches multiple changes in one check (NOT elif)"""
    from monitors.whois import detect_whois_changes

    old_state = {
        'registrar': 'Old',
        'nameservers': ['ns1.com'],
        'updated_date': '2026-01-01'
    }
    new_data = {
        'registrar': 'New',  # Changed
        'nameservers': ['ns2.com'],  # Changed
        'updated_date': '2026-08-20'  # Changed
    }

    changes = detect_whois_changes(old_state, new_data, 'test.com')

    # Must detect ALL THREE changes (not just first one)
    types = [c['type'] for c in changes]
    assert 'registrar_changed' in types
    assert 'nameservers_changed' in types
    assert 'whois_updated' in types


def test_normalize_registrar():
    """_normalize_registrar removes punctuation and entity suffixes"""
    from monitors.whois import _normalize_registrar

    # Test Real Madrid case that caused false positive
    assert _normalize_registrar("Tucows Domains Inc.") == "TUCOWS"
    assert _normalize_registrar("TUCOWS.COM, CO.") == "TUCOWS"

    # Test other common formats
    assert _normalize_registrar("Network Solutions, LLC") == "NETWORK SOLUTIONS"
    assert _normalize_registrar("NETWORK SOLUTIONS LLC") == "NETWORK SOLUTIONS"
    assert _normalize_registrar("GoDaddy.com, LLC") == "GODADDY"

    # Test null/empty handling
    assert _normalize_registrar(None) == ""
    assert _normalize_registrar("") == ""


def test_detect_whois_changes_registrar_format_variation():
    """
    detect_changes does NOT alert when registrar is same but format differs.

    This test covers the real-world issue where python-whois library
    returns different string formats for the same registrar:
    - "Tucows Domains Inc." vs "TUCOWS.COM, CO."

    Both should normalize to "TUCOWS" and NOT trigger registrar_changed.
    """
    from monitors.whois import detect_whois_changes

    # Baseline saved with format 1
    old_state = {
        'registrar': 'Tucows Domains Inc.',
        'nameservers': ['ns1.example.com']
    }

    # New query returns format 2 (different string, same company)
    new_data = {
        'registrar': 'TUCOWS.COM, CO.',
        'nameservers': ['ns1.example.com']
    }

    changes = detect_whois_changes(old_state, new_data, 'test.com')

    # Should NOT detect registrar change (normalized values are same)
    types = [c['type'] for c in changes]
    assert 'registrar_changed' not in types, \
        "Registrar format variation should not trigger false positive"

    # Should have no changes at all
    assert len(changes) == 0, \
        f"Expected no changes, got: {changes}"
