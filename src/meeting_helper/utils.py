"""工具函数"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import Transcription, Segment


def generate_filename(prefix: str = "meeting", ext: str = "wav") -> str:
    """生成带时间戳的文件名"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.{ext}"


def format_duration(seconds: float) -> str:
    """将秒数格式化为 HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_timestamp(seconds: float) -> str:
    """将秒数格式化为 [MM:SS] 时间戳"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"[{m:02d}:{s:02d}]"


def save_transcription(transcription: Transcription, output_dir: Path) -> tuple[Path, Path]:
    """保存转写结果为 JSON + TXT，返回两个文件路径"""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = transcription.audio_file.stem

    # JSON（完整数据）
    json_path = output_dir / f"{stem}.json"
    data = {
        "audio_file": str(transcription.audio_file),
        "language": transcription.language,
        "model": transcription.model,
        "duration_seconds": transcription.duration_seconds,
        "diarized": transcription.diarized,
        "speaker_count": transcription.speaker_count,
        "created_at": transcription.created_at.isoformat(),
        "segments": [
            {
                "start": s.start,
                "end": s.end,
                "speaker": s.speaker,
                "text": s.text,
            }
            for s in transcription.segments
        ],
    }
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # TXT（带时间戳的纯文本）
    txt_path = output_dir / f"{stem}.txt"
    lines = [
        _format_segment_line(s.start, s.text, s.speaker) for s in transcription.segments
    ]
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    return json_path, txt_path


def load_transcription_text(file_path: Path) -> str:
    """从 JSON 或 TXT 文件加载转写文本"""
    if file_path.suffix == ".json":
        data = json.loads(file_path.read_text(encoding="utf-8"))
        segments = data.get("segments", [])
        return "\n".join(
            _format_segment_line(s["start"], s["text"], s.get("speaker"))
            for s in segments
        )
    # TXT 直接读取
    return file_path.read_text(encoding="utf-8")


def save_summary(content: str, output_dir: Path, stem: str) -> Path:
    """保存会议纪要为 Markdown"""
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{stem}_summary.md"
    md_path.write_text(content, encoding="utf-8")
    return md_path


def _format_segment_line(start: float, text: str, speaker: str | None) -> str:
    """格式化单行转写文本。"""
    speaker_part = f" [{speaker}]" if speaker else ""
    return f"{format_timestamp(start)}{speaker_part} {text}"
