#!/usr/bin/env python3
"""
Validate robots.txt for club official sites.

Usage:
    python scripts/check_robots_txt.py https://www.flamengo.com.br
    python scripts/check_robots_txt.py --yaml config/clubs.yaml

Checks:
- 404 (no robots.txt) → allowed: True
- 200 + parse OK → allowed per rules
- Timeout/5xx/network error → allowed: False (manual review required)
"""

import argparse
import requests
import yaml
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
from pathlib import Path


USER_AGENT = 'ZooomBot'


def check_robots_txt(base_url: str) -> dict:
    """
    Check if robots.txt allows access.

    Args:
        base_url: Base URL of the site (e.g., https://www.example.com)

    Returns:
        dict with keys: allowed (bool), status (str), robots_url (str), note (str)
    """
    robots_url = urljoin(base_url, '/robots.txt')

    try:
        resp = requests.get(robots_url, timeout=10)

        # 404 = no robots.txt = allowed by default
        if resp.status_code == 404:
            return {
                'allowed': True,
                'robots_url': robots_url,
                'status': 'no_robots_txt',
                'note': '404 - No robots.txt found (allowed by default)'
            }

        # Other HTTP errors = manual review
        if resp.status_code != 200:
            return {
                'allowed': False,
                'robots_url': robots_url,
                'status': 'error',
                'http_code': resp.status_code,
                'note': f'HTTP {resp.status_code} - Manual review required'
            }

        # Parse robots.txt
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(resp.text.splitlines())

        can_fetch = rp.can_fetch(USER_AGENT, base_url)

        return {
            'allowed': can_fetch,
            'robots_url': robots_url,
            'status': 'parsed',
            'note': 'Allowed' if can_fetch else 'Blocked by robots.txt'
        }

    except requests.exceptions.Timeout:
        return {
            'allowed': False,
            'robots_url': robots_url,
            'status': 'timeout',
            'note': 'Timeout fetching robots.txt - Manual review required'
        }

    except requests.exceptions.RequestException as e:
        return {
            'allowed': False,
            'robots_url': robots_url,
            'status': 'network_error',
            'note': f'Network error: {type(e).__name__} - Manual review required'
        }

    except Exception as e:
        return {
            'allowed': False,
            'robots_url': robots_url,
            'status': 'parse_error',
            'note': f'Parse error: {type(e).__name__} - Manual review required'
        }


def check_from_yaml(yaml_path: Path):
    """Check all official_site URLs from clubs.yaml."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    print(f"\n🔍 Checking robots.txt for {len(data['clubs'])} clubs\n")

    results = []
    for club in data['clubs']:
        url = club['official_site']['url']
        club_name = club['name']

        print(f"Checking: {club_name} ({url})")
        result = check_robots_txt(url)
        result['club'] = club_name
        result['url'] = url
        results.append(result)

        # Print result
        if result['status'] == 'no_robots_txt':
            print(f"  ✅ ALLOWED (no robots.txt)\n")
        elif result['status'] == 'parsed' and result['allowed']:
            print(f"  ✅ ALLOWED by robots.txt\n")
        elif result['status'] == 'parsed' and not result['allowed']:
            print(f"  ❌ BLOCKED by robots.txt")
            print(f"     → Do NOT add to monitor_pages\n")
        else:
            print(f"  ⚠️  {result['status'].upper()} - {result['note']}")
            print(f"     → Manual review REQUIRED before adding\n")

    # Summary
    allowed_count = sum(1 for r in results if r['allowed'])
    blocked_count = sum(1 for r in results if r['status'] == 'parsed' and not r['allowed'])
    manual_count = sum(1 for r in results if r['status'] not in ['no_robots_txt', 'parsed'])

    print(f"\n📊 Summary:")
    print(f"   ✅ Allowed: {allowed_count}")
    print(f"   ❌ Blocked: {blocked_count}")
    print(f"   ⚠️  Manual Review: {manual_count}")

    if blocked_count > 0:
        print(f"\n⚠️  REMOVE these from clubs.yaml:")
        for r in results:
            if r['status'] == 'parsed' and not r['allowed']:
                print(f"     - {r['club']}: {r['url']}")

    if manual_count > 0:
        print(f"\n⚠️  MANUAL REVIEW before adding:")
        for r in results:
            if r['status'] not in ['no_robots_txt', 'parsed']:
                print(f"     - {r['club']}: {r['note']}")


def main():
    parser = argparse.ArgumentParser(description='Check robots.txt for sites')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('url', nargs='?', help='Single URL to check')
    group.add_argument('--yaml', type=Path, help='Check all URLs from clubs.yaml')

    args = parser.parse_args()

    if args.yaml:
        check_from_yaml(args.yaml)
    else:
        result = check_robots_txt(args.url)
        print(f"\nURL: {args.url}")
        print(f"Robots.txt: {result['robots_url']}")
        print(f"Status: {result['status']}")
        print(f"Allowed: {'✅ YES' if result['allowed'] else '❌ NO'}")
        print(f"Note: {result['note']}\n")


if __name__ == '__main__':
    main()
