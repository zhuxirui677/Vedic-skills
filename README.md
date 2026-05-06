# Vedic Skills

AI agent skill collection for automated video production.
One command → publish-ready `.mp4` + full copy package (title, caption, voiceover, hashtags).

Supports **6 platforms × 4 formats × 2 languages (EN/ZH)**.

---

## Skills

| Skill | Description |
|-------|-------------|
| [video-pipeline](skills/video-pipeline/) | Full AI video factory — TikTok, Instagram, YouTube, Douyin, XHS, Bilibili |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/zhuxirui677/Vedic-skills.git
cd Vedic-skills

# 2. Install Python deps
pip install google-generativeai fal-client openai requests ffmpeg-python

# 3. Install FFmpeg (system)
sudo apt install ffmpeg          # Ubuntu/Debian
brew install ffmpeg              # macOS

# 4. Set API keys (see table below)
export GEMINI_API_KEY="..."
export FAL_KEY="..."
export XAI_API_KEY="..."
export OPENAI_API_KEY="..."

# 5. Run
python skills/video-pipeline/scripts/pipeline.py
```

---

## API Keys — What You Need

### By Platform

| Platform | `platform=` | Language | GEMINI | FAL | XAI | OPENAI |
|----------|------------|----------|:------:|:---:|:---:|:------:|
| TikTok | `"tiktok"` | EN | ✅ | ✅ | ✅ | ✅ |
| Instagram | `"instagram"` | EN | ✅ | ✅ | ✅ | ✅ |
| YouTube | `"youtube"` | EN | ✅ | ✅ | ✅ | ✅ |
| 抖音 Douyin | `"douyin"` | ZH | ✅ | ✅ | ✅ | ✅ |
| 小红书 XHS | `"xiaohongshu"` | ZH | ✅ | ✅ | ✅ | ✅ |
| 哔哩哔哩 Bilibili | `"bilibili"` | ZH | ✅ | ✅ | ✅ | ✅ |

All platforms require all 4 keys. Each key serves a different layer of the pipeline.

### By Video Format

| Format | `aspect_ratio` | `long_video` | Extra condition |
|--------|---------------|-------------|-----------------|
| Short vertical (TikTok/Reels/Douyin) | `"9:16"` | `False` | — |
| Short horizontal (landscape demo) | `"16:9"` | `False` | — |
| Long vertical (long-form portrait) | `"9:16"` | `True` | set `target_duration_s` |
| Long horizontal (YouTube tutorial) | `"16:9"` | `True` | set `target_duration_s` |

Long video also generates `_chapters.txt` with YouTube timestamp markers.

### Key Details

| Key | Used For (Pipeline Layer) | Where to Get | Cost |
|-----|--------------------------|--------------|------|
| `GEMINI_API_KEY` | Layer 1 — shot list generation (Gemini 2.5 Pro) | [aistudio.google.com](https://aistudio.google.com) → Get API Key | **Free** (1500 req/day) |
| `FAL_KEY` | Layer 2 — video clip generation (Seedance 2.0) | [fal.ai](https://fal.ai) → Dashboard → API Keys | ~$0.30–0.50 per clip |
| `XAI_API_KEY` | Layer 0 — live trend search + Layer 3 — copy (Grok 3) | [console.x.ai](https://console.x.ai) | $25 free credit on signup |
| `OPENAI_API_KEY` | Layer 4 — TTS voiceover | [platform.openai.com](https://platform.openai.com) → API Keys | ~$0.01 per video |

### Cost per Run (5-shot short video)

| Item | Cost |
|------|------|
| Gemini (shot list) | Free |
| Grok 3 (trends + copy) | ~$0.05 |
| Seedance 2.0 × 5 clips | ~$1.50–2.50 |
| OpenAI TTS | ~$0.01 |
| **Total** | **~$2** |

For long video (15+ shots), multiply Seedance cost by number of shots.

---

## Usage

### Python API

```python
import sys
sys.path.insert(0, "skills/video-pipeline/scripts")
from pipeline import run_pipeline
```

#### English — TikTok short vertical (9:16)

```python
run_pipeline(
    topic="SPF 50 sunscreen outdoor test, real skin reaction",
    output_path="sunscreen_tiktok.mp4",
    assets={
        "character": "blogger.jpg",        # keeps person consistent
        "product":   "sunscreen.jpg",      # product shots
        "ref_videos": ["outdoor_walk.mp4"], # camera movement reference
    },
    platform="tiktok",
    language="en",
    aspect_ratio="9:16",
    n_shots=5,
    tts_voice="nova",
    concurrent=True,
)
```

#### English — YouTube long horizontal (16:9)

```python
run_pipeline(
    topic="How to set up a home studio for content creators — full guide",
    output_path="studio_youtube.mp4",
    assets={
        "character":  "creator.jpg",
        "ref_videos": ["studio_recording.mov", "gear_broll.mp4"],
        "extra_images": ["gear_list.jpg"],
    },
    platform="youtube",
    language="en",
    aspect_ratio="16:9",
    long_video=True,
    target_duration_s=300,   # ~5 minutes
    tts_voice="onyx",
    concurrent=True,
)
```

#### Chinese — Douyin short vertical (抖音 9:16)

```python
run_pipeline(
    topic="防晒霜户外实测，真实肤感反应",
    output_path="sunscreen_douyin.mp4",
    assets={
        "character": "blogger.jpg",
        "product":   "sunscreen.jpg",
    },
    platform="douyin",
    language="zh",
    aspect_ratio="9:16",
    n_shots=5,
    tts_voice="nova",
    concurrent=True,
)
```

#### Chinese — Bilibili long horizontal (B站 16:9)

```python
run_pipeline(
    topic="家庭影音室从零搭建完整攻略",
    output_path="home_studio_bilibili.mp4",
    assets={
        "ref_videos": ["room_tour.mp4", "gear_demo.mp4"],
    },
    platform="bilibili",
    language="zh",
    aspect_ratio="16:9",
    long_video=True,
    target_duration_s=300,
    tts_voice="onyx",
    concurrent=True,
)
```

---

## All Parameters

| Parameter | Default | Options | Description |
|-----------|---------|---------|-------------|
| `topic` | required | any string | Video subject or product description |
| `output_path` | `"output_final.mp4"` | any `.mp4` path | Output file path |
| `assets` | `{}` | see below | Media assets dict |
| `platform` | `"tiktok"` | `tiktok` `instagram` `youtube` `douyin` `xiaohongshu` `bilibili` `general` | Target platform |
| `language` | `"en"` | `"en"` `"zh"` | Output language — auto-set to `zh` for Chinese platforms |
| `aspect_ratio` | `"9:16"` | `"9:16"` `"16:9"` | Video orientation |
| `long_video` | `False` | `True` `False` | Enable long-form with chapter structure |
| `target_duration_s` | `60` | any int | Target length in seconds (used when `long_video=True`) |
| `n_shots` | auto | any int | Override shot count |
| `tts_voice` | `"nova"` | see below | OpenAI TTS voice |
| `concurrent` | `False` | `True` `False` | Parallel clip generation (~5× faster, recommended for 8+ shots) |

### Assets Dictionary

All values accept local file paths or HTTPS URLs. Local files are auto-uploaded to fal.ai CDN.

```python
assets = {
    "character":    "blogger.jpg",              # keeps person consistent across all shots
    "product":      "product.jpg",              # product reveal / animation shots
    "ref_videos":   ["screen.mp4", "broll.mp4"], # camera movement references (max 3)
    "extra_images": ["mood.jpg", "logo.png"],    # mood boards / backgrounds (max 7)
}
```

### TTS Voice Guide

| Voice | Character | Best for |
|-------|-----------|---------|
| `nova` | Warm female | Beauty, lifestyle, food |
| `shimmer` | Soft female | Skincare, wellness, fashion |
| `onyx` | Deep male | Tech, finance, YouTube tutorials |
| `alloy` | Neutral, clear | General / product demo |
| `echo` | Energetic male | Fitness, gaming |
| `fable` | Expressive | Travel, education, storytelling |

All voices support both English and Chinese.

---

## Output Files

| File | Contents |
|------|----------|
| `output_final.mp4` | Final video — clips merged, voiceover mixed, subtitles burned |
| `output_final_copy.txt` | Title + post caption + per-shot voiceover + trend brief |
| `output_final_chapters.txt` | YouTube/Bilibili timestamp markers (long video only) |
| `subs.srt` | Subtitle file |

---

## Pipeline Architecture

Five AI models work in sequence:

```
User Input (topic, optional assets)
        │
        ▼
