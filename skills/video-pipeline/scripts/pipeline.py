"""
AI Short-Video / Long-Video Automation Pipeline
Seedance 2.0 + Gemini 2.5 Pro + Grok 3 (Live Search) + OpenAI TTS

Supported formats:
  Short:  9:16 vertical  (TikTok / Instagram Reels / Douyin, 4-15s per clip)
  Short: 16:9 horizontal (YouTube Shorts horizontal / landscape demo)
  Long:   9:16 vertical  (long-form portrait, >60s total, segmented)
  Long:  16:9 horizontal (YouTube / product demo / tutorial, >60s total)

Language support:
  language="en"  — English copy, English TTS, Arial subtitles
  language="zh"  — Chinese copy, Chinese TTS, CJK subtitles (抖音/小红书/B站)
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

# CJK font path for FFmpeg subtitle rendering
CJK_FONT_NAME = "Noto Sans CJK SC"
CJK_FONT_DIR  = "/usr/share/fonts/opentype/noto"

# ── Format presets ─────────────────────────────────────────────────────────────
FORMAT_PRESETS = {
    "short_vertical": {
        "aspect_ratio":    "9:16",
        "orientation":     "vertical",
        "clip_min_s":      4,
        "clip_max_s":      10,
        "long_video":      False,
        "platform_suffix": "vertical 9:16, social media aesthetic, cinematic quality",
    },
    "short_horizontal": {
        "aspect_ratio":    "16:9",
        "orientation":     "horizontal",
        "clip_min_s":      4,
        "clip_max_s":      10,
        "long_video":      False,
        "platform_suffix": "horizontal 16:9, widescreen cinematic, high production value",
    },
    "long_vertical": {
        "aspect_ratio":    "9:16",
        "orientation":     "vertical",
        "clip_min_s":      6,
        "clip_max_s":      15,
        "long_video":      True,
        "platform_suffix": "vertical 9:16, long-form storytelling, cinematic portrait",
    },
    "long_horizontal": {
        "aspect_ratio":    "16:9",
        "orientation":     "horizontal",
        "clip_min_s":      6,
        "clip_max_s":      15,
        "long_video":      True,
        "platform_suffix": "horizontal 16:9, long-form widescreen, YouTube cinematic",
    },
}

# ── Platform rules ─────────────────────────────────────────────────────────────
PLATFORM_RULES = {
    # ── 英文平台 ──
    "tiktok": {
        "title_rule":     "TikTok title: max 60 chars, hook word first, 1-2 emojis, curiosity gap",
        "caption_rule":   "TikTok caption: punchy 3-5 lines, 3-5 hashtags mixing niche+broad, strong CTA",
        "voiceover_rule": "Fast-paced, Gen Z tone, contractions, max 10 words/sentence, hook in first 3s",
        "trend_query":    "site:tiktok.com trending sounds hashtags short video 2025",
        "language":       "en",
    },
    "instagram": {
        "title_rule":     "Instagram Reel title: max 55 chars, keyword-rich for Explore, 1 emoji",
        "caption_rule":   "Instagram caption: storytelling paragraph, line breaks, 5-8 hashtags, CTA question",
        "voiceover_rule": "Warm conversational tone, slightly slower, complete sentences, aspirational",
        "trend_query":    "site:instagram.com trending reels formats hashtags 2025",
        "language":       "en",
    },
    "youtube": {
        "title_rule":     "YouTube title: max 70 chars, keyword-rich, brackets for value prop e.g. [Full Tutorial]",
        "caption_rule":   "YouTube description: 2-3 paragraph summary, timestamps if long, 5-8 tags, subscribe CTA",
        "voiceover_rule": "Clear, authoritative, moderate pace, complete sentences, chapter transitions",
        "trend_query":    "site:youtube.com trending tutorial review long-form 2025",
        "language":       "en",
    },
    "general": {
        "title_rule":     "Title: descriptive, max 80 chars",
        "caption_rule":   "Description: clear 2-3 sentences, relevant tags",
        "voiceover_rule": "Natural conversational tone, clear pronunciation",
        "trend_query":    "trending video content 2025",
        "language":       "en",
    },
    # ── 中文平台 ──
    "douyin": {
        "title_rule":     "抖音标题：不超过20字，开头放钩子词，1-2个emoji，制造好奇心/悬念",
        "caption_rule":   "抖音文案：3-5行短句，每行15字以内，混合3-5个话题标签（#小众+#热门），结尾强CTA",
        "voiceover_rule": "语速偏快，口语化，每句不超过10字，前3秒必须有钩子",
        "trend_query":    "抖音 热门话题 爆款视频 2025 流量密码",
        "language":       "zh",
    },
    "xiaohongshu": {
        "title_rule":     "小红书标题：不超过20字，关键词前置，加感叹号或疑问句，带1个emoji",
        "caption_rule":   "小红书正文：首行抓眼，分行排版，表情符号点缀，5-8个#话题，结尾引导评论",
        "voiceover_rule": "温柔亲切，像朋友聊天，完整句子，带分享感和真实感",
        "trend_query":    "小红书 爆款笔记 热门话题 种草 2025",
        "language":       "zh",
    },
    "bilibili": {
        "title_rule":     "B站标题：不超过80字，关键词SEO优化，用【】标注亮点，引发好奇",
        "caption_rule":   "B站简介：2-3段，介绍内容+时间轴（长视频），末尾加关注引导和相关标签",
        "voiceover_rule": "清晰、有条理，适合讲解，完整句子，语速适中，章节过渡自然",
        "trend_query":    "哔哩哔哩 B站 热门视频 UP主 2025 播放量",
        "language":       "zh",
    },
}

TTS_VOICE = "nova"
TTS_MODEL = "tts-1-hd"


# ── Helper: resolve format preset ────────────────────────────────────────────
def resolve_format(aspect_ratio: str = "9:16", long_video: bool = False) -> dict:
    key_map = {
        ("9:16", False): "short_vertical",
        ("16:9", False): "short_horizontal",
        ("9:16", True):  "long_vertical",
        ("16:9", True):  "long_horizontal",
    }
    return FORMAT_PRESETS[key_map.get((aspect_ratio, long_video), "short_vertical")]


def compute_n_shots(target_duration_s: int, fmt: dict) -> int:
    if not fmt["long_video"]:
        return None
    avg = (fmt["clip_min_s"] + fmt["clip_max_s"]) / 2
    return max(3, math.ceil(target_duration_s / avg))


# ── Layer 0: Grok Live Search — Trend Intelligence ────────────────────────────
def fetch_trend_brief(
    topic: str,
    platform: str = "tiktok",
    long_video: bool = False,
    language: str = "en",
) -> dict:
    """Scrape trends via Grok Live Search. Returns trend_brief dict."""
    platform_label = platform.upper()
    format_note = (
        "long-form video (>60 seconds, multiple chapters/segments)"
        if long_video
        else "short-form video (15-60 seconds)"
    )

    if language == "zh":
        zh_platforms = {
            "douyin":      "抖音",
            "xiaohongshu": "小红书",
            "bilibili":    "哔哩哔哩",
        }
        platform_cn = zh_platforms.get(platform, platform_label)
        format_cn   = "长视频（超过60秒，含多章节）" if long_video else "短视频（15-60秒）"
        chapter_field = '- chapter_structure: 建议的3-5个章节/段落名称（适合长视频）' if long_video else ""

        search_prompt = f"""你是一位{platform_cn}趋势分析师，具备实时网络搜索能力。
