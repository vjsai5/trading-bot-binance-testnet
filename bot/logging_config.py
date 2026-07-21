

import logging
import os
from logging.handlers import RotatingFileHandler

DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE = "trading_bot.log"

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_dir: str = DEFAULT_LOG_DIR, log_file: str = DEFAULT_LOG_FILE,
                   console_level=logging.INFO, file_level=logging.DEBUG) -> logging.Logger:
    """
    Configure and return the root 'trading_bot' logger.

    Safe to call multiple times (e.g. from CLI and Streamlit) - handlers
    are not duplicated.
    """
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        
        return logger

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger


def get_logger(name: str = "trading_bot") -> logging.Logger:
    """Get a child logger under the configured 'trading_bot' namespace."""
    return logging.getLogger(name)
