#!/usr/bin/env python3
"""
Inspect raw WHOIS response for realmadrid.es to check if it's a parsing issue.
"""

import whois

domain = "realmadrid.es"

print(f"\n{'='*80}")
print(f"RAW WHOIS INSPECTION - {domain}")
print('='*80 + "\n")

try:
    w = whois.whois(domain)

    # Print raw text response
    print("RAW WHOIS TEXT:")
    print("-"*80)
    if hasattr(w, 'text') and w.text:
        print(w.text)
    else:
        print("(no raw text available)")

    print("\n" + "-"*80)
    print("PARSED FIELDS:")
    print("-"*80)
    print(f"domain_name: {w.domain_name}")
    print(f"registrar: {w.registrar}")
    print(f"name_servers: {w.name_servers}")
    print(f"status: {w.status}")
    print(f"updated_date: {w.updated_date}")
    print(f"expiration_date: {w.expiration_date}")

    # Full object dump
    print("\n" + "-"*80)
    print("FULL OBJECT ATTRIBUTES:")
    print("-"*80)
    for attr in dir(w):
        if not attr.startswith('_'):
            val = getattr(w, attr, None)
            if not callable(val):
                print(f"{attr}: {val}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80 + "\n")
