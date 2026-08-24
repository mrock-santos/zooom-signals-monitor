#!/usr/bin/env python3
"""
Validate robots.txt for all 8 proposed official sites.
"""

import subprocess
import sys
from pathlib import Path

# 8 proposed official sites
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

print("\n" + "=" * 100)
print("ROBOTS.TXT VALIDATION - 8 Proposed Official Sites")
print("=" * 100)
print(f"\nValidating {len(sites)} sites...\n")

results = []

for club_name, url in sites:
    print(f"Checking: {club_name:<25} {url}")

    # Run check_robots_txt.py
    try:
        result = subprocess.run(
            [sys.executable, "scripts/check_robots_txt.py", "--url", url],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )

        # Parse output
        output = result.stdout
        if "allowed: True" in output or "allowed=True" in output:
            status = "ALLOWED"
            flag = "[OK]"
        elif "allowed: False" in output or "allowed=False" in output:
            status = "BLOCKED"
            flag = "[!]"
        elif "error" in output.lower():
            status = "ERROR"
            flag = "[?]"
        else:
            status = "UNKNOWN"
            flag = "[?]"

        results.append((club_name, url, status, flag, output))
        print(f"  {flag} {status}")

    except subprocess.TimeoutExpired:
        results.append((club_name, url, "TIMEOUT", "[?]", "Timeout after 30s"))
        print(f"  [?] TIMEOUT")
    except Exception as e:
        results.append((club_name, url, "ERROR", "[?]", str(e)))
        print(f"  [?] ERROR: {e}")

# Summary
print("\n" + "=" * 100)
print("VALIDATION SUMMARY")
print("=" * 100)

allowed = [r for r in results if r[2] == "ALLOWED"]
blocked = [r for r in results if r[2] == "BLOCKED"]
errors = [r for r in results if r[2] in ["ERROR", "TIMEOUT", "UNKNOWN"]]

print(f"\n[OK] ALLOWED:  {len(allowed)} sites")
for club_name, url, *_ in allowed:
    print(f"     - {club_name}: {url}")

if blocked:
    print(f"\n[!] BLOCKED:   {len(blocked)} sites (REMOVE FROM MONITORING)")
    for club_name, url, *_ in blocked:
        print(f"     - {club_name}: {url}")

if errors:
    print(f"\n[?] ERRORS:    {len(errors)} sites (MANUAL REVIEW REQUIRED)")
    for club_name, url, status, *_ in errors:
        print(f"     - {club_name}: {url} ({status})")

# Recommendation
print("\n" + "=" * 100)
print("RECOMMENDATION")
print("=" * 100)

if blocked:
    print(f"\n[!] DISABLE site_monitoring for these clubs:")
    for club_name, *_ in blocked:
        print(f"    - {club_name}: set site_monitoring_enabled: false")

if errors:
    print(f"\n[?] MANUAL REVIEW needed for these clubs:")
    for club_name, url, *_ in errors:
        print(f"    - {club_name}: Check {url} manually")

if not blocked and not errors:
    print(f"\n[OK] ALL {len(allowed)} sites allow crawling!")
    print(f"     Safe to enable site_monitoring for all clubs.")

print("=" * 100 + "\n")
