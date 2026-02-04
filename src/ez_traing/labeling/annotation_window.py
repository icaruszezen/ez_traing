import os
import re
import sys
import types
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QPalette
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

LABELIMG_ROOT = Path(__file__).resolve().parents[2] / "third_party" / "labelImg"
RESOURCES_ROOT = LABELIMG_ROOT / "resources"
ICONS_DIR = RESOURCES_ROOT / "icons"
STRINGS_DIR = RESOURCES_ROOT / "strings"


def _ensure_labelimg_path():
    if str(LABELIMG_ROOT) not in sys.path:
        sys.path.insert(0, str(LABELIMG_ROOT))


def _ensure_resources_stub():
    if "libs.resources" not in sys.modules:
        sys.modules["libs.resources"] = types.ModuleType("libs.resources")


def _resolve_icon_path(icon_name):
    alias_map = {
        "help": "help.png",
        "app": "app.png",
        "expert": "expert2.png",
        "done": "done.png",
        "file": "file.png",
        "labels": "labels.png",
        "new": "objects.png",
        "close": "close.png",
        "fit-width": "fit-width.png",
        "fit-window": "fit-window.png",
        "undo": "undo.png",
        "hide": "eye.png",
        "quit": "quit.png",
        "copy": "copy.png",
        "edit": "edit.png",
        "open": "open.png",
        "save": "save.png",
        "format_voc": "format_voc.png",
        "format_yolo": "format_yolo.png",
        "format_createml": "format_createml.png",
        "save-as": "save-as.png",
        "color": "color.png",
        "color_line": "color_line.png",
        "zoom": "zoom.png",
        "zoom-in": "zoom-in.png",
        "zoom-out": "zoom-out.png",
        "light_reset": "light_reset.png",
        "light_lighten": "light_lighten.png",
        "light_darken": "light_darken.png",
        "delete": "cancel.png",
        "next": "next.png",
        "prev": "prev.png",
        "resetall": "resetall.png",
        "verify": "verify.png",
    }

    filename = alias_map.get(icon_name)
    if filename:
        candidate = ICONS_DIR / filename
        if candidate.exists():
            return candidate

    for ext in (".png", ".svg", ".ico"):
        candidate = ICONS_DIR / f"{icon_name}{ext}"
        if candidate.exists():
            return candidate

    return None


def _new_icon(icon_name):
    path = _resolve_icon_path(icon_name)
    return QIcon(str(path)) if path else QIcon()


