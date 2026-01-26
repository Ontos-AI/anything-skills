"""Skills Forge - 数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class SourceType(str, Enum):
    """内容源类型"""
    BILIBILI = "bilibili"
    ARXIV = "arxiv"
    GITHUB = "github"
    WEB = "web"


@dataclass
class Section:
    """内容章节"""
    title: str
    content: str
    start_time: Optional[float] = None  # 视频时间戳
    end_time: Optional[float] = None


@dataclass
class UnifiedContent:
    """统一的内容表示"""
    # 标识
    content_id: str
    source_type: SourceType
    source_url: str
    source_id: str
    
    # 元数据
    title: str
    author: str
    created_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    description: str = ""
    
    # 内容 (文本化后)
    full_text: str = ""
    sections: List[Section] = field(default_factory=list)
    
    # 原始数据
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 处理状态
    extracted_at: datetime = field(default_factory=datetime.now)
    transcription_model: Optional[str] = None


@dataclass
class Experience:
    """提取的经验知识"""
    title: str
    category: str  # "technique", "best_practice", "troubleshooting", etc.
    content: str
    examples: List[str] = field(default_factory=list)
    source_content_id: str = ""


@dataclass
class Skill:
    """Claude Skill 表示"""
    skill_id: str
    name: str
    description: str
    
    # SKILL.md 内容
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    instructions: str = ""
    
    # 关联
    source_content_ids: List[str] = field(default_factory=list)
    experiences: List[Experience] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
