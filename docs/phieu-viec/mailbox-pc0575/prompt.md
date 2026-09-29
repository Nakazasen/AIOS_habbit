# Ticket PC0575: pull code chính sách + GUI mới và xác nhận (2026-09-29 ~18:20 +07)

## Bối cảnh
Chủ sở hữu đã gỡ bỏ hạn chế gửi dữ liệu tới AI provider (DATA_POLICY.md 2026-09-29).
Muse đã push 2 commit lên branch `phieu-viec/rag-fix1`:
- `f27081d`: gỡ cấm trong DATA_POLICY.md + 4 file code (provider_safety, rag_v2/evidence, strong_answer_ui, notebook_qa)
- `941c31c`: dọn GUI (9 file: ide_handoff_bridge, antigravity_bridge, fine_tune_eligibility, rag_evidence, rag_answer_composer, final_answer_composer, mom_local_index, workspace_chat_ui, i18n)

P5 (mang cây ONNX) vẫn TẠM DỪNG chờ user upload model — ticket này độc lập, làm trước được.

## Việc cần làm
1. `git pull origin phieu-viec/rag-fix1` — xác nhận có đủ 2 commit trên (`git log --oneline -5`).
2. Kiểm tra nhanh (chỉ đọc, không sửa):
   - `src/aios_habit/provider_safety.py`: hàm `check_privacy_gate` không còn nhánh chặn local_only.
   - `src/aios_habit/workspace_chat_ui.py`: không còn dòng `st.warning(t("privacy_blocked_status"...`.
   - Chạy `python -m py_compile` cho 13 file đã đổi (liệt kê trong commit message) — tất cả phải OK.
3. Báo cáo vào `docs/phieu-viec/ket-qua/pc0575-gui-verify.md`: commit SHA đã pull, kết quả kiểm tra từng mục, py_compile OK/FAIL.
4. Cập nhật `trang-thai.md`: `xong-cho-duyet`, ghi commit SHA và đường dẫn báo cáo.

## Cấm
- Không merge `main`. Không đụng index production. Không sửa code để cho qua.
