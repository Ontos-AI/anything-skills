<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.104+-00897B?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Whisper-OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" alt="Whisper"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/>
</p>

<h1 align="center">⚡ Anything Skills</h1>

<p align="center">
  <strong>从任意内容源提取知识，自动生成 Claude Skills</strong>
</p>

<p align="center">
  <em>Transform any content into structured Claude Skills with AI-powered extraction</em>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎬 **Multi-Source Extraction** | Bilibili videos, ArXiv papers, GitHub repos, and more |
| 🔄 **Unified Format** | Convert any content to structured `UnifiedContent` |
| 🎙️ **AI Transcription** | OpenAI Whisper for video/audio transcription |
| 🧠 **Experience Mining** | LLM-powered knowledge extraction |
| 📝 **Skills Generation** | Auto-generate Claude `SKILL.md` files |
| 🚀 **RESTful API** | FastAPI backend with OpenAPI docs |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Content Sources                        │
├───────────┬───────────┬───────────┬───────────┬─────────────┤
│  Bilibili │   ArXiv   │  GitHub   │    Web    │    ...      │
└─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴──────┬──────┘
      │           │           │           │            │
      ▼           ▼           ▼           ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Source Processors                         │
│  • Metadata Extraction  • Content Download  • Transcription  │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     UnifiedContent                           │
│  { title, author, full_text, sections[], metadata }          │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Experience Extractor (LLM)                  │
│  • Knowledge Points  • Best Practices  • Troubleshooting     │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Skills Generator                          │
│  Output: SKILL.md files for Claude                           │
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
```

### Usage

#### CLI Mode

```bash
# Extract metadata only
python test_bilibili.py "https://www.bilibili.com/video/BV1xxxxx"

# Full extraction with transcription
python test_bilibili.py "https://www.bilibili.com/video/BV1xxxxx" --full

# Specify Whisper model
python test_bilibili.py "https://www.bilibili.com/video/BV1xxxxx" --full --model=small
```

#### API Mode

```bash
# Start server
uvicorn src.api.main:app --reload

# Open API docs
open http://localhost:8000/docs
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sources` | List supported sources |
| `POST` | `/api/v1/extract` | Extract content from URL |
| `GET` | `/api/v1/content/{id}` | Get extracted content |
| `GET` | `/api/v1/content` | List all contents |
| `POST` | `/api/v1/generate` | Generate skills |
| `GET` | `/api/v1/skills` | List generated skills |

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.bilibili.com/video/BV1GJ411x7h7",
    "options": {
      "transcribe": true,
      "model_size": "base"
    }
  }'
```

---

## 📁 Project Structure

```
anything-skills/
├── src/
│   ├── sources/           # Content source processors
│   │   ├── base.py        # SourceProcessor abstract base
│   │   └── bilibili.py    # Bilibili video processor
│   ├── models/
│   │   └── unified.py     # UnifiedContent data model
│   ├── generators/        # Skills generation (TODO)
│   ├── core/
│   │   └── config.py      # Configuration
│   └── api/
│       ├── main.py        # FastAPI app
│       └── routes.py      # API routes
├── output/
│   ├── content/           # Extracted content (JSON, SRT)
│   └── skills/            # Generated skills
├── test_bilibili.py       # CLI test script
└── requirements.txt
```

---

## 🎯 Roadmap

- [x] **Phase 1**: Bilibili video extraction & transcription
- [ ] **Phase 2**: Experience extraction with LLM
- [ ] **Phase 3**: Skills generation
- [ ] **Phase 4**: ArXiv paper support
- [ ] **Phase 5**: GitHub repository analysis
- [ ] **Phase 6**: Web content crawler

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, Pydantic
- **Video Processing**: yt-dlp, FFmpeg
- **Transcription**: OpenAI Whisper
- **LLM**: Anthropic Claude / OpenAI GPT
- **Database**: SQLite (MVP) → PostgreSQL

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/Ontos-AI">Ontos AI</a></sub>
</p>
