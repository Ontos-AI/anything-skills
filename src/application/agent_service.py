"""Application service for orchestrating agents."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, List, Optional, Dict, Any

from src.application.stream_processor import build_event
from src.core_agents.orchestrator import Orchestrator
from src.services.tool_registry import ToolRegistry
from src.services.agent_middleware import apply_middlewares


async def run_augmented_stream(
    task: str,
    sources: Optional[List[str]] = None,
    middlewares=None,
    max_rounds: int = 2,
) -> AsyncIterator[Dict[str, Any]]:
    sources = sources or []
    middlewares = middlewares or []
    queue: asyncio.Queue[Dict[str, Any] | None] = asyncio.Queue()

    async def emit(agent: str, stage: str, message: str, payload: Dict[str, Any] | None = None) -> None:
        # Force augmented lane to keep UI mapping intact.
        event = build_event("augmented", stage, f"[{agent}] {message}", payload)
        event = apply_middlewares(event, middlewares)
        await queue.put(event)

    async def runner() -> None:
        tools = ToolRegistry()
        orchestrator = Orchestrator(max_rounds=max_rounds)
        result = await orchestrator.run(task, sources, tools, emit)
        await emit("orchestrator", "done", f"Workflow completed: {result.status}", {"result": result.model_dump()})
        await queue.put(None)

    task_runner = asyncio.create_task(runner())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        if not task_runner.done():
            task_runner.cancel()
