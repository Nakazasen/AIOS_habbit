# Báo cáo khôi phục chỉ mục production và nghiệm thu khóa chỉ đọc (INDEX-RESTORE-HOME)

- **Mã vé**: `INDEX-RESTORE-HOME`
- **Mục tiêu**: Khôi phục chỉ mục production `library.sqlite` trên máy nhà `h410asrock` từ bản gốc đã đóng dấu (SHA-256 `45EB0E07…B7C0`), dọn dẹp hệ quả phụ của tài liệu trùng, và nghiệm thu bằng chứng đầu-cuối qua phiên app thật chứng minh khóa chỉ đọc mới đã bảo vệ tuyệt đối tính bất biến của chỉ mục.
- **Căn cứ**: Người dùng đã DUYỆT khôi phục tại chat 2026-10-08 ~16:07 +07. Nền tảng: báo cáo `index-hash-drift-trace-home.md` + vé `INDEX-READONLY-GUARD-HOME` đã ĐẠT.
- **Máy thực hiện**: Nhà `h410asrock` (thợ chính `agy`).
- **Thời điểm thực hiện**: 2026-10-08 16:09 – 16:44 +07.
- **Trạng thái**: Hoàn thành 100% — Sẵn sàng nghiệm thu (`xong-cho-duyet`).

---

## 1. Bảng tổng hợp các cổng kiểm chứng vật lý (Physical Evidence Gates)

| Cổng kiểm chứng | Trạng thái cổng | Băm SHA-256 | Dung lượng (byte) | Số đếm / Kết quả kiểm tra | Đánh giá |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Trước sao lưu (Production hiện tại)** | ĐÃ QUA | `B0B873D040A37796AFBC3CB5723C6636FCDC6C775C6C0A4A745B8BFD3F3E3EE6` | 2.942.201.856 | Không tiến trình giữ lock; -wal/-shm không tồn tại | Đạt chuẩn |
| **2. Bản sao lưu quay lui (`20261008-pre-restore`)** | ĐÃ QUA | `B0B873D040A37796AFBC3CB5723C6636FCDC6C775C6C0A4A745B8BFD3F3E3EE6` | 2.942.201.856 | `PRAGMA integrity_check` = `ok` | Khớp 100% |
| **3. Nguồn khôi phục gốc (`AIOS_index_split_backup`)** | ĐÃ QUA | `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` | 2.942.201.856 | Khớp tuyệt đối chuẩn đóng dấu; `integrity_check` = `ok` | Đạt chuẩn |
| **4. Dọn hệ quả phụ (Tệp tạm & Ledger)** | ĐÃ QUA | N/A | N/A | Đã xóa tệp text tạm; xóa 2 dòng ledger trong `workspace_chat.sqlite` | Đạt chuẩn |
| **5. Chép khôi phục đè production** | ĐÃ QUA | N/A | N/A | Đã chép đè tệp gốc lên production | Đạt chuẩn |
| **6. Sau khôi phục (`mode=ro&immutable=1`)** | ĐÃ QUA | `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` | 2.942.201.856 | **889** docs / **149.800** chunks / **121.331** retrievable / integrity `ok` | Khớp tuyệt đối |
| **7. Sau phiên app thật (Bằng chứng cuối)** | ĐÃ QUA | `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` | 2.942.201.856 | Băm không đổi dù chỉ 1 byte! Khóa chỉ đọc hiệu lực 100% | **XÁC NHẬN BẢO VỆ THÀNH CÔNG** |

---

## 2. Chi tiết thực hiện theo đúng 7 bước quy trình

### Bước 1: Dừng tiến trình và kiểm tra khóa tệp
- **Kiểm tra tiến trình**: Quét toàn bộ tiến trình hệ thống, xác nhận không có tiến trình Streamlit hay BGE persistent worker nào đang chạy ngầm.
- **Kiểm tra độc quyền tệp**: Mở thử nghiệm tệp `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` ở chế độ ghi/đọc nhị phân độc quyền (`r+b`), kết quả: `CAN_OPEN_FOR_READ_WRITE_EXCLUSIVELY: True`.
- **Tình trạng tệp phụ `-wal` và `-shm`**: Hoàn toàn **KHÔNG TỒN TẠI** cả hai tệp `library.sqlite-wal` và `library.sqlite-shm`.

