import whois
import time
import logging
from datetime import datetime, timedelta


class WhoisMonitor:
    """WHOIS domain registration monitor."""

    def __init__(self, config: dict):
        """
        Initialize WHOIS monitor.

        Args:
            config: Dict with rate_limit_seconds, timeout_seconds
        """
        self.rate_limit = config['rate_limit_seconds']
        self.timeout = config['timeout_seconds']
        self.logger = logging.getLogger('monitor')

    def check(self, clubs: list) -> dict:
        """
        Check WHOIS data for all enabled clubs.

        Args:
            clubs: List of club dicts with 'domains' and 'whois_enabled'

        Returns:
            {success: True, data: {club_id: {domain: {...}}}, error: None}
        """
        results = {}

        for club in clubs:
            if not club.get('whois_enabled', True):
                continue

            club_results = {}
            for domain in club.get('domains', []):
                try:
                    data = self._check_domain(domain)
                    club_results[domain] = data
                    time.sleep(self.rate_limit)

                except Exception as e:
                    self.logger.error(f"WHOIS check failed for {domain}: {e}")
                    club_results[domain] = {'error': str(e)}

            if club_results:
                results[club['id']] = club_results

        return {'success': True, 'data': results, 'error': None}

    def _check_domain(self, domain: str) -> dict:
        """
        Query WHOIS for single domain.

        Returns:
            Dict with registrar, dates, nameservers, status
        """
        w = whois.whois(domain)

        return {
            'registrar': w.registrar,
            'updated_date': self._normalize_date(w.updated_date),
            'expiry_date': self._normalize_date(w.expiration_date),
            'nameservers': w.name_servers or [],
            'status': w.status if isinstance(w.status, list) else [w.status] if w.status else [],
            'last_checked': datetime.utcnow().isoformat()
        }

    def _normalize_date(self, date) -> str | None:
        """
        Normalize date to ISO format.

        WHOIS returns different formats by TLD:
        - Some return datetime
        - Some return list of datetime
        - Some return None
        """
        if date is None:
            return None

        if isinstance(date, list):
            date = date[0]  # Take first date if list

        if isinstance(date, datetime):
            return date.date().isoformat()

        return str(date) if date else None


def detect_whois_changes(old_data: dict | None, new_data: dict, domain: str) -> list:
    """
    Detect changes between old and new WHOIS data.

    CRITICAL: Uses independent IFs (not elif) to detect multiple simultaneous changes.

    Args:
        old_data: Previous WHOIS data (or None if first check)
        new_data: Current WHOIS data
        domain: Domain name

    Returns:
        List of change dicts with 'type' and details
    """
    changes = []

    # New domain (first check)
    if old_data is None:
        changes.append({
            'type': 'new_domain',
            'domain': domain,
            'registrar': new_data.get('registrar')
        })
        return changes  # New domain = only one alert

    # From here: independent IFs (NOT elif) to catch simultaneous changes

    # Registrar changed
    if old_data.get('registrar') != new_data.get('registrar'):
        changes.append({
            'type': 'registrar_changed',
            'domain': domain,
            'old': old_data.get('registrar'),
            'new': new_data.get('registrar')
        })

    # Nameservers changed
    old_ns = set(old_data.get('nameservers', []))
    new_ns = set(new_data.get('nameservers', []))
    if old_ns != new_ns:
        changes.append({
            'type': 'nameservers_changed',
            'domain': domain,
            'added': list(new_ns - old_ns),
            'removed': list(old_ns - new_ns)
        })

    # Updated date changed (indicates recent modification)
    if old_data.get('updated_date') != new_data.get('updated_date'):
        changes.append({
            'type': 'whois_updated',
            'domain': domain,
            'new_update_date': new_data.get('updated_date')
        })

    # Expiring soon (<30 days) - ONLY alert on transition
    # (when crosses threshold for first time, not every subsequent check)
    if new_data.get('expiry_date'):
        try:
            new_expiry = datetime.fromisoformat(new_data['expiry_date'])
            new_days_left = (new_expiry.date() - datetime.now().date()).days

            # Check if this is a transition (was >30 days, now <=30 days)
            is_now_expiring = new_days_left < 30

            # Calculate old days left if we have old data
            was_expiring = False
            if old_data and old_data.get('expiry_date'):
                try:
                    old_expiry = datetime.fromisoformat(old_data['expiry_date'])
                    old_days_left = (old_expiry.date() - datetime.now().date()).days
                    was_expiring = old_days_left < 30
                except (ValueError, TypeError):
                    pass

            # Only alert if entering the <30 days window (transition)
            if is_now_expiring and not was_expiring:
                changes.append({
                    'type': 'expiring_soon',
                    'domain': domain,
                    'expiry_date': new_data['expiry_date'],
                    'days_left': new_days_left
                })
        except (ValueError, TypeError):
            pass  # Invalid date format, skip

    return changes
