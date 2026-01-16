"""
Web interface module
"""

try:
    from .web_interface import app

    __all__ = ["app"]
except ImportError:
    app = None
    __all__ = []
