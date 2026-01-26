"""Agent middleware helpers for streaming logs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Dict, Any
import time


Event = Dict[str, Any]
Middleware = Callable[[Event], Event]


@dataclass
class BuiltinMiddleware:
    """Adds timestamps and stage normalization."""

    def __call__(self, event: Event) -> Event:
        event.setdefault("timestamp", time.time())
        event["stage"] = str(event.get("stage", "info")).lower()
        event.setdefault("kind", _map_stage_to_kind(event["stage"]))
        return event


@dataclass
class TerminalMiddleware:
    """Ensures terminal events are marked for the UI."""

    def __call__(self, event: Event) -> Event:
        if event.get("stage") == "done":
            event["terminal"] = True
        return event


def _map_stage_to_kind(stage: str) -> str:
    if stage in {"plan", "thought"}:
        return "thought"
    if stage in {"action", "search", "extract"}:
        return "action"
    return "observation"


def apply_middlewares(event: Event, middlewares: Iterable[Middleware]) -> Event:
    for middleware in middlewares:
        event = middleware(event)
    return event
