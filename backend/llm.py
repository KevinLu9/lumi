import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv
from typing import Callable
import sys
import json
import re
import os
import threading

from . import events

LUMI_COLOR = "\033[35m"   # magenta
RESET      = "\033[0m"

load_dotenv()

PROVIDER     = os.environ.get("LLM_PROVIDER", "gemini").lower()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
GROQ_MODEL   = os.environ.get("GROQ_MODEL",   "meta-llama/llama-4-scout-17b-16e-instruct")

SYSTEM_PROMPT = open(os.path.join(os.path.dirname(__file__), "lumi.md")).read()


def _system_prompt() -> str:
    """Base prompt plus the loadable-tool catalog and anything Lumi remembers about
    the user (so saved memories are used proactively, not just on explicit recall)."""
    from .mcp import registry as reg
    from .mcp.memory import memory_block
    sections = [SYSTEM_PROMPT, reg.tool_catalog(), memory_block()]
    return "\n\n".join(s for s in sections if s)


_cancel = threading.Event()

# Gemini state
_gemini_chat = None

# Groq state
_groq_client: Groq | None = None
_groq_history: list[dict] = []
_groq_pending_clear = False


def cancel():
    _cancel.set()


def clear_history():
    global _gemini_chat, _groq_pending_clear
    from .mcp import registry as reg
    reg.reset_active()  # forget any tools loaded via find_tools; back to the default set
    events.emit("tools_active", names=reg.active_tool_names())
    if PROVIDER == "groq":
        # Defer the actual clear — calling this mid-tool-loop would corrupt the
        # in-progress conversation turn. _ask_groq clears at the start of the next call.
        _groq_pending_clear = True
    else:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=_system_prompt(),
            tools=reg.active_callables(),
        )
        _gemini_chat = model.start_chat(history=[])


# Token accounting. We sum usage across every API call in a turn (each tool round is a
# separate request that re-sends the growing context), so these are per-turn totals.
def _new_usage() -> dict:
    return {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "reasoning": 0}


def _add_groq_usage(acc: dict, usage) -> None:
    if not usage:
        return
    acc["input"] += getattr(usage, "prompt_tokens", 0) or 0
    acc["output"] += getattr(usage, "completion_tokens", 0) or 0
    if ptd := getattr(usage, "prompt_tokens_details", None):
        acc["cache_read"] += getattr(ptd, "cached_tokens", 0) or 0
    if ctd := getattr(usage, "completion_tokens_details", None):
        acc["reasoning"] += getattr(ctd, "reasoning_tokens", 0) or 0


def _add_gemini_usage(acc: dict, md) -> None:
    if not md:
        return
    acc["input"] += getattr(md, "prompt_token_count", 0) or 0
    acc["output"] += getattr(md, "candidates_token_count", 0) or 0
    acc["cache_read"] += getattr(md, "cached_content_token_count", 0) or 0
    acc["reasoning"] += getattr(md, "thoughts_token_count", 0) or 0


# Tools that render their own UI (via a dedicated event) and so don't need the generic
# tool-call collapsible in the chat.
_SELF_RENDERED = {"get_forecast"}


def _execute_tool(name: str, args: dict) -> str:
    from .mcp import registry as reg
    fn = reg.TOOL_FNS.get(name)
    if not fn:
        events.emit("tool_call", name=name, args=args, result="Unknown tool")
        return f"Unknown tool: {name}"
    before = reg.active_version
    try:
        result = str(fn(**args))
    except Exception as e:
        result = f"Tool error: {e}"
    if name not in _SELF_RENDERED:
        events.emit("tool_call", name=name, args=args, result=result)
    # find_tools (or reset_chat) may have changed which tools are loaded — tell the UI.
    if reg.active_version != before:
        events.emit("tools_active", names=reg.active_tool_names())
    return result


