#!/usr/bin/env python3
"""
Test _normalize_registrar() function with real values that caused false positive.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from monitors.whois import _normalize_registrar

# Real values that caused false positive
test_cases = [
    # Case 1: Real Madrid registrar formats
    {
        'label': 'Real Madrid Case',
        'input1': 'Tucows Domains Inc.',
        'input2': 'TUCOWS.COM, CO.',
        'expected_same': True
    },
    # Case 2: Different registrars (should NOT match)
    {
        'label': 'Different Registrars',
        'input1': 'GoDaddy.com, LLC',
        'input2': 'Network Solutions, LLC',
        'expected_same': False
    },
    # Case 3: Same registrar, different formatting
    {
        'label': 'Network Solutions Formats',
        'input1': 'Network Solutions, LLC',
        'input2': 'NETWORK SOLUTIONS LLC',
        'expected_same': True
    },
    # Case 4: Null/empty handling
    {
        'label': 'Null vs Empty',
        'input1': None,
        'input2': '',
        'expected_same': True
    },
]

print("\n" + "="*80)
print("REGISTRAR NORMALIZATION TEST")
print("="*80 + "\n")

passed = 0
failed = 0

for test in test_cases:
    label = test['label']
    input1 = test['input1']
    input2 = test['input2']
    expected_same = test['expected_same']

    norm1 = _normalize_registrar(input1)
    norm2 = _normalize_registrar(input2)
    actual_same = norm1 == norm2

    status = "PASS" if actual_same == expected_same else "FAIL"

    print(f"[{status}] {label}")
    print(f"      Input 1: {input1!r}")
    print(f"      Input 2: {input2!r}")
    print(f"      Normalized 1: {norm1!r}")
    print(f"      Normalized 2: {norm2!r}")
    print(f"      Same: {actual_same} (expected: {expected_same})")

    if actual_same == expected_same:
        passed += 1
    else:
        failed += 1
        print(f"      >>> ERROR: Expected same={expected_same}, got same={actual_same}")

    print()

# Summary
print("="*80)
print("SUMMARY")
print("="*80)
print(f"\nPassed: {passed}/{len(test_cases)}")
print(f"Failed: {failed}/{len(test_cases)}")

if failed == 0:
    print("\n[OK] All tests passed!")
    sys.exit(0)
else:
    print(f"\n[FAIL] {failed} test(s) failed")
    sys.exit(1)
