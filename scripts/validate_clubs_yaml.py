#!/usr/bin/env python3
"""
Validate clubs.yaml syntax and structure.
"""

import yaml
from pathlib import Path

yaml_path = Path(__file__).parent.parent / "config" / "clubs.yaml"

print("\n" + "="*80)
print("CLUBS.YAML VALIDATION")
print("="*80 + "\n")

print(f"File: {yaml_path}")
print(f"Exists: {yaml_path.exists()}\n")

try:
    # Load YAML
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    print("[OK] YAML syntax is valid\n")

    # Structure checks
    if 'clubs' not in data:
        print("[!] ERROR: Missing 'clubs' key")
        exit(1)

    clubs = data['clubs']
    print(f"[OK] Found {len(clubs)} clubs\n")

    # Validate each club
    required_fields = ['id', 'name', 'league', 'country', 'domains', 'official_site',
                      'trends_keywords', 'whois_enabled', 'site_monitoring_enabled']

    errors = []

    for i, club in enumerate(clubs, 1):
        club_id = club.get('id', f'<club #{i}>')

        # Check required fields
        missing = [f for f in required_fields if f not in club]
        if missing:
            errors.append(f"  {club_id}: Missing fields: {', '.join(missing)}")

        # Check domains list not empty
        if 'domains' in club and not club['domains']:
            errors.append(f"  {club_id}: domains list is empty")

        # Check official_site structure
        if 'official_site' in club:
            site = club['official_site']
            if 'url' not in site:
                errors.append(f"  {club_id}: official_site missing 'url'")
            if 'monitor_pages' not in site:
                errors.append(f"  {club_id}: official_site missing 'monitor_pages'")
            elif not site['monitor_pages']:
                errors.append(f"  {club_id}: monitor_pages list is empty")

    if errors:
        print("[!] VALIDATION ERRORS:")
        for err in errors:
            print(err)
        exit(1)
    else:
        print("[OK] All clubs have required fields")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    whois_enabled = sum(1 for c in clubs if c.get('whois_enabled'))
    site_enabled = sum(1 for c in clubs if c.get('site_monitoring_enabled'))

    print(f"\nTotal clubs: {len(clubs)}")
    print(f"WHOIS enabled: {whois_enabled}/{len(clubs)}")
    print(f"Site monitoring enabled: {site_enabled}/{len(clubs)}")

    # Country distribution
    from collections import Counter
    countries = Counter(c.get('country') for c in clubs)
    print(f"\nCountry distribution:")
    for country, count in countries.most_common():
        print(f"  - {country}: {count} clubs")

    print("\n" + "="*80)
    print("[OK] VALIDATION PASSED")
    print("="*80 + "\n")

except yaml.YAMLError as e:
    print(f"[!] YAML SYNTAX ERROR:\n{e}")
    exit(1)
except Exception as e:
    print(f"[!] ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
