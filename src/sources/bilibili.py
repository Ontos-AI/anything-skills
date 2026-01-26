"""Skills Forge - Bilibili内容源处理器"""
import re
import uuid
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import tempfile

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import whisper
except ImportError:
    whisper = None

from src.sources.base import SourceProcessor, SourceRegistry
from src.models.unified import UnifiedContent, SourceType, Section
from src.core.config import config


class BilibiliProcessor(SourceProcessor):
    """Bilibili视频处理器"""
    
    source_type = SourceType.BILIBILI
    
    # Bilibili URL patterns
    URL_PATTERNS = [
        r'bilibili\.com/video/(BV[\w]+)',
        r'b23\.tv/([\w]+)',
        r'bilibili\.com/video/av(\d+)',
    ]
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "skills_forge"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def can_handle(self, url: str) -> bool:
        """判断是否为Bilibili URL"""
        return any(re.search(p, url) for p in self.URL_PATTERNS)
    
    def get_source_id(self, url: str) -> Optional[str]:
        """从URL提取BV号"""
        for pattern in self.URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def extract_metadata(self, url: str) -> dict:
        """提取视频元数据"""
        if not yt_dlp:
            raise ImportError("yt-dlp is required. Install with: pip install yt-dlp")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        return {
            'id': info.get('id', ''),
            'title': info.get('title', ''),
            'description': info.get('description', ''),
            'uploader': info.get('uploader', ''),
            'uploader_id': info.get('uploader_id', ''),
            'upload_date': info.get('upload_date', ''),
            'duration': info.get('duration', 0),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'tags': info.get('tags', []),
            'categories': info.get('categories', []),
            'thumbnail': info.get('thumbnail', ''),
        }
    
    async def download_video(self, url: str, output_path: Optional[Path] = None) -> Path:
        """下载视频"""
        if not yt_dlp:
            raise ImportError("yt-dlp is required")
        
        if output_path is None:
            output_path = self.temp_dir / f"{uuid.uuid4()}.mp4"
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(output_path),
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        return output_path
    
    async def extract_audio(self, video_path: Path) -> Path:
        """从视频提取音频"""
        audio_path = video_path.with_suffix('.mp3')
        
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
            '-y', str(audio_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return audio_path
    
    async def transcribe_audio(
        self, 
        audio_path: Path, 
        model_size: str = "base",
        language: str = "zh"
    ) -> Dict[str, Any]:
        """转录音频为文本"""
        if not whisper:
            raise ImportError("whisper is required. Install with: pip install openai-whisper")
        
        model = whisper.load_model(model_size)
        result = model.transcribe(str(audio_path), language=language)
        
        return {
            'text': result['text'],
            'segments': [
                {
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text']
                }
                for seg in result['segments']
            ],
            'language': result.get('language', language)
        }
    
    async def extract_content(
        self, 
        url: str,
        transcribe: bool = True,
        model_size: str = "base",
        language: str = "zh",
        keep_video: bool = False,
        **options
    ) -> UnifiedContent:
        """完整提取流程：元数据 + 视频下载 + 音频提取 + 转录"""
        
        # 1. 提取元数据
        print(f"[1/4] 提取元数据: {url}")
        metadata = await self.extract_metadata(url)
        
        source_id = self.get_source_id(url) or metadata.get('id', '')
        content_id = str(uuid.uuid4())
        
        # 解析上传日期
        upload_date = None
        if metadata.get('upload_date'):
            try:
                upload_date = datetime.strptime(metadata['upload_date'], '%Y%m%d')
            except ValueError:
                pass
        
        # 初始化UnifiedContent
        content = UnifiedContent(
            content_id=content_id,
            source_type=SourceType.BILIBILI,
            source_url=url,
            source_id=source_id,
            title=metadata.get('title', ''),
            author=metadata.get('uploader', ''),
            created_at=upload_date,
            tags=metadata.get('tags', []),
            description=metadata.get('description', ''),
            raw_metadata=metadata,
        )
        
        if not transcribe:
            return content
        
        video_path = None
        audio_path = None
        
        try:
            # 2. 下载视频
            print(f"[2/4] 下载视频...")
            video_path = await self.download_video(url)
            
            # 3. 提取音频
            print(f"[3/4] 提取音频...")
            audio_path = await self.extract_audio(video_path)
            
            # 4. 转录
            print(f"[4/4] 转录音频 (模型: {model_size})...")
            transcript = await self.transcribe_audio(audio_path, model_size, language)
            
            # 更新内容
            content.full_text = transcript['text']
            content.transcription_model = model_size
            
            # 转换segments为sections
            content.sections = [
                Section(
                    title=f"段落 {i+1}",
                    content=seg['text'],
                    start_time=seg['start'],
                    end_time=seg['end']
                )
                for i, seg in enumerate(transcript['segments'])
            ]
            
        finally:
            # 清理临时文件
            if audio_path and audio_path.exists():
                audio_path.unlink()
            if video_path and video_path.exists() and not keep_video:
                video_path.unlink()
        
        return content
    
    def format_transcript_srt(self, content: UnifiedContent) -> str:
        """格式化为SRT字幕"""
        def format_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        
        lines = []
        for i, section in enumerate(content.sections, 1):
            if section.start_time is not None and section.end_time is not None:
                lines.append(str(i))
                lines.append(f"{format_time(section.start_time)} --> {format_time(section.end_time)}")
                lines.append(section.content)
                lines.append("")
        
        return "\n".join(lines)


# 注册处理器
SourceRegistry.register(BilibiliProcessor())
