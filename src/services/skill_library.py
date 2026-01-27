"""Helpers for reading local skills and building prompt context."""
from __future__ import annotations

from typing import List, Dict, Any

from src.services.skills_store import list_local_skills


def build_skill_context(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    skills = list_local_skills()
    query_lower = query.lower()
    matches = []
    for skill in skills:
        haystack = f"{skill.name} {skill.description}".lower()
        if query_lower in haystack:
            matches.append(skill)
    # Fallback: if no match, return most recent few (by filesystem order)
    if not matches:
        matches = skills[:limit]
    context = []
    for skill in matches[:limit]:
        content = skill.path.read_text(encoding="utf-8", errors="ignore")
        context.append(
            {
                "name": skill.name,
                "description": skill.description,
                "path": str(skill.path),
                "content": content[:2000],
            }
        )
    return context
