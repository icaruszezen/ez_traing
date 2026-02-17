"""YOLO 验证引擎。"""

import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import yaml

from ez_traing.evaluation.models import EvalConfig, EvalMetrics, EvalResult
from ez_traing.evaluation.visualization import discover_yolo_plots, generate_fallback_charts


def _get_config_dir() -> Path:
    config_dir = Path.home() / ".ez_traing"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _sanitize_name(value: str) -> str:
    value = re.sub(r"[^\w\-]+", "_", value.strip())
    return value.strip("_") or "val"


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _read_classes(dataset_dir: Path):
    for path in [dataset_dir / "classes.txt", dataset_dir / "labels" / "classes.txt"]:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                names = [line.strip() for line in f if line.strip()]
            if names:
                return names
    raise ValueError(f"找不到 classes.txt 文件: {dataset_dir}")


def build_data_yaml(dataset_name: str, dataset_dir: str, output_dir: str) -> str:
    """根据数据集目录生成 YOLO data yaml。"""
    root = Path(dataset_dir)
    if not root.exists():
        raise ValueError(f"数据集目录不存在: {dataset_dir}")

    class_names = _read_classes(root)

    images_dir = root / "images"
    if not images_dir.exists():
        images_dir = root

    train_dir = images_dir / "train"
    val_dir = images_dir / "val"

    if train_dir.exists() and val_dir.exists():
        train_path = str(train_dir)
        val_path = str(val_dir)
    else:
        train_path = str(images_dir)
        val_path = str(images_dir)

    data_config = {
        "path": str(root),
        "train": train_path,
        "val": val_path,
        "names": {i: name for i, name in enumerate(class_names)},
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    yaml_path = out / f"{_sanitize_name(dataset_name)}_val_data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_config, f, allow_unicode=True, default_flow_style=False)
    return str(yaml_path)


class EvaluationEngine:
    """模型验证执行器。"""

    def run(
        self,
        config: EvalConfig,
        log_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> EvalResult:
        def emit_log(text: str):
            if log_callback:
                log_callback(text)

        def emit_progress(value: int):
            if progress_callback:
                progress_callback(max(0, min(100, value)))

        try:
            emit_progress(2)
            model_path = Path(config.model_path)
            if not model_path.exists() or model_path.suffix.lower() != ".pt":
                raise ValueError("请选择存在的 YOLO 权重文件（.pt）")

            output_root = Path(config.output_root) if config.output_root else _get_config_dir() / "runs" / "val"
            output_root.mkdir(parents=True, exist_ok=True)
            run_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_sanitize_name(config.dataset_name)}_{_sanitize_name(model_path.stem)}"

            emit_log(f"[INFO] 数据集: {config.dataset_name}")
            emit_log(f"[INFO] 数据集目录: {config.dataset_dir}")
            emit_log(f"[INFO] 模型权重: {config.model_path}")
            emit_progress(10)

            data_yaml = build_data_yaml(config.dataset_name, config.dataset_dir, str(output_root))
            emit_log(f"[INFO] 生成 data yaml: {data_yaml}")
            emit_progress(20)

            try:
                from ultralytics import YOLO
            except ImportError as e:
                raise RuntimeError("未安装 ultralytics，请先安装依赖") from e

            emit_log("[INFO] 正在加载模型...")
            model = YOLO(config.model_path)
            emit_progress(30)

            emit_log("[INFO] 开始验证，请稍候...")
            results = model.val(
                data=data_yaml,
                imgsz=int(config.imgsz),
                batch=int(config.batch),
                device=config.device if config.device != "auto" else None,
                conf=float(config.conf),
                iou=float(config.iou),
                project=str(output_root),
                name=run_name,
                exist_ok=True,
                verbose=False,
                plots=True,
                save_json=True,
            )
            emit_progress(80)

            box = getattr(results, "box", None)
            map50 = _safe_float(getattr(box, "map50", None), 0.0)
            map50_95 = _safe_float(getattr(box, "map", None), 0.0)
            precision = _safe_float(getattr(box, "mp", None), 0.0)
            recall = _safe_float(getattr(box, "mr", None), 0.0)
            denom = precision + recall
            f1 = 0.0 if denom <= 0 else (2.0 * precision * recall / denom)

            metrics = EvalMetrics(
                map50=map50,
                map50_95=map50_95,
                precision=precision,
                recall=recall,
                f1=f1,
            )

            save_dir = str(getattr(results, "save_dir", output_root / run_name))
            artifacts = discover_yolo_plots(save_dir)
            if not artifacts:
                artifacts.update(generate_fallback_charts(metrics, save_dir))

            emit_log(f"[INFO] 验证完成，结果目录: {save_dir}")
            emit_log(
                "[METRIC] "
                f"mAP50={metrics.map50:.4f}, "
                f"mAP50-95={metrics.map50_95:.4f}, "
                f"P={metrics.precision:.4f}, "
                f"R={metrics.recall:.4f}, "
                f"F1={metrics.f1:.4f}"
            )
            emit_progress(100)

            return EvalResult(
                success=True,
                message="验证完成",
                save_dir=save_dir,
                data_yaml=data_yaml,
                metrics=metrics,
                artifacts=artifacts,
                raw_summary={"run_name": run_name},
            )
        except Exception as e:
            emit_log(f"[ERROR] 验证失败: {e}")
            return EvalResult(success=False, message=str(e))
