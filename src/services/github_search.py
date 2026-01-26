"""GitHub search helper."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import os
import httpx


@dataclass
class GitHubRepo:
    id: int
    name: str
    full_name: str
    description: str
    stars: int
    forks: int
    language: str
    url: str
    topics: List[str]


async def search_github_repos(query: str, language: Optional[str] = None) -> List[GitHubRepo]:
    params = {
        "q": query + (f"+language:{language}" if language else ""),
        "sort": "stars",
        "order": "desc",
        "per_page": "20",
    }
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Anything-Skills",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get("https://api.github.com/search/repositories", params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    repos: List[GitHubRepo] = []
    for repo in data.get("items", []) or []:
        repos.append(
            GitHubRepo(
                id=int(repo.get("id")),
                name=str(repo.get("name")),
                full_name=str(repo.get("full_name")),
                description=repo.get("description") or "",
                stars=int(repo.get("stargazers_count") or 0),
                forks=int(repo.get("forks_count") or 0),
                language=repo.get("language") or "Unknown",
                url=str(repo.get("html_url")),
                topics=repo.get("topics") or [],
            )
        )
    return repos
