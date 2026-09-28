"""The MCP server must publish the whole tool layer with usable schemas."""
from mcp_server.football_mcp import EXPOSED_TOOLS, mcp


async def test_all_tools_are_published():
    published = {t.name for t in await mcp.list_tools()}
    assert published == {t.name for t in EXPOSED_TOOLS}


async def test_tool_schemas_come_from_signatures():
    tools = {t.name: t for t in await mcp.list_tools()}
    standings = tools["get_league_standings_live"].inputSchema
    assert standings["required"] == ["league"]
    assert "season" in standings["properties"]
    assert tools["get_league_standings_live"].description


async def test_call_tool_over_mcp():
    result = await mcp.call_tool("get_current_date", {})
    content = result[0] if isinstance(result, tuple) else result
    text = content[0].text
    assert len(text) == 10 and text[4] == "-"  # YYYY-MM-DD
