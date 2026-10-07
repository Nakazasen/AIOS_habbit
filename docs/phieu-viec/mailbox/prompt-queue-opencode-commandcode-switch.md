# LỆNH: OPENCODE-SWITCH-COMMANDCODE (opencode máy nhà tự chuyển nhà cung cấp sang Command Code)

- Mã: `OPENCODE-SWITCH-COMMANDCODE`
- Quyết định nền: user chốt 2026-10-08 ~06:25 +07 — KHÔNG nâng OpenCode Go; **xoay opencode sang Command Code** (tài khoản GOAT user đang dùng, key đã có sẵn tại máy nhà trong `D:\Sandbox\AIOS_habbit\.env` dòng `AIOS_LOCAL_AI_API_KEY=`).
- **Đính chính của user 2026-10-08 ~06:33 +07:** Command Code chính là cổng mà thợ **OMP trên máy đang chạy qua** — opencode chuyển sang là cắm vào ĐÚNG kết nối OMP đang dùng, và **dùng chung túi credits GOAT với OMP**. Hệ quả bắt buộc: (a) ưu tiên soi cấu hình Command Code sẵn có của OMP trên máy này (endpoint/cách auth) và dùng lại y hệt thay vì dựng cổng mới; (b) opencode CHỈ chạy model free — bỏ mọi dự phòng trả phí, để không ăn credits của OMP (phần review/audit của OMP vẫn cần túi này).
- Thời điểm làm: ngay khi opencode hồi lại sau trần free, TRƯỚC khi tiếp tục `TEST-RED5-FIX-HOME`. Nếu tới ~07:00 08/10 opencode vẫn chưa hồi, điều phối chuyển lệnh này cho agy nhà thực hiện thay (cùng nội dung, thao tác trên cấu hình của opencode).

## Việc phải làm

1. **Định vị chỗ ghim model:** tìm nơi model mặc định của opencode đang bị ghim là bản free (`Muse Spark 1.3 Free`) — kiểm tra lần lượt: cấu hình opencode của dự án (`opencode.json` / `.opencode/`), cấu hình người dùng (`~/.config/opencode/`), và tham số khởi chạy trong watcher (`D:\Sandbox\agent-mailbox`). Ghi rõ tìm thấy ở đâu vào báo cáo.
2. **Thêm nhà cung cấp Command Code:** cấu hình provider tương thích OpenAI với endpoint `https://api.commandcode.ai/provider/v1` (đường chat completions), apiKey lấy từ biến môi trường hoặc cơ chế auth của opencode — **giá trị key đọc trực tiếp từ `.env` tại máy, chỉ dùng tại máy**: cấm in key ra log/báo cáo/mailbox, cấm commit bất kỳ tệp nào chứa key. Kiểm chứng chỉ ghi "key có mặt: có/không".
3. **Chọn model:** dùng key gọi danh sách model của Provider API; mặc định chọn model FREE mạnh nhất cho việc code trong nhóm đã biết: `inclusionai/ling-3.1-flash:free` (chính), dự phòng `inclusionai/ling-3.0-flash-sante:free`, `poolside/laguna-s-2.1-free`. **Chỉ dùng model free** (túi credits dùng chung với OMP — xem đính chính ở đầu vé): cả ba free đều không gọi được thì DỪNG và báo điều phối, không tự chuyển sang model trả phí. Đặt model đã chọn làm mặc định tại đúng chỗ ghim ở bước 1.
4. **Kiểm chứng:** chạy một phiên opencode headless ngắn (vd `opencode run` với yêu cầu đọc 1 file trong repo và tóm tắt 3 dòng) qua tuyến mới; ghi bằng chứng: provider/model đã dùng, trả lời đúng nội dung file, không lỗi auth. Kèm chạy thử một tác vụ thật nhỏ của RED5 (đọc 1 test đích và nêu kế hoạch sửa) để chắc model đủ sức code.
5. **Báo cáo:** bổ sung vào `docs/phieu-viec/ket-qua/opencode-switch-commandcode.md`: chỗ ghim model, model đã chọn + kết quả gọi thử từng model, bằng chứng phiên kiểm chứng, và cách quay lại tuyến cũ nếu cần (giá trị cấu hình cũ đã ghi lại trước khi sửa).

## Sau khi xong

Quay lại `TEST-RED5-FIX-HOME` từ điểm đang dở trên tuyến mới, ghi mốc tiếp tục vào trang-thai mailbox-opencode. Hàng chờ sau RED5 giữ nguyên: #1 `SRC-PACKAGE-511-UPLOAD-HOME`, #2 `SRC-421-PACKAGE-HOME`.

## Rào cứng

- Key là credential: chỉ ở tại máy nhà; không qua chat/mailbox/git/log dưới bất kỳ dạng nào (kể cả một phần).
- Không đụng chỉ mục; không merge `main`; sửa cấu hình phải ghi lại giá trị cũ để khôi phục được.
