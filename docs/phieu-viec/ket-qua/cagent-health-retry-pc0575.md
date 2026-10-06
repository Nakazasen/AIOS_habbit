# Kết quả kiểm tra lại sức khỏe đầu mối C-Agent trên mạng công ty (máy KDTVN-PC0575)

- Ngày đo: 2026-10-06 khoảng 13:26–13:33 +07.
- Mạng đang dùng: `vn-kdwireless` (xác nhận bằng lệnh `netsh wlan show interfaces`: SSID `vn-kdwireless`, băng tần 5 GHz, tín hiệu 75%).
- Đầu mối kiểm tra: giữ nguyên địa chỉ đã duyệt trong `src/aios_habit/cagent_api.py`, không thêm địa chỉ mới.
- Cách gọi: hàm `call_cagent_prediction` có sẵn, thời gian chờ tối đa 150 giây mỗi câu.
- Ba câu hỏi tái dùng đúng 3 câu của vé trước (Q0001/Q0609/Q2409) để so sánh trực tiếp.

## Ba câu hỏi mẫu

| Câu | Nhóm | Kết quả | Thời gian | Độ dài câu trả lời |
|-----|------|---------|-----------|--------------------|
| Q0001 | MOM | Thành công | 20,0 giây | 774 ký tự |
| Q0609 | LSU | Thành công | 26,4 giây | 361 ký tự |
| Q2409 | Điều tra lỗi | Thành công | 44,7 giây | 518 ký tự |

Không có lỗi kết nối ở câu nào. Cả 3 câu đều trả về nội dung trả lời hợp lệ.

## So sánh với vé trước

- Vé trước (`CAGENT-HEALTH-PC0575`, chạy trên mạng `KT_CHETAO`): cả 3 câu đều "Không kết nối được tới C-AGENT API" sau khoảng 42 giây mỗi câu.
- Vé này (mạng công ty `vn-kdwireless`): cả 3 câu đều thành công sau 20,0–44,7 giây.
- Suy ra: kết luận CHẾT ở vé trước chỉ đúng với mạng `KT_CHETAO` (mạng này không vào được đầu mối công ty, chỉ dùng tải Drive). Trên mạng công ty, đầu mối vẫn sống.

## Kết luận

- Trạng thái đầu mối: **SỐNG** (nhìn từ mạng công ty `vn-kdwireless`).
- Kết luận cho vé WIRE: **SẴN SÀNG** — có thể đẩy 3.392 cặp qua lane C-Agent khi máy chạy ở mạng công ty. Lưu ý độ trễ từng câu khá cao (20–45 giây), nên khi chạy hàng loạt cần tính thời gian chờ phù hợp và chạy theo mẻ nhỏ.
- Tuyệt đối không dùng kết quả mạng `KT_CHETAO` để kết luận về đầu mối.

## Cổng kiểm tra

- Biên dịch toàn bộ `src` và `tests`: đạt, không lỗi.
- Kiểm thử mẫu liên quan (`test_cagent_api.py` + `test_quality_harness.py`): 8/8 đạt.
- Kiểm thử toàn bộ: chưa chạy hết (vé này không đụng mã nguồn nên chỉ chạy mẫu liên quan).
- Lệnh `cli audit`: `PASS`.
- Nạp thử `workspace_chat_app`: đạt.
