"""模板编辑器对话框 - 裁剪模板区域并支持匹配测试。"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PyQt5.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CaptionLabel,
    DoubleSpinBox,
    FluentIcon as FIF,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    SubtitleLabel,
)

from ez_traing.template_matching.matcher import (
    TemplateMatcher,
    TemplateInfo,
    imread_unicode,
)

logger = logging.getLogger(__name__)


# ======================================================================
# Crop Image Widget
# ======================================================================


class CropImageWidget(QWidget):
    """支持鼠标拖拽矩形选区、滚轮缩放、中键/右键平移的图片裁剪控件。

    内部以原图像素坐标维护选区，显示时根据缩放和平移参数映射。
    - 左键拖拽：绘制裁剪选区
    - 滚轮：以光标为中心缩放
    - 中键/右键拖拽：平移画布
    - 双击左键：适应窗口
    """

    selection_changed = pyqtSignal()
    zoom_changed = pyqtSignal(float)

    _ZOOM_MIN = 0.1
    _ZOOM_MAX = 20.0
    _ZOOM_FACTOR = 1.15

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_image: Optional[np.ndarray] = None
        self._display_pixmap: Optional[QPixmap] = None

        self._crop_rect: Optional[Tuple[int, int, int, int]] = None

        # crop drag state
        self._dragging = False
        self._drag_start: Optional[QPoint] = None
        self._drag_current: Optional[QPoint] = None

        # zoom & pan — _zoom is relative to "fit" scale
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0

        # pan drag state (middle / right button)
        self._panning = False
        self._pan_anchor: Optional[QPoint] = None
        self._pan_start_x = 0.0
        self._pan_start_y = 0.0

        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_image(self, image: np.ndarray):
        self._source_image = image.copy()
        self._crop_rect = None
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._update_display()
        self.update()
        self.zoom_changed.emit(self._zoom)

    def get_crop_rect(self) -> Optional[Tuple[int, int, int, int]]:
        return self._crop_rect

    def get_cropped_image(self) -> Optional[np.ndarray]:
        if self._source_image is None:
            return None
        if self._crop_rect is None:
            return self._source_image.copy()
        x, y, w, h = self._crop_rect
        return self._source_image[y : y + h, x : x + w].copy()

    def reset_selection(self):
        self._crop_rect = None
        self.update()
        self.selection_changed.emit()

    def fit_to_window(self):
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.update()
        self.zoom_changed.emit(self._zoom)

    def get_zoom(self) -> float:
        return self._zoom

    # ------------------------------------------------------------------
    # Internal: display mapping
    # ------------------------------------------------------------------

    def _update_display(self):
        if self._source_image is None:
            self._display_pixmap = None
            return
        rgb = cv2.cvtColor(self._source_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self._display_pixmap = QPixmap.fromImage(qimg)

    def _fit_scale(self) -> float:
        """缩放比使图片刚好适应控件大小。"""
        if self._display_pixmap is None:
            return 1.0
        pw, ph = self._display_pixmap.width(), self._display_pixmap.height()
        ww, wh = self.width(), self.height()
        return min(ww / max(pw, 1), wh / max(ph, 1))

    def _effective_scale(self) -> float:
        return self._fit_scale() * self._zoom

    def _compute_layout(self) -> Tuple[QPoint, float]:
        if self._display_pixmap is None:
            return QPoint(0, 0), 1.0
        pw, ph = self._display_pixmap.width(), self._display_pixmap.height()
        scale = self._effective_scale()
        cx = self.width() / 2.0 + self._pan_x
        cy = self.height() / 2.0 + self._pan_y
        dx = cx - pw * scale / 2.0
        dy = cy - ph * scale / 2.0
        return QPoint(int(dx), int(dy)), scale

    def _widget_to_image(self, pos: QPoint) -> QPoint:
        offset, scale = self._compute_layout()
        if scale <= 0:
            return QPoint(0, 0)
        ix = int((pos.x() - offset.x()) / scale)
        iy = int((pos.y() - offset.y()) / scale)
        return QPoint(ix, iy)

    def _image_rect_to_widget(self, x, y, w, h) -> QRect:
        offset, scale = self._compute_layout()
        wx = int(x * scale + offset.x())
        wy = int(y * scale + offset.y())
        ww = int(w * scale)
        wh = int(h * scale)
        return QRect(wx, wy, ww, wh)

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        painter.fillRect(self.rect(), QColor(30, 30, 30))

        if self._display_pixmap is None:
            painter.setPen(QColor(128, 128, 128))
            painter.drawText(self.rect(), Qt.AlignCenter, "无图片")
            painter.end()
            return

        offset, scale = self._compute_layout()

        dest = QRect(
            offset.x(),
            offset.y(),
            int(self._display_pixmap.width() * scale),
            int(self._display_pixmap.height() * scale),
        )
        painter.drawPixmap(dest, self._display_pixmap)

        crop = self._crop_rect
        if self._dragging and self._drag_start and self._drag_current:
            p1 = self._widget_to_image(self._drag_start)
            p2 = self._widget_to_image(self._drag_current)
            crop = self._normalize_rect(p1, p2)

        if crop:
            x, y, w, h = crop
            overlay = QColor(0, 0, 0, 120)
            img_w = self._display_pixmap.width()
            img_h = self._display_pixmap.height()
            sel = self._image_rect_to_widget(x, y, w, h)
            full = self._image_rect_to_widget(0, 0, img_w, img_h)

            painter.fillRect(QRect(full.left(), full.top(), full.width(), sel.top() - full.top()), overlay)
            painter.fillRect(QRect(full.left(), sel.bottom(), full.width(), full.bottom() - sel.bottom()), overlay)
            painter.fillRect(QRect(full.left(), sel.top(), sel.left() - full.left(), sel.height()), overlay)
            painter.fillRect(QRect(sel.right(), sel.top(), full.right() - sel.right(), sel.height()), overlay)

            pen = QPen(QColor(0, 170, 255), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(sel)

        painter.end()

    # ------------------------------------------------------------------
    # Wheel zoom
    # ------------------------------------------------------------------

    def wheelEvent(self, event):
        if self._display_pixmap is None:
            return

        cursor_pos = event.pos()
        img_before = self._widget_to_image(cursor_pos)

        delta = event.angleDelta().y()
        if delta > 0:
            new_zoom = self._zoom * self._ZOOM_FACTOR
        elif delta < 0:
            new_zoom = self._zoom / self._ZOOM_FACTOR
        else:
            return

        new_zoom = max(self._ZOOM_MIN, min(new_zoom, self._ZOOM_MAX))
        self._zoom = new_zoom

        new_scale = self._effective_scale()
        pw, ph = self._display_pixmap.width(), self._display_pixmap.height()
        target_cx = cursor_pos.x() - img_before.x() * new_scale
        target_cy = cursor_pos.y() - img_before.y() * new_scale
        ideal_cx = self.width() / 2.0 - pw * new_scale / 2.0
        ideal_cy = self.height() / 2.0 - ph * new_scale / 2.0
        self._pan_x = target_cx - ideal_cx
        self._pan_y = target_cy - ideal_cy

        self.update()
        self.zoom_changed.emit(self._zoom)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if self._source_image is None:
            return

        if event.button() in (Qt.MiddleButton, Qt.RightButton):
            self._panning = True
            self._pan_anchor = event.pos()
            self._pan_start_x = self._pan_x
            self._pan_start_y = self._pan_y
            self.setCursor(Qt.ClosedHandCursor)
            return

        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start = event.pos()
            self._drag_current = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_anchor is not None:
            dx = event.pos().x() - self._pan_anchor.x()
            dy = event.pos().y() - self._pan_anchor.y()
            self._pan_x = self._pan_start_x + dx
            self._pan_y = self._pan_start_y + dy
            self.update()
            return

        if self._dragging:
            self._drag_current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.MiddleButton, Qt.RightButton) and self._panning:
            self._panning = False
            self._pan_anchor = None
            self.setCursor(Qt.CrossCursor)
            return

        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            if self._drag_start and self._drag_current:
                p1 = self._widget_to_image(self._drag_start)
                p2 = self._widget_to_image(self._drag_current)
                rect = self._normalize_rect(p1, p2)
                if rect and rect[2] >= 4 and rect[3] >= 4:
                    self._crop_rect = self._clamp_rect(rect)
                else:
                    self._crop_rect = None
            self._drag_start = None
            self._drag_current = None
            self.update()
            self.selection_changed.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.fit_to_window()

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_0:
            self.fit_to_window()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self._zoom = min(self._zoom * self._ZOOM_FACTOR, self._ZOOM_MAX)
            self.update()
            self.zoom_changed.emit(self._zoom)
        elif event.key() == Qt.Key_Minus:
            self._zoom = max(self._zoom / self._ZOOM_FACTOR, self._ZOOM_MIN)
            self.update()
            self.zoom_changed.emit(self._zoom)
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalize_rect(
        self, p1: QPoint, p2: QPoint
    ) -> Optional[Tuple[int, int, int, int]]:
        x1, y1 = min(p1.x(), p2.x()), min(p1.y(), p2.y())
        x2, y2 = max(p1.x(), p2.x()), max(p1.y(), p2.y())
        w, h = x2 - x1, y2 - y1
        if w < 1 or h < 1:
            return None
        return (x1, y1, w, h)

    def _clamp_rect(
        self, rect: Tuple[int, int, int, int]
    ) -> Tuple[int, int, int, int]:
        if self._source_image is None:
            return rect
        ih, iw = self._source_image.shape[:2]
        x, y, w, h = rect
        x = max(0, min(x, iw - 1))
        y = max(0, min(y, ih - 1))
        w = min(w, iw - x)
        h = min(h, ih - y)
        return (x, y, max(1, w), max(1, h))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()


# ======================================================================
# Template Editor Dialog
# ======================================================================


class TemplateEditorDialog(QDialog):
    """模板编辑器：裁剪模板区域 + 匹配测试预览。"""

    def __init__(
        self,
        image_path: str,
        default_label: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._image_path = image_path
        self._source_image = imread_unicode(image_path)
        self._test_image_paths: List[str] = []

        self.setWindowTitle(f"编辑模板 - {Path(image_path).name}")
        self.setMinimumSize(960, 620)
        self.resize(1100, 700)

        self._setup_ui(default_label or Path(image_path).stem)

        if self._source_image is not None:
            self._crop_widget.set_image(self._source_image)
            h, w = self._source_image.shape[:2]
            self._img_info_label.setText(f"原图尺寸: {w} x {h}")
        else:
            self._img_info_label.setText("无法读取图片")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self, default_label: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        # ---- left: crop ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        left_layout.addWidget(SubtitleLabel("模板裁剪"))

        self._crop_widget = CropImageWidget()
        self._crop_widget.selection_changed.connect(self._on_selection_changed)
        left_layout.addWidget(self._crop_widget, 1)

        info_row = QHBoxLayout()
        self._img_info_label = CaptionLabel("")
        info_row.addWidget(self._img_info_label)
        info_row.addStretch()
        self._sel_info_label = CaptionLabel("选区: 无 (将使用整张图片)")
        info_row.addWidget(self._sel_info_label)
        left_layout.addLayout(info_row)

        tool_row = QHBoxLayout()
        reset_btn = PushButton("重置选区")
        reset_btn.setIcon(FIF.SYNC)
        reset_btn.clicked.connect(self._crop_widget.reset_selection)
        tool_row.addWidget(reset_btn)

        fit_btn = PushButton("适应窗口")
        fit_btn.setIcon(FIF.FIT_PAGE)
        fit_btn.clicked.connect(self._crop_widget.fit_to_window)
        tool_row.addWidget(fit_btn)

        tool_row.addStretch()
        self._zoom_label = CaptionLabel("缩放: 100%")
        self._crop_widget.zoom_changed.connect(self._on_zoom_changed)
        tool_row.addWidget(self._zoom_label)
        left_layout.addLayout(tool_row)

        left_layout.addWidget(
            CaptionLabel("滚轮缩放 | 中键/右键拖拽平移 | 双击适应窗口")
        )

        splitter.addWidget(left)

        # ---- right: test ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        right_layout.addWidget(SubtitleLabel("匹配测试"))

        btn_row = QHBoxLayout()
        add_test_btn = PushButton("添加测试图片")
        add_test_btn.setIcon(FIF.ADD)
        add_test_btn.clicked.connect(self._on_add_test_images)
        btn_row.addWidget(add_test_btn)

        clear_test_btn = PushButton("清空")
        clear_test_btn.setIcon(FIF.DELETE)
        clear_test_btn.clicked.connect(self._on_clear_test_images)
        btn_row.addWidget(clear_test_btn)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        self._test_list = QListWidget()
        self._test_list.setMaximumHeight(120)
        self._test_list.setIconSize(QSize(48, 48))
        self._test_list.currentRowChanged.connect(self._on_test_image_selected)
        right_layout.addWidget(self._test_list)

        param_row = QHBoxLayout()
        param_row.addWidget(StrongBodyLabel("测试阈值"))
        self._test_threshold = DoubleSpinBox()
        self._test_threshold.setRange(0.1, 1.0)
        self._test_threshold.setSingleStep(0.05)
        self._test_threshold.setValue(0.8)
        self._test_threshold.setDecimals(2)
        param_row.addWidget(self._test_threshold)
        param_row.addStretch()

        run_btn = PushButton("执行测试")
        run_btn.setIcon(FIF.PLAY)
        run_btn.clicked.connect(self._on_run_test)
        param_row.addWidget(run_btn)
        right_layout.addLayout(param_row)

        self._test_preview = QLabel()
        self._test_preview.setAlignment(Qt.AlignCenter)
        self._test_preview.setMinimumHeight(200)
        self._test_preview.setStyleSheet(
            "background: #222; border-radius: 4px;"
        )
        self._test_preview.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        right_layout.addWidget(self._test_preview, 1)

        self._test_result_label = CaptionLabel("")
        right_layout.addWidget(self._test_result_label)

        splitter.addWidget(right)
        splitter.setSizes([550, 450])

        root.addWidget(splitter, 1)

        # ---- bottom: label + buttons ----
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        bottom.addWidget(StrongBodyLabel("标签名:"))
        self._label_edit = LineEdit()
        self._label_edit.setText(default_label)
        self._label_edit.setMinimumWidth(180)
        bottom.addWidget(self._label_edit)

        bottom.addStretch()

        ok_btn = PrimaryPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        bottom.addWidget(ok_btn)

        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(cancel_btn)

        root.addLayout(bottom)

    # ------------------------------------------------------------------
    # Public getters
    # ------------------------------------------------------------------

    def get_cropped_image(self) -> Optional[np.ndarray]:
        return self._crop_widget.get_cropped_image()

    def get_label(self) -> str:
        text = self._label_edit.text().strip()
        return text if text else Path(self._image_path).stem

    def get_image_path(self) -> str:
        return self._image_path

    # ------------------------------------------------------------------
    # Selection feedback
    # ------------------------------------------------------------------

    def _on_selection_changed(self):
        rect = self._crop_widget.get_crop_rect()
        if rect:
            x, y, w, h = rect
            self._sel_info_label.setText(f"选区: {w} x {h}  (x={x}, y={y})")
        else:
            self._sel_info_label.setText("选区: 无 (将使用整张图片)")

    def _on_zoom_changed(self, zoom: float):
        self._zoom_label.setText(f"缩放: {zoom * 100:.0f}%")

    # ------------------------------------------------------------------
    # Test images
    # ------------------------------------------------------------------

    def _on_add_test_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择测试图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.webp);;所有文件 (*)",
        )
        if not paths:
            return
        for p in paths:
            if p in self._test_image_paths:
                continue
            self._test_image_paths.append(p)
            pix = QPixmap(p)
            item = QListWidgetItem()
            if not pix.isNull():
                from PyQt5.QtGui import QIcon
                item.setIcon(QIcon(
                    pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                ))
            item.setText(Path(p).name)
            item.setData(Qt.UserRole, p)
            self._test_list.addItem(item)

    def _on_clear_test_images(self):
        self._test_image_paths.clear()
        self._test_list.clear()
        self._test_preview.clear()
        self._test_result_label.setText("")

    def _on_test_image_selected(self, row: int):
        if row < 0:
            return
        item = self._test_list.item(row)
        path = item.data(Qt.UserRole)
        self._show_test_image(path, boxes=[])

    # ------------------------------------------------------------------
    # Run test matching
    # ------------------------------------------------------------------

    def _on_run_test(self):
        cropped = self._crop_widget.get_cropped_image()
        if cropped is None:
            self._test_result_label.setText("没有可用的模板图像")
            return

        if not self._test_image_paths:
            self._test_result_label.setText("请先添加测试图片")
            return

        row = self._test_list.currentRow()
        if row < 0:
            row = 0
            self._test_list.setCurrentRow(0)

        test_path = self._test_image_paths[row]
        label = self.get_label()

        tpl_info = TemplateMatcher.create_template_from_image(
            cropped, label, self._image_path
        )
        matcher = TemplateMatcher(
            threshold=self._test_threshold.value(),
            max_candidates=50,
            multi_scale=False,
        )
        result = matcher.match(test_path, [tpl_info])

        self._show_test_image(test_path, result.boxes)

        if result.boxes:
            self._test_result_label.setText(
                f"找到 {len(result.boxes)} 个匹配  "
                f"(最高置信度: {max(b.confidence for b in result.boxes):.3f})"
            )
        else:
            self._test_result_label.setText("未找到匹配")

        self._update_test_list_results(matcher, tpl_info)

    def _update_test_list_results(
        self, matcher: TemplateMatcher, tpl_info: TemplateInfo
    ):
        for i, path in enumerate(self._test_image_paths):
            item = self._test_list.item(i)
            if item is None:
                continue
            if i == self._test_list.currentRow():
                continue
            result = matcher.match(path, [tpl_info])
            n = len(result.boxes)
            name = Path(path).name
            item.setText(f"{name}  ({n} 个匹配)" if n else name)

    def _show_test_image(self, path: str, boxes):
        img = imread_unicode(path)
        if img is None:
            self._test_preview.setText("无法读取图片")
            return

        for box in boxes:
            color = (0, 255, 0)
            cv2.rectangle(
                img,
                (box.x_min, box.y_min),
                (box.x_max, box.y_max),
                color,
                2,
            )
            label_text = f"{box.label} {box.confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(
                img,
                (box.x_min, box.y_min - th - 6),
                (box.x_min + tw + 4, box.y_min),
                color,
                -1,
            )
            cv2.putText(
                img,
                label_text,
                (box.x_min + 2, box.y_min - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        lw = self._test_preview.width() or 400
        lh = self._test_preview.height() or 300
        scaled = pixmap.scaled(
            lw, lh, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._test_preview.setPixmap(scaled)
