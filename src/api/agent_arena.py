"""Agent Arena routes for task comparison."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from src.services.agent_middleware import apply_middlewares, BuiltinMiddleware, TerminalMiddleware
from src.services.github_search import search_github_repos
from src.services.skills_sh import search_skills_sh
from src.services.video_pipeline import extract_from_video
from src.services.llm import generate_skill_from_prompt
from src.sources.base import SourceRegistry
from src.services.langchain_adapter import run_plan_chain


router = APIRouter()


@router.get("/agent-arena", response_class=HTMLResponse)
async def agent_arena_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("agent_arena.html", {"request": request})


def _normalize_sources(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]

def _expand_queries(task: str) -> List[str]:
    queries = [task.strip()]
    lowered = task.lower()
    if any(keyword in task for keyword in ["浏览器", "自动化", "网页"]):
        queries.extend(["browser automation", "browser", "playwright automation", "web automation"])
    if any(keyword in task for keyword in ["视频", "教程"]):
        queries.append("video tutorial")
    if "github" in lowered:
        queries.append("github automation")
    # Remove duplicates while preserving order.
    seen = set()
    unique = []
    for item in queries:
        if item and item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


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
    yield await _emit("augmented", "plan", "Decompose task and fan out to multiple sources.", middlewares)
    await asyncio.sleep(0.2)

    plan_events, plan_text = await asyncio.to_thread(run_plan_chain, task)
    for event in plan_events:
        yield await _emit("augmented", event.get("stage", "thought"), event.get("message", ""), middlewares)
    yield await _emit("augmented", "thought", plan_text, middlewares)

    if "skills.sh" in sources:
        try:
            queries = _expand_queries(task)
            results = []
            for query in queries:
                batch = await search_skills_sh(query, limit=20, offset=0)
                if batch:
                    results = batch
                    break
            names = ", ".join([item.name for item in results[:5]])
            yield await _emit(
                "augmented",
                "action",
                f"skills.sh: found {len(results)} matches. Top: {names or 'none'}",
                middlewares,
            )
        except Exception as exc:
            yield await _emit("augmented", "error", f"skills.sh search failed: {exc}", middlewares)
        await asyncio.sleep(0.2)

    if "github" in sources:
        try:
            queries = _expand_queries(task)
            repos = []
            for query in queries:
                batch = await search_github_repos(query)
                if batch:
                    repos = batch
                    break
            top = ", ".join([repo.full_name for repo in repos[:5]])
            yield await _emit(
                "augmented",
                "action",
                f"GitHub: found {len(repos)} repos. Top: {top or 'none'}",
                middlewares,
            )
        except Exception as exc:
            yield await _emit("augmented", "error", f"GitHub search failed: {exc}", middlewares)
        await asyncio.sleep(0.2)

    if "youtube" in sources:
        if "youtube.com" in task or "youtu.be" in task:
            try:
                result = extract_from_video(video_url=task)
                yield await _emit("augmented", "action", f"YouTube transcript length: {len(result.transcript)}", middlewares)
            except Exception as exc:
                yield await _emit("augmented", "error", f"YouTube extract failed: {exc}", middlewares)
        else:
            yield await _emit("augmented", "action", "YouTube selected but no URL in task.", middlewares)
        await asyncio.sleep(0.2)

    if "bilibili" in sources:
        if "bilibili.com" in task:
            processor = SourceRegistry.get_processor(task)
            if processor:
                try:
                    content = await processor.extract_content(task, transcribe=True)
                    yield await _emit("augmented", "action", f"Bilibili content: {content.title}", middlewares)
                except Exception as exc:
                    yield await _emit("augmented", "error", f"Bilibili extract failed: {exc}", middlewares)
            else:
                yield await _emit("augmented", "error", "No processor for bilibili URL.", middlewares)
        else:
            yield await _emit("augmented", "action", "Bilibili selected but no URL in task.", middlewares)
        await asyncio.sleep(0.2)

    try:
        skill = generate_skill_from_prompt(task)
        snippet = (skill.get("content") or "").strip().replace("\n", " ")
        if len(snippet) > 280:
            snippet = snippet[:280] + "..."
        summary = f"{skill['name']}: {skill['description']}\n{snippet}"
        yield await _emit("augmented", "observation", summary, middlewares)
    except Exception as exc:
        yield await _emit("augmented", "error", f"LLM generation failed: {exc}", middlewares)

    yield await _emit("augmented", "done", "Completed augmented run.", middlewares)


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
