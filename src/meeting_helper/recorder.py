"""麦克风录音模块"""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from .config import SAMPLE_RATE, CHANNELS, DTYPE


def list_devices() -> list[dict]:
    """列出所有可用音频输入设备"""
    import sounddevice as sd

    devices = sd.query_devices()
    inputs = []
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            inputs.append({"index": i, "name": d["name"], "channels": d["max_input_channels"]})
    return inputs


def record_audio(
    output_path: Path,
    duration: float | None = None,
    device: int | None = None,
    sample_rate: int = SAMPLE_RATE,
    channels: int = CHANNELS,
    on_stop: threading.Event | None = None,
) -> float:
    """
    录制音频到 WAV 文件。

    Args:
        output_path: 输出 WAV 路径
        duration: 录制时长（秒），None 则持续到 on_stop 被 set
        device: 音频设备索引，None 使用默认
        sample_rate: 采样率
        channels: 声道数
        on_stop: 停止事件，用于外部控制停止

    Returns:
        实际录制时长（秒）
    """
    import sounddevice as sd
    from scipy.io import wavfile

    frames: list[np.ndarray] = []
    stop_event = on_stop or threading.Event()

    def callback(indata: np.ndarray, frame_count: int, time_info, status):
        if status:
            pass  # 忽略 overflow 等非致命警告
        frames.append(indata.copy())

    with sd.InputStream(
        samplerate=sample_rate,
        channels=channels,
        dtype=DTYPE,
        device=device,
        callback=callback,
        blocksize=1024,
    ):
        if duration is not None:
            stop_event.wait(timeout=duration)
        else:
            stop_event.wait()

    if not frames:
        raise RuntimeError("未录制到任何音频数据")

    audio = np.concatenate(frames, axis=0)
    wavfile.write(str(output_path), sample_rate, audio)

    actual_duration = len(audio) / sample_rate
    return actual_duration
