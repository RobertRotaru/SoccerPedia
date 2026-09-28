#!/usr/bin/env bash
# Start the MCP server over HTTP and the Streamlit UI pointed at it.
set -euo pipefail
cd "$(dirname "$0")"
python -m mcp_server.football_mcp --transport http --port 8000 &
MCP_PID=$!
trap 'kill $MCP_PID' EXIT
SOCCERPEDIA_MCP_URL=http://localhost:8000/mcp streamlit run gui/app.py
