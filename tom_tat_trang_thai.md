# TÓM TẮT TRẠNG THÁI DỰ ÁN

**Ngày lập:** 30/06/2026
**Mục đích:** Báo cáo tiến độ cho giảng viên hướng dẫn (Cương Nguyễn) — cuộc gặp thông đồ án lần 1

---

## 1. TỔNG QUAN

**Đề tài:** Xây dựng hệ thống hỗ trợ đánh giá hư hỏng mặt đường sử dụng Deep Learning, tích hợp dự đoán chỉ số PCI

**Mục tiêu:** Tự động phát hiện 4 loại hư hỏng mặt đường (D00 nứt dọc, D10 nứt ngang, D20 nứt da cá sấu, D40 ổ gà) từ ảnh/video, tính PCI theo chuẩn ASTM D6433, hỗ trợ quyết định bảo dưỡng.

**Cơ sở đào tạo:** ĐH Công nghệ GTVT (UTRAN) — Viện CN Đường sắt & GTVT — Trung tâm BIM & AI

---

## 2. KẾT QUẢ ĐÃ ĐẠT (ĐẾN 30/06/2026)

### Phase 1: Setup & Pretrained Model ✅ HOÀN THÀNH
- Model YOLOv12s (yolo12s_seed0_best.pt) từ HuggingFace (SreekarAditya/yolo-rdd2022-benchmark)
- mAP50 = 0.632 (Friedman rank #1 trên RDD2022 benchmark)
- 4 classes: longitudinal_crack (D00), transverse_crack (D10), alligator_crack (D20), pothole (D40)
- Confidence threshold 0.15 (benchmark khuyến nghị 0.10–0.20)
- Inference: ~896ms/frame CPU (Intel i5-4300U)

### Phase 2: PCI Calculation Engine (ASTM D6433) ✅ HOÀN THÀNH
- **52/52 unit tests PASS**
- Deduct value curves trích xuất từ slide chuyên môn PPTX (Slide 17-22) → `data/pci_astm_d6433.json`
- Tính đầy đủ: damage density → deduct value → CDV → PCI → rating + khuyến nghị bảo dưỡng
- Hỗ trợ section-level PCI (trung bình có trọng số)
- Hiệu chỉnh bbox overestimate (đặc biệt D00 — vết nứt dài+hẹp)
- Xử lý edge case: 0 detection → PCI=100 (Good theo ASTM)

### Phase 3: Desktop GUI (PySide6) ✅ HOÀN THÀNH
- PySide6 + Fluent Design, giao diện tiếng Việt
- Image viewer, PCI gauge (6 dải màu), damage table, log panel
- Batch processing, dark/light theme, settings dialog
- 3 vòng UAT (User Acceptance Testing) đã thực hiện
- **Đang chuyển sang web dashboard** (xem Phase 5)

### Phase 4: FastSAM Segmentation (T2) ✅ HOÀN THÀNH
- **65/65 unit tests PASS**
- FastSAM-s + FastSAM-x weights đã có (23MB + 145MB)
- Pipeline: YOLOv12s detect → crop bbox → FastSAM segment → precise mask
- So sánh PCI từ bbox proxy vs segmentation mask
- Toggle "Use Segmentation" trong UI

### Phase 5: Web Dashboard 🔄 ĐANG PHÁT TRIỂN
- **Streamlit prototype HOẠT ĐỘNG** (demo bảo vệ):
  - Chạy local: `streamlit run app.py` → http://localhost:8501
  - Upload ảnh/video → inference thật → hiển thị bbox + PCI gauge + damage table
  - Chạy trên Colab PRO (GPU + cloudflared tunnel) — notebook `colab_setup.ipynb`
- **Video demo đã render:** `outputs/demo_annotated.mp4`
  - Detection thật: 3 ổ gà (D40) phát hiện, PCI 92.0–100.0
  - Annotate bbox + label + PCI overlay
- **Kế hoạch sản phẩm cuối:** FastAPI + React (deploy sau buổi gặp thầy)

---

## 3. SẢN PHẨM CỤ THỂ ĐÃ CÓ

| # | Sản phẩm | Vị trí | Trạng thái |
|---|----------|--------|------------|
| 1 | Source code (engine) | `dumps/src/engine/` | ✅ Hoàn chỉnh |
| 2 | Web dashboard (Streamlit) | `adaptive/app.py` | ✅ Chạy được |
| 3 | Script render video | `adaptive/render_video.py` | ✅ Chạy được |
| 4 | Colab notebook (GPU) | `adaptive/colab_setup.ipynb` | ✅ Sẵn sàng |
| 5 | Video demo annotate | `adaptive/outputs/demo_annotated.mp4` | ✅ Đã render |
| 6 | Đề cương chi tiết 3 chương | `adaptive/de_cuong_chi_tiet.md` | ✅ Đã lập |
| 7 | Model weights (detection) | `dumps/models/yolo-rdd2022-benchmark/` | ✅ 18.9MB |
| 8 | Model weights (FastSAM) | `dumps/models/FastSAM-s.pt, FastSAM-x.pt` | ✅ 23MB + 145MB |
| 9 | PCI data (ASTM D6433) | `dumps/data/pci_astm_d6433.json` | ✅ Đã số hóa |
| 10 | Unit tests | `dumps/tests/` | ✅ 52 + 65 = 117 tests pass |
| 11 | Bộ ảnh mẫu | `dumps/data/samples/` | ✅ 12 ảnh (6 real + 6 synthetic) |

---

## 4. KẾ HOẠCH TIẾP THEO

### Trước buổi bảo vệ (3-6 tuần)
- [ ] Hoàn thiện FastAPI + React dashboard (thay Streamlit prototype)
- [ ] T3: Train YOLOv12s-seg trên Colab PRO (nếu tìm được pretrained cộng đồng → bỏ train)
- [ ] Video processing nâng cao: side-by-side view, heatmap overlay
- [ ] Xuất báo cáo PDF theo form ASTM D6433
- [ ] Đóng gói PyInstaller (.exe) hoặc deploy cloud cho demo
- [ ] Hoàn thiện thuyết minh 3 chương theo đề cương

### Sản phẩm bắt buộc (theo `HUONG DAN THUC HIEN HOC KY DOANH NGHIEP.pdf`)
1. ✅ Source code + app chạy hoàn chỉnh (đã có)
2. ⏳ Bộ dữ liệu đã gán nhãn (RDD2022 đã có, cần tuyển chọn bộ demo)
3. ⏳ Báo cáo PDF tóm tắt 3 chương (đề cương đã có, cần viết full)

---

## 5. CÔNG NGHỆ SỬ DỤNG

| Thành phần | Công nghệ | Phiên bản |
|------------|-----------|-----------|
| Object Detection | YOLOv12s (Ultralytics) | ultralytics 8.4.52 |
| Segmentation (T2) | FastSAM-s | onnxruntime 1.26.0 |
| Segmentation (T3) | YOLOv12s-seg (Colab) | — |
| PCI Engine | ASTM D6433-07 (custom) | — |
| Web Dashboard (demo) | Streamlit | 1.58.0 |
| Web Dashboard (final) | FastAPI + React | — |
| Video Processing | OpenCV | 4.13.0 |
| Visualization | Supervision (Roboflow) | 0.28.0 |
| Inference | PyTorch CPU / Colab GPU | torch 2.12.0 |
| GPU Platform | Google Colab PRO | T4/V100 |
| Language | Python 3.12 | 3.12.10 |

---

## 6. KIẾN TRÚC HỆ THỐNG

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Ảnh /     │────▶│   YOLOv12s   │────▶│  FastSAM    │
│   Video     │     │  Detection   │     │ Segmentation│
└─────────────┘     └──────┬───────┘     └──────┬──────┘
                           │                     │
                    Bounding Boxes          Instance Masks
                           │                     │
                           ▼                     ▼
                    ┌──────────────────────────────┐
                    │       PCI Engine             │
                    │   (ASTM D6433 Standard)      │
                    │  Deduct Values → CDV → PCI   │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │    Web Dashboard             │
                    │  (Streamlit → FastAPI+React) │
                    │  Image Viewer | PCI Gauge    │
                    │  Damage Table | Video Player │
                    └──────────────────────────────┘
```

---

## 7. ĐÓNG GÓP VÀ ĐIỂM MỚI

1. **Tận dụng pretrained model cộng đồng:** Không tự train detection từ đầu, dùng YOLOv12s #1 RDD2022 benchmark → tiết kiệm thời gian, chất lượng cao
2. **PCI chuẩn ASTM D6433 chính thức:** Deduct curves trích xuất từ slide chuyên môn, verify với ASTM D6433-07 — không tự chế công thức (bài học từ 3 lần PCI sai trước đó)
3. **Kiến trúc 3 tầng tăng dần độ chính xác:** T1 (bbox proxy) → T2 (FastSAM) → T3 (end-to-end seg) — MVP nhanh, cải tiến dần
4. **Cross-platform web dashboard:** Chuyển từ desktop (PySide6) sang web (Streamlit → FastAPI+React) — chạy mọi nền tảng
5. **Tận dụng GPU Colab PRO:** Inference + training + demo public URL

---

## 8. HỎI GIẢNG VIÊN HƯỚNG DẪN

1. **Deadline bảo vệ:** Ngày cụ thể nào? (hiện ước tính 3-6 tuần từ 29/06)
2. **T3 segmentation:** Nên train trên Colab hay tìm pretrained cộng đồng? (ưu tiên pretrained nếu có)
3. **Demo bảo vệ:** Chạy local laptop hay Colab? (khuyến nghị local + Colab backup)
4. **Báo cáo PDF:** Form ASTM D6433 cụ thể nào? (Slide 17-19 form khảo sát chuẩn)
5. **Bộ dữ liệu gán nhãn:** RDD2022 đã đủ hay cần tự gán nhãn thêm?
6. **So sánh tiêu chuẩn:** ASTM vs TCVN — có cần so sánh chi tiết hay chỉ nêu lý do chọn?

---

*Tóm tắt trạng thái lập ngày 30/06/2026. Sẽ cập nhật sau cuộc gặp thông đồ án lần 1 với giảng viên hướng dẫn.*
