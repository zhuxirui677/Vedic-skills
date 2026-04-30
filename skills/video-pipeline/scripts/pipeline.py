"""
AI Short-Video / Long-Video Automation Pipeline
Seedance 2.0 + Gemini 2.5 Pro + Grok 3 (Live Search) + OpenAI TTS

Supported formats:
  Short:  9:16 vertical  (TikTok / Instagram Reels, 4-15s per clip)
  Short: 16:9 horizontal (YouTube Shorts horizontal / landscape demo)
  Long:   9:16 vertical  (long-form portrait, >60s total, segmented)
  Long:  16:9 horizontal (YouTube / product demo / tutorial, >60s total)
"""

import os, json, subprocess, asyncio, math
from pathlib import Path
import google.generativeai as genai
import fal_client
from openai import OpenAI
import requests

# ── Config ────────────────────────────────────────────────────────────────────
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
GEMINI_MODEL = "gemini-2.5-pro-preview-06-05"

grok = OpenAI(
    api_key=os.environ["XAI_API_KEY"],
    base_url="https://api.x.ai/v1",
)
GROK_MODEL = "grok-3"

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

CHARACTER_ANCHOR = (
    "Young woman, 25 years old, long hair, "
    "casual modern outfit, same person throughout, "
)

# ── Format presets ─────────────────────────────────────────────────────────────
FORMAT_PRESETS = {
    # (aspect_ratio, orientation, clip_duration_range, max_shots_short, platform_suffix)
    "short_vertical": {
        "aspect_ratio":   "9:16",
        "orientation":    "vertical",
        "clip_min_s":     4,
        "clip_max_s":     10,
        "long_video":     False,
        "platform_suffix": "vertical 9:16, social media aesthetic, cinematic quality",
    },
    "short_horizontal": {
        "aspect_ratio":   "16:9",
        "orientation":    "horizontal",
        "clip_min_s":     4,
        "clip_max_s":     10,
        "long_video":     False,
        "platform_suffix": "horizontal 16:9, widescreen cinematic, high production value",
    },
    "long_vertical": {
        "aspect_ratio":   "9:16",
        "orientation":    "vertical",
        "clip_min_s":     6,
        "clip_max_s":     15,
        "long_video":     True,
        "platform_suffix": "vertical 9:16, long-form storytelling, cinematic portrait",
    },
    "long_horizontal": {
        "aspect_ratio":   "16:9",
        "orientation":    "horizontal",
        "clip_min_s":     6,
        "clip_max_s":     15,
        "long_video":     True,
        "platform_suffix": "horizontal 16:9, long-form widescreen, YouTube cinematic",
    },
}

PLATFORM_RULES = {
    "tiktok": {
        "title_rule": "TikTok title: max 60 chars, hook word first, 1-2 emojis, curiosity gap",
        "caption_rule": "TikTok caption: punchy 3-5 lines, 3-5 hashtags mixing niche+broad, strong CTA",
        "voiceover_rule": "Fast-paced, Gen Z tone, contractions, max 10 words/sentence, hook in first 3s",
        "trend_query": "site:tiktok.com trending sounds hashtags short video 2025",
    },
    "instagram": {
        "title_rule": "Instagram Reel title: max 55 chars, keyword-rich for Explore, 1 emoji",
        "caption_rule": "Instagram caption: storytelling paragraph, line breaks, 5-8 hashtags, CTA question",
        "voiceover_rule": "Warm conversational tone, slightly slower, complete sentences, aspirational",
        "trend_query": "site:instagram.com trending reels formats hashtags 2025",
    },
    "youtube": {
        "title_rule": "YouTube title: max 70 chars, keyword-rich, brackets for value prop e.g. [Full Tutorial]",
        "caption_rule": "YouTube description: 2-3 paragraph summary, timestamps if long, 5-8 tags, subscribe CTA",
        "voiceover_rule": "Clear, authoritative, moderate pace, complete sentences, chapter transitions",
        "trend_query": "site:youtube.com trending tutorial review long-form 2025",
    },
    "general": {
        "title_rule": "Title: descriptive, max 80 chars",
        "caption_rule": "Description: clear 2-3 sentences, relevant tags",
        "voiceover_rule": "Natural conversational tone, clear pronunciation",
        "trend_query": "trending video content 2025",
    },
}

