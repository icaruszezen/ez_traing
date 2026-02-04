"""
数据集管理页面
功能：项目管理、导入、目录扫描、数据预览、标注联动
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QImage
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFileDialog,
    QSplitter,
    QFrame,
    QAbstractItemView,
    QInputDialog,
    QMessageBox,
)
from qfluentwidgets import (
    PushButton,
    PrimaryPushButton,
    TransparentPushButton,
    CardWidget,
    BodyLabel,
    SubtitleLabel,
    TitleLabel,
    CaptionLabel,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    ProgressBar,
)

# 支持的图片格式
SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff", ".tif"}

# 项目配置文件路径
def _get_config_dir() -> Path:
    """获取配置目录"""
    config_dir = Path.home() / ".ez_traing"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def _get_projects_file() -> Path:
    """获取项目配置文件路径"""
    return _get_config_dir() / "datasets.json"


@dataclass
class DatasetProject:
    """数据集项目"""
    id: str
    name: str
    directory: str
    image_count: int = 0
    annotated_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    
    @classmethod
    def create(cls, name: str, directory: str) -> "DatasetProject":
        """创建新项目"""
        now = datetime.now().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            directory=directory,
            created_at=now,
            updated_at=now,
        )


class ProjectManager:
    """项目管理器"""
    
    def __init__(self):
        self.projects: Dict[str, DatasetProject] = {}
        self._load()
    
    def _load(self):
        """加载项目配置"""
        config_file = _get_projects_file()
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("projects", []):
                        proj = DatasetProject(**item)
                        self.projects[proj.id] = proj
            except Exception:
                pass
    
    def _save(self):
        """保存项目配置"""
        config_file = _get_projects_file()
        data = {
            "projects": [asdict(p) for p in self.projects.values()]
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_project(self, project: DatasetProject):
        """添加项目"""
        self.projects[project.id] = project
        self._save()
    
    def remove_project(self, project_id: str):
        """删除项目"""
        if project_id in self.projects:
            del self.projects[project_id]
            self._save()
    
    def update_project(self, project: DatasetProject):
        """更新项目"""
        project.updated_at = datetime.now().isoformat()
        self.projects[project.id] = project
        self._save()
    
    def get_project(self, project_id: str) -> Optional[DatasetProject]:
        """获取项目"""
        return self.projects.get(project_id)
    
    def get_all_projects(self) -> List[DatasetProject]:
        """获取所有项目"""
        return list(self.projects.values())


class ImageScanner(QThread):
    """异步图片扫描线程"""
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list, int)  # image_paths, annotated_count
    
    def __init__(self, directory: str):
        super().__init__()
        self.directory = directory
        self._is_cancelled = False
    
    def run(self):
        image_paths = []
        all_files = []
        annotated_count = 0
        
        # 收集所有文件
        for root, _, files in os.walk(self.directory):
            for file in files:
                if Path(file).suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                    all_files.append(os.path.join(root, file))
        
        total = len(all_files)
        for i, file_path in enumerate(all_files):
            if self._is_cancelled:
                break
            image_paths.append(file_path)
            
            # 检查是否有标注
            path = Path(file_path)
            if path.with_suffix(".txt").exists() or path.with_suffix(".xml").exists():
                annotated_count += 1
            
            self.progress.emit(i + 1, total)
        
        self.finished.emit(image_paths, annotated_count)
    
    def cancel(self):
        self._is_cancelled = True


class ThumbnailLoader(QThread):
    """异步缩略图加载线程 - 使用 QImage 避免线程安全问题"""
    thumbnail_loaded = pyqtSignal(str, QImage)  # path, image (QImage 可跨线程)
    all_loaded = pyqtSignal()
    
    def __init__(self, image_paths: List[str], thumbnail_size: int = 120):
        super().__init__()
        self.image_paths = image_paths
        self.thumbnail_size = thumbnail_size
        self._is_cancelled = False
    
    def run(self):
        for path in self.image_paths:
            if self._is_cancelled:
                break
            try:
                # 使用 QImage 而非 QPixmap（QImage 是线程安全的）
                image = QImage(path)
                if not image.isNull():
                    scaled = image.scaled(
                        self.thumbnail_size, 
                        self.thumbnail_size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.thumbnail_loaded.emit(path, scaled)
            except Exception:
                pass
        self.all_loaded.emit()
    
    def cancel(self):
        self._is_cancelled = True


class ProjectListWidget(CardWidget):
    """项目列表组件"""
    
    project_selected = pyqtSignal(str)  # project_id
    project_deleted = pyqtSignal(str)   # project_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.setMaximumWidth(320)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # 标题
        title_label = SubtitleLabel("数据集项目")
        layout.addWidget(title_label)
        
        # 项目列表
        self.project_list = QListWidget()
        self.project_list.setStyleSheet("""
            QListWidget {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                outline: none;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #eeeeee;
            }
            QListWidget::item:last-child {
                border-bottom: none;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        self.project_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.project_list, 1)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.add_btn = PrimaryPushButton("新建项目", self, FIF.ADD)
        self.add_btn.setFixedHeight(36)
        btn_layout.addWidget(self.add_btn)
        
        self.delete_btn = TransparentPushButton("删除", self, FIF.DELETE)
        self.delete_btn.setFixedHeight(36)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(btn_layout)
    
    def add_project_item(self, project: DatasetProject, select: bool = False):
        """添加项目项"""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, project.id)
        
        # 格式化显示文本
        text = f"{project.name}\n"
        text += f"📁 {project.directory}\n"
        text += f"🖼 {project.image_count} 张图片 · ✅ {project.annotated_count} 已标注"
        item.setText(text)
        item.setSizeHint(QSize(0, 80))
        
        self.project_list.addItem(item)
        
        if select:
            self.project_list.setCurrentItem(item)
            self.delete_btn.setEnabled(True)
    
    def update_project_item(self, project: DatasetProject):
        """更新项目项"""
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            if item.data(Qt.UserRole) == project.id:
                text = f"{project.name}\n"
                text += f"📁 {project.directory}\n"
                text += f"🖼 {project.image_count} 张图片 · ✅ {project.annotated_count} 已标注"
                item.setText(text)
                break
    
    def remove_project_item(self, project_id: str):
        """移除项目项"""
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            if item.data(Qt.UserRole) == project_id:
                self.project_list.takeItem(i)
                break
        
        if self.project_list.count() == 0:
            self.delete_btn.setEnabled(False)
    
    def clear_projects(self):
        """清空项目列表"""
        self.project_list.clear()
        self.delete_btn.setEnabled(False)
    
    def get_selected_project_id(self) -> Optional[str]:
        """获取选中的项目ID"""
        items = self.project_list.selectedItems()
        if items:
            return items[0].data(Qt.UserRole)
        return None
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """项目点击"""
        project_id = item.data(Qt.UserRole)
        self.delete_btn.setEnabled(True)
        self.project_selected.emit(project_id)


