---
name: adding-tools
description: How to add a new tool (or tool module) to Lumi's backend. Use when creating, adding, or registering a tool/integration in backend/mcp — covers the @registry.tool decorator, the new-file boilerplate, REQUIRES_ENV, DESCRIPTION, auto-discovery, and how tools reach both the LLM loop and the MCP server.
---

# Adding tools to Lumi

Lumi's tools live in `backend/mcp/`. Each file is a **tool module**: a `Registry`
plus functions decorated with `@registry.tool`. The decorator generates the LLM tool
schema from the function's signature and docstring, so there is **no schema to write by
hand** and **no central list to edit** — `registry.py` auto-discovers modules in the
package.

A registered tool automatically becomes available to **both**:
- Lumi's in-app LLM loop (Groq / Gemini), via `TOOL_FNS` / `TOOL_SCHEMAS` / `TOOL_CALLABLES`.
- The standalone MCP server (`server.py`), exposed to external clients like Claude Desktop.

## Adding a tool to an existing module

Open the relevant file (e.g. `backend/mcp/browser.py`) and add a decorated function:

```python
@registry.tool
def browser_scroll(direction: str = "down") -> str:
    """Scroll the current Chrome page up or down.

    Args:
        direction: Either 'up' or 'down'.
    """
    ...
    return "Scrolled down."
```

That's it — it's live on next start. No other edits.

## Adding a whole new tool file

Create `backend/mcp/<name>.py`. Minimum boilerplate:

```python
"""One-line summary of what this module does (used as the catalog blurb if no DESCRIPTION)."""

from ._registry import Registry

registry = Registry()
DESCRIPTION = "Short blurb shown in the loadable-tools catalog."
# REQUIRES_ENV = "SOME_API_KEY"   # optional — see below


@registry.tool
def my_tool(query: str, limit: int = 5) -> str:
    """What the tool does — this sentence becomes the tool's description.

    Args:
        query: What to search for.
        limit: How many results to return.
    """
    ...
    return "result string"
```

Drop the file in `backend/mcp/` and it is discovered automatically — **you do not edit
`registry.py`, `server.py`, `app.py`, or `llm.py`.**

## How the schema is generated

`@registry.tool` builds the OpenAI/Groq function schema from the function itself:

- **Description** = the first line (summary) of the docstring.
- **Parameters** = the function's parameters. Each param's JSON type comes from its type
  hint (`int`→`integer`, `float`→`number`, `bool`→`boolean`, `str`→`string`,
  `list`→`array`, `dict`→`object`; anything else → `string`).
- **Param descriptions** = the `Args:` lines (Google-style docstring).
- **Required params** = those **without** a default value. Params with a default are
  optional.

Conventions to follow:
- Always write a docstring with a one-line summary and an `Args:` entry per parameter.
- Add type hints to every parameter.
- **Return a `str`** — it's read back to the user and spoken via TTS, so keep it short and
  natural. Catch errors and return a friendly message rather than raising.
- Use a clear, unique, snake_case function name (it's the tool name the LLM calls).

### `required=` override (rare)

If a parameter has a default but should still be advertised as required, pass it
explicitly:

```python
@registry.tool(required=["warmth"])
def light_set_white(warmth: str = "neutral", name: str = "") -> str:
    ...
```

## `DESCRIPTION`

`DESCRIPTION = "..."` is a short, human-readable blurb for the module. It appears in the
**loadable-tools catalog** that is injected into the LLM's system prompt and in the
"Tools" panel in the UI. If you omit it, the first line of the module's docstring is used
instead. Keep it to one sentence describing the module's capability.

## `REQUIRES_ENV`

`REQUIRES_ENV = "SOME_VAR"` gates the whole module: its tools are registered **only when
that environment variable is set** (loaded from `.env`). Use it for optional integrations
that need credentials. Examples: `spotify.py` sets `REQUIRES_ENV = "SPOTIFY_CLIENT_ID"`,
`tuya.py` sets `REQUIRES_ENV = "TUYA_DEVICE_ID"`. With the var unset, the module is skipped
entirely and never appears to the LLM, the catalog, or the MCP server. Omit `REQUIRES_ENV`
for tools that should always be available (subject to the loading rules below).

## Loading: `tools.py` is always loaded; everything else is on-demand

Lumi uses **progressive disclosure** to keep the LLM's context small. Only the modules in
`DEFAULT_MODULES` (currently just **`tools`**) are active at the start of a conversation —
`backend/mcp/tools.py` is **always loaded**, along with the `find_tools` meta-tool that
lives in it.

Every other module (browser, keyboard, spotify, tuya, and any you add) is **not** in the
LLM's context until the model calls `find_tools("<regex>")`, which matches against module
and tool names and loads the matches for the rest of the conversation. The catalog
injected into the system prompt tells the model what it can load.

Implications when adding a module:
- Put genuinely core, always-available utilities in `tools.py`.
- A new file you create is **lazy by default** — the model must `find_tools(...)` it. To
  make a module always-active instead, add its name to `DEFAULT_MODULES` in `registry.py`
  (one-line change).
- Give tools and the module names/descriptions that make them easy to find by regex (the
  model searches the catalog blurb conceptually and matches `find_tools` against names).

## What you do NOT touch

`registry.py` auto-discovers modules via `pkgutil`, skipping names that start with `_` and
the reserved set `{"registry", "server", "spotify_auth"}`. A module is registered only if
it defines a `registry` (a `Registry` instance) and passes its `REQUIRES_ENV` check. So
adding tools never requires editing `registry.py`, `server.py`, `app.py`, or `llm.py` —
unless you are intentionally changing `DEFAULT_MODULES`.

## Quick checklist

- [ ] File in `backend/mcp/`, not starting with `_`.
- [ ] `registry = Registry()` and functions decorated with `@registry.tool`.
- [ ] Docstring summary + `Args:` line per param; type hints on every param.
- [ ] Functions return a short, natural `str`; errors handled gracefully.
- [ ] `DESCRIPTION` set (one sentence).
- [ ] `REQUIRES_ENV` set if the module needs credentials.
- [ ] Decide default vs. lazy: core utilities go in `tools.py`; otherwise it's loaded on
      demand via `find_tools` (or add to `DEFAULT_MODULES`).