TTS_VOICE = "nova"
TTS_MODEL = "tts-1-hd"


# ── Helper: resolve format preset ────────────────────────────────────────────
def resolve_format(
    aspect_ratio: str = "9:16",
    long_video: bool = False,
) -> dict:
    """
    Map (aspect_ratio, long_video) → FORMAT_PRESETS entry.
    aspect_ratio: "9:16" | "16:9"
    long_video:   False = short clip (<60s total) | True = long-form (>60s)
    """
    key_map = {
        ("9:16",  False): "short_vertical",
        ("16:9",  False): "short_horizontal",
        ("9:16",  True):  "long_vertical",
        ("16:9",  True):  "long_horizontal",
    }
    key = key_map.get((aspect_ratio, long_video), "short_vertical")
    return FORMAT_PRESETS[key]


def compute_n_shots(
    target_duration_s: int,
    fmt: dict,
) -> int:
    """
    For long videos: estimate shot count from target total duration.
    Uses midpoint of clip range as average clip length.
    """
    if not fmt["long_video"]:
        return None   # caller provides n_shots directly
    avg = (fmt["clip_min_s"] + fmt["clip_max_s"]) / 2
    return max(3, math.ceil(target_duration_s / avg))


# ── Layer 0: Grok Live Search — Trend Intelligence ────────────────────────────
def fetch_trend_brief(
    topic: str,
    platform: str = "tiktok",
    long_video: bool = False,
) -> dict:
    """Scrape TikTok/IG/YouTube trends via Grok Live Search. Returns trend_brief dict."""
    platform_label = platform.upper()
    format_note = (
        "long-form video (>60 seconds, multiple chapters/segments)"
        if long_video
        else "short-form video (15-60 seconds)"
    )

    search_prompt = f"""You are a {platform_label} trend analyst with live web access.
Search for current trending data related to: "{topic}"
Target format: {format_note}

Perform these searches:
1. Top performing {platform_label} {format_note} formats and hooks for "{topic}" in 2025
2. Trending hashtags — mix niche (<500K) and broad (>1M)
3. Content matrix patterns: hooks, transitions, CTAs going viral
4. Competitor analysis: what top creators do differently

Return JSON:
- trending_hooks: list of 5 proven opening hooks (under 8 words each)
- hashtag_clusters: {{"niche": [5 tags], "broad": [5 tags]}}
- content_matrix: list of 3 best-performing content formats
- trending_audio_style: mood/music description
- cta_patterns: list of 3 high-engagement CTAs
- competitor_insight: 1-2 sentences
{"- chapter_structure: list of 3-5 suggested chapter/segment names for long-form" if long_video else ""}

Only output valid JSON. No markdown fences."""

    resp = grok.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "user", "content": search_prompt}],
        temperature=0.3,
        extra_body={
            "search_parameters": {
                "mode": "on",
                "sources": [{"type": "web"}, {"type": "x"}],
                "max_search_results": 20,
            }
        },
    )
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.index("{"), raw.rindex("}") + 1
        return json.loads(raw[start:end])


