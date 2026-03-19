"""会议纪要生成模块"""

from __future__ import annotations

from .summary_providers import create_summary_provider


def generate_summary(
    transcript_text: str,
    provider: str,
    api_key: str,
    model: str,
    language: str = "zh",
    base_url: str | None = None,
) -> str:
    """
    使用指定 provider 生成会议纪要。

    Args:
        transcript_text: 转写文本
        provider: 纪要 provider 名称
        api_key: provider API Key
        model: 模型名
        language: 输出语言
        base_url: 自定义 API base URL

    Returns:
        Markdown 格式纪要
    """
    summary_provider = create_summary_provider(
        provider=provider,
        api_key=api_key,
        model=model,
        language=language,
        base_url=base_url,
    )
    return summary_provider.generate(transcript_text)
