"""Skills Forge - 配置管理"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """应用配置"""
    
    # 项目路径
    BASE_DIR = Path(__file__).parent.parent.parent
    OUTPUT_DIR = BASE_DIR / "output"
    SKILLS_DIR = OUTPUT_DIR / "skills"
    CONTENT_DIR = OUTPUT_DIR / "content"
    
    # API配置
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # LLM配置
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_LLM = os.getenv("DEFAULT_LLM", "claude")
    
    # Whisper配置
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
    WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "zh")
    
    # 数据库
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/skills_forge.db")
    
    @classmethod
    def ensure_dirs(cls):
        """确保必要目录存在"""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        cls.CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        (cls.BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


config = Config()
