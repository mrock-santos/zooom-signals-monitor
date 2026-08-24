#!/usr/bin/env python3
"""
Analyze distinct mentions per club across sources.

Counts how many DIFFERENT URLs/posts mention each club, not just total score.
"""

import csv
from collections import defaultdict
from pathlib import Path
import sys

# Add parent directory to import from generate_clubs_list
sys.path.insert(0, str(Path(__file__).parent))
from generate_clubs_list import extract_club_from_text

CLARITY_WEIGHT = 1.0
WORDPRESS_WEIGHT = 0.31


def analyze_clarity(filepath: Path):
    """
    Analyze Clarity URLs.

    Returns: {club: {'mentions': count, 'score': total, 'urls': [list]}}
    """
    clubs = defaultdict(lambda: {'mentions': 0, 'score': 0, 'urls': []})

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row['URL']
            sessions = int(row['Sessions'])

            club = extract_club_from_text(url)
            if club:
                clubs[club]['mentions'] += 1
                clubs[club]['score'] += sessions * CLARITY_WEIGHT
                clubs[club]['urls'].append((url, sessions))

    return dict(clubs)


def analyze_wordpress(filepath: Path):
    """
    Analyze WordPress posts.

    Returns: {club: {'mentions': count, 'score': total, 'posts': [list]}}
    """
    clubs = defaultdict(lambda: {'mentions': 0, 'score': 0, 'posts': []})

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row['post_title']
            views = int(row['views'])

            club = extract_club_from_text(title)
            if club:
                clubs[club]['mentions'] += 1
                clubs[club]['score'] += views * WORDPRESS_WEIGHT
                clubs[club]['posts'].append((title, views))

    return dict(clubs)


