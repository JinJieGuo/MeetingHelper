"""摘要 provider 基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSummaryProvider(ABC):
    """会议纪要生成 provider 抽象。"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        language: str,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.language = language
        self.base_url = base_url

    @abstractmethod
    def generate(self, transcript_text: str) -> str:
        """根据转写生成会议纪要。"""
