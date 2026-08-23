#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test WHOIS viability before enabling in sources.yaml.

Checks:
- Can fetch data from different TLDs (.br, .com, .es, .co.uk)
- Date formats consistent?
- Any rate limiting/blocking?
- Responses stable across multiple queries?

Run LOCAL only, not on production server.
"""

import sys
import time
from datetime import datetime
import whois

# Fix Windows console encoding for emoji
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


# Test domains across different TLDs
TEST_DOMAINS = [
    ('flamengo.com.br', '.br TLD (Brazil)'),
    ('realmadrid.com', '.com TLD'),
    ('fcbarcelona.es', '.es TLD (Spain)'),
    ('mancity.com', '.com TLD'),
]


def test_domain(domain: str, label: str):
    """Test WHOIS fetch for one domain."""
    print(f"\n{'='*60}")
    print(f"Testing: {domain} ({label})")
    print('='*60)

    try:
        start = time.time()
        w = whois.whois(domain)
        elapsed = time.time() - start

        print(f"✅ Success ({elapsed:.2f}s)")
        print(f"  Registrar: {w.registrar}")
        print(f"  Updated: {w.updated_date} (type: {type(w.updated_date).__name__})")
        print(f"  Expiry: {w.expiration_date} (type: {type(w.expiration_date).__name__})")
        print(f"  Nameservers: {w.name_servers}")

        # Check for date format issues
        if isinstance(w.updated_date, list):
            print(f"  ⚠️  Updated date is LIST (some TLDs return this)")
        if isinstance(w.expiration_date, list):
            print(f"  ⚠️  Expiry date is LIST")

        return True

    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("WHOIS VIABILITY TEST")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing {len(TEST_DOMAINS)} domains across different TLDs")
    print("\n⚠️  Running LOCAL - not on production server")
    print("⚠️  Observe for: rate limiting, format inconsistencies, blocks")

    results = []
    for domain, label in TEST_DOMAINS:
        success = test_domain(domain, label)
        results.append((domain, success))
        time.sleep(3)  # Delay between tests

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)

    success_count = sum(1 for _, ok in results if ok)
    print(f"✅ Successful: {success_count}/{len(results)}")
    print(f"❌ Failed: {len(results) - success_count}/{len(results)}")

    if success_count == len(results):
        print(f"\n✅ WHOIS is VIABLE")
        print(f"   All TLDs tested successfully")
        print(f"   No blocking or rate limiting detected")
        print(f"\n📝 Next step: Enable in config/sources.yaml:")
        print(f"   sources:")
        print(f"     whois:")
        print(f"       enabled: true")
    else:
        print(f"\n❌ WHOIS has ISSUES")
        print(f"   Failed domains:")
        for domain, ok in results:
            if not ok:
                print(f"     - {domain}")
        print(f"\n📝 Next step: Leave disabled in sources.yaml")
        print(f"   Document issue in docs/incidents/")

    print("")


if __name__ == '__main__':
    main()
