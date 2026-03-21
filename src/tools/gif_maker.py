"""GIF 制作工具 — 视频转GIF、图片序列转GIF、屏幕区域录制GIF。

支持功能：
- video_to_gif: 视频转 GIF（需要 moviepy）
- images_to_gif: 图片序列转 GIF（纯 Pillow）
- capture_region_to_gif: 屏幕区域录制为 GIF（mss + Pillow）

注意：moviepy 为可选依赖，用于视频转 GIF。
未安装时，video_to_gif 功能不可用，其他功能正常。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import mss
from PIL import Image

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# 尝试导入 moviepy（可选依赖）
try:
    from moviepy.editor import VideoFileClip
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False
    logger.info("moviepy 未安装，视频转GIF功能不可用")


class GifMakerTool(BaseTool):
    """GIF 制作工具。

    支持：
    - 视频转 GIF（需要 moviepy）
    - 图片序列转 GIF
    - 屏幕区域录制为 GIF
    """

    name = "gif_maker"
    emoji = "🎞️"
    title = "GIF制作"
    description = "GIF 动图制作：视频转GIF、图片序列转GIF、屏幕区域录制GIF"
    timeout = 120

    def __init__(self, output_dir: str = "") -> None:
        """初始化 GIF 制作工具。

        Args:
            output_dir: 输出目录，默认为项目的 generated/日期/ 目录
        """
        super().__init__()
        self.output_dir = (
            Path(output_dir) if output_dir
            else Path(__file__).parent.parent.parent / "generated" / datetime.now().strftime("%Y-%m-%d")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="video_to_gif",
                description="视频转 GIF（需要安装 moviepy）",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "视频文件路径",
                    },
                    "fps": {
                        "type": "integer",
                        "description": "帧率，默认10",
                    },
                    "width": {
                        "type": "integer",
                        "description": "输出宽度像素，默认保持原始",
                    },
                    "start_time": {
                        "type": "number",
                        "description": "开始时间(秒)",
                    },
                    "end_time": {
                        "type": "number",
                        "description": "结束时间(秒)",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="images_to_gif",
                description="图片序列转 GIF",
                parameters={
                    "input_paths": {
                        "type": "string",
                        "description": "图片文件路径，多个路径用逗号分隔",
                    },
                    "fps": {
                        "type": "integer",
                        "description": "帧率，默认5",
                    },
                    "width": {
                        "type": "integer",
                        "description": "输出宽度像素",
                    },
                    "loop": {
                        "type": "integer",
                        "description": "循环次数，0为无限循环，默认0",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["input_paths"],
            ),
            ActionDef(
                name="capture_region_to_gif",
                description="屏幕区域录制为 GIF",
                parameters={
                    "x": {
                        "type": "integer",
                        "description": "左上角X坐标",
                    },
                    "y": {
                        "type": "integer",
                        "description": "左上角Y坐标",
                    },
                    "width": {
                        "type": "integer",
                        "description": "截取宽度",
                    },
                    "height": {
                        "type": "integer",
                        "description": "截取高度",
                    },
                    "duration": {
                        "type": "number",
                        "description": "录制时长(秒)，默认3",
                    },
                    "fps": {
                        "type": "integer",
                        "description": "帧率，默认10",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["x", "y", "width", "height"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定动作。"""
        action_map = {
            "video_to_gif": self._video_to_gif,
            "images_to_gif": self._images_to_gif,
            "capture_region_to_gif": self._capture_region_to_gif,
        }

        handler = action_map.get(action)
        if handler is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}",
            )

        return handler(params)

    def _get_output_path(self, params: dict, prefix: str) -> Path:
        """生成输出文件路径。"""
        filename = params.get("output_filename", "").strip()
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}"
        return self.output_dir / f"{filename}.gif"

    def _video_to_gif(self, params: dict[str, Any]) -> ToolResult:
        """视频转 GIF。"""
        if not HAS_MOVIEPY:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="视频转GIF需要安装 moviepy 库。请运行: pip install moviepy",
            )

        input_path_str = params.get("input_path", "").strip()
        if not input_path_str:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="请提供视频文件路径",
            )

        input_path = Path(input_path_str)
        if not input_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"文件不存在: {input_path}",
            )

        fps = int(params.get("fps", 10))
        width = params.get("width")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        output_path = self._get_output_path(params, "video_gif")

        try:
            clip = VideoFileClip(str(input_path))
            original_duration = clip.duration

            # 裁剪时间段
            if start_time is not None or end_time is not None:
                start = float(start_time) if start_time is not None else 0
                end = float(end_time) if end_time is not None else clip.duration
                clip = clip.subclip(start, end)

            # 调整宽度
            if width:
                clip = clip.resize(width=int(width))

            # 生成 GIF
            clip.write_gif(str(output_path), fps=fps)
            clip.close()

            result_duration = clip.duration if hasattr(clip, 'duration') else (end_time or original_duration) - (start_time or 0)
            file_size = output_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=(
                    f"✅ 视频转 GIF 完成\n"
                    f"📁 文件: {output_path.name}\n"
                    f"📏 大小: {file_size_mb:.2f} MB\n"
                    f"🎬 帧率: {fps} fps\n"
                    f"⏱️ 时长: {result_duration:.1f}秒"
                ),
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size_bytes": file_size,
                    "fps": fps,
                },
            )

        except Exception as e:
            logger.error("视频转GIF失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"视频转GIF失败: {e}",
            )

    def _images_to_gif(self, params: dict[str, Any]) -> ToolResult:
        """图片序列转 GIF。"""
        input_paths_str = params.get("input_paths", "").strip()
        if not input_paths_str:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="请提供图片文件路径（多个路径用逗号分隔）",
            )

        # 解析路径列表
        paths = [p.strip() for p in input_paths_str.split(",") if p.strip()]
        if not paths:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="没有提供有效的图片路径",
            )

        fps = int(params.get("fps", 5))
        width = params.get("width")
        loop = int(params.get("loop", 0))
        output_path = self._get_output_path(params, "images_gif")

        try:
            images = []
            valid_paths = []

            for p in paths:
                path = Path(p)
                if not path.exists():
                    logger.warning("图片文件不存在，跳过: %s", p)
                    continue

                try:
                    img = Image.open(path)
                    # 调整宽度
                    if width:
                        w = int(width)
                        ratio = w / img.width
                        h = int(img.height * ratio)
                        img = img.resize((w, h), Image.Resampling.LANCZOS)
                    # 转换为 RGBA 以支持透明
                    images.append(img.convert("RGBA"))
                    valid_paths.append(p)
                except Exception as e:
                    logger.warning("无法打开图片 %s: %s", p, e)
                    continue

            if not images:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="没有有效的图片文件",
                )

            # 计算帧间隔（毫秒）
            duration_ms = int(1000 / fps)

            # 保存为 GIF
            images[0].save(
                str(output_path),
                save_all=True,
                append_images=images[1:],
                duration=duration_ms,
                loop=loop,
                optimize=True,
            )

            file_size = output_path.stat().st_size
            file_size_kb = file_size / 1024
            loop_desc = "无限循环" if loop == 0 else f"{loop}次"

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=(
                    f"✅ 图片序列转 GIF 完成\n"
                    f"📁 文件: {output_path.name}\n"
                    f"📏 大小: {file_size_kb:.1f} KB\n"
                    f"🖼️ 帧数: {len(images)}\n"
                    f"🎬 帧率: {fps} fps\n"
                    f"🔄 循环: {loop_desc}"
                ),
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size_bytes": file_size,
                    "frame_count": len(images),
                    "fps": fps,
                    "loop": loop,
                    "valid_paths": valid_paths,
                },
            )

        except Exception as e:
            logger.error("图片序列转GIF失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"图片序列转GIF失败: {e}",
            )

    def _capture_region_to_gif(self, params: dict[str, Any]) -> ToolResult:
        """屏幕区域录制为 GIF。"""
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        w = int(params.get("width", 400))
        h = int(params.get("height", 300))
        duration = float(params.get("duration", 3))
        fps = int(params.get("fps", 10))
        output_path = self._get_output_path(params, "capture_gif")

        # 参数验证
        if w <= 0 or h <= 0:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="宽度和高度必须大于0",
            )
        if duration <= 0:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="录制时长必须大于0",
            )
        if fps <= 0 or fps > 60:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="帧率必须在1-60之间",
            )

        monitor = {"left": x, "top": y, "width": w, "height": h}
        frames = []
        frame_interval = 1.0 / fps

        try:
            with mss.mss() as sct:
                start_time = time.time()
                frame_index = 0

                while time.time() - start_time < duration:
                    # 截图
                    screenshot = sct.grab(monitor)
                    # 转换为 PIL Image（BGRA -> RGB）
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    frames.append(img)
                    frame_index += 1

                    # 等待到下一帧时间
                    elapsed = time.time() - start_time
                    next_frame_time = frame_index * frame_interval
                    if next_frame_time > elapsed:
                        time.sleep(next_frame_time - elapsed)

            if not frames:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="未能捕获任何帧",
                )

            # 计算帧间隔（毫秒）
            duration_ms = int(1000 / fps)

            # 保存为 GIF
            frames[0].save(
                str(output_path),
                save_all=True,
                append_images=frames[1:],
                duration=duration_ms,
                loop=0,
                optimize=True,
            )

            file_size = output_path.stat().st_size
            file_size_kb = file_size / 1024
            actual_duration = len(frames) / fps

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=(
                    f"✅ 屏幕区域录制 GIF 完成\n"
                    f"📁 文件: {output_path.name}\n"
                    f"📏 大小: {file_size_kb:.1f} KB\n"
                    f"📐 区域: ({x}, {y}) - {w}×{h}\n"
                    f"🖼️ 帧数: {len(frames)}\n"
                    f"🎬 帧率: {fps} fps\n"
                    f"⏱️ 时长: {actual_duration:.1f}秒"
                ),
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size_bytes": file_size,
                    "frame_count": len(frames),
                    "fps": fps,
                    "region": {"x": x, "y": y, "width": w, "height": h},
                    "actual_duration": actual_duration,
                },
            )

        except Exception as e:
            logger.error("屏幕区域录制GIF失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"屏幕区域录制GIF失败: {e}",
            )


# 用于测试
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = GifMakerTool()
        print(f"moviepy 已安装: {HAS_MOVIEPY}")

        # 测试 schema 生成
        schemas = tool.get_schema()
        for schema in schemas:
            print(f"  - {schema['function']['name']}: {schema['function']['description']}")

    asyncio.run(test())
