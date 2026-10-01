# Quyết định chính sách sau vé B0-MEASURE (Muse chốt 2026-10-01 ~10:35 +07)

Ủy quyền: user nói "tự quyết định đi" (chat 10:24 +07) cho 2 quyết định chính sách mà
verdict B0-MEASURE đã nêu không tự chốt. Cơ sở: báo cáo `docs/phieu-viec/ket-qua/b0-measure.md`
(đo trên DB thật: KDTPS 15.707 ca, LSU 23.112 ca).

## QĐ1 — "mã cho ca không có mã" (trường error code)

Nguyên tắc: mục đích của trường là **định danh ca để tra cứu**. Trường được tính là ĐỦ
khi có một trong hai:
- (a) mã thật trích được (mã điện tử FXXX/E-series...), hoặc
- (b) phân loại H (不具合分類) — cho các nhóm khuyết điểm **không có hệ mã trong nguồn**
  (外観, 画像, 表示異常, 機能, 異常音, JAM, 組立, 治具, その他, C CALL, F CALL),
  và cho ca nhóm ERROR chưa trích được mã (ghi cờ `code_missing=1`).

Lý do: đòi "mã thật" ở nhóm không có mã trong nguồn là đòi cái không tồn tại —
thước đo hỏng, không phải dữ liệu hỏng. Ca ERROR thiếu mã thật vẫn tra cứu được
bằng hiện tượng (99,79%) + nguyên nhân (99,95%), chỉ kém chính xác hơn ca có mã.

Nợ chính xác (ghi rõ, không xóa): **3.537 ca nhóm ERROR thiếu mã thật** →
vé `BK-ERRCODE`: mở rộng `extract_code_from_text` quét cột N/O/L/M/R (+531 dòng đã
xác định trong `C:/tmp/b0-measure/scan4.out.txt`), đối chiếu 217 hồ sơ `KTD-*.xlsx`
trong `Lịch sử lỗi/C Call/` (+ thư mục mã trong `C Call`/`Log`) theo mã trong tên file,
phần còn lại xuất danh sách rà tay. B1 xếp hạng: ưu tiên ca có mã thật.

## QĐ2 — "ô đối sách trống"

Ô trống hoặc `ー` mà dòng **có nội dung ở cột M/O** (hành động tức thời khi phát sinh —
100% các ô trống đều có) = **"không cần đối sách chính thức"**, trường đối sách tính là đủ.

Lý do: quy trình có cờ `不要` riêng nhưng người nhập hay bỏ trống thay vì ghi;
ca không "trần trụi" vì đã có hành động tức thời để tra cứu.

Ràng buộc cho dữ liệu mới: form B0-FORM **cấm bỏ trống** đối sách — bắt buộc chọn:
đã có đối sách / không cần đối sách / chưa xác định.

## Hệ quả số

| List | Trước QĐ | Sau QĐ1+QĐ2 | Ngưỡng 90% |
|---|---|---|---|
| Điều tra lỗi (KDTPS) | 52,96% (nới) / 9,84% (chặt) | **99,48%** | **ĐẠT → Bước 0 ĐÓNG cho list này** |
| LSU | 0% | 0% | Không đạt — cần người dùng rà soát biên bản/họp chất lượng (`.msg`/`.pptx`) theo cụm; dữ liệu LSU mới qua form đã đủ chuẩn (4/4 ca đủ 5 trường) |

Nợ còn lại sau khi đóng: (1) `BK-ERRCODE` — 3.537 ca ERROR thiếu mã thật;
(2) `BK-82` — 82 dòng thiếu hiện tượng (33) / nguyên nhân (8) / công đoạn (39),
danh sách trong `C:/tmp/b0-measure/scan4.out.txt` (máy nhà). Hai vé đã xếp vào
hàng chờ ngay sau `B1-FEAT`.
