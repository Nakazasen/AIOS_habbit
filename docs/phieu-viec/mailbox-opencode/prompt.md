# VÉ: TEST-RED22-FIX-HOME (khép các test đỏ đã xác nhận trên nhánh — ưu tiên nhóm riêng tư)

- Mã vé: `TEST-RED22-FIX-HOME`
- Role gợi ý: DEFAULT (code + test)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/test-red22-fix-home.md`
- Căn cứ: báo cáo `docs/phieu-viec/ket-qua/test-health-home.md` + điều phối đã chạy đối chiếu trên VM (07/10 ~23:00): **16 test fail y hệt trên VM** → đỏ thật trên nhánh, không phải môi trường máy nhà.

## Nguyên tắc xử lý (đọc kỹ)

Mỗi test đỏ là một vụ **lệch giữa code và đặc tả**: hoặc code sai (sửa code), hoặc test đã cũ so với quyết định đã chốt (sửa test + ghi rõ quyết định làm căn cứ trong báo cáo). **Cấm** xoá assertion/nới test vô căn cứ để lấy xanh, cấm tắt test. Từng test phải có kết luận "code sai" hay "test cũ" kèm bằng chứng trong báo cáo.

## Phạm vi theo thứ tự ưu tiên (làm và commit theo từng nhóm)

1. **Nhóm riêng tư / chặn xuất (5)** — ưu tiên cao nhất: `test_render_chat_bubble_denies_untrusted_metadata_path_traversal` (omnibar), `test_local_only_cloud_provider_blocked_and_vi_instruction` (antigravity handoff), `test_missing_db_returns_none`, `test_phase4_owner_pilot_local_only_blocks_external_export` (`allowed_external=True` thay vì `False`), `test_mom_prompt_pack_includes_refs_and_privacy_warning` (thiếu dấu `local_only`). Lưu ý bối cảnh: user đã gỡ rào gửi dữ liệu ra AI ngoài cho luồng sổ tay tri thức (DATA_POLICY 02/10) — nếu test nào thuộc luồng đó thì đối chiếu quyết định này khi kết luận code-sai/test-cũ; các rào riêng tư ngoài luồng đó vẫn phải giữ nguyên.
2. **Nhóm lane RAG v2 đã xác nhận trên VM (6):** `test_dev_cli_evaluate_uses_selected_sources_and_returns_local_metrics`, `test_full_pipeline_pass`, `test_privacy_local_only_passes` (eval_harness), 2 test `cjk_prefilter` (opt_pyloops), `test_architecture_composer_rejects_noise_and_unscoped_multi_facet_fillers` (synthesis). (3 test synthesis_provider đỏ ở máy nhà nhưng XANH trên VM — không sửa ở vé này; ghi vào báo cáo để theo dõi riêng.)
3. **Nhóm giao diện/i18n (2):** 2 test `test_ast_*_zero_hardcoded_vietnamese` (workspace_chat_ui + workspace_chat_app) — chuỗi cứng tiếng Việt phải đi qua cơ chế i18n hiện hành của repo.
4. **Nhóm dữ liệu (1) + MOM OCR (3):** `test_expert_knowledge_e2e_full_lifecycle` (`NOT_APPLICABLE` thay vì `BLOCKED_PRIVACY`); 3 test OCR trong `test_mom_local_pilot.py` (đỏ trên VM, máy nhà không báo — kiểm tra và xử lý như các nhóm trên).

## Kiểm chứng & báo cáo

- Sau mỗi nhóm: chạy lại đúng các file test của nhóm + các suite liên quan; cuối vé chạy lại TOÀN BỘ các file đã đụng + đối chiếu số đỏ trước/sau trong báo cáo.
- Cổng repo: Python 3.11, compileall + `cli audit` + import app.
- Không đụng index, không đụng các file của vé khác đang chạy (rag_v2/index.py của agy công ty; workspace_chat_app.py chỉ đụng đúng phần i18n thuộc nhóm 3 và phải báo cáo rõ dòng đã sửa).
- Không merge `main`.
