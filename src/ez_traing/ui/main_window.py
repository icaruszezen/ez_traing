from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, NavigationItemPosition

from ez_traing.pages.annotation_page import AnnotationPage
from ez_traing.pages.placeholder_page import PlaceholderPage


class AppWindow(FluentWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FluentLabel")
        self.resize(1280, 800)

        self.annotation_page = AnnotationPage(self)
        self.dataset_page = PlaceholderPage("数据集管理", "页面预留，后续开发。", self)
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
