# ĐỀ CƯƠNG CHI TIẾT ĐỒ ÁN TỐT NGHIỆP

**Tên đề tài:** Xây dựng hệ thống hỗ trợ đánh giá hư hỏng mặt đường sử dụng Deep Learning, tích hợp dự đoán chỉ số PCI

**Sinh viên thực hiện:** [Họ tên sinh viên]
**Giảng viên hướng dẫn:** Cương Nguyễn
**Cơ sở đào tạo:** Đại học Công nghệ Giao thông Vận tải (UTRAN) — Viện Công nghệ Đường sắt và Giao thông Vận tải — Trung tâm Công nghệ BIM và AI

**Ngày lập đề cương:** 30/06/2026

---

## CẤU TRÚC THUYẾT MINH (theo `hinh_thuc_trinh_bay_chuan.pdf`)

- Khổ giấy: A4
- Font: Times New Roman, cỡ 13
- Margin: trên/dưới/phải 2cm, trái 3cm
- Line spacing: 1.35
- Cấu trúc: Mở đầu → Chương 1-3 → Phụ lục → Tài liệu tham khảo

---

## MỞ ĐẦU

### 0.1. Lý do chọn đề tài
- Tình trạng suy giảm chất lượng mặt đường tại Việt Nam; chi phí bảo dưỡng lớn nếu không phát hiện sớm
- Phương pháp thủ công (kỹ sư đi khảo sát trực tiếp) tốn thời gian, chủ quan, nguy hiểm trên cao tốc
- Sự phát triển của Deep Learning (YOLO, segmentation) mở ra khả năng tự động hóa phát hiện hư hỏng từ ảnh/video
- Tích hợp với chuẩn ASTM D6433 (Pavement Condition Index) — tiêu chuẩn quốc tế có thể kiểm chứng
- Bối cảnh thực tế: hệ thống camera CCTV trên cao tốc (ITS — Intelligent Transport Systems) cung cấp nguồn ảnh liên tục

### 0.2. Mục tiêu nghiên cứu
- **Mục tiêu chính:** Xây dựng hệ thống tự động phát hiện, phân loại hư hỏng mặt đường (4 loại: nứt dọc D00, nứt ngang D10, nứt da cá sấu D20, ổ gà D40) từ ảnh/video, tính chỉ số PCI theo ASTM D6433, hỗ trợ quyết định bảo dưỡng.
- **Mục tiêu phụ:** Chuyển đổi từ desktop application sang web dashboard chạy trên mọi nền tảng; tận dụng GPU Google Colab PRO cho inference và training.

### 0.3. Đối tượng và phạm vi nghiên cứu
- **Đối tượng:** Mặt đường asphalt, 4 loại hư hỏng theo chuẩn ASTM D6433
- **Phạm vi:**
  - Sử dụng pretrained model YOLOv12s từ benchmark RDD2022 (không tự train detection từ đầu)
  - Phân vùng (segmentation) bằng FastSAM (T2) và YOLOv12s-seg trained trên Colab (T3)
  - Tính PCI theo ASTM D6433-07
  - Web dashboard (Streamlit → FastAPI + React) chạy local + Colab
- **Ngoài phạm vi:** Real-time webcam, mobile app, 3D reconstruction, cloud deployment production

### 0.4. Phương pháp nghiên cứu
- Nghiên cứu tài liệu: ASTM D6433-07, RDD2022 benchmark, các tiêu chuẩn PCI quốc tế (Trung Quốc, Vizir, CIsurf)
- Thực nghiệm: pretrained model inference, so sánh 3 tầng (bbox proxy → FastSAM → end-to-end seg)
- Phát triển phần mềm: theo quy trình GSD (Get Shit Done) — pha hóa, có tests, có verification

### 0.5. Ý nghĩa khoa học và thực tiễn
- **Khoa học:** Ứng dụng Deep Learning (YOLOv12s + FastSAM) cho bài toán đặc thù quản lý hạ tầng giao thông
- **Thực tiễn:** Giảm thời gian khảo sát, tăng tính khách quan, tích hợp với hệ thống ITS hiện có

