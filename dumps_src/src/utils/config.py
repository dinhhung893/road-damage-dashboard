"""JSON configuration loader/saver.

Config file: config/default.json
Persists user preferences across sessions (not QSettings/registry).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils.logging_setup import get_logger

logger = get_logger("config")

_DEFAULT_CONFIG_PATH = Path("config/default.json")

_DEFAULT_CONFIG: dict[str, Any] = {
    "model_path": "models/yolo-rdd2022-benchmark/yolo12s_seed0_best.pt",
    "confidence": 0.15,
    "device": "cpu",
    "sample_unit_area_sqft": 5000,
    "pci_data_path": "data/pci_astm_d6433.json",
    "output_dir": "outputs",
    "language": "vi",
}


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load config from JSON file, falling back to defaults.

    Args:
        config_path: Path to config JSON. Defaults to config/default.json.

    Returns:
        Config dict with defaults merged.
    """
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH

    config = dict(_DEFAULT_CONFIG)

    if path.exists():
        logger.info(f"Loading config: {path}")
        with open(path, encoding="utf-8") as f:
            user_config = json.load(f)
        config.update(user_config)
    else:
        logger.info(f"Config not found at {path}, using defaults")

    return config


def save_config(
    config: dict[str, Any],
    config_path: str | Path | None = None,
) -> None:
    """Save config to JSON file.

    Args:
        config: Config dict to save.
        config_path: Path to save. Defaults to config/default.json.
    """
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving config: {path}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
