# MeetingHelper 使用文档

## 1. 工具简介

MeetingHelper 是一个命令行会议助手，支持：

- 录制麦克风音频
- 将会议音频转写为文本
- 基于转写内容生成结构化会议纪要
- 通过一条命令完成完整处理流程

适用场景：

- 个人会议记录
- 项目周会纪要整理
- 访谈或沟通记录归档
- 先录音后统一转写和总结

## 2. 环境要求

运行前请确认：

- Python 版本不低于 `3.10`
- 本机有可用麦克风
- 网络可访问所配置的 OpenAI 接口
- 首次转写 Whisper 模型时，环境允许下载模型文件

## 3. 安装

在项目根目录执行：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

安装完成后，可通过以下命令确认 CLI 已注册：

```bash
meeting --help
```

## 4. 配置

### 4.1 方式一：使用 `.env`

项目根目录提供了示例文件 `.env.example`。可以复制为 `.env` 后按需修改：

```bash
cp .env.example .env
```

常用配置如下：

```env
OPENAI_API_KEY=sk-your-api-key-here
# OPENAI_BASE_URL=https://api.openai.com/v1
# WHISPER_MODEL=medium
# GPT_MODEL=gpt-4o-mini
# MEETING_LANGUAGE=zh
```

说明：

- `OPENAI_API_KEY`：生成会议纪要必填
- `OPENAI_BASE_URL`：使用自定义兼容接口时可配置
- `WHISPER_MODEL`：默认 Whisper 模型
- `GPT_MODEL`：默认总结模型
- `MEETING_LANGUAGE`：纪要输出语言，默认 `zh`

### 4.2 方式二：使用命令写入用户配置

查看当前配置：

```bash
meeting config --show
```

设置单个配置项：

```bash
meeting config --set gpt_model=gpt-4o-mini
meeting config --set language=zh
```

用户配置文件保存位置：

```text
~/.config/meeting-helper/config.json
```

### 4.3 配置优先级

同一配置项冲突时，优先级如下：

1. 命令行参数
2. 环境变量或 `.env`
3. `~/.config/meeting-helper/config.json`
4. 默认值

## 5. 输出目录

程序会自动创建以下目录：

```text
data/
├── recordings/
├── transcriptions/
└── summaries/
```

各目录用途：

- `data/recordings`：保存录音 WAV 文件
- `data/transcriptions`：保存转写 JSON 和 TXT
- `data/summaries`：保存 Markdown 纪要

## 6. 命令说明

### 6.1 查看音频输入设备

```bash
meeting devices
```

用途：

- 列出当前机器可用的麦克风输入设备
- 获取设备索引，供录音命令中的 `--device` 使用

### 6.2 录音

录制定时会议：

```bash
meeting record --duration 30
```

说明：

- `--duration` 单位是分钟
- 上例会录制 30 分钟

如果希望手动停止录音：

```bash
meeting record
```

录音开始后按 `Ctrl+C` 即可停止。

指定音频设备：

```bash
meeting record --device 1 --duration 10
```

### 6.3 转写音频

将已有音频转写为文本：

```bash
meeting transcribe data/recordings/meeting_20260318_140000.wav
```

指定 Whisper 模型：

```bash
meeting transcribe data/recordings/meeting_20260318_140000.wav --model small
```

指定语言，跳过自动检测：

```bash
meeting transcribe data/recordings/meeting_20260318_140000.wav --language zh
```

当前支持的模型：

- `tiny`
- `base`
- `small`
- `medium`
- `large-v3`

转写完成后会生成两个文件：

- `data/transcriptions/<文件名>.json`
- `data/transcriptions/<文件名>.txt`

### 6.4 生成会议纪要

基于 TXT 转写生成纪要：

```bash
meeting summarize data/transcriptions/meeting_20260318_140000.txt
```

基于 JSON 转写生成纪要：

```bash
meeting summarize data/transcriptions/meeting_20260318_140000.json
```

指定 GPT 模型和输出语言：

```bash
meeting summarize data/transcriptions/meeting_20260318_140000.txt \
  --gpt-model gpt-4o-mini \
  --language zh
```

生成结果会保存到：

```text
data/summaries/<转写文件名>_summary.md
```

### 6.5 一站式处理

如果希望直接完成“录音 -> 转写 -> 纪要”：

```bash
meeting process --duration 20
```

指定录音设备：

```bash
meeting process --device 1 --duration 20
```

如果音频已经存在，可跳过录音：