### 0.6. Bố cục thuyết minh
- Chương 1: Tổng quan về đánh giá hư hỏng mặt đường và công nghệ Deep Learning
- Chương 2: Phương pháp xây dựng hệ thống đánh giá hư hỏng mặt đường
- Chương 3: Kết quả triển khai và đánh giá

---

## CHƯƠNG 1: TỔNG QUAN VỀ ĐÁNH GIÁ HƯ HỎNG MẶT ĐƯỜNG VÀ CÔNG NGHỆ DEEP LEARNING

### 1.1. Tổng quan về quản lý bảo dưỡng mặt đường (Pavement Management System — PMS)
- 1.1.1. Khái niệm PMS và vai trò trong quản lý hạ tầng giao thông (Slide 32-50)
- 1.1.2. Quản lý tài sản hạ tầng: đường = tài sản, khấu hao theo tình trạng (Slide 60-70)
- 1.1.3. Bối cảnh thực tế tại Việt Nam: hệ thống ITS, camera CCTV trên cao tốc, VDS, VMS (Sổ tay vận hành ITS)

### 1.2. Các phương pháp đánh giá tình trạng mặt đường
- 1.2.1. Phương pháp thủ công: khảo sát hiện trường, đánh giá chủ quan
- 1.2.2. Phương pháp bán tự động: xe chuyên dụng + cảm biến
- 1.2.3. Phương pháp tự động: xử lý ảnh, Deep Learning
- 1.2.4. So sánh PSI (Present Serviceability Index — chủ quan) vs PCI (Pavement Condition Index — khách quan) (Slide 11-13)

### 1.3. Tiêu chuẩn PCI theo ASTM D6433
- 1.3.1. Lịch sử và phạm vi áp dụng của ASTM D6433-07
- 1.3.2. Quy trình khảo sát PCI: chia đoạn mẫu → chọn đoạn đại diện → khảo sát hư hỏng → tính density → tra deduct → tính CDV → ra PCI (Slide 16-19)
- 1.3.3. Phân loại hư hỏng: 4 loại chính (D00, D10, D20, D40) + Repair/Other (Slide 20)
- 1.3.4. Bảng deduct value curves và CDV correction (Slide 17-22)
- 1.3.5. Thang điểm PCI (0-100) và khuyến nghị bảo dưỡng (Slide 26)

### 1.4. So sánh với các tiêu chuẩn đánh giá khác
- 1.4.1. Tiêu chuẩn Trung Quốc (Slide 23-26)
- 1.4.2. Tiêu chuẩn Vizir (Pháp) (Slide 30-31)
- 1.4.3. Tiêu chuẩn CIsurf/CIStruct (Slide 27-28)
- 1.4.4. Tiêu chuẩn Việt Nam (TCVN 3220, QĐB 405) — lý do chọn ASTM thay vì TCVN
- 1.4.5. Bảng so sánh tổng hợp

### 1.5. Tổng quan về Deep Learning cho phát hiện đối tượng
- 1.5.1. Kiến trúc CNN và bài toán object detection
- 1.5.2. Họ mô hình YOLO (You Only Look Once): YOLOv8 → YOLOv11 → YOLOv12
- 1.5.3. Instance segmentation: FastSAM, SAM
- 1.5.4. Dataset RDD2022: 47,420 ảnh, benchmark công khai

### 1.6. Các nghiên cứu liên quan
- 1.6.1. Nghiên cứu phát hiện hư hỏng mặt đường bằng Deep Learning
- 1.6.2. Benchmark RDD2022 và model SreekarAditya/yolo-rdd2022-benchmark
- 1.6.3. Ứng dụng segmentation cho đo lường diện tích hư hỏng

---

## CHƯƠNG 2: PHƯƠNG PHÁP XÂY DỰNG HỆ THỐNG ĐÁNH GIÁ HƯ HỎNG MẶT ĐƯỜNG

### 2.1. Tổng quan kiến trúc hệ thống
- 2.1.1. Sơ đồ kiến trúc 3 tầng (T1: bbox proxy → T2: FastSAM → T3: end-to-end seg)
- 2.1.2. Pipeline xử lý: Ảnh/Video → Detection → Segmentation → PCI Engine → Báo cáo
- 2.1.3. Kiến trúc module: engine (detector, pci, segmenter) tách rời khỏi UI