搜索与以下主题相关的当前趋势数据："{topic}"
目标格式：{format_cn}

请执行以下搜索：
1. 2025年{platform_cn}关于"{topic}"的热门{format_cn}形式和开场钩子
2. 热门话题标签——混合小众（<500K）和热门（>1M）
3. 内容矩阵：正在爆火的开场方式、转场、CTA
4. 竞品分析：头部创作者的差异化内容策略

返回JSON格式：
- trending_hooks: 5个已被验证的开场钩子（每个不超过15字）
- hashtag_clusters: {{"niche": [5个小众标签], "broad": [5个热门标签]}}
- content_matrix: 3种最高效的内容形式
- trending_audio_style: 背景音乐/氛围描述
- cta_patterns: 3种高互动的CTA话术
- competitor_insight: 1-2句竞品洞察
{chapter_field}

只输出合法JSON，不要markdown代码块。"""
    else:
        chapter_field = (
            "\n- chapter_structure: list of 3-5 suggested chapter/segment names for long-form"
            if long_video else ""
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
- competitor_insight: 1-2 sentences{chapter_field}

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
    language: str = "en",
) -> list[dict]:
    """Generate structured shot list via Gemini."""
    asset_counts = asset_counts or {}
    fmt = fmt or FORMAT_PRESETS["short_vertical"]
    model = genai.GenerativeModel(GEMINI_MODEL)

    n_ref_videos  = asset_counts.get("ref_videos", 0)
    n_extra_images = asset_counts.get("extra_images", 0)
    long_video    = fmt.get("long_video", False)

    chapter_hint = ""
    if long_video and trend_brief.get("chapter_structure"):
        chapter_hint = f"\nSuggested chapters: {trend_brief['chapter_structure']}"
        chapter_hint += "\nOrganize shots into chapters; include chapter_name field per shot."

    voiceover_field = (
        "- voiceover_zh: 中文旁白占位（1-2句，口语化）"
        if language == "zh"
        else "- voiceover_en: placeholder voiceover (1-2 sentences)"
    )

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
- scene_en: English scene (Seedance prompt core, always English)
- camera_en: camera movement
- lighting_en: lighting mood
- mode: "omni_reference" | "first_last_frames" | "text_to_video"
- needs_character: bool
- needs_product: bool
- ref_video_idx: int|null
- ref_image_idxs: list[int]
{voiceover_field}

Rules:
- scene_en and camera_en MUST be English (Seedance requires English prompts)
- First shot opens with a trending hook
- Distribute ref_videos across shots (use each at least once if available)
- Use first_last_frames for product reveal/transformation
{"- Each chapter should have 2-4 shots" if long_video else ""}
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
    url = fal_client.upload_file(local_path)
    print(f"   ↑ Uploaded {Path(local_path).name} → {url[:60]}...")
    return url


def upload_assets(assets: dict) -> dict:
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
    """Construct Seedance API payload. scene_en/camera_en are always English."""
    images_list = []
    videos_list = []
    prompt_parts = []

    char_url = assets.get("character")
    if shot.get("needs_character") and char_url:
        images_list.append(char_url)
        prompt_parts.append(CHARACTER_ANCHOR + f"(@image{len(images_list)})")

    prod_url = assets.get("product")
    if shot.get("needs_product") and prod_url:
        images_list.append(prod_url)
        prompt_parts.append(f"product featured prominently (@image{len(images_list)})")

    for idx in shot.get("ref_image_idxs", []):
        extra = assets.get("extra_images", [])
        if idx < len(extra) and extra[idx]:
            images_list.append(extra[idx])
            prompt_parts.append(f"style reference (@image{len(images_list)})")

    rv_idx   = shot.get("ref_video_idx")
    ref_vids = assets.get("ref_videos", [])
    if rv_idx is not None and rv_idx < len(ref_vids) and ref_vids[rv_idx]:
        videos_list.append(ref_vids[rv_idx])
        prompt_parts.append(
            f"replicate camera movement and pacing from (@video{len(videos_list)})"
        )

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
    mode    = shot.get("mode", "text_to_video")
    payload = build_seedance_prompt(shot, assets, fmt)

    if mode == "first_last_frames":
        prod_url = assets.get("product")
        if prod_url:
            payload["first_frame_image"] = prod_url
            payload.pop("images_list", None)

    result = fal_client.run("fal-ai/seedance-2.0", arguments=payload)
    return result["video"]["url"]


async def generate_all_clips_async(shots: list[dict], assets: dict, fmt: dict) -> list[str]:
    tasks = [asyncio.to_thread(generate_video_clip, s, assets, fmt) for s in shots]
    return await asyncio.gather(*tasks)


# ── Layer 3: Copy Generation ──────────────────────────────────────────────────
def generate_copy(
    topic: str,
    shots: list[dict],
    trend_brief: dict,
    platform: str = "tiktok",
    long_video: bool = False,
    language: str = "en",
) -> dict:
    """Generate title, voiceover lines, and post caption. Supports zh/en."""
    rules        = PLATFORM_RULES.get(platform, PLATFORM_RULES["general"])
    shot_summary = "\n".join(
        f"Shot {s['shot_id']} ({s['duration']}s)"
        + (f" [{s.get('chapter_name','')}]" if long_video else "")
        + f": {s.get('scene_zh', s.get('scene_en', ''))}"
        for s in shots
    )
    hashtag_pool = (
        trend_brief.get("hashtag_clusters", {}).get("niche", [])
        + trend_brief.get("hashtag_clusters", {}).get("broad", [])
    )
    hooks = trend_brief.get("trending_hooks", [])
    ctas  = trend_brief.get("cta_patterns", [])

    if language == "zh":
        long_note = (
            "\n- 这是长视频，旁白每句需1-3句话，章节之间要有自然过渡。"
            if long_video else ""
        )
        chapter_field = (
            '- chapters: 按顺序排列的章节标题列表（用于长视频描述）'
            if long_video else ""
        )
        system = f"""你是一位顶级{platform}内容策略师，服务中文受众。

