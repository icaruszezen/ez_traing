from pathlib import Path

import pytest
import yaml
from PIL import Image

from ez_training.common.voc_io import append_voc_object, create_voc_xml, save_voc_xml
from ez_training.data_prep.models import (
    IMAGE_EXPORT_RULE_EXCLUDE_IF_ANY_UNSELECTED,
    IMAGE_EXPORT_RULE_INCLUDE_IF_ANY_SELECTED,
    DataPrepConfig,
)
from ez_training.data_prep.pipeline import DataPrepPipeline


def _write_classes(path: Path, class_names):
    path.write_text("\n".join(class_names) + "\n", encoding="utf-8")


def _create_sample(dataset_dir: Path, stem: str, labels=None):
    image_path = dataset_dir / f"{stem}.jpg"
    Image.new("RGB", (100, 100), color=(255, 255, 255)).save(image_path)

    if labels is None:
        return image_path

    root = create_voc_xml(
        folder=dataset_dir.name,
        filename=image_path.name,
        path=str(image_path),
        width=100,
        height=100,
        depth=3,
    )
    for label, xmin, ymin, xmax, ymax in labels:
        append_voc_object(root, label, xmin, ymin, xmax, ymax, img_width=100, img_height=100)
    save_voc_xml(root, dataset_dir / f"{stem}.xml")
    return image_path


def _run_pipeline(
    tmp_path: Path,
    sample_defs,
    class_names,
    selected_classes,
    image_export_rule,
    *,
    skip_unlabeled=True,
):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    for stem, labels in sample_defs:
        _create_sample(dataset_dir, stem, labels)

    classes_path = tmp_path / "classes.txt"
    _write_classes(classes_path, class_names)

    output_dir = tmp_path / "output"
    config = DataPrepConfig(
        dataset_name="demo",
        dataset_dir=str(dataset_dir),
        output_dir=str(output_dir),
        train_ratio=0.5,
        random_seed=7,
        augment_methods=[],
        augment_times=0,
        skip_unlabeled=skip_unlabeled,
        overwrite_output=True,
        custom_classes_file=str(classes_path),
        selected_classes=list(selected_classes),
        image_export_rule=image_export_rule,
    )
    summary = DataPrepPipeline(config).run()
    return output_dir, summary


def _collect_label_texts(output_dir: Path):
    result = {}
    for path in sorted((output_dir / "labels").glob("*/*.txt")):
        result[path.stem] = path.read_text(encoding="utf-8")
    return result


def test_full_selection_keeps_all_custom_classes_and_order(tmp_path):
    output_dir, summary = _run_pipeline(
        tmp_path,
        sample_defs=[
            ("cat_one", [("cat", 10, 10, 40, 40)]),
            ("dog_one", [("dog", 20, 20, 60, 70)]),
        ],
        class_names=["cat", "dog"],
        selected_classes=["cat", "dog"],
        image_export_rule=IMAGE_EXPORT_RULE_EXCLUDE_IF_ANY_UNSELECTED,
    )

    exported = _collect_label_texts(output_dir)
    assert set(exported) == {"cat_one", "dog_one"}
    assert summary.processed_images == 2
    assert (output_dir / "classes.txt").read_text(encoding="utf-8").splitlines() == ["cat", "dog"]

    data_yaml = yaml.safe_load((output_dir / "data.yaml").read_text(encoding="utf-8"))
    assert data_yaml["names"] == {0: "cat", 1: "dog"}


def test_strict_rule_excludes_mixed_and_unselected_only_images(tmp_path):
    output_dir, summary = _run_pipeline(
        tmp_path,
        sample_defs=[
            ("cat_keep_a", [("cat", 10, 10, 30, 30)]),
            ("mixed_drop", [("cat", 10, 10, 30, 30), ("dog", 40, 40, 70, 70)]),
            ("dog_drop", [("dog", 10, 10, 30, 30)]),
            ("cat_keep_b", [("cat", 15, 15, 35, 35)]),
        ],
        class_names=["cat", "dog"],
        selected_classes=["cat"],
        image_export_rule=IMAGE_EXPORT_RULE_EXCLUDE_IF_ANY_UNSELECTED,
    )

    exported = _collect_label_texts(output_dir)
    assert set(exported) == {"cat_keep_a", "cat_keep_b"}
    assert summary.processed_images == 2
    assert all(text.strip().startswith("0 ") for text in exported.values())


