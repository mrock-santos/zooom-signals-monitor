#!/usr/bin/env python3
"""
Investigate identical hashes for Real Madrid and Flamengo.
Check for redirects, page content, and path correctness.
"""

from __future__ import annotations

import requests
from hashlib import md5

# Clubs with identical hashes
investigations = [
    {
        'club': 'Real Madrid',
        'base_url': 'https://www.realmadrid.com',
        'pages': [
            {'path': '/es/futbol/plantilla', 'label': 'Plantilla (Squad)'},
            {'path': '/es/club/patrocinadores', 'label': 'Patrocinadores (Sponsors)'},
        ],
        'expected_hash': 'b3e69ecff7be1b1ef4de1a4e37215139'
    },
    {
        'club': 'Flamengo',
        'base_url': 'https://www.flamengo.com.br',
        'pages': [
            {'path': '/elenco', 'label': 'Elenco (Squad)'},
            {'path': '/patrocinadores', 'label': 'Patrocinadores (Sponsors)'},
        ],
        'expected_hash': 'da5aa53c8b9535ebc04f3813a34cbedd'
    }
]

USER_AGENT = 'Mozilla/5.0 (compatible; ZooomBot/1.0; +https://zooomsports.com/bot)'

print("\n" + "="*80)
print("IDENTICAL HASH INVESTIGATION")
print("="*80)

for inv in investigations:
    club = inv['club']
    base_url = inv['base_url']

    print(f"\n{'='*80}")
    print(f"{club}")
    print(f"{'='*80}")

    results = []

    for page in inv['pages']:
        path = page['path']
        label = page['label']
        full_url = base_url + path

        print(f"\n[{label}]")
        print(f"URL: {full_url}")

        try:
            # Fetch with redirect tracking
            response = requests.get(
                full_url,
                headers={'User-Agent': USER_AGENT},
                timeout=15,
                allow_redirects=True
            )

            # Check for redirects
            redirect_count = len(response.history)
            final_url = response.url

            print(f"  HTTP Status: {response.status_code}")
            print(f"  Redirects: {redirect_count}")

            if redirect_count > 0:
                print(f"  [!] REDIRECT DETECTED")
                print(f"      Original: {full_url}")
                print(f"      Final:    {final_url}")
                for i, r in enumerate(response.history, 1):
                    print(f"      Step {i}: {r.status_code} {r.url} -> {r.headers.get('Location', 'N/A')}")

            # Content analysis
            html = response.text
            content_hash = md5(html.encode('utf-8')).hexdigest()

            print(f"  Content size: {len(html)} chars")
            print(f"  MD5 hash: {content_hash}")

            # Extract title tag
            import re
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else 'N/A'
            print(f"  <title>: {title[:100]}")

            # Check for specific keywords
            has_squad = 'plantilla' in html.lower() or 'elenco' in html.lower() or 'jugadores' in html.lower()
            has_sponsors = 'patrocinador' in html.lower() or 'sponsor' in html.lower() or 'parceiro' in html.lower()

            print(f"  Keywords: squad={has_squad}, sponsors={has_sponsors}")

            results.append({
                'path': path,
                'label': label,
                'final_url': final_url,
                'redirected': redirect_count > 0,
                'hash': content_hash,
                'title': title,
                'has_squad': has_squad,
                'has_sponsors': has_sponsors,
            })

        except Exception as e:
            print(f"  [!] ERROR: {e}")

    # Compare results
    print(f"\n{'-'*80}")
    print("COMPARISON")
    print(f"{'-'*80}")

    if len(results) == 2:
        r1, r2 = results

        print(f"\nPage 1: {r1['label']}")
        print(f"  Hash: {r1['hash']}")
        print(f"  Redirected: {r1['redirected']}")
        print(f"  Final URL: {r1['final_url']}")

        print(f"\nPage 2: {r2['label']}")
        print(f"  Hash: {r2['hash']}")
        print(f"  Redirected: {r2['redirected']}")
        print(f"  Final URL: {r2['final_url']}")

        # Verdict
        if r1['hash'] == r2['hash']:
            print(f"\n[!] HASHES ARE IDENTICAL")

            if r1['final_url'] == r2['final_url']:
                print("    >>> Both paths redirect to THE SAME URL")
                print(f"        Final: {r1['final_url']}")
            else:
                print("    >>> Different final URLs but SAME CONTENT")
                print("        This suggests:")
                print("        - Pages have identical structure/template")
                print("        - OR pages serve same generic content")
                print("        - OR one path doesn't exist and falls back to homepage")
        else:
            print(f"\n[OK] HASHES ARE DIFFERENT")
            print(f"    Page 1: {r1['hash']}")
            print(f"    Page 2: {r2['hash']}")

        # Content analysis
        print(f"\nCONTENT INDICATORS:")
        print(f"  {r1['label']}: squad={r1['has_squad']}, sponsors={r1['has_sponsors']}")
        print(f"  {r2['label']}: squad={r2['has_squad']}, sponsors={r2['has_sponsors']}")

print("\n" + "="*80 + "\n")
