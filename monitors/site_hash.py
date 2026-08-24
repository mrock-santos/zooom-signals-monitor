from __future__ import annotations

import requests
import hashlib
import time
import logging
from datetime import datetime
from bs4 import BeautifulSoup


class SiteMonitor:
    """Official site content monitoring via hash comparison."""

    def __init__(self, config: dict):
        """
        Initialize site monitor.

        Args:
            config: Dict with rate_limit_seconds, timeout_seconds, user_agent
        """
        self.rate_limit = config['rate_limit_seconds']
        self.timeout = config['timeout_seconds']
        self.user_agent = config['user_agent']
        self.logger = logging.getLogger('monitor')

    def check(self, clubs: list) -> dict:
        """
        Check site content for all enabled clubs.

        Args:
            clubs: List of club dicts with official_site config

        Returns:
            {success: True, data: {club_id: {page_path: {hash, last_checked}}},
             error: None, errors: [{type, url, error, critical}]}
        """
        results = {}
        errors = []

        for club in clubs:
            if not club.get('site_monitoring_enabled', True):
                continue

            if 'official_site' not in club:
                continue

            club_results = {}
            base_url = club['official_site']['url']

            for page in club['official_site'].get('monitor_pages', []):
                page_path = page['path']
                full_url = base_url + page_path

                try:
                    html = self._fetch_page(full_url)
                    content_hash = self._hash_content(html)

                    club_results[page_path] = {
                        'hash': content_hash,
                        'last_checked': datetime.utcnow().isoformat()
                    }

                    time.sleep(self.rate_limit)

                except Exception as e:
                    self.logger.error(f"Site check failed for {full_url}: {e}")
                    club_results[page_path] = {'error': str(e)}

                    # Record page error for observability
                    errors.append({
                        'source': 'site',
                        'type': 'page_error',
                        'url': full_url,
                        'error': str(e),
                        'critical': False
                    })

            if club_results:
                results[club['id']] = club_results

        return {'success': True, 'data': results, 'error': None, 'errors': errors}

    def _fetch_page(self, url: str) -> str:
        """Fetch page HTML."""
        headers = {'User-Agent': self.user_agent}
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def _hash_content(self, html: str) -> str:
        """
        Hash normalized content (remove dynamic elements).

        Removes:
        - <script>, <style>, <noscript>, <iframe>
        - Elements with class containing 'ad'
        - Normalizes whitespace

        Returns:
            MD5 hex digest (32 chars)
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Remove dynamic/ad elements
        for tag in soup(['script', 'style', 'noscript', 'iframe']):
            tag.decompose()

        # Remove ads (heuristic: class contains 'ad')
        for tag in soup.find_all(class_=lambda x: x and 'ad' in x.lower()):
            tag.decompose()

        # Extract text, normalize whitespace
        text = soup.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())  # Normalize multiple spaces

        return hashlib.md5(text.encode('utf-8')).hexdigest()


def detect_site_changes(old_hash: str | None, new_hash: str) -> dict | None:
    """
    Detect if site content changed.

    Args:
        old_hash: Previous content hash (None if first check)
        new_hash: Current content hash

    Returns:
        Dict with change details or None if no change
    """
    if old_hash is None:
        return None  # First check, no comparison

    if old_hash == new_hash:
        return None  # No change

    return {
        'type': 'content_changed',
        'old_hash': old_hash[:8] + '...',  # Truncate for readability
        'new_hash': new_hash[:8] + '...'
    }
