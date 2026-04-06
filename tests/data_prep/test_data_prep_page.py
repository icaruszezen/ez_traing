import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication

import ez_training.pages.data_prep_page as data_prep_page_module
from ez_training.data_prep.models import IMAGE_EXPORT_RULE_INCLUDE_IF_ANY_SELECTED
from ez_training.pages.data_prep_page import DataPrepPage


app = QApplication.instance() or QApplication(sys.argv or ["test"])


class DummyProjectManager:
    def __init__(self, dataset_dir):
        self.project = SimpleNamespace(
            id="project-1",
            name="Demo Dataset",
            image_count=3,
            directory=str(dataset_dir),
            is_archive_root=False,
            archive_id=None,
        )

    def get_all_projects(self, exclude_archived=True):
        del exclude_archived
        return [self.project]

    def get_project(self, project_id):
        return self.project if project_id == self.project.id else None

    def get_directories(self, project_id):
        return [self.project.directory] if project_id == self.project.id else []


@pytest.fixture
def isolated_config_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(data_prep_page_module, "get_config_dir", lambda: tmp_path)
    return tmp_path


def _write_classes(path, class_names):
    path.write_text("\n".join(class_names) + "\n", encoding="utf-8")


def _process_events():
    app.processEvents()


def test_classes_file_generates_checkbox_list_and_defaults_all_selected(
    isolated_config_dir, tmp_path
):
    del isolated_config_dir
    classes_path = tmp_path / "classes.txt"
    _write_classes(classes_path, ["cat", "dog", "bird"])

    page = DataPrepPage()
    page.custom_classes_cb.setChecked(True)
    page.custom_classes_edit.setText(str(classes_path))
    _process_events()

    assert list(page._custom_class_checkboxes) == ["cat", "dog", "bird"]
    assert page._selected_custom_classes() == ["cat", "dog", "bird"]
    assert not page.custom_classes_options_widget.isHidden()


def test_switching_classes_file_refreshes_checkbox_list(isolated_config_dir, tmp_path):
    del isolated_config_dir
    classes_a = tmp_path / "classes_a.txt"
    classes_b = tmp_path / "classes_b.txt"
    _write_classes(classes_a, ["cat", "dog"])
    _write_classes(classes_b, ["enemy", "ally", "boss"])

    page = DataPrepPage()
    page.custom_classes_cb.setChecked(True)
    page.custom_classes_edit.setText(str(classes_a))
    _process_events()
    assert list(page._custom_class_checkboxes) == ["cat", "dog"]

    page.custom_classes_edit.setText(str(classes_b))
    _process_events()
    assert list(page._custom_class_checkboxes) == ["enemy", "ally", "boss"]
    assert page._selected_custom_classes() == ["enemy", "ally", "boss"]


def test_start_is_blocked_when_no_custom_classes_are_selected(
    isolated_config_dir, tmp_path
):
    del isolated_config_dir
    classes_path = tmp_path / "classes.txt"
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    _write_classes(classes_path, ["cat", "dog"])

    page = DataPrepPage()
    page.set_project_manager(DummyProjectManager(dataset_dir))
    page._refresh_dataset_list()
    page.enable_aug_cb.setChecked(False)
    page.custom_classes_cb.setChecked(True)
    page.custom_classes_edit.setText(str(classes_path))
    _process_events()
    page._clear_custom_classes_selection()

    with patch.object(data_prep_page_module.InfoBar, "warning") as mock_warning:
        page._on_start_clicked()

    assert mock_warning.called
    assert "请至少选择一个需要导出的类别" in mock_warning.call_args.kwargs["content"]
    assert page._worker is None


def test_custom_class_selection_and_rule_persist_with_new_class_added(
    isolated_config_dir, tmp_path
):
    del isolated_config_dir
    classes_path = tmp_path / "classes.txt"
    _write_classes(classes_path, ["cat", "dog"])

    page = DataPrepPage()
    page.custom_classes_cb.setChecked(True)
    page.custom_classes_edit.setText(str(classes_path))
    _process_events()
    page._custom_class_checkboxes["dog"].setChecked(False)
    page._set_image_export_rule(IMAGE_EXPORT_RULE_INCLUDE_IF_ANY_SELECTED)
    page._do_save_ui_state()

    _write_classes(classes_path, ["cat", "dog", "bird"])

    restored_page = DataPrepPage()
    _process_events()

    assert restored_page.custom_classes_cb.isChecked() is True
    assert restored_page.custom_classes_edit.text() == str(classes_path)
    assert restored_page._selected_custom_classes() == ["cat", "bird"]
    assert (
        restored_page._get_image_export_rule()
        == IMAGE_EXPORT_RULE_INCLUDE_IF_ANY_SELECTED
    )
