"""Offline protocol fixture: never used by the deployed image entry point."""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain_azure_ai.agents.hosting import ResponsesHostServer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path.cwd()))
from agent import TOOLS, approve_call, build_graph


class FixtureModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


async def read():
    async def handler(request):
        return "fixture-partner-001"
    return await approve_call(MCPToolCallRequest("get_partner", {}, "partners"), handler)


async def serve():
    tools = [StructuredTool.from_function(coroutine=read, name=name, description=name)
             for name in TOOLS]
    model = FixtureModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "get_partner", "args": {}, "id": "fixture-call-1"}]),
        AIMessage(content="fixture-partner-001"),
    ])
    with tempfile.TemporaryDirectory(prefix="lab07-protocol-") as temporary:
        async with AsyncSqliteSaver.from_conn_string(str(Path(temporary) / "checkpoints.sqlite")) as saver:
            graph = build_graph(model, tools, saver)
            await ResponsesHostServer(graph).run_async(
                host=os.environ.get("LAB07_TEST_HOST", "127.0.0.1"), port=8088,
            )


if __name__ == "__main__":
    asyncio.run(serve())
