# -*- coding: utf-8 -*-
"""Tests for monitors/trends.py (mocked - no real Google Trends calls)."""

import pytest
from unittest.mock import Mock, patch

from monitors.trends import TrendsMonitor, detect_trends_spikes


@pytest.fixture
def trends_config():
    return {
        'rate_limit_seconds': 0.01,
        'timeout_seconds': 10,
        'max_retries': 2
    }


@pytest.fixture
def sample_clubs():
    return [
        {
            'id': 'test-club',
            'trends_keywords': ['Test Club', 'Test Player']
        }
    ]


@patch('monitors.trends.TrendReq')
def test_trends_monitor_fetches_data(mock_treq, trends_config, sample_clubs):
    """Monitor fetches Trends data"""
    import pandas as pd

    mock_instance = Mock()
    mock_treq.return_value = mock_instance

    mock_data = pd.DataFrame({
        'Test Club': [10, 20, 30, 40, 50],
        'Test Player': [5, 5, 5, 5, 90],
    })
    mock_instance.interest_over_time.return_value = mock_data

    monitor = TrendsMonitor(trends_config)
    result = monitor.check(sample_clubs)

    assert result['success'] is True
    assert result['error'] is None
    assert 'test-club' in result['data']
    assert 'Test Club' in result['data']['test-club']

    club_data = result['data']['test-club']['Test Club']
    assert club_data['interest_score'] == 50
    assert club_data['avg_7d'] == 30
    assert club_data['spike'] is False


@patch('monitors.trends.TrendReq')
def test_trends_monitor_detects_spike(mock_treq, trends_config):
    """interest_score > 2x avg is flagged as spike"""
    import pandas as pd

    mock_instance = Mock()
    mock_treq.return_value = mock_instance
    mock_instance.interest_over_time.return_value = pd.DataFrame({
        'Spiky': [5, 5, 5, 5, 90]
    })

    monitor = TrendsMonitor(trends_config)
    result = monitor.check([{'id': 'c1', 'trends_keywords': ['Spiky']}])

    assert result['data']['c1']['Spiky']['spike'] is True


@patch('monitors.trends.TrendReq')
def test_trends_monitor_handles_empty_dataframe(mock_treq, trends_config):
    """Empty DataFrame returns zeroed result, not an error"""
    import pandas as pd

    mock_instance = Mock()
    mock_treq.return_value = mock_instance
    mock_instance.interest_over_time.return_value = pd.DataFrame()

    monitor = TrendsMonitor(trends_config)
    result = monitor.check([{'id': 'c1', 'trends_keywords': ['Nothing']}])

    assert result['data']['c1']['Nothing'] == {
        'interest_score': 0, 'avg_7d': 0, 'spike': False
    }


@patch('monitors.trends.TrendReq')
def test_trends_monitor_captures_exception(mock_treq, trends_config):
    """Exceptions are captured per-keyword, never raised"""
    mock_instance = Mock()
    mock_treq.return_value = mock_instance
    mock_instance.build_payload.side_effect = Exception('429 Too Many Requests')

    monitor = TrendsMonitor(trends_config)
    result = monitor.check([{'id': 'c1', 'trends_keywords': ['Boom']}])

    assert result['success'] is True
    assert 'error' in result['data']['c1']['Boom']
    assert '429' in result['data']['c1']['Boom']['error']


@patch('monitors.trends.TrendReq')
def test_trends_monitor_limits_to_three_keywords(mock_treq, trends_config):
    """Only first 3 keywords per club are queried"""
    import pandas as pd

    mock_instance = Mock()
    mock_treq.return_value = mock_instance
    mock_instance.interest_over_time.return_value = pd.DataFrame(
        {'k%d' % i: [1, 2, 3] for i in range(1, 6)}
    )

    monitor = TrendsMonitor(trends_config)
    result = monitor.check([{
        'id': 'c1',
        'trends_keywords': ['k1', 'k2', 'k3', 'k4', 'k5']
    }])

    assert len(result['data']['c1']) == 3
    assert 'k4' not in result['data']['c1']


@patch('monitors.trends.TrendReq')
def test_trends_monitor_skips_clubs_without_keywords(mock_treq, trends_config):
    """Clubs without trends_keywords are skipped entirely"""
    mock_treq.return_value = Mock()

    monitor = TrendsMonitor(trends_config)
    result = monitor.check([{'id': 'c1'}, {'id': 'c2', 'trends_keywords': []}])

    assert result['data'] == {}


def test_detect_trends_spikes():
    """detect_trends_spikes extracts only spiking keywords"""
    data = {
        'club1': {
            'keyword1': {'interest_score': 95, 'spike': True},
            'keyword2': {'interest_score': 20, 'spike': False},
        },
        'club2': {
            'keyword3': {'interest_score': 80, 'spike': True},
        }
    }

    spikes = detect_trends_spikes(data)

    assert len(spikes) == 2
    assert any(s['keyword'] == 'keyword1' for s in spikes)
    assert any(s['keyword'] == 'keyword3' for s in spikes)
    assert not any(s['keyword'] == 'keyword2' for s in spikes)


def test_detect_trends_spikes_ignores_errors():
    """Keywords with errors are never reported as spikes"""
    data = {'club1': {'kw': {'error': '429 Too Many Requests', 'spike': True}}}

    assert detect_trends_spikes(data) == []
