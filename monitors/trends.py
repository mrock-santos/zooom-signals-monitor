# -*- coding: utf-8 -*-
"""
Google Trends monitor.

CONDITIONAL SOURCE: only enable in config/sources.yaml after
scripts/test_trends_viability.py passes 3/3 with no errors.
"""

import time
import logging
from datetime import datetime

from pytrends.request import TrendReq


class TrendsMonitor:
    """Google Trends spike monitor."""

    def __init__(self, config: dict):
        """
        Initialize Trends monitor.

        Args:
            config: Dict with rate_limit_seconds, timeout_seconds, max_retries
        """
        self.rate_limit = config['rate_limit_seconds']
        self.timeout = config.get('timeout_seconds', 20)
        self.max_retries = config.get('max_retries', 2)
        self.logger = logging.getLogger('monitor')
        self.pytrends = TrendReq(hl='pt-BR', tz=180)

    def check(self, clubs: list) -> dict:
        """
        Check Trends data for club keywords.

        Args:
            clubs: List of club dicts with trends_keywords

        Returns:
            {success: True, data: {club_id: {keyword: {...}}}, error: None}
        """
        results = {}

        for club in clubs:
            keywords = club.get('trends_keywords', [])
            if not keywords:
                continue

            club_results = {}
            # Limit to 3 keywords per club to avoid rate limits
            for keyword in keywords[:3]:
                try:
                    data = self._check_keyword(keyword)
                    club_results[keyword] = data
                    time.sleep(self.rate_limit)

                except Exception as e:
                    self.logger.error(
                        "Trends check failed for '%s': %s: %s",
                        keyword, type(e).__name__, e
                    )
                    club_results[keyword] = {'error': str(e)}

            if club_results:
                results[club['id']] = club_results

        return {'success': True, 'data': results, 'error': None}

    def _check_keyword(self, keyword: str) -> dict:
        """
        Check Google Trends for keyword.

        Returns:
            Dict with interest_score, avg_7d, spike (bool), last_checked
        """
        self.pytrends.build_payload([keyword], timeframe='now 7-d', geo='BR')
        data = self.pytrends.interest_over_time()

        if data.empty:
            return {'interest_score': 0, 'avg_7d': 0, 'spike': False}

        latest_score = int(data[keyword].iloc[-1])
        avg_score = int(data[keyword].mean())

        # Spike = current score > 2x average
        is_spike = latest_score > (avg_score * 2) if avg_score > 0 else False

        return {
            'interest_score': latest_score,
            'avg_7d': avg_score,
            'spike': is_spike,
            'last_checked': datetime.utcnow().isoformat()
        }


def detect_trends_spikes(trends_data: dict) -> list:
    """
    Extract spike alerts from trends data.

    Args:
        trends_data: {club_id: {keyword: {interest_score, spike, ...}}}

    Returns:
        List of spike dicts for alerting
    """
    spikes = []

    for club_id, keywords in trends_data.items():
        for keyword, data in keywords.items():
            if 'error' in data:
                continue

            if data.get('spike', False):
                spikes.append({
                    'club_id': club_id,
                    'keyword': keyword,
                    'data': data
                })

    return spikes
