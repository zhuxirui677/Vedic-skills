# Vedic Skills — AI 视频生产工厂

给定一个主题，全自动生成发布级视频 + 完整文案包。

支持 **6 个平台 × 4 种格式 × 中英双语**，一行代码跑完整条流水线。

---

## 包含 Skill

| Skill | 说明 |
|-------|------|
| [video-pipeline](skills/video-pipeline/) | 全自动 AI 视频工厂 — 抖音 / 小红书 / B站 / TikTok / Instagram / YouTube |

---

## 快速开始

### 第一步：克隆项目

```bash
git clone https://github.com/zhuxirui677/Vedic-skills.git
cd Vedic-skills
```

### 第二步：安装依赖

```bash
pip install -r requirements.txt
```

还需要安装系统级 FFmpeg：

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

中文字幕需要 CJK 字体（英文视频可跳过）：

```bash
# Ubuntu / Debian
sudo apt install fonts-noto-cjk

# macOS
brew install --cask font-noto-sans-cjk
```

### 第三步：配置 API Key

```bash
export GEMINI_API_KEY="..."    # Gemini 2.5 Pro — 分镜生成
export FAL_KEY="..."           # Seedance 2.0 — 视频片段生成
export XAI_API_KEY="..."       # Grok 3 — 趋势搜索 + 文案
export OPENAI_API_KEY="..."    # OpenAI TTS — 旁白配音
```

### 第四步：运行示例

```bash
python example.py
```

或直接在代码里调用：

```python
import sys
sys.path.insert(0, "skills/video-pipeline/scripts")
from pipeline import run_pipeline

run_pipeline(
    topic="防晒霜户外实测，真实肤感反应",
    platform="douyin",
    language="zh",
)
```

---

## 需要哪些 API Key

### 去哪里获取

