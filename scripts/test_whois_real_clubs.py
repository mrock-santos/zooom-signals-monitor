#!/usr/bin/env python3
"""
Test WhoisMonitor against real domains from clubs.yaml.
Validate that all 8 clubs return coherent WHOIS data.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from monitors.whois import WhoisMonitor

# Load clubs.yaml
clubs_config_path = project_root / "config" / "clubs.yaml"
with open(clubs_config_path, 'r', encoding='utf-8') as f:
    clubs_data = yaml.safe_load(f)

# Load sources.yaml for WHOIS config
sources_config_path = project_root / "config" / "sources.yaml"
with open(sources_config_path, 'r', encoding='utf-8') as f:
    sources_config = yaml.safe_load(f)

print("\n" + "="*80)
print("WHOIS MONITOR - REAL CLUBS VALIDATION")
print("="*80)
print(f"\nLoaded {len(clubs_data['clubs'])} clubs from clubs.yaml\n")

# Initialize monitor with config from sources.yaml
whois_config = sources_config['sources']['whois']
monitor = WhoisMonitor(whois_config)

results = []
errors = []

for club in clubs_data['clubs']:
    club_id = club['id']
    club_name = club['name']
    domains = club.get('domains', [])
    whois_enabled = club.get('whois_enabled', False)

    print(f"\n{'='*80}")
    print(f"{club_name} ({club_id})")
    print(f"{'='*80}")
    print(f"WHOIS enabled: {whois_enabled}")
    print(f"Domains: {domains}")

    if not whois_enabled:
        print("  [SKIP] WHOIS disabled for this club")
        continue

    for domain in domains:
        print(f"\n  Querying: {domain}")
        try:
            whois_data = monitor._check_domain(domain)

            if whois_data:
                # Check key fields
                has_registrar = bool(whois_data.get('registrar'))
                has_nameservers = bool(whois_data.get('nameservers'))
                has_expiry = bool(whois_data.get('expiry_date'))

                print(f"    [OK] WHOIS data retrieved")
                print(f"         Registrar: {whois_data.get('registrar', 'None')}")
                print(f"         Nameservers: {len(whois_data.get('nameservers', []))} entries")
                print(f"         Expiry date: {whois_data.get('expiry_date', 'None')}")
                print(f"         Status: {whois_data.get('status', 'None')}")

                # Summary
                if has_registrar and has_nameservers:
                    result_status = "COMPLETE"
                elif has_registrar or has_nameservers:
                    result_status = "PARTIAL"
                else:
                    result_status = "EMPTY"

                print(f"    >>> Result: {result_status}")

                results.append({
                    'club': club_name,
                    'domain': domain,
                    'status': result_status,
                    'registrar': whois_data.get('registrar'),
                    'nameservers_count': len(whois_data.get('nameservers', []))
                })

            else:
                print(f"    [!] No WHOIS data returned")
                errors.append(f"{club_name} - {domain}: No data returned")

        except Exception as e:
            print(f"    [!] ERROR: {e}")
            errors.append(f"{club_name} - {domain}: {str(e)}")

# Summary
print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

print(f"\nTotal clubs processed: {len(clubs_data['clubs'])}")
print(f"WHOIS queries executed: {len(results)}")

if results:
    complete = [r for r in results if r['status'] == 'COMPLETE']
    partial = [r for r in results if r['status'] == 'PARTIAL']
    empty = [r for r in results if r['status'] == 'EMPTY']

    print(f"\n[OK] COMPLETE data: {len(complete)}/{len(results)}")
    for r in complete:
        print(f"     - {r['club']}: {r['domain']} ({r['registrar']})")

    if partial:
        print(f"\n[?] PARTIAL data: {len(partial)}/{len(results)}")
        for r in partial:
            print(f"     - {r['club']}: {r['domain']}")

    if empty:
        print(f"\n[!] EMPTY data: {len(empty)}/{len(results)}")
        for r in empty:
            print(f"     - {r['club']}: {r['domain']}")

if errors:
    print(f"\n[!] ERRORS: {len(errors)}")
    for err in errors:
        print(f"     - {err}")

# Verdict
print("\n" + "="*80)
print("VERDICT")
print("="*80)

if not errors and len([r for r in results if r['status'] == 'COMPLETE']) >= len(results) * 0.8:
    print("\n[OK] WHOIS monitoring validated successfully")
    print(f"     {len([r for r in results if r['status'] == 'COMPLETE'])}/{len(results)} domains returned complete data")
    print("     Ready for production use")
else:
    print("\n[?] WHOIS monitoring needs review")
    if errors:
        print(f"     {len(errors)} errors encountered")
    complete_pct = len([r for r in results if r['status'] == 'COMPLETE']) / len(results) * 100 if results else 0
    print(f"     {complete_pct:.1f}% complete data rate")

print("\n" + "="*80 + "\n")
