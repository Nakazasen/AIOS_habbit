# Kịch bản triển khai và xác minh

## 1. Trạng thái

Goal 010 đang mở lại để đơn giản hóa và sửa finding ngày 2026-09-09. Các bằng chứng G0–G10 cũ chỉ chứng minh triển khai trước đó; không được dùng để tuyên bố thiết kế mới đã sẵn sàng.

Chỉ dùng fixture giả lập trong kiểm thử. Không đưa audio thật, bản chép lời thật, DB thật hoặc dữ liệu `local_only` vào Git hay báo cáo.

## 2. Trình tự sửa

1. Sửa test để mô tả hợp đồng mới trước khi thay hành vi.
2. Sửa lưu trữ dữ liệu thô và chép lời thật/giả.
3. Bỏ điều kiện quyền khỏi Goal 010, thêm bản ghi trách nhiệm.
4. Nối lựa chọn thư viện và đường ghi snapshot an toàn.
5. Đơn giản hóa bốn chặng giao diện.
6. Chạy test tập trung, full quality gate và lượt đi bộ giao diện.
7. Audit độc lập; finding còn mở thì không nâng trạng thái Goal.

## 3. Kịch bản người dùng bắt buộc

### Kịch bản A — Dùng cá nhân

1. Chọn “Thư viện cá nhân”.
2. Nhập một chủ đề, bắt đầu phỏng vấn và trả lời bằng chữ.
3. Tạm dừng, khởi động lại ứng dụng và tiếp tục đúng phiên.
4. Xem/sửa bản nháp, nguồn và điểm chưa chắc chắn.
5. Ghi tên, độ tự tin, căn cứ, nguồn đã kiểm tra và xác nhận trách nhiệm.
6. Đưa vào thư viện rồi hỏi lại và nhận đúng nội dung có nguồn.

**Kết quả mong đợi**: không đăng nhập, không chọn quyền/phạm vi/ngân sách và không thấy token kỹ thuật ở luồng chính.

### Kịch bản B — Dùng chung

1. Chọn “Thư viện dùng chung” và một thư mục fixture.
2. Đổi sang thư viện cá nhân rồi đổi lại mà không khởi động lại.
3. Hai tiến trình cùng thử ghi: một tiến trình hoàn thành, tiến trình còn lại giữ bản nháp và nhận hướng dẫn thử lại.
4. Mô phỏng mất kết nối hoặc hết dung lượng giữa chừng.

**Kết quả mong đợi**: không có máy ghi cố định, không ghi đè âm thầm, thư viện dùng được gần nhất còn nguyên và có bản sao lưu.

### Kịch bản C — Âm thanh và quyền riêng tư

1. Từ chối xử lý âm thanh và tiếp tục bằng chữ.
2. Đồng ý, dùng audio fixture, xem và sửa bản chép lời.
3. Xác nhận mã máy, con số và đơn vị rồi tạo bản nháp.
4. Rút đồng ý và tiếp tục bằng chữ.
5. Mô phỏng bộ máy chép lời thật không sẵn sàng.

**Kết quả mong đợi**: không có raw audio/bản chép lời trong DB hồ sơ hoặc thư viện; runtime không dùng mock rồi báo là kết quả thật; giao diện không có công tắc fixture.

### Kịch bản D — Trách nhiệm và thu hồi

1. Thử xác nhận khi thiếu từng trường trách nhiệm; hệ thống giải thích trường còn thiếu.
2. Mở form xác nhận rồi sửa nội dung; hệ thống yêu cầu xem lại bản mới.
3. Xác nhận và đưa vào thư viện.
4. Thu hồi từ lịch sử, không nhập mã gói bằng tay.

**Kết quả mong đợi**: bản đang dùng bị loại khỏi truy xuất, lịch sử cũ vẫn còn và tên ghi nhận không bị gọi là danh tính xác minh.

### Kịch bản E — Người không chuyên

Người kiểm thử không đọc tài liệu kỹ thuật trước. Họ được giao bốn việc: chọn nơi lưu, hoàn thành phỏng vấn chữ, sửa/xác nhận bản nháp và đưa vào thư viện.

Ghi lại:

- Việc có hoàn thành không.
- Chỗ phải hỏi người hướng dẫn.
- Từ ngữ không hiểu.
- Nút hoặc bước bị bỏ sót.

Kịch bản chỉ đạt khi hoàn thành đủ bốn việc không cần trợ giúp. Không cần nghiên cứu người dùng quy mô lớn hoặc dựng bộ công cụ phân tích hành vi.

## 4. Kiểm thử tập trung

```powershell
uv run --no-sync --group dev pytest tests/test_expert_interview_privacy.py -q
uv run --no-sync --group dev pytest tests/test_local_transcription.py -q
uv run --no-sync --group dev pytest tests/test_controlled_knowledge_artifact.py -q
uv run --no-sync --group dev pytest tests/test_knowledge_publication.py tests/test_knowledge_publication_recovery.py -q
uv run --no-sync --group dev pytest tests/test_expert_knowledge_e2e.py -q
```

Task sửa phải bổ sung kiểm thử cho lựa chọn thư viện, thông tin trách nhiệm, hợp đồng nhóm tin cậy và bề mặt UI. Không xóa test cũ để lấy PASS; test quyền cũ được chuyển thành test tương thích lịch sử hoặc loại khỏi hợp đồng Goal 010 với lý do ghi rõ.

## 5. Quality gate trước khi đóng lại

```powershell
python --version
uv run --no-sync --group dev python scripts/check_docs.py
uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
git diff --check
```

Sau đó chạy smoke giao diện và kịch bản E. Nếu full suite có lỗi môi trường hoặc ngoài phạm vi, ghi đúng số lượng/phạm vi và giữ Goal ở trạng thái chưa sẵn sàng; không đổi test tập trung thành tuyên bố toàn hệ thống đạt.
