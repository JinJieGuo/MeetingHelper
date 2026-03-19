"""配置管理 — CLI 参数 > 环境变量/.env > 配置文件"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

# 项目根目录 & 数据目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
TRANSCRIPTIONS_DIR = DATA_DIR / "transcriptions"
SUMMARIES_DIR = DATA_DIR / "summaries"

# 用户级配置文件
CONFIG_DIR = Path.home() / ".config" / "meeting-helper"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Whisper 模型选项
WHISPER_MODELS = ("tiny", "base", "small", "medium", "large-v3")
DEFAULT_WHISPER_MODEL = "medium"
SUMMARY_PROVIDERS = ("openai", "qwen")
DEFAULT_SUMMARY_PROVIDER = "openai"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_QWEN_MODEL = "qwen-plus"
DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 录音参数
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"


@dataclass
class AppConfig:
    """应用配置，支持多级合并"""

    summary_provider: str = DEFAULT_SUMMARY_PROVIDER
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = DEFAULT_OPENAI_MODEL
    qwen_api_key: str = ""
    qwen_base_url: str = DEFAULT_QWEN_BASE_URL
    qwen_model: str = DEFAULT_QWEN_MODEL
    huggingface_token: str = ""
    whisper_model: str = DEFAULT_WHISPER_MODEL
    language: str = "zh"
    sample_rate: int = SAMPLE_RATE
    channels: int = CHANNELS
    recordings_dir: str = str(RECORDINGS_DIR)
    transcriptions_dir: str = str(TRANSCRIPTIONS_DIR)
    summaries_dir: str = str(SUMMARIES_DIR)

    def ensure_dirs(self) -> None:
        """确保数据目录存在"""
        for d in (self.recordings_dir, self.transcriptions_dir, self.summaries_dir):
            Path(d).mkdir(parents=True, exist_ok=True)


def _load_config_file() -> dict:
    """从 ~/.config/meeting-helper/config.json 读取"""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def _load_env() -> dict:
    """从 .env / 环境变量读取"""
    load_dotenv(PROJECT_ROOT / ".env")
    mapping = {
        "SUMMARY_PROVIDER": "summary_provider",
        "OPENAI_API_KEY": "openai_api_key",
        "OPENAI_BASE_URL": "openai_base_url",
        "OPENAI_MODEL": "openai_model",
        "QWEN_API_KEY": "qwen_api_key",
        "QWEN_BASE_URL": "qwen_base_url",
        "QWEN_MODEL": "qwen_model",
        "HUGGINGFACE_TOKEN": "huggingface_token",
        "WHISPER_MODEL": "whisper_model",
        "MEETING_LANGUAGE": "language",
    }
    result = {}
    for env_key, cfg_key in mapping.items():
        val = os.getenv(env_key)
        if val:
            result[cfg_key] = val

    # 兼容旧配置与 DashScope 默认环境变量
    if not result.get("openai_model"):
        legacy_gpt_model = os.getenv("GPT_MODEL")
        if legacy_gpt_model:
            result["openai_model"] = legacy_gpt_model

    if not result.get("qwen_api_key"):
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        if dashscope_api_key:
            result["qwen_api_key"] = dashscope_api_key

    return result


def _normalize_legacy_config(merged: dict) -> dict:
    """兼容旧版配置字段。"""
    normalized = dict(merged)

    legacy_gpt_model = normalized.pop("gpt_model", None)
    if legacy_gpt_model and not normalized.get("openai_model"):
        normalized["openai_model"] = legacy_gpt_model

    if not normalized.get("summary_provider"):
        normalized["summary_provider"] = DEFAULT_SUMMARY_PROVIDER

    return normalized


def load_config(**cli_overrides: str) -> AppConfig:
    """合并配置：CLI 参数 > 环境变量 > 配置文件 > 默认值"""
    merged: dict = {}
    # 1) 配置文件（最低优先级）
    merged.update(_load_config_file())
    # 2) 环境变量
    merged.update(_load_env())
    # 3) CLI 参数（最高优先级，过滤 None）
    merged.update({k: v for k, v in cli_overrides.items() if v is not None})
    merged = _normalize_legacy_config(merged)

    cfg = AppConfig(**{k: v for k, v in merged.items() if k in AppConfig.__dataclass_fields__})
    cfg.ensure_dirs()
    return cfg


def save_config(cfg: AppConfig) -> None:
    """持久化配置到文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(asdict(cfg), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def resolve_summary_settings(
    cfg: AppConfig,
    *,
    provider_override: str | None = None,
    model_override: str | None = None,
) -> tuple[str, str, str, str | None]:
    """解析当前生效的纪要 provider 配置。"""
    provider = provider_override or cfg.summary_provider
    if provider not in SUMMARY_PROVIDERS:
        raise ValueError(f"无效的纪要 provider: {provider}，可选: {', '.join(SUMMARY_PROVIDERS)}")

    if provider == "openai":
        return (
            provider,
            model_override or cfg.openai_model,
            cfg.openai_api_key,
            cfg.openai_base_url or None,
        )

    return (
        provider,
        model_override or cfg.qwen_model,
        cfg.qwen_api_key,
        cfg.qwen_base_url or None,
    )
