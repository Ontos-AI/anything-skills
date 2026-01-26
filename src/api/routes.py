"""Skills Forge - API路由"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

from src.sources.base import SourceRegistry
from src.models.unified import UnifiedContent, SourceType


# ============= Request/Response Models =============

class ExtractRequest(BaseModel):
    """内容提取请求"""
    url: str
    options: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.bilibili.com/video/BV1xxxxx",
                "options": {
                    "transcribe": True,
                    "model_size": "base",
                    "language": "zh"
                }
            }
        }


class ExtractResponse(BaseModel):
    """内容提取响应"""
    content_id: str
    status: str
    source_type: str
    title: Optional[str] = None
    message: Optional[str] = None


class ContentResponse(BaseModel):
    """内容详情响应"""
    content_id: str
    source_type: str
    source_url: str
    title: str
    author: str
    description: str
    tags: List[str]
    full_text: str
    sections: List[Dict[str, Any]]
    raw_metadata: Dict[str, Any]


class GenerateRequest(BaseModel):
    """Skills生成请求"""
    content_ids: List[str]
    skill_name: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class GenerateResponse(BaseModel):
    """Skills生成响应"""
    skill_id: str
    status: str
    message: Optional[str] = None


class SkillResponse(BaseModel):
    """Skill详情响应"""
    skill_id: str
    name: str
    description: str
    instructions: str
    source_content_ids: List[str]
    created_at: str


# ============= 内存存储 (MVP) =============

content_store: Dict[str, UnifiedContent] = {}
skill_store: Dict[str, Dict[str, Any]] = {}


# ============= Router =============

router = APIRouter(prefix="/api/v1", tags=["Skills Forge"])


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "version": "0.1.0"}


@router.get("/sources")
async def list_sources():
    """列出支持的内容源"""
    processors = SourceRegistry.list_processors()
    return {
        "sources": [
            {
                "type": p.source_type.value,
                "name": p.__class__.__name__
            }
            for p in processors
        ]
    }


@router.post("/extract", response_model=ExtractResponse)
async def extract_content(request: ExtractRequest, background_tasks: BackgroundTasks):
    """从URL提取内容"""
    processor = SourceRegistry.get_processor(request.url)
    
    if not processor:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported URL: {request.url}"
        )
    
    options = request.options or {}
    
    try:
        # 同步执行提取 (MVP简化版)
        content = await processor.extract_content(request.url, **options)
        
        # 存储
        content_store[content.content_id] = content
        
        return ExtractResponse(
            content_id=content.content_id,
            status="completed",
            source_type=content.source_type.value,
            title=content.title,
            message="Content extracted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/{content_id}", response_model=ContentResponse)
async def get_content(content_id: str):
    """获取已提取的内容"""
    if content_id not in content_store:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content = content_store[content_id]
    
    return ContentResponse(
        content_id=content.content_id,
        source_type=content.source_type.value,
        source_url=content.source_url,
        title=content.title,
        author=content.author,
        description=content.description,
        tags=content.tags,
        full_text=content.full_text,
        sections=[
            {
                "title": s.title,
                "content": s.content,
                "start_time": s.start_time,
                "end_time": s.end_time
            }
            for s in content.sections
        ],
        raw_metadata=content.raw_metadata
    )


@router.get("/content")
async def list_contents():
    """列出所有已提取的内容"""
    return {
        "contents": [
            {
                "content_id": c.content_id,
                "source_type": c.source_type.value,
                "title": c.title,
                "author": c.author
            }
            for c in content_store.values()
        ]
    }


@router.post("/generate", response_model=GenerateResponse)
async def generate_skill(request: GenerateRequest):
    """生成Skills (预留接口)"""
    # TODO: 实现Skills生成逻辑
    skill_id = str(uuid.uuid4())
    
    return GenerateResponse(
        skill_id=skill_id,
        status="pending",
        message="Skills generation is not implemented yet"
    )


@router.get("/skills")
async def list_skills():
    """列出所有Skills (预留接口)"""
    return {
        "skills": list(skill_store.values())
    }


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str):
    """获取单个Skill (预留接口)"""
    if skill_id not in skill_store:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return skill_store[skill_id]
