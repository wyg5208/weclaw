"""迷你音乐播放器面板 - 可拖拽悬浮窗口。

功能特性：
- 可拖拽悬浮小窗口
- 置顶显示（可选）
- 迷你/展开两种模式切换
- 支持键盘快捷键
- QtMultimedia 音频播放
- Audio Ducking 与 TTS 协调
- 响应工具层的播放控制指令
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any

from PySide6.QtCore import Qt, Signal, QTimer, QUrl, QSize, QPoint
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut, QAction, QCursor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QLineEdit,
    QMenu,
)

if TYPE_CHECKING:
    from src.tools.music_player import MusicPlayerTool

logger = logging.getLogger(__name__)


class MiniPlayerPanel(QFrame):
    """迷你音乐播放器面板 - 可拖拽悬浮窗口。"""

    # 信号
    play_state_changed = Signal(bool)  # 播放状态变化
    song_changed = Signal(dict)  # 当前歌曲变化
    volume_changed = Signal(float)  # 音量变化
    closed = Signal()  # 窗口关闭

    # 窗口尺寸 - 只有两种模式
    MINI_SIZE = (320, 100)      # 迷你模式：显示当前歌曲 + 控制按钮 + 进度条
    EXPANDED_SIZE = (450, 400)  # 展开模式：完整播放列表 + 管理功能
    
    def __init__(
        self,
        music_tool: Optional[MusicPlayerTool] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        
        self._music_tool = music_tool
        self._is_expanded = False  # False=迷你模式，True=展开模式
        self._dragging = False
        self._drag_pos = None
        self._ducking = False
        self._original_volume = 0.8
        
        # 播放器组件
        self._player: Optional[QMediaPlayer] = None
        self._audio_output: Optional[QAudioOutput] = None
        
        # 当前播放列表
        self._playlist: list[dict] = []
        self._current_index = 0
        
        self._setup_window()
        self._setup_player()
        self._setup_ui()
        self._setup_shortcuts()
        self._register_controller_callbacks()
        
        # 更新定时器
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(500)  # 500ms 更新一次进度
        self._update_timer.timeout.connect(self._update_progress)
    
    def _setup_window(self) -> None:
        """设置窗口属性。"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        # 固定尺寸，避免拖拽时变形
        self.setFixedSize(*self.MINI_SIZE)
        self.setMaximumHeight(600)
        self.resize(*self.MINI_SIZE)
        self.setObjectName("miniPlayerPanel")
        
        # 设置样式
        self.setStyleSheet("""
            #miniPlayerPanel {
                background-color: rgba(30, 30, 40, 240);
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 8px;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #ffffff;
                font-size: 16px;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 50);
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 50);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px;
                height: 12px;
                margin: -4px 0;
                background: #4CAF50;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50;
                border-radius: 2px;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
            }
            QListWidget {
                background-color: rgba(0, 0, 0, 30);
                border: none;
                border-radius: 4px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: rgba(76, 175, 80, 100);
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 20);
            }
        """)

    def _setup_player(self) -> None:
        """设置音频播放器。"""
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        
        # 连接信号
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.errorOccurred.connect(self._on_error)
        
        # 设置初始音量
        if self._music_tool:
            settings = self._music_tool.get_library_data().get("settings", {})
            volume = settings.get("volume", 0.8)
            self._audio_output.setVolume(volume)
            self._original_volume = volume

    def _setup_ui(self) -> None:
        """设置 UI 布局。"""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.setSpacing(6)
        
        # === 标题栏（可拖拽） ===
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(24)
        self._title_bar.setCursor(Qt.CursorShape.SizeAllCursor)
        
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        
        self._title_label = QLabel("🎵 歌曲库")
        self._title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        title_layout.addWidget(self._title_label)
        
        # 歌曲数量标签
        self._count_label = QLabel("(0)")
        self._count_label.setFont(QFont("Microsoft YaHei", 9))
        self._count_label.setStyleSheet("color: #888; padding: 0 4px;")
        title_layout.addWidget(self._count_label)
        
        title_layout.addStretch()
        
        # 模式切换按钮
        self._expand_btn = QPushButton("≡")
        self._expand_btn.setFixedSize(24, 24)
        self._expand_btn.setToolTip("展开/收起")
        self._expand_btn.clicked.connect(self._toggle_mode)
        title_layout.addWidget(self._expand_btn)
        
        # 关闭按钮
        self._close_btn = QPushButton("×")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setToolTip("关闭")
        self._close_btn.clicked.connect(self.close)
        title_layout.addWidget(self._close_btn)
        
        self._main_layout.addWidget(self._title_bar)
        
        # === 歌曲信息 ===
        self._song_info = QLabel("未播放")
        self._song_info.setFont(QFont("Microsoft YaHei", 9))
        self._song_info.setWordWrap(True)
        self._main_layout.addWidget(self._song_info)
        
        # === 播放控制 ===
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(4)
        
        self._prev_btn = QPushButton("◀◀")
        self._prev_btn.setToolTip("上一首 (Ctrl+Left)")
        self._prev_btn.clicked.connect(self._prev_song)
        controls_layout.addWidget(self._prev_btn)
        
        self._play_btn = QPushButton("▶")
        self._play_btn.setToolTip("播放/暂停 (Space)")
        self._play_btn.clicked.connect(self._toggle_play)
        controls_layout.addWidget(self._play_btn)
        
        self._next_btn = QPushButton("▶▶")
        self._next_btn.setToolTip("下一首 (Ctrl+Right)")
        self._next_btn.clicked.connect(self._next_song)
        controls_layout.addWidget(self._next_btn)
        
        controls_layout.addSpacing(8)
        
        # 音量控制
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setFixedWidth(60)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(int(self._original_volume * 100))
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        controls_layout.addWidget(self._volume_slider)
        
        controls_layout.addSpacing(8)
        
        # 循环按钮
        self._loop_btn = QPushButton("⟲")
        self._loop_btn.setToolTip("循环模式 (Ctrl+L)")
        self._loop_btn.clicked.connect(self._toggle_loop)
        controls_layout.addWidget(self._loop_btn)
        
        # 时间显示
        self._time_label = QLabel("0:00/0:00")
        self._time_label.setFont(QFont("Consolas", 9))
        self._time_label.setFixedWidth(90)
        controls_layout.addWidget(self._time_label)
        
        self._main_layout.addLayout(controls_layout)
        
        # === 进度条 ===
        self._progress_slider = QSlider(Qt.Orientation.Horizontal)
        self._progress_slider.setRange(0, 1000)
        self._progress_slider.setValue(0)
        self._progress_slider.sliderMoved.connect(self._on_seek)
        self._main_layout.addWidget(self._progress_slider)
        
        # === 展开模式的额外内容 ===
        self._expanded_widget = QWidget()
        expanded_layout = QVBoxLayout(self._expanded_widget)
        expanded_layout.setContentsMargins(0, 4, 0, 0)
        expanded_layout.setSpacing(6)
        
        # === 管理工具栏 ===
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(4)
        
        # 添加歌曲按钮
        self._add_song_btn = QPushButton("➕ 添加")
        self._add_song_btn.setToolTip("添加本地歌曲文件")
        self._add_song_btn.clicked.connect(self._on_add_songs_clicked)
        toolbar_layout.addWidget(self._add_song_btn)
        
        # 扫描文件夹按钮
        self._scan_folder_btn = QPushButton("📁 扫描")
        self._scan_folder_btn.setToolTip("扫描文件夹中的歌曲")
        self._scan_folder_btn.clicked.connect(self._on_scan_folder_clicked)
        toolbar_layout.addWidget(self._scan_folder_btn)
        
        # 刷新按钮
        self._refresh_btn = QPushButton("🔄 刷新")
        self._refresh_btn.setToolTip("刷新歌曲列表")
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        toolbar_layout.addWidget(self._refresh_btn)
        
        toolbar_layout.addStretch()
        expanded_layout.addLayout(toolbar_layout)
        
        # 搜索框
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索歌曲或标签...")
        self._search_input.textChanged.connect(self._on_search)
        expanded_layout.addWidget(self._search_input)
        
        # 播放列表
        self._playlist_widget = QListWidget()
        self._playlist_widget.itemDoubleClicked.connect(self._on_playlist_item_double_clicked)
        # 设置右键菜单
        self._playlist_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._playlist_widget.customContextMenuRequested.connect(self._show_playlist_context_menu)
        expanded_layout.addWidget(self._playlist_widget)
        
        self._expanded_widget.setVisible(False)
        self._main_layout.addWidget(self._expanded_widget)

    def _setup_shortcuts(self) -> None:
        """设置键盘快捷键。"""
        # 空格：播放/暂停
        self._play_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self._play_shortcut.activated.connect(self._toggle_play)
        
        # Ctrl+Left：上一首
        self._prev_shortcut = QShortcut(
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Left), self
        )
        self._prev_shortcut.activated.connect(self._prev_song)
        
        # Ctrl+Right：下一首
        self._next_shortcut = QShortcut(
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Right), self
        )
        self._next_shortcut.activated.connect(self._next_song)
        
        # Ctrl+L：循环模式
        self._loop_shortcut = QShortcut(
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_L), self
        )
        self._loop_shortcut.activated.connect(self._toggle_loop)
        
        # Ctrl+S：随机播放
        self._shuffle_shortcut = QShortcut(
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_S), self
        )
        self._shuffle_shortcut.activated.connect(self._toggle_shuffle)
        
        # 上下方向键：音量
        self._vol_up_shortcut = QShortcut(Qt.Key.Key_Up, self)
        self._vol_up_shortcut.activated.connect(lambda: self._adjust_volume(0.05))
        
        self._vol_down_shortcut = QShortcut(Qt.Key.Key_Down, self)
        self._vol_down_shortcut.activated.connect(lambda: self._adjust_volume(-0.05))

    def _register_controller_callbacks(self) -> None:
        """注册播放器控制器的回调函数。"""
        try:
            from src.tools.music_player_controller import get_player_controller
            
            controller = get_player_controller()
            
            # 注册播放事件回调
            controller.register_callback("play", self._on_controller_play)
            controller.register_callback("pause", self._on_controller_pause)
            controller.register_callback("resume", self._on_controller_resume)
            controller.register_callback("stop", self._on_controller_stop)
            controller.register_callback("next", self._on_controller_next)
            controller.register_callback("prev", self._on_controller_prev)
            controller.register_callback("seek", self._on_controller_seek)
            controller.register_callback("set_volume", self._on_controller_set_volume)
            controller.register_callback("set_loop", self._on_controller_set_loop)
            controller.register_callback("set_shuffle", self._on_controller_set_shuffle)
            
            logger.info("已注册播放器控制器回调")
            
        except Exception as e:
            logger.error(f"注册控制器回调失败: {e}")

    # ==================== 控制器回调 ====================

    def _on_controller_play(self, song: dict) -> None:
        """控制器播放回调。"""
        self.play_song(song)

    def _on_controller_pause(self) -> None:
        """控制器暂停回调。"""
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()

    def _on_controller_resume(self) -> None:
        """控制器继续回调。"""
        self._player.play()

    def _on_controller_stop(self) -> None:
        """控制器停止回调。"""
        self._player.stop()

    def _on_controller_next(self) -> None:
        """控制器下一首回调。"""
        self._next_song()

    def _on_controller_prev(self) -> None:
        """控制器上一首回调。"""
        self._prev_song()

    def _on_controller_seek(self, position: float, is_percent: bool = False) -> None:
        """控制器跳转回调。"""
        duration = self._player.duration()
        if is_percent:
            pos = int(position * duration)
        else:
            pos = int(position * 1000)  # 假设传入的是秒
        self._player.setPosition(pos)

    def _on_controller_set_volume(self, volume: float) -> None:
        """控制器设置音量回调。"""
        self._audio_output.setVolume(volume)
        self._volume_slider.setValue(int(volume * 100))

    def _on_controller_set_loop(self, mode: str) -> None:
        """控制器设置循环模式回调。"""
        # 更新按钮样式
        if mode == "single":
            self._loop_btn.setText("🔂")
        elif mode == "list":
            self._loop_btn.setText("⟲")
        else:
            self._loop_btn.setText("→")

    def _on_controller_set_shuffle(self, enabled: bool) -> None:
        """控制器设置随机播放回调。"""
        logger.info(f"随机播放设置为: {enabled}")

    # ==================== 播放控制 ====================

    def play_song(self, song: dict) -> None:
        """播放指定歌曲。"""
        file_path = song.get("file_path", "")
        if not file_path or not Path(file_path).exists():
            logger.warning(f"歌曲文件不存在: {file_path}")
            return
        
        # 停止当前播放
        self._player.stop()
        
        # 设置新歌曲
        self._player.setSource(QUrl.fromLocalFile(file_path))
        self._player.play()
        
        # 更新 UI
        title = song.get("title", "未知")
        artist = song.get("artist", "未知艺术家")
        self._song_info.setText(f"{title} - {artist}")
        
        # 发送信号
        self.song_changed.emit(song)
        
        logger.info(f"开始播放: {title} - {artist}")

    def _toggle_play(self) -> None:
        """切换播放/暂停。"""
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            if self._player.source().isEmpty():
                # 没有歌曲时，播放第一首
                self._play_first_song()
            else:
                self._player.play()

    def _play_first_song(self) -> None:
        """播放第一首歌曲。"""
        if not self._music_tool:
            return
        
        songs = self._music_tool.get_library_data().get("songs", {})
        if songs:
            first_song = list(songs.values())[0]
            self._playlist = list(songs.values())
            self._current_index = 0
            self.play_song(first_song)
            self._refresh_playlist()

    def _prev_song(self) -> None:
        """上一首。"""
        if not self._playlist:
            return
        
        # 获取循环模式
        settings = self._music_tool.get_library_data().get("settings", {}) if self._music_tool else {}
        shuffle = settings.get("shuffle", False)
        
        if shuffle:
            import random
            self._current_index = random.randint(0, len(self._playlist) - 1)
        else:
            self._current_index = (self._current_index - 1) % len(self._playlist)
        
        self.play_song(self._playlist[self._current_index])
        self._highlight_current_song()

    def _next_song(self) -> None:
        """下一首。"""
        if not self._playlist:
            return
        
        # 获取循环模式
        settings = self._music_tool.get_library_data().get("settings", {}) if self._music_tool else {}
        shuffle = settings.get("shuffle", False)
        
        if shuffle:
            import random
            self._current_index = random.randint(0, len(self._playlist) - 1)
        else:
            self._current_index = (self._current_index + 1) % len(self._playlist)
        
        self.play_song(self._playlist[self._current_index])
        self._highlight_current_song()

    def _toggle_loop(self) -> None:
        """切换循环模式。"""
        if not self._music_tool:
            return
        
        settings = self._music_tool.get_library_data().setdefault("settings", {})
        current = settings.get("loop_mode", "list")
        
        # 循环切换：list -> single -> none -> list
        mode_cycle = ["list", "single", "none"]
        next_index = (mode_cycle.index(current) + 1) % len(mode_cycle)
        settings["loop_mode"] = mode_cycle[next_index]
        
        # 更新按钮样式
        self._update_loop_button()
        
        # 保存设置
        self._music_tool._save_library()

    def _toggle_shuffle(self) -> None:
        """切换随机播放。"""
        if not self._music_tool:
            return
        
        settings = self._music_tool.get_library_data().setdefault("settings", {})
        current = settings.get("shuffle", False)
        settings["shuffle"] = not current
        
        # 保存设置
        self._music_tool._save_library()

    def _adjust_volume(self, delta: float) -> None:
        """调整音量。"""
        current = self._audio_output.volume()
        new_volume = max(0.0, min(1.0, current + delta))
        self._audio_output.setVolume(new_volume)
        self._volume_slider.setValue(int(new_volume * 100))

    # ==================== 播放器事件 ====================

    def _on_position_changed(self, position: int) -> None:
        """播放位置变化。"""
        duration = self._player.duration()
        if duration > 0:
            progress = int(position / duration * 1000)
            self._progress_slider.blockSignals(True)
            self._progress_slider.setValue(progress)
            self._progress_slider.blockSignals(False)
            
            # 更新时间显示
            self._update_time_display(position, duration)

    def _on_duration_changed(self, duration: int) -> None:
        """歌曲时长变化。"""
        self._update_time_display(0, duration)

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """播放状态变化。"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._play_btn.setText("⏸")
            self._update_timer.start()
            self.play_state_changed.emit(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._play_btn.setText("▶")
            self.play_state_changed.emit(False)
        else:  # StoppedState
            self._play_btn.setText("▶")
            self._update_timer.stop()
            self.play_state_changed.emit(False)
            
            # 检查是否需要播放下一首
            if self._music_tool:
                settings = self._music_tool.get_library_data().get("settings", {})
                loop_mode = settings.get("loop_mode", "list")
                
                if loop_mode == "single":
                    # 单曲循环
                    if self._playlist and 0 <= self._current_index < len(self._playlist):
                        self.play_song(self._playlist[self._current_index])
                elif loop_mode == "list" and self._playlist:
                    # 列表循环
                    self._next_song()

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        """播放错误。"""
        logger.error(f"播放器错误: {error_string}")
        self._song_info.setText(f"播放错误: {error_string}")

    def _on_volume_changed(self, value: int) -> None:
        """音量变化。"""
        volume = value / 100.0
        self._audio_output.setVolume(volume)
        self._original_volume = volume
        self.volume_changed.emit(volume)
        
        # 保存设置
        if self._music_tool:
            settings = self._music_tool.get_library_data().setdefault("settings", {})
            settings["volume"] = volume
            self._music_tool._save_library()

    def _on_seek(self, value: int) -> None:
        """跳转播放位置。"""
        duration = self._player.duration()
        if duration > 0:
            position = int(value / 1000 * duration)
            self._player.setPosition(position)

    # ==================== UI 更新 ====================

    def _update_progress(self) -> None:
        """更新播放进度。"""
        position = self._player.position()
        duration = self._player.duration()
        self._update_time_display(position, duration)

    def _update_time_display(self, position: int, duration: int) -> None:
        """更新时间显示。"""
        def format_time(ms: int) -> str:
            s = ms // 1000
            m, s = s // 60, s % 60
            return f"{m}:{s:02d}"
        
        pos_str = format_time(position)
        dur_str = format_time(duration)
        self._time_label.setText(f"{pos_str}/{dur_str}")

    def _update_loop_button(self) -> None:
        """更新循环按钮样式。"""
        if not self._music_tool:
            return
        
        settings = self._music_tool.get_library_data().get("settings", {})
        mode = settings.get("loop_mode", "list")
        
        if mode == "single":
            self._loop_btn.setText("🔂")
            self._loop_btn.setToolTip("单曲循环")
        elif mode == "list":
            self._loop_btn.setText("⟲")
            self._loop_btn.setToolTip("列表循环")
        else:
            self._loop_btn.setText("→")
            self._loop_btn.setToolTip("顺序播放")

    def _refresh_playlist(self) -> None:
        """刷新播放列表显示。"""
        self._playlist_widget.clear()
        
        for i, song in enumerate(self._playlist):
            title = song.get("title", "未知")
            artist = song.get("artist", "未知艺术家")
            # 显示序号（+1因为从1开始计数）
            item = QListWidgetItem(f"{i + 1:2d}. {title} - {artist}")
            item.setData(Qt.ItemDataRole.UserRole, song.get("id"))
            self._playlist_widget.addItem(item)
        
        # 更新数量标签
        self._count_label.setText(f"({len(self._playlist)})")
        
        self._highlight_current_song()

    def _highlight_current_song(self) -> None:
        """高亮当前播放的歌曲。"""
        self._playlist_widget.setCurrentRow(self._current_index)

    def _show_playlist_context_menu(self, pos: QPoint) -> None:
        """显示播放列表右键菜单。"""
        item = self._playlist_widget.itemAt(pos)
        if item is None:
            return
        
        row = self._playlist_widget.row(item)
        if row < 0 or row >= len(self._playlist):
            return
        
        menu = QMenu(self)
        
        # 置顶
        top_action = QAction("🔝 置顶", self)
        top_action.triggered.connect(lambda: self._move_song_to_top(row))
        menu.addAction(top_action)
        
        # 置底
        bottom_action = QAction("🔻 置底", self)
        bottom_action.triggered.connect(lambda: self._move_song_to_bottom(row))
        menu.addAction(bottom_action)
        
        menu.addSeparator()
        
        # 单曲循环
        loop_action = QAction("🔂 单曲循环", self)
        loop_action.triggered.connect(lambda: self._set_single_loop(row))
        menu.addAction(loop_action)
        
        menu.addSeparator()
        
        # 删除
        delete_action = QAction("🗑️ 删除", self)
        delete_action.triggered.connect(lambda: self._delete_song_from_playlist(row))
        menu.addAction(delete_action)
        
        menu.exec(QCursor.pos())

    def _move_song_to_top(self, row: int) -> None:
        """将歌曲置顶。"""
        if row <= 0 or row >= len(self._playlist):
            return
        song = self._playlist.pop(row)
        self._playlist.insert(0, song)
        # 如果移动的是当前歌曲之前的，调整索引
        if row < self._current_index:
            self._current_index += 1
        elif row == self._current_index:
            self._current_index = 0
        self._refresh_playlist()

    def _move_song_to_bottom(self, row: int) -> None:
        """将歌曲置底。"""
        if row < 0 or row >= len(self._playlist) - 1:
            return
        song = self._playlist.pop(row)
        self._playlist.append(song)
        # 如果移动的是当前歌曲之后的，调整索引
        if row > self._current_index:
            self._current_index -= 1
        elif row == self._current_index:
            self._current_index = len(self._playlist) - 1
        self._refresh_playlist()

    def _set_single_loop(self, row: int) -> None:
        """设置单曲循环并播放。"""
        if row < 0 or row >= len(self._playlist):
            return
        # 设置循环模式为单曲
        if self._music_tool:
            settings = self._music_tool.get_library_data().setdefault("settings", {})
            settings["loop_mode"] = "single"
            self._update_loop_button()
        # 切换到该歌曲并播放
        self._current_index = row
        self.play_song(self._playlist[row])
        self._refresh_playlist()

    def _delete_song_from_playlist(self, row: int) -> None:
        """从播放列表删除歌曲（不从歌曲库删除）。"""
        if row < 0 or row >= len(self._playlist):
            return
        
        song = self._playlist[row]
        
        # 如果删除的是当前歌曲，先停止播放
        if row == self._current_index:
            self._player.stop()
            self._song_info.setText("未播放")
            self._progress_slider.setValue(0)
            self._time_label.setText("0:00/0:00")
        
        # 从列表中移除
        self._playlist.pop(row)
        
        # 调整当前索引
        if row < self._current_index:
            self._current_index -= 1
        elif row == self._current_index and self._current_index >= len(self._playlist):
            self._current_index = max(0, len(self._playlist) - 1)
        
        self._refresh_playlist()

    # ==================== 歌曲管理 ====================

    def _on_add_songs_clicked(self) -> None:
        """添加歌曲按钮点击。"""
        if not self._music_tool:
            return
        
        from PySide6.QtWidgets import QFileDialog
        # 选择多个文件
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择歌曲文件",
            "",
            "音频文件 (*.mp3 *.wav *.flac *.m4a *.ogg);;所有文件 (*)"
        )
        
        if files:
            logger.info(f"用户选择了 {len(files)} 个文件")
            # 调用工具添加歌曲
            import asyncio
            from src.tools.music_player_controller import get_player_controller
            
            # 异步执行添加操作
            async def add_files():
                result = await self._music_tool.execute("add_songs", {
                    "paths": files,
                    "copy_to_library": True
                })
                if result.status == "success":
                    logger.info(f"添加成功：{result.output}")
                    # 刷新列表
                    self._on_refresh_clicked()
                else:
                    logger.error(f"添加失败：{result.error}")
            
            # 使用 QTimer 在主线程执行
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: asyncio.ensure_future(add_files()))

    def _on_scan_folder_clicked(self) -> None:
        """扫描文件夹按钮点击。"""
        if not self._music_tool:
            return
        
        from PySide6.QtWidgets import QFileDialog
        # 选择文件夹
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择音乐文件夹",
            ""
        )
        
        if folder:
            logger.info(f"用户选择了文件夹：{folder}")
            # 调用工具扫描
            import asyncio
            from src.tools.music_player_controller import get_player_controller
            
            async def scan_folder():
                result = await self._music_tool.execute("scan_local_music", {
                    "directory": folder,
                    "recursive": True,
                    "max_results": 100
                })
                if result.status == "success":
                    logger.info(f"扫描成功：{result.output}")
                    # 刷新列表
                    self._on_refresh_clicked()
                else:
                    logger.error(f"扫描失败：{result.error}")
            
            # 使用 QTimer 在主线程执行
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: asyncio.ensure_future(scan_folder()))

    def _on_refresh_clicked(self) -> None:
        """刷新按钮点击。"""
        logger.info("用户手动刷新歌曲列表")
        if self._music_tool:
            # 重新加载歌曲库数据
            library_data = self._music_tool.get_library_data()
            songs = library_data.get("songs", {})
            if songs:
                self._playlist = list(songs.values())
                self._current_index = 0
                
                # 恢复上次播放的歌曲
                state = library_data.get("current_state", {})
                last_id = state.get("last_played_id")
                if last_id and last_id in songs:
                    for i, song in enumerate(self._playlist):
                        if song.get("id") == last_id:
                            self._current_index = i
                            break
            
            # 刷新显示
            self._refresh_playlist()

    # ==================== 搜索 ====================

    def _on_search(self, text: str) -> None:
        """搜索歌曲。"""
        if not self._music_tool:
            return
        
        text = text.lower().strip()
        
        if not text:
            # 显示全部歌曲
            songs = self._music_tool.get_library_data().get("songs", {})
            self._playlist = list(songs.values())
        else:
            # 搜索
            self._playlist = []
            for song in self._music_tool.get_library_data().get("songs", {}).values():
                title = song.get("title", "").lower()
                artist = song.get("artist", "").lower()
                tags = " ".join(song.get("tags", [])).lower()
                
                if text in title or text in artist or text in tags:
                    self._playlist.append(song)
        
        self._refresh_playlist()

    def _on_playlist_item_double_clicked(self, item: QListWidgetItem) -> None:
        """双击播放列表项。"""
        row = self._playlist_widget.row(item)
        if 0 <= row < len(self._playlist):
            self._current_index = row
            self.play_song(self._playlist[row])

    # ==================== 模式切换 ====================

    def _toggle_mode(self) -> None:
        """切换迷你/展开模式（只有两种尺寸）。"""
        self._is_expanded = not self._is_expanded
        
        if self._is_expanded:
            # 展开模式：显示完整播放列表
            self.setFixedSize(*self.EXPANDED_SIZE)
            self._expanded_widget.setVisible(True)
            self._expand_btn.setText("−")
            self._expand_btn.setToolTip("收起播放列表")
            
            # 刷新播放列表
            if self._music_tool:
                songs = self._music_tool.get_library_data().get("songs", {})
                self._playlist = list(songs.values())
                self._refresh_playlist()
                self._highlight_current_song()
        else:
            # 迷你模式：只显示当前歌曲和控制按钮
            self.setFixedSize(*self.MINI_SIZE)
            self._expanded_widget.setVisible(False)
            self._expand_btn.setText("≡")
            self._expand_btn.setToolTip("展开播放列表")
        
        logger.info(f"播放器模式切换：{'展开' if self._is_expanded else '迷你'} ({self.width()}x{self.height()})")

    # ==================== 窗口拖拽 ====================

    def mousePressEvent(self, event) -> None:
        """鼠标按下 - 开始拖拽。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        """鼠标移动 - 拖拽窗口。"""
        if self._dragging and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        """鼠标释放 - 结束拖拽。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_pos = None

    # ==================== Audio Ducking ====================

    def duck_volume(self) -> None:
        """降低音量（TTS 播放时）。"""
        if self._ducking:
            return
        
        self._ducking = True
        settings = self._music_tool.get_library_data().get("settings", {}) if self._music_tool else {}
        ducking_level = settings.get("ducking_level", 0.3)
        self._audio_output.setVolume(self._original_volume * ducking_level)

    def restore_volume(self) -> None:
        """恢复音量（TTS 播放结束后）。"""
        if not self._ducking:
            return
        
        self._ducking = False
        self._audio_output.setVolume(self._original_volume)

    # ==================== 工具方法 ====================

    def set_music_tool(self, tool: MusicPlayerTool) -> None:
        """设置音乐工具实例。"""
        self._music_tool = tool
        
        # 恢复上次的播放状态
        library_data = tool.get_library_data()
        settings = library_data.get("settings", {})
        state = library_data.get("current_state", {})
        
        # 设置音量
        volume = settings.get("volume", 0.8)
        self._audio_output.setVolume(volume)
        self._volume_slider.setValue(int(volume * 100))
        self._original_volume = volume
        
        # 更新循环按钮
        self._update_loop_button()
        
        # 加载歌曲列表
        songs = library_data.get("songs", {})
        if songs:
            self._playlist = list(songs.values())
            self._current_index = 0
            
            # 恢复上次播放的歌曲
            last_id = state.get("last_played_id")
            if last_id and last_id in songs:
                for i, song in enumerate(self._playlist):
                    if song.get("id") == last_id:
                        self._current_index = i
                        break
        
        # 刷新播放列表显示
        self._refresh_playlist()

    def get_current_song(self) -> dict | None:
        """获取当前播放的歌曲。"""
        if 0 <= self._current_index < len(self._playlist):
            return self._playlist[self._current_index]
        return None

    def is_playing(self) -> bool:
        """是否正在播放。"""
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def _on_close(self) -> None:
        """关闭窗口。"""
        logger.info("正在关闭迷你播放器...")
        
        # 先停止定时器，防止关闭后继续触发回调
        if hasattr(self, '_update_timer') and self._update_timer:
            self._update_timer.stop()
            logger.debug("已停止更新定时器")
        
        # 断开所有控制器回调连接，防止在关闭过程中被触发
        try:
            from src.tools.music_player_controller import get_player_controller
            controller = get_player_controller()
            controller.unregister_callback("play", self._on_controller_play)
            controller.unregister_callback("pause", self._on_controller_pause)
            controller.unregister_callback("resume", self._on_controller_resume)
            controller.unregister_callback("stop", self._on_controller_stop)
            controller.unregister_callback("next", self._on_controller_next)
            controller.unregister_callback("prev", self._on_controller_prev)
            controller.unregister_callback("seek", self._on_controller_seek)
            controller.unregister_callback("set_volume", self._on_controller_set_volume)
            controller.unregister_callback("set_loop", self._on_controller_set_loop)
            controller.unregister_callback("set_shuffle", self._on_controller_set_shuffle)
            logger.debug("已取消注册所有控制器回调")
        except Exception as e:
            logger.error(f"取消注册控制器回调失败：{e}")
        
        # 停止播放器
        if self._player:
            self._player.stop()
            self._player.setSource(QUrl())  # 清空音源
            logger.debug("已停止播放器并清空音源")
        
        # 更新 UI 显示
        self._song_info.setText("未播放")
        self._progress_slider.setValue(0)
        self._time_label.setText("0:00/0:00")
        
        # 关闭窗口
        self.close()
        
        # 发出关闭信号
        self.closed.emit()
        
        logger.info("迷你播放器已关闭")

    def closeEvent(self, event) -> None:
        """窗口关闭事件。"""
        logger.debug("收到 closeEvent")
        # 如果已经调用了 _on_close，就直接接受事件
        if self._player and self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            logger.warning("播放器仍在播放，强制停止")
            self._player.stop()
        event.accept()

