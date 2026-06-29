"""Road Damage Assessment System — Web Dashboard (Streamlit).

Layout 5: Top Input Bar + Stacked Content
- Video/image preview = main, state lock (session_state)
- Source: Upload / URL / Google Drive (folder tree browser)
- Type: Video / Image / Batch
- Config panel bên phải
- Results bên dưới
- Bottom bar: Report / History / Settings / Console (expanders)
- Pipeline indicator small bottom
- Bỏ Stream/CCTV/Webcam

Cross-platform: Windows local + Colab Linux (auto-detect DUMPS_ROOT).
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
import tempfile
import time
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

import engine_bridge as eb
from engine_bridge import CODE_COLORS_RGB, CODE_COLORS_BGR

# =============================================================================
# Page config
# =============================================================================
st.set_page_config(
    page_title="Hệ thống Đánh giá Hư hỏng Mặt đường",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="collapsed",  # layout 5 không dùng sidebar chính
)

# =============================================================================
# CSS — smooth animations + premium feel
# =============================================================================
st.markdown("""
<style>
    /* Layout — centered, max-width for readability on all screens */
    .main .block-container { max-width: 1200px; margin: 0 auto; padding-top: 0.5rem; padding-bottom: 0.5rem; padding-left: 1rem; padding-right: 1rem; }
    [data-testid="stVerticalBlock"] { gap: 0.5rem; }
    [data-testid="stHorizontalBlock"] { gap: 0.8rem; }

    /* Typography */
    h1 { font-size: 1.5rem; margin: 0; font-weight: 700; }
    h2 { font-size: 1.2rem; margin: 0.2rem 0; }
    h3 { font-size: 1.05rem; margin: 0.15rem 0; }

    /* Metrics — compact cards */
    .stMetric { background: rgba(128,128,128,0.05); border: 1px solid rgba(128,128,128,0.12); border-radius: 8px; padding: 8px 10px; }
    [data-testid="stMetricValue"] { font-size: 1rem; }
    [data-testid="stMetricLabel"] { font-size: 0.78rem; }

    /* PCI gauge */
    .pci-gauge { text-align: center; padding: 0.3rem; border-radius: 10px; }
    @keyframes needleSweep { 0% { transform: rotate(-90deg); transform-origin: 110px 110px; } 100% { transform: rotate(0deg); transform-origin: 110px 110px; } }
    .pci-gauge svg line[stroke="#2c3e50"] { animation: needleSweep 0.7s cubic-bezier(0.34, 1.56, 0.64, 1); }

    /* Fade in up — smooth entrance */
    @keyframes fadeInUp { 0% { opacity: 0; transform: translateY(10px); } 100% { opacity: 1; transform: translateY(0); } }
    .stMetric, [data-testid="stAlert"], [data-testid="stImageContainer"] { animation: fadeInUp 0.4s ease-out; }

    /* Slide in left — for preview area */
    @keyframes slideInLeft { 0% { opacity: 0; transform: translateX(-15px); } 100% { opacity: 1; transform: translateX(0); } }
    [data-testid="stVideo"] { animation: slideInLeft 0.5s ease-out; }

    /* Slide in right — for config panel */
    @keyframes slideInRight { 0% { opacity: 0; transform: translateX(15px); } 100% { opacity: 1; transform: translateX(0); } }

    /* Damage tags */
    .damage-tag { display: inline-block; padding: 2px 10px; border-radius: 12px; color: white; font-size: 0.8em; margin: 2px; font-weight: 500; }
    @keyframes tagPop { 0% { transform: scale(0.8); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
    .damage-tag { animation: tagPop 0.3s ease-out; }

    /* Pipeline indicator — compact horizontal */
    .pipeline-step { display: inline-block; padding: 3px 10px; margin: 0 3px; border-radius: 16px; font-size: 0.78em; color: var(--text-color); transition: all 0.3s ease; }
    .pipeline-step.active { background: rgba(40, 167, 69, 0.2); border: 1px solid #28a745; font-weight: 600; }
    .pipeline-step.done { background: rgba(40, 167, 69, 0.1); color: #28a745; }
    .pipeline-step.pending { background: rgba(128,128,128,0.08); opacity: 0.6; }
    .pipeline-arrow { color: rgba(128,128,128,0.4); margin: 0 2px; }

    /* Severity badges */
    .severity-Low { background: rgba(46, 125, 50, 0.15); color: #2e7d32; padding: 1px 6px; border-radius: 4px; font-size: 0.8em; }
    .severity-Medium { background: rgba(245, 124, 0, 0.15); color: #f57c00; padding: 1px 6px; border-radius: 4px; font-size: 0.8em; }
    .severity-High { background: rgba(198, 40, 40, 0.15); color: #c62828; padding: 1px 6px; border-radius: 4px; font-size: 0.8em; }

    /* Khuyến nghị box */
    .recommend-box { border-left: 4px solid; padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 4px 0; transition: all 0.3s; }
    .recommend-box:hover { transform: translateX(3px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }

    /* Input bar — segmented control style */
    .input-bar { background: rgba(128,128,128,0.04); border: 1px solid rgba(128,128,128,0.1); border-radius: 10px; padding: 8px 12px; }

    /* Config panel — card style */
    .config-card { background: rgba(128,128,128,0.03); border: 1px solid rgba(128,128,128,0.1); border-radius: 10px; padding: 12px; }

    /* Process button — prominent */
    .stButton > button[kind="primary"] { border-radius: 10px; font-weight: 600; font-size: 1rem; padding: 8px 24px; transition: all 0.2s; }
    .stButton > button[kind="primary"]:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3); }

    /* Tabs — compact */
    [data-testid="stTabs"] [role="tablist"] { gap: 0.3rem; }
    [data-testid="stTabs"] [role="tab"] { padding: 0.3rem 0.7rem; font-size: 0.85rem; border-radius: 8px 8px 0 0; transition: all 0.2s; }

    /* Expander — smooth */
    [data-testid="stExpander"] { border-radius: 8px; transition: all 0.2s; }

    /* Scrollbar — subtle */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(128,128,128,0.2); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(128,128,128,0.4); }

    /* File info card */
    .file-info { background: rgba(128,128,128,0.04); border-radius: 8px; padding: 8px 12px; font-size: 0.85em; }

    /* Responsive — 1366x768 and smaller */
    @media (max-width: 1400px) {
        .main .block-container { max-width: 1100px; padding-left: 0.8rem; padding-right: 0.8rem; }
    }
    @media (max-width: 768px) {
        .main .block-container { max-width: 100%; padding-left: 0.5rem; padding-right: 0.5rem; }
        h1 { font-size: 1.2rem; }
        h3 { font-size: 0.95rem; }
        .config-card { padding: 8px; }
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Strings — VI / EN
# =============================================================================
_STRINGS = {
    "vi": {
        "app_title": "Hệ thống Đánh giá Hư hỏng Mặt đường",
        "app_subtitle": "Phát hiện hư hỏng & Tính chỉ số PCI (ASTM D6433)",
        "type_video": "🎬 Video",
        "type_image": "📷 Ảnh đơn",
        "type_batch": "📁 Batch ảnh",
        "src_upload": "📤 Upload",
        "src_url": "🔗 URL",
        "src_drive": "📁 Drive",
        "btn_select": "📂 Chọn file",
        "btn_process_video": "🚀 Xử lý video",
        "btn_process_image": "🚀 Phát hiện hư hỏng",
        "btn_process_batch": "🚀 Chạy batch",
        "config_title": "⚙️ Cấu hình xử lý",
        "results_title": "📊 Kết quả",
        "rec_title": "🛠️ Khuyến nghị bảo dưỡng",
        "export_title": "📤 Export",
        "pipeline_collect": "Thu thập",
        "pipeline_detect": "Phát hiện",
        "pipeline_assess": "Đánh giá",
        "pipeline_report": "Báo cáo",
        "pipeline_recommend": "Khuyến nghị",
        "tab_report": "📄 Báo cáo ASTM",
        "tab_history": "🗄️ Lịch sử",
        "tab_settings": "⚙️ Cài đặt",
        "tab_console": "📜 Console",
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
        "select_file": "Chọn file để bắt đầu",
        "no_file": "Chưa chọn file",
        "processing": "Đang xử lý",
        "done": "Hoàn thành",
        "file_name": "File",
        "file_size": "Size",
        "file_dims": "Kích thước",
        "file_duration": "Thời lượng",
        "file_fps": "FPS",
        "detections": "Phát hiện",
        "inference_time": "Inference",
        "total_time": "Tổng thời gian",
        "pci_index": "Chỉ số PCI",
        "pci_cdv": "CDV",
        "pci_tdv": "TDV",
        "pci_q": "q",
        "pci_area": "Diện tích mẫu",
        "conf_threshold": "Ngưỡng tin cậy",
        "sample_area": "Diện tích mẫu (ft²)",
        "device": "Thiết bị inference",
        "video_stride": "Lấy mẫu mỗi N frame",
        "video_max": "Số frame tối đa (0=∞)",
        "video_overlay": "PCI overlay trên frame",
        "video_fps": "FPS output (0=giữ nguyên)",
        "show_legend": "Hiển thị chú giải",
        "use_segmentation": "FastSAM segmentation (T2)",
        "filter_class": "Lọc theo loại hư hỏng",
        "section_pci": "PCI cấp đoạn đường",
        "batch_results": "Kết quả từng ảnh",
        "gallery": "Gallery ảnh đã annotate",
        "prev": "⬅ Trước",
        "next": "Sau ➡",
        "export_png": "📥 Ảnh PNG",
        "export_csv": "📥 CSV detections",
        "export_json": "📥 JSON PCI",
        "export_md": "📥 Markdown báo cáo",
        "copy_clipboard": "📋 Copy PCI",
        "rerun": "🔄 Chạy lại",
        "drive_browser": "📁 Google Drive browser",
        "subfolders": "📁 Thư mục con",
        "files_in": "Files trong",
        "enter_path": "Nhập đường dẫn trực tiếp",
        "path_not_exist": "Đường dẫn không tồn tại",
        "no_files": "Không có file phù hợp",
        "no_image_loaded": "Chưa chọn file. Chọn nguồn + loại + file ở trên để bắt đầu.",
        "source_label": "Nguồn",
        "type_label": "Loại đầu vào",
        "no_detections": "Không phát hiện hư hỏng nào ở ngưỡng hiện tại.",
        "detection_table": "Bảng detections",
        "pci_breakdown": "Bản ghi hư hỏng chi tiết (PCI breakdown)",
        "pre_flight": "Pre-flight",
        "model_ready": "Model ready",
        "pci_ready": "PCI data ready",
    },
    "en": {
        "app_title": "Road Damage Assessment System",
        "app_subtitle": "Damage Detection & PCI Calculation (ASTM D6433)",
        "type_video": "🎬 Video",
        "type_image": "📷 Image",
        "type_batch": "📁 Batch",
        "src_upload": "📤 Upload",
        "src_url": "🔗 URL",
        "src_drive": "📁 Drive",
        "btn_select": "📂 Select file",
        "btn_process_video": "🚀 Process video",
        "btn_process_image": "🚀 Run detection",
        "btn_process_batch": "🚀 Run batch",
        "config_title": "⚙️ Processing config",
        "results_title": "📊 Results",
        "rec_title": "🛠️ Maintenance recommendation",
        "export_title": "📤 Export",
        "pipeline_collect": "Collect",
        "pipeline_detect": "Detect",
        "pipeline_assess": "Assess",
        "pipeline_report": "Report",
        "pipeline_recommend": "Recommend",
        "tab_report": "📄 Report",
        "tab_history": "🗄️ History",
        "tab_settings": "⚙️ Settings",
        "tab_console": "📜 Console",
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
        "select_file": "Select file to start",
        "no_file": "No file selected",
        "processing": "Processing",
        "done": "Done",
        "file_name": "File",
        "file_size": "Size",
        "file_dims": "Dimensions",
        "file_duration": "Duration",
        "file_fps": "FPS",
        "detections": "Detections",
        "inference_time": "Inference",
        "total_time": "Total time",
        "pci_index": "PCI Index",
        "pci_cdv": "CDV",
        "pci_tdv": "TDV",
        "pci_q": "q",
        "pci_area": "Sample area",
        "conf_threshold": "Confidence threshold",
        "sample_area": "Sample area (sq ft)",
        "device": "Inference device",
        "video_stride": "Sample every N frames",
        "video_max": "Max frames (0=∞)",
        "video_overlay": "PCI overlay on frame",
        "video_fps": "Output FPS (0=keep)",
        "show_legend": "Show legend",
        "use_segmentation": "FastSAM segmentation (T2)",
        "filter_class": "Filter by damage type",
        "section_pci": "Section-level PCI",
        "batch_results": "Per-image results",
        "gallery": "Annotated gallery",
        "prev": "⬅ Prev",
        "next": "Next ➡",
        "export_png": "📥 PNG",
        "export_csv": "📥 CSV",
        "export_json": "📥 JSON",
        "export_md": "📥 Markdown",
        "copy_clipboard": "📋 Copy PCI",
        "rerun": "🔄 Re-run",
        "drive_browser": "📁 Google Drive browser",
        "subfolders": "📁 Subfolders",
        "files_in": "Files in",
        "enter_path": "Enter path directly",
        "path_not_exist": "Path does not exist",
        "no_files": "No matching files",
        "no_image_loaded": "No file selected. Pick source + type + file above to start.",
        "source_label": "Source",
        "type_label": "Input type",
        "no_detections": "No damage detected at current threshold.",
        "detection_table": "Detections table",
        "pci_breakdown": "Detailed damage records (PCI breakdown)",
        "pre_flight": "Pre-flight",
        "model_ready": "Model ready",
        "pci_ready": "PCI data ready",
    },
}


def _t(key: str) -> str:
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
# Session state — state lock for preview + config + results
# =============================================================================
_ss = st.session_state
_ss.setdefault("lang", "vi")
# State lock: selected file persists across reruns
_ss.setdefault("sel_type", "video")          # video / image / batch
_ss.setdefault("sel_source", "upload")        # upload / url / drive
_ss.setdefault("sel_file_path", None)         # Path of selected file
_ss.setdefault("sel_file_name", "")           # name
_ss.setdefault("sel_pil", None)               # PIL image (for image type)
_ss.setdefault("sel_video_path", None)        # video path
_ss.setdefault("sel_batch_paths", [])         # list of paths (batch)
_ss.setdefault("sel_batch_pils", [])          # list of PIL (batch)
# Config (persists)
_ss.setdefault("confidence", 0.15)
_ss.setdefault("sample_unit_area", 5000.0)
_ss.setdefault("device", "cpu")
_ss.setdefault("use_segmentation", False)
_ss.setdefault("show_legend", True)
_ss.setdefault("video_stride", 5)
_ss.setdefault("video_max", 30)
_ss.setdefault("video_overlay", True)
_ss.setdefault("video_fps", 0)
# Results (state lock)
_ss.setdefault("last_det", None)              # DetectionResult
_ss.setdefault("last_pci", None)              # PCIResult
_ss.setdefault("last_annotated", None)        # PIL annotated
_ss.setdefault("last_source_name", "")        # source file name
_ss.setdefault("last_elapsed_ms", 0)
_ss.setdefault("last_batch_results", [])      # list of dicts (batch)
# History + DB
_ss.setdefault("history", [])
_db_dir = "/content" if os.path.isdir("/content") else tempfile.gettempdir()
_ss.setdefault("db_path", str(Path(_db_dir) / "road_damage_history.sqlite"))
# Drive browser state
_ss.setdefault("drive_path_video", "/content/drive/MyDrive")
_ss.setdefault("drive_path_image", "/content/drive/MyDrive")
_ss.setdefault("drive_path_batch", "/content/drive/MyDrive")
# Bottom bar active tab
_ss.setdefault("bottom_tab", None)  # report / history / settings / console
_ss.setdefault("is_processing", False)  # disable widgets during video processing
_ss.setdefault("abort_video_flag", False)  # abort button flag


# =============================================================================
# Engine cache (load once)
# =============================================================================
@st.cache_resource
def get_detector(confidence: float, device: str):
    return eb.make_detector(confidence=confidence, device=device)


@st.cache_resource
def get_pci_engine(sample_unit_area_sqft: float):
    return eb.make_pci_engine(sample_unit_area_sqft=sample_unit_area_sqft)


# =============================================================================
# SQLite persistence
# =============================================================================
def _db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(st.session_state["db_path"], check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL, source TEXT NOT NULL, file_name TEXT,
            detections INTEGER, pci REAL, rating TEXT, inference_ms REAL,
            det_json TEXT, pci_json TEXT
        )
    """)
    conn.commit()
    return conn


def _save_history(source: str, file_name: str, det_result, pci_result):
    conn = _db_conn()
    conn.execute(
        "INSERT INTO analyses (ts, source, file_name, detections, pci, rating, inference_ms, det_json, pci_json) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), source, file_name,
         len(det_result.detections), pci_result.pci_value, pci_result.rating,
         det_result.inference_time_ms,
         json.dumps([{"code": d.code, "conf": d.confidence, "bbox": list(d.bbox)} for d in det_result.detections]),
         json.dumps({"pci": pci_result.pci_value, "rating": pci_result.rating, "cdv": pci_result.cdv, "tdv": pci_result.tdv, "q": pci_result.q})),
    )
    conn.commit()
    conn.close()
    st.session_state["history"].append({
        "ts": datetime.now().isoformat(timespec="seconds"), "source": source,
        "file": file_name, "detections": len(det_result.detections),
        "pci": pci_result.pci_value, "rating": pci_result.rating,
        "infer_ms": det_result.inference_time_ms,
    })


# =============================================================================
# Pre-flight check
# =============================================================================
def preflight_check() -> tuple[bool, list[str]]:
    warnings = []
    ok = True
    if not eb.DEFAULT_MODEL_PATH.exists():
        warnings.append(f"⚠ {_t('model_ready')}: {eb.DEFAULT_MODEL_PATH}")
        ok = False
    if not eb.DEFAULT_PCI_DATA.exists():
        warnings.append(f"⚠ {_t('pci_ready')}: {eb.DEFAULT_PCI_DATA}")
        ok = False
    return ok, warnings


# =============================================================================
# Platform + Drive helpers
# =============================================================================
def _is_colab() -> bool:
    return os.path.isdir("/content")


def _is_drive_mounted() -> bool:
    return os.path.isdir("/content/drive/MyDrive")


def _list_drive_subdirs(folder_path: str) -> list[str]:
    p = Path(folder_path)
    if not p.exists() or not p.is_dir():
        return []
    return sorted([str(f) for f in p.iterdir() if f.is_dir() and not f.name.startswith(".")])


def _list_drive_all_files(folder_path: str, file_type: str = "image") -> list[dict]:
    p = Path(folder_path)
    if not p.exists() or not p.is_dir():
        return []
    img_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    vid_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    all_exts = img_exts | vid_exts if file_type == "batch" else (vid_exts if file_type == "video" else img_exts)
    files = []
    for f in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if f.is_dir() and not f.name.startswith("."):
            files.append({"name": f.name, "path": str(f), "size": 0, "is_dir": True})
        elif f.is_file() and f.suffix.lower() in all_exts:
            try:
                size = f.stat().st_size
            except Exception:
                size = 0
            files.append({"name": f.name, "path": str(f), "size": size, "is_dir": False})
    return files


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024: return f"{size_bytes} B"
    elif size_bytes < 1024*1024: return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024*1024*1024: return f"{size_bytes/(1024*1024):.1f} MB"
    else: return f"{size_bytes/(1024*1024*1024):.2f} GB"


def _download_from_url(url: str, suffix: str = ".jpg") -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        urllib.request.urlretrieve(url, tmp.name)
        return Path(tmp.name)
    except Exception as e:
        Path(tmp.name).unlink(missing_ok=True)
        raise RuntimeError(f"URL download failed: {e}")


# =============================================================================
# Annotation + rendering helpers
# =============================================================================
def annotate_image_pil(image: Image.Image, detection_result, show_legend: bool = True) -> Image.Image:
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    font = None
    for fp in ["arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf"]:
        try:
            font = ImageFont.truetype(fp, max(12, img.height // 45))
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()
    for det in detection_result.detections:
        x1, y1, x2, y2 = det.bbox
        color = CODE_COLORS_RGB.get(det.code, (100, 100, 100))
        lw = max(2, img.width // 400)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=lw)
        label = f"{det.code} {det.confidence:.2f}"
        bbox_label = draw.textbbox((x1, max(0, y1 - 18)), label, font=font)
        draw.rectangle(bbox_label, fill=color)
        draw.text((x1, max(0, y1 - 18)), label, fill="white", font=font)
    if show_legend and detection_result.detections:
        codes = sorted({d.code for d in detection_result.detections})
        lx, ly = img.width - 180, 10
        draw.rectangle([lx - 8, ly - 6, lx + 170, ly + 6 + 22 * len(codes)], fill=(0, 0, 0, 200), outline=(255, 255, 255))
        for i, code in enumerate(codes):
            rgb = CODE_COLORS_RGB.get(code, (100, 100, 100))
            draw.rectangle([lx, ly + i * 22, lx + 16, ly + i * 22 + 14], fill=rgb)
            draw.text((lx + 22, ly + i * 22), f"{code} {_type_name(code)}", fill="white", font=font)
    return img


def pci_gauge_html(pci_value: float, rating: str, color: str) -> str:
    angle = 180 - (pci_value / 100.0) * 180
    rad = np.deg2rad(angle)
    cx, cy, r = 110, 110, 90
    x = cx + r * np.cos(rad)
    y = cy - r * np.sin(rad)
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
        <text x="{cx}" y="{cy + 28}" text-anchor="middle" font-size="28" font-weight="bold" fill="{color}">{pci_value:.1f}</text>
        <text x="{cx}" y="{cy + 48}" text-anchor="middle" font-size="12" fill="{color}" font-weight="600">{_rating_name(rating)}</text>
      </svg>
    </div>
    """


def pipeline_indicator_html(active_step: int) -> str:
    steps = [("pipeline_collect", "📥"), ("pipeline_detect", "🔍"), ("pipeline_assess", "📐"), ("pipeline_report", "📄"), ("pipeline_recommend", "🛠️")]
    parts = []
    for i, (key, emoji) in enumerate(steps, 1):
        cls = "active" if i == active_step else ("done" if i < active_step else "pending")
        parts.append(f'<span class="pipeline-step {cls}">{emoji} {i}. {_t(key)}</span>')
        if i < len(steps):
            parts.append('<span class="pipeline-arrow">→</span>')
    return '<div style="text-align:center; padding: 4px 0;">' + "".join(parts) + "</div>"


def detections_to_rows(det_result) -> list[dict]:
    rows = []
    for i, det in enumerate(det_result.detections, 1):
        x1, y1, x2, y2 = det.bbox
        rows.append({"#": i, "Mã ASTM": det.code, "Loại hư hỏng": _type_name(det.code),
                      "Confidence": f"{det.confidence:.3f}",
                      "Bbox": f"({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f})",
                      "PCI": "✓" if det.include_in_pci else "✗"})
    return rows


def pci_damage_rows(pci_result) -> list[dict]:
    return [{"Mã": d.code, "Loại": _type_name(d.code), "Mức độ": _severity_name(d.severity),
             "Mật độ (%)": f"{d.density_pct:.3f}", "GT khấu trừ": f"{d.deduct_value:.2f}",
             "Diện tích (ft²)": f"{d.corrected_area_sqft:.2f}", "Confidence": f"{d.confidence:.2f}"}
            for d in pci_result.damages]


def damage_summary_html(det_result) -> str:
    counts = Counter(d.code for d in det_result.pci_detections)
    if not counts:
        return f"<em>{_t('no_detections')}</em>"
    html = ""
    for code, count in sorted(counts.items()):
        rgb = CODE_COLORS_RGB.get(code, (100, 100, 100))
        hex_c = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        html += f'<span class="damage-tag" style="background:{hex_c}">{code} · {_type_name(code)}: {count}</span>'
    return html


def run_inference(image_path, source: str, file_name: str):
    detector = get_detector(st.session_state["confidence"], st.session_state["device"])
    pci_engine = get_pci_engine(st.session_state["sample_unit_area"])
    t0 = time.time()
    det_result = detector.detect(image_path)
    t1 = time.time()
    pci_input = eb.detections_to_pci_input(det_result)
    pci_result = pci_engine.calculate_pci(pci_input, image_area_px=det_result.image_shape[0] * det_result.image_shape[1])
    _save_history(source, file_name, det_result, pci_result)
    return det_result, pci_result, (t1 - t0) * 1000


# =============================================================================
# Drive browser — breadcrumb + subfolders + thumbnail grid
# =============================================================================
def _drive_breadcrumb(current_path: str, key_suffix: str) -> str:
    parts = Path(current_path).parts
    cols = st.columns(min(len(parts), 8))
    selected = current_path
    for i in range(len(parts)):
        partial = str(Path(*parts[:i+1]))
        with cols[i]:
            label = "🏠" if parts[i] == "/" else (parts[i][:12] + "…" if len(parts[i]) > 12 else parts[i])
            if st.button(label, key=f"bc_{key_suffix}_{i}", help=partial, use_container_width=True):
                selected = partial
    return selected


def _drive_thumbnail_grid(files: list[dict], file_type: str, key_suffix: str, multi: bool = False):
    file_items = [f for f in files if not f["is_dir"]]
    if not file_items:
        st.info(f"📭 {_t('no_files')}")
        return None if not multi else []

    n_cols = min(4, len(file_items))
    cols = st.columns(n_cols)
    selected_paths = []
    for idx, f in enumerate(file_items):
        with cols[idx % n_cols]:
            try:
                if file_type == "video":
                    # Video thumbnail — fast: just read first frame, timeout 3s
                    cap = cv2.VideoCapture(f["path"])
                    # Set timeout-ish: only try 1 read, don't seek
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        thumb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        thumb.thumbnail((150, 150))
                        st.image(thumb, width=150)
                    else:
                        st.markdown("🎬")
                elif file_type == "image" or file_type == "batch":
                    # Image thumbnail — fast
                    thumb = Image.open(f["path"])
                    thumb.thumbnail((150, 150))
                    st.image(thumb, width=150)
                else:
                    st.markdown("📄")
            except Exception as e:
                # Fallback: show icon instead of crashing/hanging
                st.markdown("🎬" if file_type == "video" else "�️")
            st.caption(f"**{f['name'][:18]}**{'…' if len(f['name']) > 18 else ''}\n{_format_size(f['size'])}")
            if multi:
                if st.checkbox("✓", key=f"fsel_{key_suffix}_{idx}", value=False):
                    selected_paths.append(f["path"])
            else:
                if st.button("✓", key=f"fsel_{key_suffix}_{idx}", help=f["name"]):
                    return f["path"]
    return selected_paths if multi else None


def _render_drive_browser(file_type: str, key_suffix: str):
    """Render Drive browser. Returns selected path(s) or None."""
    if not _is_colab():
        st.warning("⚠️ Google Drive chỉ khả dụng trên Colab.")
        return None
    if not _is_drive_mounted():
        st.info("📁 Google Drive chưa mount. Chạy cell 'Mount Google Drive' trong colab_setup.ipynb, rồi refresh.")
        st.code("from google.colab import drive\ndrive.mount('/content/drive')", language="python")
        return None

    ss_key = f"drive_path_{key_suffix}"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = "/content/drive/MyDrive"
    current = st.session_state[ss_key]

    # Breadcrumb
    new_path = _drive_breadcrumb(current, key_suffix)
    if new_path != current:
        st.session_state[ss_key] = new_path
        st.rerun()

    # Subfolders
    subdirs = _list_drive_subdirs(current)
    if subdirs:
        st.markdown(f"**{_t('subfolders')}**")
        dc = st.columns(min(5, len(subdirs)))
        for idx, sd in enumerate(subdirs):
            with dc[idx % len(dc)]:
                nm = Path(sd).name
                if st.button(f"📂 {nm[:13]}{'…' if len(nm) > 13 else ''}", key=f"dir_{key_suffix}_{idx}", help=sd, use_container_width=True):
                    st.session_state[ss_key] = sd
                    st.rerun()

    # Manual path
    with st.expander(f"🔧 {_t('enter_path')}", expanded=False):
        mp = st.text_input("Path", value=current, key=f"manual_{key_suffix}")
        if st.button("→", key=f"go_{key_suffix}") and mp != current:
            if Path(mp).exists():
                st.session_state[ss_key] = mp
                st.rerun()
            else:
                st.error(f"❌ {_t('path_not_exist')}")

    # File grid
    st.markdown(f"**📄 {_t('files_in')} `{Path(current).name}`:**")
    all_files = _list_drive_all_files(current, file_type)
    return _drive_thumbnail_grid(all_files, file_type, key_suffix, multi=(file_type == "batch"))


# =============================================================================
# Source selector — Upload / URL / Drive → sets session state
# =============================================================================
def _render_source_selector():
    """Render input bar: type + source. Sets session state on file selection."""
    is_vi = st.session_state["lang"] == "vi"
    processing = st.session_state.get("is_processing", False)

    if processing:
        st.info("⏳ " + ("Đang xử lý video — không thể thay đổi nguồn. Nhấn DỪNG để hủy." if is_vi else "Processing video — cannot change source. Click STOP to abort."))
        return

    # Row 1: Type + Source (segmented)
    c_type, c_src = st.columns([2, 2])
    with c_type:
        st.markdown(f"**{_t('type_label')}**")
        type_opts = {"video": _t("type_video"), "image": _t("type_image"), "batch": _t("type_batch")}
        st.session_state["sel_type"] = st.radio(
            "Type", options=list(type_opts.keys()),
            format_func=lambda x: type_opts[x], horizontal=True, key="radio_type", label_visibility="collapsed")
    with c_src:
        st.markdown(f"**{_t('source_label')}**")
        src_opts = {"upload": _t("src_upload"), "url": _t("src_url"), "drive": _t("src_drive")}
        st.session_state["sel_source"] = st.radio(
            "Source", options=list(src_opts.keys()),
            format_func=lambda x: src_opts[x], horizontal=True, key="radio_src", label_visibility="collapsed")

    sel_type = st.session_state["sel_type"]
    sel_source = st.session_state["sel_source"]

    # Row 2: Source-specific input
    if sel_source == "upload":
        if sel_type == "video":
            up = st.file_uploader(_t("src_upload"), type=["mp4", "avi", "mov", "mkv", "webm"], key="up_vid")
            if up:
                tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                tmp.write(up.read())
                st.session_state["sel_file_path"] = Path(tmp.name)
                st.session_state["sel_file_name"] = up.name
                st.session_state["sel_video_path"] = Path(tmp.name)
                st.session_state["sel_pil"] = None
                st.session_state["sel_batch_paths"] = []
        elif sel_type == "batch":
            ups = st.file_uploader(_t("src_upload"), type=["jpg", "jpeg", "png", "bmp", "tiff"], accept_multiple_files=True, key="up_batch")
            if ups:
                paths, pils = [], []
                for f in ups:
                    img = Image.open(f)
                    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    img.convert("RGB").save(tmp.name, "JPEG")
                    paths.append(Path(tmp.name))
                    pils.append(img)
                st.session_state["sel_batch_paths"] = paths
                st.session_state["sel_batch_pils"] = pils
                st.session_state["sel_file_name"] = f"batch_{len(paths)}"
                st.session_state["sel_file_path"] = None
                st.session_state["sel_pil"] = None
                st.session_state["sel_video_path"] = None
        else:  # image
            up = st.file_uploader(_t("src_upload"), type=["jpg", "jpeg", "png", "bmp", "tiff", "webp"], key="up_img")
            if up:
                pil = Image.open(up)
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                pil.convert("RGB").save(tmp.name, "JPEG")
                st.session_state["sel_file_path"] = Path(tmp.name)
                st.session_state["sel_file_name"] = up.name
                st.session_state["sel_pil"] = pil
                st.session_state["sel_video_path"] = None
                st.session_state["sel_batch_paths"] = []

    elif sel_source == "url":
        url = st.text_input("URL", placeholder="https://example.com/road.jpg", key="url_input")
        if url:
            suffix = ".mp4" if sel_type == "video" else ".jpg"
            try:
                fp = _download_from_url(url, suffix=suffix)
                st.session_state["sel_file_path"] = fp
                st.session_state["sel_file_name"] = url.split("/")[-1][:50] or "url_input"
                if sel_type == "video":
                    st.session_state["sel_video_path"] = fp
                    st.session_state["sel_pil"] = None
                else:
                    st.session_state["sel_pil"] = Image.open(fp)
                    st.session_state["sel_video_path"] = None
                st.session_state["sel_batch_paths"] = []
                st.success(f"✓ {st.session_state['sel_file_name']}")
            except Exception as e:
                st.error(f"❌ {e}")

    elif sel_source == "drive":
        result = _render_drive_browser(sel_type, sel_type)
        if result:
            if sel_type == "batch":
                st.session_state["sel_batch_paths"] = [Path(p) for p in result]
                st.session_state["sel_batch_pils"] = [Image.open(p) for p in result]
                st.session_state["sel_file_name"] = f"drive_batch_{len(result)}"
                st.session_state["sel_file_path"] = None
                st.session_state["sel_pil"] = None
                st.session_state["sel_video_path"] = None
            else:
                st.session_state["sel_file_path"] = Path(result)
                st.session_state["sel_file_name"] = Path(result).name
                if sel_type == "video":
                    st.session_state["sel_video_path"] = Path(result)
                    st.session_state["sel_pil"] = None
                else:
                    st.session_state["sel_pil"] = Image.open(result)
                    st.session_state["sel_video_path"] = None
                st.session_state["sel_batch_paths"] = []

    # Sample picker (fallback — from dumps/data/samples)
    if sel_type != "video" and not st.session_state.get("sel_file_path") and not st.session_state.get("sel_batch_paths"):
        samples = sorted(eb.DUMPS_SAMPLES.glob("*.jpg")) if eb.DUMPS_SAMPLES.exists() else []
        if samples:
            with st.expander("🖼️ " + ("Ảnh mẫu" if is_vi else "Sample images"), expanded=False):
                sc = st.columns(min(4, len(samples)))
                for idx, s in enumerate(samples):
                    with sc[idx % len(sc)]:
                        thumb = Image.open(s)
                        thumb.thumbnail((100, 100))
                        st.image(thumb, width=100)
                        if st.button("✓", key=f"sample_{idx}", help=s.name):
                            st.session_state["sel_file_path"] = s
                            st.session_state["sel_file_name"] = s.name
                            st.session_state["sel_pil"] = Image.open(s)
                            st.session_state["sel_video_path"] = None
                            st.session_state["sel_batch_paths"] = []
                            st.rerun()


# =============================================================================
# Preview area + Config panel — main content (state lock)
# =============================================================================
def _render_preview_and_config():
    """Render preview (left) + config (right). State lock via session_state."""
    sel_type = st.session_state["sel_type"]
    has_file = (st.session_state.get("sel_file_path") or
                st.session_state.get("sel_video_path") or
                st.session_state.get("sel_batch_paths"))

    col_preview, col_config = st.columns([2.5, 1])

    with col_config:
        # Config panel (always visible)
        st.markdown(f'<div class="config-card">', unsafe_allow_html=True)
        st.markdown(f"### {_t('config_title')}")

        st.session_state["confidence"] = st.slider(
            _t("conf_threshold"), 0.05, 0.50, st.session_state["confidence"], 0.01,
            help="RDD2022: 0.10–0.20")

        st.session_state["sample_unit_area"] = st.number_input(
            _t("sample_area"), 500.0, 20000.0, st.session_state["sample_unit_area"], 500.0,
            help="ASTM D6433: 5000 ft²")

        st.session_state["device"] = st.selectbox(
            _t("device"), ["cpu", "cuda"],
            format_func=lambda x: "CPU" if x == "cpu" else "CUDA (GPU)",
            index=0 if st.session_state["device"] == "cpu" else 1)

        if sel_type == "video":
            st.markdown("---")
            st.session_state["video_stride"] = st.number_input(_t("video_stride"), 1, 60, st.session_state["video_stride"], 1)
            st.session_state["video_max"] = st.number_input(_t("video_max"), 0, 1000, st.session_state["video_max"], 10)
            st.session_state["video_overlay"] = st.checkbox(_t("video_overlay"), st.session_state["video_overlay"])
            st.session_state["video_fps"] = st.number_input(_t("video_fps"), 0, 60, st.session_state["video_fps"], 1)

        st.session_state["show_legend"] = st.checkbox(_t("show_legend"), st.session_state["show_legend"])
        st.session_state["use_segmentation"] = st.checkbox(_t("use_segmentation"), st.session_state["use_segmentation"])

        # Pre-flight check (compact)
        pf_ok, _ = preflight_check()
        if pf_ok:
            st.caption(f"✓ {_t('pre_flight')}: {_t('model_ready')} + {_t('pci_ready')}")

        # Process button
        st.markdown("---")
        if sel_type == "video":
            btn_label = _t("btn_process_video")
        elif sel_type == "batch":
            btn_label = _t("btn_process_batch")
        else:
            btn_label = _t("btn_process_image")
        if not has_file:
            st.button(btn_label, type="primary", disabled=True, help=_t("no_file"))
        else:
            if st.button(btn_label, type="primary", key="btn_process"):
                _do_process()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_preview:
        # Preview — state lock (renders from session_state, not file picker)
        if not has_file:
            st.info(f"👆 {_t('no_image_loaded')}")
            return

        if sel_type == "video":
            # After processing: show annotated video. Before: show original.
            annotated = st.session_state.get("last_video_annotated")
            if annotated and Path(annotated).exists():
                st.markdown(f"**🎬 {_t('done')} — {_t('results_title')}**")
                st.video(annotated)
            else:
                vp = st.session_state.get("sel_video_path") or st.session_state.get("sel_file_path")
                if vp and Path(vp).exists():
                    st.video(str(vp))
            # File info (always show)
            vp_info = st.session_state.get("sel_video_path") or st.session_state.get("sel_file_path")
            if vp_info and Path(vp_info).exists():
                cap = cv2.VideoCapture(str(vp_info))
                if cap.isOpened():
                    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS) or 0
                    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    dur = total / fps if fps > 0 else 0
                    cap.release()
                    st.markdown(f"""
                    <div class="file-info">
                    📋 <b>{st.session_state['sel_file_name']}</b><br/>
                    📐 {w}×{h} @ {fps:.0f}fps · ⏱️ {dur:.0f}s · 📦 {_format_size(Path(vp_info).stat().st_size)}
                    </div>
                    """, unsafe_allow_html=True)

        elif sel_type == "batch":
            paths = st.session_state.get("sel_batch_paths", [])
            pils = st.session_state.get("sel_batch_pils", [])
            if paths:
                st.markdown(f"**📁 {len(paths)} {_t('detections').lower()}**")
                nc = min(5, len(paths))
                bc = st.columns(nc)
                for idx, (p, pil) in enumerate(zip(paths, pils)):
                    with bc[idx % nc]:
                        thumb = pil.copy()
                        thumb.thumbnail((120, 120))
                        st.image(thumb, width=120)
                        st.caption(Path(p).name[:18])

        else:  # image
            pil = st.session_state.get("sel_pil")
            if pil:
                st.image(pil, width=600)
                st.markdown(f"""
                <div class="file-info">
                📋 <b>{st.session_state['sel_file_name']}</b> · 📐 {pil.size[0]}×{pil.size[1]}
                </div>
                """, unsafe_allow_html=True)


def _do_process():
    """Run inference based on selected type. Stores results in session_state."""
    sel_type = st.session_state["sel_type"]
    fname = st.session_state["sel_file_name"]

    if sel_type == "video":
        _do_process_video()
    elif sel_type == "batch":
        _do_process_batch()
    else:
        _do_process_image()


def _do_process_image():
    fp = st.session_state.get("sel_file_path")
    if not fp:
        return
    with st.spinner(f"⏳ {_t('processing')}..."):
        det, pci, elapsed = run_inference(fp, "image", st.session_state["sel_file_name"])
    pil = st.session_state.get("sel_pil")
    anno = annotate_image_pil(pil, det, show_legend=st.session_state["show_legend"]) if pil else None
    st.session_state["last_det"] = det
    st.session_state["last_pci"] = pci
    st.session_state["last_annotated"] = anno
    st.session_state["last_source_name"] = st.session_state["sel_file_name"]
    st.session_state["last_elapsed_ms"] = elapsed
    st.session_state["last_batch_results"] = []


def _do_process_video():
    vp = st.session_state.get("sel_video_path") or st.session_state.get("sel_file_path")
    if not vp:
        return
    detector = get_detector(st.session_state["confidence"], st.session_state["device"])
    pci_engine = get_pci_engine(st.session_state["sample_unit_area"])
    cap = cv2.VideoCapture(str(vp))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    stride = st.session_state["video_stride"]
    max_f = st.session_state["video_max"]
    out_path = Path(tempfile.gettempdir()) / "annotated_video.mp4"
    out = None
    for codec in ["avc1", "H264", "mp4v"]:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
        if out.isOpened(): break
    if not out or not out.isOpened():
        st.error("❌ VideoWriter codec fail")
        cap.release()
        return

    # Set processing flag — disables other widgets
    st.session_state["is_processing"] = True

    # Calculate max frames BEFORE rendering progress (needed for ETA display)
    max_proc = max_f if max_f > 0 else total // stride

    # Progress + Console — single column below video (compact, no warning column)
    progress_container = st.container()
    with progress_container:
        st.markdown("---")
        progress = st.progress(0.0, text=f"⏳ {_t('processing')}... (~{(max_proc * 1.5):.0f}s)" if max_proc else f"⏳ {_t('processing')}...")
        st.caption("⚠️ " + ("Đang xử lý — vui lòng đợi, không chuyển tab" if st.session_state["lang"] == "vi" else "Processing — please wait, don't switch tabs"))

    # Console area (real-time log below progress)
    console_container = st.container()
    with console_container:
        console_exp = st.expander("📜 " + ("Console (real-time)", "Console (real-time)")[st.session_state["lang"] == "en"], expanded=True)
        console_placeholder = console_exp.empty()

    pci_series = []
    frame_idx = 0
    processed = 0
    t0 = time.time()
    log_lines = []

    # last_annotated_frame: keep last annotated frame to replay for skip frames
    # This preserves video timeline (every frame written, not just processed ones)
    last_annotated_frame = None
    stop_processing = False

    while True:
        ret, frame = cap.read()
        if not ret:
            log_lines.append(f"[{time.strftime('%H:%M:%S')}] ✅ End of video at frame {frame_idx}")
            break

        if frame_idx % stride == 0 and not stop_processing:
            if processed >= max_proc:
                stop_processing = True
                log_lines.append(f"[{time.strftime('%H:%M:%S')}] ✅ Max frames ({max_proc}) reached — replaying last annotated for remaining frames")
            else:
                tmp_f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                cv2.imwrite(tmp_f.name, frame)
                try:
                    det = detector.detect(tmp_f.name)
                    pci_in = eb.detections_to_pci_input(det)
                    pci_res = pci_engine.calculate_pci(pci_in, image_area_px=det.image_shape[0]*det.image_shape[1])
                    _save_history("video", f"frame_{frame_idx}", det, pci_res)
                    pci_series.append({"frame": frame_idx, "pci": pci_res.pci_value, "detections": len(det.detections), "rating": pci_res.rating, "infer_ms": det.inference_time_ms})
                    log_lines.append(f"[{time.strftime('%H:%M:%S')}] F{frame_idx}/{total} — PCI {pci_res.pci_value:.1f} ({pci_res.rating}) — {len(det.detections)} det — {det.inference_time_ms:.0f}ms")
                    # Annotate
                    for d in det.detections:
                        x1, y1, x2, y2 = [int(v) for v in d.bbox]
                        bgr = CODE_COLORS_BGR.get(d.code, (100, 100, 100))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), bgr, 2)
                        cv2.rectangle(frame, (x1, y1-22), (x1+120, y1), bgr, -1)
                        cv2.putText(frame, f"{d.code} {d.confidence:.2f}", (x1+4, y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1)
                    if st.session_state["video_overlay"]:
                        pcibgr = {"Good":(46,204,113),"Satisfactory":(39,174,96),"Fair":(15,196,241),"Poor":(14,126,230),"Very Poor":(44,62,231),"Failed":(59,23,192)}.get(pci_res.rating, (100,100,100))
                        cv2.rectangle(frame, (0,0), (320,70), (0,0,0), -1)
                        cv2.putText(frame, f"PCI: {pci_res.pci_value:.1f} ({pci_res.rating})", (10,28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, pcibgr, 2)
                        cv2.putText(frame, f"Det: {len(det.detections)} | F: {frame_idx}/{total}", (10,55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
                    last_annotated_frame = frame.copy()
                    out.write(frame)
                    processed += 1
                except Exception as e:
                    log_lines.append(f"[{time.strftime('%H:%M:%S')}] ⚠️ F{frame_idx}: {e}")
                    st.warning(f"Frame {frame_idx}: {e}")
                    out.write(frame)  # write unannotated on error
                Path(tmp_f.name).unlink(missing_ok=True)
                elapsed = time.time() - t0
                eta = (elapsed/processed)*(max_proc-processed) if processed else 0
                progress.progress(processed/max_proc, text=f"⏳ Frame {frame_idx}/{total} — PCI {pci_res.pci_value:.1f} ({pci_res.rating}) — {processed}/{max_proc} — ETA {eta:.0f}s")
                with console_placeholder:
                    st.code("\n".join(log_lines[-15:]), language="text")
        else:
            # Skip frame (not in stride) or past max_proc — write to preserve timeline
            if last_annotated_frame is not None:
                out.write(last_annotated_frame)
            else:
                out.write(frame)  # original frame if no annotated yet
        frame_idx += 1
    cap.release()
    out.release()
    progress.empty()
    st.session_state["is_processing"] = False

    st.session_state["last_batch_results"] = []
    st.session_state["last_video_annotated"] = str(out_path)
    st.session_state["last_pci_series"] = pci_series
    st.session_state["last_source_name"] = st.session_state["sel_file_name"]
    st.success(f"✓ {processed} frames in {time.time()-t0:.1f}s")


def _do_process_batch():
    paths = st.session_state.get("sel_batch_paths", [])
    if not paths:
        return
    pils = st.session_state.get("sel_batch_pils", [])
    progress = st.progress(0.0, text=f"{_t('processing')}...")
    results = []
    for i, (p, pil) in enumerate(zip(paths, pils)):
        try:
            det, pci, _ = run_inference(p, "batch", Path(p).name)
            results.append({"file": Path(p).name, "det": det, "pci": pci, "pil": pil})
        except Exception as e:
            st.warning(f"{Path(p).name}: {e}")
        progress.progress((i+1)/len(paths), text=f"{i+1}/{len(paths)}: {Path(p).name[:30]}")
    progress.empty()
    st.session_state["last_batch_results"] = results
    st.session_state["last_det"] = None
    st.session_state["last_pci"] = None
    st.session_state["last_source_name"] = f"batch_{len(results)}"


# =============================================================================
# Results area — PCI gauge + detections + chart + recommendation + export
# =============================================================================
def _render_results():
    """Render results from session_state (state lock)."""
    sel_type = st.session_state["sel_type"]

    # Video results — video already shown in preview area, here only chart + downloads
    if sel_type == "video" and st.session_state.get("last_pci_series"):
        st.markdown(f"---")
        st.markdown(f"### {_t('results_title')}")
        pipeline_indicator_html(4)

        # PCI time-series
        series = st.session_state.get("last_pci_series", [])
        if series:
            df = pd.DataFrame(series)
            col_chart, col_table = st.columns([2, 1])
            with col_chart:
                st.markdown(f"**📈 PCI {_t('pipeline_detect').lower()}**")
                st.line_chart(df.set_index("frame")["pci"])
            with col_table:
                st.dataframe(df, use_container_width=True, hide_index=True)
            # Downloads
            c1, c2 = st.columns(2)
            with c1:
                with open(st.session_state["last_video_annotated"], "rb") as f:
                    st.download_button("📥 Video MP4", f.read(), file_name="annotated.mp4", mime="video/mp4")
            with c2:
                st.download_button("📥 PCI CSV", df.to_csv(index=False).encode("utf-8"), file_name="pci_timeseries.csv", mime="text/csv")
        pipeline_indicator_html(5)
        return

    # Batch results
    if sel_type == "batch" and st.session_state.get("last_batch_results"):
        st.markdown("---")
        st.markdown(f"### {_t('results_title')}")
        pipeline_indicator_html(4)
        results = st.session_state["last_batch_results"]

        # Per-image table
        st.markdown(f"**📋 {_t('batch_results')}**")
        rows = [{"File": r["file"], "Detections": len(r["det"].detections),
                 "PCI": f"{r['pci'].pci_value:.1f}", "Rating": _rating_name(r["pci"].rating)}
                for r in results]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Section PCI
        pci_engine = get_pci_engine(st.session_state["sample_unit_area"])
        try:
            sec = pci_engine.calculate_section_pci([r["pci"] for r in results])
        except Exception:
            sec = None
        if sec and hasattr(sec, "pci_value"):
            col_s1, col_s2 = st.columns([1, 2])
            with col_s1:
                st.markdown(f"### {_t('section_pci')}")
                st.markdown(pci_gauge_html(sec.pci_value, sec.rating, sec.pci_color), unsafe_allow_html=True)
            with col_s2:
                st.markdown(f"**{sec.maintenance_action}**")
                st.caption(sec.maintenance_detail)

        # Gallery
        st.markdown(f"**📁 {_t('gallery')}**")
        nc = min(5, len(results))
        bc = st.columns(nc)
        for idx, r in enumerate(results):
            with bc[idx % nc]:
                anno = annotate_image_pil(r["pil"], r["det"], show_legend=st.session_state["show_legend"])
                st.image(anno, width=150)
                st.caption(f"{r['file'][:15]}… PCI {r['pci'].pci_value:.1f}")
        pipeline_indicator_html(5)
        return

    # Single image results
    det = st.session_state.get("last_det")
    pci = st.session_state.get("last_pci")
    anno = st.session_state.get("last_annotated")
    if not det or not pci:
        return

    st.markdown("---")
    st.markdown(f"### {_t('results_title')}")
    pipeline_indicator_html(4)

    # Annotated image
    if anno:
        col_orig, col_anno = st.columns(2)
        with col_orig:
            st.markdown(f"**{_t('file_name')}**")
            pil = st.session_state.get("sel_pil")
            if pil:
                st.image(pil, width=400)
        with col_anno:
            st.markdown(f"**🔍 {_t('pipeline_detect')}**")
            st.image(anno, width=400)

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(_t("detections"), len(det.detections))
    m2.metric(_t("inference_time"), f"{det.inference_time_ms:.0f}ms")
    m3.metric(_t("total_time"), f"{st.session_state.get('last_elapsed_ms', 0):.0f}ms")
    m4.metric(_t("file_dims"), f"{det.image_shape[1]}×{det.image_shape[0]}")

    # PCI + table
    col_pci, col_table = st.columns([1, 2])
    with col_pci:
        st.markdown(f"### {_t('pci_index')}")
        st.markdown(pci_gauge_html(pci.pci_value, pci.rating, pci.pci_color), unsafe_allow_html=True)
        st.markdown(f"**{_t('pci_cdv')}**: {pci.cdv:.2f} | **{_t('pci_tdv')}**: {pci.tdv:.2f} | **{_t('pci_q')}**: {pci.q}")
    with col_table:
        st.markdown(f"**📋 {_t('detection_table')}**")
        rows = detections_to_rows(det)
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info(_t("no_detections"))
        st.markdown(damage_summary_html(det), unsafe_allow_html=True)
        if pci.damages:
            with st.expander(f"📋 {_t('pci_breakdown')}"):
                st.dataframe(pd.DataFrame(pci_damage_rows(pci)), use_container_width=True, hide_index=True)

    # Recommendation
    pipeline_indicator_html(5)
    st.markdown(f"### {_t('rec_title')}")
    rc = pci.pci_color
    st.markdown(f"""
    <div class="recommend-box" style="border-left-color: {rc};">
      <strong style="color: {rc};">{_rating_name(pci.rating)} (PCI {pci.pci_value:.1f})</strong><br/>
      <strong>{pci.maintenance_action}</strong><br/>
      <em>{pci.maintenance_detail}</em>
    </div>
    """, unsafe_allow_html=True)

    # Export
    st.markdown(f"**{_t('export_title')}**")
    e1, e2, e3, e4, e5 = st.columns(5)
    with e1:
        if anno:
            buf = io.BytesIO(); anno.save(buf, format="PNG")
            st.download_button(_t("export_png"), buf.getvalue(), file_name=f"{Path(st.session_state['last_source_name']).stem}_annotated.png", mime="image/png")
    with e2:
        if rows:
            st.download_button(_t("export_csv"), pd.DataFrame(rows).to_csv(index=False).encode("utf-8"), file_name="detections.csv", mime="text/csv")
    with e3:
        pci_json = json.dumps({"pci": pci.pci_value, "rating": pci.rating, "cdv": pci.cdv, "damages": [{"code": d.code, "severity": d.severity} for d in pci.damages]}, ensure_ascii=False, indent=2)
        st.download_button(_t("export_json"), pci_json.encode("utf-8"), file_name="pci.json", mime="application/json")
    with e4:
        md = f"# PCI Report\n\nPCI: {pci.pci_value:.1f} ({_rating_name(pci.rating)})\nCDV: {pci.cdv:.2f}\n\n**{pci.maintenance_action}**\n{pci.maintenance_detail}\n"
        st.download_button(_t("export_md"), md.encode("utf-8"), file_name="report.md", mime="text/markdown")
    with e5:
        if st.button(_t("rerun"), key="rerun_btn"):
            _do_process_image()


# =============================================================================
# Bottom bar — Report / History / Settings / Console (expanders)
# =============================================================================
def _render_bottom_bar():
    """Render bottom bar with 4 expandable sections."""
    st.markdown("---")
    bt1, bt2, bt3, bt4 = st.columns(4)
    with bt1:
        if st.button(_t("tab_report"), key="btn_report", use_container_width=True):
            st.session_state["bottom_tab"] = "report" if st.session_state.get("bottom_tab") != "report" else None
    with bt2:
        if st.button(_t("tab_history"), key="btn_history", use_container_width=True):
            st.session_state["bottom_tab"] = "history" if st.session_state.get("bottom_tab") != "history" else None
    with bt3:
        if st.button(_t("tab_settings"), key="btn_settings", use_container_width=True):
            st.session_state["bottom_tab"] = "settings" if st.session_state.get("bottom_tab") != "settings" else None
    with bt4:
        if st.button(_t("tab_console"), key="btn_console", use_container_width=True):
            st.session_state["bottom_tab"] = "console" if st.session_state.get("bottom_tab") != "console" else None

    active = st.session_state.get("bottom_tab")
    if active == "report":
        _render_report_section()
    elif active == "history":
        _render_history_section()
    elif active == "settings":
        _render_settings_section()
    elif active == "console":
        _render_console_section()


def _render_report_section():
    with st.expander(_t("tab_report"), expanded=True):
        pci = st.session_state.get("last_pci")
        if not pci:
            st.info("👆 Run detection first, then export report here.")
            return
        st.markdown(f"**PCI**: {pci.pci_value:.1f} ({_rating_name(pci.rating)})")
        st.markdown(f"**CDV**: {pci.cdv:.2f} | **TDV**: {pci.tdv:.2f}")
        if pci.damages:
            st.dataframe(pd.DataFrame(pci_damage_rows(pci)), use_container_width=True, hide_index=True)
        st.download_button(_t("export_md"),
            f"# PCI Report\n\nPCI: {pci.pci_value:.1f}\nRating: {_rating_name(pci.rating)}\nCDV: {pci.cdv:.2f}\n\n{pci.maintenance_action}\n".encode("utf-8"),
            file_name="pci_report.md", mime="text/markdown")


def _render_history_section():
    with st.expander(_t("tab_history"), expanded=True):
        conn = _db_conn()
        df = pd.read_sql("SELECT ts, source, file_name, detections, pci, rating, inference_ms FROM analyses ORDER BY ts DESC LIMIT 200", conn)
        conn.close()
        if df.empty:
            st.info("📭 No analyses yet.")
            return
        m1, m2, m3 = st.columns(3)
        m1.metric("Total", len(df))
        m2.metric("Avg PCI", f"{df['pci'].mean():.1f}")
        m3.metric("Min PCI", f"{df['pci'].min():.1f}")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 CSV", df.to_csv(index=False).encode("utf-8"), file_name="history.csv")
        if st.button("🗑️ Clear", key="clear_hist"):
            conn = _db_conn(); conn.execute("DELETE FROM analyses"); conn.commit(); conn.close()
            st.session_state["history"] = []; st.rerun()


def _render_settings_section():
    with st.expander(_t("tab_settings"), expanded=True):
        st.markdown(f"**Model**: `{eb.DEFAULT_MODEL_PATH}`")
        st.markdown(f"**PCI data**: `{eb.DEFAULT_PCI_DATA}`")
        st.markdown(f"**DB**: `{st.session_state['db_path']}`")
        config = {k: st.session_state[k] for k in ["lang", "confidence", "sample_unit_area", "device", "use_segmentation", "show_legend"] if k in st.session_state}
        st.json(config)
        st.download_button("📥 Settings JSON", json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8"), file_name="settings.json")


def _render_console_section():
    with st.expander(_t("tab_console"), expanded=True):
        # Real-time log from session (if processing) + file log
        log_lines = []
        # Priority 1: session log (real-time during processing)
        if st.session_state.get("is_processing"):
            # During processing, console is shown inline below video — skip here
            st.info("⏳ " + ("Console đang hiển thị dưới video" if st.session_state["lang"] == "vi" else "Console shown below video during processing"))
        else:
            # Log file — read from /tmp first (outside Streamlit watch dir to prevent runOnSave loop),
            # then fallback to repo paths. Filter watchdog noise.
            log_sources = [
                Path("/tmp/road_damage_app.log"),
                Path(tempfile.gettempdir()) / "road_damage_app.log",
                Path("outputs/app.log"),
                eb._DUMPS_ROOT / "outputs" / "app.log",
                Path("/content/repo/outputs/app.log"),
            ]
            for lp in log_sources:
                if lp.exists():
                    try:
                        content = lp.read_text(encoding="utf-8", errors="replace").splitlines()
                        log_lines = [l for l in content if "watchdog" not in l.lower() and "inotify" not in l.lower()]
                        log_lines = log_lines[-200:]
                        break
                    except Exception:
                        pass
            if log_lines:
                st.code("\n".join(log_lines[-100:]), language="text")
            else:
                st.info("📭 " + ("Chưa có log. Chạy inference để sinh log." if st.session_state["lang"] == "vi" else "No logs yet. Run inference to generate."))
        # System info
        import platform
        sys_info = {"Python": platform.python_version(), "Platform": platform.platform(),
                    "Device": st.session_state["device"], "CUDA": False}
        try:
            import torch
            sys_info["CUDA"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                sys_info["GPU"] = torch.cuda.get_device_name(0)
                sys_info["GPU mem (GB)"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
        except Exception:
            pass
        st.json(sys_info)


# =============================================================================
# Main layout
# =============================================================================
# Top bar — title (left) + lang + pre-flight (right, compact)
c_title, c_right = st.columns([3, 1])
with c_title:
    st.markdown(f"### 🛣️ {_t('app_title')}")
    st.caption(f"{_t('app_subtitle')} · YOLOv12s + FastSAM + ASTM D6433")
with c_right:
    lo = {"vi": "🇻🇳 VI", "en": "🇬🇧 EN"}
    rc1, rc2 = st.columns(2)
    with rc1:
        st.session_state["lang"] = st.selectbox("🌐", options=list(lo.keys()), format_func=lambda x: lo[x], key="lang_sel", label_visibility="collapsed")
    with rc2:
        pf_ok, _ = preflight_check()
        if pf_ok:
            st.caption("✅ Ready")
        else:
            st.caption("⚠️ Check model")

# Pipeline indicator (top, small)
st.markdown(pipeline_indicator_html(1), unsafe_allow_html=True)

# Input bar
st.markdown('<div class="input-bar">', unsafe_allow_html=True)
_render_source_selector()
st.markdown('</div>', unsafe_allow_html=True)

# Preview + Config
_render_preview_and_config()

# Results
_render_results()

# Bottom bar
_render_bottom_bar()

# Pipeline indicator (bottom)
st.markdown(pipeline_indicator_html(5 if st.session_state.get("last_det") or st.session_state.get("last_batch_results") else 1), unsafe_allow_html=True)
