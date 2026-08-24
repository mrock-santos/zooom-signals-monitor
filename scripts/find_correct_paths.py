#!/usr/bin/env python3
"""
Find correct paths for pages returning 404 or ERROR.
Test common path variations.
"""

from __future__ import annotations

import requests
import re

USER_AGENT = 'Mozilla/5.0 (compatible; ZooomBot/1.0; +https://zooomsports.com/bot)'

# Sites to investigate
sites = [
    {
        'club': 'Real Madrid',
        'base_url': 'https://www.realmadrid.com',
        'language': 'es',
        'tests': {
            'squad': [
                '/es/futbol/plantilla',  # Current (ERROR)
                '/es/primer-equipo/plantilla',
                '/es/futbol/primer-equipo',
                '/es/futbol/primer-equipo/plantilla',
                '/en/football/squad',
            ],
            'sponsors': [
                '/es/club/patrocinadores',  # Current (ERROR)
                '/es/el-club/patrocinadores',
                '/es/patrocinadores',
                '/en/the-club/sponsors',
            ]
        }
    },
    {
        'club': 'Athletico Paranaense',
        'base_url': 'https://www.athletico.com.br',
        'language': 'pt',
        'tests': {
            'sponsors': [
                '/parceiros',  # Current (404)
                '/patrocinadores',
                '/clube/parceiros',
                '/clube/patrocinadores',
                '/o-clube/parceiros',
            ]
        }
    },
    {
        'club': 'Santos',
        'base_url': 'https://www.santosfc.com.br',
        'language': 'pt',
        'tests': {
            'sponsors': [
                '/patrocinadores',  # Current (404)
                '/parceiros',
                '/clube/patrocinadores',
                '/clube/parceiros',
                '/o-clube/patrocinadores',
            ]
        }
    }
]

print("\n" + "="*80)
print("FIND CORRECT PATHS")
print("="*80)

findings = {}

for site in sites:
    club = site['club']
    base_url = site['base_url']

    print(f"\n{'='*80}")
    print(f"{club}")
    print(f"{'='*80}")

    findings[club] = {}

    for category, paths in site['tests'].items():
        print(f"\n[{category.upper()}]")

        found = False

        for path in paths:
            full_url = base_url + path

            try:
                resp = requests.get(
                    full_url,
                    headers={'User-Agent': USER_AGENT},
                    timeout=10,
                    allow_redirects=True
                )

                # Extract title
                title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text, re.IGNORECASE | re.DOTALL)
                title = title_match.group(1).strip()[:80] if title_match else 'N/A'

                # Check for error indicators
                is_error = (
                    'ERROR' in title.upper() or
                    '404' in title or
                    'NOT FOUND' in title.upper() or
                    resp.status_code >= 400
                )

                # Check for relevant keywords
                html_lower = resp.text.lower()
                has_squad = 'plantilla' in html_lower or 'elenco' in html_lower or 'squad' in html_lower
                has_sponsors = 'patrocinador' in html_lower or 'sponsor' in html_lower or 'parceiro' in html_lower

                status_icon = "[OK]" if resp.status_code == 200 and not is_error else "[!]"
                content_match = (category == 'squad' and has_squad) or (category == 'sponsors' and has_sponsors)
                content_icon = "[MATCH]" if content_match else "[miss]"

                print(f"  {status_icon} {full_url}")
                print(f"      HTTP {resp.status_code} | Redirects: {len(resp.history)}")
                print(f"      Title: {title}")
                print(f"      Keywords: squad={has_squad}, sponsors={has_sponsors} {content_icon}")

                if resp.status_code == 200 and not is_error:
                    if (category == 'squad' and has_squad) or (category == 'sponsors' and has_sponsors):
                        print(f"      >>> FOUND WORKING PATH")
                        findings[club][category] = {
                            'path': path,
                            'title': title,
                            'status': 'OK'
                        }
                        found = True
                        break

            except requests.RequestException as e:
                print(f"  [!] {full_url}")
                print(f"      ERROR: {e}")

        if not found:
            print(f"\n  [!] No working path found for {category}")
            findings[club][category] = {'status': 'NOT_FOUND'}

# Summary
print("\n" + "="*80)
print("FINDINGS SUMMARY")
print("="*80)

for club, categories in findings.items():
    print(f"\n{club}:")
    for category, result in categories.items():
        if result['status'] == 'OK':
            print(f"  {category}: {result['path']}")
            print(f"    Title: {result['title']}")
        else:
            print(f"  {category}: NOT FOUND")

print("\n" + "="*80 + "\n")
