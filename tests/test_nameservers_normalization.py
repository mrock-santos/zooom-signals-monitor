"""
Test nameservers normalization to prevent false positives.

Regression test for the bug where python-whois returns inconsistent
case formatting (uppercase/lowercase/mixed) causing false nameservers_changed
alerts on every run.
"""

import pytest
from monitors.whois import _normalize_nameservers, detect_whois_changes


def test_normalize_nameservers_case_insensitive():
    """
    Nameservers differing only in case should normalize to the same set.
    """
    uppercase = ["PDNS80.ULTRADNS.COM", "PDNS80.ULTRADNS.NET"]
    lowercase = ["pdns80.ultradns.com", "pdns80.ultradns.net"]
    mixed = ["Pdns80.UltraDNS.com", "Pdns80.UltraDNS.net"]

    assert _normalize_nameservers(uppercase) == _normalize_nameservers(lowercase)
    assert _normalize_nameservers(uppercase) == _normalize_nameservers(mixed)
    assert _normalize_nameservers(lowercase) == _normalize_nameservers(mixed)


def test_normalize_nameservers_removes_duplicates():
    """
    Duplicate nameservers (after normalization) should be deduplicated.
    """
    duplicates = [
        "PDNS80.ULTRADNS.COM",
        "pdns80.ultradns.com",  # Duplicate in lowercase
        "PDNS80.ULTRADNS.NET",
        "pdns80.ultradns.net"   # Duplicate in lowercase
    ]

    normalized = _normalize_nameservers(duplicates)

    # Should only have 2 unique servers
    assert len(normalized) == 2
    assert "pdns80.ultradns.com" in normalized
    assert "pdns80.ultradns.net" in normalized


def test_normalize_nameservers_order_independent():
    """
    Nameserver order should not matter (sets are unordered).
    """
    order1 = ["ns1.example.com", "ns2.example.com", "ns3.example.com"]
    order2 = ["ns3.example.com", "ns1.example.com", "ns2.example.com"]

    assert _normalize_nameservers(order1) == _normalize_nameservers(order2)


def test_normalize_nameservers_empty():
    """
    Empty or None nameservers should return empty set.
    """
    assert _normalize_nameservers(None) == set()
    assert _normalize_nameservers([]) == set()


def test_normalize_nameservers_strips_whitespace():
    """
    Leading/trailing whitespace should be stripped.
    """
    whitespace = [" ns1.example.com ", "ns2.example.com"]
    clean = ["ns1.example.com", "ns2.example.com"]

    assert _normalize_nameservers(whitespace) == _normalize_nameservers(clean)


def test_detect_whois_changes_nameservers_case_insensitive():
    """
    REGRESSION TEST: Same nameservers in different case should NOT trigger alert.

    This is the exact scenario from the Real Madrid false positive on 2026-08-24:
    - Old state had mixed case (UPPERCASE + lowercase duplicates)
    - New query returned only uppercase
    - Should NOT alert because they're the same servers
    """
    old_data = {
        'registrar': 'TUCOWS.COM, CO.',
        'updated_date': '2024-10-01',
        'expiry_date': '2034-09-23',
        'nameservers': [
            "PDNS80.ULTRADNS.BIZ",
            "PDNS80.ULTRADNS.COM",
            "PDNS80.ULTRADNS.NET",
            "PDNS80.ULTRADNS.ORG",
            "pdns80.ultradns.net",   # Duplicate in lowercase
            "pdns80.ultradns.com",   # Duplicate in lowercase
            "pdns80.ultradns.biz",   # Duplicate in lowercase
            "pdns80.ultradns.org"    # Duplicate in lowercase
        ],
        'status': ['clientTransferProhibited'],
        'last_checked': '2026-08-23T00:00:00'
    }

    new_data = {
        'registrar': 'TUCOWS.COM, CO.',
        'updated_date': '2024-10-01',
        'expiry_date': '2034-09-23',
        'nameservers': [
            # Only uppercase this time (python-whois inconsistency)
            "PDNS80.ULTRADNS.BIZ",
            "PDNS80.ULTRADNS.COM",
            "PDNS80.ULTRADNS.NET",
            "PDNS80.ULTRADNS.ORG"
        ],
        'status': ['clientTransferProhibited'],
        'last_checked': '2026-08-24T00:00:00'
    }

    changes = detect_whois_changes(old_data, new_data, 'realmadrid.com')

    # Should NOT detect nameservers_changed
    change_types = [c['type'] for c in changes]
    assert 'nameservers_changed' not in change_types


def test_detect_whois_changes_nameservers_real_change():
    """
    Actual nameserver changes should still be detected.
    """
    old_data = {
        'registrar': 'Example Registrar',
        'updated_date': '2024-01-01',
        'expiry_date': '2025-01-01',
        'nameservers': [
            "ns1.oldprovider.com",
            "ns2.oldprovider.com"
        ],
        'status': ['ok'],
        'last_checked': '2026-08-23T00:00:00'
    }

    new_data = {
        'registrar': 'Example Registrar',
        'updated_date': '2024-01-01',
        'expiry_date': '2025-01-01',
        'nameservers': [
            # Genuinely different servers
            "ns1.newprovider.com",
            "ns2.newprovider.com"
        ],
        'status': ['ok'],
        'last_checked': '2026-08-24T00:00:00'
    }

    changes = detect_whois_changes(old_data, new_data, 'example.com')

    # SHOULD detect nameservers_changed
    change_types = [c['type'] for c in changes]
    assert 'nameservers_changed' in change_types

    # Check details
    ns_change = next(c for c in changes if c['type'] == 'nameservers_changed')
    assert set(ns_change['added']) == {'ns1.newprovider.com', 'ns2.newprovider.com'}
    assert set(ns_change['removed']) == {'ns1.oldprovider.com', 'ns2.oldprovider.com'}


def test_detect_whois_changes_nameservers_partial_change():
    """
    Partial nameserver changes (add/remove one) should be detected correctly.
    """
    old_data = {
        'registrar': 'Example Registrar',
        'updated_date': '2024-01-01',
        'expiry_date': '2025-01-01',
        'nameservers': [
            "ns1.example.com",
            "ns2.example.com"
        ],
        'status': ['ok'],
        'last_checked': '2026-08-23T00:00:00'
    }

    new_data = {
        'registrar': 'Example Registrar',
        'updated_date': '2024-01-01',
        'expiry_date': '2025-01-01',
        'nameservers': [
            "ns1.example.com",   # Kept
            "ns2.example.com",   # Kept
            "ns3.example.com"    # Added
        ],
        'status': ['ok'],
        'last_checked': '2026-08-24T00:00:00'
    }

    changes = detect_whois_changes(old_data, new_data, 'example.com')

    # Should detect nameservers_changed
    change_types = [c['type'] for c in changes]
    assert 'nameservers_changed' in change_types

    # Check details
    ns_change = next(c for c in changes if c['type'] == 'nameservers_changed')
    assert ns_change['added'] == ['ns3.example.com']
    assert ns_change['removed'] == []
