"""@tool decorator: register a tool function once and derive its OpenAI / Groq
function schema from the signature + Google-style ("Args:") docstring.

A module creates a `Registry`, decorates its tool functions with `@registry.tool`,
and exposes the collected `fns` / `schemas` / `callables`. This replaces the
hand-maintained `TOOL_FNS` dict and `TOOL_SCHEMAS` list that used to duplicate
every function's name, description, and parameter docs.
"""
import inspect
import re
from typing import Callable, get_args, get_origin, Union

# Python annotation -> JSON-schema type. Anything unrecognised falls back to "string".
_PY_TO_JSON = {
    int: "integer",
    float: "number",
    bool: "boolean",
    str: "string",
    list: "array",
    dict: "object",
}


def _json_type(annotation) -> str:
    """Map a parameter annotation to a JSON-schema type name."""
    # Unwrap Optional[X] / X | None to X.
    if get_origin(annotation) is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            annotation = args[0]
    return _PY_TO_JSON.get(annotation, "string")


def _parse_doc(doc: str) -> tuple[str, dict[str, str]]:
    """Split a docstring into (summary, {arg_name: description})."""
    doc = inspect.cleandoc(doc or "")
    parts = re.split(r"\n\s*Args:\s*\n", doc, maxsplit=1)
    summary = " ".join(parts[0].split())
    arg_docs: dict[str, str] = {}
    if len(parts) == 2:
        for line in parts[1].splitlines():
            m = re.match(r"\s*(\w+)\s*:\s*(.*)", line)
            if m:
                arg_docs[m.group(1)] = m.group(2).strip()
    return summary, arg_docs


class Registry:
    """Collects the tool functions and generated schemas for one module."""

    def __init__(self) -> None:
        self.fns: dict[str, Callable] = {}
        self.schemas: list[dict] = []
        self.callables: list[Callable] = []

    def tool(self, fn: Callable | None = None, *, required: list[str] | None = None):
        """Register `fn` as a tool. Usable bare (`@registry.tool`) or with a
        `required=[...]` override for params whose required-ness shouldn't be
        inferred from the signature's defaults."""

        def decorate(func: Callable) -> Callable:
            summary, arg_docs = _parse_doc(func.__doc__)
            props: dict[str, dict] = {}
            inferred_required: list[str] = []
            for name, p in inspect.signature(func).parameters.items():
                prop = {"type": _json_type(p.annotation)}
                if name in arg_docs:
                    prop["description"] = arg_docs[name]
                props[name] = prop
                if p.default is inspect.Parameter.empty:
                    inferred_required.append(name)

            self.fns[func.__name__] = func
            self.callables.append(func)
            self.schemas.append({
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": summary,
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": required if required is not None else inferred_required,
                    },
                },
            })
            return func

        return decorate(fn) if fn is not None else decorate
