"""设备绑定对话框。

用于 WinClaw PC 端与 PWA 用户的设备绑定功能。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QTextEdit,
)

from src.i18n import tr

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DeviceBindDialog(QDialog):
    """设备绑定对话框。"""

    # 信号：绑定成功后触发
    bound_success = Signal(str, str)  # device_id, device_fingerprint

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """构建 UI。"""
        self.setWindowTitle("设备绑定")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # 说明信息
        info_group = QGroupBox("绑定说明")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(120)
        info_text.setHtml("""
        <h3>📱 如何绑定设备？</h3>
        <ol>
            <li>打开 PWA 端（手机或网页）</li>
            <li>进入"设置" → "设备管理"</li>
            <li>点击"绑定新设备"</li>
            <li>生成绑定 Token（有效期 10 分钟）</li>
            <li>复制 64 位 Token</li>
            <li>在下方输入框中粘贴 Token</li>
            <li>点击"确认绑定"</li>
        </ol>
        """)
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)

        # Token 输入
        token_group = QGroupBox("绑定 Token")
        token_layout = QFormLayout(token_group)

        self._token_edit = QLineEdit()
        self._token_edit.setPlaceholderText("请输入 64 位绑定 Token")
        self._token_edit.setMaxLength(128)
        self._token_edit.setStyleSheet("font-family: 'Courier New', monospace; font-size: 14px;")
        token_layout.addRow("Token:", self._token_edit)

        # 验证提示
        hint_label = QLabel("💡 Token 由 PWA 端生成，格式为 64 位字符串")
        hint_label.setStyleSheet("color: gray; font-size: 12px;")
        hint_label.setWordWrap(True)
        token_layout.addRow("", hint_label)

        layout.addWidget(token_group)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._bind_button = QPushButton("确认绑定")
        self._bind_button.setDefault(True)
        self._bind_button.setMinimumWidth(100)
        self._bind_button.clicked.connect(self._on_bind)
        button_layout.addWidget(self._bind_button)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _on_bind(self) -> None:
        """处理绑定请求。"""
        token = self._token_edit.text().strip()

        if not token:
            QMessageBox.warning(self, "警告", "请输入绑定 Token")
            return

        if len(token) < 32:
            QMessageBox.warning(self, "警告", "Token 长度过短，请检查是否正确")
            return

        # 接受并发送信号
        # 实际的绑定逻辑由父组件处理
        logger.info(f"收到绑定 Token: {token[:16]}...")
        self.accept()

    def get_token(self) -> str:
        """获取输入的 Token。"""
        return self._token_edit.text().strip()

    def set_token(self, token: str) -> None:
        """设置 Token（用于测试）。"""
        self._token_edit.setText(token)

    def set_loading(self, loading: bool) -> None:
        """设置加载状态。"""
        self._bind_button.setEnabled(not loading)
        if loading:
            self._bind_button.setText("绑定中...")
        else:
            self._bind_button.setText("确认绑定")

    def show_error(self, message: str) -> None:
        """显示错误信息。"""
        QMessageBox.critical(self, "绑定失败", message)

    def show_success(self, device_id: str, device_name: str) -> None:
        """显示成功信息。"""
        QMessageBox.information(
            self,
            "绑定成功",
            f"✅ 设备绑定成功！\n\n"
            f"设备名称：{device_name}\n"
            f"设备 ID: {device_id[:16]}...\n\n"
            f"现在您可以在 PWA 端查看设备状态并进行远程对话。"
        )
