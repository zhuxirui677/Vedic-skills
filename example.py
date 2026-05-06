"""
Vedic Skills — video-pipeline 快速示例
运行前请先设置好 4 个环境变量（见 README）
"""
import sys, os
sys.path.insert(0, "skills/video-pipeline/scripts")
from pipeline import run_pipeline

# ── 示例 1：抖音短视频（中文，9:16 竖屏）────────────────────────────────────
run_pipeline(
    topic="防晒霜户外实测，真实肤感反应",
    output_path="output_douyin.mp4",
    platform="douyin",
    language="zh",
    aspect_ratio="9:16",
    n_shots=5,
    tts_voice="nova",
    concurrent=True,
    # assets={                          # 可选：提供自己的素材
    #     "character": "blogger.jpg",   # 博主照片（保持人物一致）
    #     "product":   "product.jpg",   # 产品图
    # },
)

# ── 示例 2：小红书种草（中文，9:16 竖屏）────────────────────────────────────
# run_pipeline(
#     topic="护肤早C晚A入门，敏感肌也能用",
#     output_path="output_xhs.mp4",
#     platform="xiaohongshu",
#     language="zh",
#     aspect_ratio="9:16",
#     tts_voice="shimmer",
# )

# ── 示例 3：B站长视频教程（中文，16:9 横屏）─────────────────────────────────
# run_pipeline(
#     topic="家庭影音室从零搭建完整攻略",
#     output_path="output_bilibili.mp4",
#     platform="bilibili",
#     language="zh",
#     aspect_ratio="16:9",
#     long_video=True,
#     target_duration_s=300,
#     tts_voice="onyx",
#     concurrent=True,
# )

# ── 示例 4：TikTok 短视频（英文，9:16 竖屏）─────────────────────────────────
# run_pipeline(
#     topic="SPF 50 sunscreen outdoor test, real skin reaction",
#     output_path="output_tiktok.mp4",
#     platform="tiktok",
#     language="en",
#     aspect_ratio="9:16",
#     n_shots=5,
#     tts_voice="nova",
#     concurrent=True,
# )

# ── 示例 5：YouTube 长教程（英文，16:9 横屏）─────────────────────────────────
# run_pipeline(
#     topic="How to set up a home studio for content creators",
#     output_path="output_youtube.mp4",
#     platform="youtube",
#     language="en",
#     aspect_ratio="16:9",
#     long_video=True,
#     target_duration_s=300,
#     tts_voice="onyx",
#     concurrent=True,
# )
