"""验证报告导出。"""

import csv
import json
from pathlib import Path
from typing import Dict

from ez_traing.evaluation.models import EvalConfig, EvalResult


def export_reports(result: EvalResult, config: EvalConfig, output_dir: str) -> Dict[str, str]:
    """导出验证报告到指定目录。"""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    metrics_json = root / "metrics.json"
    metrics_csv = root / "metrics.csv"

    payload = {
        "config": config.to_dict(),
        "result": result.to_dict(),
    }
    with open(metrics_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(metrics_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        if result.metrics:
            writer.writerow(["mAP50", f"{result.metrics.map50:.6f}"])
            writer.writerow(["mAP50-95", f"{result.metrics.map50_95:.6f}"])
            writer.writerow(["Precision", f"{result.metrics.precision:.6f}"])
            writer.writerow(["Recall", f"{result.metrics.recall:.6f}"])
            writer.writerow(["F1", f"{result.metrics.f1:.6f}"])
        writer.writerow([])
        writer.writerow(["save_dir", result.save_dir])
        writer.writerow(["message", result.message])

    return {
        "metrics_json": str(metrics_json),
        "metrics_csv": str(metrics_csv),
    }