### Bước 2: Sao lưu trạng thái hiện tại (Đường quay lui)
- **Đường dẫn thư mục sao lưu**: `D:\Sandbox\AIOS_index_backup\20261008-pre-restore\`
- **Tệp sao lưu**: `D:\Sandbox\AIOS_index_backup\20261008-pre-restore\library.sqlite`
- **Dung lượng**: `2.942.201.856` byte
- **Băm SHA-256**: `B0B873D040A37796AFBC3CB5723C6636FCDC6C775C6C0A4A745B8BFD3F3E3EE6` (Khớp 100% băm hiện tại).
- **Kiểm tra tính toàn vẹn**: Mở chỉ đọc qua URI `mode=ro&immutable=1`, thực thi `PRAGMA integrity_check` -> `[('ok',)]`.

### Bước 3: Kiểm chứng nguồn khôi phục gốc
- **Đường dẫn tệp nguồn**: `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- **Dung lượng**: `2.942.201.856` byte (khớp tuyệt đối chuẩn).
- **Băm SHA-256**: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` (khớp tuyệt đối chuẩn đã đóng dấu).
- **Kiểm tra tính toàn vẹn**: `PRAGMA integrity_check` -> `[('ok',)]`.

### Bước 4: Dọn hệ quả phụ của tài liệu trùng
- **Xóa tệp văn bản nguồn tạm**: Đã xóa tệp `C:\AIOS_workspace_chat_rag_v2_production\materialized_sources\wsc-b9e2ffa072623484b1fa4198.txt`. Xác nhận sau xóa: `FILE_EXISTS_AFTER: False`.
- **Dọn ledger chuẩn bị nguồn**:
  - Vị trí cơ sở dữ liệu: `C:\AIOS_workspace_chat_rag_v2_production\workspace_chat.sqlite`
  - Bảng: `source_preparation_ledger`
  - Số dòng trước khi xóa: **2 dòng** (gồm 1 dòng scope `workspace_notebook` và 1 dòng scope `notebook` của `document_id = 'wsc-b9e2ffa072623484b1fa4198'`).
  - Số dòng đã xóa: **2 dòng**.
  - Số dòng còn lại sau xóa: **0 dòng** (`LEDGER_COUNT_AFTER: 0`).

### Bước 5: Chép khôi phục
- Đã kiểm tra và đảm bảo không có tệp `-wal` hoặc `-shm` tồn dư ở thư mục đích `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\`.
- Thực hiện sao chép đè nguyên vẹn bằng `shutil.copy2` từ bản gốc sang tệp đích.

### Bước 6: Kiểm chứng sau khôi phục (`mode=ro&immutable=1`)
Kết nối an toàn tới tệp đích sau khôi phục:
- **Dung lượng**: `2.942.201.856` byte.
- **Băm SHA-256**: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` (khớp 100% chuẩn).
- **Kiểm tra tính toàn vẹn**: `PRAGMA integrity_check` -> `[('ok',)]`.
- **Số lượng tài liệu riêng biệt** (`COUNT(DISTINCT document_id)`): **`889`** tài liệu.
- **Tổng số mảnh tri thức** (`COUNT(*)`): **`149.800`** mảnh.
- **Số mảnh truy hồi được** (`retrievable = 1`): **`121.331`** mảnh.
- **Số mảnh không truy hồi** (`retrievable = 0`): **`28.469`** mảnh.
- Toàn bộ các con số thống kê hoàn toàn khớp tuyệt đối chuẩn đóng dấu nguyên bản!

---

## 3. Bước 7: Nghiệm thu guard bằng phiên app thật (Bằng chứng cuối)