### 2.2. Module phát hiện hư hỏng (Detection)
- 2.2.1. Mô hình YOLOv12s pretrained từ HuggingFace (SreekarAditya/yolo-rdd2022-benchmark)
- 2.2.2. Thông số model: 4 classes, mAP50=0.632, confidence threshold 0.15
- 2.2.3. Quy trình inference: load model → preprocess → predict → postprocess (NMS, bbox)
- 2.2.4. Mapping class names → ASTM codes (D00, D10, D20, D40)
- 2.2.5. Xử lý lớp thứ 5 (Repair/Other) — loại khỏi tính PCI

### 2.3. Module phân vùng (Segmentation)
- 2.3.1. **T2 — FastSAM:** bbox-prompted segmentation, không cần train
  - Pipeline: YOLOv12s detect → crop bbox → FastSAM segment → precise mask
  - IoU matching giữa detection và segmentation
- 2.3.2. **T3 — End-to-end segmentation:** YOLOv12s-seg trained trên Colab
  - Dataset: RDD2022 YOLO CrackScan v2 (Kaggle, đã convert sẵn)
  - Training trên Google Colab PRO (GPU T4/V100)
  - So sánh 3 phương pháp: bbox proxy vs FastSAM vs end-to-end seg

### 2.4. Module tính PCI (ASTM D6433)
- 2.4.1. Nguồn dữ liệu deduct curves: trích xuất từ slide chuyên môn PPTX (Slide 17-22) → `data/pci_astm_d6433.json`
- 2.4.2. Tính damage density = area / sample unit area (hỗ trợ ft² và m²)
- 2.4.3. Ánh xạ density → deduct value (nội suy tuyến tính từ curves)
- 2.4.4. Tính CDV (Corrected Deduct Value) từ q và TDV
- 2.4.5. PCI = 100 - CDV cho từng sample unit
- 2.4.6. PCI cấp đoạn đường (section-level): trung bình có trọng số
- 2.4.7. Gán mức độ nghiêm trọng (severity) dựa trên density
- 2.4.8. Hiệu chỉnh bbox overestimate (aspect ratio heuristic, đặc biệt D00)
- 2.4.9. Xử lý edge case: 0 detection → PCI=100, ảnh không phải mặt đường, confidence thấp

### 2.5. Module giao diện (Web Dashboard)
- 2.5.1. **Giai đoạn 1 — Streamlit (demo bảo vệ):** Python-native, tái dùng engine trực tiếp
  - Upload ảnh/video → inference → hiển thị bbox + PCI gauge + damage table
  - Chạy local + Colab PRO (GPU + cloudflared tunnel)
- 2.5.2. **Giai đoạn 2 — FastAPI + React (sản phẩm cuối):**
  - Backend FastAPI: expose engine qua REST API
  - Frontend React: dashboard đa panel (image viewer, PCI gauge, damage table, video player, settings)
  - Deploy: local + cloud (Vercel/Netlify cho frontend, Colab/Render cho backend)
- 2.5.3. **Chuyển đổi từ desktop (PySide6) sang web:** lý do (cross-platform, không cần cài đặt, tận dụng trình duyệt)

### 2.6. Xử lý video
- 2.6.1. Frame extraction (OpenCV): mp4, avi
- 2.6.2. Chiến lược lấy mẫu: mỗi N frame (theo quy trình khảo sát ASTM, không cần từng frame)
- 2.6.3. Annotate frame: bbox + label + PCI overlay
- 2.6.4. Xuất video H.264 (ffmpeg/OpenCV VideoWriter)
- 2.6.5. PCI time-series chart (PCI theo frame)

### 2.7. Tận dụng Google Colab PRO
- 2.7.1. GPU inference (T4/V100): ~30-50ms/frame thay vì 896ms CPU
- 2.7.2. Training T3 (YOLOv12s-seg) trên RDD2022
- 2.7.3. Streamlit + cloudflared tunnel: public URL demo
- 2.7.4. Rủi ro và biện pháp: session timeout → local backup + pre-compute

