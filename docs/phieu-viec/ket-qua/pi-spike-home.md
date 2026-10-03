# Vé PI-SPIKE-HOME — báo cáo máy nhà

- Ngày: 2026-10-03, khoảng 11:02–11:08 +07.
- Nhánh: `phieu-viec/rag-fix1`. Không merge `main`. Không đụng index production.
- Phạm vi: `C:\tmp\pi-spike\` và cài pi toàn cục qua npm. Không gửi dữ liệu công ty.

## 1. Cổng gate

- Vé `moi` khi nhận. Điều kiện mở đã có: máy nhà bật, Node sẵn. Không đặt `cho-muse`. Không quay no-op.
- Vé tóm tắt `KNOWLEDGE-DIGEST-PROVIDER-SWITCH` tạm đỗ theo điều phối Muse. Checkpoint local còn **847/889**. Spike này không resume batch.

## 2. Cài pi

- Node `v24.13.0`, npm `11.18.0`. Không cần cài Node thêm.
- Lệnh: `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`. Thêm 147 gói, khoảng 33 giây.
- `pi --version`: **1.0.0**.
- Telemetry tắt ở env máy (user): `PI_TELEMETRY=0`, `PI_SKIP_VERSION_CHECK=1`.

## 3. Đường model

| Đường | Kết quả | Lý do |
|---|---|---|
| Đăng nhập sẵn `~/.pi/agent/auth.json` | chết | File 2 byte, không có phiên đăng nhập. |
| `google/gemini-2.5-flash-lite` + `GEMINI_API_KEY` | **sống** | Task tạo file và sửa file đều gọi được. Model log: `gemini-2.5-flash-lite`, provider `google`. |
| Cầu nối `127.0.0.1:8585/health` | chết | Từ chối kết nối. Không cấu hình custom provider. |
| DeepSeek | chết | HTTP 402 hết số dư (đo lúc batch tóm tắt, không gọi lại trong spike). |
| OpenRouter | chết | HTTP 402 chưa mua credit. |
| Groq | chết | HTTP 403 mã 1010. |
| Mistral | chết | HTTP 429. |
| NVIDIA NIM | không dùng | Một lượt thử model trước đó quá 20 giây, không trả lời. Không quay vòng. |

Đường sống dùng cho task và RPC: Gemini Flash Lite. Không in khóa.

## 4. Task thử

Thư mục `C:\tmp\pi-spike\`. Lệnh qua `pi -p --approve --no-session --thinking off --model google/gemini-2.5-flash-lite`.

### 4.1 Tạo file — ĐẠT (nội dung lệch nhẹ yêu cầu 3 dòng)

- Prompt: tạo `bao-cao-thu.md`, báo cáo tuần giả định, có 1 bảng.
- Exit 0. Tool `write` thành công. Log: `C:\tmp\pi-spike\pi-create.log`.
- File có tiêu đề, 1 đoạn văn, và 1 bảng Markdown 3 hàng. Không có dữ liệu công ty, không có rác ngoài báo cáo.
- Chưa tách đúng 3 dòng văn riêng. Harness ghi file được.

### 4.2 Sửa file

- Lần 1, đúng ý vé «thêm 1 dòng kết luận ở cuối»: **CHƯA ĐẠT**. Model hỏi lại nội dung, không sửa file. Log: `pi-edit.log`.
- Lần 2, nhắc tự soạn câu và ghi ngay: **ĐẠT**. Tool `edit` thành công sau 1 lần `edit` lỗi khớp chữ. Dòng cuối: `**Kết luận:** Dự án đang đi đúng hướng và chúng ta sẽ cố gắng hết sức để hoàn thành mục tiêu đề ra.` Bảng giữ nguyên. Log: `pi-edit2.log`.

## 5. RPC mode

- Lệnh: `pi --mode rpc`, stdin một dòng JSON `{"id":"req-1","type":"prompt","message":"Chỉ trả đúng một từ: ping. Không gọi tool."}`.
- Exit 0. 15 event JSONL, không dòng hỏng, stderr rỗng.
- Có `response` success cho `prompt`, có chữ `ping`, kết bằng `agent_end` rồi `agent_settled`. Không thấy mất message trong lượt này.
- Nhận xét: một lệnh thì ổn định. Chưa thử hàng đợi, ngắt giữa chừng, hay nhiều lệnh liên tiếp.

## 6. Đề xuất bước tiếp

- Chưa gắn policy gate. Chưa nối Streamlit.
- Nếu làm tiếp: giữ Flash Lite cho task ngắn; Flash thường đang hết quota cụm 429, không dùng cho batch dài.
- Cầu nối cần bật sidecar trước khi thử custom provider. Spike này chưa viết extension.
- Không merge `main`.
