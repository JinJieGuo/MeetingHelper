# MeetingHelper

一个本地命令行会议助手，用于完成会议录音、语音转写和会议纪要生成。

当前版本适合个人或小团队在本地快速跑通一条最短链路：

- 麦克风录音
- 音频转写为文本
- 基于转写生成结构化会议纪要
- 一条命令串联完整流程

## 功能概览

- `meeting devices`：查看可用音频输入设备
- `meeting record`：录制麦克风音频并保存为 WAV
- `meeting transcribe`：使用 `faster-whisper` 转写音频
- `meeting summarize`：使用 OpenAI 模型生成 Markdown 纪要
- `meeting process`：执行“录音 -> 转写 -> 纪要”一站式流程
- `meeting config`：查看或写入本地配置

## 技术栈

- Python 3.10+
- Typer
- Rich
- sounddevice
- scipy
- numpy
- faster-whisper
- OpenAI Python SDK

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

安装完成后可执行：

```bash
meeting --help
```

## 配置

推荐使用项目根目录下的 `.env`：

```bash
cp .env.example .env
```

示例配置：

```env
OPENAI_API_KEY=sk-your-api-key-here
# OPENAI_BASE_URL=https://api.openai.com/v1
# WHISPER_MODEL=medium
# GPT_MODEL=gpt-4o-mini
# MEETING_LANGUAGE=zh
```

说明：

- `OPENAI_API_KEY`：生成会议纪要时必需
- `OPENAI_BASE_URL`：接入兼容 OpenAI 协议的服务时可配置
- `WHISPER_MODEL`：默认转写模型
- `GPT_MODEL`：默认纪要模型
- `MEETING_LANGUAGE`：纪要输出语言，默认 `zh`

## 快速开始

### 1. 查看麦克风

```bash
meeting devices
```

### 2. 一站式处理

录音 30 分钟并自动生成纪要：

```bash
meeting process --duration 30
```

### 3. 分步处理

先录音：

```bash
meeting record --duration 30
```

再转写：

```bash
meeting transcribe data/recordings/meeting_xxx.wav --model medium --language zh
```

最后生成纪要：

```bash
meeting summarize data/transcriptions/meeting_xxx.txt --gpt-model gpt-4o-mini --language zh
```

## 输出目录

程序会自动创建以下目录：

```text
data/
├── recordings/
├── transcriptions/
└── summaries/
```

## 文档

- 技术说明：[docs/technical-guide.md](docs/technical-guide.md)
- 使用文档：[docs/user-guide.md](docs/user-guide.md)

## 当前限制

- 当前转写能力默认绑定 `faster-whisper`
- 当前纪要生成默认绑定 OpenAI 兼容接口
- 长文本总结尚未做分段摘要和结果合并
- 转写默认使用 CPU，未暴露更多推理后端配置

## 待办事项

1. 语音转文字改成插拔式架构，支持多种模型源和接入方式，包括本地模型、远端模型、国际主流模型，以及中国主流模型服务。
2. 会议纪要生成也改成多模型源架构，支持不同大模型厂商和兼容接口的统一接入与切换。

## 项目结构

```text
MeetingHelper/
├── README.md
├── docs/
├── data/
├── pyproject.toml
└── src/meeting_helper/
    ├── cli.py
    ├── config.py
    ├── recorder.py
    ├── transcriber.py
    ├── summarizer.py
    ├── models.py
    └── utils.py
```

## 后续建议

如果下一步准备做你列出的两个待办，我建议先做接口抽象，再接模型实现：

1. 为转写和纪要分别定义 provider 接口。
2. 在配置层增加 `provider`、`model`、`base_url`、`api_key` 等统一字段。
3. 先落地本地实现和一个远端实现，再逐步扩充不同厂商适配器。

