# Bài học từ 5 phiên hội thoại (Tai_Lieu/Phien_Hoi_Thoai)

**Source:** 5 file log hội thoại trong `dumps/Tai_Lieu/Phien_Hoi_Thoai/`. Trích xuất bài học áp dụng vào dashboard + đề cương.

---

## 1. Deep Learning Road Damage Assessment.md (60KB — phiên gốc)

**Dự án gốc:** `pavement_pci_project` — YOLOv8 + PyQt5 Desktop + Gradio Web, kết nối Colab Pro GPU qua `xeodou/colab-cli`. PCI theo **tiêu chuẩn Trung Quốc** với công thức exponential decay tự chế.

**Pivot quan trọng (sang dumps hiện tại):**
- YOLOv8 → YOLO11n → **YOLOv12s pretrained** (sau khi Colab bị gián đoạn mất mạng)
- Tiêu chuẩn Trung Quốc → **ASTM D6433** (sau khi PCI sai 3 lần)
- Colab CLI (server inference) → **DirectML local + Colab chỉ train** (sau khi colab-cli crash Windows)

**Phát hiện kỹ thuật quan trọng:**
- Intel HD 4400 hỗ trợ `D3D12_GENERIC_ML` → DirectML backend khả thi (sau này DirectML crash với YOLOv12, fallback CPU)
- Stack tối ưu theo hardware thật: PySide6 + YOLO11n + Supervision + Colab train + ONNX Runtime DirectML

**Bài học cho đề cương Chương 2:** mô tả lịch sử pivot này trong mục "tiến trình phát triển" — chứng minh quyết định kỹ thuật có cơ sở, không ngẫu nhiên.

---

## 2. GSD Progress Check.md (34KB — debug Gradio crash)

**Root cause "Broken Connection" Gradio:**
1. `raise gr.Error(...)` → crash Gradio worker → WebSocket đứt
2. Codec `mp4v` không browser-compatible → Gradio cố convert → fail → crash
3. Không try/except trong `on_analyze` → lỗi nào cũng crash worker
4. `AnalysisState` custom class trong `gr.State` → Gradio 5.x không tương thích → phải dùng `dict`

**Fix:** return error message thay vì raise, codec `['avc1', 'H264', 'X264']` + fallback mp4v, try/except toàn bộ, dùng dict cho state.

**Bài học áp dụng vào Streamlit dashboard:**
- ✅ Đã áp dụng: try/except per frame trong video processing
- ✅ Đã áp dụng: session_state dùng dict ( không custom class)
- ✅ Đã áp dụng: codec mp4v trong render_video.py (Streamlit player tương thích)
- ⚠️ Codec avc1/H264 chưa thử — nên thêm fallback nếu demo Colab

**Bài học cho đề cương Chương 2 (mục 2.5.3 Chuyển đổi desktop→web):** nêu rõ lý do chuyển từ Gradio (crash worker, codec issues, state limitation) sang Streamlit → FastAPI+React.

---

## 3. Colab CLI Deep Dive.md (69KB — xác định colab-cli không hỗ trợ Windows)

**Phát hiện gốc rễ:** `google-colab-cli` (xeodou) dùng `fcntl`, `termios`, `tty` — Unix-only, không chạy được trên Windows.

**Bài học meta:** "Tao đã kết luận mà không verify Windows compatibility. Đó là lỗi của tao." → **luôn verify platform compatibility trước khi kết luận**.

**Bài học áp dụng:**
- Colab CLI bị loại → dùng Colab qua browser/notebook truyền thống + cloudflared tunnel (đã có trong colab_setup.ipynb)
- Đề cương Chương 2 mục 2.7.4 (Rủi ro Colab): nêu rõ colab-cli không khả thi trên Windows, dùng notebook + tunnel thay thế

---

## 4. Debug GUI Display Issues.md (68KB — debug PyQt5 GUI)

**5 bug đã sửa trong `pavement_pci_project`:**
1. `debug_logger.py` escape double-brace
2. `colab_worker.py` không import `logging` ở module level → NameError
3. Detection data không lưu từ inference → PCI sai
4. E2E test thiếu PYTHONPATH
5. Codec video + escape string

**Bài học error handling (INF-01 logging framework):**
- Logging phải import ở module level, không trong function
- Detection data phải persist trước khi tính PCI (separation of concerns)
- E2E test cần PYTHONPATH explicit
- Codec video phải có fallback chain

**Áp dụng vào dashboard:**
- ✅ Logging qua `src.utils.logging_setup` (import ở top)
- ✅ Detection → PCI pipeline tách bậc (run_inference return det_result + pci_result riêng)
- ⚠️ Codec fallback trong render_video.py chỉ có mp4v — nên thêm avc1/H264

---

## 5. Colab Desktop App Strategy.md (213KB — chiến lược tổng thể)

**Phiên đầu tiên:** `/gsd-new-project` cho dự án gốc `pavement_pci_project`. Cấu trúc 10 phase: Foundation → Train → Desktop → Inference → Progress Report → Video → PCI → GUI Polish → Testing → Defense.

**Stack ban đầu:** YOLO11n + PySide6 + Supervision + Colab train + DirectML inference.

**Bài học:** Cấu trúc 10 phase ban đầu được đơn giản hóa thành 7 phase trong dumps (sau pivot pretrained weights — không cần train Phase 2).

---

## Tổng hợp bài học cho dashboard + đề cương

### Cho dashboard (adaptive/app.py)
1. ✅ try/except per frame (Gradio lesson)
2. ✅ session_state dùng dict (Gradio state lesson)
3. ✅ Logging import top-level (PyQt5 lesson)
4. ✅ Detection → PCI tách bậc (PyQt5 lesson)
5. ⚠️ Codec fallback chain: mp4v → avc1 → H264 (chưa đầy đủ)
6. ⚠️ Pre-flight check Colab compatibility (colab-cli lesson)

### Cho đề cương (de_cuong_chi_tiet.md)
- **Chương 1.4.4:** Lý do chọn ASTM thay vì TCVN — lịch sử PCI sai 3 lần (G1-G2-G3)
- **Chương 2.1.1:** Tiến trình pivot: YOLOv8 → YOLO11n → YOLOv12s pretrained
- **Chương 2.5.3:** Lý do chuyển Gradio → Streamlit → FastAPI+React (crash worker, codec, state)
- **Chương 2.7.4:** Rủi ro Colab — colab-cli không Windows, dùng notebook + tunnel
- **Chương 3.5.2:** Hạn chế — inference CPU chậm, DirectML crash với YOLOv12, Colab session timeout

---

*Trích xuất: 2026-06-29. 4/5 file đã đọc full hoặc grep key insights. File Colab Desktop App Strategy (213KB) chỉ đọc 80 dòng đầu — nội dung chính trùng với Deep Learning Road Damage Assessment.md (phiên sau).*
