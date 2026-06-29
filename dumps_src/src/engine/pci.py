"""PCI (Pavement Condition Index) calculation engine — ASTM D6433.

Implements the full PCI calculation pipeline:
1. Load deduct value curves from data/pci_astm_d6433.json
2. Calculate damage density from bounding boxes
3. Assign severity level based on density
4. Look up deduct value via linear interpolation
5. Calculate CDV (Corrected Deduct Value) from q and TDV
6. PCI = 100 - CDV
7. Rate PCI into 6 categories + maintenance recommendation
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.utils.logging_setup import get_logger

logger = get_logger("pci")

# Default path to ASTM D6433 data file
_DEFAULT_PCI_DATA = Path("data/pci_astm_d6433.json")

# Bbox overestimate correction factors per damage type
# D00 (longitudinal crack) bboxes are typically very wide relative to actual crack
# D10 (transverse crack) bboxes are typically very tall relative to actual crack
BBOX_CORRECTION_FACTORS: dict[str, float] = {
    "D00": 0.3,   # Longitudinal cracks are thin lines — bbox greatly overestimates
    "D10": 0.3,   # Transverse cracks are thin lines — bbox greatly overestimates
    "D20": 0.7,   # Alligator cracking fills bbox more
    "D40": 0.8,   # Potholes fill bbox reasonably well
}


@dataclass
class DamageRecord:
    """A single damage observation for PCI calculation."""

    code: str                                    # ASTM code: D00, D10, D20, D40
    severity: str                                # Low, Medium, High
    density_pct: float                           # Damage density (%)
    deduct_value: float = 0.0                    # Looked up from curves
    bbox_area_sqft: float = 0.0                  # Bbox area in sq ft
    corrected_area_sqft: float = 0.0             # After bbox correction
    confidence: float = 0.0                      # Detection confidence

    def __post_init__(self) -> None:
        if self.severity not in ("Low", "Medium", "High"):
            raise ValueError(f"Invalid severity: {self.severity}")


@dataclass
class PCIResult:
    """PCI calculation result for a sample unit."""

    pci_value: float                             # 0–100
    rating: str                                  # Good/Satisfactory/Fair/Poor/Very Poor/Failed
    maintenance_action: str = ""                 # Recommended action
    maintenance_detail: str = ""                 # Action detail
    cdv: float = 0.0                             # Corrected Deduct Value
    tdv: float = 0.0                             # Total Deduct Value
    q: int = 0                                   # Number of deduct values > 2
    damages: list[DamageRecord] = field(default_factory=list)
    sample_unit_area_sqft: float = 5000.0

    @property
    def pci_color(self) -> str:
        """Hex color for PCI rating."""
        return PCIEngine.RATING_COLORS.get(self.rating, "#999999")


class PCIEngine:
    """ASTM D6433 PCI calculation engine.

    Args:
        pci_data_path: Path to pci_astm_d6433.json.
        sample_unit_area_sqft: Sample unit area in sq ft (default 5000).
    """

    RATING_COLORS: dict[str, str] = {
        "Good": "#2ecc71",
        "Satisfactory": "#27ae60",
        "Fair": "#f1c40f",
        "Poor": "#e67e22",
        "Very Poor": "#e74c3c",
        "Failed": "#c0392b",
    }

    def __init__(
        self,
        pci_data_path: str | Path | None = None,
        sample_unit_area_sqft: float = 5000.0,
    ) -> None:
        self.pci_data_path = Path(pci_data_path) if pci_data_path else _DEFAULT_PCI_DATA
        self.sample_unit_area_sqft = sample_unit_area_sqft
        self._data: dict[str, Any] = {}
        self._deduct_curves: dict[str, dict[str, list[list[float]]]] = {}
        self._cdv_curves: dict[str, list[list[float]]] = {}
        self._severity_rules: dict[str, dict[str, dict[str, Any]]] = {}
        self._rating_scale: dict[str, dict[str, Any]] = {}
        self._maintenance: dict[str, dict[str, str]] = {}
        self._distress_mapping: dict[str, dict[str, Any]] = {}

    @property
    def data(self) -> dict[str, Any]:
        """Lazy-load PCI data from JSON."""
        if not self._data:
            self._load_data()
        return self._data

    def _load_data(self) -> None:
        """Load and parse PCI data file."""
        if not self.pci_data_path.exists():
            raise FileNotFoundError(f"PCI data not found: {self.pci_data_path}")

        logger.info(f"Loading PCI data: {self.pci_data_path}")
        with open(self.pci_data_path, encoding="utf-8") as f:
            self._data = json.load(f)

        self._deduct_curves = self._data["deduct_value_curves"]
        self._cdv_curves = self._data["cdv_correction"]["curves"]
        self._severity_rules = self._data["severity_assignment"]
        self._rating_scale = self._data["pci_rating"]
        self._maintenance = self._data["maintenance_recommendation"]
        self._distress_mapping = self._data["distress_mapping"]

        logger.info(
            f"PCI data loaded: {len(self._deduct_curves)} distress types, "
            f"{len(self._cdv_curves)} CDV curves"
        )

    @staticmethod
    def interpolate_curve(curve: list[list[float]], x: float) -> float:
        """Linear interpolation on a curve [[x, y], ...].

        Clamps x to curve range. Returns interpolated y value.
        """
        if not curve:
            return 0.0

        # Clamp to range
        x_min = curve[0][0]
        x_max = curve[-1][0]
        x = max(x_min, min(x_max, x))

        # Find bracketing points
        for i in range(len(curve) - 1):
            x0, y0 = curve[i]
            x1, y1 = curve[i + 1]
            if x0 <= x <= x1:
                if x1 == x0:
                    return y0
                t = (x - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)

        # Extrapolate last point
        return curve[-1][1]

    def assign_severity(self, code: str, density_pct: float) -> str:
        """Assign severity level based on damage density.

        Uses severity_assignment rules from data file.
        When only bbox is available (no mask), density serves as proxy.

        Args:
            code: ASTM damage code (D00, D10, D20, D40).
            density_pct: Damage density as percentage.

        Returns:
            Severity level: "Low", "Medium", or "High".
        """
        _ = self.data  # ensure loaded
        if code not in self._severity_rules:
            logger.warning(f"Unknown damage code: {code}, defaulting to Low")
            return "Low"

        rules = self._severity_rules[code]
        # Rules are ordered Low → Medium → High with max_density_pct thresholds
        if density_pct <= rules["Low"]["max_density_pct"]:
            return "Low"
        elif density_pct <= rules["Medium"]["max_density_pct"]:
            return "Medium"
        else:
            return "High"

    def lookup_deduct_value(self, code: str, severity: str, density_pct: float) -> float:
        """Look up deduct value from curves via interpolation.

        Args:
            code: ASTM damage code.
            severity: Severity level.
            density_pct: Damage density (%).

        Returns:
            Deduct value (0–100).
        """
        _ = self.data  # ensure loaded
        if code not in self._deduct_curves:
            logger.warning(f"No deduct curve for {code}")
            return 0.0

        severity_curves = self._deduct_curves[code]
        if severity not in severity_curves:
            logger.warning(f"No {severity} curve for {code}")
            return 0.0

        curve = severity_curves[severity]
        return self.interpolate_curve(curve, density_pct)

    def calculate_cdv(self, deduct_values: list[float]) -> tuple[float, int, float]:
        """Calculate Corrected Deduct Value (CDV) from deduct values.

        ASTM D6433 procedure:
        1. Count q = number of deduct values > 2
        2. Calculate TDV = sum of all deduct values
        3. If q <= 1: CDV = TDV
        4. If q > 1: look up CDV from correction curves using q and TDV

        Args:
            deduct_values: List of deduct values for all damage types.

        Returns:
            Tuple of (CDV, q, TDV).
        """
        if not deduct_values:
            return 0.0, 0, 0.0

        _ = self.data  # ensure loaded

        q = sum(1 for dv in deduct_values if dv > 2)
        tdv = sum(deduct_values)

        if q <= 1:
            cdv = tdv
            logger.debug(f"CDV: q={q} <= 1, CDV = TDV = {tdv:.1f}")
        else:
            # Look up CDV from correction curves
            curve_key = f"q{min(q, 10)}"  # Max q=10 in data
            if curve_key not in self._cdv_curves:
                logger.warning(f"No CDV curve for q={q}, using q=10")
                curve_key = "q10"

            cdv = self.interpolate_curve(self._cdv_curves[curve_key], tdv)
            logger.debug(f"CDV: q={q}, TDV={tdv:.1f}, CDV={cdv:.1f}")

        return cdv, q, tdv

    @staticmethod
    def classify_rating(pci_value: float) -> str:
        """Classify PCI value into rating category.

        Args:
            pci_value: PCI value (0–100).

        Returns:
            Rating string.
        """
        if pci_value >= 85:
            return "Good"
        elif pci_value >= 70:
            return "Satisfactory"
        elif pci_value >= 55:
            return "Fair"
        elif pci_value >= 40:
            return "Poor"
        elif pci_value >= 25:
            return "Very Poor"
        else:
            return "Failed"

    def get_maintenance(self, rating: str) -> tuple[str, str]:
        """Get maintenance recommendation for a rating.

        Args:
            rating: PCI rating category.

        Returns:
            Tuple of (action, detail).
        """
        _ = self.data  # ensure loaded
        if rating in self._maintenance:
            rec = self._maintenance[rating]
            return rec["action"], rec["detail"]
        return "Unknown", ""

    def calculate_density(
        self,
        bbox_area_px: float,
        image_area_px: float,
        correction_factor: float = 1.0,
        mask_area_ratio: float = 0.0,
    ) -> float:
        """Calculate damage density as percentage of sample unit.

        When mask_area_ratio > 0 (from segmentation), uses mask area directly
        (no bbox correction needed — mask is precise). Otherwise uses bbox area
        with overestimate correction.

        Args:
            bbox_area_px: Bounding box area in pixels.
            image_area_px: Total image area in pixels.
            correction_factor: Factor to correct bbox overestimate (0–1).
            mask_area_ratio: Mask area as fraction of image (from segmenter).

        Returns:
            Density as percentage (0–100+).
        """
        if image_area_px <= 0:
            return 0.0

        if mask_area_ratio > 0:
            # Mask area is precise — no correction needed
            density_pct = mask_area_ratio * 100.0
        else:
            # Bbox proxy — apply overestimate correction
            proportion = bbox_area_px / image_area_px
            proportion *= correction_factor
            density_pct = proportion * 100.0

        return density_pct

    def calculate_pci(
        self,
        detections: list[dict],
        image_area_px: float = 0.0,
        apply_bbox_correction: bool = True,
    ) -> PCIResult:
        """Calculate PCI for a sample unit from detection results.

        Args:
            detections: List of detection dicts with keys:
                - code: ASTM damage code (D00, D10, D20, D40)
                - bbox: (x1, y1, x2, y2) pixel coordinates
                - confidence: Detection confidence
                - class_name: Model class name (optional, for code mapping)
            image_area_px: Image area in pixels (h * w).
            apply_bbox_correction: Whether to apply bbox overestimate correction.

        Returns:
            PCIResult with full PCI calculation details.
        """
        if not detections:
            return PCIResult(
                pci_value=100.0,
                rating="Good",
                maintenance_action="Bảo dưỡng định kỳ (routine maintenance)",
                maintenance_detail="Chỉ cần theo dõi, không cần can thiệp ngay",
                sample_unit_area_sqft=self.sample_unit_area_sqft,
            )

        if image_area_px <= 0:
            logger.warning("Image area is 0, cannot calculate density")
            return PCIResult(
                pci_value=100.0,
                rating="Good",
                sample_unit_area_sqft=self.sample_unit_area_sqft,
            )

        # Ensure data is loaded
        _ = self.data

        # Build damage records
        damage_records: list[DamageRecord] = []
        for det in detections:
            code = det.get("code", "UNKNOWN")
            bbox = det.get("bbox", (0, 0, 0, 0))
            confidence = det.get("confidence", 0.0)
            mask_area_ratio = det.get("mask_area_sqft", 0.0)  # Fraction of image from segmenter
            has_mask = det.get("has_mask", False)

            # Calculate bbox area
            x1, y1, x2, y2 = bbox
            bbox_area_px = max(0, (x2 - x1) * (y2 - y1))

            # Apply correction factor only when no mask
            if has_mask and mask_area_ratio > 0:
                correction = 1.0  # Mask is precise, no correction
                corrected_area_px = bbox_area_px  # Not used for density
            else:
                correction = BBOX_CORRECTION_FACTORS.get(code, 1.0) if apply_bbox_correction else 1.0
                corrected_area_px = bbox_area_px * correction

            # Calculate density
            density_pct = self.calculate_density(
                corrected_area_px, image_area_px,
                correction_factor=1.0,  # Already applied above
                mask_area_ratio=mask_area_ratio if has_mask else 0.0,
            )

            # Assign severity
            severity = self.assign_severity(code, density_pct)

            # Look up deduct value
            deduct_value = self.lookup_deduct_value(code, severity, density_pct)

            # Compute area in sqft
            if has_mask and mask_area_ratio > 0:
                area_sqft = round(mask_area_ratio * self.sample_unit_area_sqft, 2)
            else:
                area_sqft = round(corrected_area_px / image_area_px * self.sample_unit_area_sqft, 2)

            record = DamageRecord(
                code=code,
                severity=severity,
                density_pct=round(density_pct, 4),
                deduct_value=round(deduct_value, 2),
                bbox_area_sqft=round(bbox_area_px / image_area_px * self.sample_unit_area_sqft, 2),
                corrected_area_sqft=area_sqft,
                confidence=confidence,
            )
            damage_records.append(record)
            source = "mask" if (has_mask and mask_area_ratio > 0) else "bbox"
            logger.debug(
                f"  {code} {severity}: density={density_pct:.2f}%, "
                f"dv={deduct_value:.1f}, source={source}, "
                f"bbox_px={bbox_area_px:.0f}"
            )

        # Calculate CDV
        deduct_values = [r.deduct_value for r in damage_records]
        cdv, q, tdv = self.calculate_cdv(deduct_values)

        # Calculate PCI
        pci_value = max(0.0, 100.0 - cdv)

        # Classify rating
        rating = self.classify_rating(pci_value)

        # Get maintenance recommendation
        action, detail = self.get_maintenance(rating)

        result = PCIResult(
            pci_value=round(pci_value, 1),
            rating=rating,
            maintenance_action=action,
            maintenance_detail=detail,
            cdv=round(cdv, 1),
            tdv=round(tdv, 1),
            q=q,
            damages=damage_records,
            sample_unit_area_sqft=self.sample_unit_area_sqft,
        )

        logger.info(
            f"PCI = {result.pci_value} ({result.rating}), "
            f"CDV={result.cdv}, q={result.q}, TDV={result.tdv}, "
            f"damages={len(damage_records)}"
        )

        return result

    def calculate_section_pci(
        self, sample_results: list[PCIResult]
    ) -> dict[str, Any]:
        """Calculate section-level PCI as weighted average of sample units.

        Args:
            sample_results: List of PCIResult for each sample unit.

        Returns:
            Dict with section PCI, rating, and per-unit breakdown.
        """
        if not sample_results:
            return {
                "section_pci": 100.0,
                "rating": "Good",
                "num_units": 0,
            }

        # Simple average (equal weight per sample unit)
        avg_pci = sum(r.pci_value for r in sample_results) / len(sample_results)
        rating = self.classify_rating(avg_pci)
        action, detail = self.get_maintenance(rating)

        return {
            "section_pci": round(avg_pci, 1),
            "rating": rating,
            "maintenance_action": action,
            "maintenance_detail": detail,
            "num_units": len(sample_results),
            "unit_values": [r.pci_value for r in sample_results],
        }
