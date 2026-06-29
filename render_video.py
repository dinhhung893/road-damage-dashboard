"""Render annotated video — chạy YOLOv12s detection trên video, annotate bbox + PCI, xuất mp4.

Usage:
    python render_video.py --input video.mp4 --output annotated.mp4 --stride 5
    python render_video.py --input video.mp4 --output annotated.mp4 --stride 10 --max-frames 100

Trên Colab (GPU):
    python render_video.py --input video.mp4 --output annotated.mp4 --device cuda --stride 1
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

import engine_bridge as eb
from engine_bridge import CODE_COLORS_BGR


def render_video(
    input_path: str | Path,
    output_path: str | Path,
    confidence: float = 0.15,
    sample_unit_area_sqft: float = 5000.0,
    device: str = "cpu",
    stride: int = 5,
    max_frames: int = 0,
    use_segmentation: bool = False,
) -> dict:
    """Render annotated video. Returns stats dict."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    detector = eb.make_detector(confidence=confidence, device=device)
    pci_engine = eb.make_pci_engine(sample_unit_area_sqft=sample_unit_area_sqft)

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video: {w}x{h} @ {fps:.1f}fps, {total_frames} frames total")
    print(f"Stride: every {stride} frame → ~{total_frames // stride} frames to process")
    if max_frames:
        print(f"Max frames cap: {max_frames}")

    # Output writer — codec fallback: avc1/H264 (browser-compatible) → mp4v
    out = None
    for codec in ["avc1", "H264", "mp4v"]:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))
        if out.isOpened():
            print(f"Video codec: {codec}")
            break
    if not out.isOpened():
        raise RuntimeError(f"Cannot open VideoWriter with any codec (avc1/H264/mp4v) for {output_path}")

    frame_idx = 0
    processed = 0
    pci_series = []
    t_start = time.time()

    # Temp file for frame (engine expects path)
    import tempfile
    tmp_frame = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, prefix="frame_")
    tmp_frame_path = tmp_frame.name
    tmp_frame.close()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % stride == 0:
                if max_frames and processed >= max_frames:
                    break

                # Save frame to temp
                cv2.imwrite(tmp_frame_path, frame)

                # Detect
                det_res = detector.detect(tmp_frame_path)
                pci_in = eb.detections_to_pci_input(det_res)
                pci_res = pci_engine.calculate_pci(
                    pci_in,
                    image_area_px=det_res.image_shape[0] * det_res.image_shape[1],
                )

                pci_series.append({
                    "frame": frame_idx,
                    "pci": round(pci_res.pci_value, 2),
                    "detections": len(det_res.detections),
                    "rating": pci_res.rating,
                    "inference_ms": round(det_res.inference_time_ms, 1),
                })

                # Annotate frame
                for d in det_res.detections:
                    x1, y1, x2, y2 = [int(v) for v in d.bbox]
                    bgr = CODE_COLORS_BGR.get(d.code, (100, 100, 100))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), bgr, 2)
                    label = f"{d.code} {d.confidence:.2f}"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), bgr, -1)
                    cv2.putText(frame, label, (x1 + 2, y1 - 4),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # PCI overlay (top-left)
                overlay_h = 70
                cv2.rectangle(frame, (0, 0), (280, overlay_h), (0, 0, 0), -1)
                pci_color_bgr = {
                    "Good": (46, 204, 113),
                    "Satisfactory": (39, 174, 96),
                    "Fair": (15, 196, 241),
                    "Poor": (14, 126, 230),
                    "Very Poor": (44, 62, 231),
                    "Failed": (59, 23, 192),
                }.get(pci_res.rating, (100, 100, 100))
                cv2.putText(frame, f"PCI: {pci_res.pci_value:.1f}  ({pci_res.rating})",
                            (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, pci_color_bgr, 2)
                cv2.putText(frame, f"Detections: {len(det_res.detections)}  |  Frame: {frame_idx}/{total_frames}",
                            (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

                out.write(frame)
                processed += 1

                elapsed = time.time() - t_start
                eta = (elapsed / processed) * (min(max_frames, total_frames // stride) - processed) if processed else 0
                print(
                    f"  [{processed:4d}] frame {frame_idx:5d}/{total_frames} — "
                    f"PCI {pci_res.pci_value:5.1f} ({pci_res.rating:12s}) — "
                    f"{len(det_res.detections):2d} det — "
                    f"{det_res.inference_time_ms:5.0f}ms — "
                    f"ETA {eta:.0f}s"
                )

            frame_idx += 1
    finally:
        cap.release()
        out.release()
        Path(tmp_frame_path).unlink(missing_ok=True)

    elapsed = time.time() - t_start
    print(f"\nDone: {processed} frames processed in {elapsed:.1f}s")
    print(f"Output: {output_path}")

    # Stats
    avg_pci = sum(p["pci"] for p in pci_series) / len(pci_series) if pci_series else 0
    min_pci = min((p["pci"] for p in pci_series), default=0)
    max_pci = max((p["pci"] for p in pci_series), default=0)
    total_dets = sum(p["detections"] for p in pci_series)

    print(f"PCI: avg={avg_pci:.1f}, min={min_pci:.1f}, max={max_pci:.1f}")
    print(f"Total detections across frames: {total_dets}")

    # Save PCI time-series CSV
    csv_path = output_path.with_suffix(".pci.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("frame,pci,detections,rating,inference_ms\n")
        for p in pci_series:
            f.write(f"{p['frame']},{p['pci']},{p['detections']},{p['rating']},{p['inference_ms']}\n")
    print(f"PCI time-series CSV: {csv_path}")

    return {
        "processed": processed,
        "total_frames": total_frames,
        "elapsed_s": elapsed,
        "avg_pci": avg_pci,
        "min_pci": min_pci,
        "max_pci": max_pci,
        "total_detections": total_dets,
        "output_path": str(output_path),
        "csv_path": str(csv_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Render annotated road damage video")
    parser.add_argument("--input", "-i", required=True, help="Input video path")
    parser.add_argument("--output", "-o", required=True, help="Output video path")
    parser.add_argument("--confidence", "-c", type=float, default=0.15, help="Confidence threshold")
    parser.add_argument("--area", "-a", type=float, default=5000.0, help="Sample unit area (sqft)")
    parser.add_argument("--device", "-d", default="cpu", choices=["cpu", "cuda"], help="Inference device")
    parser.add_argument("--stride", "-s", type=int, default=5, help="Process every Nth frame")
    parser.add_argument("--max-frames", "-m", type=int, default=0, help="Max frames (0 = no limit)")
    parser.add_argument("--segmentation", action="store_true", help="Use FastSAM segmentation (T2)")
    args = parser.parse_args()

    stats = render_video(
        input_path=args.input,
        output_path=args.output,
        confidence=args.confidence,
        sample_unit_area_sqft=args.area,
        device=args.device,
        stride=args.stride,
        max_frames=args.max_frames,
        use_segmentation=args.segmentation,
    )
    print(f"\n=== SUMMARY ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
