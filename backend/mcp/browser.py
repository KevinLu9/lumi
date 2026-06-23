"""Browser tools — control Chrome via AppleScript (no special flags required)."""
import subprocess

from ._registry import Registry

registry = Registry()
DESCRIPTION = "Control the Chrome browser: navigate to URLs, read the page, click elements."


def _osascript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _ensure_chrome():
    """Open Chrome if it isn't running."""
    _osascript('tell application "Google Chrome" to activate')


@registry.tool
def browser_navigate(url: str) -> str:
    """Navigate Chrome to a URL.

    Args:
        url: Full URL to navigate to, e.g. 'https://youtube.com'.
    """
    try:
        _ensure_chrome()
        _osascript(f'tell application "Google Chrome" to open location "{url}"')
        return f"Navigated to {url}"
    except Exception as e:
        return f"Error navigating to {url}: {e}"


@registry.tool
def browser_read_page() -> str:
    """Read the visible text content of the current page in Chrome."""
    try:
        _ensure_chrome()
        js = "document.body.innerText.substring(0, 4000)"
        text = _osascript(
            f'tell application "Google Chrome" to tell active tab of front window '
            f'to execute javascript "{js}"'
        )
        return text or "(empty page)"
    except RuntimeError as e:
        if "Allow JavaScript from Apple Events" in str(e):
            return (
                "JavaScript is disabled for AppleScript. "
                "In Chrome, go to View > Developer > Allow JavaScript from Apple Events, then try again."
            )
        return f"Error reading page: {e}"


@registry.tool
def browser_click(text: str) -> str:
    """Click a visible element on the current Chrome page by its text content.

    Args:
        text: The visible text of the element to click, e.g. 'Sign in' or 'Subscribe'.
    """
    try:
        _ensure_chrome()
        safe = text.replace("'", "\\'").replace('"', '\\"')
        js = (
            "(function(){"
            f"var els=Array.from(document.querySelectorAll('a,button,input,[role=button],[role=link]'));"
            f"var el=els.find(e=>e.innerText&&e.innerText.toLowerCase().includes('{safe.lower()}'));"
            "if(el){el.click();return 'clicked';}return 'not found';"
            "})()"
        )
        result = _osascript(
            f'tell application "Google Chrome" to tell active tab of front window '
            f'to execute javascript "{js}"'
        )
        if result == "not found":
            return f"Could not find element with text '{text}' on the page."
        return f"Clicked '{text}'"
    except RuntimeError as e:
        if "Allow JavaScript from Apple Events" in str(e):
            return (
                "JavaScript is disabled for AppleScript. "
                "In Chrome, go to View > Developer > Allow JavaScript from Apple Events, then try again."
            )
        return f"Error clicking '{text}': {e}"
