"""Engine bridge — import dumps engine modules into adaptive app.

Adds dumps/src to sys.path so we can reuse detector.py, pci.py, segmenter.py
without copying code. Models and PCI data stay in dumps/.

Cross-platform: auto-detects dumps root on Windows (local) and Linux (Colab).
Override via env var DUMPS_ROOT if layout differs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Auto-detect dumps root — works on Windows (local) and Linux (Colab)
# Priority: (1) DUMPS_ROOT env var, (2) sibling of adaptive/, (3) common Colab paths
def _find_dumps_root() -> Path:
    env = os.environ.get("DUMPS_ROOT")
    if env:
        p = Path(env)
        if p.exists() and (p / "src" / "engine").exists():
            return p
    # adaptive is at <root>/adaptive, dumps should be at <root>/dumps
    # On Colab git clone: repo has dumps_src/ (engine source only, models download separately)
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "dumps",                          # sibling of adaptive (Windows: D:\Antigravity\New folder\dumps)
        here / "dumps",                                  # nested inside adaptive
        here / "dumps_src",                              # git repo: dumps_src/ has src/ + data/ (no models)
        Path("/content/drive/MyDrive/New folder/dumps"), # Colab Drive mount (common)
        Path("/content/dumps"),                          # Colab direct upload
        Path("/content/adaptive/dumps"),                 # Colab nested
        Path("/content/repo/dumps_src"),                 # Colab git clone: repo has dumps_src/
    ]
    for c in candidates:
        if c.exists() and (c / "src" / "engine").exists():
            return c
    # Fallback: Windows hardcoded (last resort)
    win = Path(r"D:\Antigravity\New folder\dumps")
    if win.exists() and (win / "src" / "engine").exists():
        return win
    raise FileNotFoundError(
        "dumps/ root not found. Set DUMPS_ROOT env var or ensure dumps/ is sibling of adaptive/. "
        f"Searched: {[str(c) for c in candidates]}"
    )

_DUMPS_ROOT = _find_dumps_root()
_DUMPS_SRC = _DUMPS_ROOT / "src"

# Insert dumps root (parent of src/) so `src.engine.detector` resolves as a package
if str(_DUMPS_ROOT) not in sys.path:
    sys.path.insert(0, str(_DUMPS_ROOT))

# Re-export engines
from src.engine.detector import RoadDamageDetector, DetectionResult, Detection  # noqa: E402
from src.engine.pci import PCIEngine, PCIResult, DamageRecord  # noqa: E402

# Default paths (resolve relative to dumps root)
DEFAULT_MODEL_PATH = _DUMPS_ROOT / "models" / "yolo-rdd2022-benchmark" / "yolo12s_seed0_best.pt"
DEFAULT_PCI_DATA = _DUMPS_ROOT / "data" / "pci_astm_d6433.json"
DEFAULT_FASTSAM_S = _DUMPS_ROOT / "models" / "FastSAM-s.pt"
DEFAULT_FASTSAM_X = _DUMPS_ROOT / "models" / "FastSAM-x.pt"
DUMPS_SAMPLES = _DUMPS_ROOT / "data" / "samples"


def make_detector(model_path: str | Path | None = None, confidence: float = 0.15, device: str = "cpu") -> RoadDamageDetector:
    """Create a RoadDamageDetector with dumps default model path."""
    mp = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    if not mp.exists():
        # Fallback: search for any yolo12s*.pt in dumps/models
        for candidate in (_DUMPS_ROOT / "models").rglob("yolo12s*.pt"):
            mp = candidate
            break
        else:
            raise FileNotFoundError(
                f"Model not found: {mp}. Run dumps/scripts/download_model.py first."
            )
    return RoadDamageDetector(model_path=mp, confidence=confidence, device=device)


def make_pci_engine(pci_data_path: str | Path | None = None, sample_unit_area_sqft: float = 5000.0) -> PCIEngine:
    """Create a PCIEngine with dumps default PCI data path."""
    pp = Path(pci_data_path) if pci_data_path else DEFAULT_PCI_DATA
    return PCIEngine(pci_data_path=pp, sample_unit_area_sqft=sample_unit_area_sqft)


def detections_to_pci_input(detection_result: DetectionResult) -> list[dict]:
    """Convert DetectionResult.detections into the dict list PCIEngine.calculate_pci expects."""
    out = []
    for d in detection_result.pci_detections:
        out.append({
            "code": d.code,
            "bbox": d.bbox,
            "confidence": d.confidence,
            "class_name": d.class_name,
            "has_mask": d.has_mask,
            "mask_area_sqft": d.mask_area_sqft,
        })
    return out


# ASTM code → Vietnamese label
CODE_VN = {
    "D00": "Nứt dọc (Longitudinal)",
    "D10": "Nứt ngang (Transverse)",
    "D20": "Nứt da cá sấu (Alligator)",
    "D40": "Ổ gà (Pothole)",
}

# ASTM code → bbox color (BGR for OpenCV, RGB for web)
CODE_COLORS_RGB = {
    "D00": (231, 76, 60),    # red
    "D10": (52, 152, 219),   # blue
    "D20": (241, 196, 15),   # yellow
    "D40": (155, 89, 182),   # purple
}
CODE_COLORS_BGR = {
    "D00": (60, 76, 231),
    "D10": (219, 152, 52),
    "D20": (15, 196, 241),
    "D40": (182, 89, 155),
}
