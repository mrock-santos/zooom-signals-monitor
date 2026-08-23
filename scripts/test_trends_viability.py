#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Google Trends viability (CAUTELA EXTREMA).

WARNING: Run LOCAL only (never on production server)
WARNING: Only 3 keywords total
WARNING: 10s delay between queries
WARNING: Any error = ABORT immediately and report INVIABLE

Criteria:
- 3/3 queries succeed = VIABLE
- Any error/timeout/429/empty = INVIABLE (leave disabled)

DO NOT retry after a failure. DO NOT tune parameters and run again.
A failure means the source stays disabled pending human decision.
"""

import sys
import time
import logging

from pytrends.request import TrendReq

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


TEST_KEYWORDS = ['Flamengo', 'Real Madrid', 'Haaland']


def test_keyword(keyword: str):
    """
    Test one keyword.

    Returns:
        True  - query succeeded with data
        False - query succeeded but returned no data
        None  - exception raised (ABORT signal)
    """
    logger.info(f"\nTesting: {keyword}")

    try:
        pytrends = TrendReq(hl='pt-BR', tz=180)
        pytrends.build_payload([keyword], timeframe='now 7-d', geo='BR')
        data = pytrends.interest_over_time()

        if data.empty:
            logger.error("  WARN: No data returned (may be too niche)")
            return False

        latest = data[keyword].iloc[-1]
        logger.info(f"  OK - interest score: {latest} ({len(data)} data points)")
        return True

    except Exception as e:
        logger.error(f"  FAILED: {type(e).__name__}: {e}")
        logger.error("\nABORTING - Trends is INVIABLE")
        return None  # Abort signal


def main():
    logger.info("\n" + "="*60)
    logger.info("GOOGLE TRENDS VIABILITY TEST")
    logger.info("="*60)
    logger.info("WARNING: CAUTELA EXTREMA - Run LOCAL only")
    logger.info(f"WARNING: Testing {len(TEST_KEYWORDS)} keywords with 10s delays")
    logger.info("WARNING: ABORT on first error - no retries\n")

    results = []
    aborted = False

    for keyword in TEST_KEYWORDS:
        result = test_keyword(keyword)

        if result is None:
            # Abort on first error
            aborted = True
            break

        results.append(result)
        time.sleep(10)  # Long delay

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info('='*60)

    if aborted or len(results) < len(TEST_KEYWORDS):
        logger.error("RESULT: TRENDS is INVIABLE (aborted after error)")
        logger.error(f"Completed: {len(results)}/{len(TEST_KEYWORDS)}")
        logger.error("\nNext step: Leave disabled in config/sources.yaml")
        logger.error("           Document in docs/incidents/")
        return 1

    if all(results):
        logger.info(f"RESULT: {len(results)}/{len(TEST_KEYWORDS)} successful")
        logger.info("RESULT: TRENDS is VIABLE")
        logger.info("\nNext step: Enable in config/sources.yaml:")
        logger.info("  sources:")
        logger.info("    google_trends:")
        logger.info("      enabled: true")
        return 0

    logger.error("RESULT: Some queries returned no data (no exception)")
    logger.error("        TRENDS is INVIABLE - leave disabled")
    return 1


if __name__ == '__main__':
    sys.exit(main())
