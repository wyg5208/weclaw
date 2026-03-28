"""
OCR 工具 - 基于 RapidOCR 的文字识别

支持:
- 图片文字识别 (截图、照片等)
- 批量识别
- 多语言支持
- 高准确率的离线识别
- 截图+OCR 一体化操作

Phase 4.6 优化：
- 延迟导入：RapidOCR/PIL 仅在实际使用时导入
- 启动速度大幅提升

Phase 4.7 增强：
- 新增 recognize_screenshot 动作：截图并识别文字（一步完成）
"""
import asyncio
import io
import logging
from pathlib import Path
from typing import Any

# 延迟导入标记
OCR_AVAILABLE: bool | None = None

# 模块引用（延迟加载后赋值）
_RapidOCR = None
_Image = None
_mss = None

logger = logging.getLogger(__name__)


def _check_ocr_dependencies() -> bool:
    """检查 OCR 依赖是否可用，延迟导入。"""
    global OCR_AVAILABLE, _RapidOCR, _Image, _mss
    if OCR_AVAILABLE is not None:
        return OCR_AVAILABLE

    try:
        from rapidocr_onnxruntime import RapidOCR
        from PIL import Image
        import mss

        _RapidOCR = RapidOCR
        _Image = Image
        _mss = mss
        OCR_AVAILABLE = True
    except ImportError:
        OCR_AVAILABLE = False

    return OCR_AVAILABLE


from .base import ActionDef, BaseTool, ToolResult, ToolResultStatus


