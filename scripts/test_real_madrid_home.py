#!/usr/bin/env python3
"""
Test Real Madrid home page vs specific pages.
Determine if it's bot blocking or wrong paths.
"""

from __future__ import annotations

import requests
import re

USER_AGENT = 'Mozilla/5.0 (compatible; ZooomBot/1.0; +https://zooomsports.com/bot)'

tests = [
    {'url': 'https://www.realmadrid.com', 'label': 'Root (no language)'},
    {'url': 'https://www.realmadrid.com/es', 'label': 'Spanish home'},
    {'url': 'https://www.realmadrid.com/en', 'label': 'English home'},
    {'url': 'https://www.realmadrid.com/es/futbol/plantilla', 'label': 'Squad (current path)'},
    {'url': 'https://www.realmadrid.com/es/club/patrocinadores', 'label': 'Sponsors (current path)'},
]

print("\n" + "="*80)
print("REAL MADRID - BOT BLOCKING TEST")
print("="*80)
print(f"User-Agent: {USER_AGENT}\n")

results = []

for test in tests:
    url = test['url']
    label = test['label']

    print(f"\n[{label}]")
    print(f"URL: {url}")

    try:
        resp = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=15,
            allow_redirects=True
        )

        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else 'N/A'

        is_error = 'ERROR' in title.upper()

        status_icon = "[OK]" if not is_error else "[!]"
        print(f"  {status_icon} HTTP {resp.status_code}")
        print(f"      Title: {title}")
        print(f"      Size: {len(resp.text)} chars")
        print(f"      Redirects: {len(resp.history)}")

        results.append({
            'url': url,
            'label': label,
            'is_error': is_error,
            'title': title,
            'status_code': resp.status_code
        })

    except Exception as e:
        print(f"  [!] ERROR: {e}")
        results.append({
            'url': url,
            'label': label,
            'is_error': True,
            'title': 'EXCEPTION',
            'status_code': 0
        })

# Analysis
print("\n" + "="*80)
print("ANALYSIS")
print("="*80)

home_pages = [r for r in results if 'home' in r['label'].lower() or r['label'] == 'Root (no language)']
specific_pages = [r for r in results if 'Squad' in r['label'] or 'Sponsors' in r['label']]

home_errors = sum(1 for r in home_pages if r['is_error'])
specific_errors = sum(1 for r in specific_pages if r['is_error'])

print(f"\nHome pages: {len(home_pages)} tested, {home_errors} errors")
for r in home_pages:
    print(f"  {'[!]' if r['is_error'] else '[OK]'} {r['label']}: {r['title'][:60]}")

print(f"\nSpecific pages: {len(specific_pages)} tested, {specific_errors} errors")
for r in specific_pages:
    print(f"  {'[!]' if r['is_error'] else '[OK]'} {r['label']}: {r['title'][:60]}")

# Verdict
print("\n" + "="*80)
print("VERDICT")
print("="*80)

if home_errors == len(home_pages):
    print("\n[!] GENERALIZED BOT BLOCKING")
    print("    Even home pages return ERROR with ZooomBot User-Agent")
    print("    RECOMMENDATION: Disable site_monitoring_enabled for Real Madrid")
    print("    Reason: Bot blocking (WHOIS monitoring still works)")
elif specific_errors == len(specific_pages) and home_errors == 0:
    print("\n[!] SPECIFIC PAGE ERRORS (home works)")
    print("    Home pages work but squad/sponsors paths return ERROR")
    print("    RECOMMENDATION: Disable site_monitoring_enabled for Real Madrid")
    print("    Reason: Correct paths not found (structure may have changed)")
else:
    print("\n[?] MIXED RESULTS")
    print(f"    Home errors: {home_errors}/{len(home_pages)}")
    print(f"    Specific errors: {specific_errors}/{len(specific_pages)}")
    print("    Further investigation needed")

print("\n" + "="*80 + "\n")
