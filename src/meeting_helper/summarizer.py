"""GPT 会议纪要生成模块"""

from __future__ import annotations

SYSTEM_PROMPT_ZH = """你是一位专业的会议记录员。请根据以下会议转写文本生成结构化的会议纪要。

输出格式要求（Markdown）：

# 会议纪要

## 会议概要
（2-3 句话总结会议主要内容）

## 讨论内容
（按议题分条列出，每个议题包含要点）

## 决策事项
（列出会议中达成的决定）

## 待办事项
| 序号 | 事项 | 负责人 | 截止日期 |
|------|------|--------|----------|
（如果能从文本中提取到具体负责人和时间则填写，否则标注"待确认"）

## 其他备注
（任何额外的重要信息）

注意：
- 保持客观，忠实于原文
- 如果转写中有不清晰的部分，用 [不清晰] 标注
- 合并重复内容，提炼关键信息
"""

SYSTEM_PROMPT_EN = """You are a professional meeting minutes writer. Generate structured meeting minutes from the following transcript.

Output format (Markdown):

# Meeting Minutes

## Summary
(2-3 sentences summarizing the meeting)

## Discussion Points
(List key topics discussed with bullet points)

## Decisions Made
(List decisions reached during the meeting)

## Action Items
| # | Task | Owner | Deadline |
|---|------|-------|----------|
(Fill in specifics if mentioned, otherwise mark "TBD")

## Additional Notes
(Any other important information)

Notes:
- Stay objective and faithful to the transcript
- Mark unclear parts with [unclear]
- Merge duplicates and extract key information
"""


def generate_summary(
    transcript_text: str,
    api_key: str,
    gpt_model: str = "gpt-4o-mini",
    language: str = "zh",
    base_url: str | None = None,
) -> str:
    """
    使用 OpenAI GPT 生成会议纪要。

    Args:
        transcript_text: 转写文本
        api_key: OpenAI API Key
        gpt_model: GPT 模型名
        language: 输出语言
        base_url: 自定义 API base URL

    Returns:
        Markdown 格式纪要
    """
    from openai import OpenAI

    system_prompt = SYSTEM_PROMPT_ZH if language.startswith("zh") else SYSTEM_PROMPT_EN

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=gpt_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"以下是会议转写文本：\n\n{transcript_text}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content