# ── Layer 1: Gemini — Shot List ───────────────────────────────────────────────
def generate_shot_list(
    topic: str,
    trend_brief: dict,
    n_shots: int = 5,
    asset_counts: dict | None = None,
    fmt: dict | None = None,
) -> list[dict]:
    """
    Generate structured shot list via Gemini.
    For long videos, n_shots can be 10-30+; Gemini will organize into chapters.
    """
    asset_counts = asset_counts or {}
    fmt = fmt or FORMAT_PRESETS["short_vertical"]
    model = genai.GenerativeModel(GEMINI_MODEL)

    n_ref_videos = asset_counts.get("ref_videos", 0)
    n_extra_images = asset_counts.get("extra_images", 0)
    long_video = fmt.get("long_video", False)

    chapter_hint = ""
    if long_video and trend_brief.get("chapter_structure"):
        chapter_hint = f"\nSuggested chapters: {trend_brief['chapter_structure']}"
        chapter_hint += "\nOrganize shots into chapters; include chapter_name field per shot."

    system = f"""You are a professional {"long-form " if long_video else ""}short-video director.
Output a JSON array of shots for a {fmt['aspect_ratio']} {"portrait" if fmt['orientation']=="vertical" else "landscape"} video.
{"Total video target: " + str(n_shots) + " shots, organized into narrative chapters." if long_video else ""}
{chapter_hint}

Available media assets:
- character photo: {"YES" if asset_counts.get("character") else "NO"}
- product photo: {"YES" if asset_counts.get("product") else "NO"}
- reference videos: {n_ref_videos} files (indices 0–{max(0, n_ref_videos-1)})
- extra images: {n_extra_images} files (indices 0–{max(0, n_extra_images-1)})

Each shot object:
- shot_id: int (1-based)
- duration: int ({fmt['clip_min_s']}–{fmt['clip_max_s']} seconds)
{"- chapter_name: string — narrative chapter this shot belongs to" if long_video else ""}
- scene_zh: Chinese description (internal ref)
- scene_en: English scene (Seedance prompt core)
- camera_en: camera movement — {"wide establishing, pan left/right, tilt up/down, push in, pull out, tracking, dolly zoom" if fmt['orientation']=="horizontal" else "close-up, wide shot, push in, pull out, tracking shot, dolly zoom"}
- lighting_en: lighting mood
- mode: "omni_reference" | "first_last_frames" | "text_to_video"
- needs_character: bool
- needs_product: bool
- ref_video_idx: int|null
- ref_image_idxs: list[int]
- voiceover_en: placeholder voiceover (1-2 sentences{"" if not long_video else ", suitable for long-form narration"})

Rules:
- First shot opens with a trending hook
- Distribute ref_videos across shots (use each at least once if available)
- Use first_last_frames for product reveal/transformation
{"- Each chapter should have 2-4 shots" if long_video else ""}
{"- Include establishing wide shots at chapter transitions" if fmt['orientation']=="horizontal" else ""}
Output valid JSON array only."""

    trend_context = (
        f"Trending hooks: {trend_brief.get('trending_hooks', [])}\n"
        f"Content formats: {trend_brief.get('content_matrix', [])}\n"
        f"Audio mood: {trend_brief.get('trending_audio_style', '')}"
    )
    prompt = (
        f"Topic: {topic}\n"
        f"Trend data:\n{trend_context}\n"
        f"Generate {n_shots} shots for {fmt['aspect_ratio']} "
        f"{'long-form' if long_video else 'short'} video."
    )

    response = model.generate_content(
        [{"role": "user", "parts": [{"text": system + "\n\n" + prompt}]}]
    )
    return json.loads(response.text)


# ── Asset Upload ──────────────────────────────────────────────────────────────
def upload_local_file(local_path: str) -> str:
    """Upload local file to fal.ai CDN, return public URL."""
    url = fal_client.upload_file(local_path)
    print(f"   ↑ Uploaded {Path(local_path).name} → {url[:60]}...")
    return url


def upload_assets(assets: dict) -> dict:
    """Resolve all local paths to public URLs. Pass-through existing URLs."""
    def resolve(val):
        if val and not str(val).startswith("http"):
            return upload_local_file(val)
        return val

    return {
        "character":    resolve(assets.get("character")),
        "product":      resolve(assets.get("product")),
        "ref_videos":   [resolve(v) for v in assets.get("ref_videos", [])],
        "extra_images": [resolve(v) for v in assets.get("extra_images", [])],
    }