平台规则：
- {rules['title_rule']}
- {rules['caption_rule']}
- 旁白风格：{rules['voiceover_rule']}{long_note}

热门钩子（第一句旁白用其中一个）：{hooks}
CTA话术（选最合适的）：{ctas}
话题标签池（选5-8个）：{hashtag_pool}

输出JSON：
- title: 字符串
- voiceover: 字符串数组（每个镜头一条，顺序对应，数量必须等于镜头数）
- post_caption: 字符串，用\\n换行，末尾附话题标签
{chapter_field}

全部中文。只输出合法JSON。"""
        user_msg = f"主题：{topic}\n\n分镜：\n{shot_summary}"
    else:
        long_note = (
            "\n- This is a LONG-FORM video. Voiceover lines should be 1-3 sentences each."
            "\n- Include smooth chapter-transition phrases between segments."
            if long_video else ""
        )
        chapter_field = (
            "\n- chapters: list of chapter titles in order (for long-form description)"
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
- post_caption: string with \\n line breaks, ends with hashtags{chapter_field}

All English. Valid JSON only."""
        user_msg = f"Topic: {topic}\n\nShots:\n{shot_summary}"

    resp = grok.chat.completions.create(
        model=GROK_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.85,
    )
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.index("{"), raw.rindex("}") + 1
        return json.loads(raw[start:end])


