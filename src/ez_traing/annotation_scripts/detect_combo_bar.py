"""自动检测游戏截图中左下角"角色连携可用"白色横条并生成 VOC 标注。

算法流程:
1. 裁剪图片左下角 ROI 区域
2. 灰度化 + 阈值 220 二值化，提取高亮白色像素
3. 查找外轮廓，按宽高比和尺寸过滤出横条形状
4. 以 Y 中心中位数做同水平线聚合，剔除离群噪声
5. 输出 / 合并 VOC 标注
"""

import argparse
from typing import List, Tuple

import cv2
import numpy as np

from ez_traing.annotation_scripts.voc_utils import DetectResult, run_annotation

LABEL = "角色连携可用"

ROI_X_RATIO = 0.40
ROI_Y_RATIO = 0.25
THRESHOLD = 220

REF_IMAGE_WIDTH = 1024
REF_BAR_WIDTH = 44
BAR_WIDTH_TOLERANCE = 10
REF_MAX_HEIGHT = 20
MIN_ASPECT_RATIO = 3.0
MAX_BARS = 4
REF_Y_TOLERANCE = 15


# ---------------------------------------------------------------------------
# 白色横条检测
# ---------------------------------------------------------------------------

def detect_white_bars(image_path: str) -> DetectResult:
    """检测图片左下角的白色横条。

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

    h, w = img.shape[:2]

    roi_x_end = int(w * ROI_X_RATIO)
    roi_y_start = int(h * (1 - ROI_Y_RATIO))
    roi = img[roi_y_start:h, 0:roi_x_end]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, THRESHOLD, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    scale = w / REF_IMAGE_WIDTH
    min_width = int((REF_BAR_WIDTH - BAR_WIDTH_TOLERANCE) * scale)
    max_width = int((REF_BAR_WIDTH + BAR_WIDTH_TOLERANCE) * scale)
    max_height = int(REF_MAX_HEIGHT * scale)
    y_tolerance = REF_Y_TOLERANCE * scale

    candidates: List[Tuple[int, int, int, int, float]] = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if ch == 0 or cw == 0:
            continue
        if cw / ch < MIN_ASPECT_RATIO:
            continue
        if cw < min_width or cw > max_width:
            continue
        if ch > max_height:
            continue

        orig_x = x
        orig_y = y + roi_y_start
        y_center = orig_y + ch / 2.0
        candidates.append((orig_x, orig_y, orig_x + cw, orig_y + ch, y_center))

    if not candidates:
        return [], w, h

    y_centers = [c[4] for c in candidates]
    median_y = float(np.median(y_centers))
    bars: List[Tuple[int, int, int, int]] = [
        (c[0], c[1], c[2], c[3])
        for c in candidates
        if abs(c[4] - median_y) <= y_tolerance
    ]

    bars.sort(key=lambda b: b[0])

    if len(bars) > MAX_BARS:
        bars = bars[:MAX_BARS]

    return bars, w, h


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def run(dataset_dir: str) -> None:
    run_annotation(dataset_dir, LABEL, detect_white_bars, item_name="横条")


def main() -> None:
    parser = argparse.ArgumentParser(description="检测角色连携可用白色横条并生成 VOC 标注")
    parser.add_argument("--dataset_dir", required=True, help="数据集目录")
    args = parser.parse_args()
    run(args.dataset_dir)


if __name__ == "__main__":
    main()
