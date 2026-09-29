# Ticket PC0575: dọn test cũ + code chết theo chính sách mới (2026-09-29 ~18:40 +07)

## Bối cảnh
Verdict vé `pc0575-gui-verify`: **ĐẠT** (3/3 mục, py_compile 13/13 OK, smoke 5/5; Muse
verify độc lập 2026-09-29 ~18:35 +07 trên HEAD `bb964df2` bằng grep + py_compile trên VM).
Hệ quả còn tồn: 16 test cũ ở 10 file vẫn assert hành vi chặn CŨ (đã gỡ theo quyết định
chủ sở hữu 2026-09-29, `00_governance/DATA_POLICY.md`) nên FAIL — OMP đúng là không sửa
code để cho qua (ghi nhận tốt). Vé này dọn dứt điểm, độc lập với P5 (P5 vẫn tạm dừng
chờ user upload model).

## Việc cần làm
1. `git pull origin phieu-viec/rag-fix1` — xác nhận HEAD có commit verdict trước.
2. Cập nhật/xóa đúng 16 test theo chính sách MỚI (danh sách chi tiết trong
   `docs/phieu-viec/ket-qua/pc0575-gui-verify.md` mục 4, bảng #1–#16):
   - `tests/test_provider_safety.py` (#1, #2): sửa assert theo hành vi mới —
     không còn chặn `local_only` / `metadata-only`.
   - `tests/test_rag_evidence.py` (#3, #4, #5): `is_external_allowed` trả `True` cho
     `local_only`; chuỗi mới là `"owner allows provider use"` (thay `"External export NOT allowed"`).
   - `tests/test_rag_v2_evidence.py` (#6, #7): `cloud_allowed=True` khi có `local_only`.
   - `tests/test_strong_answer_ui.py` (#8): hết chặn `blocked_direct_provider_call` cho `local_only`.
   - `tests/test_antigravity_bridge.py` (#9–#13): hết chặn cục bộ nên test cũ gọi mạng thật
     (lỗi DNS/timeout/403) — chuyển thành assert không chặn ở cổng (dùng mock, KHÔNG gọi
     mạng thật) hoặc skip có lý do ghi rõ trong báo cáo.
   - `tests/test_fine_tune_eligibility.py` (#14): `local_only` không còn loại fine-tune.
   - `tests/test_rag_answer_composer.py` (#15): `allowed_external` giờ `True`.
   - `tests/test_ide_handoff_bridge.py` (#16): thông điệp mới (chuỗi `"local_only evidence"` đã đổi).
   - Quy tắc: test phải assert đúng chính sách MỚI (chủ sở hữu cho phép gửi provider);
     chỉ xóa test khi hành vi nó kiểm không còn tồn tại — ghi rõ lý do sửa/xóa từng test
     trong báo cáo.
3. Dọn 2 điểm code chết (ghi trong báo cáo cũ, mục 5):
   - Chuỗi `privacy_blocked_status` trong `src/aios_habit/i18n.py` (chỉ còn định nghĩa,
     0 hit trong `src/`) — xóa sau khi grep xác nhận.
   - Nhánh `badge_data["type"] == "privacy_block"` trong `workspace_chat_app.py`
     (~dòng 3455) + hàm `render_privacy_block_message` — đường không tới được (không còn
     nguồn sinh badge `"privacy_block"` nào trong `src/`) — xóa sau khi grep xác nhận.
4. Chạy lại đúng 10 file test như vé trước — phải **0 FAIL** (toàn bộ PASS);
   `py_compile` mọi file đã đổi OK.
5. Báo cáo `docs/phieu-viec/ket-qua/pc0575-test-cleanup.md`: commit SHA đã làm, từng test
   sửa/xóa + lý do, kết quả pytest cuối (0 FAIL), code chết đã dọn.
6. Cập nhật `trang-thai.md`: `xong-cho-duyet`, ghi commit SHA và đường dẫn báo cáo.

## Cấm
- Không merge `main`. Không đụng index production. Không chạy batch embed.
- Không đụng mailbox máy nhà (`docs/phieu-viec/mailbox/` — E2v3 Phase B đang chạy).
- Không mở rộng scope: chỉ 16 test + 2 điểm code chết trên; phát hiện mới ghi vào
  báo cáo, không tự sửa thêm.
