"""End-to-end: the agent discovers tools from the real MCP server (stdio) and
calls one. The LLM is faked so no OpenAI key or network is needed."""
from datetime import datetime

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent.agent_factory import build_agent, load_mcp_tools


class ToolCallingFake(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


async def test_agent_calls_tool_through_mcp():
    tools = await load_mcp_tools()  # spawns mcp_server as a subprocess
    assert "get_league_standings_live" in {t.name for t in tools}

    model = ToolCallingFake(messages=iter([
        AIMessage(content="", tool_calls=[{"name": "get_current_date", "args": {}, "id": "call_1"}]),
        AIMessage(content="done"),
    ]))
    agent = build_agent(model=model, tools=tools)
    result = await agent._graph.ainvoke({"messages": [{"role": "user", "content": "what day is it?"}]})

    tool_msgs = [m for m in result["messages"] if m.type == "tool"]
    assert tool_msgs, "the agent never executed a tool"
    assert datetime.now().strftime("%Y-%m-%d") in str(tool_msgs[0].content)
    assert result["messages"][-1].content == "done"
