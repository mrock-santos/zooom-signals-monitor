#!/usr/bin/env python3
"""
Cleanup old logs and create state snapshots.

Retention: 90 days
"""

from datetime import datetime, timedelta
from pathlib import Path


RETENTION_DAYS = 90
LOGS_DIR = Path('logs')
STATE_FILE = Path('state/last_check.json')
ARCHIVE_DIR = Path('state/archive')


def cleanup_old_logs():
    """Remove logs older than RETENTION_DAYS."""
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed_count = 0

    for log_file in LOGS_DIR.glob('*.log'):
        try:
            file_date_str = log_file.stem  # YYYY-MM-DD
            file_date = datetime.strptime(file_date_str, '%Y-%m-%d')

            if file_date < cutoff_date:
                print(f"Removing old log: {log_file}")
                log_file.unlink()
                removed_count += 1

        except ValueError:
            print(f"Skipping non-standard log: {log_file}")

    print(f"Removed {removed_count} log files older than {RETENTION_DAYS} days")


def create_state_snapshot():
    """Create weekly snapshot of current state."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    if STATE_FILE.exists():
        import shutil
        snapshot_file = ARCHIVE_DIR / f"snapshot-{datetime.now().strftime('%Y-%m-%d')}.json"
        shutil.copy(STATE_FILE, snapshot_file)
        print(f"Created state snapshot: {snapshot_file}")

        # Remove old snapshots (keep last 12 = ~3 months)
        snapshots = sorted(ARCHIVE_DIR.glob('snapshot-*.json'))
        if len(snapshots) > 12:
            for old_snapshot in snapshots[:-12]:
                print(f"Removing old snapshot: {old_snapshot}")
                old_snapshot.unlink()


if __name__ == '__main__':
    print(f"Starting cleanup - retention: {RETENTION_DAYS} days")
    cleanup_old_logs()
    create_state_snapshot()
    print("Cleanup completed")