class OCRTool(BaseTool):
    """OCR 文字识别工具"""

    name = "ocr"
    emoji = "📝"
    title = "文字识别"
    description = "图片文字识别工具,支持截图和照片识别"

    def __init__(self):
        super().__init__()
        self._ocr_engine = None
        self._cache = None  # Phase 2: 延迟初始化缓存
        # 不在初始化时检查依赖，延迟到实际使用时

    def _get_cache(self):
        """延迟加载缓存管理器（Phase 2）"""
        if self._cache is None:
            try:
                from src.core.cache.file_cache import FileCacheManager
                self._cache = FileCacheManager()
            except ImportError:
                logger.warning("缓存管理器不可用，跳过缓存")
                self._cache = False
        return self._cache if self._cache else None

    def _check_available(self) -> bool:
        """检查 OCR 功能是否可用。"""
        if not _check_ocr_dependencies():
            raise ImportError("OCR 功能不可用。请安装依赖: pip install rapidocr-onnxruntime pillow")
        return True

    def _get_engine(self):
        """延迟加载 OCR 引擎"""
        self._check_available()
        if self._ocr_engine is None:
            self._ocr_engine = _RapidOCR()
        return self._ocr_engine

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="recognize_file",
                description="识别图片文件中的文字",
                parameters={
                    "image_path": {
                        "type": "string",
                        "description": "图片文件路径 (支持 jpg/png/bmp 等)",
                    },
                    "merge_lines": {
                        "type": "boolean",
                        "description": "是否合并多行文本,默认 True",
                        "default": True,
                    },
                },
                required_params=["image_path"],
            ),
            ActionDef(
                name="recognize_region",
                description="识别图片指定区域的文字",
                parameters={
                    "image_path": {
                        "type": "string",
                        "description": "图片文件路径",
                    },
                    "x": {"type": "integer", "description": "区域左上角 X 坐标"},
                    "y": {"type": "integer", "description": "区域左上角 Y 坐标"},
                    "width": {"type": "integer", "description": "区域宽度"},
                    "height": {"type": "integer", "description": "区域高度"},
                    "merge_lines": {
                        "type": "boolean",
                        "description": "是否合并多行",
                        "default": True,
                    },
                },
                required_params=["image_path", "x", "y", "width", "height"],
            ),
            ActionDef(
                name="recognize_screenshot",
                description="截取屏幕并识别文字（一步完成）。支持全屏或指定区域截图后立即OCR识别。",
                parameters={
                    "monitor": {
                        "type": "integer",
                        "description": "显示器编号（0=全部, 1=主显示器, 2=第二显示器...）。默认1。",
                        "default": 1,
                    },
                    "region": {
                        "type": "object",
                        "description": "截图区域（可选）。不指定则截取全屏。",
                        "properties": {
                            "left": {"type": "integer", "description": "左上角 X 坐标"},
                            "top": {"type": "integer", "description": "左上角 Y 坐标"},
                            "width": {"type": "integer", "description": "宽度"},
                            "height": {"type": "integer", "description": "高度"},
                        },
                    },
                    "merge_lines": {
                        "type": "boolean",
                        "description": "是否合并多行文本,默认 True",
                        "default": True,
                    },
                },
                required_params=[],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行 OCR 操作"""
        if action == "recognize_file":
            return await self._recognize_file(**params)
        elif action == "recognize_region":
            return await self._recognize_region(**params)
        elif action == "recognize_screenshot":
            return await self._recognize_screenshot(**params)
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未知动作: {action}",
                output=f"可用动作: {[a.name for a in self.get_actions()]}",
            )

    async def _recognize_file(self, image_path: str, merge_lines: bool = True) -> ToolResult:
        """识别整个图片的文字（Phase 2 增强：支持缓存）"""
        try:
            path = Path(image_path).expanduser().resolve()
            if not path.exists():
                return ToolResult(status=ToolResultStatus.ERROR, error=f"图片文件不存在: {image_path}")

            # 检查文件大小 (限制 20MB)
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > 20:
                return ToolResult(
                    status=ToolResultStatus.ERROR, error=f"图片过大: {file_size_mb:.1f}MB (限制 20MB)"
                )

            # Phase 2: 尝试从缓存获取
            cache = self._get_cache()
            file_hash = FileCacheManager.compute_hash(str(path)) if cache else None
            cached = None
            if cache and file_hash:
                cached = await cache.get(file_hash, "ocr")
                if cached:
                    logger.info(f"OCR缓存命中: {path.name}")
                    full_text = cached.get("text", "")
                    boxes = cached.get("boxes", [])
                    output = f"识别成功(缓存): {len(boxes)} 行文字\n\n{full_text}"
                    return ToolResult(
                        status=ToolResultStatus.SUCCESS,
                        output=output,
                        data={"text": full_text, "boxes": boxes, "line_count": len(boxes), "cached": True},
                    )

            # 在线程池中执行 OCR
            loop = asyncio.get_event_loop()
            ocr_engine = self._get_engine()
            result = await loop.run_in_executor(None, ocr_engine, str(path))

            if result is None or len(result) == 0:
                return ToolResult(
                    status=ToolResultStatus.SUCCESS, output="未识别到文字", data={"text": "", "boxes": []}
                )

            # 解析结果
            text_lines = []
            boxes = []

            for line in result[0]:
                if line:
                    box = line[0]  # 坐标框
                    text = line[1]  # 识别文字
                    confidence = line[2]  # 置信度

                    text_lines.append(text)
                    boxes.append(
                        {"text": text, "confidence": float(confidence), "box": [[int(x), int(y)] for x, y in box]}
                    )

            # 合并文本
            full_text = "\n".join(text_lines) if not merge_lines else " ".join(text_lines)

            # output 包含完整识别文字，便于 AI 模型直接使用
            output = f"识别成功: {len(text_lines)} 行文字\n\n{full_text}"

            # Phase 2: 保存到缓存
            if cache and file_hash:
                await cache.set(file_hash, "ocr", {"text": full_text, "boxes": boxes})

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=output,
                data={"text": full_text, "boxes": boxes, "line_count": len(text_lines)},
            )

        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"识别失败: {e}")

    async def _recognize_region(
        self, image_path: str, x: int, y: int, width: int, height: int, merge_lines: bool = True
    ) -> ToolResult:
        """识别图片指定区域的文字"""
        try:
            path = Path(image_path).expanduser().resolve()
            if not path.exists():
                return ToolResult(status=ToolResultStatus.ERROR, error=f"图片文件不存在: {image_path}")

            self._check_available()

            # 裁剪图片区域
            loop = asyncio.get_event_loop()

            def crop_image():
                img = _Image.open(path)
                region = img.crop((x, y, x + width, y + height))
                return region

            region_img = await loop.run_in_executor(None, crop_image)

            # OCR 识别
            ocr_engine = self._get_engine()
            result = await loop.run_in_executor(None, ocr_engine, region_img)

            if result is None or len(result) == 0:
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output="区域内未识别到文字",
                    data={"text": "", "region": {"x": x, "y": y, "width": width, "height": height}},
                )

            # 解析结果
            text_lines = []
            boxes = []

            for line in result[0]:
                if line:
                    box = line[0]
                    text = line[1]
                    confidence = line[2]

                    text_lines.append(text)
                    # 坐标偏移
                    adjusted_box = [[int(px + x), int(py + y)] for px, py in box]
                    boxes.append({"text": text, "confidence": float(confidence), "box": adjusted_box})

            full_text = "\n".join(text_lines) if not merge_lines else " ".join(text_lines)

            # output 包含完整识别文字
            output = f"区域识别成功: {len(text_lines)} 行文字\n\n{full_text}"

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=output,
                data={
                    "text": full_text,
                    "boxes": boxes,
                    "line_count": len(text_lines),
                    "region": {"x": x, "y": y, "width": width, "height": height},
                },
            )

        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"区域识别失败: {e}")

    async def _recognize_screenshot(
        self,
        monitor: int = 1,
        region: dict[str, int] | None = None,
        merge_lines: bool = True,
    ) -> ToolResult:
        """截取屏幕并识别文字（一步完成）。

        Args:
            monitor: 显示器编号（1=主显示器）
            region: 截图区域（可选）
            merge_lines: 是否合并多行文本
        """
        try:
            self._check_available()

            # 执行截图
            def capture_screen():
                with _mss.mss() as sct:
                    if region:
                        grab_area = {
                            "left": region.get("left", 0),
                            "top": region.get("top", 0),
                            "width": region.get("width", 800),
                            "height": region.get("height", 600),
                        }
                    else:
                        if monitor < 0 or monitor >= len(sct.monitors):
                            monitor = 1
                        mon = sct.monitors[monitor]
                        grab_area = {"left": mon["left"], "top": mon["top"],
                                     "width": mon["width"], "height": mon["height"]}

                    screenshot = sct.grab(grab_area)
                    img = _Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    return img

            loop = asyncio.get_event_loop()
            img = await loop.run_in_executor(None, capture_screen)

            logger.info("截图完成: %dx%d", img.width, img.height)

            # 执行 OCR
            ocr_engine = self._get_engine()
            result = await loop.run_in_executor(None, ocr_engine, img)

            if result is None or len(result) == 0:
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output="截图完成但未识别到文字",
                    data={"text": "", "boxes": [], "screenshot_size": {"width": img.width, "height": img.height}},
                )

            # 解析结果
            text_lines = []
            boxes = []

            for line in result[0]:
                if line:
                    box = line[0]
                    text = line[1]
                    confidence = line[2]

                    text_lines.append(text)
                    boxes.append({
                        "text": text,
                        "confidence": float(confidence),
                        "box": [[int(x), int(y)] for x, y in box]
                    })

            full_text = "\n".join(text_lines) if not merge_lines else " ".join(text_lines)

            # output 包含完整识别文字
            output = f"截图OCR成功: {len(text_lines)} 行文字 ({img.width}x{img.height})\n\n{full_text}"

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=output,
                data={
                    "text": full_text,
                    "boxes": boxes,
                    "line_count": len(text_lines),
                    "screenshot_size": {"width": img.width, "height": img.height},
                },
            )

        except Exception as e:
            logger.exception("截图OCR失败")
            return ToolResult(status=ToolResultStatus.ERROR, error=f"截图OCR失败: {e}")
