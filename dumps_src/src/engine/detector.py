"""Road damage detector using ultralytics YOLO (torch CPU) with optional ONNX Runtime.

Primary: ultralytics .pt inference (torch CPU — stable, simple)
Optional: ONNX Runtime + DirectML (faster GPU inference, currently has
          DmlGraphFusionHelper crash with YOLOv12 — deferred to future fix)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from ultralytics import YOLO

from src.utils.logging_setup import get_logger

logger = get_logger("detector")

# ASTM D6433 short codes for PCI mapping
CLASS_CODE_MAP = {
    "longitudinal_crack": "D00",
    "transverse_crack": "D10",
    "alligator_crack": "D20",
    "pothole": "D40",
}

# Classes excluded from PCI calculation
PCI_EXCLUDED_NAMES = {"repair", "other"}


@dataclass
class Detection:
    """Single detection result."""

    class_name: str          # e.g. "longitudinal_crack"
    class_id: int            # model class index
    confidence: float        # 0.0–1.0
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2) pixel coords
    code: str = ""           # ASTM code, e.g. "D00"
    include_in_pci: bool = True
    mask_pixels: int = 0     # Segmentation mask pixel count (0 = no mask)
    mask_area_sqft: float = 0.0  # Mask area in sq ft (0 = no mask)
    mask_contours: list = field(default_factory=list)  # Contour points for GUI rendering

    def __post_init__(self) -> None:
        if not self.code:
            self.code = CLASS_CODE_MAP.get(self.class_name, "UNKNOWN")
        if self.class_name.lower() in PCI_EXCLUDED_NAMES:
            self.include_in_pci = False

    @property
    def has_mask(self) -> bool:
        """Whether this detection has a segmentation mask."""
        return self.mask_pixels > 0

    @property
    def bbox_area_sqft(self) -> float:
        """Bbox area in sq ft (computed from bbox coords, requires image shape)."""
        # This is a raw pixel area — conversion to sqft done externally
        x1, y1, x2, y2 = self.bbox
        return abs((x2 - x1) * (y2 - y1))  # pixel area

    @property
    def effective_area_sqft(self) -> float:
        """Mask area if available, otherwise bbox area (in sq ft)."""
        return self.mask_area_sqft if self.has_mask else 0.0


@dataclass
class DetectionResult:
    """Detection results for a single image."""

    image_path: str
    detections: list[Detection] = field(default_factory=list)
    image_shape: tuple[int, int] = (0, 0)  # (height, width)
    inference_time_ms: float = 0.0
    segmentation_time_ms: float = 0.0

    @property
    def pci_detections(self) -> list[Detection]:
        """Detections included in PCI calculation (excludes Repair/Other)."""
        return [d for d in self.detections if d.include_in_pci]

    @property
    def damage_types(self) -> set[str]:
        """Unique ASTM damage codes present."""
        return {d.code for d in self.pci_detections}


class RoadDamageDetector:
    """Road damage detector using YOLOv12s pretrained weights.

    Args:
        model_path: Path to .pt weights file.
        confidence: Minimum confidence threshold.
        device: 'cpu' or 'cuda'. Defaults to 'cpu'.
    """

    def __init__(
        self,
        model_path: str | Path = "models/yolo-rdd2022-benchmark/yolo12s_seed0_best.pt",
        confidence: float = 0.15,
        device: str = "cpu",
    ) -> None:
        self.model_path = Path(model_path)
        self.confidence = confidence
        self.device = device
        self._model: Optional[YOLO] = None

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")

    @property
    def model(self) -> YOLO:
        """Lazy-load model on first access."""
        if self._model is None:
            logger.info(f"Loading model: {self.model_path}")
            self._model = YOLO(str(self.model_path))
            logger.info(
                f"Model loaded. Classes: {self._model.names} "
                f"({len(self._model.names)} classes)"
            )
        return self._model

    def detect(self, image_path: str | Path) -> DetectionResult:
        """Run detection on a single image.

        Args:
            image_path: Path to image file.

        Returns:
            DetectionResult with all detections.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.info(f"Detecting: {image_path.name}")

        # Run inference
        results = self.model(
            str(image_path),
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )

        if not results:
            logger.warning("No results returned from model")
            return DetectionResult(
                image_path=str(image_path),
                image_shape=self._read_image_shape(image_path),
            )

        result = results[0]
        img_h, img_w = result.orig_shape if result.orig_shape is not None else (0, 0)

        # Parse detections
        detections = []
        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i])
                conf = float(boxes.conf[i])
                xyxy = boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])
                class_name = self.model.names.get(cls_id, f"class_{cls_id}")

                det = Detection(
                    class_name=class_name,
                    class_id=cls_id,
                    confidence=conf,
                    bbox=(x1, y1, x2, y2),
                )
                detections.append(det)

        # Inference time from result
        speed = result.speed  # dict: preprocess, inference, postprocess (ms)
        inference_ms = speed.get("inference", 0.0)

        logger.info(
            f"Found {len(detections)} detections "
            f"({len([d for d in detections if d.include_in_pci])} PCI) "
            f"in {inference_ms:.0f}ms"
        )

        return DetectionResult(
            image_path=str(image_path),
            detections=detections,
            image_shape=(img_h, img_w),
            inference_time_ms=inference_ms,
        )

    def detect_batch(self, image_paths: list[str | Path]) -> list[DetectionResult]:
        """Run detection on multiple images.

        Args:
            image_paths: List of image file paths.

        Returns:
            List of DetectionResult, one per image.
        """
        return [self.detect(p) for p in image_paths]

    @staticmethod
    def _read_image_shape(path: Path) -> tuple[int, int]:
        """Read image shape without full decode (uses cv2)."""
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is not None:
            return img.shape[:2]  # (h, w)
        return (0, 0)
