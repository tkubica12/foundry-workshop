import asyncio
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool, ToolException
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import READ_TOOLS, TOOLS, approve_call, build_graph, require_https, select_tools


class ToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def make_tool(name):
    return StructuredTool.from_function(lambda: name, name=name, description=name)


def test_inventory_filters_extra_tools_and_rejects_duplicates():
    tools = [make_tool("partners___" + name) for name in TOOLS]
    assert len(select_tools(tools + [make_tool("delete_complaint")])) == 7
    with pytest.raises(RuntimeError):
        select_tools(tools[:-1])
    with pytest.raises(RuntimeError):
        select_tools(tools + [make_tool("get_partner")])


@pytest.mark.parametrize("name", sorted(TOOLS - READ_TOOLS))
def test_mutations_are_denied_before_any_remote_call(name):
    calls = []

    async def handler(request):
        calls.append(request)

    with pytest.raises(ToolException, match="WRITE_DENIED"):
        asyncio.run(approve_call(MCPToolCallRequest(name, {}, "test"), handler))
    assert not calls


def test_read_pauses_until_exact_approval_then_calls_once():
    calls = []

    async def read():
        request = MCPToolCallRequest("get_partner", {}, "partners")

        async def handler(request):
            calls.append(request)
            return "partner-001"

        return await approve_call(request, handler)

    tools = [StructuredTool.from_function(
        coroutine=read, name=name, description=name,
    ) if name == "get_partner" else make_tool(name) for name in TOOLS]
    model = ToolModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "get_partner", "args": {}, "id": "call-1"}]),
        AIMessage(content="partner-001"),
    ])
    graph = build_graph(model, tools, InMemorySaver())
    config = {"configurable": {"thread_id": "test-approved"}}

    async def journey():
        pending = await graph.ainvoke({"messages": [HumanMessage(content="Read the partner")]}, config)
        assert calls == []
        approval = pending["__interrupt__"][0].value
        assert approval == {"tool": "get_partner", "arguments": {}, "approval": "once"}
        result = await graph.ainvoke(Command(resume=approval), config)
        assert result["messages"][-1].content == "partner-001"
        assert len(calls) == 1

    asyncio.run(journey())


def test_forged_approval_does_not_call_remote():
    calls = []

    async def read():
        async def handler(request):
            calls.append(request)
            return "should-not-run"
        return await approve_call(MCPToolCallRequest("get_partner", {}, "partners"), handler)

    tools = [StructuredTool.from_function(coroutine=read, name=name, description=name)
             if name == "get_partner" else make_tool(name) for name in TOOLS]
    model = ToolModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "get_partner", "args": {}, "id": "call-1"}]),
    ])
    graph = build_graph(model, tools, InMemorySaver())
    config = {"configurable": {"thread_id": "test-forged"}}

    async def journey():
        await graph.ainvoke({"messages": [HumanMessage(content="Read")]}, config)
        with pytest.raises(ToolException, match="APPROVAL_DENIED"):
            await graph.ainvoke(Command(resume={"approved": True}), config)
        assert calls == []

    asyncio.run(journey())


@pytest.mark.parametrize("url", ["http://example.com", "https://user:pass@example.com", "https://example.com"])
def test_toolbox_refuses_untrusted_credential_destinations(url):
    with pytest.raises(ValueError):
        require_https(url, foundry=True)
