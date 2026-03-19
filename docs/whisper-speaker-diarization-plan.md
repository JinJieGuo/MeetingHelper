# Whisper 发言人区分改造方案

## 1. 背景

当前 MeetingHelper 的转写链路只负责语音转文字，不区分发言人。`faster-whisper` 能提供分段时间戳，但不直接提供 speaker diarization 能力，因此需要在 Whisper 转写后补一层说话人区分。

本次改造目标是：

- 保持现有 Whisper 转写能力不变
- 新增可选的发言人区分能力
- 在转写 JSON、TXT 和后续纪要生成中保留说话人标签

本次改造不包含：

- 具体人名识别
- 声纹注册与声纹比对
- 远端 ASR 或 Qwen 接入

## 2. 技术方案

采用两阶段链路：

1. `faster-whisper` 负责语音转文字
2. `pyannote.audio` 负责 speaker diarization

整条链路为：

```text
音频文件
  -> faster-whisper
  -> Whisper segments(start/end/text)
  -> pyannote.audio
  -> speaker turns(start/end/speaker)
  -> overlap 对齐
  -> 带 speaker 的转写结果
```

## 3. 输出效果

### 3.1 TXT

默认转写：

```text
[00:03] 这个需求下周上线。
[00:08] 我这边会补测试。
```

开启发言人区分后：

```text
[00:03] [SPEAKER_00] 这个需求下周上线。
[00:08] [SPEAKER_01] 我这边会补测试。
```

### 3.2 JSON

每个 segment 新增 `speaker` 字段，顶层新增：

- `diarized`
- `speaker_count`

示例：

```json
{
  "diarized": true,
  "speaker_count": 2,
  "segments": [
    {
      "start": 3.2,
      "end": 7.8,
      "speaker": "SPEAKER_00",
      "text": "这个需求下周上线。"
    }
  ]
}
```

## 4. 配置与参数

### 4.1 环境变量

- `HUGGINGFACE_TOKEN`
  - 启用发言人区分时必需
  - 用于加载 `pyannote/speaker-diarization-community-1`

### 4.2 CLI 参数

给 `meeting transcribe` 和 `meeting process` 新增：

- `--diarize`
- `--min-speakers`
- `--max-speakers`

说明：

- 不传 `--diarize` 时，行为与当前版本保持一致
- 传入 `--diarize` 时，若未配置 `HUGGINGFACE_TOKEN`，命令直接退出

## 5. 数据结构改动

### 5.1 Segment

新增：

- `speaker: str | None`

### 5.2 Transcription

新增：

- `diarized: bool`
- `speaker_count: int | None`

## 6. 代码改动点

### 6.1 新增模块

- `src/meeting_helper/diarizer.py`
  - 负责加载 `pyannote.audio`
  - 负责执行 diarization
  - 负责把 speaker turn 对齐到 Whisper segment

### 6.2 修改模块

- `src/meeting_helper/transcriber.py`
  - 新增 `diarize/hf_token/min_speakers/max_speakers` 参数
  - 在 Whisper 转写后调用 `diarizer.assign_speakers`

- `src/meeting_helper/models.py`
  - 扩展 `Segment` 和 `Transcription`

- `src/meeting_helper/utils.py`
  - JSON/TXT 输出增加 speaker 信息
  - 从 JSON 读取时保留 speaker 前缀

- `src/meeting_helper/cli.py`
  - 新增 diarization CLI 参数
  - 补充参数校验和缺失 token 的报错

- `src/meeting_helper/config.py`
  - 新增 `huggingface_token`
  - 增加 `HUGGINGFACE_TOKEN` 环境变量映射

## 7. 对齐策略

先采用简单稳定的 segment 级对齐规则：

1. 取得 Whisper segment 的起止时间
2. 取得 diarization speaker turn 的起止时间
3. 计算每个 turn 与 segment 的重叠时长
4. 选择重叠时长最大的 speaker 作为 segment 的 speaker

未匹配到任何说话人时，标记为 `UNKNOWN`。

## 8. 使用前提

- 需要安装 `pyannote.audio`
- 本机需要可用的 `ffmpeg`
- 需要 Hugging Face token
- 需要先接受 `pyannote/speaker-diarization-community-1` 模型使用条款

## 9. 已知边界

- 当前只做“区分不同发言人”，不做“识别具体是谁”
- 重叠说话和抢话场景下，speaker 归属仍可能有误差
- 当前仍按 Whisper segment 对齐，不是词级对齐，边界精度有限
- CPU 环境下启用 diarization 后速度会明显下降

## 10. 后续可演进方向

- 接入词级时间戳，提升 speaker 归属精度
- 支持说话人重命名，例如把 `SPEAKER_00` 映射为“主持人”
- 支持把 speaker 信息注入纪要模板，生成“发言人视角”的纪要
- 未来如有需要，再评估接入 WhisperX 或声纹识别能力

## 11. 实现与验证状态

当前版本已完成以下落地：

- `faster-whisper + pyannote.audio` 双阶段链路接入
- `--diarize`、`--min-speakers`、`--max-speakers` CLI 参数
- `HUGGINGFACE_TOKEN` 配置项与环境变量映射
- 转写 JSON/TXT 中的 `speaker`、`diarized`、`speaker_count`
- `process` 流程中将带 speaker 的转写文本传递给纪要生成链路
- Hugging Face gated model 未授权时的可读错误提示

本地验证结果：

- 测试音频：`data/recordings/meeting_20260318_152652.wav`
- 测试命令：`./.venv/bin/meeting transcribe data/recordings/meeting_20260318_152652.wav --model base --language zh --diarize`
- 运行结果：命令成功，生成带 `SPEAKER_00` 标签的 JSON 和 TXT 转写文件
- 本次样本识别出 `1` 个说话人，`speaker_count=1`

验证结论：

- “Whisper 转写 -> 发言人区分 -> 转写文件落盘”链路已跑通
- 当前功能已经可以用于单说话人或少量说话人的会议音频基础区分