# ── Build Seedance Prompt ─────────────────────────────────────────────────────
def build_seedance_prompt(shot: dict, assets: dict, fmt: dict) -> dict:
    """Construct Seedance API payload from shot + resolved asset URLs."""
    images_list = []
    videos_list = []
    prompt_parts = []

    # Character reference → @image1
    char_url = assets.get("character")
    if shot.get("needs_character") and char_url:
        images_list.append(char_url)
        prompt_parts.append(CHARACTER_ANCHOR + f"(@image{len(images_list)})")

    # Product reference → @image2
    prod_url = assets.get("product")
    if shot.get("needs_product") and prod_url:
        images_list.append(prod_url)
        prompt_parts.append(f"product featured prominently (@image{len(images_list)})")

    # Extra images → @image3+
    for idx in shot.get("ref_image_idxs", []):
        extra = assets.get("extra_images", [])
        if idx < len(extra) and extra[idx]:
            images_list.append(extra[idx])
            prompt_parts.append(f"style reference (@image{len(images_list)})")

    # Reference video → @video1
    rv_idx = shot.get("ref_video_idx")
    ref_vids = assets.get("ref_videos", [])
    if rv_idx is not None and rv_idx < len(ref_vids) and ref_vids[rv_idx]:
        videos_list.append(ref_vids[rv_idx])
        prompt_parts.append(
            f"replicate camera movement and pacing from (@video{len(videos_list)})"
        )

    # Scene / camera / lighting
    prompt_parts += [shot["scene_en"], shot["camera_en"], shot["lighting_en"]]
    prompt_parts.append(fmt["platform_suffix"])

    payload = {
        "prompt":       ", ".join(prompt_parts),
        "duration":     shot["duration"],
        "aspect_ratio": fmt["aspect_ratio"],
        "enable_audio": False,
    }
    if images_list:
        payload["images_list"] = images_list
    if videos_list:
        payload["videos_list"] = videos_list
    return payload


# ── Layer 2: Seedance — Generate Clips ────────────────────────────────────────
def generate_video_clip(shot: dict, assets: dict, fmt: dict) -> str:
    """Generate a single video clip via Seedance 2.0. Returns clip URL."""
    mode = shot.get("mode", "text_to_video")
    payload = build_seedance_prompt(shot, assets, fmt)

    if mode == "first_last_frames":
        prod_url = assets.get("product")
        if prod_url:
            payload["first_frame_image"] = prod_url
            payload.pop("images_list", None)

    result = fal_client.run("fal-ai/seedance-2.0", arguments=payload)
    return result["video"]["url"]


async def generate_all_clips_async(shots: list[dict], assets: dict, fmt: dict) -> list[str]:
    """Concurrent clip generation (5× faster)."""
    tasks = [
        asyncio.to_thread(generate_video_clip, s, assets, fmt) for s in shots
    ]
    return await asyncio.gather(*tasks)


# ── Layer 3: Grok — English Copy ──────────────────────────────────────────────
def generate_copy(
    topic: str,
    shots: list[dict],
    trend_brief: dict,
    platform: str = "tiktok",
    long_video: bool = False,
) -> dict:
    """Generate title, voiceover lines, and post caption via Grok."""
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["general"])
    shot_summary = "\n".join(
        f"Shot {s['shot_id']} ({s['duration']}s)"
        + (f" [{s.get('chapter_name','')}]" if long_video else "")
        + f": {s['scene_en']}"
        for s in shots
    )
    hashtag_pool = (
        trend_brief.get("hashtag_clusters", {}).get("niche", [])
        + trend_brief.get("hashtag_clusters", {}).get("broad", [])
    )
    hooks = trend_brief.get("trending_hooks", [])
    ctas  = trend_brief.get("cta_patterns", [])

    long_note = (
        "\n- This is a LONG-FORM video. Voiceover lines should be 1-3 sentences each."
        "\n- Include smooth chapter-transition phrases between segments."
        if long_video else ""
    )

    system = f"""You are a top-tier {platform.upper()} content strategist for English audiences.

Platform rules:
- {rules['title_rule']}
- {rules['caption_rule']}
- Voiceover: {rules['voiceover_rule']}{long_note}

Trending hooks (use one for first voiceover): {hooks}
CTAs (pick best): {ctas}
Hashtag pool (choose 5-8): {hashtag_pool}

Output JSON:
- title: string
- voiceover: array of strings (one per shot, in order — MUST equal number of shots)
- post_caption: string with \\n line breaks, ends with hashtags
{"- chapters: list of chapter titles in order (for long-form description)" if long_video else ""}

All English. Valid JSON only."""

    resp = grok.chat.completions.create(
        model=GROK_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Topic: {topic}\n\nShots:\n{shot_summary}"},
        ],
        temperature=0.85,
    )
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.index("{"), raw.rindex("}") + 1
        return json.loads(raw[start:end])


