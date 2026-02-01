"""Agent Arena routes for task comparison."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, Response

from src.services.agent_middleware import apply_middlewares, BuiltinMiddleware, TerminalMiddleware
from src.application.agent_service import run_augmented_stream
from src.core.config import config


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


@router.get("/api/agent-arena/skills")
async def list_generated_skills():
    """List all generated skills available for download."""
    skills_dir = config.SKILLS_DIR
    skills = []
    if skills_dir.exists():
        for entry in skills_dir.iterdir():
            if entry.is_dir():
                skill_file = entry / "SKILL.md"
                if skill_file.exists():
                    skills.append({
                        "slug": entry.name,
                        "name": entry.name.replace("-", " ").title(),
                        "path": str(skill_file),
                    })
    return {"skills": skills}


@router.get("/api/agent-arena/download/{skill_slug}")
async def download_skill(skill_slug: str):
    """Download a generated SKILL.md file."""
    skill_path = config.SKILLS_DIR / skill_slug / "SKILL.md"
    if not skill_path.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{skill_slug}' not found")
    
    content = skill_path.read_text(encoding="utf-8")
    filename = f"{skill_slug}-SKILL.md"
    
    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/markdown; charset=utf-8",
        }
    )

