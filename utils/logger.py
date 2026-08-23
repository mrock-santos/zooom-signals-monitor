import logging
from datetime import datetime
from pathlib import Path


def setup_logger(log_dir='logs'):
    """
    Setup structured logger that writes to daily log files.

    Args:
        log_dir: Directory to store log files (default: 'logs')

    Returns:
        logging.Logger configured for this session
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_file = Path(log_dir) / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    # Remove existing handlers to avoid duplicates
    logger = logging.getLogger('monitor')
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    # Format: YYYY-MM-DD HH:MM:SS [LEVEL] message
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler (append mode)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (for GitHub Actions logs)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
