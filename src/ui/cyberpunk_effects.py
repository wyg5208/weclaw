"""赛博朋克风格发光效果工具。

提供 PySide6 组件的霓虹发光特效，增强科技感视觉效果。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget
from PySide6.QtGui import QColor
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class GlowEffect:
    """发光效果工具类。
    
    为组件添加霓虹光晕特效，支持多种颜色和动画模式。
    """
    
    @staticmethod
    def apply_glow(
        widget: QWidget,
        color: str = "#9b59b6",
        blur_radius: int = 20,
        offset: int = 0,
        opacity: float = 0.8,
        animated: bool = False,
        pulse_speed: int = 1000
    ) -> QGraphicsDropShadowEffect:
        """为组件应用发光效果。
        
        Args:
            widget: 目标组件
            color: 发光颜色（十六进制）
            blur_radius: 模糊半径（越大光晕越明显）
            offset: 偏移量（0 为中心发光）
            opacity: 不透明度（0-1）
            animated: 是否启用脉冲动画
            pulse_speed: 脉冲速度（毫秒/周期）
            
        Returns:
            应用的阴影效果对象
        """
        # 创建阴影效果（用于模拟发光）
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur_radius)
        effect.setOffset(offset)
        effect.setColor(QColor(color))
        
        widget.setGraphicsEffect(effect)
        
        # 如果启用动画，创建脉冲效果
        if animated:
            GlowEffect._create_pulse_animation(effect, pulse_speed)
        
        logger.debug(f"已为 {widget.objectName() or widget.__class__.__name__} 应用发光效果")
        return effect
    
    @staticmethod
    def _create_pulse_animation(
        effect: QGraphicsDropShadowEffect,
        speed: int = 1000
    ) -> None:
        """创建脉冲动画。
        
        Args:
            effect: 阴影效果对象
            speed: 动画周期（毫秒）
        """
        # 创建不透明度动画
        animation = QPropertyAnimation(effect, b"color")
        animation.setDuration(speed)
        animation.setStartValue(QColor("#9b59b6"))
        animation.setEndValue(QColor("#d7bde2"))
        animation.setLoopCount(-1)  # 无限循环
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()
    
    @staticmethod
    def apply_double_glow(
        widget: QWidget,
        inner_color: str = "#be90d4",
        outer_color: str = "#9b59b6",
        inner_blur: int = 15,
        outer_blur: int = 30
    ) -> tuple[QGraphicsDropShadowEffect, QGraphicsDropShadowEffect]:
        """应用双层发光效果（内层 + 外层）。
        
        Args:
            widget: 目标组件
            inner_color: 内层发光颜色
            outer_color: 外层发光颜色
            inner_blur: 内层模糊半径
            outer_blur: 外层模糊半径
            
        Returns:
            (内层效果，外层效果) 元组
        """
        # 内层发光
        inner_effect = QGraphicsDropShadowEffect(widget)
        inner_effect.setBlurRadius(inner_blur)
        inner_effect.setColor(QColor(inner_color))
        
        # 外层发光
        outer_effect = QGraphicsDropShadowEffect(widget)
        outer_effect.setBlurRadius(outer_blur)
        outer_effect.setColor(QColor(outer_color))
        
        # 注意：Qt 不支持同时应用多个阴影效果到同一组件
        # 这里只应用外层效果作为妥协
        widget.setGraphicsEffect(outer_effect)
        
        logger.debug(f"已为 {widget.objectName() or widget.__class__.__name__} 应用双层发光效果")
        return inner_effect, outer_effect
    
    @staticmethod
    def remove_glow(widget: QWidget) -> None:
        """移除组件的发光效果。
        
        Args:
            widget: 目标组件
        """
        effect = widget.graphicsEffect()
        if effect:
            effect.deleteLater()
            widget.setGraphicsEffect(None)
            logger.debug(f"已移除 {widget.objectName() or widget.__class__.__name__} 的发光效果")


class CyberButtonStyle:
    """赛博朋克按钮样式工具。
    
    提供特殊的按钮交互效果，包括悬停发光、按下收缩等。
    """
    
    @staticmethod
    def setup_cyber_button(
        button: QWidget,
        glow_on_hover: bool = True,
        glow_color: str = "#9b59b6"
    ) -> None:
        """设置赛博朋克风格按钮。
        
        Args:
            button: 按钮组件
            glow_on_hover: 鼠标悬停时是否发光
            glow_color: 发光颜色
        """
        if not glow_on_hover:
            return
        
        # 初始状态不发光
        button.installEventFilter(button)
        
        # 通过事件过滤器实现悬停发光
        class ButtonEventFilter:
            def __init__(self, btn, color):
                self.button = btn
                self.glow_color = color
                self.effect = None
                
            def eventFilter(self, obj, event):
                from PySide6.QtCore import QEvent
                if event.type() == QEvent.Type.Enter:
                    # 鼠标进入 - 应用发光
                    self.effect = GlowEffect.apply_glow(
                        self.button,
                        color=self.glow_color,
                        blur_radius=25,
                        animated=True
                    )
                    return True
                elif event.type() == QEvent.Type.Leave:
                    # 鼠标离开 - 移除发光
                    if self.effect:
                        GlowEffect.remove_glow(self.button)
                        self.effect = None
                    return True
                return False
        
        filter_instance = ButtonEventFilter(button, glow_color)
        button.installEventFilter(filter_instance)
        logger.debug(f"已为按钮设置赛博朋克悬停发光效果")
