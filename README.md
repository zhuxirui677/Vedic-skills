# Vedic Skills

A collection of AI agent skills for automated content production. Each skill is a self-contained `.skill` package (zip archive) that includes a system prompt, implementation scripts, and sample assets.

---

## Skills

| Skill | File | Description |
|-------|------|-------------|
| [video-pipeline](skills/video-pipeline/) | `video-pipeline.skill` | AI short & long video factory — TikTok, Instagram, YouTube |

---

## How to Use a `.skill` File

A `.skill` file is a renamed `.zip` archive. Unzip it to get the `SKILL.md` (system prompt) and `scripts/` folder.

```bash
# Unzip
cp skills/video-pipeline.skill video-pipeline.zip
unzip video-pipeline.zip

# Install dependencies
pip install google-generativeai fal-client openai requests ffmpeg-python

# Set API keys
export GEMINI_API_KEY="your_key"
export FAL_KEY="your_key"
export XAI_API_KEY="your_key"
export OPENAI_API_KEY="your_key"

# Run
python video-pipeline/scripts/pipeline.py
```

---

# video-pipeline Skill

> **Version:** 1.0 · **Target audience:** English-speaking (TikTok, Instagram, YouTube)

## What It Does

Give it a topic, an optional product photo, and optional screen recordings — it outputs a publish-ready `.mp4` video plus a full English copy package (title, post caption, voiceover, hashtags).

**One command. Four outputs:**

| Output file | Contents |
|-------------|---------|
| `output.mp4` | Final video — clips merged, subtitles burned, TTS audio merged |
| `output_copy.txt` | Title + post caption + per-shot voiceover + trend brief |
| `output_chapters.txt` | YouTube timestamp markers (long video only) |
| `subs.srt` | Subtitle file (keep for re-use) |

---

## Architecture

Five AI models work in sequence, each with a specific job:

```
User Input
(topic, product photo, screen recordings, mood boards)
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  LAYER 0 — Grok 3 + Live Search                     │
│  Scrapes TikTok & Instagram in real time             │
│  Output: trend_brief                                 │
│  · 5 trending hooks (exact phrases)                  │
│  · Hashtag clusters (niche + broad)                  │
│  · Top content formats / content matrix              │
│  · Audio/music mood trending now                     │
│  · High-performing CTA patterns                      │
└────────────────────┬────────────────────────────────┘
                     │ trend_brief
                     ▼
┌─────────────────────────────────────────────────────┐
│  LAYER 1 — Gemini 2.5 Pro                           │
│  Structural reasoning & shot planning                │
│  · Reads trend_brief + asset inventory               │
│  · Outputs JSON shot list:                           │
│    - scene description (EN)                          │
│    - camera movement                                 │
│    - Seedance mode per shot                          │
│    - ref_video_idx → which screen recording to copy  │
│    - ref_image_idxs → which mood boards to reference │
│  Short: 3–8 shots │ Long: auto from target_duration  │
└────────────────────┬────────────────────────────────┘
                     │ shot list
                     ▼
┌─────────────────────────────────────────────────────┐
│  LAYER 2 — Seedance 2.0 (via fal.ai)                │
│  Video clip generation (concurrent optional)        │
│                                                     │
│  3 generation modes:                                │
│  · omni_reference  — character/product consistency  │
│  · first_last_frames — product animation            │
│  · text_to_video   — pure AI generation             │
│                                                     │
│  Supports: 9:16 vertical  │  16:9 horizontal        │
│  Clip duration: 4–15s per clip                      │
│  Assets injected via @image1/@video1 token syntax   │
└────────────────────┬────────────────────────────────┘
                     │ clip URLs
                     ▼
┌─────────────────────────────────────────────────────┐
│  LAYER 3 — Grok 3 (copy generation)                 │
│  English copywriting using trend_brief context      │
│  · Video title (platform-optimized length & style)  │
│  · Per-shot voiceover (one line per clip)           │
│  · Post caption with hashtags                       │
│  · Chapter titles (long video)                      │
└────────────────────┬────────────────────────────────┘
                     │ copy package
                     ▼
┌─────────────────────────────────────────────────────┐
│  LAYER 4 — OpenAI TTS + FFmpeg                      │
│  · TTS: English voiceover → .mp3 per shot           │
│  · FFmpeg: merge TTS into clip (duck original audio)│
│  · FFmpeg: concat all clips                         │
│  · FFmpeg: burn subtitles (Arial, white + outline)  │
│  · Long video: write YouTube chapter timestamps     │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
              output.mp4  +  copy package
```