| Key | 用途 | 获取地址 | 费用 |
|-----|------|---------|------|
| `GEMINI_API_KEY` | 第1层：分镜脚本生成（Gemini 2.5 Pro） | [aistudio.google.com](https://aistudio.google.com) → Get API Key | **免费**（每天 1500 次） |
| `FAL_KEY` | 第2层：视频片段生成（Seedance 2.0） | [fal.ai](https://fal.ai) → Dashboard → API Keys | 每个片段约 $0.30–0.50 |
| `XAI_API_KEY` | 第0层趋势搜索 + 第3层文案（Grok 3） | [console.x.ai](https://console.x.ai) | 注册送 $25 免费额度 |
| `OPENAI_API_KEY` | 第4层：旁白配音（TTS） | [platform.openai.com](https://platform.openai.com) → API Keys | 每个视频约 $0.01 |

### 每次运行费用（5个镜头短视频）

| 服务 | 费用 |
|------|------|
| Gemini（分镜） | 免费 |
| Grok 3（趋势 + 文案） | ~$0.05 |
| Seedance 2.0 × 5个片段 | ~$1.50–2.50 |
| OpenAI TTS（配音） | ~$0.01 |
| **合计** | **约 $2** |

长视频（15+ 个镜头）按镜头数等比增加 Seedance 费用。

### 不同平台需要的条件

| 平台 | `platform=` | 语言 | 视频比例 | 备注 |
|------|------------|------|---------|------|
| 抖音 | `"douyin"` | 中文（自动） | 9:16 | — |
| 小红书 | `"xiaohongshu"` | 中文（自动） | 9:16 | — |
| 哔哩哔哩 | `"bilibili"` | 中文（自动） | 16:9 | 长视频需设 `long_video=True` |
| TikTok | `"tiktok"` | 英文 | 9:16 | — |
| Instagram | `"instagram"` | 英文 | 9:16 | — |
| YouTube | `"youtube"` | 英文 | 16:9 | 长视频需设 `long_video=True` |

### 不同视频格式需要的条件

| 格式 | `aspect_ratio` | `long_video` | 额外条件 |
|------|---------------|-------------|---------|
| 短视频竖屏（抖音/TikTok/小红书） | `"9:16"` | `False` | — |
| 短视频横屏（产品展示） | `"16:9"` | `False` | — |
| 长视频竖屏 | `"9:16"` | `True` | 设置 `target_duration_s`（秒） |
| 长视频横屏（B站/YouTube教程） | `"16:9"` | `True` | 设置 `target_duration_s`（秒） |

---

## 使用示例

### 抖音短视频（中文，9:16）

```python
run_pipeline(
    topic="防晒霜户外实测，真实肤感反应",
    output_path="output_douyin.mp4",
    assets={
        "character": "blogger.jpg",    # 博主照片（保持人物一致）
        "product":   "sunscreen.jpg",  # 产品图
        "ref_videos": ["outdoor.mp4"], # 参考视频（仿拍运镜）
    },
    platform="douyin",
    language="zh",
    aspect_ratio="9:16",
    n_shots=5,
    tts_voice="nova",
    concurrent=True,
)
```

### 小红书种草（中文，9:16）

```python
run_pipeline(
    topic="护肤早C晚A入门，敏感肌也能用",
    output_path="output_xhs.mp4",
    platform="xiaohongshu",
    language="zh",
    aspect_ratio="9:16",
    tts_voice="shimmer",
)
```

### B站长视频教程（中文，16:9，含章节）

```python
run_pipeline(
    topic="家庭影音室从零搭建完整攻略",
    output_path="output_bilibili.mp4",
    platform="bilibili",
    language="zh",
    aspect_ratio="16:9",
    long_video=True,
    target_duration_s=300,   # 目标5分钟
    tts_voice="onyx",
    concurrent=True,
)
```

### TikTok 短视频（英文，9:16）

```python
run_pipeline(
    topic="SPF 50 sunscreen outdoor test, real skin reaction",
    output_path="output_tiktok.mp4",
    platform="tiktok",
    language="en",
    aspect_ratio="9:16",
    n_shots=5,
    tts_voice="nova",
    concurrent=True,
)
```

### YouTube 长教程（英文，16:9）

```python
run_pipeline(
    topic="How to set up a home studio for content creators",
    output_path="output_youtube.mp4",
    platform="youtube",
    language="en",
    aspect_ratio="16:9",
    long_video=True,
    target_duration_s=300,
    tts_voice="onyx",
    concurrent=True,
)
```

---

## 全部参数说明

| 参数 | 默认值 | 可选值 | 说明 |
|------|--------|--------|------|
| `topic` | 必填 | 任意字符串 | 视频主题或产品描述 |
| `output_path` | `"output_final.mp4"` | 任意 `.mp4` 路径 | 输出文件路径 |
| `assets` | `{}` | 见下方 | 媒体素材字典 |
| `platform` | `"tiktok"` | `douyin` `xiaohongshu` `bilibili` `tiktok` `instagram` `youtube` `general` | 目标平台 |
| `language` | `"en"` | `"zh"` `"en"` | 输出语言；指定中文平台时自动切换为 zh |
| `aspect_ratio` | `"9:16"` | `"9:16"` `"16:9"` | 视频比例（竖屏/横屏） |
| `long_video` | `False` | `True` `False` | 是否为长视频（含章节结构） |
| `target_duration_s` | `60` | 任意整数 | 目标时长（秒），`long_video=True` 时生效 |
| `n_shots` | 自动计算 | 任意整数 | 手动指定镜头数 |
| `tts_voice` | `"nova"` | 见下方 | OpenAI TTS 声音 |
| `concurrent` | `False` | `True` `False` | 并发生成片段（快约5倍，10个镜头以上推荐开启） |

### 素材字典 `assets`

本地路径或 HTTPS URL 均可，本地文件自动上传到 fal.ai CDN。

```python
assets = {
    "character":    "blogger.jpg",               # 保持人物一致（每个镜头注入）
    "product":      "product.jpg",               # 产品展示 / 动画镜头
    "ref_videos":   ["screen.mp4", "broll.mp4"], # 参考视频，仿拍运镜（最多3个）
    "extra_images": ["mood.jpg", "logo.png"],    # 背景 / 道具 / 风格参考（最多7个）
}
```

### TTS 声音选择

| 声音 | 风格 | 适合场景 |
|------|------|---------|
| `nova` | 温柔女声 | 美妆、生活方式、美食 |
| `shimmer` | 柔和女声 | 护肤、时尚、wellness |
| `onyx` | 低沉男声 | 科技、财经、B站教程 |
| `alloy` | 中性清晰 | 通用 / 产品Demo |
| `echo` | 活力男声 | 健身、游戏 |
| `fable` | 富有表现力 | 旅行、教育、故事 |

所有声音均原生支持中文和英文。

---

## 输出文件

| 文件 | 内容 |
|------|------|
| `output_final.mp4` | 最终视频（含旁白配音 + 字幕） |
| `output_final_copy.txt` | 标题 + 发帖文案 + 逐镜头旁白 + 趋势数据 |
| `output_final_chapters.txt` | 章节时间戳（仅长视频，适用于B站/YouTube） |
| `subs.srt` | 字幕文件（可复用） |

---

## 流水线架构

5层 AI 模型依次工作：

```
输入：主题 + 可选素材（产品图/博主照片/录屏素材）
        │
        ▼
[第 0 层] Grok 3 实时搜索
          实时抓取目标平台趋势数据
          输出：热门钩子 / 话题标签 / 内容矩阵 / CTA话术
        │
        ▼
[第 1 层] Gemini 2.5 Pro
          生成结构化分镜脚本（JSON）
          每个镜头：场景描述 / 运镜方式 / 时长 / 旁白占位
        │
        ▼
[第 2 层] Seedance 2.0（via fal.ai）
          生成视频片段（支持并发）
          三种模式：纯AI生成 / 角色一致性 / 产品动画
        │
        ▼
[第 3 层] Grok 3 文案生成
          输出：标题 / 逐镜头旁白 / 发帖文案 / 话题标签
        │
        ▼
[第 4 层] OpenAI TTS + FFmpeg
          TTS生成每个镜头配音 → 合并到片段 → 拼接 → 烧字幕
        │
        ▼
      output.mp4 + 文案包
```

---

## 项目结构

```
Vedic-skills/
├── README.md               ← 本文件
├── requirements.txt        ← Python 依赖
├── example.py              ← 快速示例脚本
└── skills/
    ├── video-pipeline.skill       ← 可分发的 .skill 包（zip）
    └── video-pipeline/
        ├── SKILL.md               ← AI agent 系统提示词
        └── scripts/
            └── pipeline.py        ← 完整实现
```

---

## 系统要求

- Python 3.10+
- FFmpeg（系统级安装）
- 中文字幕需要 Noto Sans CJK SC 字体