class ImagePreviewWidget(QFrame):
    """图片预览组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMinimumWidth(280)
        self._setup_ui()
        self._current_path: Optional[str] = None
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题
        self.title_label = SubtitleLabel("图片预览")
        layout.addWidget(self.title_label)
        
        # 图片预览区域
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(200, 200)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        self.preview_label.setText("选择图片以预览")
        layout.addWidget(self.preview_label, 1)
        
        # 图片信息
        info_card = CardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(6)
        
        self.file_name_label = BodyLabel("文件名: -")
        self.file_size_label = CaptionLabel("大小: -")
        self.image_size_label = CaptionLabel("尺寸: -")
        self.annotation_status_label = CaptionLabel("标注: -")
        
        info_layout.addWidget(self.file_name_label)
        info_layout.addWidget(self.file_size_label)
        info_layout.addWidget(self.image_size_label)
        info_layout.addWidget(self.annotation_status_label)
        
        layout.addWidget(info_card)
    
    def set_image(self, image_path: str):
        """设置预览图片"""
        self._current_path = image_path
        
        if not image_path or not os.path.exists(image_path):
            self.preview_label.setText("选择图片以预览")
            self._clear_info()
            return
        
        # 加载图片
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.preview_label.setText("无法加载图片")
            self._clear_info()
            return
        
        # 缩放显示
        preview_size = self.preview_label.size()
        scaled = pixmap.scaled(
            preview_size.width() - 20,
            preview_size.height() - 20,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        
        # 更新信息
        file_path = Path(image_path)
        file_stat = file_path.stat()
        
        self.file_name_label.setText(f"文件名: {file_path.name}")
        self.file_size_label.setText(f"大小: {self._format_size(file_stat.st_size)}")
        self.image_size_label.setText(f"尺寸: {pixmap.width()} × {pixmap.height()}")
        
        # 检查标注状态
        annotation_status = self._check_annotation_status(image_path)
        self.annotation_status_label.setText(f"标注: {annotation_status}")
    
    def _clear_info(self):
        self.file_name_label.setText("文件名: -")
        self.file_size_label.setText("大小: -")
        self.image_size_label.setText("尺寸: -")
        self.annotation_status_label.setText("标注: -")
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _check_annotation_status(self, image_path: str) -> str:
        """检查图片的标注状态"""
        path = Path(image_path)
        
        # 检查 YOLO 格式标注 (.txt)
        txt_path = path.with_suffix(".txt")
        if txt_path.exists():
            with open(txt_path, "r") as f:
                lines = [l for l in f.readlines() if l.strip()]
                if lines:
                    return f"已标注 (YOLO, {len(lines)} 个对象)"
        
        # 检查 VOC 格式标注 (.xml)
        xml_path = path.with_suffix(".xml")
        if xml_path.exists():
            return "已标注 (VOC)"
        
        return "未标注"
    
    @property
    def current_path(self) -> Optional[str]:
        return self._current_path


class ImageListPanel(CardWidget):
    """图片列表面板"""
    
    image_selected = pyqtSignal(str)  # image_path
    image_double_clicked = pyqtSignal(str)  # image_path
    
    BATCH_SIZE = 50  # 每批添加的图片数量
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._thumbnail_cache = {}
        self._path_to_item = {}  # 路径到 item 的映射，加速查找
        self._pending_paths = []  # 待添加的路径
        self._placeholder_pixmap = None
        self._add_timer = QTimer(self)
        self._add_timer.timeout.connect(self._add_batch)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 标题和统计
        header_layout = QHBoxLayout()
        self.title_label = SubtitleLabel("图片列表")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self.count_label = CaptionLabel("共 0 张图片")
        header_layout.addWidget(self.count_label)
        layout.addLayout(header_layout)
        
        # 图片列表
        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(120, 120))
        self.image_list.setSpacing(10)
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.image_list.setMovement(QListWidget.Static)
        self.image_list.setUniformItemSizes(True)  # 优化：统一项目大小
        self.image_list.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                border: 2px solid #2196f3;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        self.image_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.image_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.image_list, 1)
    
    def set_images(self, image_paths: List[str]):
        """设置图片列表 - 分批添加避免卡顿"""
        self._add_timer.stop()
        self.image_list.clear()
        self._thumbnail_cache.clear()
        self._path_to_item.clear()
        
        count = len(image_paths)
        self.count_label.setText(f"共 {count} 张图片")
        
        if count == 0:
            return
        
        # 准备占位图
        if self._placeholder_pixmap is None:
            self._placeholder_pixmap = self._create_placeholder_pixmap()
        
        # 分批添加
        self._pending_paths = list(image_paths)
        self._add_timer.start(10)  # 每 10ms 添加一批
    
    def _add_batch(self):
        """添加一批图片项"""
        if not self._pending_paths:
            self._add_timer.stop()
            return
        
        # 取出一批
        batch = self._pending_paths[:self.BATCH_SIZE]
        self._pending_paths = self._pending_paths[self.BATCH_SIZE:]
        
        # 批量添加
        for path in batch:
            item = QListWidgetItem()
            item.setIcon(QIcon(self._placeholder_pixmap))
            item.setText(Path(path).name)
            item.setData(Qt.UserRole, path)
            item.setSizeHint(QSize(140, 160))
            self.image_list.addItem(item)
            self._path_to_item[path] = item
        
        # 如果添加完成，停止定时器
        if not self._pending_paths:
            self._add_timer.stop()
    
    def update_thumbnail(self, path: str, pixmap: QPixmap):
        """更新缩略图 - 使用字典快速查找"""
        self._thumbnail_cache[path] = pixmap
        
        item = self._path_to_item.get(path)
        if item:
            item.setIcon(QIcon(pixmap))
    
    def clear(self):
        """清空列表"""
        self._add_timer.stop()
        self._pending_paths.clear()
        self.image_list.clear()
        self._thumbnail_cache.clear()
        self._path_to_item.clear()
        self.count_label.setText("共 0 张图片")
    
    def _create_placeholder_pixmap(self) -> QPixmap:
        """创建占位图"""
        pixmap = QPixmap(120, 120)
        pixmap.fill(Qt.lightGray)
        return pixmap
    
    def _on_selection_changed(self):
        """选择变化"""
        items = self.image_list.selectedItems()
        if items:
            path = items[0].data(Qt.UserRole)
            self.image_selected.emit(path)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击项目"""
        path = item.data(Qt.UserRole)
        if path:
            self.image_double_clicked.emit(path)
    
    def get_selected_path(self) -> Optional[str]:
        """获取选中的图片路径"""
        items = self.image_list.selectedItems()
        if items:
            return items[0].data(Qt.UserRole)
        return None


