# VÉ: TEST-HEALTH-HOME (rà sức khoẻ bộ test trên máy nhà — chỉ phân loại, không sửa)

- Mã vé: `TEST-HEALTH-HOME`
- Role gợi ý: DEFAULT (chạy test nền + phân loại)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/test-health-home.md`

## Bối cảnh

Báo cáo `INDEX-VERIFY-HOME` §4 ghi nhận trung thực: chạy toàn bộ pytest trên máy nhà được ~1/3 chặng trong 15 phút đã thấy fail/error rải rác, dù vé đó không đụng một dòng code nào. Chưa ai kết luận được các fail đó là do môi trường máy nhà (đường dẫn Windows, fixture, thư mục tạm) hay lỗi code thật trên nhánh. Cần một lượt rà dứt điểm để từ nay verdict nào cũng có nền test đáng tin ở máy nhà.

## Việc phải làm

1. Chạy TOÀN BỘ pytest trên máy nhà tới khi xong (tiến trình nền tách phiên, ghi log đầy đủ; đặt thư mục tạm đủ lớn, tránh lỗi đầy đĩa/tạm). Ghi: tổng số test, pass/fail/error/skip, thời gian chạy.
2. Phân loại từng test fail/error vào nhóm nguyên nhân: (a) môi trường máy nhà (đường dẫn/fixture/quyền/thiếu tệp cục bộ), (b) phụ thuộc thứ tự/thời gian (flaky — chạy lại riêng lẻ có pass không), (c) nghi lỗi code thật.
3. Với nhóm (c): ghi test nào, thông điệp lỗi cốt lõi, và bằng chứng chạy-lại-riêng-lẻ. Không sửa code ở vé này — điều phối ra vé sửa riêng theo phân loại.
4. Đối chiếu nhanh: các test thuộc nhóm (c) có nằm trong các suite điều phối đã chạy xanh trên VM không (rag_v2, quality_harness...) — ghi rõ để khoanh vùng "chỉ đỏ ở máy nhà" vs "đỏ khắp nơi".

## Rào cứng

- Chỉ chạy test + phân loại: không sửa `src/`/`tests/`, không ghi index, không merge `main`.
- Chạy nền tách phiên để không chặn các thợ khác; heartbeat mốc mỗi ~15 phút vào mailbox như quy ước vé dài.
