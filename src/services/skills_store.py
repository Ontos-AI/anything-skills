"""Filesystem-backed skill storage."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import re
import sys

from src.core.config import config


@dataclass
class LocalSkill:
    id: str
    name: str
    description: str
    source: str
    path: Path
    # Evaluation fields (added for Phase 2)
    eval_score: Optional[float] = None
    eval_badge: Optional[str] = None
    eval_report_path: Optional[Path] = None
    eval_scores: Optional[Dict[str, float]] = None  # Detailed dimension scores


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


def _evaluate_skill(skill_path: Path) -> tuple[Optional[float], Optional[str], Optional[Path], Optional[Dict[str, float]]]:
    """
    Evaluate a skill using the skill-evaluator.
    Returns (score, badge, report_path, scores_dict) or (None, None, None, None) if evaluation fails.
    """
    try:
        # Import the evaluator - handle both installed and development paths
        evaluator_path = Path(__file__).parent.parent.parent / "skills" / "skill-evaluator" / "scripts"
        if evaluator_path.exists():
            sys.path.insert(0, str(evaluator_path))
        
        from quick_eval import evaluate_skill
        from visualize import generate_html_report
        
        # Run evaluation
        report = evaluate_skill(skill_path.parent)  # skill_path is SKILL.md, we need parent dir
        
        # Generate HTML report
        html_content = generate_html_report(report.to_dict())
        report_path = skill_path.parent / "EVALUATION.html"
        report_path.write_text(html_content, encoding="utf-8")
        
        # Return detailed scores
        scores_dict = {
            "structure": round(report.scores.structure, 2),
            "triggers": round(report.scores.triggers, 2),
            "actionability": round(report.scores.actionability, 2),
            "tool_refs": round(report.scores.tool_refs, 2),
            "examples": round(report.scores.examples, 2),
        }
        
        return report.scores.overall, report.badge, report_path, scores_dict
        
    except ImportError as e:
        # Skill evaluator not available - skip silently
        print(f"[skill-store] Evaluation skipped (evaluator not available): {e}")
        return None, None, None, None
    except Exception as e:
        print(f"[skill-store] Evaluation failed: {e}")
        return None, None, None, None


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
        
        # Check for existing evaluation
        eval_report = entry / "EVALUATION.html"
        
        skills.append(
            LocalSkill(
                id=f"local-{entry.name}",
                name=name,
                description=description,
                source="local",
                path=skill_file,
                eval_report_path=eval_report if eval_report.exists() else None,
            )
        )
    return skills


def save_skill(name: str, description: str, content: str, source: str = "generated", auto_evaluate: bool = True) -> LocalSkill:
    """
    Save a skill to the filesystem.
    
    Args:
        name: Skill name
        description: Skill description  
        content: SKILL.md body content
        source: Source of the skill (generated, video, skills.sh, etc.)
        auto_evaluate: Whether to run skill-evaluator after saving (default: True)
    """
    slug = _slugify(name)
    target_dir = config.SKILLS_DIR / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    skill_file = target_dir / "SKILL.md"

    # skill-creator规范：frontmatter只包含 name 和 description
    frontmatter = "\n".join(
        [
            "---",
            f"name: {name}",
            f"description: {description}",
            "---",
            "",
        ]
    )
    skill_file.write_text(frontmatter + content.strip() + "\n", encoding="utf-8")
    
    # Run evaluation if requested
    eval_score, eval_badge, eval_report_path, eval_scores = None, None, None, None
    if auto_evaluate:
        eval_score, eval_badge, eval_report_path, eval_scores = _evaluate_skill(skill_file)
        if eval_score is not None:
            badge_emoji = {"gold": "🥇", "silver": "🥈", "bronze": "🥉", "fail": "❌"}.get(eval_badge, "")
            print(f"[skill-store] Evaluated '{name}': {badge_emoji} {eval_badge.upper()} (score: {eval_score:.2f})")
    
    return LocalSkill(
        id=f"local-{slug}", 
        name=name, 
        description=description, 
        source=source, 
        path=skill_file,
        eval_score=eval_score,
        eval_badge=eval_badge,
        eval_report_path=eval_report_path,
        eval_scores=eval_scores,
    )


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

