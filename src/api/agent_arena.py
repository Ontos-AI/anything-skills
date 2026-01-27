"""Agent Arena routes for task comparison."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from src.services.agent_middleware import apply_middlewares, BuiltinMiddleware, TerminalMiddleware
from src.application.agent_service import run_augmented_stream


router = APIRouter()


@router.get("/agent-arena", response_class=HTMLResponse)
async def agent_arena_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("agent_arena.html", {"request": request})


def _normalize_sources(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]

async def _emit(agent: str, stage: str, message: str, middlewares) -> Dict[str, Any]:
    event = {"agent": agent, "stage": stage, "message": message}
    return apply_middlewares(event, middlewares)


async def _simple_agent(task: str, sources: List[str], middlewares) -> AsyncIterator[Dict[str, Any]]:
    yield await _emit("simple", "plan", "Summarize task and pick the fastest path.", middlewares)
    await asyncio.sleep(0.2)
    yield await _emit("simple", "action", f"Task: {task}", middlewares)
    await asyncio.sleep(0.2)
    if "skills.sh" in sources:
        yield await _emit("simple", "action", "Do a quick skills.sh keyword search.", middlewares)
        await asyncio.sleep(0.2)
    if "github" in sources:
        yield await _emit("simple", "action", "Scan top GitHub repos by stars.", middlewares)
        await asyncio.sleep(0.2)
    if "youtube" in sources or "bilibili" in sources:
        yield await _emit("simple", "action", "Skim video metadata only.", middlewares)
        await asyncio.sleep(0.2)
    summary = (
        "Skill outline:\n"
        "- Goal: browser automation\n"
        "- Tools: Playwright/Selenium\n"
        "- Steps: plan -> find sources -> draft SKILL.md\n"
    )
    yield await _emit("simple", "observation", summary, middlewares)
    yield await _emit("simple", "done", "Finished minimal pass.", middlewares)


async def _system_agent(task: str, sources: List[str], middlewares) -> AsyncIterator[Dict[str, Any]]:
    async for event in run_augmented_stream(task, sources=sources, middlewares=middlewares):
        yield event


@router.get("/api/agent-arena/stream")
async def agent_arena_stream(task: str, sources: Optional[str] = None):
    if not task.strip():
        raise HTTPException(status_code=400, detail="task is required")

    source_list = _normalize_sources(sources)
    middlewares = [BuiltinMiddleware(), TerminalMiddleware()]

    async def event_stream() -> AsyncIterator[str]:
        async for event in _simple_agent(task, source_list, middlewares):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        async for event in _system_agent(task, source_list, middlewares):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
