"""
Logging configuration for Junior
"""

import logging
import sys
from typing import Optional

from .config import settings

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance

    Args:
        name: Logger name (defaults to 'junior')

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or "junior")

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        if settings.is_development:
            level = logging.DEBUG
            format_str = (
                "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
            )
        else:
            level = logging.INFO
            format_str = "%(asctime)s | %(levelname)-8s | %(message)s"

        handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger
