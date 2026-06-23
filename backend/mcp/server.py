"""Standalone FastMCP server — run with: python -m backend.mcp.server (from repo root).
Connectable from Claude Desktop or any MCP client via stdio.

Tools are derived from the shared registry (see `_registry.Registry`), so this server
exposes exactly the same tools as Lumi's in-app LLM loop — including the optional Spotify
and Tuya integrations, which `registry` only loads when their env vars are set.
"""

from fastmcp import FastMCP
from .registry import TOOL_CALLABLES

mcp = FastMCP("lumi-tools")
for _fn in TOOL_CALLABLES:
    mcp.add_tool(_fn)


if __name__ == "__main__":
    mcp.run()
