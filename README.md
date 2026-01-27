<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.104+-00897B?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Whisper-OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" alt="Whisper"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/>
</p>

<h1 align="center">⚡ Anything Skills</h1>

<p align="center">
  <strong>从视频内容提取知识，自动生成 Claude Skills</strong>
</p>

<p align="center">
  <em>Transform video content into structured Claude Skills with AI-powered extraction</em>
</p>

---

## ✨ Features

| Feature | Status | Description |
|---------|--------|-------------|
| 🎬 **Video Extraction** | ✅ Ready | Bilibili & YouTube video processing via yt-dlp |
| 🎙️ **AI Transcription** | ✅ Ready | OpenAI Whisper for video/audio transcription |
| 🧠 **Skills Generation** | ✅ Ready | LLM-powered knowledge extraction to SKILL.md |
| 🔍 **Skills Marketplace** | ✅ Ready | Search & install from skills.sh |
| 📦 **GitHub Search** | 🟡 Partial | Repository search only (no content extraction) |
| 📄 **ArXiv Papers** | 🔴 Planned | Paper parsing (coming soon) |
| 🌐 **Web Crawler** | 🔴 Planned | General web content (coming soon) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Content Sources                          │
├──────────────────┬──────────────────┬───────────────────────┤
│  Bilibili ✅     │   YouTube ✅     │   GitHub/ArXiv 🔴     │
└────────┬─────────┴────────┬─────────┴───────────────────────┘
         │                  │
         ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Video Pipeline (yt-dlp + Whisper)               │
│  • Download Video  • Extract Audio  • Transcribe to Text    │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   UnifiedContent Model                       │
│  { title, author, full_text, sections[], metadata }          │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  LLM Experience Extractor                    │
│  • Knowledge Points  • Best Practices  • Troubleshooting     │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Skills Generator                          │
│  Output: SKILL.md files → output/skills/<name>/              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# macOS
brew install ffmpeg

# Python 3.11+
pip install -r requirements.txt
```

### Installation

```bash
git clone git@github.com:Ontos-AI/anything-skills.git
cd anything-skills
pip install -r requirements.txt
cp .env.example .env  # Fill in your API keys
```

### Usage

#### 1. Start API Server

```bash
uvicorn src.api.main:app --reload
```

#### 2. Open Web UI

| UI | URL | Description |
|----|-----|-------------|
| API Docs | http://localhost:8000/docs | OpenAPI documentation |
| Anything2Skills | http://localhost:8000/anything2skills | Main web interface |
| Agent Arena | http://localhost:8000/agent-arena | Agent comparison tool |

#### 3. CLI Mode (Bilibili)

```bash
# Metadata only
python test_bilibili.py "https://www.bilibili.com/video/BV1xxxxx"

# Full extraction with transcription
python test_bilibili.py "https://www.bilibili.com/video/BV1xxxxx" --full

# Specify Whisper model (tiny/base/small/medium/large)
python test_bilibili.py "https://www.bilibili.com/video/BV1xxxxx" --full --model=small
```

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/videos/extract` | Extract skills from video URL |
| `POST` | `/api/anything2skills/generate` | Generate skill from prompt |
| `POST` | `/api/anything2skills/install` | Install skill from skills.sh |
| `GET` | `/api/anything2skills/search` | Search local/marketplace/GitHub |

### Legacy Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sources` | List supported sources |
| `POST` | `/api/v1/extract` | Extract content (Bilibili only) |
| `GET` | `/api/v1/content` | List extracted contents |

### Example: Extract from Video

```bash
curl -X POST http://localhost:8000/api/videos/extract \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=xxxxx",
    "save": true
  }'
```

---

## 📁 Project Structure

```
anything-skills/
├── src/
│   ├── sources/              # Content source processors
│   │   ├── base.py           # SourceProcessor base class
│   │   └── bilibili.py       # Bilibili processor
│   ├── services/
│   │   ├── video_pipeline.py # yt-dlp + Whisper pipeline
│   │   ├── llm.py            # LLM skill generation
│   │   ├── skills_store.py   # Local SKILL.md storage
│   │   ├── skills_sh.py      # skills.sh marketplace
│   │   └── github_search.py  # GitHub repo search
│   ├── models/
│   │   └── unified.py        # Data models
│   ├── api/
│   │   ├── main.py           # FastAPI app
│   │   ├── routes.py         # Core API routes
│   │   └── anything2skills.py # Web UI routes
│   └── templates/            # Jinja2 templates
├── output/
│   ├── content/              # Extracted content
│   └── skills/               # Generated SKILL.md files
└── requirements.txt
```

---

## 🎯 Roadmap

- [x] **Phase 1**: Video extraction (Bilibili & YouTube)
- [x] **Phase 2**: Whisper transcription
- [x] **Phase 3**: LLM-based skill generation
- [x] **Phase 4**: skills.sh marketplace integration
- [ ] **Phase 5**: GitHub repository analysis
- [ ] **Phase 6**: ArXiv paper parsing
- [ ] **Phase 7**: General web crawler

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, Pydantic |
| Video | yt-dlp, FFmpeg |
| Transcription | OpenAI Whisper |
| LLM | OpenAI API (GPT-4o-mini) |
| Templates | Jinja2 |
| HTTP Client | httpx |

---

## ⚙️ Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-xxx        # For LLM generation
OPENAI_BASE_URL=             # Optional: custom API endpoint
OPENAI_MODEL=gpt-4o-mini     # Model to use

# Optional
GITHUB_TOKEN=                # For GitHub search (higher rate limit)
WHISPER_MODEL=base           # Whisper model size
YTDLP_COOKIES_PATH=          # Path to cookies.txt for yt-dlp
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/Ontos-AI">Ontos AI</a></sub>
</p>
