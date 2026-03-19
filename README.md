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
- `meeting transcribe`：使用 `faster-whisper` 转写音频，可选发言人区分
- `meeting summarize`：使用可切换的摘要 provider 生成 Markdown 纪要
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
- pyannote.audio
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
# SUMMARY_PROVIDER=openai
# OPENAI_API_KEY=sk-your-openai-api-key-here
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_MODEL=gpt-4o-mini
# QWEN_API_KEY=sk-your-qwen-api-key-here
# QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# QWEN_MODEL=qwen-plus
# HUGGINGFACE_TOKEN=hf_your_token_here
# WHISPER_MODEL=medium
# MEETING_LANGUAGE=zh
```

说明：

- `SUMMARY_PROVIDER`：当前纪要生成 provider，默认 `openai`
- `OPENAI_API_KEY` / `QWEN_API_KEY`：分别对应各自 provider 的 API Key
- `OPENAI_BASE_URL`：接入自定义 OpenAI 兼容接口时可配置
- `QWEN_BASE_URL`：Qwen OpenAI 兼容地址，默认使用阿里云百炼北京地域地址
- `HUGGINGFACE_TOKEN`：启用发言人区分时必需
- `WHISPER_MODEL`：默认转写模型
- `OPENAI_MODEL` / `QWEN_MODEL`：各 provider 的默认纪要模型
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

如果希望区分发言人：

```bash
meeting transcribe data/recordings/meeting_xxx.wav --model medium --language zh --diarize
```

最后生成纪要：

```bash
meeting summarize data/transcriptions/meeting_xxx.txt --summary-provider openai --summary-model gpt-4o-mini --language zh
```

切换到 Qwen：

```bash
meeting summarize data/transcriptions/meeting_xxx.txt --summary-provider qwen --summary-model qwen-plus --language zh
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
- 发言人区分方案：[docs/whisper-speaker-diarization-plan.md](docs/whisper-speaker-diarization-plan.md)

## 当前状态

Whisper 发言人区分能力已经落地，当前支持：

- `meeting transcribe --diarize`
- `meeting process --diarize`
- 转写 JSON/TXT 输出 `speaker`
- 将发言人标签传递给后续纪要生成链路

本地已完成一次端到端验证：

- 测试输入：`data/recordings/meeting_20260318_152652.wav`
- 执行命令：`meeting transcribe ... --model base --language zh --diarize`
- 结果：成功生成带 `SPEAKER_00` 标签的 JSON 和 TXT 转写文件

## 当前限制

- 当前转写能力默认绑定 `faster-whisper`
- 当前纪要生成已支持 OpenAI / Qwen 两种 provider
- 长文本总结尚未做分段摘要和结果合并
- 转写默认使用 CPU，未暴露更多推理后端配置
- 发言人区分依赖 `pyannote.audio`、`ffmpeg` 和 Hugging Face token

## 待办事项

1. 语音转文字改成插拔式架构，支持多种模型源和接入方式，包括本地模型、远端模型、国际主流模型，以及中国主流模型服务。
2. 长文本纪要生成补充分段摘要、结果合并和重试策略。
3. 优化生成纪要的提示词，提升结构稳定性、行动项提取准确率和中文表达质量。

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
    ├── diarizer.py
    ├── recorder.py
    ├── summary_providers/
    ├── transcriber.py
    ├── summarizer.py
    ├── models.py
    └── utils.py
```
