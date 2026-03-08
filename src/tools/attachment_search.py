"""远程附件搜索工具

让 Agent 能够搜索用户的历史附件，支持：
- 按关键词搜索（文件名、描述、OCR文字）
- 按时间范围搜索
- 获取附件详情并再次分析
- 区分当前对话和历史对话的附件

重要设计原则：
- 当前对话的附件：用户刚刚上传的，不需要搜索，直接在消息中携带
- 历史对话的附件：需要通过此工具搜索，来自之前的对话

使用场景：
- "我昨天上传的关于拙政园的图片" → 搜索历史附件
- "找一下我之前上传的那张截图" → 搜索历史附件
- "重新分析我上周的那张报表图片" → 搜索历史附件
"""

import logging
from typing import Any

from .base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class AttachmentSearchTool(BaseTool):
    """远程附件搜索工具
    
    用于搜索历史对话中的附件。当前对话的附件会直接在消息中携带，
    不需要使用此工具。
    """

    name = "attachment_search"
    emoji = "🔍"
    title = "历史附件搜索"
    description = "搜索用户在【历史对话】中上传的附件。注意：当前对话的附件已在消息中，无需搜索。"

    def __init__(self, user_id: str = "", session_id: str = ""):
        super().__init__()
        self._user_id = user_id      # 当前用户 ID
        self._session_id = session_id  # 当前会话 ID（用于区分历史附件）

    def set_user_id(self, user_id: str) -> None:
        """设置当前用户 ID"""
        self._user_id = user_id
    
    def set_session_id(self, session_id: str) -> None:
        """设置当前会话 ID"""
        self._session_id = session_id

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="search_history",
                description="搜索【历史对话】中的附件（排除当前对话）。支持按文件名、描述、OCR文字模糊搜索。",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如'拙政园'、'报表'、'截图'等",
                    },
                    "file_type": {
                        "type": "string",
                        "description": "文件类型过滤: image/audio/file，默认 image",
                        "default": "image",
                    },
                    "days": {
                        "type": "integer",
                        "description": "搜索最近N天的附件，默认30天",
                        "default": 30,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量限制，默认5",
                        "default": 5,
                    },
                },
                required_params=["query"],
            ),
            ActionDef(
                name="get_current_session",
                description="获取【当前对话】中已上传的所有附件列表（通常不需要调用，因为当前附件已在消息中）",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="get_recent",
                description="获取最近上传的附件列表（包含所有对话）",
                parameters={
                    "file_type": {
                        "type": "string",
                        "description": "文件类型过滤: image/audio/file，留空则全部",
                        "default": "",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量，默认10",
                        "default": 10,
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="get_detail",
                description="获取附件详情，包含本地路径（可用于OCR等工具分析）",
                parameters={
                    "attachment_id": {
                        "type": "string",
                        "description": "附件ID",
                    },
                },
                required_params=["attachment_id"],
            ),
            ActionDef(
                name="stats",
                description="获取附件存储统计信息",
                parameters={},
                required_params=[],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行附件搜索操作"""
        if action == "search_history":
            return await self._search_history(**params)
        elif action == "get_current_session":
            return await self._get_current_session()
        elif action == "get_recent":
            return await self._get_recent(**params)
        elif action == "get_detail":
            return await self._get_detail(**params)
        elif action == "stats":
            return await self._get_stats()
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未知动作: {action}",
                output=f"可用动作: {[a.name for a in self.get_actions()]}",
            )

    async def _search_history(
        self,
        query: str,
        file_type: str = "image",
        days: int = 30,
        limit: int = 5,
    ) -> ToolResult:
        """搜索历史对话中的附件（排除当前对话）"""
        try:
            from src.remote_client.attachment_storage import get_attachment_storage
            
            storage = get_attachment_storage()
            
            if not self._user_id:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="未设置用户ID，无法搜索附件",
                )
            
            # 【关键】使用排除当前会话的搜索方法
            if self._session_id:
                attachments = storage.get_other_session_attachments(
                    user_id=self._user_id,
                    current_session_id=self._session_id,
                    query=query,
                    limit=limit,
                )
            else:
                # 如果没有当前会话ID，退化为普通搜索
                attachments = storage.search_attachments(
                    user_id=self._user_id,
                    query=query,
                    file_type=file_type,
                    days=days,
                    limit=limit,
                )
            
            if not attachments:
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output=f"在历史对话中未找到匹配'{query}'的附件",
                    data={"attachments": [], "count": 0, "scope": "历史对话"},
                )
            
            # 构建结果
            results = []
            for att in attachments:
                results.append({
                    "id": att.id,
                    "filename": att.filename,
                    "file_type": att.file_type,
                    "local_path": att.local_path,  # 关键：本地路径可用于 OCR
                    "session_id": att.session_id[:16] + "...",  # 显示会话ID前缀
                    "description": att.description,
                    "created_at": att.created_at.strftime("%Y-%m-%d %H:%M"),
                    "access_count": att.access_count,
                })
            
            output_lines = [
                f"在【历史对话】中找到 {len(results)} 个匹配'{query}'的附件：",
                "（这些附件来自之前的对话，不是当前对话）\n"
            ]
            for i, r in enumerate(results, 1):
                output_lines.append(f"{i}. {r['filename']}")
                output_lines.append(f"   - 路径: {r['local_path']}")
                output_lines.append(f"   - 来自会话: {r['session_id']}")
                output_lines.append(f"   - 描述: {r['description'][:50] if r['description'] else '无'}...")
                output_lines.append(f"   - 上传时间: {r['created_at']}")
                output_lines.append("")
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="\n".join(output_lines),
                data={"attachments": results, "count": len(results), "scope": "历史对话"},
            )
            
        except ImportError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="附件存储模块未安装",
            )
        except Exception as e:
            logger.error(f"搜索附件失败: {e}", exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"搜索附件失败: {e}",
            )

    async def _get_current_session(self) -> ToolResult:
        """获取当前对话中的附件"""
        try:
            from src.remote_client.attachment_storage import get_attachment_storage
            
            storage = get_attachment_storage()
            
            if not self._user_id or not self._session_id:
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output="当前对话中暂无已存储的附件（当前上传的附件直接在消息中携带）",
                    data={"attachments": [], "count": 0, "scope": "当前对话"},
                )
            
            attachments = storage.get_session_attachments(
                user_id=self._user_id,
                session_id=self._session_id,
            )
            
            if not attachments:
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output="当前对话中暂无已存储的附件",
                    data={"attachments": [], "count": 0, "scope": "当前对话"},
                )
            
            results = []
            for att in attachments:
                results.append({
                    "id": att.id,
                    "filename": att.filename,
                    "file_type": att.file_type,
                    "local_path": att.local_path,
                    "description": att.description[:50] if att.description else "",
                    "created_at": att.created_at.strftime("%Y-%m-%d %H:%M"),
                })
            
            output_lines = [
                f"【当前对话】中已上传 {len(results)} 个附件：",
                f"（会话ID: {self._session_id[:16]}...）\n"
            ]
            for i, r in enumerate(results, 1):
                output_lines.append(f"{i}. {r['filename']} ({r['created_at']})")
                output_lines.append(f"   路径: {r['local_path']}")
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="\n".join(output_lines),
                data={"attachments": results, "count": len(results), "scope": "当前对话"},
            )
            
        except Exception as e:
            logger.error(f"获取当前会话附件失败: {e}", exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"获取当前会话附件失败: {e}",
            )

    async def _get_recent(
        self,
        file_type: str = "",
        limit: int = 10,
    ) -> ToolResult:
        """获取最近的附件"""
        try:
            from src.remote_client.attachment_storage import get_attachment_storage
            
            storage = get_attachment_storage()
            
            if not self._user_id:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="未设置用户ID，无法获取附件",
                )
            
            attachments = storage.get_recent_attachments(
                user_id=self._user_id,
                file_type=file_type,
                limit=limit,
            )
            
            if not attachments:
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output="暂无上传的附件",
                    data={"attachments": [], "count": 0},
                )
            
            results = []
            for att in attachments:
                results.append({
                    "id": att.id,
                    "filename": att.filename,
                    "file_type": att.file_type,
                    "local_path": att.local_path,
                    "description": att.description[:50] if att.description else "",
                    "created_at": att.created_at.strftime("%Y-%m-%d %H:%M"),
                })
            
            output_lines = [f"最近上传的 {len(results)} 个附件：\n"]
            for i, r in enumerate(results, 1):
                output_lines.append(f"{i}. {r['filename']} ({r['created_at']})")
                output_lines.append(f"   路径: {r['local_path']}")
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="\n".join(output_lines),
                data={"attachments": results, "count": len(results)},
            )
            
        except Exception as e:
            logger.error(f"获取最近附件失败: {e}", exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"获取最近附件失败: {e}",
            )

    async def _get_detail(self, attachment_id: str) -> ToolResult:
        """获取附件详情"""
        try:
            from src.remote_client.attachment_storage import get_attachment_storage
            from pathlib import Path
            
            storage = get_attachment_storage()
            
            attachment = storage.get_attachment(attachment_id)
            if not attachment:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"附件不存在: {attachment_id}",
                )
            
            # 更新访问记录
            storage.update_access(attachment_id)
            
            # 检查本地文件是否存在
            local_exists = Path(attachment.local_path).exists()
            
            output = f"""附件详情:
- 文件名: {attachment.filename}
- 类型: {attachment.file_type}
- 本地路径: {attachment.local_path}
- 文件存在: {'是' if local_exists else '否（需要重新下载）'}
- 描述: {attachment.description}
- OCR文字: {attachment.ocr_text[:100] + '...' if len(attachment.ocr_text) > 100 else attachment.ocr_text}
- 上传时间: {attachment.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- 访问次数: {attachment.access_count}
"""
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=output,
                data={
                    "attachment": attachment.to_dict(),
                    "local_exists": local_exists,
                },
            )
            
        except Exception as e:
            logger.error(f"获取附件详情失败: {e}", exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"获取附件详情失败: {e}",
            )

    async def _get_stats(self) -> ToolResult:
        """获取存储统计"""
        try:
            from src.remote_client.attachment_storage import get_attachment_storage
            
            storage = get_attachment_storage()
            stats = storage.get_cache_stats()
            
            type_info = ", ".join([f"{k}: {v}" for k, v in stats.get("by_type", {}).items()])
            
            output = f"""附件存储统计:
- 总数量: {stats['total_count']} 个
- 总大小: {stats['total_size_mb']} MB
- 类型分布: {type_info}
- 缓存目录: {stats['cache_dir']}
- 最早上传: {stats['oldest_created']}
- 最近访问: {stats['newest_accessed']}
"""
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=output,
                data=stats,
            )
            
        except Exception as e:
            logger.error(f"获取统计失败: {e}", exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"获取统计失败: {e}",
            )
