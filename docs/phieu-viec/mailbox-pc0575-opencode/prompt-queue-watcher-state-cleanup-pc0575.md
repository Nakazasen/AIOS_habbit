# Vé WATCHER-STATE-CLEANUP-PC0575 — Đưa tệp trạng thái watcher cũ ra khỏi cây git

**Bối cảnh:** Biên bản BB-INFRA-PARITY-01 (mục 3) ghi nhận tệp `docs/phieu-viec/mailbox/watcher_state_docs_phieu_viec_mailbox_pc0575.json` (trạng thái cũ từ 2026-09-29, không thuộc vòng hiện tại) đang nằm trong cây git của kho mã và chưa được gitignore — lệch nguyên tắc state phải nằm ngoài cây git.

**Việc cần làm (chỉ một việc):** gỡ tệp đó khỏi danh sách tệp được git theo dõi (giữ nguyên tệp trên đĩa local) và bổ sung mẫu `watcher_state_*.json` vào `.gitignore` của kho mã nếu chưa có.

**Đầu ra:** một commit trên nhánh việc chứa đúng hai thay đổi trên + một dòng `ghi_chu` trong hộp thư ghi mã commit. Không cần báo cáo riêng.

**Yêu cầu chất lượng:** sau commit, `git status` sạch; không tệp nào khác bị ảnh hưởng; các watcher đang chạy không bị ngắt.

**Cách làm:** kiểm tra trước xem có tiến trình nào đang ghi tệp đó không (mtime gần đây thì dừng và báo lại), rồi gỡ theo dõi + gitignore + commit.

**Phân quyền:** chỉ đụng đúng tệp state nêu trên và `.gitignore`. Không xoá tệp trên đĩa, không sửa nội dung hộp thư hay mã nguồn.
