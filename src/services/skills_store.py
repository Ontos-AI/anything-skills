"""Filesystem-backed skill storage."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import re

from src.core.config import config


@dataclass
class LocalSkill:
    id: str
    name: str
    description: str
    source: str
    path: Path


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "skill"


def _parse_frontmatter(content: str) -> dict:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def list_local_skills() -> List[LocalSkill]:
    skills_dir = config.SKILLS_DIR
    skills: List[LocalSkill] = []
    if not skills_dir.exists():
        return skills

    for entry in skills_dir.iterdir():
        if not entry.is_dir():
            continue
        skill_file = entry / "SKILL.md"
        if not skill_file.exists():
            continue
        content = skill_file.read_text(encoding="utf-8", errors="ignore")
        frontmatter = _parse_frontmatter(content)
        name = frontmatter.get("name") or entry.name
        description = frontmatter.get("description") or "Local skill"
        skills.append(
            LocalSkill(
                id=f"local-{entry.name}",
                name=name,
                description=description,
                source="local",
                path=skill_file,
            )
        )
    return skills


def save_skill(name: str, description: str, content: str, source: str = "generated") -> LocalSkill:
    slug = _slugify(name)
    target_dir = config.SKILLS_DIR / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    skill_file = target_dir / "SKILL.md"

    frontmatter = "\n".join(
        [
            "---",
            f"name: {name}",
            f"description: {description}",
            f"source: {source}",
            "version: 1.0.0",
            "---",
            "",
        ]
    )
    skill_file.write_text(frontmatter + content.strip() + "\n", encoding="utf-8")
    return LocalSkill(id=f"local-{slug}", name=name, description=description, source=source, path=skill_file)


def install_skill_from_content(name: str, content: str) -> LocalSkill:
    frontmatter = _parse_frontmatter(content)
    description = frontmatter.get("description") or "Installed skill"
    return save_skill(name=name or frontmatter.get("name", "Installed Skill"), description=description, content=content, source="skills.sh")


def resolve_local_path(path: str) -> Optional[Path]:
    candidate = Path(path).expanduser().resolve()
    try:
        downloads_dir = config.DOWNLOADS_DIR.resolve()
    except Exception:
        downloads_dir = None

    if downloads_dir and downloads_dir in candidate.parents:
        return candidate
    return None
