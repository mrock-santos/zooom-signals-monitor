import pytest
from unittest.mock import Mock, patch
from monitors.site_hash import SiteMonitor, detect_site_changes


@pytest.fixture
def site_config():
    return {
        'rate_limit_seconds': 0.1,
        'timeout_seconds': 5,
        'user_agent': 'TestBot/1.0'
    }


@pytest.fixture
def sample_clubs():
    return [
        {
            'id': 'test-club',
            'name': 'Test Club',
            'official_site': {
                'url': 'https://example.com',
                'monitor_pages': [
                    {'path': '/squad', 'label': 'Squad', 'type': 'structural'}
                ]
            },
            'site_monitoring_enabled': True
        }
    ]


def test_site_monitor_skips_disabled_clubs(site_config):
    """Monitor skips clubs with site_monitoring_enabled: False"""
    clubs = [
        {'id': 'disabled', 'site_monitoring_enabled': False}
    ]

    monitor = SiteMonitor(site_config)
    result = monitor.check(clubs)

    assert result['success'] is True
    assert 'disabled' not in result['data']


@patch('monitors.site_hash.requests.get')
def test_site_monitor_fetches_and_hashes(mock_get, site_config, sample_clubs):
    """Monitor fetches page and creates hash"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = '<html><body>Squad content</body></html>'

    monitor = SiteMonitor(site_config)
    result = monitor.check(sample_clubs)

    assert result['success'] is True
    assert 'test-club' in result['data']
    assert '/squad' in result['data']['test-club']

    page_data = result['data']['test-club']['/squad']
    assert 'hash' in page_data
    assert 'last_checked' in page_data
    assert len(page_data['hash']) == 32  # MD5 hex


@patch('monitors.site_hash.requests.get')
def test_site_monitor_removes_dynamic_content(mock_get, site_config, sample_clubs):
    """Monitor removes scripts, styles, ads before hashing"""
    html_with_dynamic = '''
    <html>
        <head><script>var ad = 1;</script></head>
        <body>
            <div class="squad">Player 1</div>
            <div class="advertisement">Buy now!</div>
            <script>trackClick();</script>
        </body>
    </html>
    '''

    mock_get.return_value.status_code = 200
    mock_get.return_value.text = html_with_dynamic

    monitor = SiteMonitor(site_config)
    result = monitor.check(sample_clubs)

    # Should hash only "Player 1" text, not scripts/ads
    page_hash = result['data']['test-club']['/squad']['hash']
    assert page_hash  # Hash generated

    # Verify content was cleaned by calling the REAL _hash_content method
    # (not reimplementing parsing)
    cleaned_hash = monitor._hash_content(html_with_dynamic)

    # Hash from actual HTML with dynamic content
    # vs hash from clean HTML (no scripts, no ads with 'ad' in class)
    clean_html = '<html><body><div class="squad">Player 1</div></body></html>'
    clean_hash = monitor._hash_content(clean_html)

    # The hash from dynamic HTML should equal hash from clean HTML
    # (proving scripts and ads were removed)
    assert cleaned_hash == clean_hash


@patch('monitors.site_hash.requests.get')
def test_site_monitor_handles_http_errors(mock_get, site_config, sample_clubs):
    """Monitor logs error but doesn't crash on HTTP failure"""
    mock_get.side_effect = Exception('Connection timeout')

    monitor = SiteMonitor(site_config)
    result = monitor.check(sample_clubs)

    assert result['success'] is True
    assert 'test-club' in result['data']
    assert 'error' in result['data']['test-club']['/squad']


def test_detect_site_changes_first_check():
    """detect_changes returns None on first check"""
    old_hash = None
    new_hash = 'abc123def'

    change = detect_site_changes(old_hash, new_hash)
    assert change is None  # First check, no comparison


def test_detect_site_changes_no_change():
    """detect_changes returns None when hash unchanged"""
    old_hash = 'abc123'
    new_hash = 'abc123'

    change = detect_site_changes(old_hash, new_hash)
    assert change is None


def test_detect_site_changes_content_changed():
    """detect_changes detects hash difference"""
    old_hash = 'abc123'
    new_hash = 'def456'

    change = detect_site_changes(old_hash, new_hash)

    assert change is not None
    assert change['type'] == 'content_changed'
    assert 'abc123' in change['old_hash']
    assert 'def456' in change['new_hash']
