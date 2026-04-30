---
name: video-pipeline
description: AI short-video and long-video automation pipeline using Seedance 2.0, Gemini 2.5 Pro, Grok 3 Live Search, and OpenAI TTS. Supports vertical 9:16 (TikTok/Reels) and horizontal 16:9 (YouTube/landscape) in both short-clip and long-form formats. Use when producing TikTok/Instagram Reels, YouTube tutorials, product demos, or multi-chapter long videos from a topic, product photo, or blogger image. Handles trend research, shot list generation, chapter structure, video clip creation, English copywriting, voiceover, and final editing. Triggers on requests like "make a short video about X", "create a TikTok for this product", "generate a landscape video", "make a long YouTube tutorial", or any multi-shot AI video production task.
---

# Video Pipeline

Produce publish-ready videos from a topic + optional assets.
Supports **4 format modes**: short/long × vertical/horizontal.

## Format Modes

| Mode | aspect_ratio | long_video | Use case |
|------|-------------|-----------|---------|
| Short vertical | `9:16` | `False` | TikTok / Instagram Reels |
| Short horizontal | `16:9` | `False` | Landscape demo / IG carousel video |
| Long vertical | `9:16` | `True` | Long-form TikTok vlog, portrait story |
| Long horizontal | `16:9` | `True` | YouTube tutorial, product demo, full guide |

## Pipeline Overview

```
User Input (topic / product / blogger photo / screen recordings)
     ↓
[0] Grok 3 Live Search → trend_brief (hooks, hashtags, content matrix, chapters)
     ↓
[1] Gemini 2.5 Pro → shot list + Seedance prompts
     |   Short: 3-8 shots  |  Long: auto-computed from target_duration_s
     |   9:16 portrait      |  16:9 widescreen camera moves
     ↓
[2] Seedance 2.0 → video clips (concurrent, aspect_ratio passed per clip)
     ↓
[3] Grok 3 → English title + voiceover + post caption + chapter titles (long)
     ↓
[4] OpenAI TTS + FFmpeg → merge clips + burn subtitles → final .mp4
     |   Long: also writes _chapters.txt with YouTube timestamp markers
```

## Quick Start

```bash
pip install google-generativeai fal-client openai requests ffmpeg-python

export GEMINI_API_KEY="..."
export FAL_KEY="..."
export XAI_API_KEY="..."
export OPENAI_API_KEY="..."
```

```python
from scripts.pipeline import run_pipeline

# Short 9:16 TikTok (default)
run_pipeline(topic="SPF 50 sunscreen test", platform="tiktok")

# Short 16:9 landscape
run_pipeline(topic="Headphones unboxing", aspect_ratio="16:9", platform="instagram")

# Long 9:16 portrait vlog (~2 min)
run_pipeline(topic="Morning skincare routine",
             aspect_ratio="9:16", long_video=True, target_duration_s=120)

# Long 16:9 YouTube tutorial (~5 min)
run_pipeline(topic="Home studio setup guide",
             aspect_ratio="16:9", long_video=True, target_duration_s=300,
             platform="youtube", tts_voice="onyx")
```

## Key Parameters

| Param | Default | Description |
|-------|---------|-------------|
| `aspect_ratio` | `"9:16"` | `"9:16"` vertical or `"16:9"` horizontal |
| `long_video` | `False` | `True` enables long-form (60s+) chapter structure |
| `target_duration_s` | `60` | Target total seconds (used when `long_video=True`) |
| `n_shots` | auto | Override shot count; auto-computed for long video |
| `platform` | `"tiktok"` | `tiktok` / `instagram` / `youtube` / `general` |
| `concurrent` | `False` | Async clip generation (5× faster) |

## Assets Dictionary

| Key | What | Seedance mapping | Limit |
|-----|------|-----------------|-------|
| `character` | Blogger/person photo | `@image1` every shot | 1 |
| `product` | Product image | `@image2` when needed | 1 |
| `ref_videos` | Screen recordings / B-roll | `@video1-3`, Gemini distributes | ≤3 |
| `extra_images` | Mood boards / logos / props | `@image3+`, Gemini assigns | ≤7 |

All values accept local paths or HTTPS URLs. Local files auto-upload to fal.ai CDN.

## Seedance 2.0 Modes

| Use Case | Mode | Params |
|----------|------|--------|
| Text only | `text_to_video` | `prompt` |
| Person consistency | `omni_reference` | `images_list` + `@image1` |
| Product animation | `first_last_frames` | `first_frame_image` + `last_frame_image` |
| Copy camera movement | `omni_reference` + video | `videos_list` + `@video1` |
| Mix all | `omni_reference` | up to 9 images + 3 videos |

Clip duration: 4–10s (short) / 6–15s (long). Aspect ratio passed per-clip.

## Platform Modes

| Platform | Title | Caption | Voice style |
|----------|-------|---------|------------|
| `tiktok` | ≤60 chars, hook first | 3-5 lines, 3-5 hashtags | Fast, Gen Z |
| `instagram` | ≤55 chars, keyword | Storytelling, 5-8 hashtags | Warm, aspirational |
| `youtube` | ≤70 chars, keyword-rich | 2-3 paragraphs + timestamps | Clear, authoritative |
| `general` | ≤80 chars | 2-3 sentences | Natural conversational |

## TTS Voices

| Voice | Style | Best for |
|-------|-------|----------|
| `nova` | Warm female | Beauty, lifestyle |
| `shimmer` | Soft female | Wellness, skincare |
| `onyx` | Deep male | Tech, finance, YouTube |
| `alloy` | Neutral | General purpose |
| `echo` | Energetic male | Fitness, gaming |
| `fable` | Storytelling | Travel, education |

## Long-Video Output Files

When `long_video=True`, the pipeline writes extra files alongside the `.mp4`:
- `*_copy.txt` — title, caption, chapter list, voiceover per shot, trend brief
- `*_chapters.txt` — YouTube-style timestamp markers (`00:00 Intro`, `00:32 Step 1`, …)

## Key Constraints

1. All copy output is English; `scene_zh` is internal reference only
2. Grok Live Search uses `search_parameters.mode = "on"` with web + X sources
3. TTS merges per-clip before final concat (precise timing)
4. Local files upload to fal.ai CDN automatically
5. Concurrent clip generation available via `concurrent=True` (5× faster)
6. 16:9 mode uses widescreen camera moves (pan, tilt, wide establishing shots)

## Reference Material

- Full implementation: [scripts/pipeline.py](scripts/pipeline.py)
- Sample screen recordings in `assets/` for testing camera-reference workflow