def apply_voiceover_to_shots(shots: list[dict], copy: dict, language: str = "en") -> list[dict]:
    """Write voiceover lines back into shot dicts under the correct language key."""
    key = "voiceover_zh" if language == "zh" else "voiceover_en"
    for i, shot in enumerate(shots):
        if i < len(copy.get("voiceover", [])):
            shot[key] = copy["voiceover"][i]
    return shots


# ── Layer 4a: TTS ─────────────────────────────────────────────────────────────
def generate_tts_audio(text: str, out_path: str):
    """OpenAI TTS supports both English and Chinese natively."""
    response = openai_client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="mp3",
    )
    response.stream_to_file(out_path)


# ── Layer 4b: FFmpeg Merge ────────────────────────────────────────────────────
def download_clip(url: str, path: str):
    r = requests.get(url, stream=True)
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


def merge_clip_with_tts(video_path: str, audio_path: str, out_path: str):
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


def generate_srt(shots: list[dict], language: str = "en") -> str:
    """Generate SRT subtitle from shots. Reads voiceover_zh or voiceover_en."""
    key   = "voiceover_zh" if language == "zh" else "voiceover_en"
    lines = []
    current = 0.0
    for i, shot in enumerate(shots, 1):
        end = current + shot["duration"]
        lines += [
            str(i),
            f"{_fmt_time(current)} --> {_fmt_time(end)}",
            shot.get(key, ""),
            "",
        ]
        current = end
    return "\n".join(lines)


def _fmt_time(sec: float) -> str:
    h, rem = divmod(sec, 3600)
    m, s   = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def merge_all_and_subtitle(
    clip_paths: list[str],
    srt_path: str,
    output: str,
    aspect_ratio: str = "9:16",
    language: str = "en",
):
    """Concat all clips and burn subtitles. Uses CJK font for Chinese."""
    with open("filelist.txt", "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", "filelist.txt", "-c", "copy", "merged_raw.mp4"],
        check=True,
    )

    font_size  = "16" if aspect_ratio == "16:9" else "18"
    alignment  = "2"

    if language == "zh":
        font_name   = CJK_FONT_NAME
        fontsdir_arg = f":fontsdir={CJK_FONT_DIR}"
    else:
        font_name    = "Arial"
        fontsdir_arg = ""

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", "merged_raw.mp4",
            "-vf",
            f"subtitles={srt_path}{fontsdir_arg}:force_style='"
            f"FontName={font_name},FontSize={font_size},PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,Outline=2,"
            f"Alignment={alignment}'",
            "-c:a", "copy", output,
        ],
        check=True,
    )


