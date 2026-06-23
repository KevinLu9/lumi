"""Unified tool registry — auto-discovers every tool module in this package and
supports progressive disclosure (lazy tool loading) to keep the LLM's context small.

A tool module just needs a module-level `registry` (see `_registry.Registry`) with
`@registry.tool`-decorated functions. Drop the file in `backend/mcp/` and it's live —
no edits here. Optional conventions a module may set:
  * `REQUIRES_ENV = "SOME_VAR"` — load the module only when that env var is set.
  * `DESCRIPTION = "..."`       — short blurb shown in the loadable-modules catalog.

Progressive disclosure: only the *default* modules' tools (plus `find_tools`) are active
at the start of a conversation. The model loads more on demand by calling `find_tools`,
which calls `activate_matching`. `llm.py` passes only the active tools to the LLM and
injects `tool_catalog()` into the system prompt so the model knows what it can load.

`TOOL_FNS` / `TOOL_SCHEMAS` / `TOOL_CALLABLES` always hold *all* registered tools (used
for dispatch and by the standalone MCP server); the `active_*` views are the subset.
"""

import dataclasses
import importlib
import os
import pkgutil
import re

from ._registry import Registry

TOOL_FNS: dict = {}
TOOL_SCHEMAS: list[dict] = []
# Python callables passed to Gemini (it generates schemas from docstrings + type hints).
TOOL_CALLABLES: list = []

# Modules in this package that are not tool providers and must never be auto-imported.
_SKIP = {"registry", "server", "spotify_auth"}

# Modules whose tools are active from the start of every conversation. Everything else is
# loaded on demand via find_tools. (Add "browser"/"keyboard" here to make them default.)
DEFAULT_MODULES = {"tools"}


@dataclasses.dataclass
class ModuleEntry:
    name: str
    description: str
    tool_names: list[str]


MODULES: dict[str, ModuleEntry] = {}

# Names of the currently-active (loaded) tools, and a counter bumped on every change so
# llm.py can detect mid-turn activations and rebuild the Gemini chat with the new tools.
_active: set[str] = set()
active_version: int = 0


def _first_doc_line(module) -> str:
    doc = (module.__doc__ or "").strip()
    return doc.splitlines()[0].strip() if doc else module.__name__.rsplit(".", 1)[-1]


def _register(module) -> None:
    short = module.__name__.rsplit(".", 1)[-1]
    description = getattr(module, "DESCRIPTION", None) or _first_doc_line(module)
    MODULES[short] = ModuleEntry(short, description, list(module.registry.fns.keys()))
    TOOL_FNS.update(module.registry.fns)
    TOOL_SCHEMAS.extend(module.registry.schemas)
    TOOL_CALLABLES.extend(module.registry.callables)


def _discover() -> None:
    # Sorted for deterministic tool ordering regardless of filesystem order.
    for name in sorted(m.name for m in pkgutil.iter_modules([os.path.dirname(__file__)])):
        if name.startswith("_") or name in _SKIP:
            continue
        module = importlib.import_module(f"{__package__}.{name}")
        registry = getattr(module, "registry", None)
        if not isinstance(registry, Registry):
            continue
        required_env = getattr(module, "REQUIRES_ENV", None)
        if required_env and not os.environ.get(required_env):
            continue
        _register(module)


def reset_active() -> None:
    """Reset the active toolset to the defaults (called when the chat is cleared)."""
    global _active, active_version
    names: set[str] = set()
    for mod in DEFAULT_MODULES:
        if mod in MODULES:
            names.update(MODULES[mod].tool_names)
    _active = names
    active_version += 1


def active_schemas() -> list[dict]:
    return [s for s in TOOL_SCHEMAS if s["function"]["name"] in _active]


def active_callables() -> list:
    return [c for c in TOOL_CALLABLES if c.__name__ in _active]


def activate_matching(pattern: str) -> str:
    """Load every tool whose module name or tool name matches `pattern` (a regex).
    Returns a human-readable summary of what is now available (for the model to read)."""
    global active_version
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Invalid search pattern '{pattern}': {e}"

    matched: set[str] = set()
    for mod in MODULES.values():
        if rx.search(mod.name):
            matched.update(mod.tool_names)  # whole-module match
        else:
            matched.update(t for t in mod.tool_names if rx.search(t))

    if not matched:
        avail = ", ".join(sorted(m for m in MODULES if m not in DEFAULT_MODULES))
        return f"No tools matched '{pattern}'. Loadable modules: {avail or '(none)'}."

    newly = matched - _active
    _active.update(matched)
    if newly:
        active_version += 1

    desc_by = {s["function"]["name"]: s["function"].get("description", "") for s in TOOL_SCHEMAS}
    listing = "\n".join(f"- {n}: {desc_by.get(n, '')}" for n in sorted(matched))
    head = (
        f"Loaded {len(newly)} new tool(s)." if newly
        else "Those tools were already loaded."
    )
    return f"{head} Available now:\n{listing}"


def tool_catalog() -> str:
    """System-prompt blurb listing the loadable (non-default) modules and what they do."""
    extra = sorted((m for m in MODULES.values() if m.name not in DEFAULT_MODULES),
                   key=lambda m: m.name)
    if not extra:
        return ""
    lines = [
        f"- {m.name} — {m.description} ({len(m.tool_names)} tool{'s' if len(m.tool_names) != 1 else ''})"
        for m in extra
    ]
    return (
        "# Loadable tool modules\n"
        "You start with a small default toolset plus the find_tools tool. Additional tools "
        "are grouped into the modules below. When a task needs one, call "
        'find_tools(pattern) with a regex matched against module and tool names (e.g. '
        'find_tools(\"spotify\") to control music, find_tools(\"light\") for smart lights). '
        "Loaded tools stay available for the rest of the conversation.\n" + "\n".join(lines)
    )


_discover()
reset_active()
