#!/usr/bin/env python3
"""
Verify that club mentions are genuine (not false positives).

Shows actual URLs/titles for each club to manually verify.
"""

import csv
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from generate_clubs_list import extract_club_from_text


def verify_clarity(filepath: Path, clubs_to_check: list):
    """Show Clarity URLs for each club."""
    clubs = defaultdict(list)

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row['URL']
            sessions = int(row['Sessions'])
            club = extract_club_from_text(url)

            if club in clubs_to_check:
                clubs[club].append((url, sessions))

    return dict(clubs)


def verify_wordpress(filepath: Path, clubs_to_check: list):
    """Show WordPress posts for each club."""
    clubs = defaultdict(list)

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lang = row['lang']
            title = row['post_title']
            views = int(row['views'])
            club = extract_club_from_text(title)

            if club in clubs_to_check:
                clubs[club].append((lang, title, views))

    return dict(clubs)


def main():
    # 9 approved clubs
    clubs_to_check = [
        'real madrid',
        'athletico paranaense',
        'grêmio',
        'santos',
        'manchester city',
        'corinthians',
        'palmeiras',
        'barcelona',
        'flamengo'
    ]

    clarity_path = Path('exports/clarity_clean.csv')
    wordpress_path = Path('exports/wordpress_top50.csv')

    clarity_data = verify_clarity(clarity_path, clubs_to_check)
    wordpress_data = verify_wordpress(wordpress_path, clubs_to_check)

    print("\n" + "=" * 100)
    print("VERIFICATION OF 9 APPROVED CLUBS - CHECKING FOR FALSE POSITIVES")
    print("=" * 100)

    for i, club in enumerate(clubs_to_check, 1):
        clarity_mentions = clarity_data.get(club, [])
        wordpress_mentions = wordpress_data.get(club, [])

        total_mentions = len(clarity_mentions) + len(wordpress_mentions)

        print(f"\n{'='*100}")
        print(f"{i}. {club.upper()}")
        print(f"{'='*100}")
        print(f"Total mentions: {total_mentions} ({len(clarity_mentions)} Clarity + {len(wordpress_mentions)} WordPress)")

        if clarity_mentions:
            print(f"\n--- CLARITY ({len(clarity_mentions)} URLs) ---")
            for url, sessions in sorted(clarity_mentions, key=lambda x: x[1], reverse=True):
                # Extract meaningful part of URL (after domain)
                url_part = url.replace('https://zooomsports.com/', '')
                if len(url_part) > 80:
                    url_part = url_part[:77] + "..."
                print(f"  [{sessions:3d} sessions] {url_part}")

        if wordpress_mentions:
            print(f"\n--- WORDPRESS ({len(wordpress_mentions)} posts) ---")
            for lang, title, views in sorted(wordpress_mentions, key=lambda x: x[2], reverse=True):
                if len(title) > 75:
                    title = title[:72] + "..."
                print(f"  [{views:4d} views] [{lang}] {title}")

        # Manual verification prompt
        print(f"\n  >> VERIFICATION: Are all mentions above genuinely about {club.upper()} (football club)?")
        print(f"     Check for: wrong sport, different entity with same name, unrelated context")

    print(f"\n{'='*100}")
    print("NEXT STEPS:")
    print("  1. Review each club's URLs/titles above")
    print("  2. Identify any FALSE POSITIVES (wrong sport, wrong entity, etc)")
    print("  3. If found: report which club and which specific URL/title is wrong")
    print("  4. If all clean: confirm and proceed to manual enrichment")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
