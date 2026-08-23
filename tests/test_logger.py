import os
import logging
from datetime import datetime
from pathlib import Path
from utils.logger import setup_logger


def test_setup_logger_creates_daily_log_file(tmp_path):
    """Logger creates log file named YYYY-MM-DD.log"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    logger = setup_logger(log_dir=str(log_dir))

    expected_log = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    assert expected_log.exists()


def test_logger_writes_to_file(tmp_path):
    """Logger writes messages to file"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    logger = setup_logger(log_dir=str(log_dir))
    logger.info("Test message")

    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    content = log_file.read_text()
    assert "Test message" in content
    assert "[INFO]" in content


def test_logger_includes_timestamp(tmp_path):
    """Logger includes ISO timestamp in each line"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    logger = setup_logger(log_dir=str(log_dir))
    logger.warning("Warning message")

    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    content = log_file.read_text()

    # Format: YYYY-MM-DD HH:MM:SS [LEVEL] message
    import re
    pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[WARNING\] Warning message'
    assert re.search(pattern, content)
