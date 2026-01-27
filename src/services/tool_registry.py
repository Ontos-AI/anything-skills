"""Unified tool registry for agent orchestration."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import asyncio

from src.services.skills_sh import search_skills_sh
from src.services.github_search import search_github_repos
from src.services.video_pipeline import extract_from_video
from src.services.llm import generate_skill_from_prompt, generate_test_cases
from src.services.bocha_search import bocha_search


class ToolRegistry:
    """Thin wrappers over existing services to standardize calls."""

    async def skills_sh_search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        results = await search_skills_sh(query, limit=limit, offset=0)
        return [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "author": item.author,
                "stars": item.stars,
                "github_url": item.github_url,
                "raw_url": item.raw_url,
            }
            for item in results
        ]

    async def github_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        repos = await search_github_repos(query)
        payload = []
        for repo in repos[:limit]:
            payload.append(
                {
                    "id": repo.id,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "stars": repo.stars,
                    "forks": repo.forks,
                    "language": repo.language,
                    "url": repo.url,
                }
            )
        return payload

    async def video_extract(self, video_url: Optional[str] = None, local_path: Optional[str] = None) -> Dict[str, Any]:
        result = await asyncio.to_thread(extract_from_video, video_url=video_url, local_path=local_path)
        return {
            "title": result.title,
            "transcript": result.transcript,
            "extracted_skills": result.extracted_skills,
        }

    async def generate_skill(self, prompt: str) -> Dict[str, Any]:
        return await asyncio.to_thread(generate_skill_from_prompt, prompt)

    async def generate_test_cases(self, task: str, skill: Dict[str, Any]) -> List[Dict[str, Any]]:
        tests = await asyncio.to_thread(generate_test_cases, task, skill)
        if tests:
            return tests
        return [
            {
                "name": "Basic happy path",
                "input": task,
                "expected": "Skill produces the desired outcome.",
                "environment": "local",
                "edge_cases": ["missing dependency", "invalid input"],
            }
        ]

    async def web_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(bocha_search, query, top_k)
