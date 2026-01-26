"""Anything2Skills API + UI routes."""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.services.skills_store import list_local_skills, save_skill, install_skill_from_content, resolve_local_path
from src.services.skills_sh import search_skills_sh, fetch_skill_content
from src.services.github_search import search_github_repos
from src.services.llm import generate_skill_from_prompt
from src.services.video_pipeline import extract_from_video
from src.core.config import config


class GenerateRequest(BaseModel):
    prompt: str


class InstallRequest(BaseModel):
    skill: Dict[str, Any]


class VideoExtractRequest(BaseModel):
    video_url: Optional[str] = None
    local_path: Optional[str] = None
    save: bool = True


router = APIRouter()


@router.get("/anything2skills", response_class=HTMLResponse)
async def anything2skills_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("anything2skills.html", {"request": request})


@router.get("/api/anything2skills/search")
async def anything2skills_search(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    local_skills = [
        {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "source": skill.source,
        }
        for skill in list_local_skills()
        if query.lower() in f"{skill.name} {skill.description}".lower()
    ]

    try:
        skills_sh = await search_skills_sh(query, limit=100, offset=0)
        skills_sh_payload = [
            {
                "id": entry.id,
                "name": entry.name,
                "description": entry.description,
                "author": entry.author,
                "stars": entry.stars,
                "github_url": entry.github_url,
                "raw_url": entry.raw_url,
            }
            for entry in skills_sh
        ]
    except Exception:
        skills_sh_payload = []

    try:
        github_repos = await search_github_repos(query)
        github_payload = [
            {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "stars": repo.stars,
                "forks": repo.forks,
                "language": repo.language,
                "url": repo.url,
            }
            for repo in github_repos
        ]
    except Exception:
        github_payload = []

    return {
        "local_skills": local_skills,
        "skills_sh": skills_sh_payload,
        "github_repos": github_payload,
    }


@router.post("/api/anything2skills/generate")
async def anything2skills_generate(payload: GenerateRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")

    try:
        spec = generate_skill_from_prompt(payload.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    saved = save_skill(spec["name"], spec["description"], spec["content"], source="generated")
    return {"id": saved.id, "name": saved.name, "message": f"Generated skill: {saved.name}"}


@router.post("/api/anything2skills/install")
async def anything2skills_install(payload: InstallRequest):
    skill = payload.skill or {}
    raw_url = skill.get("raw_url")
    name = skill.get("name") or skill.get("id") or "installed-skill"
    if not raw_url:
        raise HTTPException(status_code=400, detail="raw_url is required")
    try:
        content = await fetch_skill_content(raw_url)
        installed = install_skill_from_content(name, content)
        return {"success": True, "message": f"Installed {installed.name} to {config.SKILLS_DIR}"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/videos/extract")
async def videos_extract(payload: VideoExtractRequest):
    if not payload.video_url and not payload.local_path:
        raise HTTPException(status_code=400, detail="video_url or local_path is required")

    local_path = None
    if payload.local_path:
        local_path = resolve_local_path(payload.local_path)
        if not local_path:
            raise HTTPException(status_code=400, detail="local_path must be inside downloads/")

    try:
        result = extract_from_video(video_url=payload.video_url, local_path=local_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    extracted = result.extracted_skills
    if payload.save:
        for skill in extracted:
            save_skill(skill.get("name", "Video Skill"), skill.get("description", "Video skill"), skill.get("content", ""), source="video")

    return {
        "video": {"title": result.title, "transcript": result.transcript},
        "extracted_skills": extracted,
    }
