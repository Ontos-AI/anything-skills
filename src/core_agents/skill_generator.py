"""Skill generation agent."""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from src.application.types import SkillSpec
from src.services.skill_library import build_skill_context


def _expand_queries(task: str) -> List[str]:
    queries = [task.strip()]
    lowered = task.lower()
    if any(keyword in task for keyword in ["浏览器", "自动化", "网页"]):
        queries.extend(["browser automation", "playwright automation", "web automation"])
    if any(keyword in task for keyword in ["视频", "教程"]):
        queries.append("video tutorial")
    if "github" in lowered:
        queries.append("github automation")
    seen = set()
    unique = []
    for item in queries:
        if item and item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


class SkillGeneratorAgent:
    name = "skill_generator"

    async def run(
        self,
        task: str,
        sources: List[str],
        tools,
        emit,
        feedback: Optional[str] = None,
        execution_summary: Optional[Dict[str, Any]] = None,
    ) -> SkillSpec:
        await emit(self.name, "plan", "Generate a draft skill spec from available sources.", {})

        context: Dict[str, Any] = {"sources": sources, "notes": []}
        local_skills = build_skill_context(task)
        if local_skills:
            context["local_skills"] = [
                {"name": item["name"], "description": item["description"], "content": item["content"]}
                for item in local_skills
            ]

        if "skills.sh" in sources:
            await emit(self.name, "action", "Searching skills.sh...", {})
            queries = _expand_queries(task)
            matches = []
            for query in queries:
                batch = await tools.skills_sh_search(query)
                if batch:
                    matches = batch
                    break
            context["skills_sh"] = matches[:5]
            await emit(self.name, "observation", f"skills.sh matches: {len(matches)}", {})

        if "github" in sources:
            await emit(self.name, "action", "Searching GitHub...", {})
            queries = _expand_queries(task)
            repos = []
            for query in queries:
                batch = await tools.github_search(query)
                if batch:
                    repos = batch
                    break
            context["github"] = repos[:5]
            await emit(self.name, "observation", f"GitHub repos: {len(repos)}", {})

        if "youtube" in sources and ("youtube.com" in task or "youtu.be" in task):
            await emit(self.name, "action", "Extracting YouTube transcript...", {})
            try:
                video = await tools.video_extract(video_url=task)
                context["video"] = {"title": video.get("title"), "transcript": video.get("transcript", "")[:2000]}
                await emit(self.name, "observation", "YouTube transcript captured.", {})
            except Exception as exc:
                await emit(self.name, "error", f"YouTube extract failed: {exc}", {})

        if "bilibili" in sources and "bilibili.com" in task:
            await emit(self.name, "action", "Bilibili URL detected (handled in sources).", {})

        if "web" in sources or "search" in sources:
            await emit(self.name, "action", "Running online search via MCP...", {})
            try:
                results = await tools.web_search(task, top_k=5)
                context["web_search"] = results
                await emit(self.name, "observation", f"Web search results: {len(results)}", {})
            except Exception as exc:
                await emit(self.name, "error", f"Web search failed: {exc}", {})

        if feedback:
            context["feedback"] = feedback
        if execution_summary:
            context["execution_summary"] = execution_summary

        prompt = (
            "Task: " + task + "\n" +
            "Context: " + str(context)
        )
        await emit(self.name, "action", "Generating skill with LLM...", {})
        skill_data = await tools.generate_skill(prompt)
        skill = SkillSpec(**skill_data)
        await emit(self.name, "observation", f"Skill drafted: {skill.name}", {})
        return skill
