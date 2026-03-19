"""说话人区分模块（基于 pyannote.audio）"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from .models import Segment

DEFAULT_DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"
UNKNOWN_SPEAKER = "UNKNOWN"


def assign_speakers(
    audio_path: Path,
    segments: list[Segment],
    hf_token: str,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> tuple[list[Segment], int | None]:
    """
    使用 pyannote.audio 对 Whisper 片段进行说话人标签回填。

    Args:
        audio_path: 音频文件路径
        segments: Whisper 产生的分段
        hf_token: Hugging Face access token
        min_speakers: 最少说话人数
        max_speakers: 最多说话人数

    Returns:
        (新分段列表, 识别到的说话人数)
    """
    if not hf_token:
        raise ValueError("未配置 HUGGINGFACE_TOKEN，无法启用发言人区分")
    if not segments:
        return [], None

    os.environ.setdefault("HF_TOKEN", hf_token)

    from huggingface_hub.errors import GatedRepoError
    from pyannote.audio import Pipeline

    try:
        pipeline = Pipeline.from_pretrained(DEFAULT_DIARIZATION_MODEL, token=hf_token)
    except GatedRepoError as exc:
        raise RuntimeError(
            "Hugging Face token 已配置，但当前账号还没有访问 "
            f"{DEFAULT_DIARIZATION_MODEL} 的权限。请先在 "
            f"https://huggingface.co/{DEFAULT_DIARIZATION_MODEL} "
            "接受使用条款并申请访问，然后重试。"
        ) from exc

    diarization_kwargs = {}
    if min_speakers is not None:
        diarization_kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        diarization_kwargs["max_speakers"] = max_speakers

    diarization = pipeline(str(audio_path), **diarization_kwargs)

    annotation = getattr(diarization, "speaker_diarization", diarization)

    speaker_turns: list[tuple[float, float, str]] = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        speaker_turns.append((float(turn.start), float(turn.end), str(speaker)))

    labels = annotation.labels() if hasattr(annotation, "labels") else []
    speaker_count = len(labels) if labels else None

    return (
        [_assign_best_speaker(segment, speaker_turns) for segment in segments],
        speaker_count,
    )


def _assign_best_speaker(
    segment: Segment,
    speaker_turns: list[tuple[float, float, str]],
) -> Segment:
    """将重叠时长最大的说话人标签分配给单个转写片段。"""
    best_speaker = None
    best_overlap = 0.0

    for turn_start, turn_end, speaker in speaker_turns:
        overlap = _compute_overlap(
            segment.start,
            segment.end,
            turn_start,
            turn_end,
        )
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = speaker

    return replace(segment, speaker=best_speaker or UNKNOWN_SPEAKER)


def _compute_overlap(
    left_start: float,
    left_end: float,
    right_start: float,
    right_end: float,
) -> float:
    """计算两个时间区间的重叠时长。"""
    return max(0.0, min(left_end, right_end) - max(left_start, right_start))
