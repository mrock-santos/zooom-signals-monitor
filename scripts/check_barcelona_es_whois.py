#!/usr/bin/env python3
"""
Check if fcbarcelona.es has same WHOIS blocking as realmadrid.es.
Red.es IP whitelist restriction.
"""

from __future__ import annotations

import whois

domain = "fcbarcelona.es"

print("\n" + "="*80)
print(f"WHOIS CHECK - {domain}")
print("="*80 + "\n")

try:
    w = whois.whois(domain)

    # Check if raw text exists
    has_raw_text = hasattr(w, 'text') and w.text and len(w.text) > 0

    print(f"Raw text available: {has_raw_text}")
    if has_raw_text:
        print(f"Raw text length: {len(w.text)} chars\n")

        # Check for Red.es restriction message
        if 'Red.es' in w.text or 'IP addresses authorised' in w.text:
            print("[!] RED.ES RESTRICTION DETECTED")
            print("\nFirst 500 chars of WHOIS response:")
            print("-"*80)
            print(w.text[:500])
            print("-"*80)
        else:
            print("[?] Raw text exists but no Red.es restriction message found")
            print("\nFirst 300 chars:")
            print("-"*80)
            print(w.text[:300])
            print("-"*80)

    # Check parsed fields
    print("\nPARSED FIELDS:")
    print(f"  domain_name: {w.domain_name}")
    print(f"  registrar: {w.registrar}")
    print(f"  name_servers: {w.name_servers}")
    print(f"  status: {w.status}")
    print(f"  expiration_date: {w.expiration_date}")

    # Verdict
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)

    if not w.registrar and not w.name_servers:
        if has_raw_text and ('Red.es' in w.text or 'IP addresses authorised' in w.text):
            print("\n[!] BLOCKED BY RED.ES")
            print("    Same issue as realmadrid.es")
            print("    RECOMMENDATION: Remove fcbarcelona.es from domains list")
        else:
            print("\n[?] EMPTY FIELDS")
            print("    Registrar and nameservers are None/empty")
            print("    But Red.es message not detected in raw text")
            print("    RECOMMENDATION: Remove anyway (no useful data)")
    else:
        print("\n[OK] WHOIS DATA AVAILABLE")
        print(f"    Registrar: {w.registrar}")
        print(f"    Nameservers: {len(w.name_servers or [])} entries")

except Exception as e:
    print(f"[!] ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80 + "\n")
