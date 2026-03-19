"""Typer CLI 入口 — 所有命令定义"""

from __future__ import annotations

import signal
import sys
import threading
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .config import (
    WHISPER_MODELS,
    DEFAULT_WHISPER_MODEL,
    load_config,
    save_config,
)
from .utils import (
    generate_filename,
    format_duration,
    save_transcription,
    load_transcription_text,
    save_summary,
)

app = typer.Typer(
    name="meeting",
    help="会议录音转写与纪要生成工具",
    no_args_is_help=True,
)
console = Console()


# ── devices ──────────────────────────────────────────────────────────


@app.command()
def devices():
    """列出可用麦克风设备"""
    from .recorder import list_devices

    devs = list_devices()
    if not devs:
        console.print("[yellow]未检测到音频输入设备[/yellow]")
        raise typer.Exit(1)

    table = Table(title="可用音频输入设备")
    table.add_column("索引", style="cyan", justify="right")
    table.add_column("名称", style="green")
    table.add_column("声道数", justify="right")
    for d in devs:
        table.add_row(str(d["index"]), d["name"], str(d["channels"]))
    console.print(table)


# ── record ───────────────────────────────────────────────────────────


@app.command()
def record(
    duration: Optional[float] = typer.Option(None, "--duration", "-d", help="录制时长（分钟），留空则 Ctrl+C 停止"),
    device: Optional[int] = typer.Option(None, "--device", help="音频设备索引（见 meeting devices）"),
):
    """录制麦克风音频"""
    from .recorder import record_audio

    cfg = load_config()
    output_dir = Path(cfg.recordings_dir)
    output_path = output_dir / generate_filename()

    duration_seconds = duration * 60 if duration is not None else None

    stop_event = threading.Event()

    def handle_signal(sig, frame):
        console.print("\n[yellow]停止录音...[/yellow]")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)

    if duration_seconds:
        console.print(f"[green]开始录音[/green] — 时长 {format_duration(duration_seconds)}，按 Ctrl+C 提前停止")
    else:
        console.print("[green]开始录音[/green] — 按 Ctrl+C 停止")

    console.print(f"  保存路径: {output_path}")

    try:
        actual = record_audio(
            output_path=output_path,
            duration=duration_seconds,
            device=device,
            sample_rate=cfg.sample_rate,
            channels=cfg.channels,
            on_stop=stop_event,
        )
        console.print(f"[green]录音完成[/green] — 时长 {format_duration(actual)}")
        console.print(f"  文件: {output_path}")
    except RuntimeError as e:
        console.print(f"[red]录音失败: {e}[/red]")
        raise typer.Exit(1)


# ── transcribe ───────────────────────────────────────────────────────


@app.command()
def transcribe(
    file: Path = typer.Argument(..., help="音频文件路径", exists=True),
    model: str = typer.Option(DEFAULT_WHISPER_MODEL, "--model", "-m", help=f"Whisper 模型 ({', '.join(WHISPER_MODELS)})"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="强制语言代码（如 zh, en），留空自动检测"),
    diarize: bool = typer.Option(False, "--diarize", help="启用发言人区分（需要 Hugging Face token）"),
    min_speakers: Optional[int] = typer.Option(None, "--min-speakers", help="最少说话人数"),
    max_speakers: Optional[int] = typer.Option(None, "--max-speakers", help="最多说话人数"),
):
    """转写音频文件为文本"""
    if model not in WHISPER_MODELS:
        console.print(f"[red]无效模型: {model}，可选: {', '.join(WHISPER_MODELS)}[/red]")
        raise typer.Exit(1)
    if min_speakers is not None and max_speakers is not None and min_speakers > max_speakers:
        console.print("[red]错误: --min-speakers 不能大于 --max-speakers[/red]")
        raise typer.Exit(1)

    cfg = load_config()

    if diarize and not cfg.huggingface_token:
        console.print("[red]错误: 未配置 HUGGINGFACE_TOKEN，无法启用发言人区分[/red]")
        raise typer.Exit(1)

    mode_desc = f"{model} + diarization" if diarize else model

    console.print(f"[green]开始转写[/green] — 模型: {mode_desc}")
    console.print(f"  文件: {file}")

    with console.status("[bold green]加载模型并转写中..."):
        from .transcriber import transcribe_audio

        try:
            result = transcribe_audio(
                audio_path=file,
                model_size=model,
                language=language,
                diarize=diarize,
                hf_token=cfg.huggingface_token,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )
        except Exception as exc:
            console.print(f"[red]转写失败: {exc}[/red]")
            raise typer.Exit(1)

    output_dir = Path(cfg.transcriptions_dir)
    json_path, txt_path = save_transcription(result, output_dir)

    speaker_info = f", 说话人数: {result.speaker_count}" if result.diarized and result.speaker_count else ""
    console.print(f"[green]转写完成[/green] — 语言: {result.language}, 片段数: {len(result.segments)}{speaker_info}")
    console.print(f"  JSON: {json_path}")
    console.print(f"  TXT:  {txt_path}")

    # 打印前几段预览
    preview_count = min(5, len(result.segments))
    if preview_count > 0:
        console.print("\n[dim]── 转写预览 ──[/dim]")
        for seg in result.segments[:preview_count]:
            speaker_label = f"[{seg.speaker}] " if seg.speaker else ""
            console.print(f"  {format_duration(seg.start)} {speaker_label}{seg.text}")
        if len(result.segments) > preview_count:
            console.print(f"  [dim]... 共 {len(result.segments)} 段[/dim]")


