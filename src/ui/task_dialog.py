"""任务编辑对话框 — 创建和编辑待办事项/每日任务。

提供两种对话框：
- TodoDialog: 待办事项编辑对话框
- DailyTaskDialog: 每日任务编辑对话框
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

# 类型选项
_CATEGORY_OPTIONS = [
    ("work", "工作"),
    ("study", "学习"),
    ("health", "健康"),
    ("family", "家庭"),
    ("social", "社交"),
    ("finance", "财务"),
    ("hobby", "爱好"),
    ("general", "通用"),
    ("other", "其他"),
]

# 时间周期选项
_TIME_FRAME_OPTIONS = [
    ("today", "今日"),
    ("week", "本周"),
    ("month", "本月"),
    ("quarter", "本季度"),
    ("year", "今年"),
    ("future", "未来"),
]

# 重复规则选项
_RECURRENCE_OPTIONS = [
    ("none", "不重复"),
    ("daily", "每天"),
    ("weekly", "每周"),
    ("monthly", "每月"),
    ("yearly", "每年"),
]


class TodoDialog(QDialog):
    """待办事项编辑对话框。

    Signals:
        todo_created: 创建新待办事项 (数据字典)
        todo_updated: 更新待办事项 (id, 数据字典)
    """

    todo_created = Signal(dict)
    todo_updated = Signal(int, dict)

    def __init__(
        self,
        todo_data: dict[str, Any] | None = None,
        family_members: list[dict] | None = None,
        parent: QWidget | None = None,
    ):
        """初始化对话框。

        Args:
            todo_data: 待办事项数据（编辑时传入）
            family_members: 家庭成员列表（用于选择关系人）
            parent: 父组件
        """
        super().__init__(parent)
        self._todo_data = todo_data or {}
        self._family_members = family_members or []
        self._is_edit = bool(todo_data and todo_data.get("id"))

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        """设置UI。"""
        title = "编辑待办事项" if self._is_edit else "新建待办事项"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setMinimumHeight(550)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QVBoxLayout(basic_group)

        # 标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:*"))
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("请输入任务标题")
        title_layout.addWidget(self._title_edit)
        basic_layout.addLayout(title_layout)

        # 描述
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("描述:"))
        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setPlaceholderText("任务详细描述（可选）")
        self._desc_edit.setMaximumHeight(80)
        desc_layout.addWidget(self._desc_edit)
        basic_layout.addLayout(desc_layout)

        # 类型和周期
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self._category_combo = QComboBox()
        for value, display in _CATEGORY_OPTIONS:
            self._category_combo.addItem(display, value)
        type_layout.addWidget(self._category_combo)
        type_layout.addSpacing(20)
        type_layout.addWidget(QLabel("时间周期:"))
        self._time_frame_combo = QComboBox()
        for value, display in _TIME_FRAME_OPTIONS:
            self._time_frame_combo.addItem(display, value)
        type_layout.addWidget(self._time_frame_combo)
        type_layout.addStretch()
        basic_layout.addLayout(type_layout)

        # 优先级
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("优先级:"))
        self._priority_group = QButtonGroup(self)
        priority_labels = ["最高", "高", "中", "低", "最低"]
        for i, label in enumerate(priority_labels):
            btn = QRadioButton(label)
            self._priority_group.addButton(btn, i + 1)
            priority_layout.addWidget(btn)
        self._priority_group.button(3).setChecked(True)  # 默认中等优先级
        priority_layout.addStretch()
        basic_layout.addLayout(priority_layout)

        layout.addWidget(basic_group)

        # 时间信息
        time_group = QGroupBox("时间安排")
        time_layout = QVBoxLayout(time_group)

        # 开始日期时间
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("开始:"))
        self._start_date_edit = QDateEdit()
        self._start_date_edit.setCalendarPopup(True)
        self._start_date_edit.setDisplayFormat("yyyy-MM-dd")
        start_layout.addWidget(self._start_date_edit)
        self._start_time_edit = QTimeEdit()
        self._start_time_edit.setDisplayFormat("HH:mm")
        start_layout.addWidget(self._start_time_edit)
        start_layout.addStretch()
        time_layout.addLayout(start_layout)

        # 结束日期时间
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("结束:"))
        self._end_date_edit = QDateEdit()
        self._end_date_edit.setCalendarPopup(True)
        self._end_date_edit.setDisplayFormat("yyyy-MM-dd")
        end_layout.addWidget(self._end_date_edit)
        self._end_time_edit = QTimeEdit()
        self._end_time_edit.setDisplayFormat("HH:mm")
        end_layout.addWidget(self._end_time_edit)
        end_layout.addStretch()
        time_layout.addLayout(end_layout)

        # 截止日期
        deadline_layout = QHBoxLayout()
        deadline_layout.addWidget(QLabel("截止:"))
        self._deadline_edit = QLineEdit()
        self._deadline_edit.setPlaceholderText("如：明天、下周五、2026-03-30")
        self._deadline_edit.setMaximumWidth(200)
        deadline_layout.addWidget(self._deadline_edit)
        deadline_layout.addStretch()
        time_layout.addLayout(deadline_layout)

        layout.addWidget(time_group)

        # 关联信息
        relation_group = QGroupBox("关联信息")
        relation_layout = QVBoxLayout(relation_group)

        # 执行人
        assignee_layout = QHBoxLayout()
        assignee_layout.addWidget(QLabel("执行人:"))
        self._assignee_edit = QLineEdit()
        self._assignee_edit.setPlaceholderText("任务执行人（可选）")
        assignee_layout.addWidget(self._assignee_edit)
        assignee_layout.addStretch()
        relation_layout.addLayout(assignee_layout)

        # 重复规则
        recurrence_layout = QHBoxLayout()
        recurrence_layout.addWidget(QLabel("重复:"))
        self._recurrence_combo = QComboBox()
        for value, display in _RECURRENCE_OPTIONS:
            self._recurrence_combo.addItem(display, value)
        recurrence_layout.addWidget(self._recurrence_combo)
        recurrence_layout.addStretch()
        relation_layout.addLayout(recurrence_layout)

        # 备注
        notes_layout = QVBoxLayout()
        notes_layout.addWidget(QLabel("备注:"))
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setPlaceholderText("其他备注信息（可选）")
        self._notes_edit.setMaximumHeight(60)
        notes_layout.addWidget(self._notes_edit)
        relation_layout.addLayout(notes_layout)

        layout.addWidget(relation_group)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # 设置默认日期为今天
        today = datetime.now()
        self._start_date_edit.setDate(today.date())

    def _load_data(self) -> None:
        """加载待办事项数据。"""
        if not self._todo_data:
            return

        # 基本信息
        self._title_edit.setText(self._todo_data.get("title", ""))
        self._desc_edit.setPlainText(self._todo_data.get("description", ""))

        category = self._todo_data.get("category", "general")
        for i in range(self._category_combo.count()):
            if self._category_combo.itemData(i) == category:
                self._category_combo.setCurrentIndex(i)
                break

        time_frame = self._todo_data.get("time_frame", "future")
        for i in range(self._time_frame_combo.count()):
            if self._time_frame_combo.itemData(i) == time_frame:
                self._time_frame_combo.setCurrentIndex(i)
                break

        priority = self._todo_data.get("priority", 3)
        btn = self._priority_group.button(priority)
        if btn:
            btn.setChecked(True)

        # 时间信息
        start_date = self._todo_data.get("start_date")
        if start_date:
            try:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                self._start_date_edit.setDate(dt.date())
            except ValueError:
                pass

        start_time = self._todo_data.get("start_time")
        if start_time:
            try:
                from PySide6.QtCore import QTime
                h, m = map(int, start_time.split(":"))
                self._start_time_edit.setTime(QTime(h, m))
            except (ValueError, AttributeError):
                pass

        end_date = self._todo_data.get("end_date")
        if end_date:
            try:
                dt = datetime.strptime(end_date, "%Y-%m-%d")
                self._end_date_edit.setDate(dt.date())
            except ValueError:
                pass

        self._deadline_edit.setText(self._todo_data.get("deadline", ""))

        # 关联信息
        self._assignee_edit.setText(self._todo_data.get("assignee", ""))

        recurrence = self._todo_data.get("recurrence", "none")
        for i in range(self._recurrence_combo.count()):
            if self._recurrence_combo.itemData(i) == recurrence:
                self._recurrence_combo.setCurrentIndex(i)
                break

        self._notes_edit.setPlainText(self._todo_data.get("notes", ""))

    def _on_accept(self) -> None:
        """确认按钮处理。"""
        title = self._title_edit.text().strip()
        if not title:
            self._title_edit.setFocus()
            return

        # 收集数据
        data = {
            "title": title,
            "description": self._desc_edit.toPlainText(),
            "category": self._category_combo.currentData(),
            "time_frame": self._time_frame_combo.currentData(),
            "priority": self._priority_group.checkedId(),
            "start_date": self._start_date_edit.date().toString("yyyy-MM-dd"),
            "start_time": self._start_time_edit.time().toString("HH:mm"),
            "end_date": self._end_date_edit.date().toString("yyyy-MM-dd"),
            "end_time": self._end_time_edit.time().toString("HH:mm"),
            "deadline": self._deadline_edit.text().strip() or None,
            "assignee": self._assignee_edit.text().strip(),
            "recurrence": self._recurrence_combo.currentData(),
            "notes": self._notes_edit.toPlainText(),
        }

        # 发送信号
        if self._is_edit:
            self.todo_updated.emit(self._todo_data.get("id"), data)
        else:
            self.todo_created.emit(data)

        self.accept()

    def get_data(self) -> dict[str, Any]:
        """获取表单数据。"""
        return {
            "title": self._title_edit.text().strip(),
            "description": self._desc_edit.toPlainText(),
            "category": self._category_combo.currentData(),
            "time_frame": self._time_frame_combo.currentData(),
            "priority": self._priority_group.checkedId(),
            "start_date": self._start_date_edit.date().toString("yyyy-MM-dd"),
            "start_time": self._start_time_edit.time().toString("HH:mm"),
            "end_date": self._end_date_edit.date().toString("yyyy-MM-dd"),
            "end_time": self._end_time_edit.time().toString("HH:mm"),
            "deadline": self._deadline_edit.text().strip() or None,
            "assignee": self._assignee_edit.text().strip(),
            "recurrence": self._recurrence_combo.currentData(),
            "notes": self._notes_edit.toPlainText(),
        }


class DailyTaskDialog(QDialog):
    """每日任务编辑对话框。

    Signals:
        task_created: 创建新每日任务
        task_updated: 更新每日任务
    """

    task_created = Signal(dict)
    task_updated = Signal(int, dict)

    def __init__(
        self,
        task_data: dict[str, Any] | None = None,
        todo_list: list[dict] | None = None,
        parent: QWidget | None = None,
    ):
        """初始化对话框。

        Args:
            task_data: 每日任务数据（编辑时传入）
            todo_list: 待办事项列表（用于选择关联任务）
            parent: 父组件
        """
        super().__init__(parent)
        self._task_data = task_data or {}
        self._todo_list = todo_list or []
        self._is_edit = bool(task_data and task_data.get("id"))

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        """设置UI。"""
        title = "编辑每日任务" if self._is_edit else "新建每日任务"
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 基本信息
        basic_group = QGroupBox("任务信息")
        basic_layout = QVBoxLayout(basic_group)

        # 关联待办事项
        if self._todo_list:
            todo_layout = QHBoxLayout()
            todo_layout.addWidget(QLabel("关联待办:"))
            self._todo_combo = QComboBox()
            self._todo_combo.addItem("无", None)
            for todo in self._todo_list:
                self._todo_combo.addItem(f"{todo.get('title', '')}", todo.get("id"))
            self._todo_combo.currentIndexChanged.connect(self._on_todo_selected)
            todo_layout.addWidget(self._todo_combo)
            basic_layout.addLayout(todo_layout)

        # 标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:*"))
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("请输入任务标题")
        title_layout.addWidget(self._title_edit)
        basic_layout.addLayout(title_layout)

        # 描述
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("描述:"))
        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setPlaceholderText("任务详细描述（可选）")
        self._desc_edit.setMaximumHeight(60)
        desc_layout.addWidget(self._desc_edit)
        basic_layout.addLayout(desc_layout)

        # 类型和优先级
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self._category_combo = QComboBox()
        for value, display in _CATEGORY_OPTIONS:
            self._category_combo.addItem(display, value)
        type_layout.addWidget(self._category_combo)
        type_layout.addSpacing(20)
        type_layout.addWidget(QLabel("优先级:"))
        self._priority_spin = QSpinBox()
        self._priority_spin.setRange(1, 5)
        self._priority_spin.setValue(3)
        type_layout.addWidget(self._priority_spin)
        type_layout.addStretch()
        basic_layout.addLayout(type_layout)

        layout.addWidget(basic_group)

        # 时间安排
        time_group = QGroupBox("时间安排")
        time_layout = QHBoxLayout(time_group)

        time_layout.addWidget(QLabel("计划时间:"))
        self._start_time_edit = QTimeEdit()
        self._start_time_edit.setDisplayFormat("HH:mm")
        time_layout.addWidget(self._start_time_edit)
        time_layout.addWidget(QLabel("-"))
        self._end_time_edit = QTimeEdit()
        self._end_time_edit.setDisplayFormat("HH:mm")
        time_layout.addWidget(self._end_time_edit)
        time_layout.addStretch()

        layout.addWidget(time_group)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # 设置默认时间为当前小时
        now = datetime.now()
        from PySide6.QtCore import QTime
        self._start_time_edit.setTime(QTime(now.hour, 0))
        self._end_time_edit.setTime(QTime(now.hour + 1, 0))

    def _load_data(self) -> None:
        """加载任务数据。"""
        if not self._task_data:
            return

        self._title_edit.setText(self._task_data.get("title", ""))
        self._desc_edit.setPlainText(self._task_data.get("description", ""))

        category = self._task_data.get("category", "general")
        for i in range(self._category_combo.count()):
            if self._category_combo.itemData(i) == category:
                self._category_combo.setCurrentIndex(i)
                break

        self._priority_spin.setValue(self._task_data.get("priority", 3))

        # 时间
        start_time = self._task_data.get("scheduled_start")
        if start_time:
            try:
                from PySide6.QtCore import QTime
                h, m = map(int, start_time.split(":"))
                self._start_time_edit.setTime(QTime(h, m))
            except (ValueError, AttributeError):
                pass

        end_time = self._task_data.get("scheduled_end")
        if end_time:
            try:
                from PySide6.QtCore import QTime
                h, m = map(int, end_time.split(":"))
                self._end_time_edit.setTime(QTime(h, m))
            except (ValueError, AttributeError):
                pass

    def _on_todo_selected(self, index: int) -> None:
        """选择待办事项时自动填充。"""
        if not hasattr(self, "_todo_combo"):
            return

        todo_id = self._todo_combo.currentData()
        if todo_id:
            # 查找对应的待办事项
            for todo in self._todo_list:
                if todo.get("id") == todo_id:
                    self._title_edit.setText(todo.get("title", ""))
                    self._desc_edit.setPlainText(todo.get("description", ""))

                    category = todo.get("category", "general")
                    for i in range(self._category_combo.count()):
                        if self._category_combo.itemData(i) == category:
                            self._category_combo.setCurrentIndex(i)
                            break

                    self._priority_spin.setValue(todo.get("priority", 3))
                    break

    def _on_accept(self) -> None:
        """确认按钮处理。"""
        title = self._title_edit.text().strip()
        if not title:
            self._title_edit.setFocus()
            return

        data = {
            "title": title,
            "description": self._desc_edit.toPlainText(),
            "category": self._category_combo.currentData(),
            "priority": self._priority_spin.value(),
            "scheduled_start": self._start_time_edit.time().toString("HH:mm"),
            "scheduled_end": self._end_time_edit.time().toString("HH:mm"),
        }

        # 如果选择了关联待办
        if hasattr(self, "_todo_combo"):
            todo_id = self._todo_combo.currentData()
            if todo_id:
                data["todo_id"] = todo_id

        if self._is_edit:
            self.task_updated.emit(self._task_data.get("id"), data)
        else:
            self.task_created.emit(data)

        self.accept()

    def get_data(self) -> dict[str, Any]:
        """获取表单数据。"""
        data = {
            "title": self._title_edit.text().strip(),
            "description": self._desc_edit.toPlainText(),
            "category": self._category_combo.currentData(),
            "priority": self._priority_spin.value(),
            "scheduled_start": self._start_time_edit.time().toString("HH:mm"),
            "scheduled_end": self._end_time_edit.time().toString("HH:mm"),
        }

        if hasattr(self, "_todo_combo"):
            todo_id = self._todo_combo.currentData()
            if todo_id:
                data["todo_id"] = todo_id

        return data
