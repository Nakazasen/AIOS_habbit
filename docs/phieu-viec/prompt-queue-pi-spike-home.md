# Vé: PI-SPIKE-HOME — chạy thử pi harness ở máy nhà (thả cửa, chưa gắn gate)

Lane: [NHÀ] OMP chạy trên máy nhà h410asrock.
Mục tiêu: chứng minh pi cài được, gọi model làm 1 task tạo/sửa file thật, thử RPC mode.
Không merge `main`; không đụng index production; chỉ làm trong `C:\tmp\pi-spike\`.

## Bước 1 — Cài pi

- `npm install -g --ignore-scripts @earendil-works/pi-coding-agent` (chưa có npm thì cài Node LTS trước).
- Kiểm tra: `pi --version`, ghi version vào báo cáo.
- Tắt telemetry ngay sau cài (dữ liệu công ty không cho ping ra ngoài): set env máy
  `PI_TELEMETRY=0` và `PI_SKIP_VERSION_CHECK=1`.

## Bước 2 — Chọn đường model (thử theo thứ tự, dừng ở đường đầu tiên sống)

1. **Model có sẵn nhanh nhất:** dùng model pi hỗ trợ mà máy đã đăng nhập sẵn
   (xem `~/.pi/agent/`, lệnh `/login` trong pi). Mục tiêu là pi chạy được task,
   chưa cần đúng đường chiến lược.
2. **Cầu nối Gemini Web** (`http://127.0.0.1:8585/health`): nếu sống, thử cấu hình
   pi custom provider trỏ vào bridge — code tham khảo
   `src/aios_habit/gemini_web_engine.py::generate_gemini_web_reply` trong repo
   (nhánh `phieu-viec/rag-fix1`). Bridge cần extension TypeScript riêng; spike này
   chỉ cần kết luận "làm được / khó ở đâu", chưa bắt xong.
3. Ghi rõ vào báo cáo: đường nào sống, đường nào chết, vì sao.

## Bước 3 — Task thử (thả cửa, chưa gắn policy gate)

Trong `C:\tmp\pi-spike\`:

1. `pi "tạo file bao-cao-thu.md: báo cáo tuần 3 dòng có 1 bảng"`
2. `pi "sửa file bao-cao-thu.md: thêm 1 dòng kết luận ở cuối"`
3. Mở file kiểm tra bằng mắt: nội dung đúng yêu cầu không, có rác không.

## Bước 4 — RPC mode (đường app Streamlit sẽ dùng)

- Thử `pi --mode rpc`: gửi 1 lệnh prompt JSON qua stdin, đọc event JSONL trả về.
- Nhận xét: ổn định không, có mất message không.

## Rào

- Không gửi dữ liệu công ty thật vào model ngoài trong spike này (chỉ dùng nội dung giả định).
- Không cài gì ra ngoài `C:\tmp\pi-spike\` + thư mục cài pi.

## Tiêu chí ĐẠT

- Báo cáo `docs/phieu-viec/ket-qua/pi-spike-home.md`: pi version, đường model nào
  sống/chết + lý do, task thử ĐẠT/CHƯA ĐẠT kèm log, nhận xét RPC mode, đề xuất bước tiếp.
- `trang-thai.md` → `xong-cho-duyet`.
