"""证件照工具 — 证件照制作、背景替换、尺寸调整、压缩、水印。

支持功能：
- 制作证件照（背景替换 + 尺寸调整）
- 更换背景色（蓝/白/红/自定义）
- 调整标准证件照尺寸
- 压缩照片到指定大小
- 添加文字水印

注意：rembg 为可选依赖，安装后可自动分割人像并替换背景。
未安装时降级为简单处理模式。
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# 尝试导入 rembg（可选依赖）
try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    logger.info("rembg 未安装，证件照工具将使用降级模式")

# 标准证件照尺寸（像素）
PHOTO_SIZES = {
    "one_inch": (295, 413),       # 一寸 25×35mm
    "two_inch": (413, 579),       # 二寸 35×49mm
    "small_one_inch": (260, 378), # 小一寸 22×32mm
    "large_one_inch": (390, 567), # 大一寸 33×48mm
}

# 背景色定义（RGB）
BG_COLORS = {
    "blue": (67, 142, 219),
    "white": (255, 255, 255),
    "red": (220, 36, 31),
}


class IDPhotoTool(BaseTool):
    """证件照制作工具。

    支持：
    - 制作证件照（背景替换 + 尺寸调整）
    - 更换背景色
    - 调整标准证件照尺寸
    - 压缩照片
    - 添加水印
    """

    name = "id_photo"
    emoji = "📷"
    title = "证件照"
    description = "证件照制作：更换背景色、调整标准尺寸、压缩、添加水印"
    timeout = 120

    def __init__(self, output_dir: str = "") -> None:
        """初始化证件照工具。

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
                name="make_id_photo",
                description="制作证件照（背景替换+尺寸调整）",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入照片路径",
                    },
                    "background_color": {
                        "type": "string",
                        "description": "背景色: blue/white/red",
                        "enum": ["blue", "white", "red"],
                    },
                    "size_type": {
                        "type": "string",
                        "description": "尺寸类型: one_inch/two_inch/small_one_inch/large_one_inch",
                        "enum": ["one_inch", "two_inch", "small_one_inch", "large_one_inch"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="change_background",
                description="更换背景色",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入照片路径",
                    },
                    "background_color": {
                        "type": "string",
                        "description": "背景色: blue/white/red/custom",
                        "enum": ["blue", "white", "red", "custom"],
                    },
                    "custom_color": {
                        "type": "string",
                        "description": "自定义RGB颜色，如 '255,200,200'",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["input_path", "background_color"],
            ),
            ActionDef(
                name="resize_photo",
                description="调整到标准证件照尺寸",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入照片路径",
                    },
                    "size_type": {
                        "type": "string",
                        "description": "尺寸类型",
                        "enum": ["one_inch", "two_inch", "small_one_inch", "large_one_inch"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["input_path", "size_type"],
            ),
            ActionDef(
                name="compress_photo",
                description="压缩照片到指定大小",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入照片路径",
                    },
                    "max_size_kb": {
                        "type": "integer",
                        "description": "最大文件大小(KB)，默认200",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="add_watermark",
                description="添加文字水印",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入照片路径",
                    },
                    "text": {
                        "type": "string",
                        "description": "水印文字",
                    },
                    "opacity": {
                        "type": "number",
                        "description": "透明度0-1，默认0.3",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["input_path", "text"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定动作。"""
        action_map = {
            "make_id_photo": self._make_id_photo,
            "change_background": self._change_background,
            "resize_photo": self._resize_photo,
            "compress_photo": self._compress_photo,
            "add_watermark": self._add_watermark,
        }

        handler = action_map.get(action)
        if handler is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}",
            )

        return handler(params)

    def _get_output_path(self, params: dict, prefix: str, ext: str = "jpg") -> Path:
        """生成输出文件路径。"""
        filename = params.get("output_filename", "").strip()
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}"
        return self.output_dir / f"{filename}.{ext}"

    def _validate_input_path(self, params: dict) -> tuple[Path | None, ToolResult | None]:
        """验证输入路径。返回 (路径, 错误结果)。"""
        input_path_str = params.get("input_path", "").strip()
        if not input_path_str:
            return None, ToolResult(
                status=ToolResultStatus.ERROR,
                error="请提供输入照片路径",
            )

        input_path = Path(input_path_str)
        if not input_path.exists():
            return None, ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"文件不存在: {input_path}",
            )

        return input_path, None

    def _make_id_photo(self, params: dict[str, Any]) -> ToolResult:
        """制作证件照（背景替换 + 尺寸调整）。"""
        input_path, error = self._validate_input_path(params)
        if error:
            return error

        bg_color_name = params.get("background_color", "blue")
        size_type = params.get("size_type", "one_inch")
        output_path = self._get_output_path(params, "id_photo")

        try:
            img = Image.open(str(input_path)).convert("RGBA")
            rembg_used = False

            if HAS_REMBG:
                # 使用 rembg 去除背景
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                result_bytes = rembg_remove(img_bytes.getvalue())
                img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

                # 创建纯色背景
                bg_rgb = BG_COLORS.get(bg_color_name, BG_COLORS["blue"])
                bg = Image.new("RGBA", img.size, bg_rgb + (255,))
                bg.paste(img, (0, 0), img)
                img = bg.convert("RGB")
                rembg_used = True
            else:
                img = img.convert("RGB")

            # 调整尺寸
            target_size = PHOTO_SIZES.get(size_type, PHOTO_SIZES["one_inch"])
            img = img.resize(target_size, Image.Resampling.LANCZOS)

            # 保存
            img.save(str(output_path), "JPEG", quality=95)

            size_name_map = {
                "one_inch": "一寸",
                "two_inch": "二寸",
                "small_one_inch": "小一寸",
                "large_one_inch": "大一寸",
            }
            size_name = size_name_map.get(size_type, size_type)
            bg_name_map = {"blue": "蓝色", "white": "白色", "red": "红色"}
            bg_name = bg_name_map.get(bg_color_name, bg_color_name)

            msg = f"✅ 证件照制作完成\n📁 文件: {output_path.name}\n📏 尺寸: {size_name} ({target_size[0]}×{target_size[1]})\n🎨 背景: {bg_name}"
            if not rembg_used:
                msg += "\n⚠️ 提示: 未安装 rembg，已跳过背景替换。安装 rembg 可自动分割人像并替换背景"

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=msg,
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "size_type": size_type,
                    "size_pixels": target_size,
                    "background_color": bg_color_name,
                    "rembg_used": rembg_used,
                },
            )

        except Exception as e:
            logger.error("制作证件照失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"制作证件照失败: {e}",
            )

    def _change_background(self, params: dict[str, Any]) -> ToolResult:
        """更换背景色。"""
        input_path, error = self._validate_input_path(params)
        if error:
            return error

        bg_color_name = params.get("background_color", "blue")
        custom_color_str = params.get("custom_color", "").strip()
        output_path = self._get_output_path(params, "bg_changed")

        # 解析背景色
        if bg_color_name == "custom" and custom_color_str:
            try:
                parts = [int(x.strip()) for x in custom_color_str.split(",")]
                if len(parts) != 3:
                    raise ValueError("需要3个RGB值")
                bg_rgb = tuple(parts)
            except Exception as e:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"自定义颜色格式错误: {e}。请使用 'R,G,B' 格式，如 '255,200,200'",
                )
        else:
            bg_rgb = BG_COLORS.get(bg_color_name, BG_COLORS["blue"])

        try:
            img = Image.open(str(input_path)).convert("RGBA")
            rembg_used = False

            if HAS_REMBG:
                # 使用 rembg 去除背景
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                result_bytes = rembg_remove(img_bytes.getvalue())
                img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

                # 创建纯色背景
                bg = Image.new("RGBA", img.size, bg_rgb + (255,))
                bg.paste(img, (0, 0), img)
                img = bg.convert("RGB")
                rembg_used = True
            else:
                # 降级：尝试简单的颜色替换（替换接近纯色的背景）
                img = self._simple_background_replace(img, bg_rgb)

            # 保存
            img.save(str(output_path), "JPEG", quality=95)

            bg_desc = f"RGB({bg_rgb[0]},{bg_rgb[1]},{bg_rgb[2]})" if bg_color_name == "custom" else bg_color_name
            msg = f"✅ 背景更换完成\n📁 文件: {output_path.name}\n🎨 新背景: {bg_desc}"
            if not rembg_used:
                msg += "\n⚠️ 提示: 未安装 rembg，使用简单颜色替换模式。安装 rembg 可获得更精准的效果"

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=msg,
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "background_color": bg_color_name,
                    "background_rgb": bg_rgb,
                    "rembg_used": rembg_used,
                },
            )

        except Exception as e:
            logger.error("更换背景失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"更换背景失败: {e}",
            )

    def _simple_background_replace(self, img: Image.Image, new_bg_rgb: tuple) -> Image.Image:
        """简单的背景替换（降级模式）。

        尝试检测并替换接近纯色的背景区域。
        """
        img_rgb = img.convert("RGB")
        pixels = img_rgb.load()
        width, height = img_rgb.size

        # 采样四角获取可能的背景色
        corner_pixels = [
            pixels[0, 0],
            pixels[width - 1, 0],
            pixels[0, height - 1],
            pixels[width - 1, height - 1],
        ]

        # 计算平均背景色
        avg_r = sum(p[0] for p in corner_pixels) // 4
        avg_g = sum(p[1] for p in corner_pixels) // 4
        avg_b = sum(p[2] for p in corner_pixels) // 4
        detected_bg = (avg_r, avg_g, avg_b)

        # 替换相似颜色的像素
        threshold = 50  # 颜色相似度阈值
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                if (abs(r - detected_bg[0]) < threshold and
                    abs(g - detected_bg[1]) < threshold and
                    abs(b - detected_bg[2]) < threshold):
                    pixels[x, y] = new_bg_rgb

        return img_rgb

    def _resize_photo(self, params: dict[str, Any]) -> ToolResult:
        """调整到标准证件照尺寸。"""
        input_path, error = self._validate_input_path(params)
        if error:
            return error

        size_type = params.get("size_type", "one_inch")
        output_path = self._get_output_path(params, "resized")

        if size_type not in PHOTO_SIZES:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的尺寸类型: {size_type}。支持: {', '.join(PHOTO_SIZES.keys())}",
            )

        try:
            img = Image.open(str(input_path))

            # 转换为 RGB（处理 PNG 等格式）
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 调整尺寸
            target_size = PHOTO_SIZES[size_type]
            img = img.resize(target_size, Image.Resampling.LANCZOS)

            # 保存
            img.save(str(output_path), "JPEG", quality=95)

            size_name_map = {
                "one_inch": "一寸 (25×35mm)",
                "two_inch": "二寸 (35×49mm)",
                "small_one_inch": "小一寸 (22×32mm)",
                "large_one_inch": "大一寸 (33×48mm)",
            }
            size_name = size_name_map.get(size_type, size_type)

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ 尺寸调整完成\n📁 文件: {output_path.name}\n📏 尺寸: {size_name}\n📐 像素: {target_size[0]}×{target_size[1]}",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "size_type": size_type,
                    "size_pixels": target_size,
                },
            )

        except Exception as e:
            logger.error("调整尺寸失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"调整尺寸失败: {e}",
            )

    def _compress_photo(self, params: dict[str, Any]) -> ToolResult:
        """压缩照片到指定大小。"""
        input_path, error = self._validate_input_path(params)
        if error:
            return error

        max_size_kb = int(params.get("max_size_kb", 200))
        output_path = self._get_output_path(params, "compressed")

        try:
            img = Image.open(str(input_path))

            # 转换为 RGB
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 二分法找到合适的质量参数
            quality = 95
            best_quality = quality
            best_buffer = None

            while quality > 10:
                buffer = io.BytesIO()
                img.save(buffer, "JPEG", quality=quality)
                size_bytes = buffer.tell()

                if size_bytes <= max_size_kb * 1024:
                    best_quality = quality
                    best_buffer = buffer
                    break

                quality -= 5
            else:
                # 即使最低质量也无法达到目标，使用最后的结果
                buffer = io.BytesIO()
                img.save(buffer, "JPEG", quality=10)
                best_quality = 10
                best_buffer = buffer

            # 保存最终结果
            best_buffer.seek(0)
            with open(output_path, "wb") as f:
                f.write(best_buffer.read())

            final_size = output_path.stat().st_size
            final_size_kb = final_size / 1024

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ 照片压缩完成\n📁 文件: {output_path.name}\n📊 大小: {final_size_kb:.1f} KB\n🎚️ 质量: {best_quality}%",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size_bytes": final_size,
                    "file_size_kb": round(final_size_kb, 1),
                    "quality": best_quality,
                },
            )

        except Exception as e:
            logger.error("压缩照片失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"压缩照片失败: {e}",
            )

    def _add_watermark(self, params: dict[str, Any]) -> ToolResult:
        """添加文字水印。"""
        from PIL import ImageDraw, ImageFont

        input_path, error = self._validate_input_path(params)
        if error:
            return error

        text = params.get("text", "").strip()
        if not text:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="请提供水印文字",
            )

        opacity = float(params.get("opacity", 0.3))
        opacity = max(0, min(1, opacity))  # 限制在 0-1 范围
        output_path = self._get_output_path(params, "watermarked")

        try:
            img = Image.open(str(input_path)).convert("RGBA")

            # 创建水印层
            watermark = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark)

            # 尝试使用系统字体
            font_size = max(16, min(img.width, img.height) // 20)
            font = None
            font_paths = [
                "msyh.ttc",     # 微软雅黑
                "simhei.ttf",   # 黑体
                "simsun.ttc",   # 宋体
                "arial.ttf",    # Arial
            ]
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except Exception:
                    continue

            if font is None:
                font = ImageFont.load_default()

            # 计算水印文字大小
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # 计算透明度值
            opacity_val = int(opacity * 255)

            # 对角线重复绘制水印
            spacing_x = text_width + 50
            spacing_y = text_height + 80

            for y in range(-text_height, img.height + text_height, spacing_y):
                for x in range(-text_width, img.width + text_width, spacing_x):
                    draw.text(
                        (x, y),
                        text,
                        font=font,
                        fill=(128, 128, 128, opacity_val),
                    )

            # 合成图像
            result = Image.alpha_composite(img, watermark)
            result = result.convert("RGB")

            # 保存
            result.save(str(output_path), "JPEG", quality=95)

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ 水印添加完成\n📁 文件: {output_path.name}\n💬 水印: {text}\n🔍 透明度: {opacity:.0%}",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "watermark_text": text,
                    "opacity": opacity,
                },
            )

        except Exception as e:
            logger.error("添加水印失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"添加水印失败: {e}",
            )


# 用于测试
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = IDPhotoTool()
        print(f"rembg 已安装: {HAS_REMBG}")
        print("支持的尺寸:", list(PHOTO_SIZES.keys()))
        print("支持的背景色:", list(BG_COLORS.keys()))

        # 测试 schema 生成
        schemas = tool.get_schema()
        for schema in schemas:
            print(f"  - {schema['function']['name']}: {schema['function']['description']}")

    asyncio.run(test())
