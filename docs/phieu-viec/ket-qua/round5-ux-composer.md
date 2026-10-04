# Báo cáo ROUND5-UX-COMPOSER — máy nhà (h410asrock)

- Trạng thái: hoàn thành 3 việc bắt buộc — chờ Muse duyệt (`xong-cho-duyet`).
- Nhánh: `phieu-viec/rag-fix1`. Mã kiểm chính: `12f1744` (fix tràn nhãn) trên nền `92bdab5` (3 việc + công tắc khối) + `db3d4ed` (tinh chỉnh cột theo cửa sổ).
- Ngày: 2026-10-04, 13:00–21:00 +07. Phiên này nhận vé lúc ~18:40 (pull, kiểm code cũ, chạy cổng, live verify, viết báo cáo) và push tiến độ theo từng mốc.
- App thật: `workspace_chat_app` cổng 8501; kho production `C:\AIOS_workspace_chat_rag_v2_production`.

## Kết luận

Ba việc bắt buộc của vé đều có bằng chứng (ảnh local + số đo live + test). Cổng kiểm repo đạt (đúng 2 fail anti-hardcode đã biết từ trước, vé cho phép). Không ghi index production — SHA kho `tri_thuc` không đổi trước/sau. Không kích hoạt nhánh `cho-muse` của cổng watcher vì phiên có tiến triển thật ở từng mốc.

## Việc 1 — Hết xô lệch composer

- Ô nhập full-width một hàng riêng; hàng dưới chỉ còn nút `[+]` đính kèm bên trái và nút `Hỏi` bên phải; dòng mờ `Đang dùng… · Khối tri thức… · Tìm nhanh` tách thành hàng riêng, không chen ngang; thanh tiến trình "Đã chuẩn bị xong…" nằm dưới, cách cụm nút.
- Ảnh live phiên này: `12-composer-1440-live.png`, `16-composer-1100-live.png`; đối chiếu bản sửa tràn trước đó: `03-composer-1100-sua-loi-tran.png`, `03b-crop-1100-sau-fix.png`, `04-composer-1440-sau-fix.png`.
- Số đo live ở cửa sổ 1100px (Chrome headless, app thật): nút gắn `x = 392,2…603,9` nằm trọn trong khung composer `380…1020`; nhãn không tràn (`scrollWidth = clientWidth = 149`); không còn chữ đè chữ.
- Fix đợt này (`12f1744`): nhãn nút gắn tự cắt ellipsis bên trong cột, nới cột nút `[4.0, 4.9, 2.1]`; test mới `test_attach_button_label_is_clipped_inside_its_column`.

## Việc 2 — Công tắc chọn khối tri thức

- Live: mặc định `Khối tri thức: Tự động`; bấm mở đúng 4 lựa chọn **Tự động / LSU / Điều tra lỗi / MOM**, không thêm toolbar/tab (`13-cong-tac-mo-1440-live.png`); chọn LSU → nhãn đổi thành `Khối tri thức: LSU` (`14-composer-lsu-da-chon-live.png`).
- Định tuyến ép khối (gọi thẳng mã thật với config production): LSU → collection `lsu`, `applied=True`, badge "Đang tra cứu khối LSU."; Điều tra lỗi → badge "Đang tra cứu khối Điều tra lỗi."; MOM → badge "Đang tra cứu khối MOM."; ép `tong_hop` → `None` (không thể vào kho tổng hợp); khối thiếu kho → thông báo tiếng Việt nêu tên khối + gợi ý quay về Tự động.
- Test: `test_workspace_chat_knowledge_block.py` (badge đúng khối ép, chế độ Tự động giữ nguyên, khối thiếu kho báo rõ, trạng thái 3 khối đọc từ file kho thật) + `test_index_domain.py`.
- Giới hạn trung thực: phiên live không gửi một câu hỏi thật kèm ép khối (notebook đang có tiến trình chuẩn bị nền 101/106 — không đụng vào để tránh ghi nguồn/worker). Phần "kết quả chỉ từ khối đó" được chứng minh ở tầng định tuyến thật + test, chưa có ảnh câu trả lời thật trong phiên này.

## Việc 3 — Dòng thư viện chung ở sidebar

- Live: dòng `Thư viện chung · 3 khối · luôn bật` gập mặc định; bấm mở ra đủ 3 khối kèm trạng thái "sẵn sàng" (`15-sidebar-thu-vien-live.png`). Trạng thái đọc từ file kho thật (`workspace_chat_domain_block_status`).
- Test: `test_sidebar_shared_library_line_is_collapsed_and_lists_three_blocks`.

## Ràng buộc cứng (không regression)

- One-shot-inline vòng 4 giữ nguyên: các test `test_one_shot_image_is_inline_ocr_text_never_a_persistent_source`, `test_attached_image_is_ocr_first_never_hard_blocked_before_ingest`, `test_image_only_question_passes_the_no_sources_gate` đều pass trong cổng test của vé.
- Code tương thích Python 3.11 (`.venv` 3.11.14).

