"""skills.sh search and install helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
import httpx


SKILLS_SH_API = "https://skills.sh/api/search"


@dataclass
class SkillsShEntry:
    id: str
    name: str
    description: str
    author: str
    stars: int
    github_url: str
    raw_url: str


def _build_github_url(source: str, skill_name: str) -> str:
    return f"https://github.com/{source}/tree/main/skills/{skill_name}"


def _build_raw_url(source: str, skill_name: str) -> str:
    return f"https://raw.githubusercontent.com/{source}/main/skills/{skill_name}/SKILL.md"


async def search_skills_sh(query: str, limit: int = 100, offset: int = 0) -> List[SkillsShEntry]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            SKILLS_SH_API,
            params={"q": query, "limit": limit, "offset": offset},
        )
        response.raise_for_status()
        data = response.json()

    entries: List[SkillsShEntry] = []
    for skill in data.get("skills", []) or []:
        source = str(skill.get("topSource") or "")
        name = str(skill.get("name") or skill.get("id") or "")
        entries.append(
            SkillsShEntry(
                id=str(skill.get("id") or name),
                name=name,
                description=f"Top source: {source}",
                author=source.split("/")[0] if source else "unknown",
                stars=int(skill.get("installs") or 0),
                github_url=_build_github_url(source, name),
                raw_url=_build_raw_url(source, name),
            )
        )
    return entries


async def fetch_skill_content(raw_url: str) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(raw_url)
        response.raise_for_status()
        return response.text