---

## Four Format Modes

| Mode | `aspect_ratio` | `long_video` | Use case | Clip length |
|------|---------------|-------------|---------|------------|
| Short vertical | `9:16` | `False` | TikTok / Instagram Reels | 4–10s |
| Short horizontal | `16:9` | `False` | Landscape demo / promo | 4–10s |
| Long vertical | `9:16` | `True` | Long-form TikTok vlog | 6–15s |
| Long horizontal | `16:9` | `True` | YouTube tutorial / full demo | 6–15s |

---

## Quick Start

### 1. Install

```bash
pip install google-generativeai fal-client openai requests ffmpeg-python
brew install ffmpeg  # macOS
```

### 2. Set API Keys

```bash
export GEMINI_API_KEY="..."    # aistudio.google.com
export FAL_KEY="..."           # fal.ai (Seedance 2.0)
export XAI_API_KEY="..."       # console.x.ai (Grok 3)
export OPENAI_API_KEY="..."    # platform.openai.com (TTS)
```

### 3. Run

```python
from scripts.pipeline import run_pipeline

# Short TikTok (default)
run_pipeline(
    topic="SPF 50 sunscreen outdoor test",
    platform="tiktok",
)

# With your own assets (local files or URLs)
run_pipeline(
    topic="New lip gloss launch",
    assets={
        "character":    "my_photo.jpg",           # blogger photo
        "product":      "lipgloss.jpg",            # product image
        "ref_videos":   ["screen_rec.mp4"],        # your screen recording
        "extra_images": ["mood_board.jpg"],        # aesthetic reference
    },
    platform="instagram",
    tts_voice="shimmer",
)

# Long YouTube tutorial (~5 min)
run_pipeline(
    topic="Home studio lighting setup guide",
    aspect_ratio="16:9",
    long_video=True,
    target_duration_s=300,
    platform="youtube",
    tts_voice="onyx",
)
```

---

## Parameters

| Parameter | Default | Options | Description |
|-----------|---------|---------|-------------|
| `topic` | required | any string | Video subject or product description |
| `output_path` | `output_final.mp4` | any `.mp4` path | Output file path |
| `assets` | `{}` | see below | Media assets dict |
| `aspect_ratio` | `"9:16"` | `"9:16"` `"16:9"` | Video orientation |
| `long_video` | `False` | `True` `False` | Enable long-form chapter structure |
| `target_duration_s` | `60` | any int | Target length in seconds (long video) |
| `n_shots` | auto | any int | Override shot count |
| `platform` | `"tiktok"` | `tiktok` `instagram` `youtube` `general` | Copy style |
| `tts_voice` | `"nova"` | see TTS table | OpenAI TTS voice |
| `concurrent` | `False` | `True` `False` | Parallel clip generation (5× faster) |

---

## Assets Dictionary

All values accept **local file paths or HTTPS URLs**. Local files are auto-uploaded to fal.ai CDN before generation.

```python
assets = {
    "character":    "path/to/blogger.jpg",        # keeps person consistent across all shots
    "product":      "path/to/product.jpg",         # product reveal / animation shots
    "ref_videos":  ["screen.mp4", "broll.mp4"],   # screen recordings or b-roll (max 3)
    "extra_images": ["mood.jpg", "logo.png"],      # backgrounds / props / mood boards (max 7)
}
```

| Key | Seedance token | Limit | Effect |
|-----|---------------|-------|--------|
| `character` | `@image1` | 1 | Character injected into every shot that needs it |
| `product` | `@image2` | 1 | Product image for reveals and close-ups |
| `ref_videos` | `@video1–3` | ≤ 3 | Gemini assigns each recording to a shot to copy its camera movement |
| `extra_images` | `@image3+` | ≤ 7 | Mood boards assigned by Gemini per shot |

