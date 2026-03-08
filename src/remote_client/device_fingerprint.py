"""设备指纹生成器

基于硬件特征生成唯一设备标识，防止身份欺诈。

支持 Windows、macOS、Linux 平台。
"""

import hashlib
import logging
import platform
import subprocess
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class DeviceFingerprint:
    """设备指纹生成器"""
    
    def __init__(self):
        self._cached_fingerprint: Optional[str] = None
        self._cached_device_id: Optional[str] = None
    
    def generate(self) -> str:
        """
        生成设备指纹
        
        Returns:
            设备指纹（SHA256 哈希值）
        """
        if self._cached_fingerprint:
            return self._cached_fingerprint
        
        components = []
        system = platform.system().lower()
        
        # 1. CPU 信息
        cpu_id = self._get_cpu_id(system)
        if cpu_id:
            components.append(f"cpu:{cpu_id}")
        
        # 2. 主板信息
        motherboard_id = self._get_motherboard_id(system)
        if motherboard_id:
            components.append(f"mb:{motherboard_id}")
        
        # 3. 硬盘序列号
        disk_id = self._get_disk_id(system)
        if disk_id:
            components.append(f"disk:{disk_id}")
        
        # 4. MAC 地址
        mac_address = self._get_mac_address()
        if mac_address:
            components.append(f"mac:{mac_address}")
        
        # 5. 机器名（作为补充）
        hostname = platform.node()
        if hostname:
            components.append(f"host:{hostname}")
        
        # 6. 系统信息
        system_info = f"{platform.system()}-{platform.machine()}-{platform.version()}"
        components.append(f"sys:{system_info}")
        
        # 如果无法获取足够信息，使用降级方案
        if len(components) < 3:
            logger.warning("无法获取足够的硬件信息，使用降级方案")
            # 使用多个稳定标识符组合
            fallback = f"{mac_address or uuid.getnode()}-{hostname}-{system_info}"
            self._cached_fingerprint = hashlib.sha256(fallback.encode()).hexdigest()
        else:
            # 组合所有组件并哈希
            combined = "|".join(components)
            self._cached_fingerprint = hashlib.sha256(combined.encode()).hexdigest()
        
        logger.info(f"设备指纹生成完成: {self._cached_fingerprint[:16]}...")
        return self._cached_fingerprint
    
    def get_device_id(self) -> str:
        """
        获取设备 ID（基于指纹生成的短 ID）
        
        Returns:
            16 字符的设备 ID
        """
        if self._cached_device_id:
            return self._cached_device_id
        
        fingerprint = self.generate()
        self._cached_device_id = fingerprint[:16]
        return self._cached_device_id
    
    def _get_cpu_id(self, system: str) -> Optional[str]:
        """获取 CPU ID"""
        try:
            if system == "windows":
                # Windows: 使用 wmic 获取 CPU ID
                result = subprocess.run(
                    ["wmic", "cpu", "get", "ProcessorId"],
                    capture_output=True, text=True, timeout=10
                )
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                if len(lines) > 1:
                    return lines[1]  # 跳过标题行
                    
            elif system == "darwin":
                # macOS: 使用 sysctl 或 system_profiler
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip()
                
            elif system == "linux":
                # Linux: 读取 /proc/cpuinfo
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        for line in f:
                            if "Serial" in line or "Hardware" in line:
                                return line.split(":")[1].strip()
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"获取 CPU ID 失败: {e}")
        
        return None
    
    def _get_motherboard_id(self, system: str) -> Optional[str]:
        """获取主板序列号"""
        try:
            if system == "windows":
                result = subprocess.run(
                    ["wmic", "baseboard", "get", "SerialNumber"],
                    capture_output=True, text=True, timeout=10
                )
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                if len(lines) > 1 and lines[1]:
                    return lines[1]
                    
            elif system == "darwin":
                result = subprocess.run(
                    ["system_profiler", "SPHardwareDataType"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if "Serial Number" in line or "Board ID" in line:
                        return line.split(":")[-1].strip()
                        
            elif system == "linux":
                result = subprocess.run(
                    ["dmidecode", "-s", "baseboard-serial-number"],
                    capture_output=True, text=True, timeout=5
                )
                serial = result.stdout.strip()
                if serial and serial != "None":
                    return serial
                    
        except Exception as e:
            logger.debug(f"获取主板 ID 失败: {e}")
        
        return None
    
    def _get_disk_id(self, system: str) -> Optional[str]:
        """获取硬盘序列号"""
        try:
            if system == "windows":
                result = subprocess.run(
                    ["wmic", "diskdrive", "get", "SerialNumber"],
                    capture_output=True, text=True, timeout=10
                )
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                if len(lines) > 1:
                    # 使用第一个硬盘的序列号
                    return lines[1]
                    
            elif system == "darwin":
                result = subprocess.run(
                    ["diskutil", "info", "/"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if "Volume UUID" in line or "Disk / Partition UUID" in line:
                        return line.split(":")[-1].strip()
                        
            elif system == "linux":
                # 使用 root 分区的 UUID
                result = subprocess.run(
                    ["blkid", "-s", "UUID", "-o", "value", "/dev/sda1"],
                    capture_output=True, text=True, timeout=5,
                    stderr=subprocess.DEVNULL
                )
                uuid_val = result.stdout.strip()
                if uuid_val:
                    return uuid_val
                    
        except Exception as e:
            logger.debug(f"获取硬盘 ID 失败: {e}")
        
        return None
    
    def _get_mac_address(self) -> Optional[str]:
        """获取主网卡 MAC 地址"""
        try:
            # 获取第一个非本地 MAC 地址
            mac = uuid.getnode()
            mac_str = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) 
                               for elements in range(0, 8*6, 8)][::-1])
            
            # 检查是否为有效 MAC（非本地管理地址）
            if mac & 0x020000000000:  # 本地管理地址标志
                logger.debug("检测到本地管理 MAC 地址")
            
            return mac_str
            
        except Exception as e:
            logger.debug(f"获取 MAC 地址失败: {e}")
        
        return None


# 全局实例
_fingerprint_generator: Optional[DeviceFingerprint] = None


def get_device_fingerprint() -> str:
    """获取设备指纹（全局缓存）"""
    global _fingerprint_generator
    if _fingerprint_generator is None:
        _fingerprint_generator = DeviceFingerprint()
    return _fingerprint_generator.generate()


def get_device_id() -> str:
    """获取设备 ID（全局缓存）"""
    global _fingerprint_generator
    if _fingerprint_generator is None:
        _fingerprint_generator = DeviceFingerprint()
    return _fingerprint_generator.get_device_id()


if __name__ == "__main__":
    # 测试
    fp = DeviceFingerprint()
    print(f"设备指纹: {fp.generate()}")
    print(f"设备 ID: {fp.get_device_id()}")
