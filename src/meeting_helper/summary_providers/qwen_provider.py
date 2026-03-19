"""Qwen 纪要生成 provider。"""

from __future__ import annotations

from .openai_provider import OpenAISummaryProvider


class QwenSummaryProvider(OpenAISummaryProvider):
    """Qwen 通过 OpenAI 兼容接口生成纪要。"""
