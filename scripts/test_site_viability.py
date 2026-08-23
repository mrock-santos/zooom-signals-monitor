#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test site monitoring viability before enabling.

Checks:
- Can fetch pages without 403/429?
- Hash stable across multiple requests?
- Response time <15s?

Run LOCAL only, after robots.txt validation passes.
"""

import sys
import time
import hashlib
import requests
from bs4 import BeautifulSoup

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


TEST_SITES = [
    ('https://www.flamengo.com.br/elenco', 'Flamengo - Elenco'),
    ('https://www.realmadrid.com/en/football/squad', 'Real Madrid - Squad'),
]

USER_AGENT = 'Mozilla/5.0 (compatible; ZooomBot/1.0; +https://zooomsports.com/bot)'


def hash_content(html: str) -> str:
    """Hash normalized content."""
    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup(['script', 'style', 'noscript', 'iframe']):
        tag.decompose()

    text = soup.get_text(separator=' ', strip=True)
    text = ' '.join(text.split())

    return hashlib.md5(text.encode('utf-8')).hexdigest()


def test_site(url: str, label: str):
    """Test one site for viability."""
    print(f"\n{'='*60}")
    print(f"Testing: {label}")
    print(f"URL: {url}")
    print('='*60)

    try:
        # First fetch
        start = time.time()
        resp1 = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=15)
        elapsed1 = time.time() - start

        if resp1.status_code != 200:
            print(f"❌ HTTP {resp1.status_code}")
            return False

        hash1 = hash_content(resp1.text)
        print(f"✅ First fetch: {elapsed1:.2f}s, hash={hash1[:12]}...")

        # Wait before second fetch
        time.sleep(5)

        # Second fetch (verify hash stability)
        start = time.time()
        resp2 = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=15)
        elapsed2 = time.time() - start

        hash2 = hash_content(resp2.text)
        print(f"✅ Second fetch: {elapsed2:.2f}s, hash={hash2[:12]}...")

        if hash1 == hash2:
            print(f"✅ Hash STABLE (no dynamic content leaking)")
        else:
            print(f"⚠️  Hash CHANGED between requests")
            print(f"   This may indicate dynamic content not being filtered")
            print(f"   Review _hash_content() logic")

        if elapsed1 > 15 or elapsed2 > 15:
            print(f"⚠️  Slow response (>{elapsed1:.1f}s or {elapsed2:.1f}s)")

        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code in (403, 429):
            print(f"❌ BLOCKED: HTTP {e.response.status_code}")
            print(f"   robots.txt may allow, but server blocks User-Agent")
        else:
            print(f"❌ HTTP Error: {e}")
        return False

    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT (>15s)")
        return False

    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("SITE MONITORING VIABILITY TEST")
    print("="*60)
    print(f"\nTesting {len(TEST_SITES)} sites")
    print("⚠️  Run LOCAL only")
    print("⚠️  Assumes robots.txt validation already passed\n")

    results = []
    for url, label in TEST_SITES:
        success = test_site(url, label)
        results.append((label, success))
        time.sleep(3)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)

    success_count = sum(1 for _, ok in results if ok)
    print(f"✅ Successful: {success_count}/{len(results)}")
    print(f"❌ Failed: {len(results) - success_count}/{len(results)}")

    if success_count == len(results):
        print(f"\n✅ SITE MONITORING is VIABLE")
        print(f"\n📝 Next step: Enable in config/sources.yaml:")
        print(f"   sources:")
        print(f"     site_monitoring:")
        print(f"       enabled: true")
    else:
        print(f"\n❌ SITE MONITORING has ISSUES")
        failed = [label for label, ok in results if not ok]
        print(f"   Failed sites: {', '.join(failed)}")
        print(f"\n📝 Next step: Leave disabled, document issue")


if __name__ == '__main__':
    main()
