#!/usr/bin/env python3
"""
Test WHOIS consistency for the same domain queried multiple times.
Check if registrar/nameservers formatting changes between queries.
"""

from __future__ import annotations

import whois
import time

domain = "realmadrid.com"
queries = 3
delay = 2  # seconds between queries

print("\n" + "="*80)
print(f"WHOIS CONSISTENCY TEST - {domain}")
print("="*80)
print(f"Queries: {queries} (with {delay}s delay)\n")

results = []

for i in range(queries):
    print(f"Query {i+1}/{queries}:")

    try:
        w = whois.whois(domain)

        registrar = w.registrar
        nameservers = w.name_servers or []

        # Normalize nameservers to uppercase for comparison
        ns_normalized = sorted([ns.upper() for ns in nameservers])

        print(f"  Registrar: {registrar}")
        print(f"  Nameservers: {len(nameservers)} entries")
        print(f"    {ns_normalized[:4]}")  # First 4

        results.append({
            'query': i+1,
            'registrar': registrar,
            'nameservers': ns_normalized
        })

    except Exception as e:
        print(f"  ERROR: {e}")

    if i < queries - 1:
        print(f"  Waiting {delay}s...")
        time.sleep(delay)
    print()

# Compare results
print("="*80)
print("COMPARISON")
print("="*80 + "\n")

if len(results) < 2:
    print("Not enough successful queries to compare")
else:
    # Check registrar consistency
    registrars = [r['registrar'] for r in results]
    registrar_unique = list(set(registrars))

    print(f"Registrar values:")
    for i, r in enumerate(results, 1):
        print(f"  Query {i}: {r['registrar']}")

    if len(registrar_unique) == 1:
        print(f"\n[OK] Registrar CONSISTENT across all queries")
    else:
        print(f"\n[!] Registrar INCONSISTENT!")
        print(f"    Found {len(registrar_unique)} different values:")
        for val in registrar_unique:
            print(f"      - {val}")

    # Check nameservers consistency
    print(f"\nNameservers:")
    first_ns = results[0]['nameservers']
    all_same = all(r['nameservers'] == first_ns for r in results)

    for i, r in enumerate(results, 1):
        match = "MATCH" if r['nameservers'] == first_ns else "DIFF"
        print(f"  Query {i}: {len(r['nameservers'])} entries [{match}]")

    if all_same:
        print(f"\n[OK] Nameservers CONSISTENT across all queries")
    else:
        print(f"\n[!] Nameservers INCONSISTENT!")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)

if len(results) >= 2:
    if len(registrar_unique) > 1:
        print("\n[!] WHOIS INCONSISTENCY DETECTED")
        print("    The python-whois library returns different registrar")
        print("    strings for the same domain queried multiple times.")
        print("\n    This causes FALSE POSITIVES in change detection:")
        print("    - First query saves baseline")
        print("    - Second query returns different format")
        print("    - System detects as 'registrar_changed'")
        print("\n    SOLUTION: Normalize registrar strings before comparison")
        print("              OR accept that registrar format may vary")
    else:
        print("\n[OK] WHOIS DATA CONSISTENT")
        print("    Same domain returns same data across queries")

print("\n" + "="*80 + "\n")
