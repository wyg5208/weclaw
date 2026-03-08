"""设置对话框。

功能：
- API Key 管理（加密存储、显示遮蔽、编辑、删除）
- 默认模型选择
- 主题切换（亮色 / 暗色 / 跟随系统）
- 全局快捷键自定义
- 设置保存后立即生效
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .keystore import (
    API_KEY_ENTRIES,
    delete_key,
    has_key,
    load_key,
    mask_key,
    save_key,
)
from .theme import Theme
from src.i18n import tr

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """设置对话框。"""

    # 信号
    theme_changed = Signal(str)  # "light" / "dark" / "system"
    model_changed = Signal(str)  # model display name
    hotkey_changed = Signal(str)  # 新快捷键字符串
    keys_updated = Signal()  # API Key 更新后
    whisper_model_changed = Signal(str)  # Whisper 模型名称
    language_changed = Signal(str)  # 语言切换后

    # Whisper 模型列表和描述
    WHISPER_MODELS = [
        ("tiny", "Tiny - 最快，准确度较低 (~1GB 内存)"),
        ("base", "Base - 快速，准确度中等 (~1GB 内存) [默认]"),
        ("small", "Small - 中等，准确度较高 (~2GB 内存)"),
        ("medium", "Medium - 较慢，准确度高 (~5GB 内存)"),
        ("large", "Large - 最慢，准确度最高 (~10GB 内存)"),
    ]

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        current_theme: str = "light",
        current_model: str = "",
        available_models: list[str] | None = None,
        current_hotkey: str = "Win+Shift+Space",
        current_whisper_model: str = "base",
        mcp_manager: object | None = None,  # MCPClientManager
    ) -> None:
        super().__init__(parent)
        self._current_theme = current_theme
        self._current_model = current_model
        self._available_models = available_models or []
        self._current_hotkey = current_hotkey
        self._current_whisper_model = current_whisper_model
        self._mcp_manager = mcp_manager
        self._key_edits: dict[str, QLineEdit] = {}
        self._setup_ui()
        # 延迟加载设备状态
        self._load_device_status()

    def _setup_ui(self) -> None:
        """构建 UI。"""
        self.setWindowTitle(tr("设置"))
        self.setMinimumSize(520, 400)
        self.resize(560, 440)

        layout = QVBoxLayout(self)

        # 选项卡
        tabs = QTabWidget()
        tabs.addTab(self._create_apikey_tab(), tr("API 密钥"))
        tabs.addTab(self._create_general_tab(), tr("通用"))
        tabs.addTab(self._create_mcp_tab(), "MCP")
        tabs.addTab(self._create_update_tab(), tr("更新"))
        layout.addWidget(tabs)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton(tr("关闭"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    # ----------------------------------------------------------------
    # API Key 选项卡
    # ----------------------------------------------------------------

    def _create_apikey_tab(self) -> QWidget:
        """创建 API Key 管理选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("API Key 使用 Windows DPAPI 加密存储，不会以明文保存在磁盘。")
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(info)

        group = QGroupBox("API 密钥管理")
        form = QFormLayout(group)

        for entry in API_KEY_ENTRIES:
            env_var = entry["env"]
            label_text = entry["label"]

            row = QHBoxLayout()

            # 密钥输入框
            edit = QLineEdit()
            edit.setPlaceholderText(entry["hint"])
            edit.setEchoMode(QLineEdit.EchoMode.Password)

            # 如果已存储，显示遮蔽值
            stored = load_key(env_var)
            if stored:
                edit.setText(stored)
                edit.setPlaceholderText(tr("已存储") + " " + mask_key(stored))

            self._key_edits[env_var] = edit
            row.addWidget(edit, stretch=1)

            # 显示/隐藏按钮
            toggle_btn = QPushButton("👁")
            toggle_btn.setFixedWidth(36)
            toggle_btn.setToolTip(tr("显示/隐藏密钥"))
            toggle_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 2px;
                    background: transparent;
                }
                QPushButton:hover {
                    background: #e0e0e0;
                    border-radius: 4px;
                }
            """)
            toggle_btn.clicked.connect(
                lambda checked, e=edit: self._toggle_echo(e)
            )
            row.addWidget(toggle_btn)

            # 保存按钮
            save_btn = QPushButton(tr("保存"))
            save_btn.setFixedWidth(50)
            save_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 2px;
                    background: transparent;
                    color: #0078d4;
                }
                QPushButton:hover {
                    background: #e0e0e0;
                    border-radius: 4px;
                }
            """)
            save_btn.clicked.connect(
                lambda checked, ev=env_var, e=edit: self._save_key(ev, e)
            )
            row.addWidget(save_btn)

            # 删除按钮
            del_btn = QPushButton("✕")
            del_btn.setFixedWidth(30)
            del_btn.setToolTip(tr("删除密钥"))
            del_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 2px;
                    background: transparent;
                    color: #dc3545;
                }
                QPushButton:hover {
                    background: #ffebee;
                    border-radius: 4px;
                }
            """)
            del_btn.clicked.connect(
                lambda checked, ev=env_var, e=edit: self._delete_key(ev, e)
            )
            row.addWidget(del_btn)

            form.addRow(label_text + ":", row)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _toggle_echo(self, edit: QLineEdit) -> None:
        """切换密钥显示/隐藏。"""
        if edit.echoMode() == QLineEdit.EchoMode.Password:
            edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            edit.setEchoMode(QLineEdit.EchoMode.Password)

    def _save_key(self, env_var: str, edit: QLineEdit) -> None:
        """保存 API Key。"""
        value = edit.text().strip()
        if not value:
            QMessageBox.warning(self, tr("提示"), tr("请输入密钥值"))
            return
        if save_key(env_var, value):
            # 同时注入到当前进程环境变量
            import os
            os.environ[env_var] = value
            edit.setPlaceholderText(tr("已存储") + " " + mask_key(value))
            self.keys_updated.emit()
            QMessageBox.information(self, tr("成功"), f"{env_var} " + tr("已安全存储"))
        else:
            QMessageBox.critical(self, tr("错误"), tr("保存失败，请重试"))

    def _delete_key(self, env_var: str, edit: QLineEdit) -> None:
        """删除 API Key。"""
        if not has_key(env_var):
            return
        reply = QMessageBox.question(
            self, tr("确认"), f"{tr('确定删除')} {env_var}？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_key(env_var)
            edit.clear()
            edit.setPlaceholderText("")
            self.keys_updated.emit()

    # ----------------------------------------------------------------
    # 通用选项卡
    # ----------------------------------------------------------------

    def _create_general_tab(self) -> QWidget:
        """创建通用设置选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # ---------- 主题 ----------
        theme_group = QGroupBox(tr("外观"))
        theme_layout = QFormLayout(theme_group)

        self._theme_combo = QComboBox()
        # 主题选项：基础 + 时尚渐变主题 + 深色系主题 + 赛博朋克主题
        theme_items = [
            tr("亮色"),
            tr("暗色"),
            tr("跟随系统"),
            tr("海洋蓝"),
            tr("森林绿"),
            tr("日落橙"),
            tr("紫色梦幻"),
            tr("玫瑰粉"),
            tr("极简白"),
            tr("深蓝色"),
            tr("深棕色"),
            tr("赛博朋克紫"),
            tr("赛博宇宙蓝"),  # 新增赛博宇宙蓝主题
        ]
        self._theme_combo.addItems(theme_items)
        _theme_map = {
            "light": 0,
            "dark": 1,
            "system": 2,
            "ocean_blue": 3,
            "forest_green": 4,
            "sunset_orange": 5,
            "purple_dream": 6,
            "pink_rose": 7,
            "minimal_white": 8,
            "deep_blue": 9,
            "deep_brown": 10,
            "cyberpunk_purple": 11,
            "cyber_universe_blue": 12,  # 新增赛博宇宙蓝主题映射
        }
        self._theme_combo.setCurrentIndex(_theme_map.get(self._current_theme, 0))
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addRow(tr("主题") + ":", self._theme_combo)

        # 语言切换
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("简体中文", "zh_CN")
        self._lang_combo.addItem("English", "en_US")
        # 设置当前语言
        from src.i18n import get_i18n_manager
        i18n = get_i18n_manager()
        current_lang = i18n.current_language
        for i in range(self._lang_combo.count()):
            if self._lang_combo.itemData(i) == current_lang:
                self._lang_combo.setCurrentIndex(i)
                break
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        theme_layout.addRow(tr("语言") + ":", self._lang_combo)

        layout.addWidget(theme_group)

        # ---------- 模型 ----------
        model_group = QGroupBox(tr("AI 模型"))
        model_layout = QFormLayout(model_group)

        self._model_combo = QComboBox()
        if self._available_models:
            self._model_combo.addItems(self._available_models)
        if self._current_model:
            idx = self._model_combo.findText(self._current_model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
        self._model_combo.currentTextChanged.connect(
            lambda name: self.model_changed.emit(name)
        )
        
        # 设置标签样式 - 缩小宽度和字体
        model_label = QLabel(tr("默认模型") + ":")
        model_label.setStyleSheet("font-size: 11px; min-width: 50px; max-width: 60px;")
        model_layout.addRow(model_label, self._model_combo)

        layout.addWidget(model_group)

        # ---------- 语音识别 ----------
        voice_group = QGroupBox(tr("语音识别 (Whisper)"))
        voice_layout = QFormLayout(voice_group)

        self._whisper_combo = QComboBox()
        for model_id, model_desc in self.WHISPER_MODELS:
            self._whisper_combo.addItem(model_desc, model_id)

        # 设置当前选中的模型
        for i, (model_id, _) in enumerate(self.WHISPER_MODELS):
            if model_id == self._current_whisper_model:
                self._whisper_combo.setCurrentIndex(i)
                break

        self._whisper_combo.currentIndexChanged.connect(self._on_whisper_model_changed)
        voice_layout.addRow(tr("识别模型") + ":", self._whisper_combo)

        whisper_hint = QLabel(
            tr("提示: 模型越大准确度越高，但需要更多内存和计算时间。") + "\n"
            + tr("首次使用时会自动下载模型（需要网络）。")
        )
        whisper_hint.setWordWrap(True)
        whisper_hint.setStyleSheet("font-size: 11px; color: gray;")
        voice_layout.addRow("", whisper_hint)

        layout.addWidget(voice_group)

        # ---------- 快捷键 ----------
        hotkey_group = QGroupBox(tr("快捷键"))
        hotkey_layout = QFormLayout(hotkey_group)

        self._hotkey_edit = QLineEdit(self._current_hotkey)
        self._hotkey_edit.setPlaceholderText("例如: Win+Shift+Space")
        hotkey_layout.addRow(tr("唤起窗口") + ":", self._hotkey_edit)

        apply_hk_btn = QPushButton(tr("应用"))
        apply_hk_btn.clicked.connect(self._on_hotkey_apply)
        hotkey_layout.addRow("", apply_hk_btn)

        layout.addWidget(hotkey_group)

        # ---------- 远程绑定 ----------
        remote_group = QGroupBox(tr("远程绑定"))
        remote_layout = QVBoxLayout(remote_group)

        self._device_status_label = QLabel("未绑定设备")
        self._device_status_label.setStyleSheet("font-size: 13px; color: gray;")
        remote_layout.addWidget(self._device_status_label)

        device_btn_layout = QHBoxLayout()

        self._bind_device_btn = QPushButton("绑定设备")
        self._bind_device_btn.clicked.connect(self._on_bind_device)
        device_btn_layout.addWidget(self._bind_device_btn)

        self._unbind_device_btn = QPushButton("解绑设备")
        self._unbind_device_btn.setEnabled(False)
        self._unbind_device_btn.clicked.connect(self._on_unbind_device)
        device_btn_layout.addWidget(self._unbind_device_btn)

        remote_layout.addLayout(device_btn_layout)

        layout.addWidget(remote_group)

        layout.addStretch()
        return widget

    def _on_theme_changed(self, index: int) -> None:
        """主题切换。"""
        theme_map = {
            0: "light",
            1: "dark",
            2: "system",
            3: "ocean_blue",
            4: "forest_green",
            5: "sunset_orange",
            6: "purple_dream",
            7: "pink_rose",
            8: "minimal_white",
            9: "deep_blue",
            10: "deep_brown",
            11: "cyberpunk_purple",
            12: "cyber_universe_blue",  # 新增赛博宇宙蓝主题
        }
        theme_str = theme_map.get(index, "light")
        self.theme_changed.emit(theme_str)

    def _on_language_changed(self, index: int) -> None:
        """语言切换。"""
        lang_code = self._lang_combo.itemData(index)
        if lang_code:
            from src.i18n import get_i18n_manager, tr as i18n_tr
            i18n = get_i18n_manager()
            if i18n.load_language(lang_code):
                QMessageBox.information(
                    self, i18n_tr("语言切换"),
                    f"{i18n_tr('语言已切换为')}: {i18n.get_language_name(lang_code)}\n"
                    f"{i18n_tr('部分界面需要重启后生效。')}"
                )
                logger.info("语言已切换为: %s", lang_code)
                # 发出语言切换信号，通知主窗口刷新 UI
                self.language_changed.emit(lang_code)

    def _on_hotkey_apply(self) -> None:
        """应用快捷键。"""
        text = self._hotkey_edit.text().strip()
        if text:
            self.hotkey_changed.emit(text)
            QMessageBox.information(self, tr("快捷键"), f"{tr('快捷键已更新为')}: {text}")

    def _on_whisper_model_changed(self, index: int) -> None:
        """切换 Whisper 模型。"""
        model_id = self._whisper_combo.itemData(index)
        if model_id:
            self.whisper_model_changed.emit(model_id)
            logger.info("Whisper 模型已切换为：%s", model_id)
    
    # ----------------------------------------------------------------
    # 设备绑定功能（Phase 5.3）
    # ----------------------------------------------------------------
    
    def _on_bind_device(self) -> None:
        """绑定设备。"""
        from .device_bind_dialog import DeviceBindDialog
        from src.remote_client.device_fingerprint import get_device_fingerprint
        from src.remote_client.device_binder import DeviceBindClient
        import asyncio
    
        dialog = DeviceBindDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
    
        token = dialog.get_token()
        if not token:
            dialog.show_error("请输入绑定 Token")
            return
    
        # 设置加载状态
        dialog.set_loading(True)
    
        try:
            # 生成设备指纹
            fingerprint = get_device_fingerprint()
            logger.info(f"生成设备指纹：{fingerprint[:16]}...")
    
            # 获取服务器地址
            server_url = self._get_server_url()
    
            # 创建绑定客户端
            binder = DeviceBindClient(server_url)
    
            # 异步执行绑定
            async def do_bind():
                return await binder.bind_device(token, fingerprint)
    
            # 在后台线程运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(do_bind()))
                device_info = future.result(timeout=30)
    
            if device_info:
                # 绑定成功
                dialog.set_loading(False)
                dialog.show_success(device_info.device_id, device_info.device_name)
                    
                # 更新 UI
                self._update_device_status(device_info)
                    
                # 通知主程序重新连接
                logger.info("设备绑定成功，将重新建立远程连接")
            else:
                # 绑定失败
                dialog.set_loading(False)
                dialog.show_error("绑定失败，请检查 Token 是否正确或服务器是否在线")
    
        except Exception as e:
            logger.error(f"绑定设备失败：{e}", exc_info=True)
            dialog.set_loading(False)
            dialog.show_error(f"绑定失败：{str(e)}")
    
    def _on_unbind_device(self) -> None:
        """解绑设备。"""
        from src.remote_client.device_binder import DeviceBindClient
        import asyncio
    
        reply = QMessageBox.question(
            self,
            "确认解绑",
            "确定要解绑当前设备吗？\n\n解绑后需要重新生成 Token 才能再次绑定。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
    
        if reply != QMessageBox.StandardButton.Yes:
            return
    
        try:
            server_url = self._get_server_url()
            binder = DeviceBindClient(server_url)
    
            # 异步执行解绑
            async def do_unbind():
                return await binder.unbind_device()
    
            # 在后台线程运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(do_unbind()))
                success = future.result(timeout=30)
    
            if success:
                QMessageBox.information(self, "解绑成功", "设备已成功解绑")
                self._clear_device_status()
            else:
                QMessageBox.warning(self, "解绑失败", "解绑失败，请稍后重试")
    
        except Exception as e:
            logger.error(f"解绑设备失败：{e}", exc_info=True)
            QMessageBox.critical(self, "解绑失败", f"解绑失败：{str(e)}")
    
    def _get_server_url(self) -> str:
        """获取服务器 HTTP API 地址。"""
        # 从配置文件中读取
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent / "config" / "default.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                remote_cfg = config.get("remote", {})
                
                # 优先使用 api_url，否则从 ws_url 提取
                api_url = remote_cfg.get("api_url")
                if api_url:
                    return api_url
                
                # 从 WebSocket URL 提取 HTTP URL
                ws_url = remote_cfg.get("server_url", "")
                if ws_url:
                    # wss://weclaw.cc/ws/bridge -> https://weclaw.cc
                    # ws://localhost:8000/ws/bridge -> http://localhost:8000
                    import re
                    match = re.match(r'wss?://([^/]+)', ws_url)
                    if match:
                        host = match.group(1)
                        protocol = "https" if ws_url.startswith("wss") else "http"
                        return f"{protocol}://{host}"
        except Exception as e:
            logger.warning(f"读取配置失败：{e}")
    
        return "http://localhost:8000"
    
    def _update_device_status(self, device_info) -> None:
        """更新设备状态显示。"""
        self._device_status_label.setText(
            f"✅ 已绑定：{device_info.device_name} ({device_info.device_id[:16]}...)"
        )
        self._bind_device_btn.setEnabled(False)
        self._unbind_device_btn.setEnabled(True)
    
    def _clear_device_status(self) -> None:
        """清除设备状态显示。"""
        self._device_status_label.setText("未绑定设备")
        self._bind_device_btn.setEnabled(True)
        self._unbind_device_btn.setEnabled(False)

    def _load_device_status(self) -> None:
        """加载设备状态。"""
        from src.remote_client.device_binder import DeviceBindClient
        import asyncio

        try:
            server_url = self._get_server_url()
            binder = DeviceBindClient(server_url)

            # 异步执行查询
            async def do_query():
                return await binder.get_device_info()

            # 在后台线程运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(do_query()))
                device_info = future.result(timeout=10)

            if device_info and device_info.status == "active":
                self._update_device_status(device_info)
            else:
                self._clear_device_status()

        except Exception as e:
            logger.warning(f"加载设备状态失败：{e}")
            self._clear_device_status()
    
    # ----------------------------------------------------------------
    # MCP 扩展选项卡（Phase 4.2）
    # ----------------------------------------------------------------

    def _create_mcp_tab(self) -> QWidget:
        """创建 MCP 扩展管理选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 说明信息
        info = QLabel(
            "MCP (Model Context Protocol) 允许连接外部工具服务。\n"
            "启用后，AI 可以使用这些工具执行更多操作。"
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(info)

        # Server 列表
        servers_group = QGroupBox("已配置的 MCP Server")
        servers_layout = QVBoxLayout(servers_group)

        # Server 列表显示
        self._mcp_table = QTableWidget()
        self._mcp_table.setColumnCount(4)
        self._mcp_table.setHorizontalHeaderLabels(["名称", "状态", "工具数", "启用"])
        self._mcp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._mcp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._mcp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        servers_layout.addWidget(self._mcp_table)

        # 加载 MCP 配置
        self._load_mcp_servers()

        layout.addWidget(servers_group)

        # 操作按钮
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_mcp_status)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()

        help_btn = QPushButton("帮助")
        help_btn.clicked.connect(self._show_mcp_help)
        btn_layout.addWidget(help_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()
        return widget

    def _load_mcp_servers(self) -> None:
        """加载 MCP Server 列表。"""
        import json
        from pathlib import Path

        config_path = Path(__file__).parent.parent.parent / "config" / "mcp_servers.json"
        self._mcp_table.setRowCount(0)

        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                servers = data.get("mcpServers", {})
                self._mcp_table.setRowCount(len(servers))

                for row, (name, cfg) in enumerate(servers.items()):
                    self._mcp_table.setItem(row, 0, QTableWidgetItem(name))

                    # 从 MCP 管理器获取真实状态
                    status = "未连接"
                    tool_count = "-"
                    
                    if self._mcp_manager is not None:
                        # 检查是否已连接
                        conn = getattr(self._mcp_manager, 'connections', {}).get(name)
                        if conn and getattr(conn, 'is_connected', False):
                            status = "已连接"
                            tools = getattr(conn, 'tools', [])
                            tool_count = str(len(tools))
                        elif cfg.get("enabled", False):
                            status = "待连接"
                    
                    self._mcp_table.setItem(row, 1, QTableWidgetItem(status))
                    self._mcp_table.setItem(row, 2, QTableWidgetItem(tool_count))

                    # 启用复选框
                    check = QCheckBox()
                    check.setChecked(cfg.get("enabled", False))
                    check.stateChanged.connect(
                        lambda state, n=name: self._toggle_mcp_server(n, state)
                    )
                    self._mcp_table.setCellWidget(row, 3, check)

        except Exception as e:
            logger.warning("加载 MCP 配置失败: %s", e)

    def _refresh_mcp_status(self) -> None:
        """刷新 MCP Server 状态。"""
        self._load_mcp_servers()
        QMessageBox.information(self, "提示", "MCP Server 列表已刷新")

    def _toggle_mcp_server(self, server_name: str, state: int) -> None:
        """切换 MCP Server 启用状态。"""
        import json
        from pathlib import Path

        config_path = Path(__file__).parent.parent.parent / "config" / "mcp_servers.json"
        enabled = state == 2  # Qt.Checked

        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if server_name in data.get("mcpServers", {}):
                    data["mcpServers"][server_name]["enabled"] = enabled

                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    logger.info("MCP Server %s %s", server_name, "启用" if enabled else "禁用")

        except Exception as e:
            logger.warning("保存 MCP 配置失败: %s", e)

    def _show_mcp_help(self) -> None:
        """显示 MCP 帮助信息。"""
        QMessageBox.information(
            self,
            "MCP 帮助",
            "MCP (Model Context Protocol) 是一种标准化协议，\n"
            "允许 AI 连接外部工具服务。\n\n"
            "常用 MCP Server:\n"
            "- filesystem: 文件系统访问\n"
            "- fetch: 网页抓取\n"
            "- github: GitHub 操作\n"
            "- database: 数据库查询\n\n"
            "更多 Server 请访问:\n"
            "https://github.com/modelcontextprotocol"
        )

    # ----------------------------------------------------------------
    # 更新选项卡
    # ----------------------------------------------------------------

    def _create_update_tab(self) -> QWidget:
        """创建更新选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 版本信息
        version_group = QGroupBox("版本信息")
        version_layout = QFormLayout(version_group)
        
        from src.updater.github_updater import get_current_version
        current_version = get_current_version()
        
        version_label = QLabel(f"<b>{current_version}</b>")
        version_layout.addRow("当前版本:", version_label)
        
        layout.addWidget(version_group)
        
        # 更新设置
        update_group = QGroupBox("更新设置")
        update_layout = QVBoxLayout(update_group)
        
        # 检查更新按钮
        check_btn = QPushButton("检查更新")
        check_btn.clicked.connect(self._on_check_update)
        update_layout.addWidget(check_btn)
        
        # 状态标签
        self._update_status = QLabel("点击上方按钮检查更新")
        self._update_status.setWordWrap(True)
        update_layout.addWidget(self._update_status)
        
        layout.addWidget(update_group)
        
        # 关于
        about_group = QGroupBox("关于")
        about_layout = QVBoxLayout(about_group)
        
        about_text = QLabel(
            "WinClaw - Windows AI 助手\n"
            "基于大语言模型的智能桌面助手\n\n"
            "GitHub: https://github.com/wyg5208/WinClaw"
        )
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)
        
        layout.addWidget(about_group)
        
        layout.addStretch()
        return widget
    
    def _on_check_update(self) -> None:
        """检查更新。"""
        self._update_status.setText("正在检查更新...")
        
        # 在后台线程检查
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def check_in_thread():
            try:
                from src.updater.github_updater import check_for_updates, get_current_version
                
                async def do_check():
                    return await check_for_updates()
                
                return asyncio.run(do_check())
            except Exception as e:
                return str(e)
        
        # 简化处理：直接显示状态
        # 实际应用中应该使用 QThread
        try:
            from src.updater.github_updater import get_current_version
            current = get_current_version()
            
            # 显示当前状态
            self._update_status.setText(
                f"当前版本: {current}\n"
                "提示: 完整的更新检查需要网络连接\n"
                "请访问 GitHub 查看最新版本"
            )
        except Exception as e:
            self._update_status.setText(f"检查失败: {e}")
