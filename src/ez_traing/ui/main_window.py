import os

from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, NavigationItemPosition

from ez_traing.pages.annotation_page import AnnotationPage
from ez_traing.pages.dataset_page import DatasetPage
from ez_traing.pages.placeholder_page import PlaceholderPage


class AppWindow(FluentWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FluentLabel")
        self.resize(1280, 800)

        self.annotation_page = AnnotationPage(self)
        self.dataset_page = DatasetPage(self)
        self.train_page = PlaceholderPage("YOLO 训练", "页面预留，后续开发。", self)
        self.eval_page = PlaceholderPage("模型验证", "页面预留，后续开发。", self)

        self.annotation_page.setObjectName("annotation")
        self.dataset_page.setObjectName("dataset")
        self.train_page.setObjectName("train")
        self.eval_page.setObjectName("eval")

        self.addSubInterface(self.annotation_page, FIF.PHOTO, "标注")
        self.addSubInterface(self.dataset_page, FIF.FOLDER, "数据集")
        self.addSubInterface(self.train_page, FIF.ROBOT, "训练")
        self.addSubInterface(
            self.eval_page,
            FIF.COMPLETED,
            "验证",
            NavigationItemPosition.BOTTOM,
        )

        # 连接数据集页面的标注联动信号
        self.dataset_page.request_annotation.connect(self._on_request_annotation)

    def _annotation_window(self):
        return getattr(self.annotation_page, "annotation_window", None)

    @property
    def file_path(self):
        annotation_window = self._annotation_window()
        return annotation_window.file_path if annotation_window else None

    @property
    def label_coordinates(self):
        annotation_window = self._annotation_window()
        return getattr(annotation_window, "label_coordinates", None)

    def _on_request_annotation(self, image_path: str):
        """处理数据集页面的标注请求，跳转到标注页面并打开图片"""
        if not image_path or not os.path.exists(image_path):
            return

        # 切换到标注页面
        self.switchTo(self.annotation_page)

        # 打开图片进行标注
        annotation_window = self._annotation_window()
        if annotation_window:
            # 使用 labelImg 的 load_file 方法加载图片
            annotation_window.load_file(image_path)
