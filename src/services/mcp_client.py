"""Minimal MCP HTTP client (JSON-RPC over HTTP)."""
from __future__ import annotations

import itertools
from typing import Any, Dict, List

import requests


class MCPHttpClient:
    def __init__(self, url: str, headers: Dict[str, str]) -> None:
        self.url = url
        self.headers = headers
        self._id_iter = itertools.count(1)

    def _rpc(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": next(self._id_iter),
            "method": method,
            "params": params or {},
        }
        headers = {"Accept": "application/json", **self.headers}
        response = requests.post(self.url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result", {})

    def list_tools(self) -> List[Dict[str, Any]]:
        result = self._rpc("tools/list")
        return result.get("tools", []) or []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._rpc("tools/call", {"name": name, "arguments": arguments})