---

## Seedance 2.0 Generation Modes

| Scenario | Mode | What happens |
|----------|------|-------------|
| No assets | `text_to_video` | Pure AI generation from prompt |
| Character / product photo | `omni_reference` | Photo injected as `@image1`/`@image2`, Seedance maintains consistency |
| Product animation (box → hand) | `first_last_frames` | Product photo used as first frame, AI generates to last frame |
| Copy camera movement | `omni_reference` + video | Screen recording injected as `@video1`, Seedance replicates movement |
| Full mix | `omni_reference` | Up to 9 images + 3 videos in one call |

Gemini automatically assigns the correct mode per shot based on available assets.

---

## Platform Presets

| Platform | Title style | Caption style | Voiceover style |
|----------|------------|--------------|----------------|
| `tiktok` | ≤ 60 chars, hook first, 1–2 emoji | 3–5 punchy lines, 3–5 hashtags, CTA | Fast-paced, Gen Z, max 10 words/sentence |
| `instagram` | ≤ 55 chars, keyword-rich | Storytelling paragraph, 5–8 hashtags | Warm, aspirational, complete sentences |
| `youtube` | ≤ 70 chars, SEO keyword | 2–3 paragraphs + chapter timestamps | Clear, authoritative |
| `general` | ≤ 80 chars | 2–3 natural sentences | Conversational |

---

## TTS Voice Guide

| Voice | Character | Best for |
|-------|-----------|---------|
| `nova` | Warm female | Beauty, lifestyle, food |
| `shimmer` | Soft female | Wellness, skincare, fashion |
| `onyx` | Deep male | Tech, finance, YouTube tutorials |
| `alloy` | Neutral, clear | General purpose |
| `echo` | Energetic male | Fitness, gaming |
| `fable` | Expressive | Travel, education, storytelling |

---

## How Grok Live Search Works

Layer 0 calls Grok 3 with `search_parameters.mode = "on"`, pulling from:
- **Web** — Google-indexed TikTok/IG content, creator blogs, trend reports
- **X (Twitter)** — real-time creator discussion, viral sound mentions

The returned `trend_brief` feeds both Gemini (shot planning) and Grok copy generation, so every hook, hashtag, and CTA reflects what is actually working this week — not training data from months ago.

---

## Stack & API Keys

| Service | Purpose | Where to get key |
|---------|---------|-----------------|
| **Seedance 2.0** (fal.ai) | Video clip generation | [fal.ai](https://fal.ai) → Dashboard → API Keys |
| **Gemini 2.5 Pro** | Shot list & structural planning | [aistudio.google.com](https://aistudio.google.com) |
| **Grok 3** (xAI) | Live trend search + English copywriting | [console.x.ai](https://console.x.ai) |
| **OpenAI TTS** | English voiceover audio | [platform.openai.com](https://platform.openai.com) |
| **FFmpeg** | Clip merging, subtitle burn, audio mix | `brew install ffmpeg` / `apt install ffmpeg` |

---

## Repo Structure

```
Vedic-skills/
├── README.md                          ← this file
└── skills/
    ├── video-pipeline.skill           ← distributable .skill package (zip)
    └── video-pipeline/
        ├── SKILL.md                   ← system prompt loaded by AI agents
        ├── scripts/
        │   └── pipeline.py            ← full Python implementation (784 lines)
        └── assets/
            ├── sample_screen_recording_short.mov  ← test footage
            └── sample_screen_recording_long.mov   ← test footage
```

---

## Notes

- All generated copy (titles, voiceover, captions, hashtags) is **English only**
- `scene_zh` in shot JSON is Chinese internal reference only — never shown to end users
- Grok JSON output includes fallback index-slicing if commentary wraps the JSON
- Concurrent mode (`concurrent=True`) runs all Seedance API calls in parallel via `asyncio` — recommended for long video (10+ shots)
- TTS audio is merged **per clip** before final concat, so subtitle timing is frame-accurate
