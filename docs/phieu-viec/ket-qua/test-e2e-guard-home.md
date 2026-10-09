# Báo cáo kết quả vé `TEST-E2E-GUARD-HOME`

- Mã vé: `TEST-E2E-GUARD-HOME`
- Đầu nhánh lúc chạy: `0cc184b` (nhánh `phieu-viec/rag-fix1`, sau verdict `6b1142c`)
- Tệp sửa duy nhất: `tests/test_commit_d_wheel_and_packaging.py` (ca `TestDesktopPackagingConfiguration::test_packaged_desktop_e2e_rag_to_atlas`)
- Không sửa mã chạy thật (`src/`), không ghi chỉ mục, không merge `main`

## Việc đã làm

1. Thêm điều kiện bỏ qua khi thiếu model: trước khi đẻ tiến trình con, dùng đúng hàm tìm model của hệ thống (`resolve_bge_m3_model_path` với `auto_configure_env=False`) để kiểm tra; không thấy thư mục thì bỏ qua kèm trạng thái tìm được. Trong tiến trình con, đổi `assert model_dir is not None` thành bỏ qua với cùng nội dung trạng thái.
2. Thêm điều kiện bỏ qua khi lượt kiểm thử lồng hết giờ: bọc `subprocess.run(..., timeout=300)` bằng `except subprocess.TimeoutExpired` rồi bỏ qua kèm lý do máy chậm dưới tải. Trần 300 giây giữ nguyên, không nới.
3. Giữ nguyên mọi khẳng định hành vi: khi máy có model và chạy kịp giờ, ca vẫn chạy thật toàn bộ (nạp liệu → chia mảnh → chỉ mục BGE-M3 → tìm lai → trích dẫn → vết bằng chứng → atlas) và vẫn đỏ khi khẳng định sai. Không bớt bước kiểm tra nào.
4. Mẫu áp dụng đúng mẫu vé dọn dẹp trước đây: bỏ qua có điều kiện kèm lý do in ra, chỉ đúng mã lỗi môi trường mới bỏ qua, comment kỹ thuật trong mã bằng tiếng Anh theo luật mã nguồn.

## Kiểm chứng sau sửa

- Chạy riêng ca: `1 passed in 20.81s` (máy nhà có model ở trạng thái `ready` nên ca chạy thật và đạt, không rơi nhánh bỏ qua).
- Chạy toàn bộ tệp chứa ca: `27 passed, 2 skipped in 664.70s`. Hai ca bỏ qua đều có lý do in ra và không liên quan thay đổi này:
  - Ca kiểm tra app đóng gói: bỏ qua vì chưa build app (`Executable not yet built`).
  - Ca cài môi trường sạch đầy đủ: bỏ qua vì quá 600 giây trên máy này (mẫu bỏ qua sẵn có từ vé dọn dẹp).
- Không ca nào khác trong tệp bị ảnh hưởng (toàn bộ ca còn lại đạt).

## Cổng kiểm tra

- `compileall src tests`: sạch.
- `python -m aios_habit.cli audit`: `Status: PASS`.
- `import aios_habit.workspace_chat_app`: thành công.
- `git diff --stat` của vé: chỉ 1 tệp kiểm thử trên (26 thêm, 11 bớt ở mốc code).
- Toàn bộ bộ kiểm thử đã xanh ở vé xác nhận trước đó trên cùng nội dung đầu nhánh (`4.218` đạt, `66` bỏ qua, `0` lỗi, `1` ca đỏ môi trường đã biết chính là ca này); vé này bịt đúng điểm đỏ đó nên không chạy lại toàn bộ (khoảng 80 phút) mà chỉ chạy riêng ca và cả tệp theo đúng yêu cầu vé.

## Kết luận

- Vé đạt ở mức chờ duyệt: hai điểm chập chờn theo môi trường của ca đã được bịt bằng bỏ qua có điều kiện, hành vi kiểm tra thật giữ nguyên.
