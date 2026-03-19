"""Whisper 语音转写模块（基于 faster-whisper）"""

from __future__ import annotations

from pathlib import Path

from .config import DEFAULT_WHISPER_MODEL
from .models import Transcription, Segment


def transcribe_audio(
    audio_path: Path,
    model_size: str = DEFAULT_WHISPER_MODEL,
    language: str | None = None,
    device: str = "cpu",
    compute_type: str = "int8",
    diarize: bool = False,
    hf_token: str | None = None,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> Transcription:
    """
    使用 faster-whisper 转写音频文件。

    Args:
        audio_path: 音频文件路径
        model_size: Whisper 模型大小
        language: 强制指定语言（None 则自动检测）
        device: 推理设备
        compute_type: 量化类型
        diarize: 是否启用发言人区分
        hf_token: Hugging Face access token
        min_speakers: 最少说话人数
        max_speakers: 最多说话人数

    Returns:
        Transcription 对象
    """
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    segments = []
    for seg in segments_iter:
        text = seg.text.strip()
        if text:
            segments.append(Segment(start=seg.start, end=seg.end, text=text))

    speaker_count: int | None = None
    if diarize:
        from .diarizer import assign_speakers

        segments, speaker_count = assign_speakers(
            audio_path=audio_path,
            segments=segments,
            hf_token=hf_token or "",
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )

    return Transcription(
        audio_file=audio_path,
        segments=segments,
        language=info.language,
        model=model_size,
        duration_seconds=info.duration,
        diarized=diarize,
        speaker_count=speaker_count,
    )
