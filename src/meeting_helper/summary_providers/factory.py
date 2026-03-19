"""摘要 provider 工厂。"""

from __future__ import annotations

from .base import BaseSummaryProvider
from .openai_provider import OpenAISummaryProvider
from .qwen_provider import QwenSummaryProvider

SUMMARY_PROVIDER_REGISTRY: dict[str, type[BaseSummaryProvider]] = {
    "openai": OpenAISummaryProvider,
    "qwen": QwenSummaryProvider,
}


def create_summary_provider(
    *,
    provider: str,
    api_key: str,
    model: str,
    language: str,
    base_url: str | None = None,
) -> BaseSummaryProvider:
    """根据 provider 名称创建实例。"""
    try:
        provider_cls = SUMMARY_PROVIDER_REGISTRY[provider]
    except KeyError as exc:
        raise ValueError(f"不支持的纪要 provider: {provider}") from exc

    return provider_cls(
        api_key=api_key,
        model=model,
        language=language,
        base_url=base_url,
    )