def _apply_fluent_palette(widget):
    palette = widget.palette()
    palette.setColor(QPalette.Window, QColor("#F3F4F7"))
    palette.setColor(QPalette.WindowText, QColor("#1F1F1F"))
    palette.setColor(QPalette.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.AlternateBase, QColor("#F6F6F8"))
    palette.setColor(QPalette.Text, QColor("#1F1F1F"))
    palette.setColor(QPalette.Button, QColor("#F7F7F9"))
    palette.setColor(QPalette.ButtonText, QColor("#1F1F1F"))
    palette.setColor(QPalette.Highlight, QColor("#DDEBFF"))
    palette.setColor(QPalette.HighlightedText, QColor("#1F1F1F"))
    palette.setColor(QPalette.ToolTipBase, QColor("#FFFFFF"))
    palette.setColor(QPalette.ToolTipText, QColor("#1F1F1F"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#9E9E9E"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#9E9E9E"))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#9E9E9E"))
    widget.setPalette(palette)


def _apply_fluent_stylesheet(widget):
    accent = "#0078D4"
    widget.setObjectName("fluentAnnotationWindow")
    widget.setAttribute(Qt.WA_StyledBackground, True)
    widget.setStyleSheet(
        f"""
#fluentAnnotationWindow {{
    background-color: #F3F4F7;
}}
#fluentAnnotationWindow QMenuBar {{
    background-color: #F7F7F9;
    color: #1F1F1F;
}}
#fluentAnnotationWindow QMenuBar::item:selected {{
    background-color: #E9EEF6;
}}
#fluentAnnotationWindow QMenu {{
    background-color: #FFFFFF;
    color: #1F1F1F;
    border: 1px solid #E3E3E3;
}}
#fluentAnnotationWindow QMenu::item:selected {{
    background-color: #E9EEF6;
}}
#fluentAnnotationWindow QToolBar {{
    background-color: #F7F7F9;
    border: 1px solid #E3E3E3;
}}
#fluentAnnotationWindow QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    color: #1F1F1F;
    border-radius: 6px;
}}
#fluentAnnotationWindow QToolButton:hover {{
    background-color: #E9EEF6;
    border-color: #D6E4FF;
}}
#fluentAnnotationWindow QToolButton:pressed {{
    background-color: #DDEBFF;
    border-color: #C4D8FF;
}}
#fluentAnnotationWindow QToolButton:checked {{
    background-color: #DDEBFF;
    border-color: #B7D0FF;
}}
#fluentAnnotationWindow QDockWidget {{
    background-color: #F7F7F9;
    border: 1px solid #E3E3E3;
}}
#fluentAnnotationWindow QDockWidget::title {{
    background-color: #F0F2F6;
    color: #1F1F1F;
    padding: 7px 36px 8px 12px;
    font-weight: 600;
    border-bottom: 1px solid #E3E3E3;
    min-height: 32px;
}}
#fluentAnnotationWindow QDockWidget::close-button,
#fluentAnnotationWindow QDockWidget::float-button {{
    border: 1px solid transparent;
    border-radius: 4px;
    subcontrol-position: top right;
    margin: 6px;
}}
#fluentAnnotationWindow QDockWidget::close-button:hover,
#fluentAnnotationWindow QDockWidget::float-button:hover {{
    background-color: #E9EEF6;
    border-color: #D6E4FF;
}}
#fluentAnnotationWindow #dockTitleBar {{
    background-color: #F0F2F6;
    border-bottom: 1px solid #E3E3E3;
}}
#fluentAnnotationWindow #dockTitleLabel {{
    color: #1F1F1F;
    font-weight: 600;
    font-size: 14px;
}}
#fluentAnnotationWindow #dockTitleButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 2px;
}}
#fluentAnnotationWindow #dockTitleButton:hover {{
    background-color: #E9EEF6;
    border-color: #D6E4FF;
}}
#fluentAnnotationWindow #dockTitleButton:pressed {{
    background-color: #DDEBFF;
    border-color: #C4D8FF;
}}
#fluentAnnotationWindow #labelDockContainer,
#fluentAnnotationWindow #fileDockContainer {{
    background-color: transparent;
    font-size: 13px;
}}
#fluentAnnotationWindow QFrame#panelSeparator {{
    background-color: #E3E3E3;
    border: none;
}}
#fluentAnnotationWindow QListWidget,
#fluentAnnotationWindow QTreeView,
#fluentAnnotationWindow QTableView {{
    background-color: #FFFFFF;
    border: 1px solid #E3E3E3;
    border-radius: 6px;
    color: #1F1F1F;
    outline: none;
}}
#fluentAnnotationWindow QListWidget::item {{
    padding: 8px 12px;
    margin: 2px 4px;
    border-radius: 4px;
    font-size: 13px;
}}
#fluentAnnotationWindow QListWidget::item:hover {{
    background-color: #F5F7FA;
}}
#fluentAnnotationWindow QListWidget::item:selected,
#fluentAnnotationWindow QTreeView::item:selected,
#fluentAnnotationWindow QTableView::item:selected {{
    background-color: #DDEBFF;
    color: #1F1F1F;
}}
#fluentAnnotationWindow QLineEdit,
#fluentAnnotationWindow QTextEdit,
#fluentAnnotationWindow QPlainTextEdit,
#fluentAnnotationWindow QComboBox,
#fluentAnnotationWindow QSpinBox,
#fluentAnnotationWindow QDoubleSpinBox {{
    background-color: #FFFFFF;
    border: 1px solid #D0D0D0;
    border-radius: 4px;
    color: #1F1F1F;
}}
#fluentAnnotationWindow QLineEdit:focus,
#fluentAnnotationWindow QTextEdit:focus,
#fluentAnnotationWindow QPlainTextEdit:focus,
#fluentAnnotationWindow QComboBox:focus,
#fluentAnnotationWindow QSpinBox:focus,
#fluentAnnotationWindow QDoubleSpinBox:focus {{
    border-color: {accent};
}}
#fluentAnnotationWindow QCheckBox::indicator,
#fluentAnnotationWindow QRadioButton::indicator {{
    background-color: #FFFFFF;
    border: 1px solid #8A8A8A;
    border-radius: 3px;
}}
#fluentAnnotationWindow QCheckBox::indicator:checked,
#fluentAnnotationWindow QRadioButton::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}
#fluentAnnotationWindow QStatusBar {{
    background-color: #F7F7F9;
    color: #1F1F1F;
}}
#fluentAnnotationWindow QToolTip {{
    background-color: #FFFFFF;
    color: #1F1F1F;
    border: 1px solid #E3E3E3;
}}
"""
    )


def _apply_fluent_style(widget):
    _apply_fluent_palette(widget)
    _apply_fluent_stylesheet(widget)


def _patch_string_bundle(label_string_bundle):
    def _create_lookup_fallback_list(self, locale_str):
        result_paths = []
        base_path = STRINGS_DIR / "strings"
        result_paths.append(str(base_path))
        if locale_str is not None:
            tags = re.split("[^a-zA-Z]", locale_str)
            for tag in tags:
                last_path = result_paths[-1]
                result_paths.append(last_path + "-" + tag)
        return result_paths

    def _load_bundle(self, path):
        filename = f"{path}.properties"
        if not os.path.exists(filename):
            return
        with open(filename, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                key_value = line.split("=")
                key = key_value[0].strip()
                value = "=".join(key_value[1:]).strip().strip('"')
                self.id_to_message[key] = value

    label_string_bundle.StringBundle._StringBundle__create_lookup_fallback_list = _create_lookup_fallback_list
    label_string_bundle.StringBundle._StringBundle__load_bundle = _load_bundle


def _patch_utils(label_utils):
    label_utils.new_icon = _new_icon


def _apply_labelimg_patches():
    _ensure_labelimg_path()
    _ensure_resources_stub()

    from libs import stringBundle as label_string_bundle
    from libs import utils as label_utils

    if "libs" in sys.modules and "libs.resources" in sys.modules:
        setattr(sys.modules["libs"], "resources", sys.modules["libs.resources"])

    _patch_string_bundle(label_string_bundle)
    _patch_utils(label_utils)


_apply_labelimg_patches()

import labelImg as labelimg_module

labelimg_module.__appname__ = "FluentLabel"


FLUENT_PREDEFINED_DIALOG_STYLE = """
PredefinedLabelsDialog {
    background-color: #FCFCFC;
    border: 1px solid #E5E5E5;
    border-radius: 8px;
}
PredefinedLabelsDialog QLabel#titleLabel {
    font-size: 18px;
    font-weight: 600;
    color: #1A1A1A;
    padding: 4px 0;
}
PredefinedLabelsDialog QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}
PredefinedLabelsDialog QListWidget::item {
    padding: 10px 12px;
    border-radius: 4px;
    color: #1A1A1A;
    margin: 2px 4px;
}
PredefinedLabelsDialog QListWidget::item:hover {
    background-color: #F5F5F5;
}
PredefinedLabelsDialog QListWidget::item:selected {
    background-color: #E5F1FB;
    color: #1A1A1A;
}
PredefinedLabelsDialog QListWidget::item:selected:hover {
    background-color: #CCE4F7;
}
PredefinedLabelsDialog QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #D1D1D1;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 13px;
    color: #1A1A1A;
    min-width: 70px;
}
PredefinedLabelsDialog QPushButton:hover {
    background-color: #F5F5F5;
    border-color: #C1C1C1;
}
PredefinedLabelsDialog QPushButton:pressed {
    background-color: #E5E5E5;
    border-color: #A0A0A0;
}
PredefinedLabelsDialog QPushButton#primaryBtn {
    background-color: #0078D4;
    border: 1px solid #0067B8;
    color: #FFFFFF;
}
PredefinedLabelsDialog QPushButton#primaryBtn:hover {
    background-color: #1084D9;
    border-color: #0078D4;
}
PredefinedLabelsDialog QPushButton#primaryBtn:pressed {
    background-color: #006CBD;
    border-color: #005A9E;
}
PredefinedLabelsDialog QPushButton#dangerBtn {
    color: #C42B1C;
    border-color: #C42B1C;
}
PredefinedLabelsDialog QPushButton#dangerBtn:hover {
    background-color: #FDF3F2;
    border-color: #C42B1C;
}
PredefinedLabelsDialog QPushButton#dangerBtn:pressed {
    background-color: #FCE4E1;
}
"""


class PredefinedLabelsDialog(QDialog):
    """预设标签编辑对话框"""

    def __init__(self, parent, labels, classes_file):
        super().__init__(parent)
        self.setWindowTitle("编辑预设标签")
        self.setMinimumSize(360, 450)
        self._labels = labels.copy()
        self._classes_file = classes_file
        self._setup_ui()

    def _setup_ui(self):
        # 应用Fluent样式
        self.setStyleSheet(FLUENT_PREDEFINED_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 标题
        from PyQt5.QtWidgets import QLabel
        title_label = QLabel("编辑预设标签")
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)

        # 标签列表
        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.InternalMove)
        self._list.itemDoubleClicked.connect(self._edit_item)
        self._refresh_list()
        layout.addWidget(self._list)

        # 按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_label)
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self._edit_selected)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.clicked.connect(self._delete_label)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 分隔线
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #E5E5E5;")
        layout.addWidget(separator)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)
        bottom_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save_and_close)
        bottom_layout.addWidget(save_btn)

        layout.addLayout(bottom_layout)

    def _refresh_list(self):
        self._list.clear()
        for label in self._labels:
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self._list.addItem(item)

    def _add_label(self):
        text, ok = QInputDialog.getText(self, "添加标签", "请输入新标签名称:")
        if ok and text.strip():
            label = text.strip()
            if label not in self._labels:
                self._labels.append(label)
                self._refresh_list()
            else:
                QMessageBox.warning(self, "提示", f"标签 '{label}' 已存在")

    def _edit_item(self, item):
        old_label = item.text()
        text, ok = QInputDialog.getText(self, "编辑标签", "请输入新标签名称:", text=old_label)
        if ok and text.strip():
            new_label = text.strip()
            if new_label != old_label:
                if new_label in self._labels:
                    QMessageBox.warning(self, "提示", f"标签 '{new_label}' 已存在")
                    return
                idx = self._labels.index(old_label)
                self._labels[idx] = new_label
                self._refresh_list()

    def _edit_selected(self):
        item = self._list.currentItem()
        if item:
            self._edit_item(item)
        else:
            QMessageBox.information(self, "提示", "请先选择一个标签")

    def _delete_label(self):
        item = self._list.currentItem()
        if item:
            label = item.text()
            reply = QMessageBox.question(
                self, "确认删除", f"确定要删除标签 '{label}' 吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._labels.remove(label)
                self._refresh_list()
        else:
            QMessageBox.information(self, "提示", "请先选择一个标签")

    def _save_and_close(self):
        # 从列表中更新顺序（支持拖拽排序）
        new_labels = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            label = item.text().strip()
            if label and label not in new_labels:
                new_labels.append(label)
        self._labels = new_labels

        try:
            with open(self._classes_file, "w", encoding="utf-8") as f:
                for label in self._labels:
                    f.write(f"{label}\n")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def get_labels(self):
        return self._labels


class AnnotationWindow(labelimg_module.MainWindow):
    def __init__(
        self,
        default_filename=None,
        default_prefdef_class_file=None,
        default_save_dir=None,
        parent=None,
    ):
        if default_prefdef_class_file is None:
            default_prefdef_class_file = str(LABELIMG_ROOT / "data" / "predefined_classes.txt")

        self._predefined_classes_file = default_prefdef_class_file

        super().__init__(default_filename, default_prefdef_class_file, default_save_dir)

        if parent is not None:
            self.setParent(parent)
            self.setWindowFlags(Qt.Widget)

        _apply_fluent_style(self)
        self._setup_dock_title_bars()
        self._setup_edit_labels_menu()

    def _setup_dock_title_bars(self):
        """自定义右侧 Dock 标题栏，避免文字裁切"""
        if hasattr(self, "dock"):
            self._apply_dock_title_bar(self.dock, show_float=False)
        if hasattr(self, "file_dock"):
            self._apply_dock_title_bar(self.file_dock, show_float=True)

    def _apply_dock_title_bar(self, dock, show_float=False):
        title_bar = QWidget(dock)
        title_bar.setObjectName("dockTitleBar")
        title_bar.setAttribute(Qt.WA_StyledBackground, True)
        title_bar.setMinimumHeight(32)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(6)

        title_label = QLabel(dock.windowTitle(), title_bar)
        title_label.setObjectName("dockTitleLabel")
        title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        layout.addWidget(title_label)
        layout.addStretch()

        if show_float and (dock.features() & QDockWidget.DockWidgetFloatable):
            float_btn = QToolButton(title_bar)
            float_btn.setObjectName("dockTitleButton")
            float_btn.setAutoRaise(True)
            float_btn.setToolTip("浮动/停靠")
            float_btn.clicked.connect(lambda: dock.setFloating(not dock.isFloating()))
            layout.addWidget(float_btn)

            dock.topLevelChanged.connect(
                lambda floating, btn=float_btn, d=dock: self._update_dock_float_icon(btn, d, floating)
            )
            self._update_dock_float_icon(float_btn, dock, dock.isFloating())

        dock.setTitleBarWidget(title_bar)

    def _update_dock_float_icon(self, button, dock, floating):
        icon = dock.style().standardIcon(
            QStyle.SP_TitleBarNormalButton if floating else QStyle.SP_TitleBarMaxButton
        )
        button.setIcon(icon)

    def _setup_edit_labels_menu(self):
        """在编辑菜单中添加预设标签编辑项"""
        edit_labels_action = QAction(_new_icon("labels"), "编辑预设标签...", self)
        edit_labels_action.triggered.connect(self._open_predefined_labels_dialog)

        # 在编辑菜单中添加分隔符和菜单项
        if hasattr(self, "menus") and hasattr(self.menus, "edit"):
            self.menus.edit.addSeparator()
            self.menus.edit.addAction(edit_labels_action)

    def _open_predefined_labels_dialog(self):
        """打开预设标签编辑对话框"""
        dialog = PredefinedLabelsDialog(self, self.label_hist, self._predefined_classes_file)
        if dialog.exec_() == QDialog.Accepted:
            self.label_hist = dialog.get_labels()
            self._sync_label_ui()

    def _sync_label_ui(self):
        """同步更新界面上的标签相关组件"""
        # 更新默认标签下拉框 (DefaultLabelComboBox 内部使用 cb 属性存储 QComboBox)
        if hasattr(self, "default_label_combo_box") and hasattr(self.default_label_combo_box, "cb"):
            # 阻止信号触发，避免 clear 时 index 越界
            self.default_label_combo_box.cb.blockSignals(True)
            self.default_label_combo_box.cb.clear()
            self.default_label_combo_box.cb.addItems(self.label_hist)
            self.default_label_combo_box.items = self.label_hist
            self.default_label_combo_box.cb.blockSignals(False)
            if self.label_hist:
                self.default_label = self.label_hist[0]

        # 更新标签对话框
        if hasattr(self, "label_dialog"):
            from libs.labelDialog import LabelDialog
            self.label_dialog = LabelDialog(parent=self, list_item=self.label_hist)
