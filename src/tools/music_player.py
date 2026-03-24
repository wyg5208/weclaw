"""歌曲库管理工具 - 支持音乐播放、标签管理、播放列表等功能。

核心功能：
- 音乐播放控制（播放、暂停，切歌、循环、随机）
- 歌曲库管理（添加、删除、搜索、扫描本地）
- 标签系统（内置标签 + 自定义标签）
- 播放列表管理
- Audio Ducking（与 TTS 协调）

使用 QtMultimedia（PySide6 内置）作为音频引擎。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus
from src.tools.music_player_controller import get_player_controller

logger = logging.getLogger(__name__)

# 支持的音频格式
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac"}

# 内置标签定义
BUILTIN_TAGS = {
    # 风格标签
    "轻音乐": {"color": "#4CAF50", "category": "style"},
    "古典": {"color": "#9C27B0", "category": "style"},
    "流行": {"color": "#2196F3", "category": "style"},
    "摇滚": {"color": "#F44336", "category": "style"},
    "爵士": {"color": "#FF9800", "category": "style"},
    "电子": {"color": "#00BCD4", "category": "style"},
    "民乐": {"color": "#795548", "category": "style"},
    "说唱": {"color": "#7C4DFF", "category": "style"},
    "R&B": {"color": "#E040FB", "category": "style"},
    # 情绪标签
    "治愈": {"color": "#E91E63", "category": "mood"},
    "欢快": {"color": "#FFEB3B", "category": "mood"},
    "平静": {"color": "#03A9F4", "category": "mood"},
    "悲伤": {"color": "#3F51B5", "category": "mood"},
    "浪漫": {"color": "#F48FB1", "category": "mood"},
    "激励": {"color": "#FF5722", "category": "mood"},
    "忧郁": {"color": "#5C6BC0", "category": "mood"},
    # 场景标签
    "工作专注": {"color": "#607D8B", "category": "scene"},
    "运动健身": {"color": "#8BC34A", "category": "scene"},
    "睡眠": {"color": "#3F51B5", "category": "scene"},
    "冥想": {"color": "#26A69A", "category": "scene"},
    "读书": {"color": "#7986CB", "category": "scene"},
    "派对": {"color": "#FF4081", "category": "scene"},
    # 乐器标签
    "钢琴曲": {"color": "#9E9E9E", "category": "instrument"},
    "吉他曲": {"color": "#8D6E63", "category": "instrument"},
    "提琴曲": {"color": "#6D4C41", "category": "instrument"},
    "古筝曲": {"color": "#A1887F", "category": "instrument"},
    "笛子": {"color": "#BCAAA4", "category": "instrument"},
}


class MusicPlayerTool(BaseTool):
    """歌曲库管理工具 - 提供音乐播放和管理功能。"""

    name = "music_player"
    emoji = "🎵"
    title = "歌曲库"
    description = "歌曲库管理：播放音乐、管理标签、创建播放列表、扫描本地音乐"
    timeout = 300  # 5 分钟超时（扫描可能较慢）

    def __init__(self, library_dir: str = ""):
        """初始化歌曲库工具。

        Args:
            library_dir: 歌曲库数据目录路径，默认为 .qoder/data/music_library
        """
        super().__init__()
        
        # 设置数据目录
        if library_dir:
            self._library_dir = Path(library_dir)
        else:
            # 默认路径：项目根目录/.qoder/data/music_library
            self._library_dir = Path(__file__).parent.parent.parent / ".qoder" / "data" / "music_library"
        
        self._music_dir = self._library_dir / "music"
        self._library_file = self._library_dir / "library.json"
        
        # 确保目录存在
        self._library_dir.mkdir(parents=True, exist_ok=True)
        self._music_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载歌曲库数据
        self._library_data = self._load_library()
        
        # 播放器状态（与 UI 共享）
        self._player_state = {
            "is_playing": False,
            "is_paused": False,
            "current_song_id": None,
            "current_position": 0.0,
            "volume": self._library_data.get("settings", {}).get("volume", 0.8),
        }
        
        # 获取播放器控制器
        self._controller = get_player_controller()
        
        logger.info(f"MusicPlayerTool 初始化完成，歌曲库路径: {self._library_dir}")

    def _load_library(self) -> dict[str, Any]:
        """加载歌曲库数据。"""
        if self._library_file.exists():
            try:
                with open(self._library_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"加载歌曲库数据: {len(data.get('songs', {}))} 首歌曲")
                    return data
            except Exception as e:
                logger.error(f"加载歌曲库数据失败: {e}")
        
        # 创建默认数据结构
        default_data = {
            "version": "1.0",
            "library_dir": str(self._music_dir),
            "songs": {},
            "tags": {},
            "playlists": {},
            "settings": {
                "volume": 0.8,
                "loop_mode": "list",  # single / list / none
                "shuffle": False,
                "ducking_enabled": True,
                "ducking_level": 0.3,
            },
            "current_state": {
                "last_played_id": None,
                "current_position": 0.0,
                "current_playlist": None,
                "current_playlist_index": 0,
            },
        }
        
        # 添加内置标签
        for tag_name, tag_info in BUILTIN_TAGS.items():
            default_data["tags"][tag_name] = {
                "color": tag_info["color"],
                "category": tag_info["category"],
                "count": 0,
                "is_builtin": True,
            }
        
        self._save_library(default_data)
        return default_data

    def _save_library(self, data: dict[str, Any] | None = None) -> bool:
        """保存歌曲库数据。"""
        try:
            save_data = data or self._library_data
            with open(self._library_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存歌曲库数据失败: {e}")
            return False

    def get_actions(self) -> list[ActionDef]:
        """返回工具支持的所有动作定义。"""
        return [
            # === 歌曲管理 ===
            ActionDef(
                name="add_songs",
                description="添加歌曲到歌曲库。支持从本地路径添加，默认复制到歌曲库目录。",
                parameters={
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要添加的歌曲文件路径列表",
                    },
                    "copy_to_library": {
                        "type": "boolean",
                        "description": "是否复制到歌曲库目录（默认 true）",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要添加的标签列表",
                    },
                },
                required_params=["paths"],
            ),
            ActionDef(
                name="scan_local_music",
                description="扫描本地硬盘或指定目录，查找并导入 MP3 等音频文件。",
                parameters={
                    "directory": {
                        "type": "string",
                        "description": "要扫描的目录路径，不指定则扫描常见音乐目录",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归扫描子目录（默认 true）",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大导入数量（默认 100）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="download_song",
                description="从用户提供的 URL 下载歌曲到歌曲库。注意版权问题。",
                parameters={
                    "url": {
                        "type": "string",
                        "description": "歌曲文件的下载 URL",
                    },
                    "title": {
                        "type": "string",
                        "description": "歌曲标题",
                    },
                    "artist": {
                        "type": "string",
                        "description": "歌手名",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要添加的标签列表",
                    },
                },
                required_params=["url"],
            ),
            ActionDef(
                name="delete_song",
                description="从歌曲库删除歌曲。可选择是否同时删除文件。",
                parameters={
                    "song_id": {
                        "type": "string",
                        "description": "要删除的歌曲 ID",
                    },
                    "delete_file": {
                        "type": "boolean",
                        "description": "是否同时删除文件（默认 false）",
                    },
                },
                required_params=["song_id"],
            ),
            ActionDef(
                name="update_song_info",
                description="更新歌曲的元数据信息。",
                parameters={
                    "song_id": {
                        "type": "string",
                        "description": "歌曲 ID",
                    },
                    "title": {
                        "type": "string",
                        "description": "新标题",
                    },
                    "artist": {
                        "type": "string",
                        "description": "新歌手名",
                    },
                    "album": {
                        "type": "string",
                        "description": "新专辑名",
                    },
                    "rating": {
                        "type": "integer",
                        "description": "评分（1-5）",
                    },
                    "favorite": {
                        "type": "boolean",
                        "description": "是否收藏",
                    },
                },
                required_params=["song_id"],
            ),
            # === 播放控制 ===
            ActionDef(
                name="play_song",
                description="播放指定歌曲。可以通过 ID、标题或标签搜索。",
                parameters={
                    "song_id": {
                        "type": "string",
                        "description": "歌曲 ID",
                    },
                    "title": {
                        "type": "string",
                        "description": "歌曲标题（模糊匹配）",
                    },
                    "artist": {
                        "type": "string",
                        "description": "歌手名（模糊匹配）",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签列表（播放匹配的第一首）",
                    },
                    "playlist": {
                        "type": "string",
                        "description": "播放列表名称（播放列表中的歌曲）",
                    },
                    "volume": {
                        "type": "number",
                        "description": "音量（0.0-1.0）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="pause_song",
                description="暂停当前播放。",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="resume_song",
                description="继续播放已暂停的歌曲。",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="stop_song",
                description="停止当前播放。",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="next_song",
                description="播放下一首歌曲。",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="prev_song",
                description="播放上一首歌曲。",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="seek_to",
                description="跳转到指定播放位置。",
                parameters={
                    "position": {
                        "type": "number",
                        "description": "目标位置（秒或百分比，如 30 或 0.5）",
                    },
                    "is_percent": {
                        "type": "boolean",
                        "description": "position 是否为百分比（默认 false，即秒）",
                    },
                },
                required_params=["position"],
            ),
            ActionDef(
                name="set_volume",
                description="设置播放音量。",
                parameters={
                    "volume": {
                        "type": "number",
                        "description": "音量值（0.0-1.0）",
                    },
                },
                required_params=["volume"],
            ),
            ActionDef(
                name="set_loop_mode",
                description="设置循环播放模式。",
                parameters={
                    "mode": {
                        "type": "string",
                        "enum": ["single", "list", "none"],
                        "description": "循环模式：single=单曲循环，list=列表循环，none=顺序播放",
                    },
                },
                required_params=["mode"],
            ),
            ActionDef(
                name="shuffle_play",
                description="切换随机播放模式。",
                parameters={
                    "enabled": {
                        "type": "boolean",
                        "description": "是否启用随机播放（不指定则切换当前状态）",
                    },
                },
                required_params=[],
            ),
            # === 搜索与查询 ===
            ActionDef(
                name="search_songs",
                description="搜索歌曲库。支持按标题、歌手、标签搜索。",
                parameters={
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词（匹配标题和歌手）",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签过滤列表",
                    },
                    "favorite_only": {
                        "type": "boolean",
                        "description": "仅显示收藏的歌曲",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量限制（默认 20）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="get_now_playing",
                description="获取当前播放信息。",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="get_playlist",
                description="获取播放列表内容。",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "播放列表名称（不指定则返回当前播放列表）",
                    },
                },
                required_params=[],
            ),
            # === 标签管理 ===
            ActionDef(
                name="create_tag",
                description="创建自定义标签。",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "标签名称",
                    },
                    "color": {
                        "type": "string",
                        "description": "标签颜色（十六进制，如 #FF5722）",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["style", "mood", "scene", "instrument", "custom"],
                        "description": "标签分类",
                    },
                },
                required_params=["name"],
            ),
            ActionDef(
                name="add_tag",
                description="为歌曲添加标签。",
                parameters={
                    "song_id": {
                        "type": "string",
                        "description": "歌曲 ID",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要添加的标签列表",
                    },
                },
                required_params=["song_id", "tags"],
            ),
            ActionDef(
                name="remove_tag",
                description="移除歌曲的标签。",
                parameters={
                    "song_id": {
                        "type": "string",
                        "description": "歌曲 ID",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要移除的标签列表",
                    },
                },
                required_params=["song_id", "tags"],
            ),
            # === 播放列表管理 ===
            ActionDef(
                name="create_playlist",
                description="创建新的播放列表。",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "播放列表名称",
                    },
                    "description": {
                        "type": "string",
                        "description": "播放列表描述",
                    },
                    "song_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "初始歌曲 ID 列表",
                    },
                },
                required_params=["name"],
            ),
            ActionDef(
                name="add_to_playlist",
                description="添加歌曲到播放列表。",
                parameters={
                    "playlist_name": {
                        "type": "string",
                        "description": "播放列表名称",
                    },
                    "song_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要添加的歌曲 ID 列表",
                    },
                },
                required_params=["playlist_name", "song_ids"],
            ),
            ActionDef(
                name="remove_from_playlist",
                description="从播放列表移除歌曲。",
                parameters={
                    "playlist_name": {
                        "type": "string",
                        "description": "播放列表名称",
                    },
                    "song_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要移除的歌曲 ID 列表",
                    },
                },
                required_params=["playlist_name", "song_ids"],
            ),
            # === 设置 ===
            ActionDef(
                name="get_player_settings",
                description="获取播放器设置。",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="set_player_settings",
                description="设置播放器参数。",
                parameters={
                    "volume": {
                        "type": "number",
                        "description": "默认音量（0.0-1.0）",
                    },
                    "loop_mode": {
                        "type": "string",
                        "enum": ["single", "list", "none"],
                        "description": "循环模式",
                    },
                    "shuffle": {
                        "type": "boolean",
                        "description": "是否随机播放",
                    },
                    "ducking_enabled": {
                        "type": "boolean",
                        "description": "是否启用 Audio Ducking（TTS 时降低音量）",
                    },
                    "ducking_level": {
                        "type": "number",
                        "description": "Ducking 时的音量级别（0.0-1.0）",
                    },
                },
                required_params=[],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定动作。"""
        try:
            # 歌曲管理
            if action == "add_songs":
                return await self._add_songs(params)
            elif action == "scan_local_music":
                return await self._scan_local_music(params)
            elif action == "download_song":
                return await self._download_song(params)
            elif action == "delete_song":
                return await self._delete_song(params)
            elif action == "update_song_info":
                return await self._update_song_info(params)
            
            # 播放控制
            elif action == "play_song":
                return await self._play_song(params)
            elif action == "pause_song":
                return await self._pause_song(params)
            elif action == "resume_song":
                return await self._resume_song(params)
            elif action == "stop_song":
                return await self._stop_song(params)
            elif action == "next_song":
                return await self._next_song(params)
            elif action == "prev_song":
                return await self._prev_song(params)
            elif action == "seek_to":
                return await self._seek_to(params)
            elif action == "set_volume":
                return await self._set_volume(params)
            elif action == "set_loop_mode":
                return await self._set_loop_mode(params)
            elif action == "shuffle_play":
                return await self._shuffle_play(params)
            
            # 搜索与查询
            elif action == "search_songs":
                return await self._search_songs(params)
            elif action == "get_now_playing":
                return await self._get_now_playing(params)
            elif action == "get_playlist":
                return await self._get_playlist(params)
            
            # 标签管理
            elif action == "create_tag":
                return await self._create_tag(params)
            elif action == "add_tag":
                return await self._add_tag(params)
            elif action == "remove_tag":
                return await self._remove_tag(params)
            
            # 播放列表管理
            elif action == "create_playlist":
                return await self._create_playlist(params)
            elif action == "add_to_playlist":
                return await self._add_to_playlist(params)
            elif action == "remove_from_playlist":
                return await self._remove_from_playlist(params)
            
            # 设置
            elif action == "get_player_settings":
                return await self._get_player_settings(params)
            elif action == "set_player_settings":
                return await self._set_player_settings(params)
            
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"未知的动作: {action}",
                )
        
        except Exception as e:
            logger.error(f"执行动作 {action} 失败: {e}")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e),
            )

    # ==================== 歌曲管理 ====================

    async def _add_songs(self, params: dict[str, Any]) -> ToolResult:
        """添加歌曲到歌曲库。"""
        paths = params.get("paths", [])
        copy_to_library = params.get("copy_to_library", True)
        tags = params.get("tags", [])
        
        if not paths:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="未提供歌曲路径",
            )
        
        added_songs = []
        failed_paths = []
        
        for path_str in paths:
            path = Path(path_str)
            
            # 检查文件是否存在
            if not path.exists():
                failed_paths.append(f"{path_str} (文件不存在)")
                continue
            
            # 检查文件格式
            if path.suffix.lower() not in SUPPORTED_AUDIO_FORMATS:
                failed_paths.append(f"{path_str} (不支持的格式)")
                continue
            
            try:
                # 生成歌曲 ID
                song_id = str(uuid.uuid4())
                
                # 确定文件存储路径
                if copy_to_library:
                    dest_path = self._music_dir / path.name
                    # 处理重名文件
                    if dest_path.exists():
                        stem = path.stem
                        suffix = path.suffix
                        counter = 1
                        while dest_path.exists():
                            dest_path = self._music_dir / f"{stem}_{counter}{suffix}"
                            counter += 1
                    shutil.copy2(path, dest_path)
                    file_path = str(dest_path)
                    original_path = str(path)
                else:
                    file_path = str(path)
                    original_path = None
                
                # 提取歌曲信息（从文件名）
                title = path.stem
                artist = "未知艺术家"
                
                # 尝试从文件名解析（格式：歌手 - 歌名）
                if " - " in title:
                    parts = title.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                
                # 创建歌曲记录
                song_data = {
                    "id": song_id,
                    "title": title,
                    "artist": artist,
                    "album": "",
                    "duration": 0,  # 需要播放器获取
                    "file_path": file_path,
                    "original_path": original_path,
                    "file_type": "local",
                    "tags": tags.copy(),
                    "added_at": datetime.now().isoformat(),
                    "play_count": 0,
                    "last_played_at": None,
                    "favorite": False,
                    "rating": 0,
                    "lyrics": None,
                }
                
                # 添加到歌曲库
                self._library_data["songs"][song_id] = song_data
                
                # 更新标签计数
                for tag in tags:
                    if tag in self._library_data["tags"]:
                        self._library_data["tags"][tag]["count"] += 1
                
                added_songs.append(f"{title} - {artist}")
                
            except Exception as e:
                failed_paths.append(f"{path_str} ({str(e)})")
        
        # 保存数据
        self._save_library()
        
        # 构建结果
        result_parts = []
        if added_songs:
            result_parts.append(f"成功添加 {len(added_songs)} 首歌曲：\n" + "\n".join(f"  • {s}" for s in added_songs))
        if failed_paths:
            result_parts.append(f"失败 {len(failed_paths)} 个：\n" + "\n".join(f"  ✗ {p}" for p in failed_paths))
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS if added_songs else ToolResultStatus.ERROR,
            output="\n\n".join(result_parts),
            data={"added_count": len(added_songs), "failed_count": len(failed_paths)},
        )

    async def _scan_local_music(self, params: dict[str, Any]) -> ToolResult:
        """扫描本地目录查找音频文件。"""
        directory = params.get("directory")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 100)
        
        # 默认扫描目录
        scan_dirs = []
        if directory:
            scan_dirs = [Path(directory)]
        else:
            # 常见音乐目录
            home = Path.home()
            scan_dirs = [
                home / "Music",
                home / "Downloads",
                Path("D:/Music") if Path("D:/").exists() else None,
                Path("E:/Music") if Path("E:/").exists() else None,
            ]
            scan_dirs = [d for d in scan_dirs if d and d.exists()]
        
        found_files = []
        
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            
            try:
                if recursive:
                    for ext in SUPPORTED_AUDIO_FORMATS:
                        found_files.extend(scan_dir.rglob(f"*{ext}"))
                else:
                    for ext in SUPPORTED_AUDIO_FORMATS:
                        found_files.extend(scan_dir.glob(f"*{ext}"))
            except PermissionError:
                continue
        
        # 去重并限制数量
        found_files = list(set(found_files))[:max_results]
        
        if not found_files:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="未找到音频文件",
                data={"found_count": 0},
            )
        
        # 添加到歌曲库
        added_songs = []
        for file_path in found_files:
            # 检查是否已存在
            existing = any(
                s.get("original_path") == str(file_path) or s.get("file_path") == str(file_path)
                for s in self._library_data["songs"].values()
            )
            if existing:
                continue
            
            # 使用 add_songs 逻辑添加
            result = await self._add_songs({
                "paths": [str(file_path)],
                "copy_to_library": True,
                "tags": [],
            })
            if result.is_success:
                added_songs.append(file_path.name)
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"扫描完成：找到 {len(found_files)} 个音频文件，新增 {len(added_songs)} 首到歌曲库",
            data={
                "found_count": len(found_files),
                "added_count": len(added_songs),
                "added_songs": added_songs,
            },
        )

    async def _download_song(self, params: dict[str, Any]) -> ToolResult:
        """从 URL 下载歌曲。"""
        url = params.get("url")
        title = params.get("title", "未知歌曲")
        artist = params.get("artist", "未知艺术家")
        tags = params.get("tags", [])
        
        if not url:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="未提供下载 URL",
            )
        
        try:
            import urllib.request
            
            # 从 URL 提取文件名
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            filename = unquote(Path(parsed.path).name)
            
            if not filename:
                filename = f"{title}.mp3"
            
            # 下载文件
            dest_path = self._music_dir / filename
            urllib.request.urlretrieve(url, dest_path)
            
            # 创建歌曲记录
            song_id = str(uuid.uuid4())
            song_data = {
                "id": song_id,
                "title": title,
                "artist": artist,
                "album": "",
                "duration": 0,
                "file_path": str(dest_path),
                "original_path": url,
                "file_type": "url",
                "tags": tags.copy(),
                "added_at": datetime.now().isoformat(),
                "play_count": 0,
                "last_played_at": None,
                "favorite": False,
                "rating": 0,
                "lyrics": None,
            }
            
            self._library_data["songs"][song_id] = song_data
            self._save_library()
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"下载成功：{title} - {artist}\n文件：{filename}",
                data={"song_id": song_id, "file_path": str(dest_path)},
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"下载失败：{str(e)}",
            )

    async def _delete_song(self, params: dict[str, Any]) -> ToolResult:
        """删除歌曲。"""
        song_id = params.get("song_id")
        delete_file = params.get("delete_file", False)
        
        if not song_id or song_id not in self._library_data["songs"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="歌曲不存在",
            )
        
        song = self._library_data["songs"][song_id]
        title = song.get("title", "未知")
        artist = song.get("artist", "未知")
        
        # 删除文件
        if delete_file:
            file_path = Path(song.get("file_path", ""))
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"删除文件失败: {e}")
        
        # 从播放列表移除
        for playlist in self._library_data["playlists"].values():
            if song_id in playlist.get("song_ids", []):
                playlist["song_ids"].remove(song_id)
        
        # 更新标签计数
        for tag in song.get("tags", []):
            if tag in self._library_data["tags"]:
                self._library_data["tags"][tag]["count"] = max(0, 
                    self._library_data["tags"][tag]["count"] - 1)
        
        # 删除歌曲记录
        del self._library_data["songs"][song_id]
        self._save_library()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已删除歌曲：{title} - {artist}",
        )

    async def _update_song_info(self, params: dict[str, Any]) -> ToolResult:
        """更新歌曲信息。"""
        song_id = params.get("song_id")
        
        if not song_id or song_id not in self._library_data["songs"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="歌曲不存在",
            )
        
        song = self._library_data["songs"][song_id]
        
        # 更新字段
        if "title" in params:
            song["title"] = params["title"]
        if "artist" in params:
            song["artist"] = params["artist"]
        if "album" in params:
            song["album"] = params["album"]
        if "rating" in params:
            song["rating"] = max(0, min(5, params["rating"]))
        if "favorite" in params:
            song["favorite"] = params["favorite"]
        
        self._save_library()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已更新歌曲信息：{song['title']} - {song['artist']}",
            data=song,
        )

    # ==================== 播放控制 ====================
    # 通过播放器控制器通知 UI 层执行实际播放

    async def _play_song(self, params: dict[str, Any]) -> ToolResult:
        """播放歌曲。"""
        song_id = params.get("song_id")
        title = params.get("title")
        artist = params.get("artist")
        tags = params.get("tags", [])
        playlist_name = params.get("playlist")
        volume = params.get("volume")
        
        target_song = None
        playlist_songs = []
        
        # 确定播放列表
        if playlist_name and playlist_name in self._library_data["playlists"]:
            playlist = self._library_data["playlists"][playlist_name]
            playlist_songs = [
                self._library_data["songs"][sid]
                for sid in playlist.get("song_ids", [])
                if sid in self._library_data["songs"]
            ]
        
        # 查找目标歌曲
        if song_id and song_id in self._library_data["songs"]:
            target_song = self._library_data["songs"][song_id]
        elif title or artist:
            # 模糊搜索
            for song in self._library_data["songs"].values():
                match = True
                if title and title.lower() not in song.get("title", "").lower():
                    match = False
                if artist and artist.lower() not in song.get("artist", "").lower():
                    match = False
                if match:
                    target_song = song
                    break
        elif tags:
            # 按标签搜索
            for song in self._library_data["songs"].values():
                if any(tag in song.get("tags", []) for tag in tags):
                    target_song = song
                    break
        elif playlist_songs:
            # 播放列表第一首
            target_song = playlist_songs[0]
        
        if not target_song:
            # 如果没有任何指定，播放第一首
            if self._library_data["songs"]:
                target_song = list(self._library_data["songs"].values())[0]
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="歌曲库为空，请先添加歌曲",
                )
        
        # 更新播放状态
        self._player_state["current_song_id"] = target_song["id"]
        self._player_state["is_playing"] = True
        self._player_state["is_paused"] = False
        if volume is not None:
            self._player_state["volume"] = volume
        
        # 更新歌曲播放计数
        target_song["play_count"] = target_song.get("play_count", 0) + 1
        target_song["last_played_at"] = datetime.now().isoformat()
        
        # 更新当前状态
        self._library_data["current_state"]["last_played_id"] = target_song["id"]
        if playlist_name:
            self._library_data["current_state"]["current_playlist"] = playlist_name
        
        self._save_library()
        
        # 通过控制器通知 UI 层播放
        self._controller.play(target_song)
        if volume is not None:
            self._controller.set_volume(volume)
        
        # 构建输出
        tags_str = " | ".join(target_song.get("tags", [])) or "无标签"
        output = f"正在播放：{target_song['title']} - {target_song['artist']}\n标签：{tags_str}"
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={
                "action": "play",
                "song": target_song,
                "playlist": playlist_songs if playlist_songs else None,
                "volume": self._player_state["volume"],
            },
        )

    async def _pause_song(self, params: dict[str, Any]) -> ToolResult:
        """暂停播放。"""
        if not self._player_state["is_playing"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="当前没有正在播放的歌曲",
            )
        
        self._player_state["is_paused"] = True
        
        # 通过控制器通知 UI 层暂停
        self._controller.pause()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="已暂停播放",
            data={"action": "pause"},
        )

    async def _resume_song(self, params: dict[str, Any]) -> ToolResult:
        """继续播放。"""
        if not self._player_state["is_paused"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="当前没有暂停的歌曲",
            )
        
        self._player_state["is_paused"] = False
        
        # 通过控制器通知 UI 层继续
        self._controller.resume()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="继续播放",
            data={"action": "resume"},
        )

    async def _stop_song(self, params: dict[str, Any]) -> ToolResult:
        """停止播放。"""
        self._player_state["is_playing"] = False
        self._player_state["is_paused"] = False
        self._player_state["current_position"] = 0.0
        
        # 通过控制器通知 UI 层停止
        self._controller.stop()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="已停止播放",
            data={"action": "stop"},
        )

    async def _next_song(self, params: dict[str, Any]) -> ToolResult:
        """下一首。"""
        current_id = self._player_state.get("current_song_id")
        songs = list(self._library_data["songs"].values())
        
        if not songs:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="歌曲库为空",
            )
        
        # 找到当前歌曲的索引
        current_index = 0
        if current_id:
            for i, song in enumerate(songs):
                if song["id"] == current_id:
                    current_index = i
                    break
        
        # 计算下一首索引
        settings = self._library_data.get("settings", {})
        if settings.get("shuffle"):
            import random
            next_index = random.randint(0, len(songs) - 1)
        else:
            next_index = (current_index + 1) % len(songs)
        
        next_song = songs[next_index]
        
        return await self._play_song({"song_id": next_song["id"]})

    async def _prev_song(self, params: dict[str, Any]) -> ToolResult:
        """上一首。"""
        current_id = self._player_state.get("current_song_id")
        songs = list(self._library_data["songs"].values())
        
        if not songs:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="歌曲库为空",
            )
        
        # 找到当前歌曲的索引
        current_index = 0
        if current_id:
            for i, song in enumerate(songs):
                if song["id"] == current_id:
                    current_index = i
                    break
        
        # 计算上一首索引
        prev_index = (current_index - 1) % len(songs)
        prev_song = songs[prev_index]
        
        return await self._play_song({"song_id": prev_song["id"]})

    async def _seek_to(self, params: dict[str, Any]) -> ToolResult:
        """跳转播放位置。"""
        position = params.get("position", 0)
        is_percent = params.get("is_percent", False)
        
        # 通过控制器通知 UI 层跳转
        self._controller.seek(position, is_percent)
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"跳转到 {'%.1f%%' % (position * 100) if is_percent else f'{position}秒'}",
            data={
                "action": "seek",
                "position": position,
                "is_percent": is_percent,
            },
        )

    async def _set_volume(self, params: dict[str, Any]) -> ToolResult:
        """设置音量。"""
        volume = params.get("volume", 0.8)
        volume = max(0.0, min(1.0, volume))
        
        self._player_state["volume"] = volume
        self._library_data["settings"]["volume"] = volume
        self._save_library()
        
        # 通过控制器通知 UI 层设置音量
        self._controller.set_volume(volume)
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"音量设置为 {int(volume * 100)}%",
            data={"action": "set_volume", "volume": volume},
        )

    async def _set_loop_mode(self, params: dict[str, Any]) -> ToolResult:
        """设置循环模式。"""
        mode = params.get("mode", "list")
        
        if mode not in ["single", "list", "none"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="无效的循环模式，可选：single、list、none",
            )
        
        self._library_data["settings"]["loop_mode"] = mode
        self._save_library()
        
        # 通过控制器通知 UI 层设置循环模式
        self._controller.set_loop(mode)
        
        mode_names = {"single": "单曲循环", "list": "列表循环", "none": "顺序播放"}
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"循环模式：{mode_names[mode]}",
            data={"action": "set_loop_mode", "mode": mode},
        )

    async def _shuffle_play(self, params: dict[str, Any]) -> ToolResult:
        """切换随机播放。"""
        current = self._library_data["settings"].get("shuffle", False)
        enabled = params.get("enabled", not current)
        
        self._library_data["settings"]["shuffle"] = enabled
        self._save_library()
        
        # 通过控制器通知 UI 层设置随机播放
        self._controller.set_shuffle(enabled)
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"随机播放：{'开启' if enabled else '关闭'}",
            data={"action": "shuffle", "enabled": enabled},
        )

    # ==================== 搜索与查询 ====================

    async def _search_songs(self, params: dict[str, Any]) -> ToolResult:
        """搜索歌曲。"""
        keyword = params.get("keyword", "").lower()
        tags = params.get("tags", [])
        favorite_only = params.get("favorite_only", False)
        limit = params.get("limit", 20)
        
        results = []
        
        for song in self._library_data["songs"].values():
            # 关键词匹配
            if keyword:
                title_match = keyword in song.get("title", "").lower()
                artist_match = keyword in song.get("artist", "").lower()
                if not (title_match or artist_match):
                    continue
            
            # 标签匹配
            if tags:
                song_tags = song.get("tags", [])
                if not all(tag in song_tags for tag in tags):
                    continue
            
            # 收藏过滤
            if favorite_only and not song.get("favorite"):
                continue
            
            results.append(song)
        
        # 限制数量
        results = results[:limit]
        
        if not results:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="未找到匹配的歌曲",
                data={"results": [], "total": 0},
            )
        
        # 格式化输出
        lines = [f"找到 {len(results)} 首歌曲："]
        for i, song in enumerate(results, 1):
            tags_str = ", ".join(song.get("tags", [])) or "无标签"
            favorite_mark = "★" if song.get("favorite") else " "
            lines.append(f"  {i}. {favorite_mark} {song['title']} - {song['artist']} [{tags_str}]")
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"results": results, "total": len(results)},
        )

    async def _get_now_playing(self, params: dict[str, Any]) -> ToolResult:
        """获取当前播放信息。"""
        song_id = self._player_state.get("current_song_id")
        
        if not song_id or song_id not in self._library_data["songs"]:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="当前没有播放中的歌曲",
                data={"is_playing": False},
            )
        
        song = self._library_data["songs"][song_id]
        
        status = "播放中" if self._player_state["is_playing"] and not self._player_state["is_paused"] else "已暂停"
        tags_str = " | ".join(song.get("tags", [])) or "无标签"
        
        output = f"{status}：{song['title']} - {song['artist']}\n标签：{tags_str}"
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={
                "is_playing": self._player_state["is_playing"],
                "is_paused": self._player_state["is_paused"],
                "song": song,
                "position": self._player_state.get("current_position", 0),
                "volume": self._player_state.get("volume", 0.8),
            },
        )

    async def _get_playlist(self, params: dict[str, Any]) -> ToolResult:
        """获取播放列表。"""
        name = params.get("name")
        
        if name:
            if name not in self._library_data["playlists"]:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"播放列表 '{name}' 不存在",
                )
            playlists = {name: self._library_data["playlists"][name]}
        else:
            playlists = self._library_data["playlists"]
        
        if not playlists:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="暂无播放列表",
                data={"playlists": {}},
            )
        
        # 格式化输出
        lines = []
        for pl_name, pl_data in playlists.items():
            song_ids = pl_data.get("song_ids", [])
            description = pl_data.get("description", "")
            lines.append(f"歌单：{pl_name} ({len(song_ids)} 首)")
            if description:
                lines.append(f"  描述：{description}")
            
            for i, song_id in enumerate(song_ids[:10], 1):  # 最多显示 10 首
                if song_id in self._library_data["songs"]:
                    song = self._library_data["songs"][song_id]
                    lines.append(f"  {i}. {song['title']} - {song['artist']}")
            
            if len(song_ids) > 10:
                lines.append(f"  ... 还有 {len(song_ids) - 10} 首")
            lines.append("")
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines).strip(),
            data={"playlists": playlists},
        )

    # ==================== 标签管理 ====================

    async def _create_tag(self, params: dict[str, Any]) -> ToolResult:
        """创建自定义标签。"""
        name = params.get("name")
        color = params.get("color", "#607D8B")
        category = params.get("category", "custom")
        
        if not name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="标签名称不能为空",
            )
        
        if name in self._library_data["tags"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"标签 '{name}' 已存在",
            )
        
        self._library_data["tags"][name] = {
            "color": color,
            "category": category,
            "count": 0,
            "is_builtin": False,
        }
        self._save_library()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已创建标签：{name}",
            data={"tag": name, "color": color, "category": category},
        )

    async def _add_tag(self, params: dict[str, Any]) -> ToolResult:
        """为歌曲添加标签。"""
        song_id = params.get("song_id")
        tags = params.get("tags", [])
        
        if not song_id or song_id not in self._library_data["songs"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="歌曲不存在",
            )
        
        if not tags:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="未提供标签",
            )
        
        song = self._library_data["songs"][song_id]
        added_tags = []
        
        for tag in tags:
            # 自动创建不存在的标签
            if tag not in self._library_data["tags"]:
                self._library_data["tags"][tag] = {
                    "color": "#607D8B",
                    "category": "custom",
                    "count": 0,
                    "is_builtin": False,
                }
            
            if tag not in song.get("tags", []):
                song.setdefault("tags", []).append(tag)
                self._library_data["tags"][tag]["count"] += 1
                added_tags.append(tag)
        
        self._save_library()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已为《{song['title']}》添加标签：{', '.join(added_tags)}",
            data={"song_id": song_id, "added_tags": added_tags},
        )

    async def _remove_tag(self, params: dict[str, Any]) -> ToolResult:
        """移除歌曲标签。"""
        song_id = params.get("song_id")
        tags = params.get("tags", [])
        
        if not song_id or song_id not in self._library_data["songs"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="歌曲不存在",
            )
        
        song = self._library_data["songs"][song_id]
        removed_tags = []
        
        for tag in tags:
            if tag in song.get("tags", []):
                song["tags"].remove(tag)
                if tag in self._library_data["tags"]:
                    self._library_data["tags"][tag]["count"] = max(0,
                        self._library_data["tags"][tag]["count"] - 1)
                removed_tags.append(tag)
        
        self._save_library()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已从《{song['title']}》移除标签：{', '.join(removed_tags)}",
            data={"song_id": song_id, "removed_tags": removed_tags},
        )

    # ==================== 播放列表管理 ====================

    async def _create_playlist(self, params: dict[str, Any]) -> ToolResult:
        """创建播放列表。"""
        name = params.get("name")
        description = params.get("description", "")
        song_ids = params.get("song_ids", [])
        
        if not name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="播放列表名称不能为空",
            )
        
        if name in self._library_data["playlists"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"播放列表 '{name}' 已存在",
            )
        
        # 过滤有效的歌曲 ID
        valid_song_ids = [sid for sid in song_ids if sid in self._library_data["songs"]]
        
        self._library_data["playlists"][name] = {
            "description": description,
            "song_ids": valid_song_ids,
            "created_at": datetime.now().isoformat(),
        }
        self._save_library()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已创建播放列表：{name}（{len(valid_song_ids)} 首歌曲）",
            data={"name": name, "song_count": len(valid_song_ids)},
        )

    async def _add_to_playlist(self, params: dict[str, Any]) -> ToolResult:
        """添加歌曲到播放列表。"""
        playlist_name = params.get("playlist_name")
        song_ids = params.get("song_ids", [])
        
        if not playlist_name or playlist_name not in self._library_data["playlists"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="播放列表不存在",
            )
        
        playlist = self._library_data["playlists"][playlist_name]
        added_count = 0
        
        for song_id in song_ids:
            if song_id in self._library_data["songs"] and song_id not in playlist["song_ids"]:
                playlist["song_ids"].append(song_id)
                added_count += 1
        
        self._save_library()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已添加 {added_count} 首歌曲到播放列表「{playlist_name}」",
            data={"playlist_name": playlist_name, "added_count": added_count},
        )

    async def _remove_from_playlist(self, params: dict[str, Any]) -> ToolResult:
        """从播放列表移除歌曲。"""
        playlist_name = params.get("playlist_name")
        song_ids = params.get("song_ids", [])
        
        if not playlist_name or playlist_name not in self._library_data["playlists"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="播放列表不存在",
            )
        
        playlist = self._library_data["playlists"][playlist_name]
        removed_count = 0
        
        for song_id in song_ids:
            if song_id in playlist["song_ids"]:
                playlist["song_ids"].remove(song_id)
                removed_count += 1
        
        self._save_library()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已从播放列表「{playlist_name}」移除 {removed_count} 首歌曲",
            data={"playlist_name": playlist_name, "removed_count": removed_count},
        )

    # ==================== 设置 ====================

    async def _get_player_settings(self, params: dict[str, Any]) -> ToolResult:
        """获取播放器设置。"""
        settings = self._library_data.get("settings", {})
        
        lines = ["播放器设置："]
        lines.append(f"  音量：{int(settings.get('volume', 0.8) * 100)}%")
        lines.append(f"  循环模式：{settings.get('loop_mode', 'list')}")
        lines.append(f"  随机播放：{'开启' if settings.get('shuffle') else '关闭'}")
        lines.append(f"  Audio Ducking：{'开启' if settings.get('ducking_enabled') else '关闭'}")
        if settings.get("ducking_enabled"):
            lines.append(f"  Ducking 级别：{int(settings.get('ducking_level', 0.3) * 100)}%")
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data=settings,
        )

    async def _set_player_settings(self, params: dict[str, Any]) -> ToolResult:
        """设置播放器参数。"""
        settings = self._library_data.setdefault("settings", {})
        
        if "volume" in params:
            settings["volume"] = max(0.0, min(1.0, params["volume"]))
        if "loop_mode" in params:
            if params["loop_mode"] in ["single", "list", "none"]:
                settings["loop_mode"] = params["loop_mode"]
        if "shuffle" in params:
            settings["shuffle"] = params["shuffle"]
        if "ducking_enabled" in params:
            settings["ducking_enabled"] = params["ducking_enabled"]
        if "ducking_level" in params:
            settings["ducking_level"] = max(0.0, min(1.0, params["ducking_level"]))
        
        self._save_library()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="设置已更新",
            data=settings,
        )

    # ==================== 工具方法 ====================

    def get_library_data(self) -> dict[str, Any]:
        """获取歌曲库数据（供 UI 使用）。"""
        return self._library_data

    def get_player_state(self) -> dict[str, Any]:
        """获取播放器状态（供 UI 使用）。"""
        return self._player_state

    def update_player_state(self, state: dict[str, Any]) -> None:
        """更新播放器状态（供 UI 调用）。"""
        self._player_state.update(state)
