# 70 Slides Chuyên môn — Trích xuất nội dung then chốt

**Source:** `dumps/Tai_Lieu/Chuyen_Mon/Quan ly bao duong mat duong - Cac chi tieu danh gia.pptx` (70 slides, Dr.Eng. Trần Thị Kim Đăng, ĐH GTVT)

**Method:** Đọc 6 slide then chốt qua MCP `9router-vision` (analyze_image). Các slide còn lại được tham chiếu qua `DE_XUAT_BO_SUNG.md` đã phân tích đầy đủ.

---

## Slide 11-13 — PSI vs PCI (tham chiếu DE_XUAT #13)
- **PSI (Present Serviceability Index):** chỉ số chủ quan, đánh giá bằng cảm nhận người đi đường
- **PCI (Pavement Condition Index):** chỉ số khách quan, tính từ distress quan sát được
- **Lý do chọn PCI:** phù hợp automatic assessment (Deep Learning detect distress → tính PCI)

## Slide 16 — Quy trình xác định PCI (ASTM D6433) — 5 bước
1. **Chia mặt đường thành các đoạn mẫu đơn vị** (diện tích ~5000 ft²)
2. **Chọn đoạn đại diện** để theo dõi (ví dụ 40 mẫu → 10% = 4 mẫu thí nghiệm)
3. **Khảo sát type, phạm vi, severity** của hư hỏng (quan sát bằng mắt, ghi bằng tay)
4. **Tính PCI mỗi mẫu:** density → deduct value → tổng deduct → PCI = 100 - deduct
5. **Tổng hợp PCI đoạn:** dựa trên giá trị các mẫu theo dõi (section-level PCI)

**Áp dụng vào dashboard:** Tab Batch implements bước 5 (section-level PCI). Pipeline indicator 5-step phản ánh quy trình này.

## Slide 17 — Alligator Cracking 3 mức độ (ví dụ minh họa)
- **FIG. X1.1 Low-Severity:** vết nứt mảnh, song song, ít interconnected
- **FIG. X1.2 Medium-Severity:** mạng lưới nứt interconnected (như da cá sấu)
- **FIG. X1.3 High-Severity:** mảnh well-defined, edge spalled, có thể lỏng lẻo under traffic

**Áp dụng:** severity assignment trong PCI engine dựa trên density (Low/Medium/High).

## Slide 18 — Form khảo sát ASTM D6433 (Survey Data Sheet)
- **19 loại distress:** Alligator Cracking, Bleeding, Block Cracking, Bumps and Sags, Corrugation, Depression, Edge Cracking, Jt. Reflection Cracking, Lane/Shoulder Drop Off, Long & Trans Cracking, Patching, Polished Aggregate, Potholes, Railroad Crossing, Rutting, Shoving, Slippage Cracking, Swell, Weathering/Ravelling
- **Columns:** DISTRESS SEVERITY | QUANTITY | TOTAL | DENSITY % | DEDUCT VALUE
- **Sketch box:** 25'×100', hướng khảo sát, mũi tên North

**Áp dụng:** Tab Report phỏng form này (tên đoạn, người khảo sát, ngày, bảng distress).

## Slide 20 — Đồ thị điều chỉnh số deduct values (FIG. 5)
- **Công thức:** `m = 1 + (9/98) * (100 - MaxDV)`
- **Trục X:** Highest Deduct Value (0-120)
- **Trục Y:** No. of Deduct Values (0-12)
- **Mục đích:** điều chỉnh số deduct values dùng trong tính CDV

**Áp dụng:** PCI engine đã implement CDV calculation với correction curves (từ Slide 21-22).

## Slide 23 — Công thức PCI Trung Quốc
- **Công thức:** `PCI = C - ΣΣ a(Ti, Sj, Dij) * F(t, d)`
  - C = điểm tối đa mỗi đoạn (100)
  - Ti = loại hư hỏng
  - Sj = mức độ nghiêm trọng
  - a(Ti, Sj, Dij) = điểm khấu trừ
  - F(t, d) = hệ số gia quyền khi nhiều loại hư hỏng
- **So sánh với ASTM D6433:** cùng nguyên lý (100 - tổng deduct), khác ở deduct curves và correction factor

**Áp dụng:** Đề cương Chương 1.4.1 — so sánh tiêu chuẩn Trung Quốc với ASTM.

## Slide 26 — Bảng PCI → Khuyến nghị bảo dưỡng (tiêu chuẩn Trung Quốc)
| Phân loại | PCI | Biện pháp |
|-----------|-----|-----------|
| Rất tốt | 100-91 | Không cần |
| Tốt | 90-81 | Bảo dưỡng thường xuyên |
| Khá | 80-71 | Sửa chữa nhỏ |
| Trung bình | 70-51 | Sửa chữa nhỏ-vừa |
| Kém | 50-31 | Sửa chữa vừa-lớn |
| Rất kém | ≤31 | Sửa chữa lớn hoặc cải tạo |

**Lưu ý:** Bảng này theo **tiêu chuẩn Trung Quốc**, khác với ASTM D6433 (Good 85-100, Satisfactory 70-85, Fair 55-70, Poor 40-55, Very Poor 25-40, Failed 0-25). Dashboard dùng ASTM (đã số hóa trong `data/pci_astm_d6433.json`).

**Áp dụng:** Tab Ảnh đơn khuyến nghị box dùng ASTM rating + maintenance action.

---

## Slides chưa đọc chi tiết (tham chiếu qua DE_XUAT)
- **Slide 1-10:** tổng quan PMS, PSI (DE_XUAT #11-13)
- **Slide 19:** deduct value curves chi tiết (đã số hóa vào pci_astm_d6433.json)
- **Slide 21-22:** CDV correction curves (đã số hóa)
- **Slide 24-25:** tiêu chuẩn Trung Quốc chi tiết (DE_XUAT #2)
- **Slide 27-28:** CIsurf/CIStruct (Pháp) (DE_XUAT #2)
- **Slide 29-31:** Vizir (Pháp) (DE_XUAT #2)
- **Slide 32-50:** PMS context (DE_XUAT #11)
- **Slide 60-70:** Asset management context (DE_XUAT #12)

---

## Áp dụng vào đề cương (de_cuong_chi_tiet.md cập nhật)

**Chương 1.3.2 — Quy trình khảo sát PCI:** 5 bước từ Slide 16 (chi tiết hóa)
**Chương 1.3.3 — 4 loại hư hỏng chính:** D00/D10/D20/D40 + mô tả severity từ Slide 17
**Chương 1.3.4 — Deduct value curves:** từ Slide 18-22 (đã số hóa)
**Chương 1.3.5 — Thang điểm PCI + khuyến nghị:** Slide 26 (so sánh Trung Quốc vs ASTM)
**Chương 1.4.1 — Tiêu chuẩn Trung Quốc:** công thức PCI từ Slide 23
**Chương 1.4.4 — So sánh với TCVN:** lý do chọn ASTM (PCI sai 3 lần với công thức tự chế)

## Áp dụng vào dashboard (app.py cập nhật)

**Tab Report:** form khảo sát phỏng Slide 18 (Survey Data Sheet)
**Tab Ảnh đơn khuyến nghị:** bảng ASTM (không phải Trung Quốc — đã có trong pci_astm_d6433.json)
**Tab About thang PCI:** bảng 6 mức ASTM + ghi chú so sánh Trung Quốc

---

*Trích xuất: 2026-06-29. 6/70 slides đọc chi tiết qua MCP vision. 64 slides còn lại tham chiếu qua DE_XUAT_BO_SUNG.md (đã phân tích đầy đủ 36 đề xuất).*