```bash
meeting process --audio-file data/recordings/meeting_20260318_140000.wav
```

同时指定 Whisper 和 GPT 模型：

```bash
meeting process \
  --audio-file data/recordings/meeting_20260318_140000.wav \
  --model medium \
  --gpt-model gpt-4o-mini \
  --language zh
```

注意：

- `meeting process` 会在开始时检查 `OPENAI_API_KEY`
- 即使使用已有音频文件，只要要生成纪要，也必须先配置 OpenAI Key

## 7. 推荐使用流程

### 7.1 最常见流程

1. 配置 `.env` 中的 `OPENAI_API_KEY`
2. 使用 `meeting devices` 确认麦克风索引
3. 执行 `meeting process --duration 30`
4. 在 `data/summaries/` 查看生成的 Markdown 纪要

### 7.2 分步流程

如果希望先确认转写结果，再决定是否生成纪要：

1. `meeting record --duration 30`
2. `meeting transcribe <录音文件>`
3. 检查 `data/transcriptions/*.txt`
4. `meeting summarize <转写文件>`

这种方式更适合：

- 先人工检查转写质量
- 先做内容脱敏，再发送给模型总结
- 多份转写统一批量生成纪要

## 8. 输出结果说明

### 8.1 WAV 录音文件

- 保存原始会议音频
- 便于重复转写或后续归档

### 8.2 JSON 转写文件

适合程序处理，包含：

- 原音频路径
- 识别语言
- 模型名称
- 音频时长
- 分段时间与文本

### 8.3 TXT 转写文件

适合人工查看，示例格式如下：

```text
[00:00] 大家好，我们开始今天的项目周会。
[00:08] 先同步一下当前版本的进度。
```

### 8.4 Markdown 纪要文件

默认会生成结构化内容，例如：

- 会议概要
- 讨论内容
- 决策事项
- 待办事项
- 其他备注

## 9. 常见问题

### 9.1 提示“未检测到音频输入设备”

建议检查：

- 系统是否识别到麦克风
- 当前终端或 Python 进程是否有麦克风权限
- 是否选择了正确的录音设备

可先执行：

```bash
meeting devices
```

### 9.2 提示“未配置 OPENAI_API_KEY”

说明还没有为总结功能配置 OpenAI Key。请确认：

- `.env` 中是否设置了 `OPENAI_API_KEY`
- 环境变量是否生效
- 或者是否写入了 `~/.config/meeting-helper/config.json`

### 9.3 转写速度较慢

当前代码固定使用 CPU 进行 Whisper 推理。影响速度的主要因素包括：

- 音频时长
- 模型大小
- 机器 CPU 性能

如果只追求速度，可尝试更小模型，例如：

```bash
meeting transcribe your_audio.wav --model base
```

### 9.4 生成纪要失败

通常优先检查：

- OpenAI Key 是否正确
- 网络是否能访问配置的接口地址
- `OPENAI_BASE_URL` 是否填写正确
- 转写文本是否为空

### 9.5 长会议能不能直接总结

当前版本没有对超长转写进行分段摘要或上下文裁剪。会议过长时，可能出现：

- 请求耗时明显增加
- 模型上下文不足
- 输出不完整

对于超长会议，建议：

1. 先人工拆分转写文本
2. 分段总结
3. 再合并整理最终纪要

## 10. 注意事项

- 首次使用 Whisper 模型时，可能触发模型下载
- `record` 和 `process` 手动停止时使用 `Ctrl+C`
- 当前录音输出格式固定为 WAV
- 纪要生成结果依赖转写质量，音频越清晰，输出通常越稳定

## 11. 快速命令清单

```bash
# 安装
pip install -e .

# 查看帮助
meeting --help

# 查看麦克风
meeting devices

# 录音 15 分钟
meeting record --duration 15

# 转写音频
meeting transcribe data/recordings/meeting_xxx.wav --model medium --language zh

# 生成纪要
meeting summarize data/transcriptions/meeting_xxx.txt --gpt-model gpt-4o-mini --language zh

# 一站式处理
meeting process --duration 15 --device 1 --model medium --gpt-model gpt-4o-mini --language zh

# 查看配置
meeting config --show
```

## 12. 总结

如果你希望最省事地使用这个工具，优先采用下面的方式：

1. 配置 `.env`
2. 执行 `meeting devices`
3. 执行 `meeting process --duration <分钟数>`

如果你更关注可控性，则建议采用“录音、转写、总结”分步执行的方式。