## Cổng kiểm bắt buộc

- `uv run --no-sync --group dev python -m compileall src tests`: sạch.
- 3 file test vé yêu cầu (`test_workspace_chat_composer_ui.py`, `test_workspace_chat_connector_guard.py`, `test_workspace_chat_ui_i18n.py`): **81 pass**; đúng **2 fail anti-hardcode đã biết từ trước** (vé cho phép, không sửa).
- Test riêng ROUND5 (`composer_ui` + `knowledge_block` + `index_domain`): **93 pass**.
- `aios_habit.cli audit`: `"status": "PASS"`; import `aios_habit.workspace_chat_app`: OK (PYTHONPATH=src).
- Full suite toàn repo (`pytest -q`, chạy lại với temp trên `D:\tmp\pytest-omp`): **3.994 pass / 43 fail / 19 error / 37 skip** — không có lỗi nào thuộc mã composer/công tắc khối của vé; chi tiết nhóm ở mục "Ghi chú full suite" cuối báo cáo.
- Ghi chú môi trường: ổ `C:` chỉ còn ~0,2 GB → lần chạy full đầu tiên lỗi tạo thư mục tạm (234 fail/88 error thuần hạ tầng, không phải lỗi mã); đã trỏ `TMPDIR/TEMP` sang `D:\tmp\pytest-omp` rồi chạy lại.

## Kho tri thức (không đổi)

| Mục | Trước | Sau |
| --- | --- | --- |
| File | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

Chỉ có log worker (`logs\bge_worker.stderr.log`) được ghi trong phiên live — không phải file index.

## Cổng watcher

- Không có dấu hiệu "watcher tự mở OMP 4 lần liên tiếp mà không tiến triển": trong `docs/phieu-viec/mailbox` không có `watcher_state_*`/`watcher_*.log`; `Watch-Mailbox.ps1` đang để `$AUTO_LAUNCH = $false` (chỉ popup nhắc).
- Phiên có tiến triển thật (mốc commit 18:40 → 19:00 → 19:10 → 20:46) → **không** đặt `cho-muse`.

## Ảnh bằng chứng (local — `.gitignore` bỏ qua `*.png`)

- Phiên live 20:25: `12-composer-1440-live.png`, `13-cong-tac-mo-1440-live.png`, `14-composer-lsu-da-chon-live.png`, `15-sidebar-thu-vien-live.png`, `16-composer-1100-live.png`.
- Giữ đối chiếu: `01`–`06`, `08`, `10`, `11` (các phiên trong ngày).
- Thư mục: `docs/phieu-viec/ket-qua/round5-ux-composer-anh/` (không commit theo quy ước repo).

## Ghi chú full suite (43 fail / 19 error — đều ngoài phạm vi vé)

Nhóm theo nguyên nhân đọc trực tiếp từ log (không nhóm nào chạm mã composer / công tắc khối; thay đổi của vé chỉ là CSS + chỉ số cột + 1 test tĩnh):

- **Worker BGE không khởi động được trong môi trường này** (12 fail): `test_bge_subprocess_worker/client`, `test_bge_worker_persist` — `bge_worker_init_stdout_eof` / `bge_worker_persist_unavailable` (app thật cũng gặp `No module named 'aios_habit'` khi spawn worker).
- **Thiếu dữ liệu thật trên đường dẫn WSL** (10 error + 1 fail): `test_error_cases_f4`, `test_chat_action_error_lookup` — `\home\hatch\workspace\aios_data\...` không tồn tại trên máy này.
- **Thiếu gói tuỳ chọn** (9 fail): `test_graphify_adapter` — `graphifyy==0.9.50` chưa cài trong venv (`--no-sync`; ổ `C:` hết chỗ chặn cài thêm).
- **Đóng gói/môi trường venv** (3 fail): `test_commit_d_wheel_and_packaging` — `uv.lock` cần cập nhật + smoke test `No module named 'aios_habit'`; `test_owner_workflow_cli`, `test_rag_v2_dev_cli` cùng dạng gọi CLI thiếu gói.
- **Đúng 2 anti-hardcode đã biết của vé** (2 fail): `test_workspace_chat_ui_i18n` (dòng 1938/1939 `module_root` + `render_chat_bubble`) — vé cho phép bỏ qua.
- **Còn lại lẻ tẻ** (mạng DNS `urlopen`, ngưỡng/ngữ nghĩa retrieval `rag_v2_eval_harness`, lệch kỳ vọng test cũ so với mã hiện tại như `extract_xlsx_text` (có từ commit `767ea66`/`d562bb5`) và nhãn provider cũ theo quyết định chủ 29/9 `941c31c`): không liên quan layout composer.

Chưa có mốc baseline full-suite sạch trên máy này để đối chiếu tuyệt đối (ổ `C:` gần đầy, worker BGE lỗi môi trường); Muse cần baseline có thể yêu cầu chạy đúng 43 test này trên commit trước vé.
