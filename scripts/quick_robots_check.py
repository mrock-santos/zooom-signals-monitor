#!/usr/bin/env python3
"""Quick robots.txt check without emoji issues."""

import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin

sites = [
    ("Real Madrid", "https://www.realmadrid.com"),
    ("Athletico Paranaense", "https://www.athletico.com.br"),
    ("Corinthians", "https://www.corinthians.com.br"),
    ("Grêmio", "https://gremio.net"),
    ("Santos", "https://www.santosfc.com.br"),
    ("Palmeiras", "https://www.palmeiras.com.br"),
    ("Barcelona", "https://www.fcbarcelona.com"),
    ("Flamengo", "https://www.flamengo.com.br"),
]

USER_AGENT = "Mozilla/5.0 (compatible; ZooomBot/1.0; +https://zooomsports.com/bot)"

print("\n" + "="*80)
print("ROBOTS.TXT VALIDATION - 8 Sites")
print("="*80 + "\n")

results = []

for club_name, url in sites:
    robots_url = urljoin(url, '/robots.txt')

    try:
        # Fetch robots.txt
        response = requests.get(robots_url, timeout=10, headers={'User-Agent': USER_AGENT})

        if response.status_code == 404:
            # 404 = no robots.txt = allowed by default
            result = "ALLOWED"
            detail = "404 (no robots.txt, default allow)"
        elif response.status_code == 200:
            # Parse robots.txt
            rp = RobotFileParser()
            rp.parse(response.text.splitlines())

            # Check if our user agent can fetch the root
            can_fetch = rp.can_fetch(USER_AGENT, url)

            if can_fetch:
                result = "ALLOWED"
                detail = "200 (parsed, allowed)"
            else:
                result = "BLOCKED"
                detail = "200 (parsed, BLOCKED)"
        else:
            # Other status codes = manual review
            result = "ERROR"
            detail = f"HTTP {response.status_code}"

    except requests.Timeout:
        result = "ERROR"
        detail = "Timeout"
    except Exception as e:
        result = "ERROR"
        detail = str(e)[:50]

    results.append((club_name, url, result, detail))

    status_mark = "[OK]" if result == "ALLOWED" else "[!]" if result == "BLOCKED" else "[?]"
    print(f"{status_mark} {club_name:<25} {result:<10} {detail}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

allowed = [r for r in results if r[2] == "ALLOWED"]
blocked = [r for r in results if r[2] == "BLOCKED"]
errors = [r for r in results if r[2] == "ERROR"]

print(f"\n[OK] ALLOWED: {len(allowed)}/8 sites")
if blocked:
    print(f"[!] BLOCKED:  {len(blocked)}/8 sites - DISABLE site_monitoring")
    for name, *_ in blocked:
        print(f"    - {name}")
if errors:
    print(f"[?] ERRORS:   {len(errors)}/8 sites - Manual review needed")
    for name, url, _, detail in errors:
        print(f"    - {name}: {detail}")

print("\n" + "="*80 + "\n")
