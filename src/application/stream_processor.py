"""Stream event normalization for SSE."""
from __future__ import annotations

import time
from typing import Dict, Any


def build_event(agent: str, stage: str, message: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "agent": agent,
        "stage": stage,
        "message": message,
        "payload": payload or {},
        "timestamp": time.time(),
    }
