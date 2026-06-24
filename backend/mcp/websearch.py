"""Web search — let Lumi answer general-knowledge and current-events questions.

Primary provider is Tavily (free tier: 1,000 API credits/month, no card). Its
`answer` field returns a synthesized one-liner that's ideal for speaking. If the
Tavily call fails (e.g. monthly credits exhausted) and the optional `ddgs`
package is installed, we fall back to a no-key DuckDuckGo search.

Requires TAVILY_API_KEY in .env. Get a free key at https://app.tavily.com.
"""

import os

import requests
from dotenv import load_dotenv

from ._registry import Registry

registry = Registry()
REQUIRES_ENV = "TAVILY_API_KEY"  # only registered when a key is present
DESCRIPTION = "Search the web for facts, current events, and general questions; can also give a synthesized answer."

load_dotenv()

_TAVILY_URL = "https://api.tavily.com/search"


def _tavily(query: str, *, max_results: int, include_answer: bool) -> dict:
    resp = requests.post(
        _TAVILY_URL,
        json={
            "api_key": os.environ["TAVILY_API_KEY"],
            "query": query,
            "search_depth": "basic",
            "include_answer": include_answer,
            "max_results": max_results,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _ddg_fallback(query: str, max_results: int) -> list[dict] | None:
    """Best-effort no-key fallback. Returns result dicts or None if unavailable."""
    try:
        from ddgs import DDGS  # optional dependency
    except Exception:
        return None
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=max_results))
        return [
            {"title": h.get("title", ""), "url": h.get("href", ""), "content": h.get("body", "")}
            for h in hits
        ]
    except Exception:
        return None


@registry.tool
def web_search(query: str, limit: int = 3) -> str:
    """Search the web and return the top results (title, snippet, and link).

    Use this for facts, current events, or anything outside your built-in
    knowledge. For a single spoken answer rather than a list, use web_answer.

    Args:
        query: What to search for.
        limit: How many results to return (default 3).
    """
    limit = max(1, min(limit, 10))
    results = None
    try:
        results = _tavily(query, max_results=limit, include_answer=False).get("results", [])
    except Exception:
        results = _ddg_fallback(query, limit)
        if results is None:
            return "I couldn't reach the web search service just now."
    if not results:
        return f"I didn't find anything for '{query}'."

    # Side-channel structured results to the UI, mirroring the weather widget.
    from .. import events
    events.emit("search", query=query, results=[
        {"title": r.get("title", ""), "url": r.get("url", "")} for r in results
    ])

    lines = []
    for r in results[:limit]:
        snippet = (r.get("content") or "").strip().replace("\n", " ")
        if len(snippet) > 160:
            snippet = snippet[:157] + "..."
        lines.append(f"{r.get('title', 'Result')}: {snippet}")
    return f"Top results for '{query}' — " + " | ".join(lines)


@registry.tool
def web_answer(query: str) -> str:
    """Get a single synthesized answer to a question from the web, ready to speak.

    Prefer this over web_search when the user asks a direct question (e.g. 'who
    won the game last night?', 'how tall is the Eiffel Tower?').

    Args:
        query: The question to answer.
    """
    try:
        data = _tavily(query, max_results=5, include_answer=True)
    except Exception:
        # No synthesized answer without Tavily; degrade to a snippet from results.
        fb = _ddg_fallback(query, 1)
        if fb:
            return (fb[0].get("content") or "").strip() or "I couldn't find a clear answer."
        return "I couldn't reach the web search service just now."
    answer = (data.get("answer") or "").strip()
    if answer:
        return answer
    results = data.get("results", [])
    if results:
        return (results[0].get("content") or "").strip() or f"I didn't find a clear answer for '{query}'."
    return f"I didn't find anything for '{query}'."


if __name__ == "__main__":
    print("search:", web_search("tallest mountain in the world"))
    print("answer:", web_answer("how tall is Mount Everest?"))
