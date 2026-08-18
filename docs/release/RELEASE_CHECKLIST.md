# Danh Mục Kiểm Tra Phát Hành (Release Checklist)

Status: `ACTIVE`
Owner role: Release owner / reviewer
Last reviewed: 2026-08-16
Review cadence: Every intended release or hotfix

## Phạm vi và Khả năng Truy xuất Nguồn gốc (Scope and Traceability)

- [ ] Phạm vi Gate Card, các phi mục tiêu (non-goals) và phương án hoàn tác (rollback) là hiện hành.
- [ ] Các bản ghi yêu cầu / ADR / hợp đồng giao diện / rủi ro phản ánh đúng thay đổi.
- [ ] Trạng thái trong CHANGELOG và PROJECT_HANDOVER là đúng sự thật thực tế.

## Chất lượng (Quality)

- [ ] `uv run --no-sync --group dev python scripts/check_docs.py` đạt (PASS).
- [ ] `uv run --no-sync --group dev python -m compileall src tests` đạt (PASS).
- [ ] `uv run --no-sync --group dev pytest -q` đạt (PASS).
- [ ] Lệnh CLI audit đạt (PASS) không có lỗi / cảnh báo.
- [ ] Import Workspace Chat đạt (PASS).
- [ ] `git diff --check` và `git diff --cached --check` đạt (PASS).
- [ ] Các bài kiểm thử trọng điểm bao phủ đầy đủ các hợp đồng đã thay đổi.

## Quyền riêng tư và Bảo mật (Privacy and Security)

- [ ] Tuyệt đối không có secret, tệp runtime riêng tư, tài liệu thô, ảnh chụp màn hình hoặc artifact chẩn đoán cục bộ nào bị đưa vào stage/theo dõi trong Git.
- [ ] Tác động đến mô hình mối đe dọa / quyền riêng tư / phụ thuộc đã được đánh giá.
- [ ] Nếu bản phát hành kích hoạt hoặc quảng bá một tuyến provider bên ngoài thực tế, thẻ `AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION` phải ở trạng thái `DONE` kèm theo bằng chứng kiểm thử hồi quy và đe dọa/quyền riêng tư cụ thể của tuyến.
- [ ] Mọi bài kiểm thử live smoke với provider đều chạy tường minh, generic, đã làm sạch và được ghi lại mà không chứa API key hoặc nội dung nguồn riêng tư.
- [ ] Các quyết định về kênh báo cáo bảo mật và liên hệ sự cố đã được xem xét nếu bản phát hành là công khai.

## Phân phối và Hoàn tác (Delivery and Rollback)

- [ ] Môi trường được hỗ trợ đã được lựa chọn / kiểm chứng theo chính sách.
- [ ] Các bước cài đặt / đóng gói sạch và tạo SBOM đã được thực hiện nếu việc phân phối nằm trong phạm vi; nếu không, bản phát hành phải được gắn nhãn chỉ dùng dạng checkout mã nguồn (checkout-only).
- [ ] Phiên bản / commit đã kiểm chứng trước đó được chỉ định rõ ràng làm mục tiêu hoàn tác (rollback target).
- [ ] Tác động sao lưu / di chuyển dữ liệu được đánh giá trước khi thay đổi dữ liệu lưu trữ bền vững.
- [ ] Đợt diễn tập sao lưu / khôi phục tổng hợp là hiện hành cho các thay đổi hành vi JSONL/SQLite; tuyệt đối không tuyên bố RTO/RPO hoặc khôi phục đa phiên bản nếu thiếu bằng chứng độc lập.

Mỗi hộp kiểm (checkbox) là một bằng chứng, không phải là sự thay thế cho log lệnh hay quyết định của người review.

