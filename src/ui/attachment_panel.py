"""附件面板 UI 组件 - 显示和管理已上传的文件附件。

功能:
- 列表显示已上传的文件（图标 + 文件名 + 大小）
- 每个文件有删除按钮
- 支持添加文件和清空全部
- 支持拖拽文件到面板
- 可折叠/展开
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from .attachment_manager import AttachmentInfo, AttachmentManager


class AttachmentItemWidget(QWidget):
    """单个附件项的显示组件。"""
    
    remove_clicked = Signal(str)  # 发出文件路径
    
    def __init__(self, attachment: "AttachmentInfo", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._attachment = attachment
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(8)
        
        # 图标
        icon_label = QLabel(self._attachment.get_icon())
        icon_label.setFixedWidth(20)
        layout.addWidget(icon_label)
        
        # 文件名
        name_label = QLabel(self._attachment.name)
        name_label.setToolTip(self._attachment.path)
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # 限制文件名显示长度
        if len(self._attachment.name) > 25:
            name_label.setText(self._attachment.name[:22] + "...")
        layout.addWidget(name_label)
        
        # 文件大小
        size_label = QLabel(self._attachment.size_display())
        size_label.setStyleSheet("color: #888; font-size: 11px;")
        size_label.setFixedWidth(60)
        layout.addWidget(size_label)
        
        # 删除按钮
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setToolTip("移除此附件")
        remove_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 10px;
                background: #ddd;
                font-weight: bold;
                color: #666;
            }
            QPushButton:hover {
                background: #ff6b6b;
                color: white;
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self._attachment.path))
        layout.addWidget(remove_btn)
    
    @property
    def attachment(self) -> "AttachmentInfo":
        return self._attachment


class AttachmentPanel(QFrame):
    """附件面板 - 显示已上传文件的可折叠面板。"""
    
    # 信号
    add_files_requested = Signal()  # 请求添加文件
    file_removed = Signal(str)      # 文件被移除
    clear_requested = Signal()      # 请求清空
    files_dropped = Signal(list)    # 拖放文件 (paths)
    quick_commands_requested = Signal()  # 快捷命令
    combo_commands_requested = Signal()  # 组合命令
    
    def __init__(self, attachment_manager: "AttachmentManager", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._manager = attachment_manager
        self._is_collapsed = True  # 默认折叠
        self._setup_ui()
        self._connect_signals()
        self.setAcceptDrops(True)
        
        # 设置对象名称，用于主题样式识别
        self.setObjectName("attachmentPanel")
        
        # 初始状态：隐藏内容区
        self._content_widget.setVisible(False)
        self._update_header()
    
    def _setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        # 基础样式，背景色由主题控制
        self.setStyleSheet("""
            QFrame {
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # 标题栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # 折叠/展开按钮 + 标题
        self._toggle_btn = QPushButton("▶ 📎 附件 (0)")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                padding: 4px 8px;
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                background: #e9ecef;
                border-radius: 4px;
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self._toggle_btn)
        
        header_layout.addStretch()
        
        # 添加按钮
        self._add_btn = QPushButton("+ 添加")
        self._add_btn.setFixedHeight(24)
        self._add_btn.setToolTip("添加文件附件")
        self._add_btn.setStyleSheet("""
            QPushButton {
                padding: 2px 10px;
                border: 1px solid #28a745;
                border-radius: 4px;
                background: #28a745;
                color: white;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        self._add_btn.clicked.connect(self.add_files_requested.emit)
        header_layout.addWidget(self._add_btn)
        
        # 清空按钮
        self._clear_btn = QPushButton("清空")
        self._clear_btn.setFixedHeight(24)
        self._clear_btn.setToolTip("清空所有附件")
        self._clear_btn.setStyleSheet("""
            QPushButton {
                padding: 2px 10px;
                border: 1px solid #dc3545;
                border-radius: 4px;
                background: transparent;
                color: #dc3545;
            }
            QPushButton:hover {
                background: #dc3545;
                color: white;
            }
        """)
        self._clear_btn.clicked.connect(self.clear_requested.emit)
        self._clear_btn.setVisible(False)  # 初始隐藏
        header_layout.addWidget(self._clear_btn)

        # 快捷命令按钮
        self._quick_cmd_btn = QPushButton("⚡ 快捷命令")
        self._quick_cmd_btn.setFixedHeight(24)
        self._quick_cmd_btn.setToolTip("常用快捷命令")
        self._quick_cmd_btn.setStyleSheet("""
            QPushButton {
                padding: 2px 8px;
                border: 1px solid #6c757d;
                border-radius: 4px;
                background: transparent;
                color: #6c757d;
            }
            QPushButton:hover {
                background: #6c757d;
                color: white;
            }
        """)
        self._quick_cmd_btn.clicked.connect(self.quick_commands_requested.emit)
        header_layout.addWidget(self._quick_cmd_btn)

        # 组合命令按钮
        self._combo_cmd_btn = QPushButton("🔗 组合命令")
        self._combo_cmd_btn.setFixedHeight(24)
        self._combo_cmd_btn.setToolTip("常用组合命令")
        self._combo_cmd_btn.setStyleSheet("""
            QPushButton {
                padding: 2px 8px;
                border: 1px solid #6c757d;
                border-radius: 4px;
                background: transparent;
                color: #6c757d;
            }
            QPushButton:hover {
                background: #6c757d;
                color: white;
            }
        """)
        self._combo_cmd_btn.clicked.connect(self.combo_commands_requested.emit)
        header_layout.addWidget(self._combo_cmd_btn)
        
        layout.addLayout(header_layout)
        
        # 内容区域（可折叠）
        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.setSpacing(0)
        
        # 文件列表
        self._list_widget = QListWidget()
        self._list_widget.setMinimumHeight(40)
        self._list_widget.setMaximumHeight(150)
        self._list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ced4da;
                border-radius: 4px;
                background: white;
            }
            QListWidget::item {
                padding: 2px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background: #f8f9fa;
            }
        """)
        content_layout.addWidget(self._list_widget)
        
        # 拖放提示
        self._drop_hint = QLabel("拖放文件到此处添加")
        self._drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_hint.setStyleSheet("color: #888; font-size: 11px; padding: 8px;")
        self._drop_hint.setVisible(True)
        content_layout.addWidget(self._drop_hint)
        
        layout.addWidget(self._content_widget)
    
    def _connect_signals(self) -> None:
        """连接附件管理器信号。"""
        self._manager.attachment_added.connect(self._on_attachment_added)
        self._manager.attachment_removed.connect(self._on_attachment_removed)
        self._manager.attachments_cleared.connect(self._on_attachments_cleared)
    
    def _toggle_collapse(self) -> None:
        """切换折叠/展开状态。"""
        self._is_collapsed = not self._is_collapsed
        self._content_widget.setVisible(not self._is_collapsed)
        self._update_header()
    
    def _update_header(self) -> None:
        """更新标题栏显示。"""
        count = self._manager.count
        arrow = "▼" if not self._is_collapsed else "▶"
        self._toggle_btn.setText(f"{arrow} 📎 附件 ({count})")
        
        # 有附件时显示清空按钮
        self._clear_btn.setVisible(count > 0)
        
        # 更新拖放提示
        self._drop_hint.setVisible(count == 0)
        self._list_widget.setVisible(count > 0)
    
    def _on_attachment_added(self, attachment: "AttachmentInfo") -> None:
        """附件添加时的处理。"""
        # 创建列表项
        item = QListWidgetItem(self._list_widget)
        item.setSizeHint(AttachmentItemWidget(attachment).sizeHint())
        
        # 创建自定义组件
        widget = AttachmentItemWidget(attachment)
        widget.remove_clicked.connect(self._on_item_remove_clicked)
        
        self._list_widget.addItem(item)
        self._list_widget.setItemWidget(item, widget)
        
        # 自动展开
        if self._is_collapsed:
            self._toggle_collapse()
        
        self._update_header()
    
    def _on_attachment_removed(self, file_path: str) -> None:
        """附件移除时的处理。"""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            widget = self._list_widget.itemWidget(item)
            if isinstance(widget, AttachmentItemWidget) and widget.attachment.path == file_path:
                self._list_widget.takeItem(i)
                break
        
        self._update_header()
    
    def _on_attachments_cleared(self) -> None:
        """附件清空时的处理。"""
        self._list_widget.clear()
        self._update_header()
    
    def _on_item_remove_clicked(self, file_path: str) -> None:
        """列表项删除按钮点击。"""
        self.file_removed.emit(file_path)
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """拖拽进入事件。"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # 拖拽时的高亮效果，背景色由主题控制
            self.setStyleSheet("""
                QFrame {
                    border-radius: 6px;
                }
            """)
    
    def dragLeaveEvent(self, event) -> None:
        """拖拽离开事件。"""
        # 恢复默认样式，背景色由主题控制
        self.setStyleSheet("""
            QFrame {
                border-radius: 6px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent) -> None:
        """拖拽放下事件。"""
        # 恢复默认样式，背景色由主题控制
        self.setStyleSheet("""
            QFrame {
                border-radius: 6px;
            }
        """)
        
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if local_path and Path(local_path).is_file():
                    paths.append(local_path)
            
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
    
    def expand(self) -> None:
        """展开面板。"""
        if self._is_collapsed:
            self._toggle_collapse()
    
    def collapse(self) -> None:
        """折叠面板。"""
        if not self._is_collapsed:
            self._toggle_collapse()
