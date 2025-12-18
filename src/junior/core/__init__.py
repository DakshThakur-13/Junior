"""
Core configuration and settings for Junior
"""

from .config import settings, Settings
from .logging import get_logger

__all__ = ["settings", "Settings", "get_logger"]
