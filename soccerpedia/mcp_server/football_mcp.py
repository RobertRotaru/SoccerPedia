"""Soccerpedia MCP server.

Exposes the football tool layer (football-data.org, API-Football, Transfermarkt,
Wikipedia) over the Model Context Protocol, so any MCP client can use it:
the Soccerpedia LangChain agent, Claude Desktop, Cursor, the MCP Inspector, ...

Run it:
    python -m mcp_server.football_mcp                      # stdio (default)
    python -m mcp_server.football_mcp --transport http     # streamable HTTP on :8000/mcp
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import os
import sys

from dotenv import load_dotenv

# Make `config` and `agent` importable no matter where the server is launched from.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from mcp.server.fastmcp import FastMCP  # noqa: E402

from agent import tools as football_tools  # noqa: E402

# The tools the server publishes. Each one is a LangChain @tool; we register the
# underlying Python function so MCP derives the JSON schema from its signature
# and docstring - one source of truth for both the agent and external clients.
EXPOSED_TOOLS = [
    football_tools.get_current_date,
    football_tools.get_latest_matches_live,
    football_tools.get_league_standings_live,
    football_tools.get_upcoming_matches,
    football_tools.get_live_matches,
    football_tools.get_player_career_stats_live,
    football_tools.compare_players_live,
    football_tools.get_transfer_news_live,
    football_tools.get_players_multi_club_career,
    football_tools.search_football_info,
]


def _stdout_safe(fn):
    """Route stray print() output to stderr.

    Over the stdio transport, stdout *is* the JSON-RPC channel, so any debug
    print inside a data source would corrupt the protocol stream.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with contextlib.redirect_stdout(sys.stderr):
            return fn(*args, **kwargs)

    return wrapper


def build_server(host: str = "127.0.0.1", port: int = 8000) -> FastMCP:
    server = FastMCP(
        "soccerpedia",
        instructions=(
            "Live football data: results, fixtures, standings, player careers, "
            "transfers and head-to-head comparisons. League codes: PL, PD, BL1, "
            "SA, FL1, CL, EL, WC."
        ),
        host=host,
        port=port,
    )
    for lc_tool in EXPOSED_TOOLS:
        server.add_tool(
            _stdout_safe(lc_tool.func),
            name=lc_tool.name,
            description=lc_tool.description,
        )
    return server


mcp = build_server()


def main() -> None:
    parser = argparse.ArgumentParser(description="Soccerpedia MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "http":
        build_server(args.host, args.port).run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