# ── Long-video: chapter markers ───────────────────────────────────────────────
def write_chapter_markers(shots: list[dict], output_txt: str):
    seen_chapters = set()
    current = 0.0
    lines   = []
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
    aspect_ratio: str = "9:16",
    long_video: bool = False,
    target_duration_s: int = 60,
    n_shots: int | None = None,
    # ── Platform / language / voice ─────────────────
    platform: str = "tiktok",
    language: str = "en",       # "en" | "zh"
    tts_voice: str = "nova",
    concurrent: bool = False,
) -> dict:
    """
    End-to-end video production pipeline.

    language="zh" 时自动切换：
      - Grok 搜索抖音/小红书/B站趋势（中文）
      - Gemini 生成中文旁白占位
      - Grok 输出中文标题 + 旁白 + 文案
      - TTS 朗读中文（OpenAI TTS 原生支持）
      - 字幕使用 Noto Sans CJK SC 字体

    中文平台可选：platform="douyin" | "xiaohongshu" | "bilibili"

    Examples:
      # 抖音短视频（中文）
      run_pipeline(topic="防晒霜户外测评", platform="douyin", language="zh")

      # 小红书竖版（中文）
      run_pipeline(topic="护肤早C晚A教程", platform="xiaohongshu", language="zh", tts_voice="shimmer")

      # B站长视频（中文）
      run_pipeline(topic="家庭影音室搭建全攻略", platform="bilibili", language="zh",
                   aspect_ratio="16:9", long_video=True, target_duration_s=300)

      # TikTok 短视频（英文，原有功能不变）
      run_pipeline(topic="SPF 50 sunscreen outdoor test", platform="tiktok", language="en")
    """
    global TTS_VOICE
    TTS_VOICE = tts_voice
    assets    = assets or {}

    # 平台默认语言推断
    if language == "en" and platform in ("douyin", "xiaohongshu", "bilibili"):
        language = "zh"

    fmt = resolve_format(aspect_ratio, long_video)
    if n_shots is None:
        n_shots = compute_n_shots(target_duration_s, fmt) if long_video else 5

    lang_label = "中文" if language == "zh" else "English"
    print(
        f"🚀 Pipeline: {topic}\n"
        f"   Format  : {aspect_ratio} {'long-form' if long_video else 'short'} "
        f"({n_shots} shots, ~{n_shots * (fmt['clip_min_s'] + fmt['clip_max_s'])//2}s est.)\n"
        f"   Platform: {platform.upper()}  Language: {lang_label}"
    )

    print("📦 Uploading assets...")
    resolved     = upload_assets(assets)
    asset_counts = {
        "character":    bool(resolved.get("character")),
        "product":      bool(resolved.get("product")),
        "ref_videos":   len(resolved.get("ref_videos", [])),
        "extra_images": len(resolved.get("extra_images", [])),
    }
    print(f"   → {asset_counts}")

    print("🔍 Scraping trends...")
    trend_brief = fetch_trend_brief(topic, platform, long_video, language)
    print(f"   → Hooks: {trend_brief.get('trending_hooks', [])[:2]}")
    if long_video:
        print(f"   → Chapters: {trend_brief.get('chapter_structure', [])}")

    print("📝 Generating shot list...")
    shots = generate_shot_list(topic, trend_brief, n_shots, asset_counts, fmt, language)
    print(f"   → {len(shots)} shots generated")

    print("✍️  Generating copy...")
    copy  = generate_copy(topic, shots, trend_brief, platform, long_video, language)
    shots = apply_voiceover_to_shots(shots, copy, language)
    print(f"   → Title: {copy['title']}")

    voiceover_key = "voiceover_zh" if language == "zh" else "voiceover_en"

    print(f"🔊 Generating TTS ({TTS_VOICE})...")
    tts_paths = []
    for shot in shots:
        tts_path = f"tts_{shot['shot_id']:02d}.mp3"
        generate_tts_audio(shot.get(voiceover_key, ""), tts_path)
        tts_paths.append(tts_path)

    print("🎞️  Generating video clips...")
    if concurrent:
        urls = asyncio.run(generate_all_clips_async(shots, resolved, fmt))
    else:
        urls = []
        for shot in shots:
            chapter_tag = f"[{shot.get('chapter_name','')}] " if long_video else ""
            print(f"   Shot {shot['shot_id']}: {chapter_tag}{shot['scene_en'][:50]}")
            urls.append(generate_video_clip(shot, resolved, fmt))

    clip_paths = []
    for i, (url, shot) in enumerate(zip(urls, shots)):
        raw_path    = f"clip_{shot['shot_id']:02d}_raw.mp4"
        voiced_path = f"clip_{shot['shot_id']:02d}.mp4"
        download_clip(url, raw_path)
        merge_clip_with_tts(raw_path, tts_paths[i], voiced_path)
        clip_paths.append(voiced_path)
        print(f"   ✅ {voiced_path}")

    srt_content = generate_srt(shots, language)
    with open("subs.srt", "w", encoding="utf-8") as f:
        f.write(srt_content)
    print("🔗 Merging + burning subtitles...")
    merge_all_and_subtitle(clip_paths, "subs.srt", output_path, aspect_ratio, language)

    copy_path = output_path.replace(".mp4", "_copy.txt")
    chapters  = copy.get("chapters", [])
    with open(copy_path, "w", encoding="utf-8") as f:
        f.write(f"[标题/TITLE]\n{copy['title']}\n\n")
        f.write(f"[文案/CAPTION]\n{copy['post_caption']}\n\n")
        if long_video and chapters:
            f.write("[章节/CHAPTERS]\n" + "\n".join(chapters) + "\n\n")
        f.write("[旁白/VOICEOVER]\n")
        for i, v in enumerate(copy.get("voiceover", []), 1):
            f.write(f"Shot {i}: {v}\n")
        f.write(f"\n[趋势数据/TREND BRIEF]\n{json.dumps(trend_brief, indent=2, ensure_ascii=False)}\n")

    chapter_markers = []
    if long_video:
        markers_path    = output_path.replace(".mp4", "_chapters.txt")
        chapter_markers = write_chapter_markers(shots, markers_path)
        print(f"   📑 Chapter markers → {markers_path}")

    total_s = sum(s["duration"] for s in shots)
    print(f"\n🎉 Done! → {output_path}  ({total_s}s / {fmt['aspect_ratio']} / {lang_label})")
    return {
        "video_path":       output_path,
        "title":            copy["title"],
        "post_caption":     copy["post_caption"],
        "voiceover":        copy.get("voiceover", []),
        "trend_brief":      trend_brief,
        "chapters":         chapter_markers,
        "total_duration_s": total_s,
        "aspect_ratio":     fmt["aspect_ratio"],
        "language":         language,
    }