# ── summarize ────────────────────────────────────────────────────────


@app.command()
def summarize(
    file: Path = typer.Argument(..., help="转写文件路径（JSON 或 TXT）", exists=True),
    gpt_model: Optional[str] = typer.Option(None, "--gpt-model", help="GPT 模型名"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="纪要语言（zh/en）"),
):
    """根据转写文本生成会议纪要"""
    cfg = load_config(
        gpt_model=gpt_model,
        language=language,
    )

    if not cfg.openai_api_key:
        console.print("[red]错误: 未配置 OPENAI_API_KEY[/red]")
        console.print("  请在 .env 文件或环境变量中设置 OPENAI_API_KEY")
        raise typer.Exit(1)

    transcript_text = load_transcription_text(file)
    if not transcript_text.strip():
        console.print("[red]错误: 转写文件为空[/red]")
        raise typer.Exit(1)

    console.print(f"[green]生成纪要[/green] — 模型: {cfg.gpt_model}")

    with console.status("[bold green]GPT 生成中..."):
        from .summarizer import generate_summary

        content = generate_summary(
            transcript_text=transcript_text,
            api_key=cfg.openai_api_key,
            gpt_model=cfg.gpt_model,
            language=cfg.language,
            base_url=cfg.openai_base_url or None,
        )

    output_dir = Path(cfg.summaries_dir)
    md_path = save_summary(content, output_dir, file.stem)

    console.print(f"[green]纪要生成完成[/green]")
    console.print(f"  文件: {md_path}")
    console.print()
    console.print(Panel(content, title="会议纪要", border_style="green"))


# ── process ──────────────────────────────────────────────────────────


