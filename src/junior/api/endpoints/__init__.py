"""
API Endpoints package
"""

from . import research
from . import documents
from . import chat
from . import translate
from . import format
from . import health
from . import judges
from . import cases
from . import websocket
from . import audio
from . import wall

__all__ = [
    "research",
    "documents",
    "chat",
    "translate",
    "format",
    "health",
    "judges",
    "cases",
    "websocket",
    "wall",
    "audio",
]