### 2.8. Kiểm thử và đánh giá
- 2.8.1. Unit tests cho PCI engine (ASTM D6433 logic) — 52 test cases
- 2.8.2. Unit tests cho detector + segmenter — 65 test cases
- 2.8.3. Benchmark inference speed: CPU vs GPU (Colab)
- 2.8.4. So sánh PCI tự động vs đánh giá thủ công (sai số ≤ 5 điểm) — cần ground truth
- 2.8.5. Test độ nhạy PCI theo confidence threshold (0.10→0.20)

---

## CHƯƠNG 3: KẾT QUẢ TRIỂN KHAI VÀ ĐÁNH GIÁ

### 3.1. Kết quả module phát hiện (Detection)
- 3.1.1. Model YOLOv12s load thành công, 4 classes đúng
- 3.1.2. Kết quả detection trên ảnh mẫu (real_damage samples)
- 3.1.3. Inference time: ~896ms CPU (Intel i5-4300U), ~30-50ms GPU (Colab T4)
- 3.1.4. Ảnh annotate với bounding boxes + labels + confidence

### 3.2. Kết quả module phân vùng (Segmentation)
- 3.2.1. **T2 — FastSAM:** mask chính xác trong detected bounding boxes
- 3.2.2. So sánh diện tích: bbox proxy vs segmentation mask (đặc biệt D00 — bbox overestimate)
- 3.2.3. **T3 — End-to-end seg:** kết quả training trên Colab (nếu hoàn thành)
- 3.2.4. Bảng so sánh 3 phương pháp: độ chính xác diện tích, thời gian, độ phức tạp

### 3.3. Kết quả module PCI
- 3.3.1. PCI engine pass 100% unit tests (52/52)
- 3.3.2. Kết quả PCI trên ảnh mẫu: rating + khuyến nghị bảo dưỡng
- 3.3.3. PCI cấp đoạn đường (section-level) từ batch processing
- 3.3.4. Verify deduct curves với bản chính thức ASTM D6433-07

### 3.4. Kết quả web dashboard
- 3.4.1. **Streamlit demo:** chạy local + Colab, upload ảnh/video, hiển thị kết quả inference thật
- 3.4.2. **Video demo:** video annotate với detection + PCI overlay (outputs/demo_annotated.mp4)
- 3.4.3. **FastAPI + React (nếu hoàn thành):** dashboard đa panel, deploy cloud
- 3.4.4. Ảnh chụp màn hình dashboard

### 3.5. Đánh giá tổng thể
- 3.5.1. Ưu điểm: tự động hóa, tính khách quan, tái sử dụng pretrained model, cross-platform
- 3.5.2. Hạn chế: inference CPU chậm, model pretrained không tối ưu cho điều kiện Việt Nam, phụ thuộc Colab cho GPU
- 3.5.3. So sánh với phương pháp thủ công: thời gian, chi phí, tính nhất quán

### 3.6. Hướng phát triển
- 3.6.1. Tích hợp GIS/Map: hiển thị PCI theo vị trí địa lý (Slide 32-50)
- 3.6.2. Tích hợp với hệ thống camera CCTV trên cao tốc (ITS) — real-time
- 3.6.3. Train model trên dataset Việt Nam (điều kiện đường, khí hậu đặc thù)
- 3.6.4. Mobile app cho khảo sát hiện trường
- 3.6.5. 3D pavement reconstruction
- 3.6.6. Multi-camera support, drone imagery

---

## KẾT LUẬN

- Hệ thống đã hoàn thành 4/7 phase: detection, PCI engine, segmentation, web dashboard prototype
- Đạt được mục tiêu chính: phát hiện hư hỏng + tính PCI chuẩn ASTM D6433
- Web dashboard chạy được trên mọi nền tảng (browser), tận dụng GPU Colab
- Đề xuất hướng phát triển: GIS integration, real-time CCTV, dataset Việt Nam

---

## PHỤ LỤC

- Phụ lục A: Mã nguồn hệ thống (GitHub repository)
- Phụ lục B: Bộ dữ liệu mẫu (data/samples/)
- Phụ lục C: Bảng deduct value curves ASTM D6433 (data/pci_astm_d6433.json)
- Phụ lục D: Ảnh chụp màn hình dashboard
- Phụ lục E: Video demo (outputs/demo_annotated.mp4)
- Phụ lục F: Kết quả unit tests (52 + 65 = 117 tests pass)