def apply_voiceover_to_shots(shots: list[dict], copy: dict) -> list[dict]:
    """Merge voiceover lines back into shot dicts."""
    for i, shot in enumerate(shots):
        if i < len(copy.get("voiceover", [])):
            shot["voiceover_en"] = copy["voiceover"][i]
    return shots


# ── Layer 4a: TTS ─────────────────────────────────────────────────────────────
def generate_tts_audio(text: str, out_path: str):
    """Generate TTS audio file for a single voiceover line."""
    response = openai_client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="mp3",
    )
    response.stream_to_file(out_path)


# ── Layer 4b: FFmpeg Merge ────────────────────────────────────────────────────
def download_clip(url: str, path: str):
    """Download a video clip from URL."""
    r = requests.get(url, stream=True)
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


def merge_clip_with_tts(video_path: str, audio_path: str, out_path: str):
    """Overlay TTS audio onto a clip, duck original audio to 10%."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex",
            "[0:a]volume=0.1[orig];[orig][1:a]amix=inputs=2:duration=shortest[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            out_path,
        ],
        check=True,
    )


def generate_srt(shots: list[dict]) -> str:
    """Generate SRT subtitle content from shots."""
    lines = []
    current = 0.0
    for i, shot in enumerate(shots, 1):
        end = current + shot["duration"]
        lines += [
            str(i),
            f"{_fmt_time(current)} --> {_fmt_time(end)}",
            shot.get("voiceover_en", ""),
            "",
        ]
        current = end
    return "\n".join(lines)


def _fmt_time(sec: float) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def merge_all_and_subtitle(
    clip_paths: list[str],
    srt_path: str,
    output: str,
    aspect_ratio: str = "9:16",
):
    """Concat all clips and burn subtitles. Adjusts subtitle position for 16:9."""
    with open("filelist.txt", "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", "filelist.txt", "-c", "copy", "merged_raw.mp4"],
        check=True,
    )

    # 16:9: subtitles at bottom (Alignment=2); 9:16: same but font slightly bigger
    font_size = "16" if aspect_ratio == "16:9" else "18"
    alignment = "2"   # bottom-center for both orientations

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", "merged_raw.mp4",
            "-vf",
            f"subtitles={srt_path}:force_style='"
            f"FontName=Arial,FontSize={font_size},PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,Outline=2,"
            f"Alignment={alignment}'",
            "-c:a", "copy", output,
        ],
        check=True,
    )


# ── Long-video: chapter markers ───────────────────────────────────────────────
def write_chapter_markers(shots: list[dict], output_txt: str):
    """
    Write YouTube-style chapter markers to a text file.
    Format:  00:00 Intro
             00:08 Chapter 2 ...
    Only meaningful for long-form videos.
    """
    seen_chapters = set()
    current = 0.0
    lines = []
    for shot in shots:
        chapter = shot.get("chapter_name")
        if chapter and chapter not in seen_chapters:
            seen_chapters.add(chapter)
            mins, secs = divmod(int(current), 60)
            lines.append(f"{mins:02d}:{secs:02d} {chapter}")
        current += shot["duration"]
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return lines


# ── Main Pipeline ─────────────────────────────────────────────────────────────
def run_pipeline(
    topic: str,
    output_path: str = "output_final.mp4",
    assets: dict | None = None,
    # ── Format control ──────────────────────────────
    aspect_ratio: str = "9:16",    # "9:16" | "16:9"
    long_video: bool = False,      # False = short clip | True = long-form
    target_duration_s: int = 60,   # total video target (used when long_video=True)
    n_shots: int | None = None,    # override shot count (auto-computed if long_video)
    # ── Platform / voice ────────────────────────────
    platform: str = "tiktok",      # tiktok | instagram | youtube | general
    tts_voice: str = "nova",
    concurrent: bool = False,
) -> dict:
    """
    End-to-end video production pipeline.

    Format examples:
      Short 9:16 TikTok:   aspect_ratio="9:16", long_video=False, n_shots=5
      Short 16:9 landscape: aspect_ratio="16:9", long_video=False, n_shots=5
      Long  9:16 portrait:  aspect_ratio="9:16", long_video=True, target_duration_s=120
      Long  16:9 YouTube:   aspect_ratio="16:9", long_video=True, target_duration_s=300, platform="youtube"

    Args:
        topic:              Video topic/concept
        output_path:        Final .mp4 output path
        assets:             Dict with character, product, ref_videos, extra_images
        aspect_ratio:       "9:16" (vertical) or "16:9" (horizontal/widescreen)
        long_video:         True for long-form (60s+) with chapter structure
        target_duration_s:  Target total duration in seconds (used when long_video=True)
        n_shots:            Override shot count; auto-computed when long_video=True
        platform:           tiktok / instagram / youtube / general
        tts_voice:          OpenAI TTS voice name
        concurrent:         Use async clip generation (5× faster)

    Returns:
        Dict with video_path, title, post_caption, voiceover, trend_brief,
        and chapters (long-form only).
    """
    global TTS_VOICE
    TTS_VOICE = tts_voice
    assets = assets or {}

    # Resolve format preset
    fmt = resolve_format(aspect_ratio, long_video)
    if n_shots is None:
        n_shots = compute_n_shots(target_duration_s, fmt) if long_video else 5

    print(
        f"🚀 Pipeline: {topic}\n"
        f"   Format : {aspect_ratio} {'long-form' if long_video else 'short'} "
        f"({n_shots} shots, ~{n_shots * (fmt['clip_min_s'] + fmt['clip_max_s'])//2}s est.)\n"
        f"   Platform: {platform.upper()}"
    )

    # Upload assets
    print("📦 Uploading assets...")
    resolved = upload_assets(assets)
    asset_counts = {
        "character":    bool(resolved.get("character")),
        "product":      bool(resolved.get("product")),
        "ref_videos":   len(resolved.get("ref_videos", [])),
        "extra_images": len(resolved.get("extra_images", [])),
    }
    print(f"   → {asset_counts}")

    # Layer 0: Trends
    print("🔍 Scraping trends...")
    trend_brief = fetch_trend_brief(topic, platform, long_video)
    print(f"   → Hooks: {trend_brief.get('trending_hooks', [])[:2]}")
    if long_video:
        print(f"   → Chapters: {trend_brief.get('chapter_structure', [])}")

    # Layer 1: Shot list
    print("📝 Generating shot list...")
    shots = generate_shot_list(topic, trend_brief, n_shots, asset_counts, fmt)
    print(f"   → {len(shots)} shots generated")

    # Layer 3: Copy
    print("✍️  Generating copy...")
    copy = generate_copy(topic, shots, trend_brief, platform, long_video)
    shots = apply_voiceover_to_shots(shots, copy)
    print(f"   → Title: {copy['title']}")

    # Layer 4a: TTS
    print(f"🔊 Generating TTS ({TTS_VOICE})...")
    tts_paths = []
    for shot in shots:
        tts_path = f"tts_{shot['shot_id']:02d}.mp3"
        generate_tts_audio(shot.get("voiceover_en", ""), tts_path)
        tts_paths.append(tts_path)

    # Layer 2: Generate clips
    print("🎞️  Generating video clips...")
    if concurrent:
        urls = asyncio.run(generate_all_clips_async(shots, resolved, fmt))
    else:
        urls = []
        for shot in shots:
            chapter_tag = f"[{shot.get('chapter_name','')}] " if long_video else ""
            print(f"   Shot {shot['shot_id']}: {chapter_tag}{shot['scene_en'][:50]}")
            urls.append(generate_video_clip(shot, resolved, fmt))

    # Download + merge TTS per clip
    clip_paths = []
    for i, (url, shot) in enumerate(zip(urls, shots)):
        raw_path    = f"clip_{shot['shot_id']:02d}_raw.mp4"
        voiced_path = f"clip_{shot['shot_id']:02d}.mp4"
        download_clip(url, raw_path)
        merge_clip_with_tts(raw_path, tts_paths[i], voiced_path)
        clip_paths.append(voiced_path)
        print(f"   ✅ {voiced_path}")

    # Layer 4b: Final merge + subtitles
    srt_content = generate_srt(shots)
    with open("subs.srt", "w", encoding="utf-8") as f:
        f.write(srt_content)
    print("🔗 Merging + burning subtitles...")
    merge_all_and_subtitle(clip_paths, "subs.srt", output_path, aspect_ratio)

    # Save copy package
    copy_path = output_path.replace(".mp4", "_copy.txt")
    chapters   = copy.get("chapters", [])
    with open(copy_path, "w", encoding="utf-8") as f:
        f.write(f"[TITLE]\n{copy['title']}\n\n")
        f.write(f"[POST CAPTION]\n{copy['post_caption']}\n\n")
        if long_video and chapters:
            f.write(f"[CHAPTERS]\n" + "\n".join(chapters) + "\n\n")
        f.write("[VOICEOVER]\n")
        for i, v in enumerate(copy.get("voiceover", []), 1):
            f.write(f"Shot {i}: {v}\n")
        f.write(f"\n[TREND BRIEF]\n{json.dumps(trend_brief, indent=2)}\n")

    # Chapter markers file (long-form)
    chapter_markers = []
    if long_video:
        markers_path = output_path.replace(".mp4", "_chapters.txt")
        chapter_markers = write_chapter_markers(shots, markers_path)
        print(f"   📑 Chapter markers → {markers_path}")

    total_s = sum(s["duration"] for s in shots)
    print(f"\n🎉 Done! → {output_path}  ({total_s}s / {fmt['aspect_ratio']})")
    return {
        "video_path":      output_path,
        "title":           copy["title"],
        "post_caption":    copy["post_caption"],
        "voiceover":       copy.get("voiceover", []),
        "trend_brief":     trend_brief,
        "chapters":        chapter_markers,
        "total_duration_s": total_s,
        "aspect_ratio":    fmt["aspect_ratio"],
    }


# ── Usage Examples ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # ── Example 1: Short vertical 9:16 TikTok (original behavior) ─────────────
    run_pipeline(
        topic="SPF 50 sunscreen outdoor test, real skin reaction",
        output_path="sunscreen_tiktok.mp4",
        assets={
            "character": "assets/blogger_face.jpg",
            "product":   "assets/sunscreen_bottle.jpg",
            "ref_videos": ["assets/outdoor_walk_raw.mp4"],
        },
        aspect_ratio="9:16",
        long_video=False,
        n_shots=5,
        platform="tiktok",
        tts_voice="nova",
        concurrent=True,
    )

    # ── Example 2: Short horizontal 16:9 landscape demo ───────────────────────
    # run_pipeline(
    #     topic="Product unboxing: premium wireless headphones",
    #     output_path="headphones_landscape.mp4",
    #     assets={
    #         "product": "assets/headphones.jpg",
    #         "ref_videos": ["assets/desk_broll.mp4"],
    #     },
    #     aspect_ratio="16:9",
    #     long_video=False,
    #     n_shots=6,
    #     platform="instagram",
    #     tts_voice="alloy",
    # )

    # ── Example 3: Long vertical 9:16 portrait (e.g. 2-min vlog) ─────────────
    # run_pipeline(
    #     topic="Morning skincare routine — 5 steps for glowing skin",
    #     output_path="skincare_vlog_long.mp4",
    #     assets={
    #         "character": "assets/blogger_face.jpg",
    #         "ref_videos": ["assets/bathroom_broll.mp4", "assets/product_lineup.mp4"],
    #         "extra_images": ["assets/product_flat.jpg"],
    #     },
    #     aspect_ratio="9:16",
    #     long_video=True,
    #     target_duration_s=120,    # ~2 minutes
    #     platform="tiktok",
    #     tts_voice="shimmer",
    #     concurrent=True,
    # )

    # ── Example 4: Long horizontal 16:9 YouTube tutorial ─────────────────────
    # run_pipeline(
    #     topic="How to set up a home studio for content creators — full guide",
    #     output_path="home_studio_youtube.mp4",
    #     assets={
    #         "character": "assets/creator.jpg",
    #         "ref_videos": [
    #             "assets/studio_recording.mov",   # screen recording / room tour
    #             "assets/gear_broll.mp4",
    #         ],
    #         "extra_images": ["assets/gear_list.jpg", "assets/room_layout.png"],
    #     },
    #     aspect_ratio="16:9",
    #     long_video=True,
    #     target_duration_s=300,    # ~5 minutes
    #     platform="youtube",
    #     tts_voice="onyx",
    #     concurrent=True,
    # )
