"""LLM helpers for skill generation."""
from __future__ import annotations

import json
import os
from typing import List, Dict, Any

from openai import OpenAI


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM generation")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    return OpenAI(api_key=api_key, base_url=base_url)


def generate_skill_from_prompt(prompt: str) -> Dict[str, Any]:
    client = _client()
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "Generate a concise skill spec. Return JSON with name, description, tags (array), content (SKILL.md body, no frontmatter).",
            },
            {"role": "user", "content": prompt},
        ],
    )
    message = response.choices[0].message.content or "{}"
    parsed = json.loads(message)
    return {
        "name": str(parsed.get("name") or "Untitled Skill"),
        "description": str(parsed.get("description") or "Generated skill"),
        "tags": [str(tag) for tag in parsed.get("tags", []) if tag],
        "content": str(parsed.get("content") or ""),
    }


def extract_skills_from_transcript(payload: Dict[str, str]) -> List[Dict[str, Any]]:
    client = _client()
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "Extract 1-3 skills from the transcript. Return JSON { skills: [{ name, description, tags, content }] }. content is SKILL.md body only.",
            },
            {"role": "user", "content": json.dumps(payload)},
        ],
    )
    message = response.choices[0].message.content or "{}"
    parsed = json.loads(message)
    skills = parsed.get("skills") or []
    results: List[Dict[str, Any]] = []
    for skill in skills:
        results.append(
            {
                "name": str(skill.get("name") or "Untitled Skill"),
                "description": str(skill.get("description") or "Generated skill"),
                "tags": [str(tag) for tag in skill.get("tags", []) if tag],
                "content": str(skill.get("content") or ""),
            }
        )
    return results