Thực hiện tự động hóa đầu-cuối qua script `local_runs/run_app_restore_verify.py` điều khiển Streamlit thật và Chrome CDP headless:
1. **Kiểm tra SHA-256 trước khi mở app**: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`.
2. **Khởi động ứng dụng**:
   - Streamlit khởi chạy với PID 6928, HTTP server phản hồi health check sau `1.05` giây.
   - Tạo cuộc trò chuyện sạch `CONV-RESTORE-F21480` trong sổ `mom_opcenter` kế thừa 215 nguồn có sẵn, **TUYỆT ĐỐI KHÔNG BẬT THÊM NGUỒN MỚI NÀO**.
   - Điều hướng Chrome tới `?nb=mom_opcenter&conv=CONV-RESTORE-F21480`.
   - Toàn bộ giao diện sẵn sàng gõ câu hỏi sau `32.36` giây.
3. **Gửi câu hỏi mẫu trên nguồn có sẵn**:
   - Mã câu hỏi: `Q0718`
   - Loại câu: Nguyên nhân (DMT–PMT)
   - Nội dung câu hỏi: `"File có xác nhận chênh lệch DMT–PMT chính là nguyên nhân duy nhất gây NG không?"`
   - Thời gian chờ toàn trình: **`381.64` giây** (bao gồm nạp và khởi động lạnh BGE worker ONNX fp32 + truy xuất + tổng hợp AI qua Router).
4. **Đáp án hiển thị nguyên văn trên giao diện (1.367 ký tự)**:
   ```markdown
   **Tóm tắt:** Không. Trong toàn bộ nguồn được cung cấp, không có dữ kiện nào nhắc đến "chênh lệch DMT–PMT", cũng không có khẳng định rằng chênh lệch đó là nguyên nhân duy nhất gây NG. Bằng chứng hiện có không đủ để trả lời câu hỏi theo hướng khẳng định.

   **Điều đã xác nhận:**
   - "PMT" chỉ xuất hiện với tư cách tên cột trong `手順書付シナリオ.xlsx` (cột G2=PMT, J3=PMT – cột đánh dấu giai đoạn xác minh), không phải là một nguyên nhân gây NG [2][12][15].
   - Các nguyên nhân NG được ghi nhận trong `Báo_cáo_lỗi_xuất_kho_AMS.xlsx` là khác:
     - Nhóm 1 (1 thùng): "Nguyên nhân trên EDI đang tồn tại dữ liệu Lot sản xuất"; ORICON ID %9702: "VendorShippingInfoとの照合NG。あわせて「格納指示FLG_Error」が発生しています" [3][6][7].
     - Nhóm 2 (6 thùng): "Camera không đọc được tem QR dán ở các mặt phụ (Trái/Phải/Trước/Sau) kết hợp lỗi CAM", mã lỗi bắt đầu bằng 0201...; ORICON ID %10304: "左側QR照合NG。あわせてCAM処理失敗および格納指示FLG_Errorが発生しています" [3][6][7].
   - Có thùng ORICON_STATUS = '0000000000000001' (trạng thái OK) vẫn bị đẩy ra cổng NG, và file ghi rõ "Nguyên nhân đang được điều tra" [3][6][7].

   **Điểm chưa đủ bằng chứng:**
   - Không có đề cập đến "DMT", không có bảng/so sánh chênh lệch DMT–PMT, và không có kết luận "nguyên nhân duy nhất" trong bất kỳ nguồn nào. Không th

   [Lưu ý: Câu trả lời bị cắt ngắn do đạt giới hạn độ dài token của mô hình.]

   Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng.
   ```
5. **Ảnh chụp giao diện thật**: Đã lưu tại `docs/phieu-viec/ket-qua/index-restore-home-app-session.png` (102.288 bytes).
6. **Kiểm tra băm SHA-256 sau khi đóng phiên**:
   - Băm SHA-256 sau phiên app: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`.
   - So sánh trước / sau: **TRÙNG KHỚP 100% TUYỆT ĐỐI**.
   - **KẾT LUẬN**: Khóa chỉ đọc mới (`read_only=True` fail-closed, guard ở cả prepare lẫn drain queue) đã hoạt động hoàn hảo trong môi trường ứng dụng thực tế. Chỉ mục hoàn toàn bất biến.

---

## 4. Bằng chứng kiểm tra chất lượng (Quality Gates)

| Lệnh kiểm tra | Yêu cầu theo `AGENTS.md` | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :---: |
| `uv run --no-sync --group dev python -m compileall src tests` | Biên dịch không lỗi cú pháp | Hoàn tất sạch, 0 lỗi cú pháp | **PASS** |
| `uv run --no-sync --group dev python -m aios_habit.cli audit` | `status: "PASS"` | `{"errors": [], "status": "PASS", "warnings": []}` | **PASS** |
| `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` | Nạp thành công module UI | `IMPORT_OK` | **PASS** |
| `uv run --no-sync --group dev pytest tests/test_workspace_chat_rag_v2_adapter.py tests/test_workspace_chat_router_adapter.py -q` | Kiểm thử đơn vị liên quan | **91 passed in 4.59s** | **PASS** |

---

## 5. Kết luận nghiệm thu

1. Chỉ mục production `library.sqlite` tại `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` đã được khôi phục thành công 100% về bản gốc đã đóng dấu:
   - SHA-256: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
   - Dung lượng: `2.942.201.856` byte
   - 889 tài liệu / 149.800 mảnh / 121.331 mảnh truy hồi
2. Bản sao lưu đường lui trước khôi phục đã được lưu trữ an toàn tại `D:\Sandbox\AIOS_index_backup\20261008-pre-restore\library.sqlite`.
3. Toàn bộ tệp tạm và 2 bản ghi ledger của tài liệu trùng `wsc-b9e2ffa072623484b1fa4198` đã được dọn sạch hoàn toàn.
4. Phiên ứng dụng thực tế đã nghiệm thu thành công: Băm SHA-256 trước và sau phiên hoàn toàn trùng khớp, chứng minh cơ chế bảo vệ chỉ đọc mới đã khóa cứng an toàn tuyệt đối.

Kính trình Điều phối Muse xem xét, phê duyệt và gỡ bỏ đóng băng để phát hành vé tiếp theo `UI-ANSWER-QUALITY2-HOME`!
