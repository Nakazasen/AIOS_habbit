# Vé CAGENT-HEALTH-RETRY-PC0575 — Kiểm tra lại C-Agent trên mạng công ty

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Thợ:** opencode.
**Role gợi ý:** SMOL (kiểm tra nhanh).

## Bối cảnh

- Vé `CAGENT-HEALTH-PC0575` trước đó chạy trên mạng KT_CHETAO và kết luận endpoint
  CHẾT — nhưng user xác nhận KT_CHETAO KHÔNG vào được kdtvn (đặc tính mạng,
  chỉ dùng tải Drive). Kết luận đó VÔ GIÁ TRỊ.
- User đã chuyển sang mạng công ty (`vn-kdwireless`) lúc ~13:20 +07.
- Vé này: kiểm tra lại endpoint trên MẠNG CÔNG TY hiện tại.

## Rào mạng (bắt buộc)

- Chạy kiểm tra trên mạng ĐANG DÙNG (vn-kdwireless). Ghi rõ tên mạng/Wi-Fi
  đang dùng vào báo cáo (lệnh `netsh wlan show interfaces`).
- TUYỆT ĐỐI KHÔNG kết luận gì từ mạng KT_CHETAO.

## Endpoint

- `https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f`
- Module gọi: `src/aios_habit/cagent_api.py`, hàm `call_cagent_prediction`.
- Tuyệt đối không hardcode URL mới, không bịa endpoint.

## Việc cần làm (đúng thứ tự)

1. Xác nhận mạng đang dùng (ghi tên Wi-Fi vào báo cáo).
2. Gọi 3 câu hỏi mẫu qua `call_cagent_prediction` (lấy từ `wire-qa-mapping.jsonl`,
   1 câu mỗi nhóm MOM/LSU/Điều-tra-lỗi). Đo thời gian phản hồi từng câu.
3. Ghi nhận: endpoint SỐNG/CHẾT, độ trễ từng câu (giây), có lỗi gì không.
4. Báo cáo ngắn `docs/phieu-viec/ket-qua/cagent-health-retry-pc0575.md`:
   tên mạng, trạng thái, 3 số đo, kết luận SẴN SÀNG / CHƯA SẴN SÀNG cho vé WIRE.

## Rào cứng

- Chỉ đọc/kiểm tra, không sửa code lane C-Agent.
- Không merge `main`. Python 3.11.

**Verdict:** Muse review trên bằng chứng độc lập.
