"""共享的 QPainter 绘制辅助函数（支持中文标签渲染）。"""

from typing import Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap


def draw_box_label(
    painter: QPainter,
    text: str,
    x: int,
    y_bottom: int,
    bg_color_bgr: Tuple[int, int, int],
):
    """在 QPainter 上绘制带背景色的文字标签（支持中文）。

    ``y_bottom`` 是标签区域的底边 y 坐标（通常等于检测框的 y_min）。
    ``bg_color_bgr`` 为 BGR 三元组，与 OpenCV 的颜色约定一致。
    """
    fm = painter.fontMetrics()
    tw = fm.horizontalAdvance(text)
    th = fm.height()
    pad = 3
    r, g, b = bg_color_bgr[2], bg_color_bgr[1], bg_color_bgr[0]

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(r, g, b))
    painter.drawRect(x, y_bottom - th - 2 * pad, tw + 2 * pad, th + 2 * pad)

    painter.setPen(QColor(255, 255, 255))
    painter.setBrush(Qt.NoBrush)
    painter.drawText(x + pad, y_bottom - fm.descent() - pad, text)


def begin_label_painter(pixmap: QPixmap, pixel_size: int = 16) -> QPainter:
    """创建用于在 QPixmap 上绘制标签文字的 QPainter。"""
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    font = QFont("Microsoft YaHei", -1)
    font.setPixelSize(pixel_size)
    painter.setFont(font)
    return painter
