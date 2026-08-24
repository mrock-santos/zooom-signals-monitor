#!/usr/bin/env python3
"""
Retest Grêmio and Corinthians with correct User-Agent.
Check if 403/405 errors persist or were false negatives.
"""

import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin

# User-Agent from sources.yaml
USER_AGENT = "Mozilla/5.0 (compatible; ZooomBot/1.0; +https://zooomsports.com/bot)"

sites_to_retest = [
    ("Corinthians", "https://www.corinthians.com.br", "405"),
    ("Grêmio", "https://gremio.net", "403"),
]

print("\n" + "="*80)
print("RETEST WITH CORRECT USER-AGENT")
print("="*80)
print(f"User-Agent: {USER_AGENT}\n")

for club_name, url, previous_error in sites_to_retest:
    robots_url = urljoin(url, '/robots.txt')

    print(f"\n{club_name}")
    print(f"  URL: {robots_url}")
    print(f"  Previous error: HTTP {previous_error}")

    try:
        # Request WITH User-Agent header
        response = requests.get(
            robots_url,
            timeout=10,
            headers={'User-Agent': USER_AGENT}
        )

        print(f"  New status: HTTP {response.status_code}")

        if response.status_code == 404:
            result = "ALLOWED"
            detail = "404 (no robots.txt, default allow)"
        elif response.status_code == 200:
            # Parse robots.txt
            rp = RobotFileParser()
            rp.parse(response.text.splitlines())

            can_fetch = rp.can_fetch(USER_AGENT, url)

            if can_fetch:
                result = "ALLOWED"
                detail = "200 (parsed, crawling ALLOWED)"
            else:
                result = "BLOCKED"
                detail = "200 (parsed, crawling BLOCKED by robots.txt)"
        elif response.status_code in [403, 405]:
            result = "BLOCKED"
            detail = f"HTTP {response.status_code} (error persists, real block)"
        else:
            result = "ERROR"
            detail = f"HTTP {response.status_code}"

        print(f"  Result: {result}")
        print(f"  Detail: {detail}")

        # Verdict
        if previous_error in str(response.status_code):
            print(f"  >>> ERROR PERSISTED - Real blocking, keep site_monitoring: false")
        else:
            print(f"  >>> ERROR FIXED - Was false negative, can enable site_monitoring")

    except Exception as e:
        print(f"  Error: {e}")
        print(f"  >>> EXCEPTION - Keep site_monitoring: false")

print("\n" + "="*80 + "\n")
