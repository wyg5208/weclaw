"""任务卡片组件 — 用于显示待办事项和每日任务。

提供两种卡片样式：
- TodoCard: 待办事项卡片
- DailyTaskCard: 每日任务卡片
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

# 类型显示名称映射
_CATEGORY_DISPLAY = {
    "work": "工作",
    "study": "学习",
    "health": "健康",
    "family": "家庭",
    "social": "社交",
    "finance": "财务",
    "hobby": "爱好",
    "general": "通用",
    "other": "其他",
}

_TIME_FRAME_DISPLAY = {
    "today": "今日",
    "week": "本周",
    "month": "本月",
    "quarter": "本季度",
    "year": "今年",
    "future": "未来",
}

_STATUS_DISPLAY = {
    "pending": "待办",
    "in_progress": "进行中",
    "completed": "已完成",
    "cancelled": "已取消",
    "paused": "已中止",
}

_PRIORITY_ICONS = {
    1: "🔴",
    2: "🟠",
    3: "🟡",
    4: "🟢",
    5: "⚪",
}

_STATUS_COLORS = {
    "pending": "#f0ad4e",      # 橙色
    "in_progress": "#5bc0de",   # 蓝色
    "completed": "#5cb85c",     # 绿色
    "cancelled": "#d9534f",     # 红色
    "paused": "#777777",        # 灰色
}


class TodoCard(QFrame):
    """待办事项卡片组件。

    Signals:
        start_clicked: 点击"开始"按钮
        complete_clicked: 点击"完成"按钮
        edit_clicked: 点击"编辑"按钮
        delete_clicked: 点击"删除"按钮
    """

    start_clicked = Signal(int)      # todo_id
    complete_clicked = Signal(int)
    edit_clicked = Signal(int)
    delete_clicked = Signal(int)

    def __init__(self, todo_data: dict[str, Any], parent: QWidget | None = None):
        """初始化卡片。

        Args:
            todo_data: 待办事项数据字典
            parent: 父组件
        """
        super().__init__(parent)
        self._todo_data = todo_data
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI。"""
        self.setObjectName("todoCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 标题行：优先级图标 + 标题 + 状态标签
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        priority = self._todo_data.get("priority", 3)
        priority_icon = _PRIORITY_ICONS.get(priority, "🟡")

        title = self._todo_data.get("title", "未命名任务")
        self._title_label = QLabel(f"{priority_icon} {title}")
        self._title_label.setFont(QFont("", 10, QFont.Weight.Bold))
        self._title_label.setWordWrap(True)
        header_layout.addWidget(self._title_label, stretch=1)

        # 状态标签
        status = self._todo_data.get("status", "pending")
        status_display = _STATUS_DISPLAY.get(status, "待办")
        status_color = _STATUS_COLORS.get(status, "#f0ad4e")
        self._status_label = QLabel(status_display)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                color: white;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(self._status_label)

        layout.addLayout(header_layout)

        # 详情行：类型 | 时间周期 | 截止时间
        details_parts = []

        category = self._todo_data.get("category", "general")
        category_display = _CATEGORY_DISPLAY.get(category, "通用")
        details_parts.append(f"类型: {category_display}")

        time_frame = self._todo_data.get("time_frame", "future")
        time_frame_display = _TIME_FRAME_DISPLAY.get(time_frame, "未来")
        details_parts.append(f"周期: {time_frame_display}")

        deadline = self._todo_data.get("deadline")
        if deadline:
            details_parts.append(f"截止: {deadline}")

        details_text = " | ".join(details_parts)
        self._detail_label = QLabel(details_text)
        self._detail_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self._detail_label)

        # 描述（如果有）
        description = self._todo_data.get("description", "")
        if description:
            desc_label = QLabel(description[:50] + ("..." if len(description) > 50 else ""))
            desc_label.setStyleSheet("color: #666; font-size: 10px;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # 操作按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        todo_id = self._todo_data.get("id")

        if status == "pending":
            start_btn = QPushButton("开始")
            start_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
            start_btn.clicked.connect(lambda: self.start_clicked.emit(todo_id))
            btn_layout.addWidget(start_btn)

        if status in ("pending", "in_progress"):
            complete_btn = QPushButton("完成")
            complete_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
            complete_btn.clicked.connect(lambda: self.complete_clicked.emit(todo_id))
            btn_layout.addWidget(complete_btn)

        edit_btn = QPushButton("编辑")
        edit_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(todo_id))
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(todo_id))
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 设置卡片样式
        self.setStyleSheet("""
            #todoCard {
                background-color: rgba(30, 25, 70, 0.3);
                border: 1px solid #6c3483;
                border-radius: 8px;
            }
            #todoCard:hover {
                border-color: #9b59b6;
                background-color: rgba(155, 89, 182, 0.1);
            }
        """)

    def update_data(self, todo_data: dict[str, Any]) -> None:
        """更新卡片数据。"""
        self._todo_data = todo_data
        # 重新构建UI
        # 简化处理：直接刷新标题和状态
        priority = todo_data.get("priority", 3)
        priority_icon = _PRIORITY_ICONS.get(priority, "🟡")
        self._title_label.setText(f"{priority_icon} {todo_data.get('title', '')}")

        status = todo_data.get("status", "pending")
        status_display = _STATUS_DISPLAY.get(status, "待办")
        status_color = _STATUS_COLORS.get(status, "#f0ad4e")
        self._status_label.setText(status_display)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                color: white;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)


