# Road Damage Assessment — Web Dashboard (Adaptive)

Web dashboard cho đồ án tốt nghiệp: Hệ thống đánh giá hư hỏng mặt đường sử dụng Deep Learning + ASTM D6433 PCI.

Tái sử dụng engine từ `dumps/` (detector + PCI + segmenter) — không copy code, dùng `engine_bridge.py` wire qua sys.path.

## Cấu trúc

```
adaptive/
├── app.py                    # Streamlit dashboard (demo bảo vệ)
├── engine_bridge.py          # Wire engine từ dumps/
├── render_video.py           # Script CLI render video annotate
├── colab_setup.ipynb         # Notebook Colab PRO (GPU + tunnel)
├── de_cuong_chi_tiet.md      # Đề cương chi tiết 3 chương
├── tom_tat_trang_thai.md     # Tóm tắt trạng thái dự án
├── README.md                 # File này
└── outputs/
    ├── demo_annotated.mp4    # Video demo đã render (detection thật)
    ├── sample_input.mp4      # Video input (slideshow ảnh mẫu)
    └── demo_annotated.pci.csv # PCI time-series
```

## Chạy Streamlit (local)

```powershell
# Dùng venv của dumps (đã có đầy đủ deps)
cd D:\Antigravity\New folder\adaptive
D:\Antigravity\New folder\dumps\.venv\Scripts\python.exe -m streamlit run app.py
```

Mở browser: http://localhost:8501

### Tính năng
- **Tab Ảnh đơn:** upload ảnh → inference → bbox + PCI gauge + damage table
- **Tab Batch ảnh:** upload nhiều ảnh → batch inference → PCI cấp đoạn đường
- **Tab Video:** upload video → process → video annotate + PCI time-series
- **Tab Giới thiệu:** thông tin đồ án, kiến trúc, model

### Cấu hình (sidebar)
- Confidence threshold (0.05–0.50, mặc định 0.15)
- Diện tích mẫu đơn vị (ft², mặc định 5000)
- Thiết bị inference (cpu / cuda)
- FastSAM segmentation (T2) toggle

## Chạy trên Colab PRO (GPU)

1. Mở `colab_setup.ipynb` trong Google Colab
2. Runtime → Change runtime type → GPU (T4)
3. Chạy các cell theo thứ tự:
   - Cell 1: install deps
   - Cell 2-3: mount Drive / clone repo + patch paths
   - Cell 4-5: start Streamlit + cloudflared tunnel
   - Cell 6: click public URL (xxxx.trycloudflare.com)

**Lợi ích Colab:**
- GPU inference ~30-50ms/frame (vs 896ms CPU)
- Render video dài trong vài phút
- Public URL demo (chia sẻ với thầy)

**Rủi ro:** Colab session timeout (idle 90 phút, giới hạn 24h). Luôn có bản backup local.

## Render video demo (CLI)

```powershell
# Render từ video input
python render_video.py --input video.mp4 --output annotated.mp4 --stride 5 --max-frames 50

# Với GPU (Colab)
python render_video.py --input video.mp4 --output annotated.mp4 --device cuda --stride 1
```

Video output có:
- Bounding boxes + labels (D00/D10/D20/D40 + confidence)
- PCI overlay (giá trị + rating, đổi màu theo tình trạng)
- Frame counter

PCI time-series CSV xuất kèm (frame, pci, detections, rating, inference_ms).

## Demo cho giảng viên

### Cách 1: Streamlit local (khuyến nghị)
1. Chạy `streamlit run app.py`
2. Mở browser localhost:8501
3. Tab "Ảnh đơn" → chọn ảnh mẫu `real_damage_03` → xem bbox + PCI
4. Tab "Video" → upload `outputs/sample_input.mp4` → process → xem video annotate
5. Tab "Giới thiệu" → thuyết trình kiến trúc + model

### Cách 2: Video demo có sẵn
- Mở `outputs/demo_annotated.mp4` (442KB, 18 frame)
- Detection thật: 3 ổ gà (D40) trên frames 6-8, PCI 92.0–100.0

### Cách 3: Colab PRO (nếu muốn GPU)
- Mở `colab_setup.ipynb` trên Colab
- Public URL cho thầy xem từ xa

## Engine (tái sử dụng từ dumps/)

| Module | File | Chức năng |
|--------|------|-----------|
| Detector | `dumps/src/engine/detector.py` | YOLOv12s detection, 4 classes |
| PCI Engine | `dumps/src/engine/pci.py` | ASTM D6433 PCI calculation |
| Segmenter | `dumps/src/engine/segmenter.py` | FastSAM segmentation (T2) |
| PCI Data | `dumps/data/pci_astm_d6433.json` | Deduct curves, CDV, severity |
| Model | `dumps/models/yolo-rdd2022-benchmark/yolo12s_seed0_best.pt` | YOLOv12s weights (18.9MB) |

## Model Performance

- **Model:** YOLOv12s (pretrained RDD2022 benchmark)
- **mAP50:** 0.632 (Friedman rank #1)
- **Classes:** 4 (D00, D10, D20, D40)
- **Inference:** ~896ms CPU / ~30-50ms GPU (Colab T4)
- **Source:** [HuggingFace SreekarAditya/yolo-rdd2022-benchmark](https://huggingface.co/SreekarAditya/yolo-rdd2022-benchmark)

## Kế hoạch phát triển (sau demo bảo vệ)

1. **FastAPI + React:** thay Streamlit prototype bằng stack production
2. **T3 End-to-end seg:** train YOLOv12s-seg trên Colab (hoặc tìm pretrained cộng đồng)
3. **Video processing nâng cao:** side-by-side view, heatmap overlay, timeline scrubber
4. **Báo cáo PDF:** form ASTM D6433
5. **Deploy cloud:** Vercel (frontend) + Render/Fly.io (backend)
6. **PyInstaller:** đóng gói .exe standalone (nếu cần)

## Liên hệ

- **Sinh viên:** [Họ tên]
- **GVHD:** Cương Nguyễn
- **Cơ sở:** ĐH Công nghệ GTVT (UTRAN) — Trung tâm BIM & AI