def test_lenient_rule_keeps_mixed_image_and_drops_unselected_boxes(tmp_path):
    output_dir, summary = _run_pipeline(
        tmp_path,
        sample_defs=[
            ("cat_keep_a", [("cat", 10, 10, 30, 30)]),
            ("mixed_keep", [("cat", 10, 10, 30, 30), ("dog", 40, 40, 70, 70)]),
            ("dog_drop", [("dog", 10, 10, 30, 30)]),
            ("cat_keep_b", [("cat", 15, 15, 35, 35)]),
        ],
        class_names=["cat", "dog"],
        selected_classes=["cat"],
        image_export_rule=IMAGE_EXPORT_RULE_INCLUDE_IF_ANY_SELECTED,
    )

    exported = _collect_label_texts(output_dir)
    assert set(exported) == {"cat_keep_a", "mixed_keep", "cat_keep_b"}
    assert summary.processed_images == 3

    mixed_lines = exported["mixed_keep"].strip().splitlines()
    assert len(mixed_lines) == 1
    assert mixed_lines[0].startswith("0 ")


@pytest.mark.parametrize(
    "image_export_rule",
    [
        IMAGE_EXPORT_RULE_EXCLUDE_IF_ANY_UNSELECTED,
        IMAGE_EXPORT_RULE_INCLUDE_IF_ANY_SELECTED,
    ],
)
def test_unselected_only_images_are_excluded_in_both_rules(tmp_path, image_export_rule):
    output_dir, _ = _run_pipeline(
        tmp_path,
        sample_defs=[
            ("cat_keep_a", [("cat", 10, 10, 30, 30)]),
            ("dog_drop", [("dog", 10, 10, 30, 30)]),
            ("cat_keep_b", [("cat", 15, 15, 35, 35)]),
        ],
        class_names=["cat", "dog"],
        selected_classes=["cat"],
        image_export_rule=image_export_rule,
    )

    exported = _collect_label_texts(output_dir)
    assert "dog_drop" not in exported


def test_negative_samples_are_kept_when_skip_unlabeled_is_disabled(tmp_path):
    output_dir, summary = _run_pipeline(
        tmp_path,
        sample_defs=[
            ("cat_keep_a", [("cat", 10, 10, 30, 30)]),
            ("negative_keep", None),
            ("cat_keep_b", [("cat", 15, 15, 35, 35)]),
        ],
        class_names=["cat", "dog"],
        selected_classes=["cat"],
        image_export_rule=IMAGE_EXPORT_RULE_EXCLUDE_IF_ANY_UNSELECTED,
        skip_unlabeled=False,
    )

    exported = _collect_label_texts(output_dir)
    assert set(exported) == {"cat_keep_a", "negative_keep", "cat_keep_b"}
    assert exported["negative_keep"] == ""
    assert summary.processed_images == 3


def test_validate_rejects_empty_selected_classes(tmp_path):
    classes_path = tmp_path / "classes.txt"
    _write_classes(classes_path, ["cat", "dog"])

    config = DataPrepConfig(
        dataset_name="demo",
        dataset_dir=str(tmp_path / "dataset"),
        output_dir=str(tmp_path / "output"),
        custom_classes_file=str(classes_path),
        selected_classes=[],
    )

    with pytest.raises(ValueError, match="至少选择一个"):
        config.validate()


def test_pipeline_rejects_empty_custom_classes_file(tmp_path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    _create_sample(dataset_dir, "cat_keep_a", [("cat", 10, 10, 30, 30)])
    _create_sample(dataset_dir, "cat_keep_b", [("cat", 15, 15, 35, 35)])

    classes_path = tmp_path / "classes.txt"
    classes_path.write_text("", encoding="utf-8")

    config = DataPrepConfig(
        dataset_name="demo",
        dataset_dir=str(dataset_dir),
        output_dir=str(tmp_path / "output"),
        train_ratio=0.5,
        random_seed=7,
        augment_methods=[],
        augment_times=0,
        custom_classes_file=str(classes_path),
        selected_classes=["cat"],
    )

    with pytest.raises(ValueError, match="自定义类别文件为空"):
        DataPrepPipeline(config).run()


def test_pipeline_rejects_when_filter_removes_all_samples(tmp_path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    _create_sample(dataset_dir, "dog_drop_a", [("dog", 10, 10, 30, 30)])
    _create_sample(dataset_dir, "dog_drop_b", [("dog", 15, 15, 35, 35)])

    classes_path = tmp_path / "classes.txt"
    _write_classes(classes_path, ["cat", "dog"])

    config = DataPrepConfig(
        dataset_name="demo",
        dataset_dir=str(dataset_dir),
        output_dir=str(tmp_path / "output"),
        train_ratio=0.5,
        random_seed=7,
        augment_methods=[],
        augment_times=0,
        custom_classes_file=str(classes_path),
        selected_classes=["cat"],
        image_export_rule=IMAGE_EXPORT_RULE_EXCLUDE_IF_ANY_UNSELECTED,
    )

    with pytest.raises(ValueError, match="过滤后，没有可导出的样本"):
        DataPrepPipeline(config).run()
