# VÉ: SRC-421-RECEIVE-PC0575 (nhận 421 tệp hiện tại + cập nhật vân tay chỉ mục theo bản mới) — CHỈ PHÁT HÀNH KHI GÓI ĐÃ LÊN DRIVE

- Mã vé: `SRC-421-RECEIVE-PC0575`
- Role gợi ý: DEFAULT (nhận tệp + ghi chỉ mục có rào an toàn)
- Máy: công ty KDTVN-PC0575 (CPU-only)
- Báo cáo: `docs/phieu-viec/ket-qua/src-421-receive-pc0575.md`
- Quyết định nền: user chốt 2026-10-08 ~05:54 +07 — chép tệp hiện tại + cập nhật vân tay theo bản mới cho 421 mã lệch (danh sách: `docs/phieu-viec/ket-qua/src-package-511-lech.csv`).
- Điều kiện phát hành (điều phối kiểm trước khi copy vé này vào prompt.md): gói `src-421-current-home.zip` + `manifest-421.csv` đã ở thư mục Drive AIOS_Data và đã kiểm chứng kích thước/băm phía Drive.

## Việc phải làm

1. **Tải gói** từ AIOS_Data (tự chuyển mạng `ngoai` theo quy ước, kiểm `DRIVE=OK`), giải nén vào vùng đệm riêng — CHƯA ghi đè gì.
2. **Đối chiếu khi nhận:** băm lại từng tệp vừa nhận, so với `manifest-421.csv`: tệp nào lệch manifest thì loại ra và báo riêng, không dùng.
3. **Xác minh cách tính vân tay:** trước khi sửa bất cứ thứ gì, lấy 3 mã thuộc nhóm 90 đã khớp (từ gói `SRC-PACKAGE-511`) và kiểm chứng hàm vân tay của repo cho ra đúng giá trị chỉ mục đang lưu. Không khớp cách tính thì DỪNG, báo điều phối — cấm đoán.
4. **Chép tệp:** đặt 421 tệp vào đúng đường dẫn materialized mà chỉ mục đang trỏ tới (theo manifest).
5. **Cập nhật vân tay — rào an toàn ghi chỉ mục (bắt buộc đủ ba):**
   - Sao lưu MỚI tệp chỉ mục trước khi ghi + kiểm `quick_check` bản sao lưu = ok.
   - Chạy thử (dry-run): in danh sách đúng 421 mã sẽ đổi, vân tay cũ → mới, khẳng định không mã nào ngoài danh sách bị đụng.
   - Ghi thật theo lô có điểm tiếp tục (batch/resume); chỉ cập nhật trường vân tay của đúng 421 tài liệu đó.
6. **Kiểm chứng sau ghi:** `quick_check` ok; đọc lại vân tay của 421 mã khớp manifest; mở xem tệp nguồn thật qua đường app cho tối thiểu 5 tài liệu thuộc nhóm 421 (dùng thật, kèm ảnh/bằng chứng); chạy bộ truy vấn mẫu theo mã như cổng của SRC-PROBE để chắc tìm kiếm không vỡ.

## Rào cứng

- Thiếu một trong ba rào ở bước 5 (sao lưu mới / dry-run / batch-resume) thì KHÔNG ghi — báo CHƯA ĐẠT phần ghi.
- Không đổi nội dung mảnh (chunks) — vé này chỉ đổi tệp nguồn + vân tay tài liệu.
- Không merge `main`. Mạng: xong việc chuyển về `congty` nếu vé sau cần LAN.
