import os
import sys
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Corrected path to ensure it maps properly inside the ./data directory
LOG_DIR = "./data/logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Generate filename with current date (dd_mm_yyyy)
current_date_str = datetime.now().strftime("%d_%m_%Y")
log_filename = f"sync_{current_date_str}.log"
log_filepath = os.path.join(LOG_DIR, log_filename)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance with both
    a daily rotating file handler and a console stream handler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if get_logger is called multiple times for the same name
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M"
    )

    # Daily Rotating File Handler
    file_handler = TimedRotatingFileHandler(
        filename=log_filepath,
        when="midnight",
        interval=1,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Output Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
