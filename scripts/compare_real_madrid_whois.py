#!/usr/bin/env python3
"""
Compare WHOIS data for realmadrid.com vs realmadrid.es.
Check if they are different enough to justify monitoring both.
"""

import whois

domains = [
    "realmadrid.com",
    "realmadrid.es"
]

print("\n" + "="*80)
print("WHOIS COMPARISON - realmadrid.com vs realmadrid.es")
print("="*80 + "\n")

whois_data = {}

for domain in domains:
    print(f"Fetching WHOIS for {domain}...")
    try:
        w = whois.whois(domain)
        whois_data[domain] = {
            'registrar': w.registrar,
            'nameservers': w.name_servers or [],
            'status': w.status if isinstance(w.status, list) else [w.status] if w.status else [],
            'updated_date': w.updated_date,
            'expiry_date': w.expiration_date,
        }
        print(f"  OK - Registrar: {w.registrar}")
    except Exception as e:
        print(f"  ERROR: {e}")
        whois_data[domain] = {'error': str(e)}

# Compare
print("\n" + "="*80)
print("COMPARISON")
print("="*80 + "\n")

com_data = whois_data.get('realmadrid.com', {})
es_data = whois_data.get('realmadrid.es', {})

if 'error' in com_data or 'error' in es_data:
    print("ERROR: Cannot compare - one or both queries failed")
    print("\nRECOMMENDATION: Keep both domains (cannot confirm duplication)")
else:
    # Compare key fields
    same_registrar = com_data['registrar'] == es_data['registrar']
    same_nameservers = set(com_data['nameservers']) == set(es_data['nameservers'])

    print(f"Registrar:")
    print(f"  .com: {com_data['registrar']}")
    print(f"  .es:  {es_data['registrar']}")
    print(f"  >>> {'SAME' if same_registrar else 'DIFFERENT'}")

    print(f"\nNameservers:")
    print(f"  .com: {com_data['nameservers']}")
    print(f"  .es:  {es_data['nameservers']}")
    print(f"  >>> {'SAME' if same_nameservers else 'DIFFERENT'}")

    # Verdict
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)

    if same_registrar and same_nameservers:
        print("\n[!] DUPLICATE DATA - Same registrar AND same nameservers")
        print("    Monitoring both wastes WHOIS API calls")
        print("    RECOMMENDATION: Remove one domain (keep .com, remove .es)")
        print("    Changes in one will likely mirror in the other")
    elif same_registrar or same_nameservers:
        print("\n[?] PARTIAL OVERLAP - Some fields match")
        print(f"    Same registrar: {same_registrar}")
        print(f"    Same nameservers: {same_nameservers}")
        print("    RECOMMENDATION: Keep both (partial difference justifies monitoring)")
    else:
        print("\n[OK] DIFFERENT DATA - Different registrar AND nameservers")
        print("    RECOMMENDATION: Keep both domains")

print("\n" + "="*80 + "\n")
