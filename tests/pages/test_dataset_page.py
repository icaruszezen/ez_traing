import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from ez_training.pages.dataset_page import (
    ImageInfo,
    ImageListPanel,
    ImageScanner,
    _matches_image_filters,
)


app = QApplication.instance() or QApplication(sys.argv or ["test"])


def test_image_scanner_collects_unique_labels_per_image(tmp_path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "classes.txt").write_text("enemy\nally\n", encoding="utf-8")
    (dataset_dir / "sample.jpg").write_bytes(b"")
    (dataset_dir / "sample.txt").write_text(
        "0 0.5 0.5 0.1 0.1\n"
        "1 0.5 0.5 0.1 0.1\n"
        "0 0.6 0.6 0.1 0.1\n",
        encoding="utf-8",
    )

    received = {}
    scanner = ImageScanner(str(dataset_dir), recursive=False)
    scanner.finished.connect(lambda infos, stats: received.update(infos=infos, stats=stats))

    scanner.run()

    assert len(received["infos"]) == 1
    info = received["infos"][0]
    assert info.path.endswith("sample.jpg")
    assert info.is_annotated is True
    assert info.labels == ["enemy", "ally"]
    assert received["stats"].label_counts == {"enemy": 2, "ally": 1}


def test_matches_image_filters_supports_label_selection():
    info = ImageInfo(
        path="/tmp/enemy.jpg",
        is_annotated=True,
        image_type="jpg",
        labels=["enemy", "boss"],
    )

    assert _matches_image_filters(info, "全部", "全部", "enemy") is True
    assert _matches_image_filters(info, "已标注", "jpg", "boss") is True
    assert _matches_image_filters(info, "未标注", "全部", "enemy") is False
    assert _matches_image_filters(info, "全部", "png", "enemy") is False
    assert _matches_image_filters(info, "全部", "全部", "ally") is False


def test_image_list_panel_adds_and_resets_label_filter_options():
    panel = ImageListPanel()

    panel.set_label_options(["ally", "enemy"])
    assert [panel.label_filter.itemText(i) for i in range(panel.label_filter.count())] == [
        "全部",
        "ally",
        "enemy",
    ]

    panel.label_filter.setCurrentText("enemy")
    panel.clear()

    assert panel.label_filter.count() == 1
    assert panel.label_filter.itemText(0) == "全部"
    assert panel.label_filter.currentText() == "全部"
