"""训练前数据准备页面。"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import QFileDialog, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    CaptionLabel,
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
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

from ez_traing.data_prep.augmentation import get_augmentation_specs
from ez_traing.data_prep.models import DataPrepConfig, DataPrepSummary
from ez_traing.data_prep.pipeline import DataPrepPipeline


def _get_default_output_dir() -> str:
    output_dir = Path.home() / ".ez_traing" / "prepared_dataset"
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)


class DataPrepWorker(QThread):
    """数据准备后台线程。"""

    progress = pyqtSignal(int, str)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str, object)

    def __init__(self, config: DataPrepConfig):
        super().__init__()
        self._config = config
        self._cancelled = False

    def run(self):
        try:
            pipeline = DataPrepPipeline(self._config)
            summary = pipeline.run(
                log_callback=self.log.emit,
                progress_callback=self.progress.emit,
                is_cancelled=lambda: self._cancelled,
            )
            if self._cancelled:
                self.finished.emit(False, "任务已取消", None)
                return
            self.finished.emit(True, "数据准备完成", summary)
        except Exception as e:
            self.finished.emit(False, str(e), None)

    def cancel(self):
        self._cancelled = True
        self.log.emit("收到取消请求，正在停止...")


class DataPrepPage(QWidget):
    """训练前数据准备页面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_manager = None
        self._project_ids: List[str] = []
        self._current_project_id: Optional[str] = None
        self._worker: Optional[DataPrepWorker] = None
        self._method_checkboxes: Dict[str, CheckBox] = {}
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = ScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget(self)
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(36, 20, 36, 20)
        self._content_layout.setSpacing(16)

        self._content_layout.addWidget(TitleLabel("训练前数据准备", self))
        self._content_layout.addWidget(self._create_dataset_card())
        self._content_layout.addWidget(self._create_split_card())
        self._content_layout.addWidget(self._create_augmentation_card())
        self._content_layout.addWidget(self._create_output_card())
        self._content_layout.addWidget(self._create_action_card())
        self._content_layout.addWidget(self._create_log_card())
        self._content_layout.addStretch()

        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)

    def _create_dataset_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel("数据源", card))
        layout.addWidget(StrongBodyLabel("选择数据集项目", card))
        self.dataset_combo = ComboBox(card)
        self.dataset_combo.setPlaceholderText("请先在数据集页面创建项目")
        self.dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        layout.addWidget(self.dataset_combo)

        btn_layout = QHBoxLayout()
        self.refresh_dataset_btn = PushButton("刷新项目列表", card)
        self.refresh_dataset_btn.setIcon(FIF.SYNC)
        self.refresh_dataset_btn.clicked.connect(self._refresh_dataset_list)
        btn_layout.addWidget(self.refresh_dataset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.dataset_info_label = CaptionLabel("未选择数据集", card)
        self.dataset_info_label.setWordWrap(True)
        layout.addWidget(self.dataset_info_label)
        return card

    def _create_split_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel("训练集 / 验证集划分", card))

        ratio_layout = QHBoxLayout()
        ratio_layout.addWidget(BodyLabel("训练集比例 (%)", card))
        self.train_ratio_spin = SpinBox(card)
        self.train_ratio_spin.setRange(50, 95)
        self.train_ratio_spin.setValue(80)
        self.train_ratio_spin.valueChanged.connect(self._update_ratio_hint)
        ratio_layout.addWidget(self.train_ratio_spin)
        ratio_layout.addStretch()
        layout.addLayout(ratio_layout)

        seed_layout = QHBoxLayout()
        seed_layout.addWidget(BodyLabel("随机种子", card))
        self.seed_spin = SpinBox(card)
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setValue(42)
        seed_layout.addWidget(self.seed_spin)
        seed_layout.addStretch()
        layout.addLayout(seed_layout)

        self.ratio_hint_label = CaptionLabel("", card)
        layout.addWidget(self.ratio_hint_label)
        layout.addWidget(
            CaptionLabel("已启用防泄露划分：同源命名样本会按组分到同一集合", card)
        )
        self._update_ratio_hint()
        return card

    def _create_augmentation_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel("数据增强", card))
        self.enable_aug_cb = CheckBox("启用数据增强", card)
        self.enable_aug_cb.setChecked(True)
        self.enable_aug_cb.toggled.connect(self._on_aug_toggled)
        layout.addWidget(self.enable_aug_cb)

        count_layout = QHBoxLayout()
        count_layout.addWidget(BodyLabel("每张图生成增强样本数", card))
        self.aug_count_spin = SpinBox(card)
        self.aug_count_spin.setRange(1, 10)
        self.aug_count_spin.setValue(1)
        count_layout.addWidget(self.aug_count_spin)
        count_layout.addStretch()
        layout.addLayout(count_layout)

        scope_layout = QHBoxLayout()
        scope_layout.addWidget(BodyLabel("增强作用范围", card))
        self.aug_scope_combo = ComboBox(card)
        self.aug_scope_combo.addItem("仅训练集", "train")
        self.aug_scope_combo.addItem("训练集 + 验证集", "both")
        scope_layout.addWidget(self.aug_scope_combo)
        scope_layout.addStretch()
        layout.addLayout(scope_layout)

        layout.addWidget(CaptionLabel("可多选增强方法（越多越强，但耗时更长）", card))

        self.aug_methods_container = QWidget(card)
        methods_layout = QGridLayout(self.aug_methods_container)
        methods_layout.setContentsMargins(0, 0, 0, 0)
        methods_layout.setHorizontalSpacing(18)
        methods_layout.setVerticalSpacing(6)

        specs = get_augmentation_specs()
        for i, (key, display_name) in enumerate(specs):
            cb = CheckBox(display_name, self.aug_methods_container)
            cb.setChecked(key in {"hflip", "brightness_contrast", "gauss_noise"})
            row = i // 3
            col = i % 3
            methods_layout.addWidget(cb, row, col)
            self._method_checkboxes[key] = cb
        layout.addWidget(self.aug_methods_container)

        self.aug_hint_label = CaptionLabel("当前已选择 3 种增强方法", card)
        layout.addWidget(self.aug_hint_label)

        for cb in self._method_checkboxes.values():
            cb.toggled.connect(self._update_aug_hint)

        self._update_aug_hint()
        self._on_aug_toggled(self.enable_aug_cb.isChecked())
        return card

    def _create_output_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel("输出设置", card))
        layout.addWidget(StrongBodyLabel("输出目录", card))

        row = QHBoxLayout()
        self.output_dir_edit = LineEdit(card)
        self.output_dir_edit.setText(_get_default_output_dir())
        row.addWidget(self.output_dir_edit, 1)
        self.browse_output_btn = PushButton("浏览", card)
        self.browse_output_btn.setIcon(FIF.FOLDER)
        self.browse_output_btn.clicked.connect(self._browse_output_dir)
        row.addWidget(self.browse_output_btn)
        layout.addLayout(row)

        self.skip_unlabeled_cb = CheckBox("仅处理有 VOC 标注的图片（跳过无标注）", card)
        self.skip_unlabeled_cb.setChecked(True)
        layout.addWidget(self.skip_unlabeled_cb)

        self.overwrite_cb = CheckBox("覆盖输出目录中的旧结果（images/labels/data.yaml/classes.txt）", card)
        self.overwrite_cb.setChecked(True)
        layout.addWidget(self.overwrite_cb)
        return card

    def _create_action_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel("执行", card))
        btn_layout = QHBoxLayout()
        self.start_btn = PrimaryPushButton("开始准备数据", card)
        self.start_btn.setIcon(FIF.PLAY)
        self.start_btn.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.start_btn)

        self.cancel_btn = PushButton("取消", card)
        self.cancel_btn.setIcon(FIF.CLOSE)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.cancel_btn)

        self.open_output_btn = PushButton("打开输出目录", card)
        self.open_output_btn.setIcon(FIF.FOLDER)
        self.open_output_btn.clicked.connect(self._open_output_dir)
        btn_layout.addWidget(self.open_output_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.progress_bar = ProgressBar(card)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.progress_label = CaptionLabel("就绪", card)
        layout.addWidget(self.progress_label)
        return card

    def _create_log_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(SubtitleLabel("日志", card))
        header.addStretch()
        clear_btn = PushButton("清空", card)
        clear_btn.clicked.connect(lambda: self.log_edit.clear())
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self.log_edit = TextEdit(card)
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(220)
        self.log_edit.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_edit)
        return card

    def set_project_manager(self, manager) -> None:
        self._project_manager = manager

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_dataset_list()

    def _refresh_dataset_list(self):
        if self._project_manager is None:
            return

        prev_id = self._current_project_id
        self.dataset_combo.blockSignals(True)
        self.dataset_combo.clear()
        self._project_ids.clear()

        projects = self._project_manager.get_all_projects()
        for proj in projects:
            self.dataset_combo.addItem(f"{proj.name} ({proj.image_count} 张)")
            self._project_ids.append(proj.id)

        if not projects:
            self.dataset_info_label.setText("请先在“数据集”页面创建项目")
            self._current_project_id = None
        elif prev_id in self._project_ids:
            idx = self._project_ids.index(prev_id)
            self.dataset_combo.setCurrentIndex(idx)
            self._current_project_id = prev_id
            self._update_dataset_info(prev_id)
        else:
            self.dataset_combo.setCurrentIndex(0)
            self._current_project_id = self._project_ids[0]
            self._update_dataset_info(self._current_project_id)

        self.dataset_combo.blockSignals(False)

    def _on_dataset_changed(self, index: int):
        if index < 0 or index >= len(self._project_ids):
            self._current_project_id = None
            self.dataset_info_label.setText("未选择数据集")
            return
        self._current_project_id = self._project_ids[index]
        self._update_dataset_info(self._current_project_id)

    def _update_dataset_info(self, project_id: str):
        if self._project_manager is None:
            return
        project = self._project_manager.get_project(project_id)
        if not project:
            return
        self.dataset_info_label.setText(
            f"项目: {project.name}\n目录: {project.directory}\n记录图片数: {project.image_count}"
        )

    def _update_ratio_hint(self):
        train = self.train_ratio_spin.value()
        val = 100 - train
        self.ratio_hint_label.setText(f"当前划分比例: train {train}% / val {val}%")

    def _on_aug_toggled(self, enabled: bool):
        self.aug_count_spin.setEnabled(enabled)
        self.aug_scope_combo.setEnabled(enabled)
        self.aug_methods_container.setEnabled(enabled)
        self.aug_hint_label.setEnabled(enabled)

    def _update_aug_hint(self):
        selected = len(self._selected_methods())
        self.aug_hint_label.setText(f"当前已选择 {selected} 种增强方法")

    def _selected_methods(self) -> List[str]:
        return [key for key, cb in self._method_checkboxes.items() if cb.isChecked()]

    def _browse_output_dir(self):
        current = self.output_dir_edit.text().strip() or _get_default_output_dir()
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", current)
        if path:
            self.output_dir_edit.setText(path)

    def _open_output_dir(self):
        path = self.output_dir_edit.text().strip()
        if path and os.path.isdir(path):
            os.startfile(path)

    def _on_start_clicked(self):
        if self._project_manager is None:
            return
        if self._current_project_id is None:
            InfoBar.warning(
                title="提示",
                content="请先选择数据集项目",
                parent=self.window(),
                position=InfoBarPosition.TOP,
            )
            return

        project = self._project_manager.get_project(self._current_project_id)
        if not project:
            InfoBar.error(
                title="错误",
                content="数据集项目不存在",
                parent=self.window(),
                position=InfoBarPosition.TOP,
            )
            return

        if not os.path.isdir(project.directory):
            InfoBar.error(
                title="错误",
                content=f"数据集目录不存在: {project.directory}",
                parent=self.window(),
                position=InfoBarPosition.TOP,
            )
            return

        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            InfoBar.warning(
                title="提示",
                content="请选择输出目录",
                parent=self.window(),
                position=InfoBarPosition.TOP,
            )
            return
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        methods: List[str] = []
        augment_times = 0
        augment_scope = "train"
        if self.enable_aug_cb.isChecked():
            methods = self._selected_methods()
            if not methods:
                InfoBar.warning(
                    title="提示",
                    content="已启用增强，请至少选择一种增强方法",
                    parent=self.window(),
                    position=InfoBarPosition.TOP,
                )
                return
            augment_times = self.aug_count_spin.value()
            augment_scope = self.aug_scope_combo.currentData()

        config = DataPrepConfig(
            dataset_name=project.name,
            dataset_dir=project.directory,
            output_dir=output_dir,
            train_ratio=self.train_ratio_spin.value() / 100.0,
            random_seed=self.seed_spin.value(),
            augment_methods=methods,
            augment_times=augment_times,
            augment_scope=augment_scope,
            skip_unlabeled=self.skip_unlabeled_cb.isChecked(),
            overwrite_output=self.overwrite_cb.isChecked(),
        )

        self._worker = DataPrepWorker(config)
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._log)
        self._worker.finished.connect(self._on_finished)

        self.progress_bar.setValue(0)
        self.progress_label.setText("正在准备数据...")
        self._set_running_state(True)
        self._log("任务启动")
        self._worker.start()

    def _on_cancel_clicked(self):
        if self._worker:
            self._worker.cancel()

    def _on_progress(self, percent: int, text: str):
        self.progress_bar.setValue(percent)
        self.progress_label.setText(text)

    def _on_finished(self, success: bool, message: str, summary_obj: object):
        self._set_running_state(False)
        if success:
            summary: DataPrepSummary = summary_obj
            self.progress_bar.setValue(100)
            self.progress_label.setText(
                f"完成: train={summary.train_images}, val={summary.val_images}, 增强={summary.augmented_images}"
            )
            self._log(
                f"完成: 输出 {summary.processed_images} 张, 类别 {summary.classes_count} 个, "
                f"YAML={summary.yaml_path}"
            )
            InfoBar.success(
                title="数据准备完成",
                content=f"输出目录: {summary.output_dir}",
                parent=self.window(),
                position=InfoBarPosition.TOP,
                duration=5000,
            )
        else:
            self._log(f"失败: {message}")
            self.progress_label.setText("执行失败")
            InfoBar.error(
                title="执行失败",
                content=message,
                parent=self.window(),
                position=InfoBarPosition.TOP,
            )
        self._worker = None

    def _set_running_state(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        self.dataset_combo.setEnabled(not running)
        self.refresh_dataset_btn.setEnabled(not running)
        self.train_ratio_spin.setEnabled(not running)
        self.seed_spin.setEnabled(not running)
        self.enable_aug_cb.setEnabled(not running)
        self.aug_count_spin.setEnabled(not running and self.enable_aug_cb.isChecked())
        self.aug_scope_combo.setEnabled(not running and self.enable_aug_cb.isChecked())
        self.aug_methods_container.setEnabled(not running and self.enable_aug_cb.isChecked())
        self.output_dir_edit.setEnabled(not running)
        self.browse_output_btn.setEnabled(not running)
        self.skip_unlabeled_cb.setEnabled(not running)
        self.overwrite_cb.setEnabled(not running)

    def _log(self, text: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_edit.append(f"[{timestamp}] {text}")
        cursor = self.log_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_edit.setTextCursor(cursor)
