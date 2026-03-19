# MeetingHelper 技术说明

## 1. 项目定位

MeetingHelper 是一个本地命令行工具，用于完成会议音频的录制、语音转写和会议纪要生成。项目当前以单包 Python CLI 的形式实现，核心目标是提供一条从麦克风到 Markdown 纪要的最短处理链路。

当前能力范围：

- 列出本机可用音频输入设备
- 录制麦克风音频并保存为 WAV 文件
- 使用 `faster-whisper` 对音频进行离线转写
- 可选使用 `pyannote.audio` 做发言人区分
- 使用可插拔的摘要 provider 根据转写文本生成结构化会议纪要
- 通过单条命令串联“录音 -> 转写 -> 总结”流程

## 2. 目录结构

项目目录较小，核心代码集中在 `src/meeting_helper`：

```text
MeetingHelper/
├── .env.example                 # 环境变量示例
├── data/
│   ├── recordings/              # 录音输出目录
│   ├── transcriptions/          # 转写输出目录
│   └── summaries/               # 纪要输出目录
├── docs/
│   ├── technical-guide.md       # 技术说明
│   ├── user-guide.md            # 使用文档
│   └── whisper-speaker-diarization-plan.md
├── pyproject.toml               # 打包配置与依赖声明
└── src/
    └── meeting_helper/
        ├── __init__.py
        ├── cli.py               # Typer CLI 入口
        ├── config.py            # 配置加载与持久化
        ├── diarizer.py          # 发言人区分
        ├── models.py            # 数据模型
        ├── recorder.py          # 麦克风录音
        ├── summarizer.py        # 纪要生成入口
        ├── summary_providers/   # OpenAI / Qwen 摘要 provider
        ├── transcriber.py       # Whisper 转写
        └── utils.py             # 文件与格式化工具
```

## 3. 技术栈

### 3.1 运行时与分发

- Python `>=3.10`
- `setuptools` + `pyproject.toml`
- 命令入口：`meeting = meeting_helper.cli:app`

### 3.2 主要依赖

- `typer`：命令行框架
- `rich`：终端表格、状态提示和面板输出
- `sounddevice`：音频输入设备查询与实时录音
- `scipy`：将采集数据写入 WAV
- `numpy`：音频帧拼接
- `faster-whisper`：本地语音转写
- `pyannote.audio`：说话人区分
- `openai`：调用 GPT 生成会议纪要
- `python-dotenv`：加载项目根目录 `.env`

## 4. 架构概览

当前实现采用简单的分层方式：

- `cli.py`
  - 负责参数解析、交互输出、流程编排和错误退出。
- `config.py`
  - 负责默认配置、环境变量读取、用户配置文件读写和目录初始化。
- `recorder.py`
  - 负责音频输入设备枚举与录音。
- `transcriber.py`
  - 负责 Whisper 模型加载和音频转写。
- `diarizer.py`
  - 负责说话人区分与 speaker 标签回填。
- `summarizer.py`
  - 负责接收请求并分发到具体摘要 provider。
- `summary_providers/*`
  - 负责 OpenAI / Qwen 等具体模型源的适配。
- `utils.py`
  - 负责文件名生成、时间格式化、转写结果保存和纪要保存。
- `models.py`
  - 定义 `Recording`、`Segment`、`Transcription`、`Summary` 等数据结构。

这套结构的特点是：

- 模块边界清晰，便于快速理解
- CLI 直接编排业务流程，适合小型工具
- 业务逻辑尚未抽象成 service 层，因此扩展复杂流程时会逐步受限

## 5. 核心执行链路

### 5.1 录音链路

`meeting record` 的主要路径如下：

1. CLI 从配置中读取录音目录、采样率和声道数。
2. 使用时间戳生成输出文件名，如 `meeting_20260318_140000.wav`。
3. 注册 `SIGINT` 处理逻辑，以便 `Ctrl+C` 触发停止事件。
4. `recorder.record_audio()` 打开 `sounddevice.InputStream`。
5. 在回调中持续收集音频帧。
6. 结束后将帧拼接为 `numpy.ndarray`，再由 `scipy.io.wavfile.write()` 写为 WAV。

实现特点：