def load():
    global _gemini_chat, _groq_client
    from .mcp import registry as reg
    if PROVIDER == "groq":
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("Set the GROQ_API_KEY environment variable")
        _groq_client = Groq(api_key=api_key)
    else:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("Set the GEMINI_API_KEY environment variable")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=_system_prompt(),
            tools=reg.active_callables(),
        )
        _gemini_chat = model.start_chat(history=[])


def _ask_gemini(text: str) -> tuple[str, dict]:
    global _gemini_chat
    from .mcp import registry as reg
    usage = _new_usage()
    response = _gemini_chat.send_message(text)
    _add_gemini_usage(usage, getattr(response, "usage_metadata", None))

    for _ in range(5):
        try:
            parts = response.candidates[0].content.parts
        except (IndexError, AttributeError):
            break

        fc_parts = [p for p in parts if hasattr(p, "function_call") and p.function_call.name]
        if not fc_parts:
            break

        before = reg.active_version
        fn_responses = []
        for part in fc_parts:
            fc = part.function_call
            result = _execute_tool(fc.name, dict(fc.args))
            fn_responses.append(genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=fc.name,
                    response={"result": result},
                )
            ))

        # If find_tools loaded new tools this round, rebuild the chat (preserving history)
        # so the model can call the freshly-loaded tools on its next turn.
        if reg.active_version != before:
            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=_system_prompt(),
                tools=reg.active_callables(),
            )
            _gemini_chat = model.start_chat(history=_gemini_chat.history)

        response = _gemini_chat.send_message(fn_responses)
        _add_gemini_usage(usage, getattr(response, "usage_metadata", None))

    try:
        text_out = "".join(
            p.text for p in response.candidates[0].content.parts
            if hasattr(p, "text") and p.text
        )
    except (IndexError, AttributeError):
        text_out = ""
    return text_out, usage


def _ask_groq(text: str) -> tuple[str, dict]:
    global _groq_pending_clear
    from .mcp import registry as reg
    usage = _new_usage()
    if _groq_pending_clear:
        _groq_history.clear()
        _groq_pending_clear = False
    _groq_history.append({"role": "user", "content": text})

    for _ in range(6):  # up to 5 tool rounds + final reply
        response = _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": _system_prompt()}] + _groq_history,
            tools=reg.active_schemas(),
        )
        _add_groq_usage(usage, getattr(response, "usage", None))
        message = response.choices[0].message

        if not message.tool_calls:
            _groq_history.append({"role": "assistant", "content": message.content})
            return message.content or "", usage

        _groq_history.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        })
        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            result = _execute_tool(tc.function.name, args)
            _groq_history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return "", usage


def _strip_markdown(text: str) -> str:
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', text)
    text = re.sub(r'`{1,3}[^`\n]*`{1,3}', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    return text


def ask(text: str, on_sentence: Callable[[str], None]):
    _cancel.clear()

    raw, usage = _ask_groq(text) if PROVIDER == "groq" else _ask_gemini(text)

    if _cancel.is_set():
        return

    events.emit("lumi_message", text=raw, usage=usage)
    sys.stdout.write(f"\r\033[K{LUMI_COLOR}Lumi:{RESET} {raw}\n")
    sys.stdout.flush()

    # Strip <silent> blocks from TTS but keep them visible in the terminal output above.
    tts_text = re.sub(r'<silent>.*?</silent>', '', raw, flags=re.DOTALL)
    tts_text = re.sub(r'<silent>.*', '', tts_text, flags=re.DOTALL)
    tts_text = _strip_markdown(tts_text).strip()

    # Feed sentences to TTS one at a time.
    while tts_text and not _cancel.is_set():
        match = re.search(r'[.!?]["\']?\s+', tts_text)
        if not match:
            break
        sentence = tts_text[:match.end()].strip()
        tts_text = tts_text[match.end():]
        if sentence:
            on_sentence(sentence)

    if tts_text.strip() and not _cancel.is_set():
        on_sentence(tts_text.strip())
