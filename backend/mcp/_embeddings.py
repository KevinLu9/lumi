"""Text embeddings via the Gemini API (`gemini-embedding-001`).

Used to give Lumi's long-term memory semantic recall. Deliberately tolerant: if
no GEMINI_API_KEY is set or the call fails, `embed` returns None so callers can
fall back to keyword search instead of breaking.

Underscore-prefixed so the tool registry never imports it as a tool module.
"""

import os
import threading

from dotenv import load_dotenv

load_dotenv()

# gemini-embedding-001 defaults to 3072 dims; we request 768 to keep the vector
# store compact (cosine ranking is unaffected by the reduction).
MODEL = "models/gemini-embedding-001"
DIM = 768

_configured = False
_lock = threading.Lock()


def _ensure_configured() -> bool:
    """Configure the Gemini client once. Returns False if no key is available."""
    global _configured
    if _configured:
        return True
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return False
    with _lock:
        if not _configured:
            import google.generativeai as genai
            genai.configure(api_key=key)
            _configured = True
    return True


def embed(text: str, *, query: bool = False) -> list[float] | None:
    """Embed `text` and return a 768-float vector, or None on any failure.

    Args:
        text: The text to embed.
        query: True when embedding a search query, False (default) when embedding
            a document/fact to store. Sets the Gemini task_type accordingly.
    """
    text = (text or "").strip()
    if not text or not _ensure_configured():
        return None
    try:
        import google.generativeai as genai
        result = genai.embed_content(
            model=MODEL,
            content=text,
            task_type="retrieval_query" if query else "retrieval_document",
            output_dimensionality=DIM,
        )
        vec = result["embedding"]
        return vec if vec and len(vec) == DIM else None
    except Exception:
        return None


def available() -> bool:
    """True if embeddings can be produced (a Gemini key is configured)."""
    return _ensure_configured()


if __name__ == "__main__":
    import math

    def cos(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb)

    print("available:", available())
    a = embed("The user is vegetarian.")
    b = embed("what does the user like to eat?", query=True)
    c = embed("The capital of France is Paris.")
    if a and b and c:
        print("dim:", len(a))
        print("sim(diet, food-query):", round(cos(a, b), 3))
        print("sim(diet, paris):     ", round(cos(a, c), 3))
    else:
        print("embedding unavailable (no GEMINI_API_KEY?) — got:", bool(a), bool(b), bool(c))
