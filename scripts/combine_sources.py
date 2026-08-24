#!/usr/bin/env python3
"""
Combine Clarity + WordPress with weighted scores.

Clarity: 1.0 (30 days window)
WordPress: 0.31 (all-time, mean age 96 days)
"""

import csv
from collections import Counter
from pathlib import Path
import sys
import os

# Add parent directory to path to import from generate_clubs_list
sys.path.insert(0, str(Path(__file__).parent))
from generate_clubs_list import extract_club_from_text, logger

CLARITY_WEIGHT = 1.0
WORDPRESS_WEIGHT = 0.31

def parse_clarity(filepath: Path) -> Counter:
    """Parse Clarity CSV (URL, Sessions)."""
    scores = Counter()

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row['URL']
            sessions = int(row['Sessions'])

            club = extract_club_from_text(url)
            if club:
                scores[club] += sessions * CLARITY_WEIGHT

    return scores


def parse_wordpress(filepath: Path) -> Counter:
    """Parse WordPress CSV (lang, post_title, views)."""
    scores = Counter()

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row['post_title']
            views = int(row['views'])

            club = extract_club_from_text(title)
            if club:
                scores[club] += views * WORDPRESS_WEIGHT

    return scores


def main():
    logger.info("Combining Clarity + WordPress with weighted scores\n")

    clarity_path = Path('exports/clarity_clean.csv')
    wordpress_path = Path('exports/wordpress_top50.csv')

    # Parse sources
    clarity_scores = parse_clarity(clarity_path)
    wordpress_scores = parse_wordpress(wordpress_path)

    # Combine
    combined = Counter()
    combined.update(clarity_scores)
    combined.update(wordpress_scores)

    # Stats
    logger.info(f"Clarity:   {len(clarity_scores)} clubs, weight {CLARITY_WEIGHT}")
    logger.info(f"WordPress: {len(wordpress_scores)} clubs, weight {WORDPRESS_WEIGHT}")
    logger.info(f"Combined:  {len(combined)} clubs total\n")

    # Top 15 with source breakdown
    logger.info("Top 15 clubs by combined score:\n")
    logger.info(f"{'Rank':<5} {'Club':<25} {'Total':>8}  {'Clarity':>8}  {'WordPress':>10}  {'Breakdown'}")
    logger.info("-" * 85)

    for i, (club, total_score) in enumerate(combined.most_common(15), 1):
        clarity_pts = clarity_scores.get(club, 0)
        wordpress_pts = wordpress_scores.get(club, 0)

        # Source breakdown
        sources = []
        if clarity_pts > 0:
            sources.append(f"C:{int(clarity_pts)}")
        if wordpress_pts > 0:
            sources.append(f"W:{int(wordpress_pts)}")
        breakdown = " + ".join(sources)

        logger.info(f"{i:<5} {club.title():<25} {int(total_score):>8}  {int(clarity_pts):>8}  {int(wordpress_pts):>10}  {breakdown}")

    logger.info(f"\n{'='*85}")
    logger.info(f"Weights: Clarity={CLARITY_WEIGHT} (30 days), WordPress={WORDPRESS_WEIGHT} (96 days mean)")


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    main()
