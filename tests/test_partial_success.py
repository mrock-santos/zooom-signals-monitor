"""
Test that partial success (some sources worked, some failed) doesn't exit(1).

Regression test for bug where exit(1) triggered even when alerts were sent successfully,
preventing state commit in GitHub Actions.
"""

import pytest
from unittest.mock import Mock, patch


def test_partial_success_does_not_exit():
    """
    Partial success scenario: WHOIS works, Site monitoring has errors.
    Should NOT exit(1) because WHOIS produced data.
    """
    from main import run_monitors

    clubs = [
        {
            'id': 'test-club',
            'name': 'Test Club',
            'domains': ['test.com'],
            'whois_enabled': True,
            'site_monitoring_enabled': True,
            'official_site': {
                'url': 'https://test.com',
                'monitor_pages': [{'path': '/test', 'label': 'Test'}]
            }
        }
    ]

    sources_config = {
        'sources': {
            'whois': {'enabled': True, 'rate_limit_seconds': 0.1, 'timeout_seconds': 5},
            'site_monitoring': {'enabled': True, 'rate_limit_seconds': 0.1, 'timeout_seconds': 5,
                              'user_agent': 'Test'},
            'google_trends': {'enabled': False}
        }
    }

    previous_state = {}
    logger = Mock()

    # Mock WHOIS to succeed
    with patch('monitors.whois.WhoisMonitor.check') as mock_whois:
        mock_whois.return_value = {
            'success': True,
            'data': {'test-club': {'test.com': {'registrar': 'Test'}}},
            'error': None,
            'errors': []
        }

        # Mock Site to have errors but also data
        with patch('monitors.site_hash.SiteMonitor.check') as mock_site:
            mock_site.return_value = {
                'success': True,
                'data': {'test-club': {'/test': {'hash': 'abc123'}}},
                'error': None,
                'errors': [
                    {'source': 'site', 'type': 'page_error', 'url': 'https://test.com/broken',
                     'error': '404', 'critical': False}
                ]
            }

            result = run_monitors(clubs, sources_config, previous_state, None, logger)

            # Both sources should have data
            assert 'whois' in result['sources_with_data']
            assert 'site_monitoring' in result['sources_with_data']

            # Should have errors but not be a total failure
            assert len(result['errors']) == 1
            assert result['errors'][0]['type'] == 'page_error'

            # sources_enabled should be 2
            assert result['sources_enabled'] == 2


def test_total_failure_exits():
    """
    Total failure scenario: All sources produce zero data.
    Should allow exit(1) logic to trigger (we test the condition, not the exit itself).
    """
    from main import run_monitors

    clubs = [
        {
            'id': 'test-club',
            'name': 'Test Club',
            'domains': ['test.com'],
            'whois_enabled': True
        }
    ]

    sources_config = {
        'sources': {
            'whois': {'enabled': True, 'rate_limit_seconds': 0.1, 'timeout_seconds': 5},
            'site_monitoring': {'enabled': False},
            'google_trends': {'enabled': False}
        }
    }

    previous_state = {}
    logger = Mock()

    # Mock WHOIS to return no data
    with patch('monitors.whois.WhoisMonitor.check') as mock_whois:
        mock_whois.return_value = {
            'success': True,
            'data': {},  # No data!
            'error': None,
            'errors': [
                {'source': 'whois', 'type': 'domain_error', 'domain': 'test.com',
                 'error': 'Connection refused', 'critical': False}
            ]
        }

        result = run_monitors(clubs, sources_config, previous_state, None, logger)

        # No sources should have data
        assert len(result['sources_with_data']) == 0

        # sources_enabled should be 1
        assert result['sources_enabled'] == 1

        # This condition should allow exit(1) in main():
        # enabled and not sources_with_data
        assert result['sources_enabled'] and not result['sources_with_data']
