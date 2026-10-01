# Đặc tả API realtime JIG (J1-RT)

Mục đích: cổng để jig đẩy dữ liệu đo lên server realtime, và server đẩy ngược
về AI để phân tích, cảnh báo xu hướng dẫn đến phát sinh NG. Triển khai tham
chiếu: `src/aios_habit/production_prediction/stream_api.py` (server),
`rt_consumer.py` (AI), `rt_replay.py` (phát lại mô phỏng).

## 1. Endpoint jig → server: nhận dòng log

- **Địa chỉ:** `POST /api/v1/jig/stream-log`
- **Định dạng:** JSON — một object, một mảng object, hoặc NDJSON (mỗi dòng một
  object JSON). `Content-Type: application/json`.
- **Format bản tin** (mỗi dòng):

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `unit_serial` | Có | Mã đơn vị sản phẩm (vd serial LSU) |
| `jig_id` | Không (mặc định `unknown`) | Mã jig/đồ gá đo |
| `metric` | Có | Tên thông số (vd `SKEW:BLACK`, `BOW:BLACK:0`) |
| `value` | Không | Giá trị đo (số; dấu phẩy được đổi thành chấm) |
| `unit` | Không | Đơn vị (vd `um`) |
| `timestamp` | Không | ISO 8601 thời điểm đo; thiếu thì server lấy giờ nhận |
| `status` | Không | Trạng thái dòng (mặc định `unknown`) |
| `nguon` | Không | `that` (mặc định) hoặc `SIMULATED_REALTIME` (phát lại mô phỏng) |

- **Tần suất:** agent trên jig gom theo lô — mỗi 5–30 giây hoặc mỗi 20–50 đơn
  vị đo gửi một lô; tối đa **100 bản tin/lô** (server cắt bớt phần thừa).
- **Xác thực:** header `Authorization: Bearer <token>`. Mỗi jig một token riêng,
  cấu hình phía server (`StreamListener(auth_token=...)`). Sai/thiếu → **401**
  `{"trang_thai": "Thiếu hoặc sai mã truy cập."}`. Không đặt token thì server
  chấp nhận mọi request (chỉ dùng trong mạng nội bộ tin cậy).
- **Retry:** lỗi mạng/timeout → gửi lại với backoff mũ (0,5s → 1s → 2s, tối đa
  3 lần). Nhận **200** `{"trang_thai": "Đã ghi nhận", "so_dong": N}` mới coi là
  xong; không gửi lại lô đã được 200 (tránh trùng — server không khử trùng lặp,
  trách nhiệm thuộc về agent gửi).
- **Mã lỗi:** 400 bản tin sai format (kèm lý do tiếng Việt), 401 sai auth,
  404 sai địa chỉ.

## 2. Endpoint server → AI: lấy sự kiện

- **Địa chỉ:** `GET /api/v1/jig/events?since=<cursor>&limit=<n>`
- **Kiểu:** poll theo cursor (mặc định; đơn giản, không giữ kết nối). `since`
  là cursor của sự kiện cuối đã xử lý; server trả các sự kiện **mới hơn**,
  đúng thứ tự cursor tăng dần.
- **Format envelope** (mỗi sự kiện):

```json
{
  "cursor": 123,
  "thoi_gian": "2026-10-01T19:20:00",
  "loai": "canh_bao_drift",
  "jig_id": "2ND-1035",
  "metric": "SKEW:BLACK",
  "noi_dung": {"gia_tri": 1.5, "don_vi": "um", "z": 4.2, "chi_tiet": "..."}
}
```

- **Các loại sự kiện:** `canh_bao_drift` (thông số trôi khỏi nền — server tự
  sinh khi nhận dòng mới), `thong_tin` (bản tin vận hành, vd bắt đầu/kết thúc
  phát lại).
- **Retry:** consumer KHÔNG tiến cursor khi gặp lỗi; thử lại backoff mũ rồi mới
  báo lỗi tiếng Việt. Resume luôn từ cursor cuối đã lưu — sự kiện lưu bền trong
  SQLite nên không mất khi server/AI khởi động lại.
- **Xác thực:** cùng Bearer token như endpoint 1.
- **Nhịp poll gợi ý:** mỗi 5–10 giây; `limit` tối đa 500/lần.

## 3. Phát hiện drift (server tự sinh sự kiện)

Khi nhận dòng mới, server so **trung bình 10 điểm gần nhất** với **nền 40 điểm
trước đó** của cùng cặp (jig, thông số); lệch ≥ 3σ của nền → sinh 1 sự kiện
`canh_bao_drift` cho cả đợt vi phạm (không spam mỗi điểm). Ghi chú kỹ thuật:
hàm `ewma_status` cũ so EWMA với trung bình *cùng* cửa sổ nên tự triệt tiêu và
thực tế không bao giờ kích hoạt (đã chứng minh bằng số) — giữ lại vì tương
thích ngược, đường realtime dùng `phat_hien_drift`.

## 4. Giới hạn và lưu ý vận hành

- Server lưu SQLite (WAL mode); backup định kỳ theo quy trình backup chung.
- Chỉ bind LAN nội bộ (`127.0.0.1` hoặc IP LAN), không mở ra internet.
- Prototype hiện tại là minh chứng kỹ thuật: phát lại (`rt_replay`) gắn nhãn
  `SIMULATED_REALTIME` để phân biệt tuyệt đối với dữ liệu thật trực tiếp.
