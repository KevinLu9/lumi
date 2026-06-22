"""Keyboard tools — type text into whatever field the user currently has focused.

Uses macOS System Events to paste at the cursor. Requires Accessibility permission for
the app that launched Lumi (System Settings > Privacy & Security > Accessibility).
"""
import subprocess
import time


def _osascript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def type_text(text: str) -> str:
    """Type text into wherever the cursor currently is — the focused app or text field.

    Use this to insert text the user dictated into another application, e.g. a document,
    email, code editor, or any text box the user has clicked into. The text is pasted at
    the current cursor position (replacing the current selection, if any).

    Args:
        text: The text to insert at the current cursor location.
    """
    try:
        # Paste via the clipboard for reliability with long / multiline / unicode text,
        # preserving and restoring whatever the user already had on the clipboard.
        old = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
        subprocess.run(["pbcopy"], input=text, text=True, check=True)
        time.sleep(0.05)
        _osascript('tell application "System Events" to keystroke "v" using command down')
        time.sleep(0.15)
        subprocess.run(["pbcopy"], input=old, text=True)
        return f"Typed {len(text)} characters at the cursor."
    except RuntimeError as e:
        msg = str(e).lower()
        if "not allowed" in msg or "assistive" in msg or "1002" in msg or "accessibility" in msg:
            return (
                "I need Accessibility permission to type for you. Enable it for your "
                "terminal (or the app running Lumi) under System Settings > Privacy & "
                "Security > Accessibility, then try again."
            )
        return f"Error typing text: {e}"
    except Exception as e:
        return f"Error typing text: {e}"


TOOL_FNS: dict = {
    "type_text": type_text,
}

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": (
                "Type text into wherever the cursor currently is — the focused app or "
                "text field. Use to insert dictated text into another application."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to insert at the current cursor location.",
                    }
                },
                "required": ["text"],
            },
        },
    },
]