# ── Usage Examples ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # ── 抖音短视频（中文）────────────────────────────────────────────────────
    run_pipeline(
        topic="防晒霜户外实测，真实肤感反应",
        output_path="sunscreen_douyin.mp4",
        assets={
            "character": "assets/blogger_face.jpg",
            "product":   "assets/sunscreen_bottle.jpg",
        },
        platform="douyin",
        language="zh",
        aspect_ratio="9:16",
        long_video=False,
        n_shots=5,
        tts_voice="nova",
        concurrent=True,
    )

    # ── 小红书种草（中文）────────────────────────────────────────────────────
    # run_pipeline(
    #     topic="护肤早C晚A入门教程，敏感肌也适用",
    #     output_path="skincare_xhs.mp4",
    #     assets={"character": "assets/blogger_face.jpg"},
    #     platform="xiaohongshu",
    #     language="zh",
    #     aspect_ratio="9:16",
    #     tts_voice="shimmer",
    # )

    # ── B站长视频教程（中文）──────────────────────────────────────────────────
    # run_pipeline(
    #     topic="家庭影音室从零搭建完整攻略",
    #     output_path="home_studio_bilibili.mp4",
    #     platform="bilibili",
    #     language="zh",
    #     aspect_ratio="16:9",
    #     long_video=True,
    #     target_duration_s=300,
    #     tts_voice="onyx",
    #     concurrent=True,
    # )

    # ── TikTok short vertical（英文，原功能不变）────────────────────────────
    # run_pipeline(
    #     topic="SPF 50 sunscreen outdoor test, real skin reaction",
    #     output_path="sunscreen_tiktok.mp4",
    #     platform="tiktok",
    #     language="en",
    #     aspect_ratio="9:16",
    #     n_shots=5,
    #     tts_voice="nova",
    #     concurrent=True,
    # )
