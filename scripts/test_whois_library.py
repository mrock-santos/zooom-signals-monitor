#!/usr/bin/env python3
"""
Test python-whois library for .com vs .es TLDs.
"""

import whois

domains = {
    "realmadrid.com": ".com (should work)",
    "realmadrid.es": ".es (reported as empty)",
}

print("\n" + "="*80)
print("WHOIS LIBRARY TEST - .com vs .es")
print("="*80 + "\n")

for domain, desc in domains.items():
    print(f"\n{domain} ({desc})")
    print("-"*80)

    try:
        w = whois.whois(domain)

        # Check if we got ANY data
        has_data = any([
            w.registrar,
            w.name_servers,
            w.status,
            w.updated_date,
            w.expiration_date,
        ])

        if has_data:
            print("[OK] WHOIS data retrieved:")
            print(f"  Registrar: {w.registrar}")
            print(f"  Nameservers: {w.name_servers}")
            print(f"  Status: {w.status}")
        else:
            print("[!] NO WHOIS DATA - All fields empty/None")
            print(f"  Registrar: {w.registrar}")
            print(f"  Nameservers: {w.name_servers}")
            print(f"  Raw text length: {len(w.text) if w.text else 0} chars")

            # Check if raw text exists but parsing failed
            if w.text and len(w.text) > 0:
                print("\n  [!] Raw WHOIS text EXISTS but parsing FAILED")
                print("      First 500 chars:")
                print("      " + "-"*76)
                print("      " + w.text[:500].replace("\n", "\n      "))
            else:
                print("\n  [!] No raw WHOIS text - query may have failed or been blocked")

    except Exception as e:
        print(f"[!] ERROR: {e}")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print("""
HYPOTHESIS:
- If .com works but .es returns empty: TLD-specific issue
  → Either python-whois doesn't support .es parsing
  → Or .es registry blocks/redacts WHOIS data (GDPR/privacy)

IMPLICATION FOR MONITORING:
- If .es WHOIS is genuinely empty: monitoring it wastes API calls
  → No change detection possible (always empty = no signal)
  → RECOMMENDATION: Remove realmadrid.es from domains list
""")
print("="*80 + "\n")