@app.command()
def process(
    audio_file: Optional[Path] = typer.Option(None, "--audio-file", "-f", help="已有音频文件（跳过录音）"),
    duration: Optional[float] = typer.Option(None, "--duration", "-d", help="录制时长（分钟）"),
    device: Optional[int] = typer.Option(None, "--device", help="音频设备索引"),
    model: str = typer.Option(DEFAULT_WHISPER_MODEL, "--model", "-m", help="Whisper 模型"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="语言代码"),
    gpt_model: Optional[str] = typer.Option(None, "--gpt-model", help="GPT 模型名"),
    diarize: bool = typer.Option(False, "--diarize", help="启用发言人区分（需要 Hugging Face token）"),
    min_speakers: Optional[int] = typer.Option(None, "--min-speakers", help="最少说话人数"),
    max_speakers: Optional[int] = typer.Option(None, "--max-speakers", help="最多说话人数"),
):
    """一站式处理：录音 → 转写 → 生成纪要"""
    cfg = load_config(gpt_model=gpt_model, language=language)
    if min_speakers is not None and max_speakers is not None and min_speakers > max_speakers:
        console.print("[red]错误: --min-speakers 不能大于 --max-speakers[/red]")
        raise typer.Exit(1)

    if not cfg.openai_api_key:
        console.print("[red]错误: 未配置 OPENAI_API_KEY（纪要生成需要）[/red]")
        raise typer.Exit(1)
    if diarize and not cfg.huggingface_token:
        console.print("[red]错误: 未配置 HUGGINGFACE_TOKEN，无法启用发言人区分[/red]")
        raise typer.Exit(1)

    # ── Step 1: 录音（或使用已有文件）──
    if audio_file:
        if not audio_file.exists():
            console.print(f"[red]文件不存在: {audio_file}[/red]")
            raise typer.Exit(1)
        wav_path = audio_file
        console.print(f"[green]使用已有音频[/green]: {wav_path}")
    else:
        from .recorder import record_audio

        wav_path = Path(cfg.recordings_dir) / generate_filename()
        duration_seconds = duration * 60 if duration is not None else None

        stop_event = threading.Event()

        def handle_signal(sig, frame):
            console.print("\n[yellow]停止录音...[/yellow]")
            stop_event.set()

        signal.signal(signal.SIGINT, handle_signal)

        if duration_seconds:
            console.print(f"[green]Step 1/3: 开始录音[/green] — 时长 {format_duration(duration_seconds)}")
        else:
            console.print("[green]Step 1/3: 开始录音[/green] — 按 Ctrl+C 停止")

        actual = record_audio(
            output_path=wav_path,
            duration=duration_seconds,
            device=device,
            sample_rate=cfg.sample_rate,
            channels=cfg.channels,
            on_stop=stop_event,
        )
        console.print(f"  录音完成 — {format_duration(actual)}")

        # 恢复默认 SIGINT 行为
        signal.signal(signal.SIGINT, signal.default_int_handler)

    # ── Step 2: 转写 ──
    mode_desc = f"{model} + diarization" if diarize else model
    console.print(f"\n[green]Step 2/3: 转写[/green] — 模型: {mode_desc}")

    with console.status("[bold green]加载模型并转写中..."):
        from .transcriber import transcribe_audio

        try:
            transcription = transcribe_audio(
                audio_path=wav_path,
                model_size=model,
                language=language,
                diarize=diarize,
                hf_token=cfg.huggingface_token,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )
        except Exception as exc:
            console.print(f"[red]转写失败: {exc}[/red]")
            raise typer.Exit(1)

    output_dir = Path(cfg.transcriptions_dir)
    json_path, txt_path = save_transcription(transcription, output_dir)
    speaker_info = f", 说话人数: {transcription.speaker_count}" if transcription.diarized and transcription.speaker_count else ""
    console.print(f"  转写完成 — {len(transcription.segments)} 段, 语言: {transcription.language}{speaker_info}")
    console.print(f"  JSON: {json_path}")
    console.print(f"  TXT:  {txt_path}")

    # ── Step 3: 纪要 ──
    console.print(f"\n[green]Step 3/3: 生成纪要[/green] — 模型: {cfg.gpt_model}")
    transcript_text = load_transcription_text(json_path)

    with console.status("[bold green]GPT 生成中..."):
        from .summarizer import generate_summary

        summary_content = generate_summary(
            transcript_text=transcript_text,
            api_key=cfg.openai_api_key,
            gpt_model=cfg.gpt_model,
            language=cfg.language,
            base_url=cfg.openai_base_url or None,
        )

    md_path = save_summary(summary_content, Path(cfg.summaries_dir), wav_path.stem)
    console.print(f"  纪要已保存: {md_path}")
    console.print()
    console.print(Panel(summary_content, title="会议纪要", border_style="green"))


# ── config ───────────────────────────────────────────────────────────


@app.command("config")
def config_cmd(
    show: bool = typer.Option(False, "--show", "-s", help="显示当前配置"),
    set_value: Optional[str] = typer.Option(None, "--set", help="设置配置项（格式: key=value）"),
):
    """查看或设置配置"""
    from dataclasses import asdict

    cfg = load_config()

    if set_value:
        if "=" not in set_value:
            console.print("[red]格式错误，请使用 key=value[/red]")
            raise typer.Exit(1)
        key, value = set_value.split("=", 1)
        key = key.strip()
        if key not in cfg.__dataclass_fields__:
            console.print(f"[red]未知配置项: {key}[/red]")
            console.print(f"  可用: {', '.join(cfg.__dataclass_fields__.keys())}")
            raise typer.Exit(1)
        setattr(cfg, key, value)
        save_config(cfg)
        console.print(f"[green]已设置[/green] {key} = {value}")
        return

    # 默认或 --show：显示配置
    table = Table(title="当前配置")
    table.add_column("配置项", style="cyan")
    table.add_column("值", style="green")
    for key, value in asdict(cfg).items():
        display_val = str(value)
        if key in {"openai_api_key", "huggingface_token"} and value:
            display_val = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
        table.add_row(key, display_val)
    console.print(table)
