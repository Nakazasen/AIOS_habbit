# VÉ: SRC-PACKAGE-511-HOME (đóng gói 511 tệp vật liệu hoá từ máy nhà giữ chỉ mục)

- Mã vé: `SRC-PACKAGE-511-HOME`
- Role gợi ý: DEFAULT
- Máy: nhà h410asrock (máy giữ chỉ mục gốc)
- Báo cáo: `docs/phieu-viec/ket-qua/src-package-511-home.md`
- Điều kiện bốc vé: xếp hàng trong mailbox máy nhà, sau `ROUTER-POOL-COMMANDCODE-HOME`.
- Đầu vào bắt buộc: `docs/phieu-viec/ket-qua/ban-ke-511.csv` (511 dòng: `document_id, source_path, source_fingerprint, n_content, nhom`) + `docs/phieu-viec/ket-qua/src-sync-pc0575.md` mục 13.

## Bối cảnh

Vé SRC-SYNC trên máy công ty đã chứng minh: 511 tài liệu trong chỉ mục thiếu tệp `.txt` vật liệu hoá tại máy công ty, và không nguồn nào trên Drive tái tạo được đúng byte (mẫu chuyển đổi 0/4 — tệp Drive lệch phiên bản so với thời điểm nạp chỉ mục). Nguồn byte đúng duy nhất là chính các tệp vật liệu hoá trên **máy nhà giữ chỉ mục**. Vé này đóng gói chúng để chuyển sang máy công ty.

## Việc phải làm

1. Trên máy nhà, xác định các gốc vật liệu hoá của workspace giữ chỉ mục (nhánh canary `local_runs/workspace_chat_rag_v2_canary/materialized_sources` và nhánh production `C:\AIOS_workspace_chat_rag_v2_production\...`). Cột `source_path` trong CSV là đường dẫn đích tại PC0575 — trên máy nhà tìm tệp theo tên `{document_id}.txt` trong các gốc này.
2. Với mỗi mã trong 511: băm SHA-256 tệp tìm được, đối chiếu `source_fingerprint` trong CSV.
   - **Chỉ đóng gói tệp KHỚP băm.** Tệp không tìm thấy hoặc lệch băm: liệt kê riêng trong báo cáo (mã + lý do), không đoán, không thay thế bằng tệp khác.
3. Đóng gói zip giữ cấu trúc 2 gốc (canary / production) kèm `manifest.csv` trong gói (document_id, đường dẫn tương đối, sha256). Tải gói lên Drive (thư mục AIOS_Data), ghi link + dung lượng vào báo cáo.
4. Báo cáo tổng: số tệp khớp / 511, danh sách thiếu/lệch, link gói. Phía máy công ty sẽ có vé nhận riêng: giải nén đúng `source_path`, băm lại từng tệp, chạy probe.

## Rào cứng

- Chỉ-đọc tệp nguồn và chỉ mục máy nhà; không ghi index; không xóa/sửa tệp gốc.
- Máy nhà đo/không dùng GPU cho vé này (việc thuần sao chép + băm).
- Không merge `main`.
