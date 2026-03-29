"""远程文件分享工具 — 桌面端与 PWA 的文件/语音消息互传。

支持动作：
- send_file: 将桌面端本地文件发送到 PWA
- send_files: 将多个本地文件批量发送到 PWA
- send_voice: 将桌面端本地语音文件发送到 PWA（作为语音消息）

依赖：RemoteBridgeClient 实例（通过 set_bridge_client() 延迟注入）
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# 支持的语音文件扩展名
VOICE_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".opus", ".webm"}


class RemoteFileShareTool(BaseTool):
    """远程文件分享工具。

    将桌面端本地文件通过服务器中转发送给 PWA 端用户。
    支持文件消息和语音消息两种模式。

    工作流程：
    1. 调用 RemoteBridgeClient._upload_file_to_remote() 上传文件到服务器
    2. 通过 WebSocket 发送 file_share 消息通知 PWA 端下载
    """

    name = "remote_file_share"
    emoji = "📤"
    title = "远程文件分享"
    description = "将桌面端文件发送到 PWA 端（手机/浏览器），支持文档、图片、语音等所有类型"
    timeout = 180  # 大文件上传可能较慢

    def __init__(self) -> None:
        self._bridge_client = None  # 延迟注入

    def set_bridge_client(self, bridge_client) -> None:
        """注入 RemoteBridgeClient 实例。

        在 GUI 初始化远程桥接后调用，采用与 CronTool.set_agent_dependencies() 相同的模式。

        Args:
            bridge_client: RemoteBridgeClient 实例
        """
        self._bridge_client = bridge_client
        logger.info("RemoteFileShareTool: bridge_client 已注入")

    # ------------------------------------------------------------------
    # Schema 定义
    # ------------------------------------------------------------------

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="send_file",
                description=(
                    "将桌面端本地文件发送到 PWA 端用户。"
                    "支持文档(docx/xlsx/pptx/pdf)、图片(jpg/png)、音频、视频等所有类型。"
                    "当你为远程 PWA 用户生成了文件（如 PPT、报告、图片等），必须调用此工具将结果发送回去。"
                ),
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "要发送的本地文件绝对路径",
                    },
                    "description": {
                        "type": "string",
                        "description": "文件描述（会显示在 PWA 端）",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "目标 PWA 用户 ID（留空则发送给当前会话用户）",
                    },
                },
                required_params=["file_path"],
            ),
            ActionDef(
                name="send_files",
                description=(
                    "将多个桌面端本地文件批量发送到 PWA 端用户。"
                    "适用于同时发送多个相关文件的场景。"
                ),
                parameters={
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要发送的本地文件路径列表",
                    },
                    "message": {
                        "type": "string",
                        "description": "附带的文字说明",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "目标 PWA 用户 ID（留空则发送给当前会话用户）",
                    },
                },
                required_params=["file_paths"],
            ),
            ActionDef(
                name="send_voice",
                description=(
                    "将桌面端本地语音/音频文件作为语音消息发送到 PWA 端。"
                    "PWA 端会以语音消息形式展示，用户可直接播放收听。"
                    "支持格式：mp3, wav, ogg, flac, aac, m4a, opus, webm。"
                ),
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "语音文件的本地绝对路径",
                    },
                    "transcript": {
                        "type": "string",
                        "description": "语音内容的文字转录（可选，方便 PWA 端显示字幕）",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "目标 PWA 用户 ID（留空则发送给当前会话用户）",
                    },
                },
                required_params=["file_path"],
            ),
        ]

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        if action == "send_file":
            return await self._send_file(params)
        elif action == "send_files":
            return await self._send_files(params)
        elif action == "send_voice":
            return await self._send_voice(params)
        else:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"未知动作: {action}")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _check_bridge(self) -> ToolResult | None:
        """检查 bridge_client 是否可用，不可用则返回错误 ToolResult。"""
        if not self._bridge_client:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="远程桥接客户端未初始化，无法发送文件到 PWA。请确认远程连接已启用。",
            )
        if not self._bridge_client.is_connected:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="远程桥接未连接，无法发送文件到 PWA。请检查网络连接或等待重连。",
            )
        return None

    def _resolve_user_id(self, params: dict) -> str:
        """解析目标用户 ID。优先使用参数中的 user_id，否则取第一个在线 PWA 用户。"""
        user_id = params.get("user_id", "")
        if user_id:
            return user_id

        # 自动选取当前在线的 PWA 用户
        if self._bridge_client and self._bridge_client.stats.pwa_connections:
            first_conn = self._bridge_client.stats.pwa_connections[0]
            logger.info(f"自动选取 PWA 用户: {first_conn.user_id[:8]}")
            return first_conn.user_id

        return ""

    async def _send_file(self, params: dict) -> ToolResult:
        """发送单个文件到 PWA。"""
        err = self._check_bridge()
        if err:
            return err

        file_path = params.get("file_path", "")
        if not file_path:
            return ToolResult(status=ToolResultStatus.ERROR, error="未指定文件路径")

        path = Path(file_path)
        if not path.is_file():
            return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")

        user_id = self._resolve_user_id(params)
        if not user_id:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="没有在线的 PWA 用户，无法发送文件。",
            )

        description = params.get("description", path.name)

        success = await self._bridge_client.send_file_to_pwa(
            user_id=user_id,
            file_path=file_path,
            description=description,
        )

        if success:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"文件已发送到 PWA: {path.name}",
                data={"filename": path.name, "user_id": user_id},
            )
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"文件发送失败: {path.name}（可能是上传到服务器失败）",
            )

    async def _send_files(self, params: dict) -> ToolResult:
        """批量发送文件到 PWA。"""
        err = self._check_bridge()
        if err:
            return err

        file_paths = params.get("file_paths", [])
        if not file_paths:
            return ToolResult(status=ToolResultStatus.ERROR, error="未指定文件路径列表")

        # 验证所有文件存在
        valid_paths = []
        missing = []
        for fp in file_paths:
            if Path(fp).is_file():
                valid_paths.append(fp)
            else:
                missing.append(fp)

        if not valid_paths:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"所有文件都不存在: {missing}")

        user_id = self._resolve_user_id(params)
        if not user_id:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="没有在线的 PWA 用户，无法发送文件。",
            )

        message = params.get("message", "")

        success = await self._bridge_client.send_files_to_pwa(
            user_id=user_id,
            file_paths=valid_paths,
            message=message,
        )

        sent_names = [Path(p).name for p in valid_paths]
        output = f"已发送 {len(valid_paths)} 个文件到 PWA: {', '.join(sent_names)}"
        if missing:
            output += f"\n跳过 {len(missing)} 个不存在的文件"

        return ToolResult(
            status=ToolResultStatus.SUCCESS if success else ToolResultStatus.ERROR,
            output=output,
            data={"sent": len(valid_paths), "missing": len(missing)},
        )

    async def _send_voice(self, params: dict) -> ToolResult:
        """发送语音消息到 PWA。"""
        err = self._check_bridge()
        if err:
            return err

        file_path = params.get("file_path", "")
        if not file_path:
            return ToolResult(status=ToolResultStatus.ERROR, error="未指定语音文件路径")

        path = Path(file_path)
        if not path.is_file():
            return ToolResult(status=ToolResultStatus.ERROR, error=f"语音文件不存在: {file_path}")

        # 校验是否为音频文件
        suffix = path.suffix.lower()
        if suffix not in VOICE_EXTENSIONS:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的语音格式: {suffix}，支持: {', '.join(sorted(VOICE_EXTENSIONS))}",
            )

        user_id = self._resolve_user_id(params)
        if not user_id:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="没有在线的 PWA 用户，无法发送语音消息。",
            )

        transcript = params.get("transcript", "")
        description = f"[语音消息] {transcript}" if transcript else "[语音消息]"

        success = await self._bridge_client.send_file_to_pwa(
            user_id=user_id,
            file_path=file_path,
            description=description,
        )

        if success:
            output = f"语音消息已发送到 PWA: {path.name}"
            if transcript:
                output += f" (转录: {transcript[:50]}...)" if len(transcript) > 50 else f" (转录: {transcript})"
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=output,
                data={"filename": path.name, "user_id": user_id, "transcript": transcript},
            )
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"语音消息发送失败: {path.name}",
            )
