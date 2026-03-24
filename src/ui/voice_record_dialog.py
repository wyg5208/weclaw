"""录音可视化弹窗。

提供录音过程中的可视化反馈，让用户清楚地知道：
- 何时可以开始说话
- 录音进行中的状态（倒计时、音量指示）
- 识别处理中的状态
- 最终结果

支持三种录音模式：
1. 定时录音：显示倒计时进度条
2. VAD录音：显示已录音时长，说完自动停止
3. 对话模式持续监听：显示动态监听状态
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QWidget,
    QSizePolicy,
)

logger = logging.getLogger(__name__)


class RecordState(Enum):
    """录音状态。"""
    PREPARING = "preparing"       # 准备中
    RECORDING = "recording"       # 录音中
    PROCESSING = "processing"     # 识别处理中
    SUCCESS = "success"           # 识别成功
    ERROR = "error"               # 出错
    CANCELLED = "cancelled"       # 已取消


class VoiceWaveWidget(QWidget):
    """语音波形动画控件。

    在录音时显示跳动的音量条动画，给用户直观的视觉反馈。
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._bars = 7
        self._bar_heights = [0.3] * self._bars
        self._active = False
        self._tick = 0
        self.setMinimumSize(120, 50)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._animate)

    def start(self) -> None:
        """启动动画。"""
        self._active = True
        self._tick = 0
        self._timer.start()
        self.update()

    def stop(self) -> None:
        """停止动画。"""
        self._active = False
        self._timer.stop()
        self._bar_heights = [0.3] * self._bars
        self.update()

    def _animate(self) -> None:
        """更新动画帧。"""
        import math
        self._tick += 1
        for i in range(self._bars):
            # 生成节奏感的波动效果
            phase = self._tick * 0.5 + i * 0.8
            self._bar_heights[i] = 0.3 + 0.7 * abs(math.sin(phase))
        self.update()

    def paintEvent(self, event) -> None:
        """绘制音量条。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_width = max(6, w // (self._bars * 2))
        gap = max(3, bar_width // 2)
        total_width = self._bars * bar_width + (self._bars - 1) * gap
        x_start = (w - total_width) // 2

        for i in range(self._bars):
            bar_h = int(h * self._bar_heights[i])
            x = x_start + i * (bar_width + gap)
            y = (h - bar_h) // 2

            if self._active:
                color = QColor("#ff4444")
            else:
                color = QColor("#cccccc")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(x, y, bar_width, bar_h, bar_width // 2, bar_width // 2)

        painter.end()


class VoiceRecordState:
    """录音状态管理器（轻量级，不使用独立对话框）。

    通过信号通知主窗口更新录音状态UI，而不是弹出独立对话框。
    避免遮挡主界面的对话区域。
    """

    # 信号
    stop_requested = Signal()          # 用户请求停止录音
    cancelled = Signal()               # 用户取消
    state_changed = Signal(object, str, float)  # (状态, 状态文本, 已录时长)

    def __init__(
        self,
        duration: float = 30.0,
        parent: Optional[QWidget] = None,
        *,
        vad_mode: bool = True,
    ):
        """初始化录音状态管理器。

        Args:
            duration: 录音时长(秒), VAD模式下为最大上限
            parent: 父窗口（用于QObject父级关系）
            vad_mode: 是否为VAD模式（说完自动停止）
        """
        # 注意：这个类不是QWidget，但需要Signal功能
        # 实际使用时会作为QObject的成员
        self._duration = duration
        self._elapsed = 0.0
        self._state = RecordState.PREPARING
        self._result_text = ""
        self._vad_mode = vad_mode
        self._countdown_timer: Optional[QTimer] = None
        self._parent = parent

    def _emit_state(self, status_text: str) -> None:
        """发送状态更新信号。"""
        try:
            self.state_changed.emit(self._state, status_text, self._elapsed)
        except RuntimeError:
            pass  # 信号可能未连接

    # ====== 状态切换 ======

    def start_recording(self) -> None:
        """切换到录音中状态。"""
        self._state = RecordState.RECORDING
        self._elapsed = 0.0

        # 启动计时器
        if self._parent:
            self._countdown_timer = QTimer(self._parent)
            self._countdown_timer.setInterval(100)  # 100ms 更新一次
            self._countdown_timer.timeout.connect(self._on_countdown_tick)
            self._countdown_timer.start()

        self._emit_state(f"🔴 0.0s")

    def set_processing(self) -> None:
        """切换到识别处理中状态。"""
        self._state = RecordState.PROCESSING

        if self._countdown_timer:
            self._countdown_timer.stop()
            self._countdown_timer = None

        self._emit_state("⏳ 识别中...")

    def set_success(self, text: str) -> None:
        """切换到识别成功状态。

        Args:
            text: 识别出的文字
        """
        self._state = RecordState.SUCCESS
        self._result_text = text
        self._emit_state("✅ 完成")

    def set_error(self, error_msg: str) -> None:
        """切换到错误状态。

        Args:
            error_msg: 错误信息
        """
        self._state = RecordState.ERROR

        if self._countdown_timer:
            self._countdown_timer.stop()
            self._countdown_timer = None

        self._emit_state("❌ 失败")

    def set_no_speech(self) -> None:
        """未检测到语音。"""
        self._state = RecordState.ERROR

        if self._countdown_timer:
            self._countdown_timer.stop()
            self._countdown_timer = None

        self._emit_state("🔇 无语音")

    def cancel(self) -> None:
        """取消录音。"""
        if self._countdown_timer:
            self._countdown_timer.stop()
            self._countdown_timer = None
        self._state = RecordState.CANCELLED
        self.cancelled.emit()

    def get_elapsed(self) -> float:
        """获取已录音时长。"""
        return self._elapsed

    def get_state(self) -> RecordState:
        """获取当前状态。"""
        return self._state

    # ====== 内部方法 ======

    def _on_countdown_tick(self) -> None:
        """计时更新。"""
        self._elapsed += 0.1

        # 发送状态更新
        self._emit_state(f"🔴 {self._elapsed:.1f}s")

        # 达到最大时长自动停止计时器
        if self._elapsed >= self._duration:
            if self._countdown_timer:
                self._countdown_timer.stop()
                self._countdown_timer = None

    def request_stop(self) -> None:
        """请求停止录音。"""
        self.stop_requested.emit()


# ====== 保留原有对话框类作为可选方案（标记为Legacy） ======

class VoiceRecordDialog(QDialog):
    """录音可视化弹窗（传统版本，已被VoiceRecordState替代）。

    保留此类以备需要独立对话框的场景。
    默认情况下，新代码应使用VoiceRecordState配合主窗口内联UI。
    """

    # 信号
    stop_requested = Signal()          # 用户请求停止录音
    cancelled = Signal()               # 用户取消

    def __init__(
        self,
        duration: float = 30.0,
        parent: Optional[QWidget] = None,
        *,
        vad_mode: bool = True,
    ):
        """初始化录音弹窗。

        Args:
            duration: 录音时长(秒), VAD模式下为最大上限
            parent: 父窗口
            vad_mode: 是否为VAD模式（说完自动停止）
        """
        super().__init__(parent)
        self._duration = duration
        self._elapsed = 0.0
        self._state = RecordState.PREPARING
        self._result_text = ""
        self._vad_mode = vad_mode

        self._countdown_timer: Optional[QTimer] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化界面。"""
        self.setWindowTitle("语音录入")
        self.setFixedSize(280, 200)  # 缩小尺寸
        self.setModal(False)  # 非模态，不阻塞主窗口
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        # === 状态图标 ===
        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_font = QFont()
        icon_font.setPointSize(32)
        self._icon_label.setFont(icon_font)
        self._icon_label.setText("🎤")
        layout.addWidget(self._icon_label)

        # === 状态文字 ===
        self._status_label = QLabel("准备录音...")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(11)
        status_font.setBold(True)
        self._status_label.setFont(status_font)
        layout.addWidget(self._status_label)

        # === 提示文字 ===
        self._hint_label = QLabel("即将开始，请准备说话")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._hint_label)

        # === 结果文字区域 ===
        self._result_label = QLabel("")
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setWordWrap(True)
        self._result_label.setStyleSheet("color: #333; font-size: 11px;")
        self._result_label.setVisible(False)
        self._result_label.setMaximumHeight(40)
        layout.addWidget(self._result_label)

        # === 按钮栏 ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._stop_btn = QPushButton("⏹ 停止")
        self._stop_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #ff4444;"
            "  color: white;"
            "  border: none;"
            "  border-radius: 4px;"
            "  padding: 6px 16px;"
            "  font-size: 12px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "  background-color: #cc3333;"
            "}"
        )
        self._stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self._stop_btn)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #f0f0f0;"
            "  border: 1px solid #ddd;"
            "  border-radius: 4px;"
            "  padding: 6px 16px;"
            "  font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #e0e0e0;"
            "}"
        )
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

    # ====== 状态切换 ======

    def start_recording(self) -> None:
        """切换到录音中状态。"""
        self._state = RecordState.RECORDING
        self._elapsed = 0.0

        self._icon_label.setText("🔴")
        self._status_label.setText("录音中...")
        self._status_label.setStyleSheet("color: #ff4444; font-size: 11px; font-weight: bold;")

        if self._vad_mode:
            self._hint_label.setText("请说话，说完后自动停止")
            self._hint_label.setStyleSheet("color: #ff6b6b; font-size: 11px;")
        else:
            self._hint_label.setText("请开始说话")
            self._hint_label.setStyleSheet("color: #ff6b6b; font-size: 11px;")

        self._stop_btn.setEnabled(True)
        self._result_label.setVisible(False)

        # 启动计时器
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(100)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)
        self._countdown_timer.start()

        self.show()
        self.raise_()
        self.activateWindow()

    def set_processing(self) -> None:
        """切换到识别处理中状态。"""
        self._state = RecordState.PROCESSING

        if self._countdown_timer:
            self._countdown_timer.stop()

        self._icon_label.setText("⏳")
        self._status_label.setText("识别中...")
        self._status_label.setStyleSheet("color: #f39c12; font-size: 11px; font-weight: bold;")
        self._hint_label.setText("正在将语音转为文字...")
        self._hint_label.setStyleSheet("color: #888; font-size: 11px;")

        self._stop_btn.setEnabled(False)
        self._stop_btn.setText("处理中...")

    def set_success(self, text: str) -> None:
        """切换到识别成功状态。

        Args:
            text: 识别出的文字
        """
        self._state = RecordState.SUCCESS
        self._result_text = text

        self._icon_label.setText("✅")
        self._status_label.setText("识别完成")
        self._status_label.setStyleSheet("color: #27ae60; font-size: 11px; font-weight: bold;")

        display_text = text if len(text) <= 40 else text[:37] + "..."
        self._hint_label.setText("\u201c" + display_text + "\u201d")
        self._hint_label.setStyleSheet("color: #333; font-size: 11px;")

        self._stop_btn.setVisible(False)
        self._cancel_btn.setText("关闭")

        # 1.5秒后自动关闭
        QTimer.singleShot(1500, self._auto_close)

    def set_error(self, error_msg: str) -> None:
        """切换到错误状态。

        Args:
            error_msg: 错误信息
        """
        self._state = RecordState.ERROR

        if self._countdown_timer:
            self._countdown_timer.stop()

        self._icon_label.setText("❌")
        self._status_label.setText("识别失败")
        self._status_label.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
        self._hint_label.setText(error_msg[:50] if len(error_msg) > 50 else error_msg)
        self._hint_label.setStyleSheet("color: #e74c3c; font-size: 11px;")

        self._stop_btn.setVisible(False)
        self._cancel_btn.setText("关闭")

        # 2秒后自动关闭
        QTimer.singleShot(2000, self._auto_close)

    def set_no_speech(self) -> None:
        """未检测到语音。"""
        self._state = RecordState.ERROR

        if self._countdown_timer:
            self._countdown_timer.stop()

        self._icon_label.setText("🔇")
        self._status_label.setText("未检测到语音")
        self._status_label.setStyleSheet("color: #f39c12; font-size: 11px; font-weight: bold;")
        self._hint_label.setText("请确认麦克风是否正常")
        self._hint_label.setStyleSheet("color: #888; font-size: 11px;")

        self._stop_btn.setVisible(False)
        self._cancel_btn.setText("关闭")

        # 2秒后自动关闭
        QTimer.singleShot(2000, self._auto_close)

    # ====== 对话模式支持 ======

    def start_listening(self) -> None:
        """切换到持续监听状态（对话模式）。"""
        self._state = RecordState.RECORDING

        self._icon_label.setText("🔴")
        self._status_label.setText("监听中...")
        self._status_label.setStyleSheet("color: #ff4444; font-size: 11px; font-weight: bold;")
        self._hint_label.setText("请说话，系统会自动识别")
        self._hint_label.setStyleSheet("color: #ff6b6b; font-size: 11px;")

        self._stop_btn.setText("⏹ 停止")
        self._stop_btn.setEnabled(True)

        self.show()
        self.raise_()
        self.activateWindow()

    # ====== 内部方法 ======

    def _on_countdown_tick(self) -> None:
        """计时更新。"""
        self._elapsed += 0.1

        if self._vad_mode:
            self._status_label.setText(f"录音中 {self._elapsed:.1f}s")
            if self._elapsed >= self._duration:
                if self._countdown_timer:
                    self._countdown_timer.stop()
        else:
            if self._elapsed >= self._duration:
                if self._countdown_timer:
                    self._countdown_timer.stop()

    def _on_stop(self) -> None:
        """停止录音按钮。"""
        self.stop_requested.emit()

    def _on_cancel(self) -> None:
        """取消按钮。"""
        if self._countdown_timer:
            self._countdown_timer.stop()
        self.cancelled.emit()
        self.close()

    def _auto_close(self) -> None:
        """自动关闭。"""
        if self.isVisible():
            self.close()

    def closeEvent(self, event) -> None:
        """关闭事件。"""
        if self._countdown_timer:
            self._countdown_timer.stop()
        super().closeEvent(event)