[Layer 0] Grok 3 + Live Search
          Scrapes target platform trends in real time
          → trending_hooks, hashtag_clusters, content_matrix
        │
        ▼
[Layer 1] Gemini 2.5 Pro
          Generates structured shot list (JSON)
          → scene descriptions, camera moves, durations, voiceover placeholders
        │
        ▼
[Layer 2] Seedance 2.0 (via fal.ai)
          Generates video clips (concurrent optional)
          Modes: text_to_video | omni_reference | first_last_frames
        │
        ▼
[Layer 3] Grok 3
          Generates platform-optimized copy
          → title, per-shot voiceover, post caption, hashtags
        │
        ▼
[Layer 4] OpenAI TTS + FFmpeg
          TTS → .mp3 per shot
          FFmpeg → merge audio into clips → concat → burn subtitles
        │
        ▼
      output.mp4 + copy package
```

---

## System Requirements

- Python 3.10+
- FFmpeg installed (`ffmpeg` in PATH)
- For Chinese subtitles: `Noto Sans CJK SC` font
  ```bash
  sudo apt install fonts-noto-cjk   # Ubuntu/Debian
  brew install --cask font-noto-sans-cjk  # macOS
  ```

---

## Repo Structure

```
Vedic-skills/
├── README.md
└── skills/
    ├── video-pipeline.skill           ← distributable .skill package (zip)
    └── video-pipeline/
        ├── SKILL.md                   ← system prompt for AI agents
        └── scripts/
            └── pipeline.py            ← full implementation
```