class DailyTaskCard(QFrame):
    """每日任务卡片组件。

    Signals:
        start_clicked: 点击"开始"按钮
        complete_clicked: 点击"完成"按钮
        cancel_clicked: 点击"取消"按钮
    """

    start_clicked = Signal(int)      # task_id
    complete_clicked = Signal(int)
    cancel_clicked = Signal(int)

    def __init__(self, task_data: dict[str, Any], parent: QWidget | None = None):
        """初始化卡片。

        Args:
            task_data: 每日任务数据字典
            parent: 父组件
        """
        super().__init__(parent)
        self._task_data = task_data
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI。"""
        self.setObjectName("dailyTaskCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 标题行：时间 + 标题 + 状态
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        # 计划时间
        scheduled_start = self._task_data.get("scheduled_start", "")
        if scheduled_start:
            time_label = QLabel(f"⏰ {scheduled_start}")
            time_label.setStyleSheet("color: #00ffff; font-size: 11px; font-weight: bold;")
            header_layout.addWidget(time_label)

        priority = self._task_data.get("priority", 3)
        priority_icon = _PRIORITY_ICONS.get(priority, "🟡")
        title = self._task_data.get("title", "未命名任务")
        self._title_label = QLabel(f"{priority_icon} {title}")
        self._title_label.setFont(QFont("", 10, QFont.Weight.Bold))
        self._title_label.setWordWrap(True)
        header_layout.addWidget(self._title_label, stretch=1)

        # 状态标签
        status = self._task_data.get("status", "pending")
        status_display = _STATUS_DISPLAY.get(status, "待办")
        status_color = _STATUS_COLORS.get(status, "#f0ad4e")
        self._status_label = QLabel(status_display)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                color: white;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(self._status_label)

        layout.addLayout(header_layout)

        # 详情行
        details_parts = []

        category = self._task_data.get("category")
        if category:
            category_display = _CATEGORY_DISPLAY.get(category, "通用")
            details_parts.append(category_display)

        # 来源标识
        source = self._task_data.get("source", "manual")
        if source == "ai_suggested":
            details_parts.append("🤖 AI推荐")
        elif source == "from_todo":
            details_parts.append("📋 来自待办")

        if details_parts:
            details_text = " | ".join(details_parts)
            detail_label = QLabel(details_text)
            detail_label.setStyleSheet("color: #888; font-size: 10px;")
            layout.addWidget(detail_label)

        # 操作按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        task_id = self._task_data.get("id")

        if status == "pending":
            start_btn = QPushButton("开始")
            start_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
            start_btn.clicked.connect(lambda: self.start_clicked.emit(task_id))
            btn_layout.addWidget(start_btn)

        if status in ("pending", "in_progress"):
            complete_btn = QPushButton("完成")
            complete_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
            complete_btn.clicked.connect(lambda: self.complete_clicked.emit(task_id))
            btn_layout.addWidget(complete_btn)

        if status != "completed":
            cancel_btn = QPushButton("取消")
            cancel_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
            cancel_btn.clicked.connect(lambda: self.cancel_clicked.emit(task_id))
            btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 设置卡片样式
        self.setStyleSheet("""
            #dailyTaskCard {
                background-color: rgba(30, 25, 70, 0.3);
                border: 1px solid #6c3483;
                border-radius: 8px;
            }
            #dailyTaskCard:hover {
                border-color: #9b59b6;
                background-color: rgba(155, 89, 182, 0.1);
            }
        """)

    def update_status(self, status: str) -> None:
        """更新状态显示。"""
        self._task_data["status"] = status
        status_display = _STATUS_DISPLAY.get(status, "待办")
        status_color = _STATUS_COLORS.get(status, "#f0ad4e")
        self._status_label.setText(status_display)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                color: white;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)


# ----------------------------------------------------------------------
# 辅助函数
# ----------------------------------------------------------------------

def create_time_frame_filter(parent: QWidget) -> tuple[QWidget, Callable[[str], None]]:
    """创建时间周期筛选器。

    Returns:
        (筛选器组件, 设置回调函数)
    """
    from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton

    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    button_group = QButtonGroup(widget)
    time_frames = [
        ("today", "今日"),
        ("week", "本周"),
        ("month", "本月"),
        ("quarter", "季度"),
        ("year", "今年"),
        ("future", "未来"),
    ]

    current_filter = ["today"]  # 默认选中今日

    def on_button_clicked(checked: bool, tf: str) -> None:
        if checked:
            current_filter[0] = tf

    for i, (tf, display) in enumerate(time_frames):
        btn = QPushButton(display)
        btn.setCheckable(True)
        btn.setChecked(i == 0)
        btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                padding: 4px 10px;
                border-radius: 4px;
            }
            QPushButton:checked {
                background-color: #9b59b6;
                color: white;
            }
        """)
        btn.clicked.connect(lambda checked, t=tf: on_button_clicked(checked, t))
        button_group.addButton(btn, i)
        layout.addWidget(btn)

    def get_current_filter() -> str:
        return current_filter[0]

    return widget, get_current_filter


def create_status_filter(parent: QWidget) -> tuple[QWidget, Callable[[str], None]]:
    """创建状态筛选器。

    Returns:
        (筛选器组件, 获取当前筛选值函数)
    """
    from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel

    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    label = QLabel("状态:")
    label.setStyleSheet("font-size: 10px;")
    layout.addWidget(label)

    combo = QComboBox()
    combo.addItems(["全部", "待办", "进行中", "已完成", "已取消"])
    combo.setFixedWidth(80)
    combo.setStyleSheet("font-size: 10px;")
    layout.addWidget(combo)

    status_map = {
        "全部": None,
        "待办": "pending",
        "进行中": "in_progress",
        "已完成": "completed",
        "已取消": "cancelled",
    }

    def get_current_status() -> str | None:
        return status_map.get(combo.currentText())

    return widget, get_current_status
