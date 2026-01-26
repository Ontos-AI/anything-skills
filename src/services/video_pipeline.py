"""Video extraction pipeline using yt-dlp + Whisper."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import subprocess
import uuid

import whisper

from src.core.config import config
from src.services.llm import extract_skills_from_transcript


@dataclass
class VideoResult:
    title: str
    transcript: str
    extracted_skills: List[Dict[str, Any]]


def _run_command(args: List[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Command failed")


def _download_audio(video_url: str) -> Path:
    config.ensure_dirs()
    base_name = f"yt-{uuid.uuid4().hex}"
    output_template = str(config.DOWNLOADS_DIR / f"{base_name}.%(ext)s")

    args = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", output_template, video_url]
    cookies_path = os.getenv("YTDLP_COOKIES_PATH") or str(config.BASE_DIR / "cookies" / "cookies.txt")
    if Path(cookies_path).exists():
        args.extend(["--cookies", cookies_path])

    _run_command(args)

    for candidate in config.DOWNLOADS_DIR.iterdir():
        if candidate.name.startswith(base_name) and candidate.suffix == ".mp3":
            return candidate
    raise RuntimeError("yt-dlp did not produce mp3 output")


def _transcribe_audio(audio_path: Path) -> str:
    model_name = os.getenv("WHISPER_MODEL") or "base"
    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio_path))
    return (result.get("text") or "").strip() or "Transcript not available"


def _fallback_skills(transcript: str) -> List[Dict[str, Any]]:
    keywords = []
    for word in transcript.lower().split():
        word = word.strip(".,:;!?")
        if len(word) >= 5 and word not in keywords:
            keywords.append(word)
        if len(keywords) >= 8:
            break
    return [
        {
            "name": "General Knowledge Skill",
            "description": "Auto-generated from transcript.",
            "tags": keywords,
            "content": "Review the transcript and refine the steps into a concrete skill.",
        }
    ]


def extract_from_video(
    *,
    video_url: Optional[str] = None,
    local_path: Optional[Path] = None,
    title: Optional[str] = None,
) -> VideoResult:
    if not video_url and not local_path:
        raise ValueError("video_url or local_path is required")

    if video_url:
        audio_path = _download_audio(video_url)
        title = title or video_url
    else:
        audio_path = local_path
        title = title or audio_path.name

    transcript = _transcribe_audio(audio_path)

    extracted_skills: List[Dict[str, Any]] = []
    try:
        extracted_skills = extract_skills_from_transcript(
            {
                "title": title,
                "description": "",
                "transcript": transcript,
            }
        )
    except Exception:
        extracted_skills = _fallback_skills(transcript)

    return VideoResult(title=title, transcript=transcript, extracted_skills=extracted_skills)