class DatasetPage(QWidget):
    """数据集管理页面"""
    
    # 信号：请求打开图片进行标注
    request_annotation = pyqtSignal(str)  # image_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_manager = ProjectManager()
        self.current_project: Optional[DatasetProject] = None
        self.image_paths: List[str] = []
        self._scanner: Optional[ImageScanner] = None
        self._thumbnail_loader: Optional[ThumbnailLoader] = None
        
        self._setup_ui()
        self._load_projects()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # 顶部标题和操作栏
        header = self._create_header()
        main_layout.addWidget(header)
        
        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 主内容区域
        content_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：项目列表
        self.project_list_widget = ProjectListWidget()
        self.project_list_widget.project_selected.connect(self._on_project_selected)
        self.project_list_widget.add_btn.clicked.connect(self._on_add_project)
        self.project_list_widget.delete_btn.clicked.connect(self._on_delete_project)
        content_splitter.addWidget(self.project_list_widget)
        
        # 中间：图片列表
        self.image_list_panel = ImageListPanel()
        self.image_list_panel.image_selected.connect(self._on_image_selected)
        self.image_list_panel.image_double_clicked.connect(self._on_image_double_clicked)
        content_splitter.addWidget(self.image_list_panel)
        
        # 右侧：预览区域
        self.preview_widget = ImagePreviewWidget()
        content_splitter.addWidget(self.preview_widget)
        
        # 设置分割比例
        content_splitter.setSizes([280, 500, 320])
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 2)
        content_splitter.setStretchFactor(2, 1)
        
        main_layout.addWidget(content_splitter, 1)
        
        # 底部状态栏
        self.status_label = CaptionLabel("选择或创建数据集项目")
        main_layout.addWidget(self.status_label)
    
    def _create_header(self) -> QWidget:
        """创建顶部标题栏"""
        header = CardWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # 标题
        title = TitleLabel("数据集管理")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = PushButton("刷新", self, FIF.SYNC)
        self.refresh_btn.clicked.connect(self._on_refresh_project)
        self.refresh_btn.setEnabled(False)
        layout.addWidget(self.refresh_btn)
        
        # 打开标注按钮
        self.annotate_btn = PrimaryPushButton("打开标注", self, FIF.EDIT)
        self.annotate_btn.setEnabled(False)
        self.annotate_btn.clicked.connect(self._on_annotate_clicked)
        layout.addWidget(self.annotate_btn)
        
        return header
    
    def _load_projects(self):
        """加载所有项目"""
        self.project_list_widget.clear_projects()
        projects = self.project_manager.get_all_projects()
        for project in projects:
            self.project_list_widget.add_project_item(project)
    
    def _on_add_project(self):
        """添加新项目"""
        # 选择目录
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择数据集目录",
            "",
            QFileDialog.ShowDirsOnly
        )
        if not directory:
            return
        
        # 输入项目名称
        default_name = Path(directory).name
        name, ok = QInputDialog.getText(
            self,
            "新建数据集项目",
            "项目名称:",
            text=default_name
        )
        if not ok or not name.strip():
            return
        
        # 创建项目
        project = DatasetProject.create(name.strip(), directory)
        self.project_manager.add_project(project)
        self.project_list_widget.add_project_item(project, select=True)
        
        # 自动扫描
        self._load_project(project)
        
        InfoBar.success(
            title="成功",
            content=f"已创建项目: {name}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def _on_delete_project(self):
        """删除项目"""
        project_id = self.project_list_widget.get_selected_project_id()
        if not project_id:
            return
        
        project = self.project_manager.get_project(project_id)
        if not project:
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除项目 \"{project.name}\" 吗？\n\n（只删除项目记录，不会删除实际文件）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.project_manager.remove_project(project_id)
            self.project_list_widget.remove_project_item(project_id)
            
            if self.current_project and self.current_project.id == project_id:
                self.current_project = None
                self.image_paths.clear()
                self.image_list_panel.clear()
                self.preview_widget.set_image(None)
                self.refresh_btn.setEnabled(False)
                self.annotate_btn.setEnabled(False)
                self.status_label.setText("选择或创建数据集项目")
            
            InfoBar.success(
                title="成功",
                content=f"已删除项目: {project.name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def _on_project_selected(self, project_id: str):
        """项目选择"""
        project = self.project_manager.get_project(project_id)
        if project:
            self._load_project(project)
    
    def _on_refresh_project(self):
        """刷新当前项目"""
        if self.current_project:
            self._load_project(self.current_project)
    
    def _load_project(self, project: DatasetProject):
        """加载项目"""
        # 取消之前的任务
        if self._scanner and self._scanner.isRunning():
            self._scanner.cancel()
            self._scanner.wait()
        
        if self._thumbnail_loader and self._thumbnail_loader.isRunning():
            self._thumbnail_loader.cancel()
            self._thumbnail_loader.wait()
        
        self.current_project = project
        self.image_paths.clear()
        self.image_list_panel.clear()
        self.preview_widget.set_image(None)
        
        # 检查目录是否存在
        if not os.path.isdir(project.directory):
            InfoBar.error(
                title="错误",
                content=f"目录不存在: {project.directory}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            self.status_label.setText("目录不存在")
            return
        
        # 更新UI状态
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"正在扫描: {project.name}...")
        
        # 启动扫描
        self._scanner = ImageScanner(project.directory)
        self._scanner.progress.connect(self._on_scan_progress)
        self._scanner.finished.connect(self._on_scan_finished)
        self._scanner.start()
    
    def _on_scan_progress(self, current: int, total: int):
        """扫描进度"""
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))
        self.status_label.setText(f"正在扫描: {current}/{total}")
    
    def _on_scan_finished(self, image_paths: List[str], annotated_count: int):
        """扫描完成"""
        self.image_paths = sorted(image_paths)
        count = len(self.image_paths)
        
        # 更新项目信息
        if self.current_project:
            self.current_project.image_count = count
            self.current_project.annotated_count = annotated_count
            self.project_manager.update_project(self.current_project)
            self.project_list_widget.update_project_item(self.current_project)
        
        if count == 0:
            self.progress_bar.setVisible(False)
            self.status_label.setText("未找到图片文件")
            self.annotate_btn.setEnabled(False)
            InfoBar.info(
                title="提示",
                content="该目录下未找到支持的图片文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # 更新图片列表
        self.image_list_panel.set_images(self.image_paths)
        self.status_label.setText(f"扫描完成，共 {count} 张图片，正在加载缩略图...")
        
        # 启动缩略图加载
        self._thumbnail_loader = ThumbnailLoader(self.image_paths)
        self._thumbnail_loader.thumbnail_loaded.connect(self._on_thumbnail_loaded)
        self._thumbnail_loader.all_loaded.connect(self._on_thumbnails_all_loaded)
        self._thumbnail_loader.start()
    
    def _on_thumbnail_loaded(self, path: str, image: QImage):
        """缩略图加载 - 在主线程中将 QImage 转换为 QPixmap"""
        pixmap = QPixmap.fromImage(image)
        self.image_list_panel.update_thumbnail(path, pixmap)
        
        # 更新进度
        loaded = len(self.image_list_panel._thumbnail_cache)
        total = len(self.image_paths)
        if total > 0:
            self.progress_bar.setValue(int(loaded / total * 100))
    
    def _on_thumbnails_all_loaded(self):
        """所有缩略图加载完成"""
        self.progress_bar.setVisible(False)
        project_name = self.current_project.name if self.current_project else ""
        self.status_label.setText(f"{project_name}: 已加载 {len(self.image_paths)} 张图片")
        
        InfoBar.success(
            title="完成",
            content=f"成功加载 {len(self.image_paths)} 张图片",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def _on_image_selected(self, image_path: str):
        """图片选择"""
        self.preview_widget.set_image(image_path)
        self.annotate_btn.setEnabled(True)
    
    def _on_image_double_clicked(self, image_path: str):
        """图片双击"""
        self._open_for_annotation(image_path)
    
    def _on_annotate_clicked(self):
        """打开标注"""
        path = self.image_list_panel.get_selected_path()
        if path:
            self._open_for_annotation(path)
    
    def _open_for_annotation(self, image_path: str):
        """打开图片进行标注"""
        if os.path.exists(image_path):
            self.request_annotation.emit(image_path)
        else:
            InfoBar.error(
                title="错误",
                content="图片文件不存在",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def get_selected_image_path(self) -> Optional[str]:
        """获取当前选中的图片路径"""
        return self.image_list_panel.get_selected_path()
    
    def get_all_image_paths(self) -> List[str]:
        """获取所有图片路径"""
        return self.image_paths.copy()
    
    def get_current_project(self) -> Optional[DatasetProject]:
        """获取当前项目"""
        return self.current_project
