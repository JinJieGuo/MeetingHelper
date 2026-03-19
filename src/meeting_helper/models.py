"""数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Recording:
    """录音元数据"""

    file_path: Path
    duration_seconds: float
    sample_rate: int
    channels: int
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Segment:
    """转写片段"""

    start: float
    end: float
    text: str
    speaker: str | None = None


@dataclass
class Transcription:
    """转写结果"""

    audio_file: Path
    segments: list[Segment]
    language: str
    model: str
    duration_seconds: float
    diarized: bool = False
    speaker_count: int | None = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def full_text(self) -> str:
        lines = []
        for seg in self.segments:
            speaker_prefix = f"[{seg.speaker}] " if seg.speaker else ""
            lines.append(f"{speaker_prefix}{seg.text}")
        return "\n".join(lines)


@dataclass
class Summary:
    """会议纪要"""

    transcription_file: Path
    content: str
    provider: str
    model: str
    language: str
    created_at: datetime = field(default_factory=datetime.now)
