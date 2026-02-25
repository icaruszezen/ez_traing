"""OpenCV 模板匹配引擎，封装 cv2.matchTemplate 并提供 NMS 去重。"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from ez_traing.prelabeling.models import BoundingBox

logger = logging.getLogger(__name__)


def imread_unicode(path: str, flags: int = cv2.IMREAD_COLOR) -> Optional[np.ndarray]:
    """读取可能含非 ASCII（如中文）路径的图片，兼容 Windows。"""
    try:
        data = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(data, flags)
    except Exception:
        return None


@dataclass
class TemplateInfo:
    """单个模板图的元信息。"""

    path: str
    label: str
    image: Optional[np.ndarray] = field(default=None, repr=False)
    height: int = 0
    width: int = 0


@dataclass
class MatchResult:
    """单张目标图的匹配结果。"""

    image_path: str
    success: bool
    boxes: List[BoundingBox] = field(default_factory=list)
    error_message: str = ""


class TemplateMatcher:
    """基于 OpenCV 的多模板匹配器。

    Parameters
    ----------
    threshold : float
        匹配分数下限，低于此值的候选框被过滤。
    max_candidates : int
        每张图片最多保留的候选框数（NMS 之后）。
    nms_iou_threshold : float
        NMS 的 IoU 阈值。
    method : int
        cv2.matchTemplate 使用的匹配算法，默认 TM_CCOEFF_NORMED。
    multi_scale : bool
        是否在多个缩放尺度上搜索。
    scale_range : tuple
        缩放搜索范围 (min_scale, max_scale)。
    scale_steps : int
        缩放搜索步数。
    """

    def __init__(
        self,
        threshold: float = 0.8,
        max_candidates: int = 50,
        nms_iou_threshold: float = 0.3,
        method: int = cv2.TM_CCOEFF_NORMED,
        multi_scale: bool = False,
        scale_range: Tuple[float, float] = (0.5, 1.5),
        scale_steps: int = 10,
    ):
        self.threshold = threshold
        self.max_candidates = max_candidates
        self.nms_iou_threshold = nms_iou_threshold
        self.method = method
        self.multi_scale = multi_scale
        self.scale_range = scale_range
        self.scale_steps = scale_steps

    # ------------------------------------------------------------------
    # Template loading
    # ------------------------------------------------------------------

    @staticmethod
    def load_template(path: str, label: str) -> TemplateInfo:
        """加载模板图片并返回 TemplateInfo。

        Raises
        ------
        ValueError
            文件不存在或无法解码。
        """
        p = Path(path)
        if not p.is_file():
            raise ValueError(f"模板文件不存在: {path}")

        img = imread_unicode(str(p), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"无法读取模板图片: {path}")

        h, w = img.shape[:2]
        return TemplateInfo(path=path, label=label, image=img, height=h, width=w)

    # ------------------------------------------------------------------
    # Single-image matching
    # ------------------------------------------------------------------

    def match(
        self,
        target_path: str,
        templates: List[TemplateInfo],
    ) -> MatchResult:
        """对单张目标图执行多模板匹配。"""
        target = imread_unicode(target_path, cv2.IMREAD_COLOR)
        if target is None:
            return MatchResult(
                image_path=target_path,
                success=False,
                error_message=f"无法读取目标图片: {target_path}",
            )

        all_boxes: List[BoundingBox] = []

        for tpl in templates:
            if tpl.image is None:
                continue
            try:
                if self.multi_scale:
                    boxes = self._match_multi_scale(target, tpl)
                else:
                    boxes = self._match_single_scale(target, tpl)
                all_boxes.extend(boxes)
            except Exception as exc:
                logger.warning(
                    "模板 %s 在 %s 上匹配出错: %s",
                    tpl.label,
                    target_path,
                    exc,
                )

        all_boxes = self._nms(all_boxes)

        if self.max_candidates and len(all_boxes) > self.max_candidates:
            all_boxes.sort(key=lambda b: b.confidence, reverse=True)
            all_boxes = all_boxes[: self.max_candidates]

        return MatchResult(image_path=target_path, success=True, boxes=all_boxes)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match_single_scale(
        self, target: np.ndarray, tpl: TemplateInfo
    ) -> List[BoundingBox]:
        th, tw = tpl.height, tpl.width
        if target.shape[0] < th or target.shape[1] < tw:
            return []

        result = cv2.matchTemplate(target, tpl.image, self.method)
        return self._extract_boxes(result, tw, th, tpl.label)

    def _match_multi_scale(
        self, target: np.ndarray, tpl: TemplateInfo
    ) -> List[BoundingBox]:
        boxes: List[BoundingBox] = []
        lo, hi = self.scale_range
        for scale in np.linspace(lo, hi, self.scale_steps):
            new_w = max(1, int(tpl.width * scale))
            new_h = max(1, int(tpl.height * scale))
            if new_h > target.shape[0] or new_w > target.shape[1]:
                continue
            resized = cv2.resize(tpl.image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            result = cv2.matchTemplate(target, resized, self.method)
            boxes.extend(self._extract_boxes(result, new_w, new_h, tpl.label))
        return boxes

    def _extract_boxes(
        self, result: np.ndarray, tw: int, th: int, label: str
    ) -> List[BoundingBox]:
        locations = np.where(result >= self.threshold)
        boxes: List[BoundingBox] = []
        for y, x in zip(*locations):
            score = float(result[y, x])
            boxes.append(
                BoundingBox(
                    label=label,
                    x_min=int(x),
                    y_min=int(y),
                    x_max=int(x + tw),
                    y_max=int(y + th),
                    confidence=score,
                )
            )
        return boxes

    def _nms(self, boxes: List[BoundingBox]) -> List[BoundingBox]:
        """非极大值抑制。"""
        if not boxes:
            return boxes

        coords = np.array(
            [[b.x_min, b.y_min, b.x_max, b.y_max] for b in boxes], dtype=np.float32
        )
        scores = np.array([b.confidence for b in boxes], dtype=np.float32)

        indices = cv2.dnn.NMSBoxes(
            bboxes=coords.tolist(),
            scores=scores.tolist(),
            score_threshold=self.threshold,
            nms_threshold=self.nms_iou_threshold,
        )

        if len(indices) == 0:
            return []

        kept_indices = indices.flatten().tolist()
        return [boxes[i] for i in kept_indices]
