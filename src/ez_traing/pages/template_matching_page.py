"""模板匹配标注页面 - 使用 OpenCV 模板匹配进行数据标注"""

import logging
import os
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Dict, List, Optional, Tuple

import cv2
from PyQt5.QtCore import QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QImage, QPixmap, QTextCursor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox as QtCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    CaptionLabel,
    CheckBox,
    ComboBox,
    DoubleSpinBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    ScrollArea,
    SpinBox,
    StrongBodyLabel,
    SubtitleLabel,
    TextEdit,
    TitleLabel,
)

from ez_traing.common.constants import SUPPORTED_IMAGE_FORMATS
from ez_traing.pages.template_editor_dialog import TemplateEditorDialog
from ez_traing.prelabeling.models import BoundingBox
from ez_traing.prelabeling.voc_writer import VOCAnnotationWriter
from ez_traing.template_matching.matcher import TemplateMatcher, TemplateInfo, imread_unicode
from ez_traing.template_matching.worker import TemplateMatchingStats, TemplateMatchingWorker

logger = logging.getLogger(__name__)


# ======================================================================
# Image scan worker (reused pattern from prelabeling_page)
# ======================================================================


class _ImageScanWorker(QThread):
    finished = pyqtSignal(str, list, str, float)

    def __init__(self, project_id: str, directory: str):
        super().__init__()
        self._project_id = project_id
        self._directory = directory
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        t0 = perf_counter()
        paths: List[str] = []
        error = ""
        try:
            for root, _, files in os.walk(self._directory):
                if self._cancelled:
                    break
                for f in files:
                    if Path(f).suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                        paths.append(os.path.join(root, f))
            paths.sort()
        except OSError as e:
            error = str(e)
        self.finished.emit(self._project_id, paths, error, perf_counter() - t0)


# ======================================================================
# Template Matching Page
# ======================================================================


