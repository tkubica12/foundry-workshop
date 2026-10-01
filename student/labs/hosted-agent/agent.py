"""A small LangGraph workflow with an explicit per-call approval boundary."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urlsplit

import httpx
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain.agents import create_agent
from langchain_core.tools import BaseTool, ToolException
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest, MCPToolCallResult
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import interrupt

SCOPE = "https://ai.azure.com/.default"
TOOLS = {
    "get_partner", "search_partners", "get_complaint", "search_complaints",
    "create_complaint", "assign_complaint", "add_complaint_note",
}
READ_TOOLS = {"get_partner", "search_partners", "get_complaint", "search_complaints"}
SYSTEM_PROMPT = (Path(__file__).parent / "system-prompt.txt").read_text(encoding="utf-8")


def tool_basename(name: str) -> str:
    return name.rsplit("___", 1)[-1]


def select_tools(discovered: list[BaseTool]) -> list[BaseTool]:
    selected = [tool for tool in discovered if tool_basename(tool.name) in TOOLS]
    names = [tool_basename(tool.name) for tool in selected]
    if len(names) != len(set(names)) or set(names) != TOOLS:
        raise RuntimeError("Expected exactly the seven Lab 4 tools; missing or duplicate tools")
    return selected


async def approve_call(
    request: MCPToolCallRequest,
    handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
) -> MCPToolCallResult:
    name = tool_basename(request.name)
    if name not in READ_TOOLS:
        raise ToolException("LAB07_WRITE_DENIED: this hosted-agent exercise is read-only")
    decision = {"tool": request.name, "arguments": request.args, "approval": "once"}
    approved = interrupt(decision)
    if approved != decision:
        raise ToolException("LAB07_APPROVAL_DENIED: exact tool and arguments were not approved")
    # No remote side effect occurs before the checkpointed approval.
    return await handler(request)


class EntraAuth(httpx.Auth):
    def __init__(self, credential: DefaultAzureCredential):
        self._token = get_bearer_token_provider(credential, SCOPE)

    def auth_flow(self, request):
        request.headers["Authorization"] = "Bearer " + self._token()
        yield request


def require_https(value: str, *, foundry: bool = False) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("A credential-free HTTPS endpoint is required")
    if foundry and not parsed.hostname.endswith(".services.ai.azure.com"):
        raise ValueError("The toolbox must be on a Foundry project endpoint")
    return value


def mcp_client(credential: DefaultAzureCredential) -> MultiServerMCPClient:
    toolbox = os.environ.get("TOOLBOX_ENDPOINT")
    if toolbox:
        connections = {"toolbox": {
            "transport": "streamable_http",
            "url": require_https(toolbox, foundry=True),
            "headers": {"Foundry-Features": "Toolsets=V1Preview"},
            "auth": EntraAuth(credential),
            "timeout": 60,
            "sse_read_timeout": 90,
        }}
    else:
        key = os.environ["MCP_API_KEY"]
        if not key or key.startswith("${{"):
            raise ValueError("MCP credential connection did not resolve")
        connections = {
            name: {
                "transport": "streamable_http",
                "url": require_https(os.environ[variable]),
                "headers": {"Authorization": "Bearer " + key},
                "timeout": 60,
                "sse_read_timeout": 90,
            }
            for name, variable in (("partners", "PARTNERS_MCP_URL"), ("complaints", "COMPLAINTS_MCP_URL"))
        }
    return MultiServerMCPClient(
        connections, tool_interceptors=[approve_call], handle_tool_errors=False,
    )


def build_graph(model, tools: list[BaseTool], checkpointer, callbacks=None):
    graph = create_agent(
        model=model, tools=select_tools(tools), system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer, name="workshop-langgraph",
    )
    return graph.with_config({"callbacks": callbacks or [], "recursion_limit": 20})


async def serve() -> None:
    from langchain_openai import ChatOpenAI
    from langchain_azure_ai.agents.hosting import FoundryCheckpointSaver, ResponsesHostServer
    from langchain_azure_ai.callbacks.tracers import AzureAIOpenTelemetryTracer

    credential = DefaultAzureCredential()
    endpoint = require_https(os.environ["FOUNDRY_PROJECT_ENDPOINT"], foundry=True)
    with AIProjectClient(endpoint=endpoint, credential=credential, allow_preview=True) as project:
        with project.get_openai_client() as client:
            model = ChatOpenAI(
                model=os.environ["MODEL_DEPLOYMENT_NAME"],
                base_url=str(client.base_url),
                api_key=get_bearer_token_provider(credential, SCOPE),
                use_responses_api=True, max_retries=0, timeout=90,
            )
            tools = await mcp_client(credential).get_tools()
            tracer = AzureAIOpenTelemetryTracer(
                name="workshop-langgraph",
                agent_id=os.environ.get("FOUNDRY_AGENT_NAME"),
                enable_content_recording=os.environ.get("LAB07_RECORD_CONTENT") == "true",
                trace_all_langgraph_nodes=True,
                auto_configure_azure_monitor=False,
            )
            port = int(os.environ.get("PORT", "8088"))
            if os.environ.get("FOUNDRY_AGENT_NAME"):
                graph = build_graph(model, tools, FoundryCheckpointSaver(endpoint=endpoint), [tracer])
                await ResponsesHostServer(graph).run_async(port=port)
            else:
                state = Path(os.environ.get("LAB07_STATE_DIR", str(Path.home() / ".agentserver" / "lab07")))
                state.mkdir(parents=True, exist_ok=True)
                async with AsyncSqliteSaver.from_conn_string(str(state / "checkpoints.sqlite")) as saver:
                    graph = build_graph(model, tools, saver, [tracer])
                    await ResponsesHostServer(graph).run_async(host="127.0.0.1", port=port)


if __name__ == "__main__":
    asyncio.run(serve())
