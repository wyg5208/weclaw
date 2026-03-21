"""设备绑定 API 客户端。

用于 WinClaw PC 端调用远程服务器的设备绑定接口。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("aiohttp 库未安装，请运行：pip install aiohttp")

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    device_name: str
    bound_at: str
    last_connected: Optional[str]
    status: str
    access_token: Optional[str] = None  # ✅ 新增：JWT access token
    refresh_token: Optional[str] = None  # ✅ 新增：JWT refresh token


class DeviceBindClient:
    """设备绑定 API 客户端"""

    def __init__(self, server_url: str = "http://localhost:8000"):
        """
        初始化客户端
        
        Args:
            server_url: 远程服务器地址
        """
        self.server_url = server_url.rstrip('/')
        self._token: Optional[str] = None

    def set_token(self, token: str) -> None:
        """设置认证 Token"""
        self._token = token

    async def bind_device(
        self,
        binding_token: str,
        device_fingerprint: str,
        device_name: str = ""
    ) -> Optional[DeviceInfo]:
        """
        绑定设备
        
        Args:
            binding_token: PWA 端生成的绑定 Token
            device_fingerprint: 设备指纹（PC 端自动生成）
            device_name: 设备名称（可选）
            
        Returns:
            绑定成功返回设备信息（包含 JWT Token），失败返回 None
        """
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp 库未安装")
            return None

        url = f"{self.server_url}/api/auth/bind-device"
        
        headers = {
            "Content-Type": "application/json"
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        payload = {
            "binding_token": binding_token,
            "device_fingerprint": device_fingerprint,
            "device_name": device_name or f"WinClaw-{device_fingerprint[:8]}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("success"):
                            logger.info(f"设备绑定成功：{data.get('device_id', '')[:16]}...")
                            
                            # ✅ 保存返回的 JWT Token
                            access_token = data.get("access_token")
                            refresh_token = data.get("refresh_token")
                            
                            if access_token:
                                # 保存到安全存储
                                from ..ui.keystore import save_key
                                save_key("WECLAW_ACCESS_TOKEN", access_token)
                                logger.info("已保存 access token")
                            
                            if refresh_token:
                                save_key("WECLAW_REFRESH_TOKEN", refresh_token)
                                logger.info("已保存 refresh token")
                            
                            return DeviceInfo(
                                device_id=data.get("device_id", ""),
                                device_name=data.get("device_name", ""),
                                bound_at="",
                                last_connected=None,
                                status="active",
                                access_token=access_token,
                                refresh_token=refresh_token
                            )
                        else:
                            logger.error(f"绑定失败：{data.get('message', '未知错误')}")
                            return None
                    else:
                        error_data = await response.json()
                        detail = error_data.get("detail", "未知错误")
                        logger.error(f"绑定请求失败 ({response.status}): {detail}")
                        return None
        except Exception as e:
            logger.error(f"绑定设备时发生错误：{e}")
            return None

    async def get_device_info(self) -> Optional[DeviceInfo]:
        """
        获取已绑定的设备信息
        
        Returns:
            设备信息，未绑定返回 None
        """
        if not AIOHTTP_AVAILABLE:
            return None

        url = f"{self.server_url}/api/auth/device"
        
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return DeviceInfo(**data)
                    elif response.status == 404:
                        logger.info("当前未绑定设备")
                        return None
                    else:
                        error_data = await response.json()
                        logger.error(f"获取设备信息失败 ({response.status}): {error_data.get('detail', '未知错误')}")
                        return None
        except Exception as e:
            logger.error(f"获取设备信息时发生错误：{e}")
            return None

    async def unbind_device(self) -> bool:
        """
        解绑设备
        
        Returns:
            解绑是否成功
        """
        if not AIOHTTP_AVAILABLE:
            return False

        url = f"{self.server_url}/api/auth/device"
        
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers) as response:
                    if response.status == 200:
                        logger.info("设备解绑成功")
                        return True
                    else:
                        error_data = await response.json()
                        logger.error(f"解绑失败 ({response.status}): {error_data.get('detail', '未知错误')}")
                        return False
        except Exception as e:
            logger.error(f"解绑设备时发生错误：{e}")
            return False
