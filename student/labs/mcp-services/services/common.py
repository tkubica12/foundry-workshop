import copy
import hashlib
import hmac
import os
from threading import RLock
from typing import Annotated, Generic, TypeVar

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from starlette.middleware import Middleware

T = TypeVar("T", bound=BaseModel)
Limit = Annotated[int, Field(ge=1, le=100)]
Offset = Annotated[int, Field(ge=0)]
Version = Annotated[int, Field(ge=1)]


class FixedKeyVerifier(TokenVerifier):
    def __init__(self, key: str):
        super().__init__()
        if not key or len(key) < 12 or any(c.isspace() for c in key):
            raise ValueError("MCP_API_KEY must contain at least 12 non-whitespace characters")
        self._digest = hashlib.sha256(key.encode()).digest()

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(hashlib.sha256(token.encode()).digest(), self._digest):
            return AccessToken(token=token, client_id="workshop-client", scopes=["tools"])
        return None


def server(name: str) -> FastMCP:
    mcp = FastMCP(name, auth=FixedKeyVerifier(os.environ.get("MCP_API_KEY", "")))

    @mcp.custom_route("/healthz", methods=["GET"])
    async def health(request):
        return JSONResponse({"status": "ok", "service": name, "data": "synthetic-in-memory"})

    return mcp


class KeyBoundary:
    def __init__(self, app):
        self.app = app
        self.digest = hashlib.sha256(os.environ["MCP_API_KEY"].encode()).digest()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
            headers = dict(scope["headers"])
            value = headers.get(b"authorization", b"")
            scheme, _, token = value.partition(b" ")
            if scheme.lower() != b"bearer" or not hmac.compare_digest(hashlib.sha256(token).digest(), self.digest):
                response = JSONResponse({"error": "Unauthorized"}, status_code=401,
                                        headers={"WWW-Authenticate": "Bearer"})
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def http_app(mcp: FastMCP):
    return mcp.http_app(stateless_http=True, json_response=True, middleware=[Middleware(KeyBoundary)])


class Store(Generic[T]):
    def __init__(self, rows: list[T]):
        self.rows = {row.id: row for row in rows}
        self.lock = RLock()

    def get(self, identifier: str) -> T:
        with self.lock:
            if identifier not in self.rows:
                raise ToolError(f"Not found: {identifier}")
            return copy.deepcopy(self.rows[identifier])

    def check(self, identifier: str, expected_version: int) -> T:
        row = self.get(identifier)
        if row.version != expected_version:
            raise ToolError(f"Version conflict: expected {expected_version}, current {row.version}; fetch and retry")
        return row

    def page(self, rows: list[T], offset: int, limit: int) -> dict:
        ordered = sorted(rows, key=lambda row: row.id)
        end = offset + limit
        return {"items": [row.model_dump(mode="json") for row in ordered[offset:end]],
                "total": len(ordered), "offset": offset, "limit": limit,
                "next_offset": end if end < len(ordered) else None}

    def delete(self, identifier: str, expected_version: int) -> dict:
        with self.lock:
            self.check(identifier, expected_version)
            del self.rows[identifier]
            return {"deleted": True, "id": identifier}
