"""Road Damage Assessment System — Web Dashboard (Streamlit).

13-pillar completeness framework:
- 5-step pipeline: Thu thập → Phát hiện → Đánh giá → Báo cáo → Khuyến nghị
- Multi-input: image, batch folder, video, RTSP/HLS/MJPEG CCTV, clipboard, CLI
- Multi-output: annotated PNG/JPEG+legend, CSV, JSON, PDF ASTM, batch PDF, SQLite, settings JSON, clipboard
- Localization: VI (primary) / EN
- Theme: dark/light
- Resilience: pre-flight check, auto-save session, batch resume, crash recovery

Tái sử dụng engine từ dumps/ qua engine_bridge.
"""

from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

import engine_bridge as eb
from engine_bridge import CODE_VN, CODE_COLORS_RGB, CODE_COLORS_BGR

# =============================================================================
# Page config
# =============================================================================
st.set_page_config(
    page_title="Hệ thống Đánh giá Hư hỏng Mặt đường",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
    .main .block-container { max-width: 1500px; padding-top: 1rem; padding-bottom: 1rem; }
    h1, h2, h3 { color: #1a1a2e; }
    .stMetric { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 10px; }
    .pci-gauge { text-align: center; padding: 0.5rem; border-radius: 12px; }
    @keyframes needleSweep { 0% { transform: rotate(-90deg); transform-origin: 110px 110px; } 100% { transform: rotate(0deg); transform-origin: 110px 110px; } }
    .pci-gauge svg line[stroke="#2c3e50"] { animation: needleSweep 0.8s ease-out; }
    @keyframes fadeInUp { 0% { opacity: 0; transform: translateY(8px); } 100% { opacity: 1; transform: translateY(0); } }
    .stMetric { animation: fadeInUp 0.4s ease-out; }
    .damage-tag { display: inline-block; padding: 3px 10px; border-radius: 14px; color: white; font-size: 0.82em; margin: 2px; font-weight: 500; }
    .pipeline-step { background: rgba(41, 128, 185, 0.12); border-left: 4px solid #2980b9; padding: 8px 12px; margin: 4px 0; border-radius: 4px; font-size: 0.9em; color: var(--text-color); }
    .pipeline-step strong { color: inherit; }
    .pipeline-step.active { background: rgba(40, 167, 69, 0.15); border-left-color: #28a745; }
    .pipeline-step.pending { background: rgba(255, 193, 7, 0.12); border-left-color: #ffc107; opacity: 0.7; }
    .severity-low { background: #e8f5e9; color: #2e7d32; }
    .severity-medium { background: #fff8e1; color: #f57c00; }
    .severity-high { background: #ffebee; color: #c62828; }
    .kbd { display: inline-block; padding: 1px 6px; background: #eee; border: 1px solid #ccc; border-radius: 3px; font-family: monospace; font-size: 0.85em; }
    div[data-testid="stSidebar"] { background: #f8f9fa; }
    .stAlert { border-radius: 8px; }
    .metric-card { background: white; border-radius: 8px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


# =============================================================================
# Strings — VI (primary) / EN (port từ dumps/src/ui/strings.py)
# =============================================================================
_STRINGS = {
    "vi": {
        "app_title": "Hệ thống Đánh giá Hư hỏng Mặt đường",
        "app_subtitle": "Phát hiện hư hỏng & Tính chỉ số PCI (ASTM D6433)",
        "tab_image": "📷 Ảnh đơn",
        "tab_batch": "📁 Batch ảnh",
        "tab_video": "🎬 Video",
        "tab_stream": "📡 Stream/CCTV",
        "tab_report": "📄 Báo cáo",
        "tab_history": "🗄️ Lịch sử",
        "tab_settings": "⚙️ Cài đặt",
        "tab_about": "ℹ️ Giới thiệu",
        "pipeline_collect": "Thu thập",
        "pipeline_detect": "Phát hiện",
        "pipeline_assess": "Đánh giá",
        "pipeline_report": "Báo cáo",
        "pipeline_recommend": "Khuyến nghị",
        "type_D00": "Vết nứt dọc",
        "type_D10": "Vết nứt ngang",
        "type_D20": "Vết nứt da cá",
        "type_D40": "Ổ gà",
        "severity_Low": "Thấp",
        "severity_Medium": "Trung bình",
        "severity_High": "Cao",
        "rating_Good": "Tốt",
        "rating_Satisfactory": "Hài lòng",
        "rating_Fair": "Trung bình",
        "rating_Poor": "Kém",
        "rating_Very Poor": "Rất kém",
        "rating_Failed": "Hỏng",
    },
    "en": {
        "app_title": "Road Damage Assessment System",
        "app_subtitle": "Damage Detection & PCI Calculation (ASTM D6433)",
        "tab_image": "📷 Single Image",
        "tab_batch": "📁 Batch",
        "tab_video": "🎬 Video",
        "tab_stream": "📡 Stream/CCTV",
        "tab_report": "📄 Report",
        "tab_history": "🗄️ History",
        "tab_settings": "⚙️ Settings",
        "tab_about": "ℹ️ About",
        "pipeline_collect": "Collect",
        "pipeline_detect": "Detect",
        "pipeline_assess": "Assess",
        "pipeline_report": "Report",
        "pipeline_recommend": "Recommend",
        "type_D00": "Longitudinal Crack",
        "type_D10": "Transverse Crack",
        "type_D20": "Alligator Crack",
        "type_D40": "Pothole",
        "severity_Low": "Low",
        "severity_Medium": "Medium",
        "severity_High": "High",
        "rating_Good": "Good",
        "rating_Satisfactory": "Satisfactory",
        "rating_Fair": "Fair",
        "rating_Poor": "Poor",
        "rating_Very Poor": "Very Poor",
        "rating_Failed": "Failed",
    },
}


def _t(key: str) -> str:
    """Translate a key by current session language."""
    lang = st.session_state.get("lang", "vi")
    return _STRINGS.get(lang, _STRINGS["vi"]).get(key, key)


def _type_name(code: str) -> str:
    return _t(f"type_{code}") if code in ("D00", "D10", "D20", "D40") else code


def _severity_name(sev: str) -> str:
    return _t(f"severity_{sev}") if sev in ("Low", "Medium", "High") else sev


def _rating_name(rating: str) -> str:
    return _t(f"rating_{rating}") if rating in (
        "Good", "Satisfactory", "Fair", "Poor", "Very Poor", "Failed"
    ) else rating


# =============================================================================
# Session state defaults
# =============================================================================
_ss = st.session_state
_ss.setdefault("lang", "vi")
_ss.setdefault("history", [])  # list of dicts: {ts, source, file, detections, pci, rating, infer_ms}
_ss.setdefault("last_detection", None)  # cache last DetectionResult
_ss.setdefault("last_pci", None)  # cache last PCIResult
_ss.setdefault("last_pil", None)  # cache last PIL image
_ss.setdefault("last_annotated", None)  # cache last annotated PIL
# SQLite DB path — cross-platform (Colab Linux uses /content, Windows uses temp)
import os as _os
_db_dir = "/content" if _os.path.isdir("/content") else tempfile.gettempdir()
_ss.setdefault("db_path", str(Path(_db_dir) / "road_damage_history.sqlite"))


# =============================================================================
# Cache engines (load once, reuse across interactions)
# =============================================================================
@st.cache_resource
def get_detector(confidence: float, device: str):
    return eb.make_detector(confidence=confidence, device=device)


@st.cache_resource
def get_pci_engine(sample_unit_area_sqft: float):
    return eb.make_pci_engine(sample_unit_area_sqft=sample_unit_area_sqft)


# =============================================================================
# SQLite persistence (Dữ liệu pillar)
# =============================================================================
def _db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(st.session_state["db_path"], check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            source TEXT NOT NULL,
            file_name TEXT,
            detections INTEGER,
            pci REAL,
            rating TEXT,
            inference_ms REAL,
            det_json TEXT,
            pci_json TEXT
        )
    """)
    conn.commit()
    return conn


def _save_history(source: str, file_name: str, det_result, pci_result):
    conn = _db_conn()
    conn.execute(
        "INSERT INTO analyses (ts, source, file_name, detections, pci, rating, inference_ms, det_json, pci_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.now().isoformat(timespec="seconds"),
            source,
            file_name,
            len(det_result.detections),
            pci_result.pci_value,
            pci_result.rating,
            det_result.inference_time_ms,
            json.dumps([{"code": d.code, "conf": d.confidence, "bbox": list(d.bbox)} for d in det_result.detections]),
            json.dumps({"pci": pci_result.pci_value, "rating": pci_result.rating, "cdv": pci_result.cdv, "tdv": pci_result.tdv, "q": pci_result.q}),
        ),
    )
    conn.commit()
    conn.close()
    st.session_state["history"].append({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "file": file_name,
        "detections": len(det_result.detections),
        "pci": pci_result.pci_value,
        "rating": pci_result.rating,
        "infer_ms": det_result.inference_time_ms,
    })


# (Helper functions continue in next edit: annotate_image_pil, pci_gauge_html, pipeline indicator, pre-flight check)


# =============================================================================
# Annotation — draw bbox + labels + legend on PIL image
# =============================================================================
def annotate_image_pil(image: Image.Image, detection_result, show_labels: bool = True, show_legend: bool = True) -> Image.Image:
    """Draw bounding boxes + labels + legend on a PIL image. Returns new PIL image."""
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    # Font fallback chain: Windows arial → Linux DejaVu → default
    font = None
    for font_path in ["arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf"]:
        try:
            font = ImageFont.truetype(font_path, max(12, img.height // 45))
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()
    font_small = font

    for det in detection_result.detections:
        x1, y1, x2, y2 = det.bbox
        color = CODE_COLORS_RGB.get(det.code, (100, 100, 100))
        lw = max(2, img.width // 400)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=lw)
        if show_labels:
            label = f"{det.code} {det.confidence:.2f}"
            bbox_label = draw.textbbox((x1, max(0, y1 - 18)), label, font=font_small)
            draw.rectangle(bbox_label, fill=color)
            draw.text((x1, max(0, y1 - 18)), label, fill="white", font=font_small)

    if show_legend and detection_result.detections:
        codes_present = sorted({d.code for d in detection_result.detections})
        lx, ly = img.width - 180, 10
        draw.rectangle([lx - 8, ly - 6, lx + 170, ly + 6 + 22 * len(codes_present)], fill=(0, 0, 0, 200), outline=(255, 255, 255))
        for i, code in enumerate(codes_present):
            rgb = CODE_COLORS_RGB.get(code, (100, 100, 100))
            draw.rectangle([lx, ly + i * 22, lx + 16, ly + i * 22 + 14], fill=rgb)
            draw.text((lx + 22, ly + i * 22), f"{code} {_type_name(code)}", fill="white", font=font_small)
    return img


# =============================================================================
# PCI gauge — semicircular SVG with 6 color bands + needle
# =============================================================================
def pci_gauge_html(pci_value: float, rating: str, color: str) -> str:
    """Render a semicircular PCI gauge as HTML/SVG. Ports pci_gauge.py logic."""
    angle = 180 - (pci_value / 100.0) * 180  # PCI 100 = left (180°), PCI 0 = right (0°)
    rad = np.deg2rad(angle)
    cx, cy, r = 110, 110, 90
    x = cx + r * np.cos(rad)
    y = cy - r * np.sin(rad)
    rating_vn = _rating_name(rating)
    return f"""
    <div class="pci-gauge">
      <svg width="220" height="135" viewBox="0 0 220 135">
        <path d="M {cx-r} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" fill="none" stroke="#8e44ad" stroke-width="14" stroke-dasharray="42.4 9999"/>
        <path d="M {cx-r+44} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" fill="none" stroke="#e74c3c" stroke-width="14" stroke-dasharray="42.4 9999" stroke-dashoffset="-47.1"/>
        <path d="M {cx-r+88} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" fill="none" stroke="#e67e22" stroke-width="14" stroke-dasharray="42.4 9999" stroke-dashoffset="-94.2"/>
        <path d="M {cx-r+132} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" fill="none" stroke="#f1c40f" stroke-width="14" stroke-dasharray="42.4 9999" stroke-dashoffset="-141.3"/>
        <path d="M {cx-r+176} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" fill="none" stroke="#27ae60" stroke-width="14" stroke-dasharray="42.4 9999" stroke-dashoffset="-188.4"/>
        <line x1="{cx}" y1="{cy}" x2="{x:.2f}" y2="{y:.2f}" stroke="#2c3e50" stroke-width="3" stroke-linecap="round"/>
        <circle cx="{cx}" cy="{cy}" r="6" fill="#2c3e50"/>
        <text x="{cx - r - 8}" y="{cy + 14}" font-size="10" fill="#666">0</text>
        <text x="{cx + r - 4}" y="{cy + 14}" font-size="10" fill="#666">100</text>
        <text x="{cx}" y="{cy + 28}" text-anchor="middle" font-size="28" font-weight="bold" fill="{color}">{pci_value:.1f}</text>
        <text x="{cx}" y="{cy + 48}" text-anchor="middle" font-size="12" fill="{color}" font-weight="600">{rating_vn}</text>
      </svg>
    </div>
    """


# =============================================================================
# Pipeline indicator — 5-step (Thu thập → Phát hiện → Đánh giá → Báo cáo → Khuyến nghị)
# =============================================================================
def pipeline_indicator(active_step: int) -> None:
    """Render 5-step pipeline horizontal indicator. active_step: 1-5 (0 = none started)."""
    steps = [
        ("pipeline_collect", "📥"),
        ("pipeline_detect", "🔍"),
        ("pipeline_assess", "📐"),
        ("pipeline_report", "📄"),
        ("pipeline_recommend", "🛠️"),
    ]
    cols = st.columns(len(steps))
    for i, ((key, emoji), col) in enumerate(zip(steps, cols), 1):
        cls = "active" if i == active_step else ("pipeline-step" if i < active_step else "pending")
        if i < active_step:
            cls = "active"
        elif i == active_step:
            cls = "active"
        else:
            cls = "pending"
        col.markdown(
            f'<div class="pipeline-step {cls}">{emoji} <strong>{i}. {_t(key)}</strong></div>',
            unsafe_allow_html=True,
        )


# =============================================================================
# Pre-flight check (Phục hồi pillar) — verify model + PCI data exist before inference
# =============================================================================
def preflight_check() -> tuple[bool, list[str]]:
    """Verify engine dependencies are present. Returns (ok, warnings)."""
    warnings = []
    ok = True
    if not eb.DEFAULT_MODEL_PATH.exists():
        warnings.append(f"⚠ Model không tìm thấy: `{eb.DEFAULT_MODEL_PATH}`. Chạy `dumps/scripts/download_model.py`.")
        ok = False
    if not eb.DEFAULT_PCI_DATA.exists():
        warnings.append(f"⚠ Dữ liệu PCI không tìm thấy: `{eb.DEFAULT_PCI_DATA}`.")
        ok = False
    samples = list(eb.DUMPS_SAMPLES.glob("*.jpg")) if eb.DUMPS_SAMPLES.exists() else []
    if not samples:
        warnings.append("⚠ Không có ảnh mẫu trong `dumps/data/samples/`.")
    return ok, warnings


# =============================================================================
# Source input helpers — Upload / Google Drive / URL direct
# =============================================================================
def _download_from_url(url: str, suffix: str = ".jpg") -> Path:
    """Download file from URL to temp file. Returns path."""
    import urllib.request
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        urllib.request.urlretrieve(url, tmp.name)
        return Path(tmp.name)
    except Exception as e:
        Path(tmp.name).unlink(missing_ok=True)
        raise RuntimeError(f"URL download failed: {e}")


def _list_drive_images(folder_path: str) -> list[str]:
    """List image files in a Google Drive mounted folder (Colab: /content/drive/MyDrive/...)."""
    p = Path(folder_path)
    if not p.exists():
        return []
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    return sorted([str(f) for f in p.iterdir() if f.suffix.lower() in exts])


def _list_drive_videos(folder_path: str) -> list[str]:
    """List video files in a Google Drive mounted folder."""
    p = Path(folder_path)
    if not p.exists():
        return []
    exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    return sorted([str(f) for f in p.iterdir() if f.suffix.lower() in exts])


def _is_colab() -> bool:
    """Check if running on Colab (Linux + /content exists). Drive may not be mounted yet."""
    import os as _os
    return _os.path.isdir("/content")


def _is_drive_mounted() -> bool:
    """Check if Google Drive is mounted at /content/drive/MyDrive."""
    import os as _os
    return _os.path.isdir("/content/drive/MyDrive")


def _source_selector(key_suffix: str = "", file_type: str = "image") -> tuple[str, Path | None, Image.Image | None, str]:
    """Render source input selector. Returns (source_label, file_path, pil_image, file_name).
    file_type: 'image' or 'video' or 'batch'
    """
    lang = st.session_state["lang"]
    is_vi = lang == "vi"

    source_options = {
        "upload": "📤 " + ("Tải lên" if is_vi else "Upload"),
        "url": "🔗 " + ("URL trực tiếp" if is_vi else "Direct URL"),
        "drive": "📁 " + ("Google Drive" if is_vi else "Google Drive"),
    }
    source = st.radio(
        "Nguồn đầu vào" if is_vi else "Input source",
        options=list(source_options.keys()),
        format_func=lambda x: source_options[x],
        horizontal=True,
        key=f"src_{key_suffix}",
    )

    file_path = None
    pil_img = None
    file_name = ""

    if source == "upload":
        if file_type == "image":
            uploaded = st.file_uploader(
                "Tải lên ảnh (jpg, png, bmp, tiff, webp)" if is_vi else "Upload image",
                type=["jpg", "jpeg", "png", "bmp", "tiff", "webp"],
                key=f"up_img_{key_suffix}",
            )
            if uploaded:
                pil_img = Image.open(uploaded)
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                pil_img.convert("RGB").save(tmp.name, "JPEG")
                file_path = Path(tmp.name)
                file_name = uploaded.name
        elif file_type == "video":
            uploaded = st.file_uploader(
                "Tải lên video (mp4, avi, mov)" if is_vi else "Upload video",
                type=["mp4", "avi", "mov", "mkv", "webm"],
                key=f"up_vid_{key_suffix}",
            )
            if uploaded:
                tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                tmp.write(uploaded.read())
                file_path = Path(tmp.name)
                file_name = uploaded.name

    elif source == "url":
        url = st.text_input(
            "URL (https://...)" if is_vi else "URL",
            placeholder="https://example.com/road.jpg",
            key=f"url_{key_suffix}",
        )
        if url:
            suffix = ".mp4" if file_type == "video" else ".jpg"
            try:
                file_path = _download_from_url(url, suffix=suffix)
                file_name = url.split("/")[-1][:50] or "url_input"
                if file_type == "image":
                    pil_img = Image.open(file_path)
                st.success(f"✓ {('Đã tải' if is_vi else 'Downloaded')}: {file_name}")
            except Exception as e:
                st.error(f"❌ {e}")

    elif source == "drive":
        if not _is_colab():
            st.warning("⚠️ " + ("Google Drive chỉ khả dụng trên Colab." if is_vi else "Google Drive only on Colab."))
        elif not _is_drive_mounted():
            # Drive not mounted — must mount from Colab cell (drive.mount() needs Colab kernel, not subprocess)
            st.info("� " + (
                "Google Drive chưa mount. **Chạy cell '2.5. Mount Google Drive'** trong `colab_setup.ipynb` trước, sau đó refresh dashboard."
                if is_vi else
                "Drive not mounted. **Run cell '2.5. Mount Google Drive'** in `colab_setup.ipynb` first, then refresh dashboard."
            ))
            st.code("from google.colab import drive\ndrive.mount('/content/drive')", language="python")
        else:
            # Drive mounted — show folder browser
            default_path = "/content/drive/MyDrive"
            drive_path = st.text_input(
                "Đường dẫn thư mục Drive" if is_vi else "Drive folder path",
                value=default_path,
                key=f"drv_{key_suffix}",
            )
            if file_type == "batch":
                files = _list_drive_images(drive_path)
                if files:
                    selected = st.multiselect(
                        f"Chọn ảnh ({len(files)} tìm thấy)" if is_vi else f"Select images ({len(files)} found)",
                        options=files,
                        format_func=lambda x: Path(x).name,
                        key=f"drv_sel_{key_suffix}",
                    )
                    if selected:
                        file_path = selected  # list of paths for batch
                        file_name = f"drive_batch_{len(selected)}"
                else:
                    st.info(f"📭 {('Không có ảnh trong' if is_vi else 'No images in')} {drive_path}")
            elif file_type == "video":
                files = _list_drive_videos(drive_path)
                if files:
                    selected = st.selectbox(
                        f"Chọn video ({len(files)})" if is_vi else f"Select video ({len(files)})",
                        options=[""] + files,
                        format_func=lambda x: Path(x).name if x else f"— {('chọn' if is_vi else 'select')} —",
                        key=f"drv_sel_{key_suffix}",
                    )
                    if selected:
                        file_path = Path(selected)
                        file_name = Path(selected).name
                else:
                    st.info(f"📭 {('Không có video trong' if is_vi else 'No videos in')} {drive_path}")
            else:  # image
                files = _list_drive_images(drive_path)
                if files:
                    selected = st.selectbox(
                        f"Chọn ảnh ({len(files)})" if is_vi else f"Select image ({len(files)})",
                        options=[""] + files,
                        format_func=lambda x: Path(x).name if x else f"— {('chọn' if is_vi else 'select')} —",
                        key=f"drv_sel_{key_suffix}",
                    )
                    if selected:
                        file_path = Path(selected)
                        file_name = Path(selected).name
                        pil_img = Image.open(file_path)
                else:
                    st.info(f"📭 {('Không có ảnh trong' if is_vi else 'No images in')} {drive_path}")

    return source, file_path, pil_img, file_name


# =============================================================================
# Detection runner — central inference with PCI + history persistence
# =============================================================================
def run_inference(image_path, source: str, file_name: str, do_segmentation: bool = False):
    """Run detection + PCI + save history. Returns (det_result, pci_result, elapsed_ms)."""
    detector = get_detector(st.session_state["confidence"], st.session_state["device"])
    pci_engine = get_pci_engine(st.session_state["sample_unit_area"])
    t0 = time.time()
    det_result = detector.detect(image_path)
    t1 = time.time()
    pci_input = eb.detections_to_pci_input(det_result)
    pci_result = pci_engine.calculate_pci(
        pci_input,
        image_area_px=det_result.image_shape[0] * det_result.image_shape[1],
        apply_bbox_correction=True,
    )
    _save_history(source, file_name, det_result, pci_result)
    return det_result, pci_result, (t1 - t0) * 1000


def detections_to_rows(det_result) -> list[dict]:
    """Convert DetectionResult to dataframe rows (detailed)."""
    rows = []
    for i, det in enumerate(det_result.detections, 1):
        x1, y1, x2, y2 = det.bbox
        rows.append({
            "#": i,
            "Mã ASTM": det.code,
            "Loại hư hỏng": _type_name(det.code),
            "Confidence": f"{det.confidence:.3f}",
            "Bbox (x1,y1,x2,y2)": f"({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f})",
            "Tính vào PCI": "✓" if det.include_in_pci else "✗",
        })
    return rows


def pci_damage_rows(pci_result) -> list[dict]:
    """PCI damage records table (per-distress PCI breakdown)."""
    rows = []
    for dmg in pci_result.damages:
        rows.append({
            "Mã": dmg.code,
            "Loại": _type_name(dmg.code),
            "Mức độ": _severity_name(dmg.severity),
            "Mật độ (%)": f"{dmg.density_pct:.3f}",
            "GT khấu trừ": f"{dmg.deduct_value:.2f}",
            "Diện tích (ft²)": f"{dmg.corrected_area_sqft:.2f}",
            "Confidence": f"{dmg.confidence:.2f}",
        })
    return rows


def damage_summary_html(det_result) -> str:
    """Compact colored tag summary by class count."""
    counts = Counter(d.code for d in det_result.pci_detections)
    if not counts:
        return "<em>Không phát hiện hư hỏng nào ở ngưỡng hiện tại.</em>"
    html = ""
    for code, count in sorted(counts.items()):
        rgb = CODE_COLORS_RGB.get(code, (100, 100, 100))
        hex_c = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        html += f'<span class="damage-tag" style="background:{hex_c}">{code} · {_type_name(code)}: {count}</span>'
    return html


# (Sidebar + tabs continue in next edits)


# =============================================================================
# Sidebar — Settings (Tùy biến pillar: language, theme, confidence, area, device, segmentation)
# =============================================================================
with st.sidebar:
    st.markdown("## ⚙️ " + ("Cài đặt" if st.session_state["lang"] == "vi" else "Settings"))

    # Language toggle (theme is handled by Streamlit native menu — Settings > Theme: System/Light/Dark)
    lang_opts = {"vi": "🇻🇳 Tiếng Việt", "en": "🇬🇧 English"}
    st.session_state["lang"] = st.selectbox(
        "🌐 Ngôn ngữ / Language",
        options=list(lang_opts.keys()),
        format_func=lambda x: lang_opts[x],
        key="lang_select",
    )

    st.markdown("---")
    st.markdown("### 🔬 " + ("Tham số inference" if st.session_state["lang"] == "vi" else "Inference params"))

    st.session_state["confidence"] = st.slider(
        "Confidence threshold" if st.session_state["lang"] == "en" else "Ngưỡng tin cậy",
        min_value=0.05, max_value=0.50, value=0.15, step=0.01,
        help="RDD2022 benchmark khuyến nghị 0.10–0.20",
    )

    st.session_state["sample_unit_area"] = st.number_input(
        "Diện tích mẫu đơn vị (ft²)" if st.session_state["lang"] == "en" else "Sample unit area (sq ft)",
        min_value=500.0, max_value=20000.0, value=5000.0, step=500.0,
        help="ASTM D6433 mặc định 5000 ft² (~465 m²)",
    )

    st.session_state["device"] = st.selectbox(
        "Thiết bị inference" if st.session_state["lang"] == "vi" else "Inference device",
        options=["cpu", "cuda"],
        format_func=lambda x: "CPU" if x == "cpu" else "CUDA (GPU)",
    )

    st.session_state["use_segmentation"] = st.checkbox(
        "FastSAM segmentation (T2)" if st.session_state["lang"] == "en" else "Phân vùng FastSAM (T2)",
        value=False,
        help="Bật để tính diện tích chính xác từ mask thay vì bbox proxy",
    )

    st.session_state["show_legend"] = st.checkbox(
        "Hiển thị chú giải (legend)" if st.session_state["lang"] == "vi" else "Show legend",
        value=True,
    )

    st.markdown("---")
    st.markdown("### 🩺 " + ("Kiểm tra hệ thống" if st.session_state["lang"] == "vi" else "System check"))
    pf_ok, pf_warnings = preflight_check()
    if pf_ok:
        st.success("✓ " + ("Sẵn sàng inference" if st.session_state["lang"] == "vi" else "Ready for inference"))
    else:
        for w in pf_warnings:
            st.warning(w)

    st.markdown("---")
    # UTL-01 — Recent files (Tiện ích pillar) — last 10 analyses from SQLite
    st.markdown("### 🕒 " + ("Phân tích gần đây" if st.session_state["lang"] == "vi" else "Recent analyses"))
    try:
        conn = _db_conn()
        recent = pd.read_sql("SELECT ts, file_name, pci, rating FROM analyses ORDER BY ts DESC LIMIT 10", conn)
        conn.close()
        if not recent.empty:
            for _, row in recent.iterrows():
                st.caption(f"📁 {row['file_name'][:30]} · PCI {row['pci']:.1f} ({row['rating']}) · {row['ts'][11:]}")
        else:
            st.caption("—" + (" Chưa có phân tích nào" if st.session_state["lang"] == "vi" else " No analyses yet"))
    except Exception:
        st.caption("—" + (" Chưa có DB" if st.session_state["lang"] == "vi" else " No DB"))

    st.markdown("---")
    st.caption("ĐH Công nghệ GTVT · Viện CN ĐS&GTVT · TT BIM & AI")


# =============================================================================
# Header
# =============================================================================
st.markdown(f"""
# 🛣️ {_t('app_title')}
**{_t('app_subtitle')}** · YOLOv12s + FastSAM + ASTM D6433
""")

# Tab structure — 8 tabs (compact, no About/Footer)
TAB_KEYS = ["tab_image", "tab_batch", "tab_video", "tab_stream", "tab_report", "tab_history", "tab_settings", "tab_console"]
# Insert tab_console string
_STRINGS["vi"]["tab_console"] = "📜 Console"
_STRINGS["en"]["tab_console"] = "📜 Console"
tab_objects = st.tabs([_t(k) for k in TAB_KEYS])
tabs = dict(zip(TAB_KEYS, tab_objects))

# (Tab contents continue in next edits)


# =============================================================================
# Tab: Ảnh đơn — full single-image workflow with 5-step pipeline indicator
# =============================================================================
with tabs["tab_image"]:
    st.markdown("### " + ("Phân tích ảnh đơn" if st.session_state["lang"] == "vi" else "Single image analysis"))
    pipeline_indicator(1)

    # Source selector: Upload / URL / Google Drive + sample picker
    src_source, input_path, input_pil, src_name = _source_selector("single", file_type="image")

    # Sample picker (always available — from dumps/data/samples)
    if input_path is None:
        st.markdown("**" + ("Hoặc chọn ảnh mẫu:" if st.session_state["lang"] == "vi" else "Or pick a sample:") + "**")
        sample_files = sorted(eb.DUMPS_SAMPLES.glob("*.jpg")) if eb.DUMPS_SAMPLES.exists() else []
        sample_options = {f.name: f for f in sample_files}
        opts = ["(chọn ...)"] + list(sample_options.keys()) if sample_options else ["(không có ảnh mẫu)"]
        selected_sample = st.selectbox("Ảnh mẫu", options=opts, label_visibility="collapsed", key="sample_single")
        if selected_sample and selected_sample not in ("(chọn ...)", "(không có ảnh mẫu)"):
            input_path = sample_options[selected_sample]
            input_pil = Image.open(input_path)
            src_name = selected_sample
            src_source = "sample"

    if input_path is not None and input_pil is not None:
        pipeline_indicator(2)
        col_orig, col_anno = st.columns(2)
        with col_orig:
            st.markdown("**" + ("Ảnh gốc" if st.session_state["lang"] == "vi" else "Original") + "**")
            st.image(input_pil, use_column_width=True)

        try:
            with st.spinner("Đang chạy inference..." if st.session_state["lang"] == "vi" else "Running inference..."):
                det_result, pci_result, elapsed_ms = run_inference(
                    input_path, "image", src_name,
                    do_segmentation=st.session_state["use_segmentation"],
                )
            annotated = annotate_image_pil(
                input_pil, det_result,
                show_legend=st.session_state["show_legend"],
            )
            st.session_state["last_detection"] = det_result
            st.session_state["last_pci"] = pci_result
            st.session_state["last_pil"] = input_pil
            st.session_state["last_annotated"] = annotated
            st.session_state["last_source"] = src_name

            with col_anno:
                st.markdown("**" + ("Ảnh đã annotate" if st.session_state["lang"] == "vi" else "Annotated") + "**")
                st.image(annotated, use_column_width=True)

            pipeline_indicator(3)

            # Metrics row (Chỉ mục pillar)
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Detections", len(det_result.detections))
            m2.metric("Inference (ms)", f"{det_result.inference_time_ms:.0f}")
            m3.metric("Tổng thời gian (ms)", f"{elapsed_ms:.0f}")
            m4.metric("Kích thước", f"{det_result.image_shape[1]}×{det_result.image_shape[0]}")
            m5.metric("Model", "YOLOv12s")

            # PCI + damage tables
            col_pci, col_table = st.columns([1, 2])
            with col_pci:
                st.markdown("### 📐 " + ("Chỉ số PCI" if st.session_state["lang"] == "vi" else "PCI Index"))
                st.markdown(pci_gauge_html(pci_result.pci_value, pci_result.rating, pci_result.pci_color), unsafe_allow_html=True)
                st.markdown(f"**CDV:** {pci_result.cdv:.2f} | **TDV:** {pci_result.tdv:.2f} | **q:** {pci_result.q}")
                st.markdown(f"**Diện tích mẫu:** {pci_result.sample_unit_area_sqft:.0f} ft² ({pci_result.sample_unit_area_sqft * 0.0929:.1f} m²)")
            with col_table:
                st.markdown("### " + ("Bảng detections" if st.session_state["lang"] == "vi" else "Detections table"))
                rows = detections_to_rows(det_result)
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Không phát hiện hư hỏng nào ở ngưỡng hiện tại.")
                st.markdown(damage_summary_html(det_result), unsafe_allow_html=True)

                # PCI damage records (detailed per-distress)
                if pci_result.damages:
                    with st.expander("📋 " + ("Bản ghi hư hỏng chi tiết (PCI breakdown)" if st.session_state["lang"] == "vi" else "Detailed damage records (PCI breakdown)")):
                        st.dataframe(pd.DataFrame(pci_damage_rows(pci_result)), use_container_width=True, hide_index=True)

                # UTL-02 — Filter detections by class (Tiện ích pillar)
                if det_result.detections:
                    all_codes = sorted({d.code for d in det_result.detections})
                    filter_codes = st.multiselect(
                        "🔍 " + ("Lọc theo loại hư hỏng" if st.session_state["lang"] == "vi" else "Filter by damage type"),
                        options=all_codes,
                        default=all_codes,
                        format_func=lambda c: f"{c} · {_type_name(c)}",
                        key="filter_class_single",
                    )
                    if len(filter_codes) < len(all_codes):
                        filtered_dets = [d for d in det_result.detections if d.code in filter_codes]
                        st.caption(f"Showing {len(filtered_dets)}/{len(det_result.detections)} detections after filter")
                        if filtered_dets:
                            st.dataframe(pd.DataFrame(detections_to_rows(type("X", (), {"detections": filtered_dets})())), use_container_width=True, hide_index=True)

            pipeline_indicator(4)
            # Export buttons (Báo cáo pillar) + OUT-05 clipboard copy
            ex1, ex2, ex3, ex4, ex5 = st.columns(5)
            with ex1:
                buf = io.BytesIO()
                annotated.save(buf, format="PNG")
                st.download_button("📥 Ảnh PNG", buf.getvalue(), file_name=f"{Path(src_name).stem}_annotated.png", mime="image/png")
            with ex2:
                csv_buf = io.StringIO()
                pd.DataFrame(rows).to_csv(csv_buf, index=False)
                st.download_button("📥 CSV detections", csv_buf.getvalue().encode("utf-8"), file_name=f"{Path(src_name).stem}_detections.csv", mime="text/csv")
            with ex3:
                pci_json = json.dumps({
                    "pci": pci_result.pci_value, "rating": pci_result.rating, "cdv": pci_result.cdv,
                    "tdv": pci_result.tdv, "q": pci_result.q,
                    "maintenance": pci_result.maintenance_action,
                    "damages": [{"code": d.code, "severity": d.severity, "density": d.density_pct, "deduct": d.deduct_value} for d in pci_result.damages],
                }, ensure_ascii=False, indent=2)
                st.download_button("📥 JSON PCI", pci_json.encode("utf-8"), file_name=f"{Path(src_name).stem}_pci.json", mime="application/json")
            with ex4:
                if st.button("🔄 " + ("Chạy lại" if st.session_state["lang"] == "vi" else "Re-run"), key="rerun_single"):
                    st.rerun()
            with ex5:
                # OUT-05 — Copy PCI summary to clipboard
                pci_clip = f"PCI={pci_result.pci_value:.1f} ({_rating_name(pci_result.rating)}) | CDV={pci_result.cdv:.2f} | Det={len(det_result.detections)} | {_type_name('D00') if False else ''}".replace(f" | {_type_name('D00') if False else ''}", "")
                st.code(pci_clip, language="text")
                st.caption("📋 " + ("Copy text trên (Ctrl+C)" if st.session_state["lang"] == "vi" else "Copy text above (Ctrl+C)"))

            pipeline_indicator(5)
            # Khuyến nghị bảo dưỡng (Khuyến nghị pillar — DE_XUAT #1, Slide 26)
            st.markdown("### 🛠️ " + ("Khuyến nghị bảo dưỡng" if st.session_state["lang"] == "vi" else "Maintenance recommendation"))
            rec_color = pci_result.pci_color
            st.markdown(f"""
            <div style="border-left: 4px solid {rec_color}; background: #f8f9fa; padding: 12px; border-radius: 4px;">
              <strong style="color: {rec_color};">{_rating_name(pci_result.rating)} (PCI {pci_result.pci_value:.1f})</strong><br/>
              <strong>{pci_result.maintenance_action}</strong><br/>
              <em>{pci_result.maintenance_detail}</em>
            </div>
            """, unsafe_allow_html=True)

        except FileNotFoundError as e:
            st.error(f"Không tìm thấy file: {e}")
            st.info("Chạy `python dumps/scripts/download_model.py` để tải model weights.")
        except Exception as e:
            st.error(f"Lỗi inference: {e}")
    else:
        st.info("👆 " + ("Tải lên ảnh hoặc chọn ảnh mẫu để bắt đầu phân tích." if st.session_state["lang"] == "vi" else "Upload image or pick a sample to start."))


# =============================================================================
# Tab: Batch ảnh — multi-image batch → section-level PCI
# =============================================================================
with tabs["tab_batch"]:
    st.markdown("### " + ("Xử lý hàng loạt ảnh (Batch)" if st.session_state["lang"] == "vi" else "Batch image processing"))
    st.caption("📤 " + (
        "Tải lên nhiều ảnh → batch inference → PCI cấp đoạn đường (section-level) theo ASTM D6433. "
        "ASTM quy định khảo sát nhiều mẫu đơn vị trên 1 đoạn đường → PCI đoạn = trung bình có trọng số."
        if st.session_state["lang"] == "vi" else
        "Upload multiple images → batch inference → section-level PCI per ASTM D6433."
    ))
    pipeline_indicator(1)

    # Source selector for batch: Upload / URL / Google Drive folder
    batch_source, batch_path, _, _ = _source_selector("batch", file_type="batch")
    batch_files = None  # upload file objects
    batch_drive_paths = None  # drive file paths (list)

    if batch_source == "upload":
        batch_files = st.file_uploader(
            "Tải lên nhiều ảnh" if st.session_state["lang"] == "vi" else "Upload multiple images",
            type=["jpg", "jpeg", "png", "bmp", "tiff"],
            accept_multiple_files=True,
            key="batch_images",
        )
        batch_count = len(batch_files) if batch_files else 0
    elif batch_source == "drive" and isinstance(batch_path, list):
        batch_drive_paths = batch_path
        batch_count = len(batch_path)
    else:
        batch_count = 0

    if batch_count > 0:
        st.info(f"📋 {batch_count} " + ("ảnh đã chọn" if st.session_state["lang"] == "vi" else "images selected"))
        col_run, col_clear, col_stride = st.columns([2, 1, 2])
        with col_run:
            run_batch = st.button("🚀 " + ("Chạy batch inference" if st.session_state["lang"] == "vi" else "Run batch"), type="primary")
        with col_stride:
            batch_max = st.number_input("Giới hạn số ảnh (0=tất cả)", 0, 100, 0, 10, key="batch_max")

        if run_batch:
            pipeline_indicator(2)
            # Build unified file list: (name, path, pil_image) from upload or drive
            preloaded = []
            if batch_files:  # upload source
                files_to_process = batch_files[:batch_max] if batch_max > 0 else batch_files
                skeleton = st.empty()
                skeleton.info(f"⏳ {len(files_to_process)} " + ("ảnh đang xử lý." if st.session_state["lang"] == "vi" else "images queued."))
                progress = st.progress(0.0, text="Đang xử lý...")
                st.caption("⚡ " + ("Prefetch: đang tải ảnh trước..." if st.session_state["lang"] == "vi" else "Prefetching..."))
                for f in files_to_process:
                    img = Image.open(f)
                    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    img.convert("RGB").save(tmp.name, "JPEG")
                    preloaded.append((f.name, Path(tmp.name), img))
            elif batch_drive_paths:  # drive source
                files_to_process = batch_drive_paths[:batch_max] if batch_max > 0 else batch_drive_paths
                skeleton = st.empty()
                skeleton.info(f"⏳ {len(files_to_process)} " + ("ảnh đang xử lý." if st.session_state["lang"] == "vi" else "images queued."))
                progress = st.progress(0.0, text="Đang xử lý...")
                for fp in files_to_process:
                    img = Image.open(fp)
                    preloaded.append((Path(fp).name, Path(fp), img))
            else:
                st.error("❌ " + ("Không có ảnh nào được chọn." if st.session_state["lang"] == "vi" else "No images selected."))
                st.stop()
            skeleton.empty()
            results = []
            for i, (fname, tmp_path, img) in enumerate(preloaded):
                try:
                    det_res, pci_res, _ = run_inference(tmp_path, "batch", fname)
                    results.append({"file": fname, "det": det_res, "pci": pci_res, "pil": img})
                except Exception as e:
                    st.warning(f"Lỗi {fname}: {e}")
                progress.progress((i + 1) / len(files_to_process), text=f"Đã xử lý {i+1}/{len(files_to_process)}: {fname}")
            progress.empty()

            if not results:
                st.error("Không có kết quả hợp lệ.")
            else:
                pipeline_indicator(3)
                # Summary table
                st.markdown("### " + ("Kết quả từng ảnh" if st.session_state["lang"] == "vi" else "Per-image results"))
                table_rows = [{
                    "File": r["file"],
                    "Detections": len(r["det"].detections),
                    "PCI": f"{r['pci'].pci_value:.1f}",
                    "Rating": _rating_name(r["pci"].rating),
                    "Inference (ms)": f"{r['det'].inference_time_ms:.0f}",
                } for r in results]
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

                # Section-level PCI
                pci_engine = get_pci_engine(st.session_state["sample_unit_area"])
                try:
                    section_pci = pci_engine.calculate_section_pci([r["pci"] for r in results])
                except Exception:
                    section_pci = None
                if section_pci is not None:
                    col_s1, col_s2 = st.columns([1, 2])
                    with col_s1:
                        st.markdown("### 📐 " + ("PCI cấp đoạn đường" if st.session_state["lang"] == "vi" else "Section-level PCI"))
                        if hasattr(section_pci, "pci_value"):
                            st.markdown(pci_gauge_html(section_pci.pci_value, section_pci.rating, section_pci.pci_color), unsafe_allow_html=True)
                            st.markdown(f"**Khuyến nghị:** {section_pci.maintenance_action}")
                        else:
                            st.metric("PCI đoạn đường", f"{section_pci:.1f}")
                    with col_s2:
                        st.markdown("**Giải thích ASTM D6433:**")
                        st.markdown("""
                        - Mỗi ảnh = 1 mẫu đơn vị (sample unit)
                        - PCI đoạn đường = trung bình có trọng số PCI các mẫu
                        - ASTM yêu cầu khảo sát nhiều mẫu đại diện trên 1 đoạn
                        - Đoạn đường dài 1 đoạn (~100m) → 5-10 ảnh mẫu → 1 PCI đoạn
                        """)

                pipeline_indicator(4)
                # Export batch CSV
                csv_buf = io.StringIO()
                pd.DataFrame(table_rows).to_csv(csv_buf, index=False)
                st.download_button("📥 CSV batch", csv_buf.getvalue().encode("utf-8"), file_name="batch_results.csv", mime="text/csv")

                # Gallery + NAV-01 prev/next batch navigation
                pipeline_indicator(5)
                st.markdown("### " + ("Gallery ảnh đã annotate" if st.session_state["lang"] == "vi" else "Annotated gallery"))

                # NAV-01 — Prev/Next navigation through batch results
                st.session_state.setdefault("batch_nav_idx", 0)
                if st.session_state["batch_nav_idx"] >= len(results):
                    st.session_state["batch_nav_idx"] = 0
                nav_cur = st.session_state["batch_nav_idx"]

                nav_c1, nav_c2, nav_c3, nav_c4 = st.columns([1, 2, 1, 2])
                with nav_c1:
                    if st.button("⬅ " + ("Trước" if st.session_state["lang"] == "vi" else "Prev"), key="batch_prev", disabled=(nav_cur == 0)):
                        st.session_state["batch_nav_idx"] = max(0, nav_cur - 1)
                        st.rerun()
                with nav_c2:
                    st.markdown(f"**{nav_cur + 1}/{len(results)}** — {results[nav_cur]['file'][:40]} · PCI {results[nav_cur]['pci'].pci_value:.1f}")
                with nav_c3:
                    if st.button("Sau ➡" if st.session_state["lang"] == "vi" else "Next", key="batch_next", disabled=(nav_cur >= len(results) - 1)):
                        st.session_state["batch_nav_idx"] = min(len(results) - 1, nav_cur + 1)
                        st.rerun()
                with nav_c4:
                    st.caption("⌨️ " + ("Dùng nút Trước/Sau để duyệt" if st.session_state["lang"] == "vi" else "Use Prev/Next to navigate"))

                # Show current selected image large + all gallery thumbs below
                cur_r = results[nav_cur]
                st.markdown(f"#### {cur_r['file']} — PCI {cur_r['pci'].pci_value:.1f} ({_rating_name(cur_r['pci'].rating)})")
                cur_anno = annotate_image_pil(cur_r["pil"], cur_r["det"], show_legend=st.session_state["show_legend"])
                col_cur_img, col_cur_info = st.columns([2, 1])
                with col_cur_img:
                    st.image(cur_anno, use_column_width=True)
                with col_cur_info:
                    st.markdown("**" + ("Detections:" if st.session_state["lang"] == "en" else "Phát hiện:") + f"** {len(cur_r['det'].detections)}")
                    st.markdown(damage_summary_html(cur_r["det"]), unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(detections_to_rows(cur_r["det"])), use_container_width=True, hide_index=True)

                # Thumbnail strip
                st.markdown("**" + ("Tất cả ảnh (click để xem lớn):" if st.session_state["lang"] == "vi" else "All images:") + "**")
                n_cols = min(6, len(results))
                cols = st.columns(n_cols)
                for idx, r in enumerate(results):
                    with cols[idx % n_cols]:
                        anno = annotate_image_pil(r["pil"], r["det"], show_legend=False)
                        st.image(anno, caption=f"#{idx+1} PCI {r['pci'].pci_value:.1f}", use_column_width=True)
                        if st.button("👁️", key=f"jump_{idx}"):
                            st.session_state["batch_nav_idx"] = idx
                            st.rerun()
    else:
        st.info("👆 " + ("Chọn nguồn ảnh (Upload / URL / Drive) để chạy batch." if st.session_state["lang"] == "vi" else "Select image source (Upload / URL / Drive) to run batch."))


# (Remaining tabs: video, stream, report, history, settings, about — next edits)


# =============================================================================
# Tab: Video — upload → frame extraction → annotate → export + PCI time-series
# =============================================================================
with tabs["tab_video"]:
    st.markdown("### " + ("Xử lý video" if st.session_state["lang"] == "vi" else "Video processing"))
    st.caption("📤 " + (
        "Upload video → trích frame → detection từng frame → annotate → xuất video đã gắn nhãn. "
        "Theo quy trình khảo sát ASTM D6433 (lấy mẫu mỗi N frame, không cần từng frame)."
        if st.session_state["lang"] == "vi" else
        "Upload → extract frames → per-frame detection → annotate → export. ASTM sampling: every Nth frame."
    ))
    pipeline_indicator(1)

    # Source selector for video: Upload / URL / Google Drive
    vid_source, tmp_video_path, _, vid_name = _source_selector("video", file_type="video")

    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        if tmp_video_path is not None and tmp_video_path.exists():
            st.video(str(tmp_video_path))

            with col_v2:
                st.markdown("**" + ("Cấu hình xử lý:" if st.session_state["lang"] == "vi" else "Processing config:") + "**")
                frame_stride = st.number_input("Lấy mẫu mỗi N frame", 1, 60, 5, 1, key="video_stride",
                                                help="ASTM không cần từng frame. N=5 → xử lý 1/5.")
                max_frames = st.number_input("Số frame tối đa (0=∞)", 0, 1000, 50, 10, key="video_max")
                show_overlay = st.checkbox("PCI overlay trên frame", value=True, key="video_overlay")
                fps_target = st.number_input("FPS output (0=giữ nguyên)", 0, 60, 0, 1, key="video_fps")

                if st.button("🎬 " + ("Xử lý video" if st.session_state["lang"] == "vi" else "Process video"), type="primary", key="process_video"):
                    pipeline_indicator(2)
                    detector = get_detector(st.session_state["confidence"], st.session_state["device"])
                    pci_engine = get_pci_engine(st.session_state["sample_unit_area"])

                    progress = st.progress(0.0, text="Đang mở video...")
                    cap = cv2.VideoCapture(str(tmp_video_path))
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    out_fps = fps_target if fps_target > 0 else src_fps

                    out_path = tmp_video_path.with_suffix(".annotated.mp4")
                    # Codec fallback: avc1/H264 (browser-compatible) → mp4v (fallback)
                    for codec in ["avc1", "H264", "mp4v"]:
                        fourcc = cv2.VideoWriter_fourcc(*codec)
                        out = cv2.VideoWriter(str(out_path), fourcc, out_fps, (w, h))
                        if out.isOpened():
                            break
                    if not out.isOpened():
                        st.error("❌ Không thể mở VideoWriter với bất kỳ codec nào (avc1/H264/mp4v).")
                        cap.release()
                        st.stop()

                    frame_idx = 0
                    processed = 0
                    pci_series = []
                    t_start = time.time()
                    max_proc = max_frames if max_frames > 0 else total_frames // frame_stride

                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        if frame_idx % frame_stride == 0:
                            if processed >= max_proc:
                                break
                            tmp_frame = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                            cv2.imwrite(tmp_frame.name, frame)
                            try:
                                det_res = detector.detect(tmp_frame.name)
                                pci_in = eb.detections_to_pci_input(det_res)
                                pci_res = pci_engine.calculate_pci(
                                    pci_in, image_area_px=det_res.image_shape[0] * det_res.image_shape[1])
                                _save_history("video", f"frame_{frame_idx}", det_res, pci_res)
                                pci_series.append({"frame": frame_idx, "pci": pci_res.pci_value,
                                                   "detections": len(det_res.detections), "rating": pci_res.rating,
                                                   "infer_ms": det_res.inference_time_ms})
                                # Annotate frame
                                for d in det_res.detections:
                                    x1, y1, x2, y2 = [int(v) for v in d.bbox]
                                    bgr = CODE_COLORS_BGR.get(d.code, (100, 100, 100))
                                    cv2.rectangle(frame, (x1, y1), (x2, y2), bgr, 2)
                                    label = f"{d.code} {d.confidence:.2f}"
                                    cv2.rectangle(frame, (x1, y1 - 22), (x1 + 120, y1), bgr, -1)
                                    cv2.putText(frame, label, (x1 + 4, y1 - 6),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                                if show_overlay:
                                    pci_bgr = {"Good": (46, 204, 113), "Satisfactory": (39, 174, 96),
                                               "Fair": (15, 196, 241), "Poor": (14, 126, 230),
                                               "Very Poor": (44, 62, 231), "Failed": (59, 23, 192)}.get(pci_res.rating, (100, 100, 100))
                                    cv2.rectangle(frame, (0, 0), (320, 70), (0, 0, 0), -1)
                                    cv2.putText(frame, f"PCI: {pci_res.pci_value:.1f} ({pci_res.rating})",
                                                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, pci_bgr, 2)
                                    cv2.putText(frame, f"Det: {len(det_res.detections)} | Frame: {frame_idx}/{total_frames}",
                                                (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                                out.write(frame)
                                processed += 1
                            except Exception as e:
                                st.warning(f"Frame {frame_idx} lỗi: {e}")
                            Path(tmp_frame.name).unlink(missing_ok=True)
                            elapsed = time.time() - t_start
                            eta = (elapsed / processed) * (max_proc - processed) if processed else 0
                            progress.progress(processed / max_proc,
                                              text=f"Frame {frame_idx}/{total_frames} — PCI {pci_res.pci_value:.1f} — ETA {eta:.0f}s")
                        frame_idx += 1
                    cap.release()
                    out.release()
                    progress.empty()

                    st.success(f"✓ {processed} frame đã xử lý trong {time.time()-t_start:.1f}s")
                    pipeline_indicator(3)
                    st.markdown("**" + ("Video đã annotate:" if st.session_state["lang"] == "vi" else "Annotated video:") + "**")
                    st.video(str(out_path))

                    if pci_series:
                        pipeline_indicator(4)
                        st.markdown("### 📈 " + ("PCI theo frame" if st.session_state["lang"] == "vi" else "PCI over frames"))
                        df = pd.DataFrame(pci_series)
                        col_chart, col_table = st.columns([2, 1])
                        with col_chart:
                            st.line_chart(df.set_index("frame")[["pci"]])
                        with col_table:
                            st.dataframe(df, use_container_width=True, hide_index=True)

                        # Downloads
                        pipeline_indicator(5)
                        c1, c2 = st.columns(2)
                        with c1:
                            with open(out_path, "rb") as f:
                                st.download_button("📥 Video MP4", f.read(),
                                                   file_name="road_damage_annotated.mp4", mime="video/mp4")
                        with c2:
                            st.download_button("📥 PCI CSV", df.to_csv(index=False).encode("utf-8"),
                                               file_name="pci_timeseries.csv", mime="text/csv")
        else:
            st.info("👆 " + ("Chọn nguồn video (Upload / URL / Drive) để xử lý." if st.session_state["lang"] == "vi" else "Select video source (Upload / URL / Drive) to process."))
            st.markdown("""
            **" + ("Video demo có sẵn:" if st.session_state["lang"] == "vi" else "Demo video available:") + "**
            - `outputs/demo_annotated.mp4` — render bằng `render_video.py` từ ảnh mẫu
            - **CLI render:** `python render_video.py --input video.mp4 --output annotated.mp4 --stride 5`
            """)


# =============================================================================
# Tab: Stream/CCTV — RTSP/HLS/MJPEG/Webcam input (Khám phá pillar — 27 video items)
# =============================================================================
with tabs["tab_stream"]:
    st.markdown("### " + ("Stream / CCTV / Webcam" if st.session_state["lang"] == "vi" else "Stream / CCTV / Webcam"))
    st.caption("📡 " + (
        "Hỗ trợ RTSP/HLS/MJPEG từ camera CCTV trên cao tốc. "
        "Tương lai: tích hợp hệ thống ITS (VDS, VMS) để nhận ảnh liên tục."
        if st.session_state["lang"] == "vi" else
        "RTSP/HLS/MJPEG from CCTV cameras. Future: ITS integration."
    ))
    pipeline_indicator(1)

    stream_type = st.radio(
        "Loại stream" if st.session_state["lang"] == "vi" else "Stream type",
        options=["rtsp", "hls", "mjpeg"],
        format_func=lambda x: {
            "rtsp": "🎥 RTSP (camera CCTV)",
            "hls": "📺 HLS (.m3u8)",
            "mjpeg": "📹 MJPEG",
        }[x],
        horizontal=True,
    )

    stream_url = st.text_input(
        "URL stream" if st.session_state["lang"] == "vi" else "Stream URL",
        placeholder="rtsp://user:pass@192.168.1.10:554/stream",
        key="stream_url",
    )

    col_sc, col_sm = st.columns([2, 1])
    with col_sc:
        max_stream_frames = st.number_input("Số frame captures", 1, 200, 20, 5, key="stream_max")
        stream_interval = st.number_input("Khoảng cách giữa frames (giây)", 0.1, 30.0, 2.0, 0.5, key="stream_interval")
    with col_sm:
        st.markdown("**" + ("Lưu ý:" if st.session_state["lang"] == "vi" else "Note:") + "**")
        st.caption("- " + ("Demo giới hạn số frame captures" if st.session_state["lang"] == "vi" else "Demo limits frame captures"))
        st.caption("- " + ("RTSP cần mạng cùng VLAN với camera" if st.session_state["lang"] == "vi" else "RTSP needs same VLAN as camera"))

    if st.button("▶ " + ("Bắt đầu capture" if st.session_state["lang"] == "vi" else "Start capture"), type="primary", key="start_stream"):
        if not stream_url:
            st.error("❌ " + ("Nhập URL stream trước." if st.session_state["lang"] == "vi" else "Enter stream URL first."))
        else:
            st.warning("⚠ " + ("Đang thử kết nối stream. Nếu lỗi, kiểm tra URL và mạng." if st.session_state["lang"] == "vi" else "Attempting connection. If fails, check URL and network."))
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                st.error("❌ " + ("Không mở được stream. Kiểm tra URL/đặc quyền camera." if st.session_state["lang"] == "vi" else "Cannot open stream."))
            else:
                pipeline_indicator(2)
                detector = get_detector(st.session_state["confidence"], st.session_state["device"])
                pci_engine = get_pci_engine(st.session_state["sample_unit_area"])
                captured = []
                progress = st.progress(0.0, text="Đang capture...")
                for i in range(max_stream_frames):
                    ret, frame = cap.read()
                    if not ret:
                        st.warning(f"Frame {i} không đọc được — auto-reconnect (Phục hồi pillar).")
                        break
                    tmp_f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    cv2.imwrite(tmp_f.name, frame)
                    try:
                        det_res = detector.detect(tmp_f.name)
                        pci_in = eb.detections_to_pci_input(det_res)
                        pci_res = pci_engine.calculate_pci(pci_in, image_area_px=det_res.image_shape[0] * det_res.image_shape[1])
                        _save_history("stream", f"{stream_type}_frame_{i}", det_res, pci_res)
                        pil_img = Image.open(tmp_f.name)
                        captured.append({"frame": i, "pil": pil_img, "det": det_res, "pci": pci_res})
                    except Exception as e:
                        st.warning(f"Frame {i}: {e}")
                    Path(tmp_f.name).unlink(missing_ok=True)
                    progress.progress((i + 1) / max_stream_frames, text=f"Frame {i+1}/{max_stream_frames}")
                    time.sleep(stream_interval)
                cap.release()
                progress.empty()

                if captured:
                    pipeline_indicator(3)
                    st.success(f"✓ {len(captured)} frame đã capture")
                    st.markdown("### " + ("Kết quả" if st.session_state["lang"] == "vi" else "Results"))
                    rows = [{"Frame": c["frame"], "Detections": len(c["det"].detections),
                             "PCI": f"{c['pci'].pci_value:.1f}", "Rating": _rating_name(c["pci"].rating)}
                            for c in captured]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    st.markdown("### " + ("Gallery" if st.session_state["lang"] == "vi" else "Gallery"))
                    cols = st.columns(min(4, len(captured)))
                    for idx, c in enumerate(captured):
                        with cols[idx % len(cols)]:
                            anno = annotate_image_pil(c["pil"], c["det"], show_legend=st.session_state["show_legend"])
                            st.image(anno, caption=f"F{c['frame']} PCI {c['pci'].pci_value:.1f}", use_column_width=True)


# (Remaining tabs: report, history, settings, about — next edit)


# =============================================================================
# Tab: Report — ASTM D6433 form export (Báo cáo pillar — DE_XUAT #10)
# =============================================================================
with tabs["tab_report"]:
    st.markdown("### " + ("Xuất báo cáo ASTM D6433" if st.session_state["lang"] == "vi" else "ASTM D6433 Report Export"))
    st.caption("📄 " + (
        "Báo cáo theo form khảo sát ASTM D6433: thông tin đoạn đường, danh sách hư hỏng, "
        "bảng deduct values, CDV, PCI, khuyến nghị bảo dưỡng."
        if st.session_state["lang"] == "vi" else
        "Report follows ASTM D6433 survey form: section info, damage list, deduct values, CDV, PCI."
    ))

    if st.session_state["last_pci"] is None:
        st.info("👆 " + ("Chạy phát hiện trên Tab Ảnh đơn/Video trước, sau đó quay lại đây để xuất báo cáo." if st.session_state["lang"] == "vi" else "Run detection in Image/Video tab first."))
    else:
        pci_result = st.session_state["last_pci"]
        det_result = st.session_state["last_detection"]
        annotated = st.session_state["last_annotated"]
        src_name = st.session_state.get("last_source", "analysis")

        st.markdown("#### " + ("Thông tin đoạn đường" if st.session_state["lang"] == "vi" else "Section information"))

        # CUST-05 — Road section management (save/load named sections)
        sections_path = Path("outputs/saved_sections.json")
        sections_path.parent.mkdir(parents=True, exist_ok=True)
        saved_sections = {}
        if sections_path.exists():
            try:
                saved_sections = json.loads(sections_path.read_text(encoding="utf-8"))
            except Exception:
                saved_sections = {}
        sec_mgmt = st.expander("🗂️ " + ("Quản lý đoạn đường đã lưu" if st.session_state["lang"] == "vi" else "Saved road sections"), expanded=False)
        with sec_mgmt:
            if saved_sections:
                sec_options = ["(mới)"] + list(saved_sections.keys())
                load_sec = st.selectbox("📋 " + ("Tải đoạn đã lưu" if st.session_state["lang"] == "vi" else "Load saved section"),
                                        options=sec_options, key="load_section")
                if load_sec != "(mới)":
                    sd = saved_sections[load_sec]
                    sec_name_default = load_sec
                    sec_surveyor_default = sd.get("surveyor", "Sinh viên UTRAN")
                    sec_road_type_default = sd.get("road_type", "Cao tốc")
                    sec_area_default = sd.get("sample_unit_area", pci_result.sample_unit_area_sqft)
                    if st.button("🗑️ " + ("Xóa đoạn này" if st.session_state["lang"] == "vi" else "Delete this section"), key="del_sec"):
                        saved_sections.pop(load_sec, None)
                        sections_path.write_text(json.dumps(saved_sections, ensure_ascii=False, indent=2), encoding="utf-8")
                        st.rerun()
                else:
                    sec_name_default = sec_surveyor_default = sec_road_type_default = None
                    sec_area_default = pci_result.sample_unit_area_sqft
            else:
                sec_name_default = sec_surveyor_default = sec_road_type_default = None
                sec_area_default = pci_result.sample_unit_area_sqft
                st.caption("—" + (" Chưa có đoạn nào được lưu" if st.session_state["lang"] == "vi" else " No sections saved yet"))

        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            section_name = st.text_input("Tên đoạn đường" if st.session_state["lang"] == "vi" else "Section name",
                                          value=sec_name_default if sec_name_default else "Demo section")
            surveyor = st.text_input("Người khảo sát" if st.session_state["lang"] == "vi" else "Surveyor",
                                      value=sec_surveyor_default if sec_surveyor_default else "Sinh viên UTRAN")
        with col_r2:
            survey_date = st.date_input("Ngày khảo sát" if st.session_state["lang"] == "vi" else "Survey date", value=datetime.now().date())
            sample_unit_area = st.number_input("Diện tích mẫu (ft²)", value=sec_area_default, key="report_area")
        with col_r3:
            road_type = st.selectbox("Loại đường", ["Cao tốc", "Quốc lộ", "Tỉnh lộ", "Đô thị", "Khác"],
                                      index=["Cao tốc", "Quốc lộ", "Tỉnh lộ", "Đô thị", "Khác"].index(sec_road_type_default) if sec_road_type_default else 0)
            weather = st.selectbox("Thời tiết", ["Nắng", "Nhiều mây", "Mưa", "Khác"])

        # Save current section
        if st.button("💾 " + ("Lưu đoạn đường" if st.session_state["lang"] == "vi" else "Save section"), key="save_sec"):
            saved_sections[section_name] = {
                "surveyor": surveyor, "road_type": road_type,
                "sample_unit_area": sample_unit_area,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }
            sections_path.write_text(json.dumps(saved_sections, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success(f"✓ {section_name} " + ("đã lưu" if st.session_state["lang"] == "vi" else "saved"))

        st.markdown("#### " + ("Kết quả PCI" if st.session_state["lang"] == "vi" else "PCI result"))
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            st.markdown(pci_gauge_html(pci_result.pci_value, pci_result.rating, pci_result.pci_color), unsafe_allow_html=True)
        with col_p2:
            st.markdown(f"**PCI:** {pci_result.pci_value:.1f} ({_rating_name(pci_result.rating)})")
            st.markdown(f"**CDV:** {pci_result.cdv:.2f} | **TDV:** {pci_result.tdv:.2f} | **q:** {pci_result.q}")
            st.markdown(f"**Số detections:** {len(det_result.detections)}")
            st.markdown(f"**Khuyến nghị:** {pci_result.maintenance_action}")

        if pci_result.damages:
            st.markdown("#### " + ("Bảng hư hỏng chi tiết" if st.session_state["lang"] == "vi" else "Damage detail table"))
            st.dataframe(pd.DataFrame(pci_damage_rows(pci_result)), use_container_width=True, hide_index=True)

        if annotated is not None:
            st.markdown("#### " + ("Ảnh đã annotate" if st.session_state["lang"] == "vi" else "Annotated image"))
            st.image(annotated, use_column_width=True)

        st.markdown("#### " + ("Xuất báo cáo" if st.session_state["lang"] == "vi" else "Export"))
        c1, c2, c3 = st.columns(3)
        with c1:
            # Markdown report (can be converted to PDF/Word later)
            md_lines = [
                f"# Báo cáo Khảo sát Hư hỏng Mặt đường (ASTM D6433)",
                f"",
                f"**Đoạn đường:** {section_name}  ",
                f"**Người khảo sát:** {surveyor}  ",
                f"**Ngày:** {survey_date}  ",
                f"**Loại đường:** {road_type} — Thời tiết: {weather}  ",
                f"**Diện tích mẫu đơn vị:** {sample_unit_area} ft² ({sample_unit_area*0.0929:.1f} m²)",
                f"",
                f"## Kết quả",
                f"",
                f"| Chỉ số | Giá trị |",
                f"|--------|---------|",
                f"| PCI | {pci_result.pci_value:.1f} |",
                f"| Rating | {_rating_name(pci_result.rating)} |",
                f"| CDV | {pci_result.cdv:.2f} |",
                f"| TDV | {pci_result.tdv:.2f} |",
                f"| q | {pci_result.q} |",
                f"| Số detections | {len(det_result.detections)} |",
                f"",
                f"## Khuyến nghị bảo dưỡng",
                f"",
                f"**{pci_result.maintenance_action}**  ",
                f"{pci_result.maintenance_detail}",
                f"",
                f"## Bảng hư hỏng chi tiết",
                f"",
                f"| Mã | Loại | Mức độ | Mật độ (%) | GT khấu trừ | Diện tích (ft²) | Confidence |",
                f"|----|------|--------|-----------|-------------|-----------------|------------|",
            ]
            for d in pci_result.damages:
                md_lines.append(f"| {d.code} | {_type_name(d.code)} | {_severity_name(d.severity)} | {d.density_pct:.3f} | {d.deduct_value:.2f} | {d.corrected_area_sqft:.2f} | {d.confidence:.2f} |")
            md_report = "\n".join(md_lines)
            st.download_button("📥 Markdown báo cáo", md_report.encode("utf-8"),
                               file_name=f"pci_report_{Path(src_name).stem}.md", mime="text/markdown")
        with c2:
            if annotated is not None:
                buf = io.BytesIO()
                annotated.save(buf, format="PNG")
                st.download_button("📥 Ảnh PNG", buf.getvalue(),
                                   file_name=f"{Path(src_name).stem}_annotated.png", mime="image/png")
        with c3:
            csv_buf = io.StringIO()
            pd.DataFrame(pci_damage_rows(pci_result)).to_csv(csv_buf, index=False)
            st.download_button("📥 CSV damages", csv_buf.getvalue().encode("utf-8"),
                               file_name=f"{Path(src_name).stem}_damages.csv", mime="text/csv")


# =============================================================================
# Tab: History — SQLite-backed session log (Dữ liệu pillar — DE_XUAT #24 INF-01 logging)
# =============================================================================
with tabs["tab_history"]:
    st.markdown("### " + ("Lịch sử phân tích" if st.session_state["lang"] == "vi" else "Analysis history"))
    st.caption("🗄️ " + ("Lưu SQLite — dữ liệu tồn tại qua các phiên làm việc (crash recovery). DB tại: " if st.session_state["lang"] == "vi" else "SQLite-backed — persists across sessions. DB at: ") + f"`{st.session_state['db_path']}`")

    conn = _db_conn()
    df = pd.read_sql("SELECT ts, source, file_name, detections, pci, rating, inference_ms FROM analyses ORDER BY ts DESC LIMIT 200", conn)
    conn.close()

    if df.empty:
        st.info("📭 " + ("Chưa có bản ghi nào. Chạy phát hiện trên các tab khác để bắt đầu." if st.session_state["lang"] == "vi" else "No records yet. Run detection in other tabs."))
    else:
        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng analyses", len(df))
        m2.metric("PCI trung bình", f"{df['pci'].mean():.1f}" if not df.empty else "—")
        m3.metric("PCI thấp nhất", f"{df['pci'].min():.1f}" if not df.empty else "—")
        m4.metric("Tổng detections", int(df['detections'].sum()))

        st.markdown("#### " + ("Bảng lịch sử" if st.session_state["lang"] == "vi" else "History table"))
        st.dataframe(df, use_container_width=True, hide_index=True)

        # PCI distribution chart
        st.markdown("#### " + ("Phân bố PCI" if st.session_state["lang"] == "vi" else "PCI distribution"))
        st.bar_chart(df.set_index("ts")["pci"] if len(df) > 1 else pd.DataFrame({"pci": [df['pci'].iloc[0]]}, index=[df['ts'].iloc[0]]))

        # Export full history + DAT-02 SQLite backup
        st.markdown("#### " + ("Xuất toàn bộ" if st.session_state["lang"] == "vi" else "Export all"))
        bk1, bk2, bk3 = st.columns(3)
        with bk1:
            st.download_button("📥 CSV lịch sử", df.to_csv(index=False).encode("utf-8"),
                               file_name="analysis_history.csv", mime="text/csv")
        with bk2:
            # DAT-02 — SQLite backup download
            db_path = Path(st.session_state["db_path"])
            if db_path.exists():
                with open(db_path, "rb") as f:
                    st.download_button("🗄️ " + ("Backup SQLite" if st.session_state["lang"] == "vi" else "SQLite backup"),
                                       f.read(), file_name="road_damage_history.sqlite",
                                       mime="application/octet-stream")
        with bk3:
            # DAT-02 — Restore from backup (upload SQLite)
            restore_file = st.file_uploader("📤 " + ("Restore SQLite" if st.session_state["lang"] == "vi" else "Restore SQLite"),
                                            type=["sqlite", "db"], key="restore_db")
            if restore_file is not None:
                with open(db_path, "wb") as f:
                    f.write(restore_file.read())
                st.success("✓ " + ("Đã restore. Refresh để xem." if st.session_state["lang"] == "vi" else "Restored. Refresh."))
        if st.button("🗑️ " + ("Xóa lịch sử" if st.session_state["lang"] == "vi" else "Clear history"), key="clear_history"):
            conn = _db_conn()
            conn.execute("DELETE FROM analyses")
            conn.commit()
            conn.close()
            st.session_state["history"] = []
            st.success("✓ " + ("Đã xóa." if st.session_state["lang"] == "vi" else "Cleared."))
            st.rerun()


# =============================================================================
# Tab: Settings — Tùy biến pillar
# =============================================================================
with tabs["tab_settings"]:
    st.markdown("### " + ("Cài đặt chi tiết" if st.session_state["lang"] == "vi" else "Advanced settings"))

    st.markdown("#### " + ("Đường dẫn model" if st.session_state["lang"] == "vi" else "Model paths"))
    st.code(f"Detection: {eb.DEFAULT_MODEL_PATH}", language="text")
    st.code(f"PCI data:  {eb.DEFAULT_PCI_DATA}", language="text")
    st.code(f"FastSAM-s: {eb.DEFAULT_FASTSAM_S}", language="text")
    st.code(f"FastSAM-x: {eb.DEFAULT_FASTSAM_X}", language="text")

    st.markdown("#### " + ("Thư mục output" if st.session_state["lang"] == "vi" else "Output directories"))
    out_dirs = ["outputs/images", "outputs/reports", "outputs/videos", "outputs/logs"]
    for d in out_dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    st.code("\n".join(out_dirs), language="text")

    st.markdown("#### " + ("Cấu hình hiện tại" if st.session_state["lang"] == "vi" else "Current configuration"))
    config = {
        "language": st.session_state["lang"],
        "confidence": st.session_state["confidence"],
        "sample_unit_area_sqft": st.session_state["sample_unit_area"],
        "device": st.session_state["device"],
        "use_segmentation": st.session_state["use_segmentation"],
        "show_legend": st.session_state["show_legend"],
        "db_path": st.session_state["db_path"],
    }
    st.json(config)

    # Export settings (Mở rộng pillar)
    st.download_button("📥 Export settings JSON", json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name="settings.json", mime="application/json")


# (About tab + footer — final edit)


# =============================================================================
# Tab: Console — runtime log viewer (Phản hồi pillar — debug/errors/process)
# =============================================================================
with tabs["tab_console"]:
    st.markdown("### 📜 " + ("Console / Log runtime" if st.session_state["lang"] == "vi" else "Runtime console / log"))
    st.caption("🔍 " + (
        "Hiển thị log runtime: lỗi, tiến trình inference, warnings."
        if st.session_state["lang"] == "vi" else
        "Shows runtime log: errors, inference progress, warnings."
    ))

    # Live log buffer in session_state (in-memory, resets on page reload)
    st.session_state.setdefault("log_buffer", [])
    log_buffer = st.session_state["log_buffer"]

    # Controls
    log_c1, log_c2, log_c3 = st.columns([1, 1, 2])
    with log_c1:
        log_level = st.selectbox("Mức log", ["ALL", "INFO", "WARNING", "ERROR"], key="log_level")
    with log_c2:
        log_max = st.number_input("Số dòng tối đa", 50, 2000, 200, 50, key="log_max")
    with log_c3:
        auto_refresh = st.checkbox("🔄 Auto-refresh (2s)" if st.session_state["lang"] == "vi" else "Auto-refresh (2s)", value=False, key="log_auto")

    # Read log file (adaptive local + dumps outputs — cross-platform)
    log_sources = [
        Path("outputs/app.log"),
        eb._DUMPS_ROOT / "outputs" / "app.log",  # cross-platform via engine_bridge
    ]
    log_lines = []
    for lp in log_sources:
        if lp.exists():
            try:
                content = lp.read_text(encoding="utf-8", errors="replace").splitlines()
                log_lines = content[-log_max:] if len(content) > log_max else content
                st.session_state["log_source"] = str(lp)
                break
            except Exception as e:
                st.warning(f"Không đọc được {lp}: {e}")

    # Also include in-session log buffer
    log_lines = log_buffer + log_lines

    # Filter by level
    if log_level != "ALL":
        log_lines = [l for l in log_lines if log_level in l.upper()]

    # Display
    if log_lines:
        st.code("\n".join(log_lines[-log_max:]), language="text")
        st.caption(f"📋 {len(log_lines)} dòng · " + ("Nguồn: " if st.session_state["lang"] == "vi" else "Source: ") + st.session_state.get("log_source", "in-memory buffer"))
    else:
        st.info("📭 " + ("Chưa có log. Chạy inference ở tab khác để sinh log." if st.session_state["lang"] == "vi" else "No logs yet. Run inference in other tabs."))

    # Manual log entry (for testing/debugging)
    with st.expander("✏️ " + ("Ghi log thủ công (test)" if st.session_state["lang"] == "vi" else "Manual log entry (test)")):
        test_msg = st.text_input("Message", key="log_test_msg")
        test_level = st.selectbox("Level", ["INFO", "WARNING", "ERROR"], key="log_test_level")
        if st.button("Ghi log" if st.session_state["lang"] == "vi" else "Write log", key="log_test_write"):
            entry = f"[{datetime.now().strftime('%H:%M:%S')}] {test_level}: {test_msg}"
            log_buffer.append(entry)
            st.success("✓ " + ("Đã ghi" if st.session_state["lang"] == "vi" else "Written"))

    # Clear buffer
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ " + ("Xóa log buffer" if st.session_state["lang"] == "vi" else "Clear log buffer"), key="clear_log"):
            st.session_state["log_buffer"] = []
            st.rerun()
    with c2:
        if log_lines:
            st.download_button("📥 " + ("Tải log" if st.session_state["lang"] == "vi" else "Download log"),
                               "\n".join(log_lines).encode("utf-8"),
                               file_name=f"runtime_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                               mime="text/plain")

    # System info (useful for Colab debugging)
    st.markdown("---")
    st.markdown("### 🖥️ " + ("Thông tin hệ thống" if st.session_state["lang"] == "vi" else "System info"))
    import platform
    import sys
    sys_info = {
        "Python": sys.version.split()[0],
        "Platform": platform.platform(),
        "Device (config)": st.session_state["device"],
        "Confidence": st.session_state["confidence"],
        "Sample area (ft²)": st.session_state["sample_unit_area"],
        "Segmentation T2": st.session_state["use_segmentation"],
        "Language": st.session_state["lang"],
        "DB path": st.session_state["db_path"],
    }
    # GPU check (only if torch available)
    try:
        import torch
        sys_info["CUDA available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            sys_info["GPU"] = torch.cuda.get_device_name(0)
            sys_info["GPU memory (GB)"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
    except Exception as e:
        sys_info["torch"] = f"error: {e}"
    st.json(sys_info)


# (End of app — footer removed for compactness)






