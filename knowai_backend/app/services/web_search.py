"""
Web Search Service — provides real-time web search capability for the AI assistant.

Uses DuckDuckGo (no API key required). Falls back gracefully on failure.
"""

import logging
from typing import Any

logger = logging.getLogger("knowai.web_search")

try:
    from ddgs import DDGS

    _available = True
except ImportError:
    try:
        from duckduckgo_search import DDGS

        _available = True
    except ImportError:
        DDGS = None  # type: ignore
        _available = False
        logger.warning("ddgs / duckduckgo_search not installed — web search disabled")


def search_web(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search the web for recent information.

    Args:
        query: Search query string.
        max_results: Max number of results to return (default 5).

    Returns:
        A list of dicts with keys ``title``, ``href``, ``body``.
        Empty list if search is unavailable or fails.
    """
    if not _available:
        return []

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", ""),
                }
                for r in results
            ]
    except Exception as exc:
        logger.warning("Web search failed for %r: %s", query, exc)
        return []
