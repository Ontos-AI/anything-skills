"""Skills Forge - 内容源处理器基类"""
from abc import ABC, abstractmethod
from typing import Optional
import re

from src.models.unified import UnifiedContent, SourceType


class SourceProcessor(ABC):
    """内容源处理器抽象基类"""
    
    source_type: SourceType
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """判断是否能处理该URL"""
        pass
    
    @abstractmethod
    async def extract_metadata(self, url: str) -> dict:
        """提取元数据"""
        pass
    
    @abstractmethod
    async def extract_content(self, url: str, **options) -> UnifiedContent:
        """提取并返回统一格式内容"""
        pass
    
    def get_source_id(self, url: str) -> Optional[str]:
        """从URL提取源ID"""
        return None


class SourceRegistry:
    """内容源处理器注册表"""
    
    _processors: list[SourceProcessor] = []
    
    @classmethod
    def register(cls, processor: SourceProcessor):
        """注册处理器"""
        cls._processors.append(processor)
    
    @classmethod
    def get_processor(cls, url: str) -> Optional[SourceProcessor]:
        """根据URL获取对应的处理器"""
        for processor in cls._processors:
            if processor.can_handle(url):
                return processor
        return None
    
    @classmethod
    def list_processors(cls) -> list[SourceProcessor]:
        """列出所有处理器"""
        return cls._processors.copy()