- 默认采样率 `16000`
- 默认单声道
- 数据类型固定为 `int16`
- 未录到任何帧时抛出 `RuntimeError`

### 5.2 转写链路

`meeting transcribe` 和 `meeting process` 中的转写逻辑一致：

1. CLI 校验 Whisper 模型名是否合法。
2. `transcriber.transcribe_audio()` 初始化 `WhisperModel`。
3. 调用 `model.transcribe()` 并启用 `vad_filter=True`。
4. 将返回片段转换为内部 `Segment` 数据结构。
5. 若开启 `--diarize`，调用 `diarizer.assign_speakers()` 对齐 speaker 标签。
6. `utils.save_transcription()` 同时输出 JSON 和 TXT。

当前转写实现的固定参数：

- 推理设备：`cpu`
- 量化类型：`int8`
- VAD 静音阈值：`500ms`
- speaker 对齐规则：按 segment 与 diarization turn 的最大重叠时长匹配

转写输出文件：

- `data/transcriptions/<stem>.json`
- `data/transcriptions/<stem>.txt`

其中：

- JSON 保存完整元数据和分段结果
- TXT 保存带 `[MM:SS]` 时间戳的纯文本
- 启用 diarization 时，JSON/TXT 都会包含发言人标签

### 5.3 纪要生成链路

`meeting summarize` 和 `meeting process` 中的总结逻辑一致：

1. CLI 加载配置并解析当前启用的摘要 provider。
2. `utils.load_transcription_text()` 读取 TXT 或 JSON 转写内容。
3. `summarizer.generate_summary()` 通过工厂创建 provider。
4. provider 根据语言选择提示词，并通过 OpenAI 兼容 Chat Completions 接口生成 Markdown 格式纪要。
5. `utils.save_summary()` 将结果写入 `data/summaries/<stem>_summary.md`。

当前已实现的摘要 provider：

- `openai`
- `qwen`

其中 `qwen` 根据文档使用 OpenAI 兼容接口，默认 `base_url` 为 `https://dashscope.aliyuncs.com/compatible-mode/v1`。

系统提示词当前固定为两套模板：

- 中文模板：输出“会议概要、讨论内容、决策事项、待办事项、其他备注”
- 英文模板：输出对应英文结构

## 6. 命令设计

当前 CLI 一共提供 6 个命令：

- `meeting devices`
- `meeting record`
- `meeting transcribe`
- `meeting summarize`
- `meeting process`
- `meeting config`

设计上分为两类：

- 原子命令：分别处理设备查看、录音、转写、总结、配置
- 聚合命令：`process` 负责串联完整流程

`process` 的调用顺序是固定的：

1. 使用现有音频或先录音
2. 转写音频
3. 基于转写生成纪要

## 7. 配置机制

### 7.1 配置来源

配置优先级由高到低为：

1. CLI 参数
2. 环境变量与项目根目录 `.env`
3. 用户配置文件 `~/.config/meeting-helper/config.json`
4. 代码内默认值

### 7.2 可用配置项

`AppConfig` 当前字段如下：

- `summary_provider`
- `openai_api_key`
- `openai_base_url`
- `openai_model`
- `qwen_api_key`
- `qwen_base_url`
- `qwen_model`
- `whisper_model`
- `huggingface_token`
- `language`
- `sample_rate`
- `channels`
- `recordings_dir`
- `transcriptions_dir`
- `summaries_dir`

### 7.3 环境变量映射

- `SUMMARY_PROVIDER` -> `summary_provider`
- `OPENAI_API_KEY` -> `openai_api_key`
- `OPENAI_BASE_URL` -> `openai_base_url`
- `OPENAI_MODEL` -> `openai_model`
- `QWEN_API_KEY` -> `qwen_api_key`
- `QWEN_BASE_URL` -> `qwen_base_url`
- `QWEN_MODEL` -> `qwen_model`
- `HUGGINGFACE_TOKEN` -> `huggingface_token`
- `WHISPER_MODEL` -> `whisper_model`
- `GPT_MODEL` -> `openai_model`（兼容旧配置）
- `DASHSCOPE_API_KEY` -> `qwen_api_key`（兼容阿里云默认环境变量）
- `MEETING_LANGUAGE` -> `language`

