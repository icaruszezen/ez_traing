"""自动检测游戏截图中敌人血条并生成 VOC 标注。

基于 MaaEnd AutoFight 的 hasEnemyInScreen() 逻辑，通过 RGB 颜色匹配 +
连通域分析在两个 ROI 区域（小怪中部区 / Boss 顶部区）检测红色血条。

所有 ROI 坐标与过滤阈值以 1280x720 为基准，运行时按实际分辨率自动缩放。
"""

import argparse
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np

from ez_traing.annotation_scripts.voc_utils import DetectResult, run_annotation

LABEL = "血条"

# ---------------------------------------------------------------------------
# 基准分辨率 & 检测区域定义（坐标/阈值均基于 1280x720）
# ---------------------------------------------------------------------------

REF_WIDTH = 1280
REF_HEIGHT = 720


@dataclass(frozen=True)
class HpBarZone:
    name: str
    roi_x: int
    roi_y: int
    roi_w: int
    roi_h: int
    lower_rgb: Tuple[int, int, int]
    upper_rgb: Tuple[int, int, int]
    min_pixel_count: int


ZONES: List[HpBarZone] = [
    HpBarZone(
        name="小怪血条",
        roi_x=0, roi_y=0, roi_w=1280, roi_h=620,
        lower_rgb=(235, 75, 95),
        upper_rgb=(255, 95, 120),
        min_pixel_count=50,
    ),
    HpBarZone(
        name="Boss血条",
        roi_x=400, roi_y=0, roi_w=500, roi_h=100,
        lower_rgb=(240, 60, 90),
        upper_rgb=(255, 90, 140),
        min_pixel_count=200,
    ),
]

MIN_ASPECT_RATIO = 2.0
REF_MIN_WIDTH = 15
REF_MORPH_KERNEL = 3
REF_BOX_PADDING = 3


# ---------------------------------------------------------------------------
# 缩放工具
# ---------------------------------------------------------------------------

def _scale_roi(
    zone: HpBarZone, sx: float, sy: float, img_w: int, img_h: int,
) -> Tuple[int, int, int, int]:
    """将基准 ROI 按缩放因子映射到实际图片，clamp 到图片边界。"""
    x = max(0, int(zone.roi_x * sx))
    y = max(0, int(zone.roi_y * sy))
    w = int(zone.roi_w * sx)
    h = int(zone.roi_h * sy)
    x2 = min(img_w, x + w)
    y2 = min(img_h, y + h)
    return x, y, x2, y2


def _rgb_to_bgr(rgb: Tuple[int, int, int]) -> np.ndarray:
    return np.array([rgb[2], rgb[1], rgb[0]], dtype=np.uint8)


# ---------------------------------------------------------------------------
# 血条检测
# ---------------------------------------------------------------------------

def detect_hp_bars(image_path: str) -> DetectResult:
    """检测图片中的敌人血条。

    Returns:
        ``(bars, width, height)`` — *bars* 为 ``[(xmin, ymin, xmax, ymax), ...]``
        原图坐标系下的外接矩形列表；读取失败时返回 ``([], 0, 0)``。
    """
    try:
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        print(f"  无法读取图片: {image_path}")
        return [], 0, 0
    if img is None:
        print(f"  无法读取图片: {image_path}")
        return [], 0, 0

    img_h, img_w = img.shape[:2]
    sx = img_w / REF_WIDTH
    sy = img_h / REF_HEIGHT
    area_scale = sx * sy

    kernel_size = max(1, int(REF_MORPH_KERNEL * min(sx, sy)))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

    min_width = int(REF_MIN_WIDTH * sx)
    pad_x = max(1, int(REF_BOX_PADDING * sx))
    pad_y = max(1, int(REF_BOX_PADDING * sy))

    all_bars: List[Tuple[int, int, int, int]] = []

    for zone in ZONES:
        x1, y1, x2, y2 = _scale_roi(zone, sx, sy, img_w, img_h)
        if x2 <= x1 or y2 <= y1:
            continue

        roi = img[y1:y2, x1:x2]

        lower_bgr = _rgb_to_bgr(zone.lower_rgb)
        upper_bgr = _rgb_to_bgr(zone.upper_rgb)
        mask = cv2.inRange(roi, lower_bgr, upper_bgr)

        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)

        scaled_min_count = int(zone.min_pixel_count * area_scale)

        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < scaled_min_count:
                continue

            bx = stats[i, cv2.CC_STAT_LEFT]
            by = stats[i, cv2.CC_STAT_TOP]
            bw = stats[i, cv2.CC_STAT_WIDTH]
            bh = stats[i, cv2.CC_STAT_HEIGHT]

            if bh == 0 or bw / bh < MIN_ASPECT_RATIO:
                continue
            if bw < min_width:
                continue

            xmin = max(0, x1 + bx - pad_x)
            ymin = max(0, y1 + by - pad_y)
            xmax = min(img_w, x1 + bx + bw + pad_x)
            ymax = min(img_h, y1 + by + bh + pad_y)
            all_bars.append((xmin, ymin, xmax, ymax))

    return all_bars, img_w, img_h


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def run(dataset_dir: str) -> None:
    run_annotation(dataset_dir, LABEL, detect_hp_bars, item_name="血条")


def main() -> None:
    parser = argparse.ArgumentParser(description="检测敌人血条并生成 VOC 标注")
    parser.add_argument("--dataset_dir", required=True, help="数据集目录")
    args = parser.parse_args()
    run(args.dataset_dir)


if __name__ == "__main__":
    main()
