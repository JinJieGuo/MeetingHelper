"""OpenAI 纪要生成 provider。"""

from __future__ import annotations

from openai import OpenAI

from .base import BaseSummaryProvider
from .prompts import build_user_prompt, get_system_prompt


class OpenAISummaryProvider(BaseSummaryProvider):
    """使用 OpenAI Chat Completions 生成纪要。"""

    def generate(self, transcript_text: str) -> str:
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": get_system_prompt(self.language)},
                {"role": "user", "content": build_user_prompt(transcript_text, self.language)},
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("模型未返回纪要内容")
        return content
