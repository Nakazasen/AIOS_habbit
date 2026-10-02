# Vé DEPLOY-BUOC05-PC0575 — Deploy tính năng Bước 0–5 lên máy công ty + mở LAN cho người dùng

LANE: [CTY] — OMP làm toàn bộ trên KDTVN-PC0575 (CPU-only). Muse KHÔNG làm vé này.

XẾP HÀNG: phát hành sau khi **cả hai** điều kiện tới —
(a) `OPT-RAGV2-PYLOOPS` verdict ĐẠT trên PC0575 (app đã nhanh), và
(b) `B5` verdict ĐẠT trên máy nhà (đủ bộ tính năng Bước 0–5).
Không phát hành sớm hơn: deploy app chậm hoặc thiếu tính năng đều không đạt đích.

## Bối cảnh

Các tính năng Bước 0–5 (B0-FORM form nhập chuẩn, B1-FEAT tra cứu, B2 vòng phản hồi,
B3 cây điều tra 4M + Why-Why, B4 xu hướng + cảnh báo, B5 phân loại tự động + cảnh báo
tái phát) do Muse code trên VM và OMP verify trên máy nhà — nhưng **chưa bao giờ được
deploy và kiểm tra chạy thật trên PC0575**, là máy LAN người dùng công ty sẽ dùng
(theo `docs/dich-den-du-an.md`: đích cuối là người dùng công ty dùng được).
Vé này lấp đúng khoảng trống đó.

## Việc cần làm (theo thứ tự)

1. `git pull` branch `phieu-viec/rag-fix1` trên PC0575 → ghi SHA code deploy.
2. Chuẩn bị DB ca lỗi cho các tính năng B0–B5: code tìm DB theo thứ tự
   `AIOS_ERROR_CASES_DB` → `C:/tmp/buoc0-deploy/error_cases_deploy.db`
   (`chat_action_case_form.py:resolve_db_path`, fail-closed nếu không có).
   Lấy DB thật **đúng cách máy nhà đã làm**: copy file `C:/tmp/b0-dict/error_cases_dict.db`
   từ máy nhà sang PC0575 (USB/Drive), verify SHA-256 khớp `6bd41a8c…2369`, rồi trỏ
   `AIOS_ERROR_CASES_DB` vào đó. Cấm tự bịa DB / tự chế dữ liệu — chỉ DỪNG + báo
   `cho-muse` khi không lấy được DB thật bằng cách nào.
3. Restart app CPU-only (`RUN_AIOS_WORKSPACE_CHAT.bat`, env như hiện tại),
   verify `/_stcore/health` = `ok`, LAN vào được từ thiết bị khác.
4. Verify từng tính năng với dữ liệu thật (không insert ca giả vào DB thật;
   nếu cần thử insert thì gắn tiền tố `SIMULATED_` và xóa ngay sau khi xong):
   - B0-FORM: mở form, render đủ 12 trường, validate chặn đúng 5 trường bắt buộc.
   - B1-FEAT: nhập 1 error code thật → ra top 3–5 + nguyên nhân/đối sách/link gốc,
     đo thời gian (kỳ vọng <1 phút sau OPT-RAGV2-PYLOOPS).
   - B2: bấm đánh giá đúng/sai/một phần trên 1 gợi ý → log ghi nhận.
   - B3: nhập 1 hiện tượng thật → ra cây 4M + Why-Why + xuất file đúng format.
   - B4: mở biểu đồ xu hướng + sinh báo cáo định kỳ được.
   - B5: nhập hiện tượng → hiện gợi ý phân loại + cảnh báo tái phát (nếu có lịch sử).
5. An toàn dữ liệu: đo SHA-256 production `collections/tri_thuc/library.sqlite`
   **trước và sau** deploy — phải **không đổi** (tính năng Bước 0–5 không được ghi
   vào index RAG; B0-FORM chỉ ghi DB ca lỗi, không ghi index).
6. Báo cáo `docs/phieu-viec/ket-qua/deploy-buoc05-pc0575.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT

- Đủ 6 tính năng B0–B5 mở được và chạy được trên PC0575 CPU-only với dữ liệu thật.
- B1-FEAT trả lời <1 phút (sau OPT-RAGV2-PYLOOPS).
- App LAN truy cập được từ thiết bị khác (như P5b đã làm).
- SHA production `library.sqlite` không đổi suốt vé.
- Commit riêng trên branch `phieu-viec/rag-fix1`, không đụng `main`, không force-push.

## Cấm

- Cấm tự bịa DB ca lỗi; lấy đúng DB thật từ máy nhà (verify SHA `6bd41a8c…2369`), chỉ dừng và báo khi không lấy được.
- Cấm ghi vào production `library.sqlite` (mọi ghi của B0-FORM đi vào DB ca lỗi).
- Cấm chạy `--apply`/migrate nào không có trong vé.
