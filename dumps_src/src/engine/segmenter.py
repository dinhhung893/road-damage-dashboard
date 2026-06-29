"""Road damage segmenter using FastSAM for instance segmentation.

Uses bbox-prompted segmentation: crop detected bbox → FastSAM → precise mask.
Replaces bbox proxy area with mask area for more accurate PCI calculation.

Pipeline: YOLOv12s detect → crop bbox → FastSAM segment → mask → PCI
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from ultralytics import FastSAM

from src.engine.detector import Detection, DetectionResult
from src.utils.logging_setup import get_logger

logger = get_logger("segmenter")

# Minimum crop size (pixels) to run segmentation — smaller crops produce poor masks
MIN_CROP_SIZE = 32


class RoadDamageSegmenter:
    """Road damage segmenter using FastSAM.

    Args:
        model_path: Path to FastSAM .pt weights file.
        device: 'cpu' or 'cuda'. Defaults to 'cpu'.
        imgsz: Inference image size for FastSAM. Smaller = faster.
    """

    def __init__(
        self,
        model_path: str | Path = "models/FastSAM-s.pt",
        device: str = "cpu",
        imgsz: int = 640,
    ) -> None:
        self.model_path = Path(model_path)
        self.device = device
        self.imgsz = imgsz
        self._model: Optional[FastSAM] = None
        self._load_failed = False

        if not self.model_path.exists():
            logger.warning(f"FastSAM model not found: {self.model_path}")
            self._load_failed = True

    @property
    def model(self) -> Optional[FastSAM]:
        """Lazy-load model on first access. Returns None if unavailable."""
        if self._load_failed:
            return None
        if self._model is None:
            try:
                logger.info(f"Loading FastSAM: {self.model_path}")
                self._model = FastSAM(str(self.model_path))
                logger.info("FastSAM loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load FastSAM: {e}")
                self._load_failed = True
                return None
        return self._model

    @property
    def is_available(self) -> bool:
        """Whether FastSAM model is available for segmentation."""
        return self.model is not None

    def segment_bbox(self, image: np.ndarray, bbox: tuple[float, float, float, float]) -> Optional[np.ndarray]:
        """Segment a single bbox region from the image.

        Args:
            image: Full image as numpy array (BGR).
            bbox: (x1, y1, x2, y2) pixel coordinates.

        Returns:
            Binary mask (same size as crop) or None if segmentation fails.
        """
        if self.model is None:
            return None

        x1, y1, x2, y2 = [int(v) for v in bbox]
        img_h, img_w = image.shape[:2]

        # Clamp to image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(img_w, x2), min(img_h, y2)

        crop_w, crop_h = x2 - x1, y2 - y1
        if crop_w < MIN_CROP_SIZE or crop_h < MIN_CROP_SIZE:
            logger.debug(f"Crop too small ({crop_w}x{crop_h}), skipping segmentation")
            return None

        # Crop bbox region
        crop = image[y1:y2, x1:x2]

        try:
            results = self.model(
                crop,
                device=self.device,
                retina_masks=True,
                imgsz=self.imgsz,
                conf=0.4,
                iou=0.9,
                verbose=False,
            )

            if not results or results[0].masks is None:
                logger.debug("FastSAM returned no masks for crop")
                return None

            # Use the largest mask (most likely the damage)
            masks = results[0].masks.data  # tensor: (N, H, W)
            if masks is None or len(masks) == 0:
                return None

            # Find largest mask by pixel count
            mask_np = masks.cpu().numpy()
            areas = mask_np.sum(axis=(1, 2))
            best_idx = int(areas.argmax())
            best_mask = mask_np[best_idx]

            # Binarize
            binary_mask = (best_mask > 0.5).astype(np.uint8)
            return binary_mask

        except Exception as e:
            logger.warning(f"FastSAM segmentation failed for bbox: {e}")
            return None

    @staticmethod
    def mask_to_contours(mask: np.ndarray, bbox_offset: tuple[int, int] = (0, 0)) -> list[list[tuple[float, float]]]:
        """Convert binary mask to contour points for rendering.

        Args:
            mask: Binary mask (H, W) with values 0 or 1.
            bbox_offset: (x_offset, y_offset) to shift contours from crop to image coords.

        Returns:
            List of contours, each contour is list of (x, y) points.
        """
        contours, _ = cv2.findContours(
            mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        x_off, y_off = bbox_offset
        result = []
        for contour in contours:
            if len(contour) < 3:
                continue
            points = [(float(pt[0][0] + x_off), float(pt[0][1] + y_off)) for pt in contour]
            result.append(points)
        return result

    def segment_detections(
        self,
        image: np.ndarray,
        detections: list[Detection],
        image_shape: tuple[int, int] = (0, 0),
    ) -> float:
        """Add segmentation mask data to each detection.

        Runs FastSAM on each detected bbox crop and adds mask_pixels
        and mask_area_sqft to Detection objects.

        Args:
            image: Full image as numpy array (BGR).
            detections: List of Detection objects with bbox data.
            image_shape: (height, width) of image for area conversion.

        Returns:
            Total segmentation time in milliseconds.
        """
        if self.model is None:
            logger.info("FastSAM not available, skipping segmentation")
            return 0.0

        start = time.perf_counter()
        img_h, img_w = image_shape if image_shape != (0, 0) else image.shape[:2]

        # Total image area in pixels
        total_pixels = img_h * img_w
        if total_pixels == 0:
            return 0.0

        for det in detections:
            if not det.include_in_pci:
                continue

            mask = self.segment_bbox(image, det.bbox)
            if mask is not None:
                det.mask_pixels = int(mask.sum())
                # Convert mask pixels to sqft using image area ratio
                # mask_area_sqft = (mask_pixels / total_pixels) * sample_unit_area
                # But we only store pixel ratio — PCI engine converts using config
                # Store as fraction of image area for now
                det.mask_area_sqft = det.mask_pixels / total_pixels

                # Extract contours for GUI rendering
                x1, y1 = int(det.bbox[0]), int(det.bbox[1])
                det.mask_contours = self.mask_to_contours(mask, bbox_offset=(x1, y1))

                logger.debug(
                    f"  {det.code}: mask={det.mask_pixels}px "
                    f"({det.mask_area_sqft:.4f} of image), "
                    f"{len(det.mask_contours)} contours"
                )
            else:
                logger.debug(f"  {det.code}: no mask, using bbox proxy")

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"Segmentation complete: {elapsed_ms:.0f}ms for {len(detections)} detections")
        return elapsed_ms

    def segment_image(self, image_path: str | Path, result: DetectionResult) -> DetectionResult:
        """Run segmentation on a DetectionResult's detections.

        Convenience method that loads image and runs segmentation.

        Args:
            image_path: Path to image file.
            result: DetectionResult from RoadDamageDetector.detect().

        Returns:
            Same DetectionResult with mask data added to detections.
        """
        image = cv2.imread(str(image_path))
        if image is None:
            logger.warning(f"Cannot read image for segmentation: {image_path}")
            return result

        seg_time = self.segment_detections(image, result.pci_detections, result.image_shape)
        result.segmentation_time_ms = seg_time
        return result
