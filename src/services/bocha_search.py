"""Bocha MCP online search integration."""
from __future__ import annotations

import os
from typing import Any, Dict, List

import requests


def _auth_header(value: str) -> str:
    if value.lower().startswith("bearer "):
        return value
    return f"Bearer {value}"


def bocha_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Call Bocha web search REST API (preferred) and normalize results."""
    api_key = os.getenv("BOCHA_API_KEY")
    if not api_key:
        raise RuntimeError("BOCHA_API_KEY is required")

    endpoint = os.getenv("BOCHA_API_ENDPOINT", "https://api.bocha.cn/v1/web-search")
    headers = {
        "Content-Type": "application/json",
        "Authorization": _auth_header(api_key),
        "Accept": "application/json",
    }
    payload = {
        "query": query,
        "count": top_k,
        "summary": True,
        "freshness": "noLimit",
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()

    results = data.get("data") or data.get("results") or []
    normalized: List[Dict[str, Any]] = []
    if isinstance(results, list):
        for item in results:
            normalized.append(
                {
                    "title": item.get("title", ""),
                    "content": item.get("snippet") or item.get("summary") or item.get("content", ""),
                    "url": item.get("url") or item.get("link") or "",
                }
            )
    return normalized
