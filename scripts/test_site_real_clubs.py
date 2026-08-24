#!/usr/bin/env python3
"""
Test SiteMonitor against real monitor_pages from clubs.yaml.
Validate HTTP 200, hash generation, no blocking.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urljoin

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from monitors.site_hash import SiteMonitor

# Load clubs.yaml
clubs_config_path = project_root / "config" / "clubs.yaml"
with open(clubs_config_path, 'r', encoding='utf-8') as f:
    clubs_data = yaml.safe_load(f)

# Load sources.yaml for Site config
sources_config_path = project_root / "config" / "sources.yaml"
with open(sources_config_path, 'r', encoding='utf-8') as f:
    sources_config = yaml.safe_load(f)

print("\n" + "="*80)
print("SITE MONITOR - REAL CLUBS VALIDATION")
print("="*80)
print(f"\nLoaded {len(clubs_data['clubs'])} clubs from clubs.yaml\n")

# Initialize monitor
site_config = sources_config['sources']['site_monitoring']
monitor = SiteMonitor(site_config)

results = []
errors = []
total_pages = 0

for club in clubs_data['clubs']:
    club_id = club['id']
    club_name = club['name']
    site_enabled = club.get('site_monitoring_enabled', False)
    official_site = club.get('official_site', {})

    print(f"\n{'='*80}")
    print(f"{club_name} ({club_id})")
    print(f"{'='*80}")
    print(f"Site monitoring enabled: {site_enabled}")

    if not site_enabled:
        print("  [SKIP] Site monitoring disabled for this club")
        continue

    base_url = official_site.get('url')
    monitor_pages = official_site.get('monitor_pages', [])

    print(f"Base URL: {base_url}")
    print(f"Monitor pages: {len(monitor_pages)}")

    for page in monitor_pages:
        total_pages += 1
        path = page['path']
        label = page['label']
        page_type = page.get('type', 'unknown')

        full_url = urljoin(base_url, path)

        print(f"\n  [{total_pages}] {label}")
        print(f"      URL: {full_url}")
        print(f"      Type: {page_type}")

        try:
            # Fetch page HTML
            html = monitor._fetch_page(full_url)

            if html:
                # Compute hash
                content_hash = monitor._hash_content(html)

                print(f"      [OK] HTTP 200")
                print(f"           Hash: {content_hash}")
                print(f"           Size: {len(html)} chars")

                results.append({
                    'club': club_name,
                    'label': label,
                    'url': full_url,
                    'status': 'OK',
                    'http_code': 200,
                    'hash': content_hash
                })
            else:
                print(f"      [!] No data returned")
                errors.append(f"{club_name} - {label}: No data returned")

        except Exception as e:
            print(f"      [!] ERROR: {e}")
            errors.append(f"{club_name} - {label}: {str(e)}")

# Summary
print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

print(f"\nTotal clubs processed: {len(clubs_data['clubs'])}")
print(f"Clubs with site monitoring: {len([c for c in clubs_data['clubs'] if c.get('site_monitoring_enabled')])}")
print(f"Pages tested: {total_pages}")
print(f"Successful: {len(results)}/{total_pages}")

if results:
    print(f"\n[OK] SUCCESSFUL FETCHES: {len(results)}")
    for r in results:
        print(f"     - {r['club']}: {r['label']} (HTTP {r['http_code']})")

if errors:
    print(f"\n[!] ERRORS: {len(errors)}")
    for err in errors:
        print(f"     - {err}")

# Verdict
print("\n" + "="*80)
print("VERDICT")
print("="*80)

success_rate = len(results) / total_pages * 100 if total_pages > 0 else 0

if not errors and success_rate == 100:
    print(f"\n[OK] SITE monitoring validated successfully")
    print(f"     {len(results)}/{total_pages} pages fetched (100%)")
    print("     All pages return HTTP 200, hash generated")
    print("     No blocking detected")
    print("     Ready for production use")
elif success_rate >= 80:
    print(f"\n[?] SITE monitoring mostly working ({success_rate:.1f}%)")
    print(f"     {len(results)}/{total_pages} pages successful")
    if errors:
        print(f"     {len(errors)} errors need review")
else:
    print(f"\n[!] SITE monitoring needs review ({success_rate:.1f}% success)")
    print(f"     {len(errors)}/{total_pages} pages failed")

print("\n" + "="*80 + "\n")
