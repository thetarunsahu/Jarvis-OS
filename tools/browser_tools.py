from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus, urlparse


class BrowserTools:
    """Safe URL construction and browser launch helpers.

    The tool layer only opens explicit http/https URLs. Permission decisions are
    handled by ToolRegistry before any browser window/tab is opened.
    """

    @staticmethod
    def open_url(url: str) -> dict[str, object]:
        target = BrowserTools._normalise_url(url)
        opened = webbrowser.open(target, new=2)
        return {
            "url": target,
            "opened": bool(opened),
            "message": f"Opened {target} in the default browser.",
        }

    @staticmethod
    def search_web(query: str) -> dict[str, object]:
        text = query.strip()
        if not text:
            raise ValueError("query cannot be empty")

        target = f"https://www.google.com/search?q={quote_plus(text)}"
        opened = webbrowser.open(target, new=2)
        return {
            "query": text,
            "url": target,
            "opened": bool(opened),
            "message": f"Opened a web search for '{text}'.",
        }

    @staticmethod
    def search_youtube(query: str) -> dict[str, object]:
        text = query.strip()
        if not text:
            raise ValueError("query cannot be empty")

        target = f"https://www.youtube.com/results?search_query={quote_plus(text)}"
        opened = webbrowser.open(target, new=2)
        return {
            "query": text,
            "url": target,
            "opened": bool(opened),
            "message": f"Opened a YouTube search for '{text}'.",
        }

    @staticmethod
    def _normalise_url(url: str) -> str:
        raw = url.strip()
        if not raw:
            raise ValueError("url cannot be empty")

        if "://" not in raw:
            raw = "https://" + raw

        parsed = urlparse(raw)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("Only http and https URLs are allowed.")
        if not parsed.netloc:
            raise ValueError("URL must include a valid host name.")

        return parsed.geturl()
