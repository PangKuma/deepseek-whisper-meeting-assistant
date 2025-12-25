# Decision Keeper

> 基于本地 Whisper 和 DeepSeek 的智能会议决策助理

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![MLX Whisper](https://img.shields.io/badge/Whisper-MLX%20Local-green.svg)
![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 🌟 项目简介

Decision Keeper 是一个**本地优先**的 Python 命令行工具，专为解决会议记录繁琐、核心决策容易遗漏的痛点而设计。

### 核心价值

- **🔒 隐私安全**：录音转文字完全在本地运行（基于 Apple MLX 框架），数据不上传云端
- **🎯 决策导向**：利用 DeepSeek 大模型精准提取"核心决议"和"待办事项"，而非泛泛而谈的摘要
- **⚡ 简单易用**：将音视频文件放入文件夹，运行脚本，自动输出结构化 Markdown 纪要

---

## ✨ 核心功能

- **本地转录**：使用 `mlx_whisper` 在 Mac（Apple Silicon）上实现极速语音识别，支持中英文混合
- **结构化输出**：自动生成包含"一句话摘要"、"关键议题"、"P0级决议"、"待办清单"的标准 Markdown 文档
- **多格式支持**：支持 `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.mp4`, `.mov`, `.mkv`, `.webm` 等常见音视频格式
- **智能清洗**：自动去除文件名中的特殊字符（冒号、斜杠、空格等），生成规范的文档命名
- **增量处理**：自动跳过已处理的文件，避免重复计算

---

## 🏗️ 工作原理

```mermaid
flowchart LR
    A[video_input/<br/>音视频文件统一入口] --> B[main.py<br/>文件扫描与去重]
    B --> C[FFmpeg 预处理<br/>压缩并标准化为 MP3]
    C --> D[audio_input/<br/>临时 MP3 文件]
    D --> E[transcribe_mlx.py<br/>本地 Whisper 转录]
    E --> F[text_output/<br/>带时间戳的逐字稿]
    F --> G[summarize.py<br/>DeepSeek API 结构化分析]
    G --> H[summary_output/<br/>最终会议纪要 .md]
```

---

## 🚀 快速开始

### 环境要求

- **操作系统**：macOS（推荐 M1/M2/M3 系列芯片以获得最佳 Whisper 性能）
- **Python**：3.10 或更高版本
- **FFmpeg**：用于音视频预处理（[安装指南](https://ffmpeg.org/download.html)）

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/your-username/decision-keeper.git
cd decision-keeper
```

2. **创建虚拟环境并安装依赖**

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装核心依赖
pip install mlx-whisper openai python-dotenv
```

3. **配置 DeepSeek API Key**

创建 `.env` 文件（可参考 `.env.example`）：

```bash
DEEPSEEK_API_KEY=sk-your_api_key_here
SUMMARY_FOLDER=./summary_output
```

> 💡 如何获取 DeepSeek API Key：访问 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册并创建 API Key

### 运行方法

1. **准备会议录音**

将音视频文件统一放入 `./video_input/` 文件夹：
- 支持格式：`.mp4`, `.mov`, `.mkv`, `.webm`, `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`
- 系统会自动使用 FFmpeg 将所有文件压缩并标准化为 MP3 格式

2. **执行主程序**

```bash
# 确保在虚拟环境中
source .venv/bin/activate

# 运行
python main.py
```

3. **查看结果**

生成的 Markdown 纪要位于：
- 默认：`./summary_output/`
- 自定义：`.env` 中 `SUMMARY_FOLDER` 指定的路径

---

## 📂 项目结构

```
decision-keeper/
├── main.py              # 主程序：文件扫描、去重、任务调度
├── transcribe_mlx.py    # 本地 Whisper 转录模块
├── summarize.py         # DeepSeek API 结构化总结模块
├── meeting_input/       # 会议输入目录（入口）
├── video_input/         # 音视频文件清洗（自动清理）
├── audio_input/         # FFmpeg 处理后的标准化 MP3（自动清理）
├── text_output/         # 临时转录文本（自动清理）
├── summary_output/      # 最终 Markdown 纪要输出目录
├── models/              # Whisper 本地模型存放目录
├── .env                 # 环境变量配置文件（需自行创建）
└── requirements.txt     # Python 依赖列表
```

### 核心文件说明

| 文件 | 作用 |
|------|------|
| `main.py` | 调度中心：扫描 video_input，使用 FFmpeg 标准化音频，调用转录与总结模块，处理完成后自动清理临时文件 |
| `transcribe_mlx.py` | 调用本地 Whisper 模型（4-bit 量化），输出带时间戳的中文逐字稿 |
| `summarize.py` | 通过 DeepSeek API 提取"一句话摘要"、"核心决议"、"待办清单"等结构化信息 |

---

## ⚙️ 配置说明

### `.env` 文件详解

```bash
# 必填：DeepSeek API 密钥
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx

# 可选：自定义输出路径（默认为 ./summary_output）
SUMMARY_FOLDER=/path/to/your/obsidian/vault

# 可选：自定义 Whisper 模型路径（需修改 transcribe_mlx.py 中的 MODEL_PATH 变量）
```

### Whisper 模型配置

默认使用 4-bit 量化模型（位于 `./models/turbo-4bit`），如需更换模型：

编辑 `transcribe_mlx.py` 第 8 行：

```python
MODEL_PATH = "./models/your-model-name"
```

> 💡 推荐模型：`large-v3-turbo`（平衡速度与精度），详见 [mlx-whisper 文档](https://github.com/ml-explore/mlx-whisper)

---

## 📋 输出格式示例

生成的 Markdown 纪要包含以下结构：

```markdown
# 会议纪要：{自动生成的标题}

## 📌 一句话摘要
{50 字以内的核心目的摘要}

## 👥 关键议题与讨论
- 议题一：核心观点/冲突点
- 议题二：...

## ✅ 决议与待办 (TODO)

**🚀 核心决议：**
- [P0] {重要决议内容}
- [P1] {次要决议内容}

**📝 待办清单：**
- [ ] @张三：完成调研报告 [本周五]
- [ ] @李四：准备演示文稿 [下周三]

## 💡 详细内容记录
{按时间或逻辑顺序的详细会议内容}
```

---

## 🔒 隐私与安全

- **本地转录**：Whisper 运行在你的 Mac 上，录音数据不会离设备
- **API 最小化**：仅将文本摘要发送至 DeepSeek API（不包含原始音频）
- **自动清理**：中间文件（`.txt` 逐字稿）处理完成后自动删除

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 🙏 致谢

- [mlx-whisper](https://github.com/ml-explore/mlx-whisper) — Apple Silicon 上的本地 Whisper 实现
- [DeepSeek](https://www.deepseek.com/) — 强大的开源大语言模型
- [OpenAI Python SDK](https://github.com/openai/openai-python) — API 客户端库

---

<div align="center">

**让决策不被遗忘，让会议更有效率** ⚡️

Made with ❤️ by Decision Keeper Team

</div>