class TemplateMatchingPage(QWidget):
    """模板匹配标注页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_manager = None
        self._project_ids: List[str] = []
        self._current_project_id: Optional[str] = None
        self._image_paths: List[str] = []
        self._scan_worker: Optional[_ImageScanWorker] = None
        self._scan_cache: Dict[str, Tuple[int, List[str]]] = {}
        self._worker: Optional[TemplateMatchingWorker] = None

        # 模板列表：(path, label, TemplateInfo)
        self._template_infos: List[TemplateInfo] = []

        # 匹配结果：image_path -> list[BoundingBox]
        self._match_results: Dict[str, List[BoundingBox]] = {}
        # 勾选状态：(image_path, box_index) -> checked
        self._check_states: Dict[Tuple[str, int], bool] = {}

        self._run_started_at: Optional[float] = None
        self._log_buffer: List[str] = []
        self._log_flush_timer = QTimer(self)
        self._log_flush_timer.setInterval(100)
        self._log_flush_timer.timeout.connect(self._flush_log_buffer)

        self._voc_writer = VOCAnnotationWriter()

        self._setup_ui()

    # ==================================================================
    # UI Setup
    # ==================================================================

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(36, 20, 36, 20)
        self._content_layout.setSpacing(16)

        self._content_layout.addWidget(TitleLabel("模板匹配", self))
        self._content_layout.addSpacing(4)

        self._content_layout.addWidget(self._create_dataset_card())
        self._content_layout.addWidget(self._create_template_card())
        self._content_layout.addWidget(self._create_params_card())
        self._content_layout.addWidget(self._create_action_card())
        self._content_layout.addWidget(self._create_result_card())
        self._content_layout.addWidget(self._create_log_card())
        self._content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # Card: 数据集选择
    # ------------------------------------------------------------------

    def _create_dataset_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel("数据集选择", card))

        self.dataset_combo = ComboBox(card)
        self.dataset_combo.setPlaceholderText("请先在数据集页面创建项目")
        self.dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        layout.addWidget(self.dataset_combo)

        self.dataset_info_label = CaptionLabel("", card)
        layout.addWidget(self.dataset_info_label)

        return card

    # ------------------------------------------------------------------
    # Card: 模板管理
    # ------------------------------------------------------------------

    def _create_template_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel("模板图片", card))

        self._tpl_count_label = CaptionLabel("已添加 0 个模板", card)
        layout.addWidget(self._tpl_count_label)

        self._tpl_list = QListWidget(card)
        self._tpl_list.setMinimumHeight(120)
        self._tpl_list.setMaximumHeight(200)
        self._tpl_list.setSpacing(4)
        self._tpl_list.setIconSize(QSize(64, 64))
        layout.addWidget(self._tpl_list)

        btn_row = QHBoxLayout()
        add_btn = PushButton("添加模板", card)
        add_btn.setIcon(FIF.ADD)
        add_btn.clicked.connect(self._on_add_templates)
        btn_row.addWidget(add_btn)

        remove_btn = PushButton("移除选中", card)
        remove_btn.setIcon(FIF.DELETE)
        remove_btn.clicked.connect(self._on_remove_template)
        btn_row.addWidget(remove_btn)

        clear_btn = PushButton("清空全部", card)
        clear_btn.setIcon(FIF.CLOSE)
        clear_btn.clicked.connect(self._on_clear_templates)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addWidget(
            CaptionLabel(
                "每个模板的文件名（不含扩展名）将作为标注类别名称",
                card,
            )
        )

        return card

    # ------------------------------------------------------------------
    # Card: 匹配参数
    # ------------------------------------------------------------------

    def _create_params_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel("匹配参数", card))

        # 阈值
        row1 = QHBoxLayout()
        row1.addWidget(StrongBodyLabel("匹配阈值", card))
        self.threshold_spin = DoubleSpinBox(card)
        self.threshold_spin.setRange(0.1, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setValue(0.8)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setToolTip("匹配得分不低于此值的候选框才会保留")
        row1.addWidget(self.threshold_spin)
        row1.addStretch()
        layout.addLayout(row1)

        # 最大候选数
        row2 = QHBoxLayout()
        row2.addWidget(StrongBodyLabel("每图最大候选数", card))
        self.max_candidates_spin = SpinBox(card)
        self.max_candidates_spin.setRange(1, 500)
        self.max_candidates_spin.setValue(50)
        row2.addWidget(self.max_candidates_spin)
        row2.addStretch()
        layout.addLayout(row2)

        # 多尺度
        self.multi_scale_cb = CheckBox("启用多尺度搜索", card)
        self.multi_scale_cb.setToolTip(
            "在多种缩放比例下搜索模板，速度较慢但可匹配不同大小的目标"
        )
        layout.addWidget(self.multi_scale_cb)

        # 跳过已有标注
        self.skip_annotated_cb = CheckBox("跳过已有标注的图片", card)
        self.skip_annotated_cb.setChecked(True)
        layout.addWidget(self.skip_annotated_cb)

        return card

    # ------------------------------------------------------------------
    # Card: 操作按钮
    # ------------------------------------------------------------------

    def _create_action_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel("操作", card))

        btn_row = QHBoxLayout()

        self.start_btn = PrimaryPushButton("开始匹配", card)
        self.start_btn.setIcon(FIF.PLAY)
        self.start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self.start_btn)

        self.cancel_btn = PushButton("取消", card)
        self.cancel_btn.setIcon(FIF.CLOSE)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.progress_bar = ProgressBar(card)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.progress_label = CaptionLabel("就绪", card)
        layout.addWidget(self.progress_label)

        return card

    # ------------------------------------------------------------------
    # Card: 结果预览
    # ------------------------------------------------------------------

    def _create_result_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(SubtitleLabel("匹配结果预览", card))
        header.addStretch()

        self._select_all_btn = PushButton("全选", card)
        self._select_all_btn.clicked.connect(self._on_select_all)
        header.addWidget(self._select_all_btn)

        self._deselect_all_btn = PushButton("全不选", card)
        self._deselect_all_btn.clicked.connect(self._on_deselect_all)
        header.addWidget(self._deselect_all_btn)

        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal, card)

        # 左侧：结果图片列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(StrongBodyLabel("图片列表", left))

        self._result_image_list = QListWidget(left)
        self._result_image_list.currentRowChanged.connect(self._on_result_image_selected)
        left_layout.addWidget(self._result_image_list)
        splitter.addWidget(left)

        # 右侧：候选框表格 + 预览图
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(StrongBodyLabel("候选框", right))

        self._box_table = QTableWidget(right)
        self._box_table.setColumnCount(7)
        self._box_table.setHorizontalHeaderLabels(
            ["选择", "标签", "x_min", "y_min", "x_max", "y_max", "置信度"]
        )
        self._box_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self._box_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._box_table.setMinimumHeight(160)
        self._box_table.setMaximumHeight(240)
        right_layout.addWidget(self._box_table)

        self._preview_label = QLabel(right)
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setMinimumHeight(240)
        self._preview_label.setStyleSheet(
            "background: #222; border-radius: 4px;"
        )
        right_layout.addWidget(self._preview_label)

        splitter.addWidget(right)
        splitter.setSizes([280, 600])

        layout.addWidget(splitter)

        # 保存按钮
        save_row = QHBoxLayout()
        self.save_btn = PrimaryPushButton("保存选中结果", card)
        self.save_btn.setIcon(FIF.SAVE)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save)
        save_row.addWidget(self.save_btn)
        save_row.addStretch()

        self._result_summary_label = CaptionLabel("", card)
        save_row.addWidget(self._result_summary_label)

        layout.addLayout(save_row)

        return card

    # ------------------------------------------------------------------
    # Card: 日志
    # ------------------------------------------------------------------

    def _create_log_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(SubtitleLabel("日志", card))
        hdr.addStretch()
        clear_btn = PushButton("清空", card)
        clear_btn.clicked.connect(self._clear_log)
        hdr.addWidget(clear_btn)
        layout.addLayout(hdr)

        self.log_text = TextEdit(card)
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(160)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)

        return card

    # ==================================================================
    # Public API
    # ==================================================================

    def set_project_manager(self, manager):
        self._project_manager = manager

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_dataset_list()

    # ==================================================================
    # Dataset handling (same pattern as PrelabelingPage)
    # ==================================================================

    def _refresh_dataset_list(self):
        if not self._project_manager:
            return

        prev = self._current_project_id

        self.dataset_combo.blockSignals(True)
        self.dataset_combo.clear()
        self._project_ids.clear()

        for proj in self._project_manager.get_all_projects():
            self.dataset_combo.addItem(f"{proj.name} ({proj.image_count} 张图片)")
            self._project_ids.append(proj.id)

        if not self._project_ids:
            self.dataset_info_label.setText("请先在数据集页面创建项目")
        elif prev in self._project_ids:
            self.dataset_combo.setCurrentIndex(self._project_ids.index(prev))
        else:
            self._current_project_id = None
            self._image_paths.clear()
            self.dataset_info_label.setText("")

        self.dataset_combo.blockSignals(False)

    def _on_dataset_changed(self, index: int):
        if index < 0 or index >= len(self._project_ids):
            self._current_project_id = None
            self._image_paths.clear()
            self.dataset_info_label.setText("")
            return

        pid = self._project_ids[index]
        self._current_project_id = pid
        proj = self._project_manager.get_project(pid)
        if proj:
            self._scan_project(proj)

    def _scan_project(self, project):
        if not os.path.isdir(project.directory):
            self._image_paths.clear()
            self.dataset_info_label.setText("目录不存在")
            self._log(f"目录不存在: {project.directory}", "error")
            return

        try:
            mtime = Path(project.directory).stat().st_mtime_ns
        except OSError:
            mtime = -1

        cached = self._scan_cache.get(project.id)
        if cached and cached[0] == mtime:
            self._image_paths = list(cached[1])
            self.dataset_info_label.setText(
                f"已加载 {len(self._image_paths)} 张图片（缓存）"
            )
            return

        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()

        self.dataset_info_label.setText("正在扫描图片...")
        self._scan_worker = _ImageScanWorker(project.id, project.directory)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_scan_finished(self, project_id, paths, error, elapsed):
        if project_id != self._current_project_id:
            return
        if error:
            self._image_paths.clear()
            self.dataset_info_label.setText("扫描出错")
            self._log(f"扫描出错: {error}", "error")
            return
        self._image_paths = list(paths)
        self.dataset_info_label.setText(f"已加载 {len(paths)} 张图片")
        self._log(f"已加载 {len(paths)} 张图片，耗时 {elapsed:.2f}s")

        try:
            proj = self._project_manager.get_project(project_id)
            if proj:
                mtime = Path(proj.directory).stat().st_mtime_ns
                self._scan_cache[project_id] = (mtime, list(paths))
        except OSError:
            pass

    # ==================================================================
    # Template management
    # ==================================================================

    def _on_add_templates(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择模板图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.webp);;所有文件 (*)",
        )
        if not paths:
            return

        added = 0
        for p in paths:
            if any(t.path == p and t.label == Path(p).stem for t in self._template_infos):
                continue

            dialog = TemplateEditorDialog(p, Path(p).stem, parent=self.window())
            if dialog.exec_() != QDialog.Accepted:
                continue

            cropped = dialog.get_cropped_image()
            label = dialog.get_label()
            if cropped is None:
                self._log(f"无法读取图片: {p}", "error")
                continue

            info = TemplateMatcher.create_template_from_image(cropped, label, p)
            self._template_infos.append(info)
            self._add_template_list_item(info)
            added += 1

        if added:
            self._update_tpl_count()
            self._log(f"添加了 {added} 个模板")

    def _add_template_list_item(self, info: TemplateInfo):
        if info.image is not None:
            rgb = cv2.cvtColor(info.image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg)
        else:
            pix = QPixmap(info.path)

        if pix.isNull():
            pix = QPixmap(64, 64)
            pix.fill(Qt.lightGray)
        else:
            pix = pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        item = QListWidgetItem()
        item.setIcon(QIcon(pix))
        item.setText(f"{info.label}  ({info.width}x{info.height})")
        item.setToolTip(info.path)
        item.setData(Qt.UserRole, info.path)
        self._tpl_list.addItem(item)

    def _on_remove_template(self):
        row = self._tpl_list.currentRow()
        if row < 0:
            return
        item = self._tpl_list.takeItem(row)
        path = item.data(Qt.UserRole)
        self._template_infos = [t for t in self._template_infos if t.path != path]
        self._update_tpl_count()

    def _on_clear_templates(self):
        self._template_infos.clear()
        self._tpl_list.clear()
        self._update_tpl_count()

    def _update_tpl_count(self):
        self._tpl_count_label.setText(f"已添加 {len(self._template_infos)} 个模板")

    # ==================================================================
    # Matching flow
    # ==================================================================

    def _on_start(self):
        if not self._template_infos:
            InfoBar.warning(
                title="提示",
                content="请先添加至少一个模板图片",
                parent=self.window(),
                position=InfoBarPosition.TOP,
            )
            return

        if not self._image_paths:
            InfoBar.warning(
                title="提示",
                content="当前数据集没有图片",
                parent=self.window(),
                position=InfoBarPosition.TOP,
            )
            return

        matcher = TemplateMatcher(
            threshold=self.threshold_spin.value(),
            max_candidates=self.max_candidates_spin.value(),
            multi_scale=self.multi_scale_cb.isChecked(),
        )

        self._match_results.clear()
        self._check_states.clear()
        self._result_image_list.clear()
        self._box_table.setRowCount(0)
        self._preview_label.clear()
        self.save_btn.setEnabled(False)
        self._result_summary_label.setText("")

        self._worker = TemplateMatchingWorker(
            image_paths=self._image_paths,
            templates=self._template_infos,
            matcher=matcher,
            skip_annotated=self.skip_annotated_cb.isChecked(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.image_completed.connect(self._on_image_completed)
        self._worker.finished.connect(self._on_finished)

        self._set_running(True)
        self._run_started_at = perf_counter()
        self._log("模板匹配开始")
        self._log(f"模板数: {len(self._template_infos)}, 图片数: {len(self._image_paths)}")
        self._worker.start()

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
            self._log("正在取消...", "warning")

    def _on_progress(self, current, total, message):
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))
        self.progress_label.setText(f"{current}/{total} - {message}")

    def _on_image_completed(self, path, success, message, boxes):
        if boxes:
            self._match_results[path] = boxes
            for i in range(len(boxes)):
                self._check_states[(path, i)] = True

            item = QListWidgetItem(
                f"{Path(path).name}  ({len(boxes)} 个)"
            )
            item.setData(Qt.UserRole, path)
            self._result_image_list.addItem(item)

        if not success:
            self._log(message, "error")

    def _on_finished(self, stats: TemplateMatchingStats):
        self._set_running(False)
        self.progress_bar.setValue(100)

        elapsed = 0.0
        if self._run_started_at:
            elapsed = perf_counter() - self._run_started_at
            self._run_started_at = None

        total_boxes = sum(len(b) for b in self._match_results.values())
        summary = (
            f"完成 - 总计: {stats.total}, 匹配: {stats.matched}, "
            f"无匹配: {stats.empty}, 失败: {stats.failed}, "
            f"跳过: {stats.skipped}, 候选框: {total_boxes}"
        )
        self._log(summary)
        self._log(f"耗时: {elapsed:.2f}s")
        self.progress_label.setText(summary)

        if total_boxes > 0:
            self.save_btn.setEnabled(True)
            self._result_summary_label.setText(
                f"{len(self._match_results)} 张图片共 {total_boxes} 个候选框"
            )
        else:
            self._result_summary_label.setText("未找到任何匹配")

        InfoBar.success(
            title="模板匹配完成",
            content=summary,
            parent=self.window(),
            position=InfoBarPosition.TOP,
            duration=5000,
        )

        self._worker = None

    # ==================================================================
    # Result preview
    # ==================================================================

    def _on_result_image_selected(self, row):
        if row < 0:
            self._box_table.setRowCount(0)
            self._preview_label.clear()
            return

        item = self._result_image_list.item(row)
        path = item.data(Qt.UserRole)
        boxes = self._match_results.get(path, [])

        self._populate_box_table(path, boxes)
        self._render_preview(path, boxes)

    def _populate_box_table(self, image_path: str, boxes: List[BoundingBox]):
        self._box_table.blockSignals(True)
        self._box_table.setRowCount(len(boxes))

        for i, box in enumerate(boxes):
            cb = QtCheckBox()
            cb.setChecked(self._check_states.get((image_path, i), True))
            cb.stateChanged.connect(
                lambda state, p=image_path, idx=i: self._on_box_check_changed(
                    p, idx, state == Qt.Checked
                )
            )
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self._box_table.setCellWidget(i, 0, cb_widget)

            self._box_table.setItem(i, 1, QTableWidgetItem(box.label))
            self._box_table.setItem(i, 2, QTableWidgetItem(str(box.x_min)))
            self._box_table.setItem(i, 3, QTableWidgetItem(str(box.y_min)))
            self._box_table.setItem(i, 4, QTableWidgetItem(str(box.x_max)))
            self._box_table.setItem(i, 5, QTableWidgetItem(str(box.y_max)))
            self._box_table.setItem(
                i, 6, QTableWidgetItem(f"{box.confidence:.3f}")
            )

            for col in range(1, 7):
                it = self._box_table.item(i, col)
                if it:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)

        self._box_table.blockSignals(False)

    def _on_box_check_changed(self, image_path: str, idx: int, checked: bool):
        self._check_states[(image_path, idx)] = checked

    def _render_preview(self, image_path: str, boxes: List[BoundingBox]):
        """在预览区绘制带候选框的图片。"""
        img = imread_unicode(image_path)
        if img is None:
            self._preview_label.setText("无法读取图片")
            return

        for i, box in enumerate(boxes):
            checked = self._check_states.get((image_path, i), True)
            color = (0, 255, 0) if checked else (128, 128, 128)
            cv2.rectangle(img, (box.x_min, box.y_min), (box.x_max, box.y_max), color, 2)
            label_text = f"{box.label} {box.confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
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

        label_w = self._preview_label.width() or 560
        label_h = self._preview_label.height() or 400
        scaled = pixmap.scaled(label_w, label_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._preview_label.setPixmap(scaled)

    # ==================================================================
    # Select / Deselect all
    # ==================================================================

    def _on_select_all(self):
        for key in self._check_states:
            self._check_states[key] = True
        self._refresh_current_table()

    def _on_deselect_all(self):
        for key in self._check_states:
            self._check_states[key] = False
        self._refresh_current_table()

    def _refresh_current_table(self):
        row = self._result_image_list.currentRow()
        if row >= 0:
            item = self._result_image_list.item(row)
            path = item.data(Qt.UserRole)
            boxes = self._match_results.get(path, [])
            self._populate_box_table(path, boxes)
            self._render_preview(path, boxes)

    # ==================================================================
    # Save
    # ==================================================================

    def _on_save(self):
        saved_count = 0
        merged_count = 0
        total_boxes = 0

        for image_path, boxes in self._match_results.items():
            selected: List[BoundingBox] = []
            for i, box in enumerate(boxes):
                if self._check_states.get((image_path, i), True):
                    selected.append(box)

            if not selected:
                continue

            try:
                image_size = self._voc_writer._get_image_size(image_path)
                has_existing = Path(image_path).with_suffix(".xml").exists()

                if has_existing:
                    self._voc_writer.save_merged_annotation(
                        image_path, image_size, selected
                    )
                    merged_count += 1
                else:
                    self._voc_writer.save_annotation(
                        image_path, image_size, selected
                    )

                saved_count += 1
                total_boxes += len(selected)
            except Exception as exc:
                self._log(f"保存失败 {Path(image_path).name}: {exc}", "error")

        summary = f"已保存 {saved_count} 张图片的 {total_boxes} 个标注框"
        if merged_count:
            summary += f"（其中 {merged_count} 张与已有标注合并）"

        self._log(summary)
        InfoBar.success(
            title="保存完成",
            content=summary,
            parent=self.window(),
            position=InfoBarPosition.TOP,
            duration=5000,
        )

    # ==================================================================
    # UI state
    # ==================================================================

    def _set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        self.cancel_btn.setVisible(running)
        self.dataset_combo.setEnabled(not running)
        self.threshold_spin.setEnabled(not running)
        self.max_candidates_spin.setEnabled(not running)
        self.multi_scale_cb.setEnabled(not running)
        self.skip_annotated_cb.setEnabled(not running)
        self.save_btn.setEnabled(not running and bool(self._match_results))

    # ==================================================================
    # Logging
    # ==================================================================

    def _log(self, message: str, level: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S")
        tag = level.upper()
        self._log_buffer.append(f"[{ts}] [{tag}] {message}")
        if not self._log_flush_timer.isActive():
            self._log_flush_timer.start()

    def _flush_log_buffer(self):
        if not self._log_buffer:
            self._log_flush_timer.stop()
            return
        chunk = "\n".join(self._log_buffer)
        self._log_buffer.clear()
        self.log_text.append(chunk)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        self._log_flush_timer.stop()

    def _clear_log(self):
        self._log_buffer.clear()
        self.log_text.clear()
