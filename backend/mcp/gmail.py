"""Gmail tools (read-only) — let Lumi read and search the user's inbox.

Requires GOOGLE_CLIENT_ID in .env and a one-time `python -m backend.mcp.google_auth`
to grant access (shares the same consent as the Calendar tools). Read-only: there
is no send tool. To add sending later, add the gmail.send scope in google_auth.py.
"""

from ._registry import Registry

registry = Registry()
REQUIRES_ENV = "GOOGLE_CLIENT_ID"  # only registered when Google is configured
DESCRIPTION = "Search the user's Gmail inbox (read-only) with Gmail query syntax."


def _service():
    from . import google_auth
    return google_auth.service("gmail", "v1")


def _header(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _summarize(svc, msg_ids: list[dict], count: int) -> list[str]:
    out = []
    for m in msg_ids[:count]:
        msg = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        sender = _header(msg, "From").split("<")[0].strip().strip('"') or "Unknown"
        subject = _header(msg, "Subject") or "(no subject)"
        snippet = (msg.get("snippet") or "").strip()
        if len(snippet) > 100:
            snippet = snippet[:97] + "..."
        out.append(f"{sender}: {subject}" + (f" — {snippet}" if snippet else ""))
    return out


def _query(q: str, count: int, empty_msg: str) -> str:
    from . import google_auth
    count = max(1, min(count, 10))
    try:
        svc = _service()
        ids = svc.users().messages().list(
            userId="me", q=q, maxResults=count,
        ).execute().get("messages", [])
        if not ids:
            return empty_msg
        lines = _summarize(svc, ids, count)
    except google_auth.NotConnectedError as e:
        return str(e)
    except Exception as e:
        return f"Couldn't reach Gmail: {e}"
    return " | ".join(lines)


@registry.tool
def email_search(query: str, count: int = 5) -> str:
    """Search the user's Gmail and summarize the matching messages.

    Uses Gmail's search query syntax. Combine filters with spaces (AND) or OR.
    Prefer including 'in:inbox' by default so results match what the user sees
    in their inbox, unless they specifically want sent/spam/trash/all mail.
    Common filters:
        - in:inbox / in:sent / in:spam / in:trash / in:anywhere / label:<name>
        - is:unread / is:read / is:starred / is:important
        - from:<sender> / to:<recipient> / subject:<text>
        - has:attachment / filename:pdf
        - newer_than:1d / older_than:7d (units: d=day, m=month, y=year)
        - after:2024/01/31 / before:2024/02/15 (YYYY/MM/DD)
    To list unread inbox mail, pass query='in:inbox is:unread'. Examples:
        'in:inbox is:unread newer_than:1d',
        'in:inbox from:bank subject:invoice has:attachment',
        'in:anywhere is:starred older_than:30d'.

    Args:
        query: A Gmail search query, e.g. 'in:inbox is:unread newer_than:1d' or
            'in:inbox from:bank subject:invoice'.
        count: How many results to summarize (default 5, max 10).
    """
    return _query(query, count, f"No emails matched '{query}'.")


if __name__ == "__main__":
    print(email_search("is:unread", 5))
    print(email_search("newer_than:7d", 3))