def main():
    clarity_path = Path('exports/clarity_clean.csv')
    wordpress_path = Path('exports/wordpress_top50.csv')

    # Analyze sources
    clarity_clubs = analyze_clarity(clarity_path)
    wordpress_clubs = analyze_wordpress(wordpress_path)

    # Combine all clubs
    all_clubs = set(list(clarity_clubs.keys()) + list(wordpress_clubs.keys()))

    # Build combined data
    combined = []
    for club in all_clubs:
        clarity_data = clarity_clubs.get(club, {'mentions': 0, 'score': 0})
        wordpress_data = wordpress_clubs.get(club, {'mentions': 0, 'score': 0})

        total_mentions = clarity_data['mentions'] + wordpress_data['mentions']
        total_score = clarity_data['score'] + wordpress_data['score']

        # Count sources (how many sources mention this club)
        sources_count = sum([
            1 if clarity_data['mentions'] > 0 else 0,
            1 if wordpress_data['mentions'] > 0 else 0
        ])

        # Flags
        single_mention_only = (total_mentions == 1)
        multi_source = (sources_count >= 2)

        combined.append({
            'club': club,
            'total_score': int(total_score),
            'total_mentions': total_mentions,
            'clarity_mentions': clarity_data['mentions'],
            'clarity_score': int(clarity_data['score']),
            'wordpress_mentions': wordpress_data['mentions'],
            'wordpress_score': int(wordpress_data['score']),
            'sources_count': sources_count,
            'single_mention': single_mention_only,
            'multi_source': multi_source,
            'clarity_urls': clarity_clubs.get(club, {}).get('urls', []),
            'wordpress_posts': wordpress_clubs.get(club, {}).get('posts', [])
        })

    # Sort by total score
    combined.sort(key=lambda x: x['total_score'], reverse=True)

    # Print report
    print("\n" + "=" * 120)
    print("DISTINCT MENTIONS ANALYSIS — All 16 Clubs")
    print("=" * 120)
    print(f"\n{'#':<3} {'Club':<25} {'Total':>6} {'Mentions':>9} {'Sources':>8}  {'Clarity':>7}  {'WordPress':>10}  {'Flags'}")
    print(f"{'':3} {'':25} {'Score':>6} {'(URLs/':>9} {'(C+W)':>8}  {'Score':>7}  {'Score':>10}")
    print(f"{'':3} {'':25} {'':6} {'Posts)':>9} {'':8}  {'(URLs)':>7}  {'(Posts)':>10}")
    print("-" * 120)

    for i, data in enumerate(combined, 1):
        club = data['club'].title()
        total_score = data['total_score']
        total_mentions = data['total_mentions']
        sources = data['sources_count']

        clarity_score = data['clarity_score']
        clarity_mentions = data['clarity_mentions']

        wordpress_score = data['wordpress_score']
        wordpress_mentions = data['wordpress_mentions']

        # Flags
        flags = []
        if data['single_mention']:
            flags.append("[!] SINGLE")
        if data['multi_source']:
            flags.append("[OK] MULTI-SRC")
        flag_str = " ".join(flags) if flags else ""

        print(f"{i:<3} {club:<25} {total_score:>6} {total_mentions:>9} {sources:>8}  "
              f"{clarity_score:>7}  {wordpress_score:>10}  {flag_str}")
        print(f"{'':3} {'':25} {'':6} {'':9} {'':8}  "
              f"({clarity_mentions} URLs) ({wordpress_mentions} posts)")

    # Summary section
    print("\n" + "=" * 120)
    print("RISK FLAGS")
    print("=" * 120)

    single_mention = [d for d in combined if d['single_mention']]
    if single_mention:
        print(f"\n[!] SINGLE MENTION ONLY ({len(single_mention)} clubs) - Isolated spike risk:")
        for data in single_mention:
            print(f"    • {data['club'].title()} ({data['total_score']} pts) - ", end="")

            if data['clarity_mentions'] == 1:
                url, sessions = data['clarity_urls'][0]
                url_short = url[:60] + "..." if len(url) > 60 else url
                print(f"1 Clarity URL ({sessions} sessions): {url_short}")
            elif data['wordpress_mentions'] == 1:
                title, views = data['wordpress_posts'][0]
                title_short = title[:60] + "..." if len(title) > 60 else title
                print(f"1 WordPress post ({views} views × 0.31 = {int(views * 0.31)} pts): {title_short}")

    print("\n" + "=" * 120)
    print("CONFIDENCE FLAGS")
    print("=" * 120)

    multi_source = [d for d in combined if d['multi_source']]
    if multi_source:
        print(f"\n[OK] MULTI-SOURCE CONFIRMATION ({len(multi_source)} clubs) - Strongest signal:")
        for data in multi_source:
            sources_detail = []
            if data['clarity_mentions'] > 0:
                sources_detail.append(f"Clarity: {data['clarity_mentions']} URLs")
            if data['wordpress_mentions'] > 0:
                sources_detail.append(f"WordPress: {data['wordpress_mentions']} posts")

            print(f"    • {data['club'].title()} ({data['total_score']} pts, {data['total_mentions']} mentions) - "
                  f"{' + '.join(sources_detail)}")

    multi_mention_single_source = [d for d in combined if d['total_mentions'] > 1 and not d['multi_source']]
    if multi_mention_single_source:
        print(f"\n[OK] MULTIPLE MENTIONS (single source) ({len(multi_mention_single_source)} clubs) - Recurrent interest:")
        for data in multi_mention_single_source:
            source = "Clarity" if data['clarity_mentions'] > 0 else "WordPress"
            mentions = data['clarity_mentions'] if data['clarity_mentions'] > 0 else data['wordpress_mentions']
            print(f"    • {data['club'].title()} ({data['total_score']} pts) - "
                  f"{source}: {mentions} different URLs/posts")

    print("\n" + "=" * 120)
    print(f"Legend:")
    print(f"  [!] SINGLE       = Only 1 URL/post mentions this club (isolated spike risk)")
    print(f"  [OK] MULTI-SRC   = Mentioned in BOTH Clarity AND WordPress (strongest validation)")
    print(f"  Sources (C+W)    = Number of sources: 1 (single) or 2 (both)")
    print("=" * 120 + "\n")


if __name__ == '__main__':
    main()
