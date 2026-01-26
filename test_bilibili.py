#!/usr/bin/env python3
"""
Bilibili提取测试脚本
用法: python test_bilibili.py <bilibili_url>
"""
import sys
import asyncio
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.sources.bilibili import BilibiliProcessor
from src.models.unified import UnifiedContent


async def test_metadata_only(url: str):
    """只测试元数据提取"""
    print("=" * 60)
    print("测试模式: 元数据提取 (不下载视频)")
    print("=" * 60)
    
    processor = BilibiliProcessor()
    
    if not processor.can_handle(url):
        print(f"❌ 不支持的URL: {url}")
        return None
    
    print(f"✓ URL格式正确")
    print(f"  Source ID: {processor.get_source_id(url)}")
    
    print("\n正在提取元数据...")
    metadata = await processor.extract_metadata(url)
    
    print("\n📋 元数据:")
    print(f"  标题: {metadata.get('title', 'N/A')}")
    print(f"  UP主: {metadata.get('uploader', 'N/A')}")
    print(f"  时长: {metadata.get('duration', 0)}秒")
    print(f"  播放: {metadata.get('view_count', 0)}")
    print(f"  点赞: {metadata.get('like_count', 0)}")
    print(f"  标签: {', '.join(metadata.get('tags', []))[:100]}...")
    
    return metadata


async def test_full_extraction(url: str, model_size: str = "base"):
    """完整提取测试 (包含转录)"""
    print("=" * 60)
    print(f"测试模式: 完整提取 (包含视频下载和转录)")
    print(f"Whisper模型: {model_size}")
    print("=" * 60)
    
    processor = BilibiliProcessor()
    
    if not processor.can_handle(url):
        print(f"❌ 不支持的URL: {url}")
        return None
    
    try:
        content = await processor.extract_content(
            url,
            transcribe=True,
            model_size=model_size,
            language="zh"
        )
        
        print("\n✅ 提取完成!")
        print(f"\n📋 内容摘要:")
        print(f"  Content ID: {content.content_id}")
        print(f"  标题: {content.title}")
        print(f"  UP主: {content.author}")
        print(f"  描述: {content.description[:100]}..." if content.description else "  描述: N/A")
        print(f"  段落数: {len(content.sections)}")
        print(f"  总文本长度: {len(content.full_text)} 字符")
        
        # 显示前几段内容
        if content.sections:
            print(f"\n📝 前3段内容:")
            for i, section in enumerate(content.sections[:3]):
                time_info = ""
                if section.start_time is not None:
                    time_info = f"[{section.start_time:.1f}s-{section.end_time:.1f}s]"
                print(f"  {i+1}. {time_info} {section.content[:80]}...")
        
        # 保存结果
        output_dir = Path(__file__).parent / "output" / "content"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{content.content_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'content_id': content.content_id,
                'source_type': content.source_type.value,
                'source_url': content.source_url,
                'title': content.title,
                'author': content.author,
                'description': content.description,
                'tags': content.tags,
                'full_text': content.full_text,
                'sections': [
                    {
                        'title': s.title,
                        'content': s.content,
                        'start_time': s.start_time,
                        'end_time': s.end_time
                    }
                    for s in content.sections
                ],
                'raw_metadata': content.raw_metadata
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存: {output_file}")
        
        # 生成SRT字幕
        srt_content = processor.format_transcript_srt(content)
        srt_file = output_dir / f"{content.content_id}.srt"
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        print(f"📄 SRT字幕已保存: {srt_file}")
        
        return content
        
    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    if len(sys.argv) < 2:
        print("用法: python test_bilibili.py <bilibili_url> [--full] [--model=base]")
        print("\n选项:")
        print("  --full        完整提取 (包含视频下载和转录)")
        print("  --model=SIZE  Whisper模型大小 (tiny/base/small/medium/large)")
        print("\n示例:")
        print("  python test_bilibili.py https://www.bilibili.com/video/BV1xxxxx")
        print("  python test_bilibili.py https://www.bilibili.com/video/BV1xxxxx --full")
        print("  python test_bilibili.py https://www.bilibili.com/video/BV1xxxxx --full --model=small")
        sys.exit(1)
    
    url = sys.argv[1]
    full_mode = "--full" in sys.argv
    
    # 解析model参数
    model_size = "base"
    for arg in sys.argv:
        if arg.startswith("--model="):
            model_size = arg.split("=")[1]
    
    if full_mode:
        asyncio.run(test_full_extraction(url, model_size))
    else:
        asyncio.run(test_metadata_only(url))


if __name__ == "__main__":
    main()