---

## TÀI LIỆU THAM KHẢO (xếp theo ABC)

1. ASTM International. (2007). *Standard Practice for Roads and Parking Lots Pavement Condition Index Surveys* (ASTM D6433-07).
2. Chu, V., et al. (2022). *RDD2022: A multi-national dataset for road damage detection*. arXiv.
3. Hu, J., et al. (2023). *YOLOv12: Real-time object detection with attention mechanisms*.
4. Sreekar Aditya. (2025). *yolo-rdd2022-benchmark* [HuggingFace]. https://huggingface.co/SreekarAditya/yolo-rdd2022-benchmark
5. Zhao, X., et al. (2023). *FastSAM: Fast Segment Anything Model*.
6. Ultralytics. (2025). *YOLOv12 Documentation*. https://docs.ultralytics.com
7. Roboflow. (2025). *Supervision: Visualize and analyze detections*. https://github.com/roboflow/supervision
8. Streamlit Inc. (2025). *Streamlit Documentation*. https://docs.streamlit.io
9. Google. (2025). *Google Colab PRO*. https://colab.research.google.com
10. Bộ GTVT. (2003). *TCVN 3220:2003 — Phân loại và đánh giá mặt đường*.
11. ... (bổ sung thêm theo quá trình viết)

---

## DANH MỤC BẢNG

1. Bảng 1.1: So sánh các tiêu chuẩn đánh giá mặt đường
2. Bảng 2.1: Thông số model YOLOv12s
3. Bảng 2.2: Bảng deduct value curves ASTM D6433
4. Bảng 3.1: Kết quả detection trên ảnh mẫu
5. Bảng 3.2: So sánh 3 phương pháp segmentation
6. Bảng 3.3: Kết quả PCI trên ảnh mẫu
7. Bảng 3.4: Benchmark inference time

## DANH MỤC HÌNH

1. Hình 1.1: Sơ đồ PMS
2. Hình 1.2: Quy trình khảo sát PCI ASTM D6433
3. Hình 1.3: 4 loại hư hỏng mặt đường
4. Hình 2.1: Kiến trúc hệ thống 3 tầng
5. Hình 2.2: Pipeline xử lý
6. Hình 3.1: Ảnh annotate với bounding boxes
7. Hình 3.2: PCI gauge
8. Hình 3.3: Web dashboard
9. Hình 3.4: Video demo frame

## DANH MỤC TỪ VIẾT TẮT

- **PCI**: Pavement Condition Index — Chỉ số tình trạng mặt đường
- **PMS**: Pavement Management System — Hệ thống quản lý bảo dưỡng mặt đường
- **ASTM**: American Society for Testing and Materials — Hiệp hội Thử nghiệm và Vật liệu Hoa Kỳ
- **CDV**: Corrected Deduct Value — Giá trị khấu trừ hiệu chỉnh
- **TDV**: Total Deduct Value — Tổng giá trị khấu trừ
- **YOLO**: You Only Look Once — Thuật toán phát hiện đối tượng real-time
- **FastSAM**: Fast Segment Anything Model
- **mAP**: mean Average Precision — Độ chính xác trung bình
- **ITS**: Intelligent Transport Systems — Hệ thống giao thông thông minh
- **CCTV**: Closed-Circuit Television — Hệ thống camera giám sát
- **VDS**: Vehicle Detection System
- **VMS**: Variable Message Sign — Biển báo thông tin biến thiên
- **RDD2022**: Road Damage Detection 2022 dataset
- **D00/D10/D20/D40**: Mã hư hỏng ASTM (nứt dọc/nứt ngang/nứt da cá sấu/ổ gà)
- **PSI**: Present Serviceability Index
- **GIS**: Geographic Information System
- **GPU**: Graphics Processing Unit
- **API**: Application Programming Interface
- **GUI**: Graphical User Interface

---

*Đề cương chi tiết lập ngày 30/06/2026. Nội dung từng mục sẽ được hoàn thiện dần theo tiến độ đồ án.*
