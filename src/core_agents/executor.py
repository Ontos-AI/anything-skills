"""Skill execution agent."""
from __future__ import annotations

import csv
import importlib.util
import re
from datetime import date, timedelta
from typing import List, Dict, Any

from src.core.config import config
from src.application.types import ExecutionReport


class ExecutorAgent:
    name = "executor"

    def _pick_first_url(self, results: List[Dict[str, Any]], patterns: List[str]) -> str | None:
        for item in results:
            for key in ("url", "content", "title"):
                value = item.get(key, "") or ""
                for pattern in patterns:
                    match = re.search(pattern, value)
                    if match:
                        return match.group(0)
        return None

    async def run(self, task: str, sources: List[str], tools, emit) -> ExecutionReport:
        await emit(self.name, "plan", "Execute task using available tools.", {})
        issues: List[str] = []
        outputs: Dict[str, Any] = {}
        urls = re.findall(r"https?://\S+", task)
        bilibili_url = next((u for u in urls if "bilibili.com" in u or "b23.tv" in u), None)
        youtube_url = next((u for u in urls if "youtube.com" in u or "youtu.be" in u), None)

        if "bilibili" in sources and not bilibili_url:
            try:
                await emit(self.name, "action", "Searching Bilibili via web search...", {})
                results = await tools.web_search(f"{task} site:bilibili.com/video", top_k=5)
                bilibili_url = self._pick_first_url(results, [r"https?://\\S*bilibili\\.com/\\S+", r"https?://b23\\.tv/\\S+"])
                if bilibili_url:
                    await emit(self.name, "observation", f"Selected Bilibili URL: {bilibili_url}", {})
            except Exception as exc:
                issues.append(f"Bilibili search failed: {exc}")

        if "youtube" in sources and not youtube_url:
            try:
                await emit(self.name, "action", "Searching YouTube via web search...", {})
                results = await tools.web_search(f"{task} site:youtube.com/watch OR youtu.be", top_k=5)
                youtube_url = self._pick_first_url(
                    results,
                    [r"https?://\\S*youtube\\.com/\\S+", r"https?://youtu\\.be/\\S+"],
                )
                if youtube_url:
                    await emit(self.name, "observation", f"Selected YouTube URL: {youtube_url}", {})
            except Exception as exc:
                issues.append(f"YouTube search failed: {exc}")

        if "github" in sources or "github" in task.lower():
            try:
                await emit(self.name, "action", "Fetching GitHub trending repositories (last 30 days)...", {})
                today = date.today()
                start_date = (today - timedelta(days=30)).isoformat()
                query = f"created:>={start_date} stars:>100"
                repos = await tools.github_search(query, limit=20)
                if not repos:
                    issues.append("No GitHub repositories returned.")
                else:
                    config.ensure_dirs()
                    output_dir = config.OUTPUT_DIR / "runs"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    csv_path = output_dir / f"github_trending_{start_date.replace('-', '')}_to_{today.isoformat().replace('-', '')}.csv"
                    with csv_path.open("w", encoding="utf-8", newline="") as f:
                        writer = csv.DictWriter(
                            f,
                            fieldnames=[
                                "full_name",
                                "description",
                                "stars",
                                "forks",
                                "language",
                                "url",
                            ],
                        )
                        writer.writeheader()
                        for repo in repos:
                            writer.writerow(
                                {
                                    "full_name": repo.get("full_name"),
                                    "description": repo.get("description"),
                                    "stars": repo.get("stars"),
                                    "forks": repo.get("forks"),
                                    "language": repo.get("language"),
                                    "url": repo.get("url"),
                                }
                            )

                    outputs["csv"] = str(csv_path)
                    outputs["sample"] = repos[:5]

                    # Optional XLSX if pandas is available.
                    if importlib.util.find_spec("pandas") is not None:
                        import pandas as pd

                        xlsx_path = output_dir / f"github_trending_{start_date.replace('-', '')}_to_{today.isoformat().replace('-', '')}.xlsx"
                        pd.DataFrame(repos).to_excel(xlsx_path, index=False)
                        outputs["xlsx"] = str(xlsx_path)

                    await emit(self.name, "observation", f"Saved CSV: {csv_path.name}", {})
            except Exception as exc:
                issues.append(f"GitHub execution failed: {exc}")

        if "bilibili" in sources and (bilibili_url or "bilibili.com" in task):
            try:
                await emit(self.name, "action", "Extracting Bilibili transcript...", {})
                result = await tools.video_extract(video_url=bilibili_url or task)
                outputs["video"] = {
                    "title": result.get("title"),
                    "transcript": result.get("transcript", "")[:4000],
                    "extracted_skills": result.get("extracted_skills", []),
                }
                await emit(self.name, "observation", "Bilibili transcript captured.", {})
            except Exception as exc:
                issues.append(f"Bilibili execution failed: {exc}")

        if "youtube" in sources and (youtube_url or "youtube.com" in task or "youtu.be" in task):
            try:
                await emit(self.name, "action", "Extracting YouTube transcript...", {})
                result = await tools.video_extract(video_url=youtube_url or task)
                outputs["video"] = {
                    "title": result.get("title"),
                    "transcript": result.get("transcript", "")[:4000],
                    "extracted_skills": result.get("extracted_skills", []),
                }
                await emit(self.name, "observation", "YouTube transcript captured.", {})
            except Exception as exc:
                issues.append(f"YouTube execution failed: {exc}")

        if ("web" in sources or "search" in sources) and not outputs:
            try:
                await emit(self.name, "action", "Running online search via MCP...", {})
                results = await tools.web_search(task, top_k=5)
                outputs["web_search"] = results
                await emit(self.name, "observation", f"Web search results: {len(results)}", {})
            except Exception as exc:
                issues.append(f"Web search failed: {exc}")

        if not outputs and not issues:
            issues.append("No executable path matched this task.")

        passed = not issues
        notes = "Execution succeeded." if passed else "Execution failed."
        await emit(self.name, "observation", notes, {"issues": issues, "outputs": outputs})
        return ExecutionReport(passed=passed, issues=issues, notes=notes, outputs=outputs)