### 7.4 目录初始化

每次执行 `load_config()` 时，都会调用 `ensure_dirs()` 自动创建：

- `data/recordings`
- `data/transcriptions`
- `data/summaries`

这意味着即使首次运行，只要配置加载成功，输出目录会自动补齐。

## 8. 数据模型与文件产物

### 8.1 内存数据模型

`models.py` 中定义了以下对象：

- `Recording`
  - 描述录音文件与采样参数
- `Segment`
  - 描述单个转写片段，支持可选 `speaker`
- `Transcription`
  - 聚合音频文件、片段、语言、模型和时长
  - 可标记是否开启发言人区分以及识别到的说话人数
  - 暴露 `full_text` 属性，用于拼接整段文本
- `Summary`
  - 描述纪要内容与关联转写文件

其中 `Recording` 和 `Summary` 当前主要起建模作用，实际命令流程中并未完整串接为统一领域对象。

### 8.2 文件输出约定

录音输出：

- `data/recordings/meeting_<timestamp>.wav`

转写输出：

- `data/transcriptions/<audio_stem>.json`
- `data/transcriptions/<audio_stem>.txt`

纪要输出：

- `data/summaries/<input_stem>_summary.md`

## 9. 错误处理与交互方式

### 9.1 CLI 交互

项目使用 `rich` 进行输出增强：

- 表格：展示设备列表与配置项
- 状态栏：显示转写和总结的处理中状态
- 面板：展示最终生成的会议纪要

### 9.2 错误处理特点

当前错误处理以“命令级退出”为主：

- 参数非法时直接 `typer.Exit(1)`
- 录音失败时打印错误并退出
- 缺少当前摘要 provider 的 API Key 时退出
- 输入文件为空时退出

尚未覆盖的方面：

- OpenAI / Qwen API 异常的细分处理
- Whisper 模型下载或加载失败的恢复逻辑
- pyannote 模型权限、token 或 `ffmpeg` 缺失时的自动诊断
- 不同平台音频设备兼容性诊断
- 输出文件写入失败时的更明确提示

## 10. 当前实现限制

从当前代码看，项目已经能完成基础闭环，但仍存在一些明显边界：

- 转写设备固定为 CPU，未暴露 GPU 配置项
- 发言人区分依赖 `pyannote.audio`、`ffmpeg` 和 Hugging Face token
- speaker 归属目前基于 segment 级重叠匹配，仍有边界误差
- 长文本总结没有分段、截断或重试机制，超长会议可能直接受模型上下文限制
- `process` 命令目前仍默认包含纪要生成步骤，因此会要求当前摘要 provider 的 Key
- `config --set` 以字符串方式写入，数值型配置缺少类型校验
- 录音文件格式固定为 WAV，未提供压缩格式输出
- `Recording`、`Summary` 模型尚未用于统一持久化
- 没有自动化测试与持续集成配置
- `src/meeting_helper/__pycache__` 和 `src/meeting_helper.egg-info` 当前位于源码树中，属于构建产物，后续应避免纳入版本管理

## 11. 可扩展方向

如果后续继续演进，优先级较高的方向通常是：

- 增加 service 层，降低 CLI 与底层实现的耦合
- 为转写和总结增加更强的异常处理与重试策略
- 支持超长转写文本分片总结与结果合并
- 提供更多输出模板，如周会、评审会、一对一沟通
- 为录音、转写、配置模块补充自动化测试
- 增加平台诊断命令，如检查麦克风、依赖和模型缓存状态

## 12. 结论

MeetingHelper 当前是一个实现直接、职责清楚的 Python CLI 工具。它适合个人或小团队在本地快速完成“会议录音 -> 语音转写 -> 纪要生成”的闭环。代码量不大，理解成本低，适合作为轻量工具直接使用，也适合作为后续扩展的基础版本。

补充说明：Whisper 发言人区分能力已完成实现，并已通过一次本地端到端验证。验证命令为 `meeting transcribe data/recordings/meeting_20260318_152652.wav --model base --language zh --diarize`，结果成功生成带 `speaker` 标签的 JSON 和 TXT 转写文件。
