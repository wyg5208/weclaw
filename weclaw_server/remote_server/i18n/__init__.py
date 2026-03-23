"""国际化（i18n）支持模块

提供多语言翻译功能，支持错误消息、提示等的本地化。
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class I18nManager:
    """国际化管理器"""
    
    _instance: Optional['I18nManager'] = None
    _translations: Dict[str, Dict[str, str]] = {}
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化国际化管理器"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._load_translations()
        self._initialized = True
        
        logger.info("国际化管理器已初始化")
    
    def _load_translations(self):
        """加载翻译文件"""
        # 查找翻译文件路径
        possible_paths = [
            Path(__file__).parent / "i18n" / "messages.json",
            Path(__file__).parent.parent / "i18n" / "messages.json",
            Path.cwd() / "i18n" / "messages.json",
        ]
        
        messages_file = None
        for path in possible_paths:
            if path.exists():
                messages_file = path
                break
        
        if not messages_file:
            logger.warning("未找到翻译文件，使用默认消息")
            return
        
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                self._translations = json.load(f)
            logger.info(f"已加载翻译文件：{messages_file}")
        except Exception as e:
            logger.error(f"加载翻译文件失败：{e}")
    
    def get(self, key: str, lang: str = "zh_CN", default: Optional[str] = None) -> str:
        """获取翻译文本
        
        Args:
            key: 翻译键
            lang: 语言代码（zh_CN/en_US）
            default: 默认文本（如果翻译不存在）
            
        Returns:
            翻译后的文本
        """
        if lang not in self._translations:
            # 降级到中文
            lang = "zh_CN"
        
        translations = self._translations.get(lang, {})
        return translations.get(key, default or key)
    
    def t(self, key: str, lang: str = "zh_CN", **kwargs) -> str:
        """获取翻译文本（便捷方法）
        
        Args:
            key: 翻译键
            lang: 语言代码
            **kwargs: 格式化参数
            
        Returns:
            翻译并格式化后的文本
        """
        text = self.get(key, lang)
        
        # 简单的字符串格式化
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass  # 忽略格式化错误
        
        return text


# 全局单例
_i18n_manager: Optional[I18nManager] = None


def get_i18n_manager() -> I18nManager:
    """获取国际化管理器单例"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager


def t(key: str, lang: str = "zh_CN", default: Optional[str] = None, **kwargs) -> str:
    """便捷翻译函数
    
    Args:
        key: 翻译键
        lang: 语言代码
        default: 默认文本
        **kwargs: 格式化参数
        
    Returns:
        翻译后的文本
    """
    manager = get_i18n_manager()
    return manager.t(key, lang, **kwargs)


def get_user_language(user_id: str) -> str:
    """获取用户语言偏好
    
    TODO: 从数据库或配置中读取用户语言设置
    目前默认返回中文
    """
    # 未来可以从用户配置中读取
    # user_manager = context.get_user_manager()
    # if user_manager:
    #     user = user_manager.get_user(user_id)
    #     if user and user.settings:
    #         return user.settings.get("language", "zh_CN")
    
    return "zh_CN"
