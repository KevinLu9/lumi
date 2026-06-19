"""Browser tools — open URLs and search the web."""
import webbrowser
from urllib.parse import quote_plus


def open_url(url: str) -> str:
    """Open a URL in the user's default web browser.

    Args:
        url: Full URL to open, e.g. 'https://youtube.com'.
    """
    webbrowser.open(url)
    return f"Opened {url}"


def search_web(query: str) -> str:
    """Search Google for a query and open the results in the browser.

    Args:
        query: Search terms, e.g. 'Python tutorials' or 'weather Sydney'.
    """
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open(url)
    return f"Searching for: {query}"


TOOL_FNS: dict = {
    "open_url": open_url,
    "search_web": search_web,
}

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL in the user's default web browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to open, e.g. 'https://youtube.com'.",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search Google for a query and open the results page in the browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search terms, e.g. 'Python tutorials' or 'weather Sydney'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]
