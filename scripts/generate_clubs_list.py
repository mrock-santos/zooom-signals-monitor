#!/usr/bin/env python3
"""
Generate clubs.yaml from real traffic data.

Usage:
    python scripts/generate_clubs_list.py \
        --clarity clarity_export.csv \
        --gsc gsc_queries.csv \
        --output config/clubs.yaml

Analyzes:
- Clarity: sessions per URL containing club mentions
- GSC: clicks per query containing club mentions
- WordPress: engagement score from posts (requires DB access or manual list)

Outputs ranked list of top 8-10 clubs by combined score.
Manual enrichment required after generation (domains, URLs, keywords).
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections import Counter
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


# Known club name patterns (PT/ES/EN variations)
# Only clubs that appear in actual traffic data (Clarity + WordPress)
CLUB_PATTERNS = {
    # Brazilian clubs (found in data)
    'corinthians': ['corinthians', 'timão', 'corinthian'],
    'santos': ['santos', 'peixe'],
    'athletico paranaense': ['athletico', 'athletico paranaense', 'cap', 'furacão'],
    'grêmio': ['grêmio', 'gremio', 'tricolor gaúcho', 'tricolor gaucho'],
    'flamengo': ['flamengo', 'fla', 'mengão'],
    'palmeiras': ['palmeiras', 'verdão'],
    'são paulo': ['são paulo', 'sao paulo', 'spfc', 'tricolor paulista'],

    # European clubs (found in data)
    'real madrid': ['real madrid', 'madrid', 'merengues'],
    'freiburg': ['freiburg', 'sc freiburg'],
    'aston villa': ['aston villa', 'villa'],

    # Other clubs (original list, not yet found in data but kept for potential matches)
    'barcelona': ['barcelona', 'barça', 'barca', 'blaugrana'],
    'manchester city': ['manchester city', 'man city', 'city'],
    'manchester united': ['manchester united', 'man united', 'united'],
    'liverpool': ['liverpool', 'reds'],
    'atletico madrid': ['atletico madrid', 'atlético madrid', 'atleti'],
    'chelsea': ['chelsea', 'blues'],
    'arsenal': ['arsenal', 'gunners'],
    'boca juniors': ['boca juniors', 'boca', 'xeneizes'],
    'river plate': ['river plate', 'river', 'millonarios'],
}


def normalize_text(text: str) -> str:
    """Normalize text for matching (lowercase, no accents)."""
    import unicodedata
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text


def extract_club_from_text(text: str) -> str | None:
    """
    Extract club name from URL or query text.

    Args:
        text: URL path or search query

    Returns:
        Canonical club name (key from CLUB_PATTERNS) or None
    """
    normalized = normalize_text(text)

    for club, patterns in CLUB_PATTERNS.items():
        for pattern in patterns:
            if pattern in normalized:
                return club

    return None


def parse_clarity_csv(filepath: Path) -> Counter:
    """
    Parse Clarity export CSV and count sessions per club.

    Expected columns: URL, Sessions (or similar)
    """
    club_scores = Counter()

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Detect column names (case-insensitive)
        columns = {col.lower(): col for col in reader.fieldnames}
        url_col = columns.get('url') or columns.get('page')
        sessions_col = columns.get('sessions') or columns.get('pageviews')

        if not url_col or not sessions_col:
            logger.warning(f"WARNING: Clarity CSV missing expected columns. Found: {reader.fieldnames}")
            logger.warning(f"         Expected: URL/Page and Sessions/Pageviews")
            return club_scores

        for row in reader:
            url = row[url_col]
            try:
                sessions = int(row[sessions_col])
            except (ValueError, KeyError):
                continue

            club = extract_club_from_text(url)
            if club:
                club_scores[club] += sessions

    return club_scores


def parse_gsc_csv(filepath: Path) -> Counter:
    """
    Parse GSC queries export and count clicks per club.

    Expected columns: Query, Clicks
    """
    club_scores = Counter()

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        columns = {col.lower(): col for col in reader.fieldnames}
        query_col = columns.get('query') or columns.get('top queries')
        clicks_col = columns.get('clicks') or columns.get('cliques')

        if not query_col or not clicks_col:
            logger.warning(f"WARNING: GSC CSV missing expected columns. Found: {reader.fieldnames}")
            return club_scores

        for row in reader:
            query = row[query_col]
            try:
                clicks = int(float(row[clicks_col]))  # May have decimals
            except (ValueError, KeyError):
                continue

            club = extract_club_from_text(query)
            if club:
                # Weight search clicks higher (organic intent)
                club_scores[club] += clicks * 2

    return club_scores


def generate_clubs_yaml(ranked_clubs: list, output_path: Path):
    """
    Generate clubs.yaml with ranked clubs.

    Manual enrichment needed:
    - Verify each club makes sense (not adversary-only mentions)
    - Add domains (via manual search)
    - Add official_site URLs
    - Add monitor_pages (elenco, patrocinadores)
    - Add trends_keywords
    """
    clubs_data = {
        'clubs': []
    }

    # Template for manual completion
    for club, score in ranked_clubs[:10]:  # Top 10
        club_entry = {
            'id': club.replace(' ', '-'),
            'name': club.title(),
            'score': score,  # Can remove after validation
            'league': 'TODO',
            'country': 'TODO',
            'domains': ['TODO.com'],
            'official_site': {
                'url': 'https://TODO.com',
                'monitor_pages': [
                    {'path': '/elenco', 'label': 'Elenco', 'type': 'structural'}
                ]
            },
            'whois_enabled': True,
            'site_monitoring_enabled': True,
            'trends_keywords': [club.title(), 'TODO-player-name']
        }
        clubs_data['clubs'].append(club_entry)

    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(clubs_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    logger.info(f"\nSUCCESS: Generated {output_path}")
    logger.info(f"         {len(clubs_data['clubs'])} clubs listed")
    logger.warning(f"\nWARNING: MANUAL ENRICHMENT REQUIRED:")
    logger.warning(f"         - Verify each club is protagonist (not just adversary mention)")
    logger.warning(f"         - Fill in league, country, domains")
    logger.warning(f"         - Add official_site URL + monitor_pages")
    logger.warning(f"         - Add trends_keywords (club + key players)")
    logger.warning(f"         - Remove 'score' field after validation")


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    parser = argparse.ArgumentParser(description='Generate clubs.yaml from traffic data')
    parser.add_argument('--clarity', type=Path, help='Clarity export CSV')
    parser.add_argument('--gsc', type=Path, help='GSC queries export CSV')
    parser.add_argument('--output', type=Path, default=Path('config/clubs.yaml'))

    args = parser.parse_args()

    club_scores = Counter()

    # Parse Clarity
    if args.clarity and args.clarity.exists():
        logger.info(f"Parsing Clarity: {args.clarity}")
        clarity_scores = parse_clarity_csv(args.clarity)
        logger.info(f"  Found {len(clarity_scores)} clubs")
        club_scores.update(clarity_scores)
    else:
        logger.warning(f"WARNING: Clarity file not found or not provided")

    # Parse GSC
    if args.gsc and args.gsc.exists():
        logger.info(f"Parsing GSC: {args.gsc}")
        gsc_scores = parse_gsc_csv(args.gsc)
        logger.info(f"  Found {len(gsc_scores)} clubs")
        club_scores.update(gsc_scores)
    else:
        logger.warning(f"WARNING: GSC file not found or not provided")

    # Rank
    ranked = club_scores.most_common(15)

    logger.info(f"\nTop clubs by combined score:")
    for i, (club, score) in enumerate(ranked, 1):
        logger.info(f"   {i:2d}. {club.title():20s} - {score:6d} points")

    # Generate YAML
    if ranked:
        generate_clubs_yaml(ranked, args.output)
    else:
        logger.error(f"\nERROR: No clubs found in data sources")
        logger.error(f"       Verify CSV files have expected columns")


if __name__ == '__main__':
    main()
