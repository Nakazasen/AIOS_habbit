# VÉ: TEST-RED5-FIX-HOME (khép 5 ca đỏ còn lại + vệ sinh test gói tùy chọn graphify)

- Mã vé: `TEST-RED5-FIX-HOME`
- Role gợi ý: DEFAULT (code + test)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/test-red5-fix-home.md`
- Căn cứ: báo cáo `test-health-round2-home.md` §5. Điều phối đã chạy đối chiếu trên VM (08/10 ~02:50): `dieu_huong` + `phase2i_mapping` đỏ cả trên VM; 3 ca còn lại (manifest, provider_limitations, xlsx_reparse) XANH trên VM — là ca "chỉ đỏ ở máy nhà", phải truy vết khác biệt trạng thái trước khi kết luận.

## Nguyên tắc

Như vé RED22: mỗi ca kết luận code-sai (sửa code) hoặc test-cũ/trạng-thái-lệch (sửa test/tệp sinh kèm căn cứ) — cấm nới test vô căn cứ, cấm xoá assertion.

## Nhóm 1 — 5 ca nghi code (theo thứ tự)

1. `test_provider_limitations_contain_accurate_reasons` — thiếu lý do `cloud_privacy_blocked` ở tầng synthesis (đỏ cũ, liên quan chính sách riêng tư: đối chiếu DATA_POLICY hiện hành trước khi quyết code hay test).
2. `test_dieu_huong_chinh_co_ten_tieng_viet_nhin_thay` — test đòi chuỗi tiêu đề `### 💬 Trợ lý AIOS` (FR-027/SC-015) trong `workspace_chat_app.py`, code hiện không còn: xác định đặc tả còn hiệu lực không (rà spec/ADR liên quan) → còn hiệu lực thì khôi phục tiêu đề đúng chỗ; đã bị thay thế bởi quyết định UX sau thì cập nhật test bám quyết định đó, ghi rõ căn cứ.
3. `test_phase2i_owner_choice_mapping_helpers` — ánh xạ nhãn owner-choice sai.
4. `test_public_v3_manifest_checksums_match_files` — băm manifest `corpus_public_v3.json` lệch file `src-quality-process`: xác định manifest là tệp sinh (tạo lại đúng quy trình) hay file đã đổi mà manifest chưa cập nhật; xanh trên VM nên soi khác biệt trạng thái máy nhà trước.
5. `test_app_no_xlsx_reparse_in_ai_path` — còn gọi `extract_xlsx_text` trong đường AI: xác định đường gọi thật ở máy nhà và xử lý như các ca trên.

## Nhóm 2 — vệ sinh gói tùy chọn (môi trường hoá thành skip sạch)

- 9 test `test_graphify_adapter.py` + 1 smoke phụ thuộc gói tùy chọn `graphifyy==0.9.50` không có trong venv máy nhà: gắn cơ chế bỏ qua sạch khi thiếu gói (theo đúng mẫu các test tùy chọn khác trong repo nếu có), KHÔNG cài gói vào môi trường chính ở vé này. Sau sửa: các test này phải `skipped` có lý do rõ trên máy nhà thay vì fail/error.

## Nhóm 3 — bảo trì nhỏ

- `test_uv_lock_check_succeeds`: đồng bộ lại `uv.lock` theo `pyproject` hiện hành (chạy `uv lock` đúng quy trình repo, commit kèm báo cáo nêu thay đổi chính). Ca timeout cài venv cô lập (môi trường) chỉ phân loại lại, không sửa.

## Kiểm chứng & rào

- Sau mỗi nhóm chạy lại file test liên quan; cuối vé chạy lại toàn bộ các file đã đụng + đối chiếu đỏ trước/sau.
- Cổng repo: Python 3.11, compileall, `cli audit`, import app. Không ghi index, không merge `main`.
