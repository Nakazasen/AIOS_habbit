# Biên bản Bàn giao Dự án (Project Handover)

Cập nhật: 2026-09-12
Nguồn trạng thái chuẩn: [ROADMAP.md](ROADMAP.md) là nguồn trạng thái chuẩn duy nhất cho vòng đời các Gate; tệp này là ảnh chụp nhanh (snapshot) vận hành và không được tự ý chuyển các tuyên bố lịch sử thành tuyên bố phát hành hiện tại.

## Ảnh chụp trạng thái hiện tại (Current Snapshot)

- **Đợt T030–T057:** Đã commit và push tại `1d0749b` trên `gate1-local-case-sqlite`. Kiểm toán lại ngày 2026-09-07 xác nhận local/remote cùng SHA; 29 test US10/Workspace Chat trọng điểm, `compileall`, CLI audit, import, hợp đồng tài liệu và chính sách UI tiếng Việt đều đạt. Không dùng lượt này để tuyên bố full suite 2.559 test hiện tại.
- **Feature 009 — Trợ lý thực thi công việc cho kỹ sư:** `PARTIAL` ngày 2026-09-13. Đã hoàn tất và kiểm chứng độc lập 100% US1 (Báo cáo lỗi xưởng), US2 (Rà soát thiết kế công đoạn), nền an toàn thực thi và chính sách phân quyền đường dẫn (T000–T019). US3 (Sửa mã trong vùng cách ly) tạm hoãn chờ runtime OpenCode thực tế chứng minh đầy đủ deny/event/undo; US4 (Hàng đợi công việc bền vững) đang chuẩn hóa giao diện người dùng qua từ điển dùng chung `t(...)` không phô bày thuật ngữ kỹ thuật và nối trực tiếp luồng enqueue/process thực tế. `antigravity_bridge.py` tiếp tục là nguồn AI cho Workspace Chat và giữ nguyên vẹn.
- **Feature 010 — AI phỏng vấn chuyên gia:** `REOPENED_FOR_SIMPLIFICATION`. T000–T080 và bằng chứng G0–G10 được giữ làm lịch sử, nhưng kiểm toán lại ngày 2026-09-09 không chấp nhận tuyên bố sẵn sàng vận hành: mô hình phân quyền không có hệ tài khoản chung tạo an toàn giả; dữ liệu bản chép lời, fallback mock, trạng thái xuất bản/thu hồi và hành trình UI còn finding. ADR/spec/plan đã chuyển sang nhóm tin cậy, tên ghi nhận trách nhiệm, chọn thư viện cá nhân/dùng chung và luồng bốn chặng. Cần hoàn tất T083–T109 rồi kiểm toán lại.
- **Điểm lưu Goal 010 ngày 2026-09-09:** Mã và tài liệu hiện tại chỉ là trạng thái đang làm, chưa nghiệm thu. Ý chí kiểm toán, bằng chứng đã chạy, phạm vi commit và các điểm chặn để tiếp tục được ghi tại [biên bản kế thừa Goal 010](docs/reports/BIEN_BAN_KE_THUA_AUDIT_GOAL_010_2026-09-09.md).
- **Goal 011 — Vòng trí nhớ công việc thích nghi:** `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT`. Execution T001–T030 và bổ sung UX T030A: Workspace Chat hiện lựa chọn “Cho AIOS ghi nhớ để hỗ trợ tôi tốt hơn”, giữ lựa chọn cục bộ qua lần mở sau và không yêu cầu lệnh PowerShell; khi chưa có lựa chọn thì cờ `adaptive_work_memory` mặc định tắt vẫn là giá trị ban đầu. Hệ thống gọi lại bốn nguồn hiện có; nhớ/quên/sửa sai ghi JSONL append-only ngoài Git; Goal 010 chỉ là nguồn tùy chọn. Ba finding remediation đã sửa: bridge ngoài fail-closed theo fingerprint, lệnh quên từ chối kết quả mơ hồ/khác workspace và block memory không vượt 4.000 ký tự. Thẻ cổng: [AIOS-ADAPTIVE-WORK-MEMORY.md](docs/roadmap/backlog/AIOS-ADAPTIVE-WORK-MEMORY.md). Chưa commit/push; còn kiểm toán độc lập lại và smoke UI thật.

- **Chuẩn bị nguồn tăng dần (005):** `TECHNICAL_PASS`. Playwright smoke 6/6 PASS ngày 2026-09-12 (`scripts/Chay_Smoke_005.bat` / `scripts/smoke_005_incremental_source_prep.py`; artifact `local_runs/smoke_005/result.json`, không commit). Nguồn mới được chuẩn bị riêng; khi BGE-M3 không có deployment hợp lệ, UI phải hiện rõ thư viện chưa sẵn sàng. S4 trên UI thật xác nhận Non-blocking RAG: hỏi được trên tài liệu đã sẵn sàng trong lúc file mới còn ingest, không khóa cả thư viện.

- **Thanh nhập chat hiện đại (007):** `TECHNICAL_PASS`. Playwright smoke 6/6 PASS ngày 2026-09-12 (`scripts/Chay_Smoke_007.bat` / `scripts/smoke_007_modern_chat_composer.py`; artifact `local_runs/smoke_007/result.json`, không commit). Test composer tập trung `107 passed`. Composer compact có ô nhập, nút đính kèm, chọn mô hình (Gemini Web / C-AGENT / Nakazasen), Ctrl+↵ và mũi tên gửi. Gửi rỗng hiện hướng dẫn; gửi khi chưa có nguồn hiện «Thiếu ngữ cảnh» (Streamlit có thể giữ text trong ô). Đính kèm PNG hiện thumbnail + «Bỏ ảnh». Dán clipboard không tự động hóa được vì trình duyệt đòi thao tác người dùng. Không tuyên bố nghiệm thu xưởng.

- **Tổng hợp đa nguồn (002):** vẫn `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE`. Lát chất lượng 2026-09-12 trên BGE-M3 Hybrid: câu nhiều vế được tách facet cục bộ (không cần cloud), truy xuất không cắt 3 nguồn khi đa ý, câu trả lời extractive theo `Ý 1`/`Ý 2`/`Còn thiếu`. Test tập trung lát này đạt. Câu một vế vẫn có thể bị prefilter 3 lúc chuẩn bị. Full pytest 2778 passed / 2 failed ngoài 002. Không ngang NotebookLM. Không đóng cổng. Commit `db42102` đã push.

- **Quản lý cuộc trò chuyện (004):** `TECHNICAL_PASS`. 2026-09-13: `pytest -q -m "not desktop_packaging"` **2774 passed / 0 failed** (182s). Xóa phiên có xác nhận đúng hội thoại, không để màn hình trắng. Test đóng gói desktop tách marker `desktop_packaging` (không thuộc cổng 004). Không tuyên bố nghiệm thu xưởng.

- **Đánh giá chunk (006):** vẫn `IMPLEMENTED_PENDING_REAL_CORPUS_VALIDATION`. E1/E2 đã xong trên corpus công khai; cắt câu CJK chỉ cho ingest mới, không rebuild index Workspace Chat. 2026-09-12: 79 test harness đạt. Không có bộ case đóng băng trên tài liệu chủ sở hữu nên **không** mở E3/E4 và không giả PASS.

- **Sửa lỗi phạm vi câu hỏi chờ (005 follow-up):** Đã gộp vào đóng cổng trên. Retrieval không đọc lại toàn bộ thư viện cho câu hỏi quá rộng; tiến độ chuẩn bị và xóa nguồn đã được smoke trình duyệt xác nhận.

- **Giao diện chính (Primary UI):** Workspace Chat. Các tệp giao diện công khai của Case Cockpit cũ đang được cho dừng (retired), tuy nhiên các dịch vụ dùng chung dựa trên `case_store` vẫn có các luồng gọi trực tiếp và tuyệt đối không được xóa nếu chưa có kế hoạch di chuyển tách biệt.
- **Git:** Nhánh `main...origin/main` hiện có một cây làm việc chưa commit đáng kể, bao gồm RAG, Workspace Chat, Antigravity, tài liệu và các bài kiểm thử. Cần bảo toàn các thay đổi hiện có; phân tách và đánh giá kỹ lưỡng trước khi đưa ra bất kỳ tuyên bố phát hành hoặc chạy benchmark nào.
- **Dữ liệu riêng tư:** `local_cases/`, `local_runs/`, tài liệu nguồn gốc, bộ nhớ đệm mô hình (cache), thông tin xác thực (credentials) và câu trả lời benchmark luôn được Git bỏ qua. Tuyệt đối không đưa chúng vào Git để làm cho báo cáo bàn giao trông có vẻ "đầy đủ".
- **Hồ sơ vụ Workspace Chat (Cổng 1, commit `2bb7a5f`, kiểm toán lại 2026-08-30):** Nền lưu hồ sơ được giữ nguyên: SQLite cục bộ tách kho, transaction case/evidence/audit, từ chối trace không phải `local_only`, không sao chép câu hỏi/câu trả lời/đoạn trích và idempotent theo trace. FR-002/FR-004 được nâng bằng migration có version/backup/rollback và activity append-only có chuỗi digest; FR-016 được khóa bằng thông báo UI tiếng Việt an toàn; FR-018 được kiểm bằng AST trên toàn bộ module Workspace Chat/case được hỗ trợ.
- **Vòng hồ sơ 008, Cổng 1A + US1:** `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE`. Đã có quyền/vai trò theo phạm vi cho người thao tác cục bộ, phiên bản chống ghi đè, danh sách/bộ lọc/chi tiết/dòng thời gian/việc cần bổ sung/giao việc/mở dấu vết và gắn thêm siêu dữ liệu bằng chứng. Lượt kiểm tra tập trung đạt `169 passed` trên lệnh mặc định và `56 passed` trên Python 3.11; lớp chặn thông báo cuối cùng đạt thêm `66 passed`. `compileall`, hợp đồng tài liệu, `git diff --check`, lệnh kiểm toán và lệnh nhập Workspace Chat đều thoát mã 0.
- **Mốc 0 (T001–T005):** `TECHNICAL_PASS`. Khóa đường cơ sở Python 3.11, fault injection atomicity kho Case, bộ quét tiếng Việt 100% không cho phép bộ chọn ngôn ngữ hoặc traceback ngoại vi, ma trận smoke headless Streamlit port 8537 đạt `ok`.
- **Mốc 1 (T006–T010, US2):** `TECHNICAL_PASS` & `OPERATIONAL_PARTIAL`. Thẩm định chuyên gia `ExpertRequest`/`ExpertReview` append-only, kiểm soát quyền theo scope (`expert.request`, `expert.resolve_conflict`), giao diện chi tiết hồ sơ tiếng Việt và kịch bản restart/readback case LSU có citation đạt `RESTART_READBACK_PASS`.
- **Mốc 2 (T011–T017, US7):** `TECHNICAL_PASS` & `OPERATIONAL_PARTIAL`. Gói hợp đồng tự quyết định LSU Iris (`specs/008-evidence-case-loop/contracts/lsu-iris-input.md`), bộ fixture giả lập chuẩn 7 kịch bản (`valid`, `missing_keys`, `conflicting_keys`, `orphan_keys`, `future_leak`, `corrupt`, `time_series`), module đọc/chuẩn hóa/nối trace `production_prediction.lsu_iris`, kho SQLite có migration và chốt chặn `BLOCKED_DATA`, màn hình kiểm tra dữ liệu LSU và tra cứu chuỗi Unit tiếng Việt trong Workspace Chat. Rehearsal trọn vẹn tệp -> SQLite -> màn hình đạt `REHEARSAL_RESTART_READBACK_PASS`. Dữ liệu thật chờ gắn kết nguồn cục bộ `KHO_LSU_CUC_BO` để chuyển `OPERATIONAL_PASS`.
- **Mốc 3 (T018–T022, US8):** `TECHNICAL_PASS` & `LEARNING_SHADOW` (`OPERATIONAL_PARTIAL`). Giao thức phát lại lịch sử khóa `as_of_time`, chống rò rỉ tương lai 100%, so sánh phương án nền `no_alert` với `EWMA` (3 std), nhánh mô hình học máy được khóa an toàn (`not_applicable`). Báo cáo so sánh tiếng Việt tất định theo digest. Tự động chấm kết luận `LEARNING_SHADOW` theo hợp đồng `lsu-acceptance-rubric.md` để mở chạy bóng chỉ đọc thu thập outcome.
- **Mốc 4 (T023–T027, US9):** `TECHNICAL_PASS` & `OPERATIONAL_PARTIAL`. Trình chạy bóng thủ công (`ManualShadowRunner`) theo lô nhỏ an toàn CPU laptop, tiến độ thời gian thực, nút dừng an toàn; đánh giá nguy cơ gắn `idempotency_key` bất biến từ digest, liên kết tự động sang Workspace Case SQLite cục bộ với reference `local_only` chống trùng lặp; ghi nhận kết quả thực tế (outcome) đa chiều (kể cả Unit NG bị bỏ sót không có cảnh báo trước đó); giao diện người dùng tiếng Việt 4 Tab không lộ bộ chọn model máy học hay nút gửi cảnh báo ngoại vi. Rehearsal trọn vẹn tệp -> tiến độ -> nguy cơ -> case -> outcome -> chống trùng đạt `REHEARSAL_MILESTONE_4_PASS`. Đang chờ dữ liệu lô sản xuất thực tế tại xưởng để nghiệm thu `OPERATIONAL_PASS`.
- **Giới hạn định danh Cổng 1A:** runtime hiện chỉ được duyệt cho một người dùng cục bộ, với `local_admin` do ứng dụng cấp và quyền cụ thể theo phạm vi. Mã người thao tác không được lấy từ biểu mẫu hoặc nội dung AI. Phải giữ chế độ nhiều người dùng ở trạng thái từ chối cho đến khi có ánh xạ tài khoản/hệ điều hành và kiểm thử chống mượn danh.
- **Cấu hình kiểm thử:** `pytest` hiện nằm trong nhóm phụ thuộc `dev` và đã ghi nhận trong lockfile. Lệnh `uv lock --check` đã vượt qua. Môi trường `.venv` hiện tại gặp lỗi từ chối quyền truy cập (access denied) của Windows đối với metadata cũ của `aios_habit` khi chạy `uv sync`; không tự ý xóa hoặc thay đổi quyền sở hữu môi trường đó mà chưa có sự chấp thuận của chủ sở hữu.
- **Chọn biểu đồ khi nhập tệp CSV LSU (015):** `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT` ngày 2026-09-18. Ô chọn gọn ở Thẻ 1 (mã JIG, chỉ số ưu tiên nhóm độ lệch/độ nghiêng 4 màu, 1 trong 3 loại xu hướng/phân bố/so sánh theo màu, ảnh PNG 300 DPI/SVG) và lệnh chat tự nhiên trên Omnibar dùng chung hàm dựng `chart_selection.py`; ảnh dùng chung cho xem trước, tải về và email cảnh báo; tệp đo sâu không tiêu đề được tự nhận diện linh hoạt. Kiểm thử mới `21 passed` (`test_csv_chart_selector.py` 17 + `test_csv_chart_selector_ui.py` 4, cùng 32 passed với `test_spc_chart.py`/`test_jig_chat_wire.py`). `compileall`, CLI audit (`PASS`), `import workspace_chat_app`, quét tiếng Việt và `check_docs.py` đều đạt. Full suite còn fail có sẵn ngoài phạm vi (7 fail đã chứng minh trên cây gốc bằng stash gồm nhóm báo lỗi xưởng và đóng gói, 3 fail flaky do tải gồm desktop e2e/smoke/OCR đều đạt khi chạy lẻ). Nghiên cứu chỉ ở mức manifest thư mục `D:\Sandbox\Iris LSU`, không đưa dòng dữ liệu thô vào Git. Chưa commit/push; còn kiểm toán độc lập và smoke trình duyệt Thẻ 1.

## Bằng chứng đã xác minh ngày 2026-08-16 (Verified Evidence)

| Hạng mục | Bằng chứng hiện tại | Phạm vi ranh giới |
| --- | --- | --- |
| Lưu trữ JSONL cục bộ | 33 bài kiểm thử trọng điểm ĐẠT; bao gồm ghi nguyên tử (atomic write), khôi phục (rollback) và ghi log an toàn dòng lỗi | Chưa phải kết quả toàn bộ suite |
| Workspace Chat / Giao diện bàn giao | 59 bài kiểm thử trọng điểm ĐẠT | Chưa phải smoke test trên trình duyệt hoặc trực tiếp với provider |
| Cầu nối Antigravity, bàn giao & RAG đa nguồn | 43 bài kiểm thử trọng điểm ĐẠT | Chưa kiểm chứng trực tiếp sidecar/provider thực tế |
| Adaptive Reranking UX (Feature 003) | 154 bài kiểm thử trọng điểm ĐẠT, 1.175 test toàn bộ ĐẠT, schema v3 và circuit breaker hoàn tất | `IMPLEMENTED_PENDING_REAL_BENCHMARK`; canary/production activation `BLOCKED` cho đến khi chạy benchmark thật trên model/corpus |

| Thu thập kiểm thử repository | `pytest --collect-only -q`: đã thu thập 1,143 bài kiểm thử | Thu thập không tương đương với chạy kiểm thử thành công |

| Vệ sinh mã nguồn | `compileall`, `uv lock --check`, và `git diff --check` ĐẠT | Cây làm việc vẫn ở trạng thái chưa commit |

Các Gate Card đã hoàn thành hiện có trong cây làm việc là tài liệu ghi nhận kết quả triển khai. Chúng được đánh dấu là đang chờ xác minh toàn bộ test suite cho đến khi toàn bộ quality gate bắt buộc được chạy thành công trên diff cuối cùng.

## Quy trình Tiếp tục An toàn (Safe Continuation)

1. Kiểm tra cây làm việc hiện có trước khi đưa ra bất kỳ quyết định benchmark, dọn dẹp hoặc commit nào:

   ```powershell
   git status --short --branch
   git diff --check
   git diff --cached --check
   ```

2. Trên một môi trường ổn định, cài đặt và chạy chuỗi công cụ phát triển có thể tái lập:

   ```powershell
   uv sync --group dev
   uv run --no-sync --group dev python scripts/check_docs.py
   uv run --no-sync --group dev python -m compileall src tests
   uv run --no-sync --group dev pytest -q
   uv run --no-sync --group dev python -m aios_habit.cli audit
   ```

3. Tuyệt đối không coi một bộ kiểm thử trọng điểm vượt qua hoặc số lượng test thu thập được là sự cho phép để đánh dấu Gate Card thành `DONE`, công bố báo cáo 12 câu hỏi, hoặc chạy benchmark provider trực tiếp. Phải ghi lại chính xác câu lệnh, mã thoát (exit code) và phạm vi kiểm thử.

4. Đối với luồng benchmark RAG, phải bảo toàn định danh/checkpoint đóng băng. Chẩn đoán cục bộ chưa đóng dấu chỉ được giới hạn ở preflight không dùng provider, Stage A hoặc chạy thử nghiệm (dry-run) với đúng `BQ01,BQ02`; bắt buộc phải từ chối `--run`.

5. Trước khi commit, cần tách biệt mã sản phẩm/tài liệu khỏi các tùy biến cục bộ và dữ liệu runtime bị bỏ qua. Chỉ cập nhật roadmap, changelog và biên bản bàn giao này dựa trên bằng chứng từ diff cuối cùng.

## Rủi ro Vận hành Cần Chuyển giao Tiếp theo (Operational Risks)

- Các dòng JSONL không hợp lệ hiện chỉ được hiển thị trong log cục bộ theo tên tệp/số dòng. Giữ lại tệp cục bộ gốc để phục hồi; tuyệt đối không sao chép nội dung bản ghi vào issue hoặc kênh chat.
- Lệnh `uv sync --group dev` có thể thất bại trên môi trường Windows `.venv` hiện tại do thư mục metadata cũ bị khóa quyền. Hãy dừng lại, xác định các tiến trình đang chạy và xin phê duyệt trước khi tạo lại môi trường.
- Toàn bộ bộ kiểm thử chưa được chạy lại đầy đủ trong đợt bàn giao này. Số lượng kiểm thử dự kiến thu thập là 1,143, nhưng chỉ lượt chạy hoàn chỉnh với mã thoát 0 mới được tính là ĐẠT.
- Tài liệu này không ngụ ý bất kỳ trạng thái worker benchmark/BGE nào đang hoạt động; hãy kiểm tra danh sách tiến trình và các artifact runtime bị bỏ qua ngay trước khi khởi chạy lại.

## Bổ sung ngày 2026-09-19 (chưa commit lúc ghi)

- **006 E5 Lite-CPU**: profiler chọn kiểu chia, cha-con chỉ tài liệu dài, cấu hình theo lần tải, sửa mảnh có hoàn tác, cờ thí điểm, chống trùng và giữ mảnh chi tiết. `T032-T036` xong có kiểm thử, `T037` ca BGE đêm còn mở.
- **004 kho chung**: đăng ký preset, mỗi kho một thư viện riêng, nút tạo thư viện, hộp thư theo kho, thấy và đổi thư viện trong sổ, sửa lỗi nút quay về. Kiểm thử liên quan đạt.
- **007 gợi ý**: gợi ý mở đầu và tiếp theo bám mạch kèm tên đầy đủ khi gửi, bộ đo 8 mạch 24 câu đạt, đo trả lời thật trúng nguồn 20/24.
- **010 phỏng vấn**: nút vào thẳng chặng phỏng vấn, màn phỏng vấn ba ngôn ngữ thí điểm, giọng nói tạm ẩn, đề xuất đa ngôn ngữ đã duyệt thí điểm.
- **011 trí nhớ**: Sổ bài học xem phân trang, quên từng bài, thước dung lượng và huy hiệu lâu chưa dùng.
- Toàn bộ mới chỉ qua kiểm thử tập trung, kiểm toán lệnh và quét tiếng Việt. Chưa chạy đủ bộ, chưa smoke trình duyệt, chưa kiểm toán độc lập.

## Bổ sung ngày 2026-09-23 (chưa commit lúc ghi)

- **007 smoke trình duyệt đã có thật**: `scripts/smoke_007_modern_chat_composer.py` được mở rộng từ 6 lên **12 kịch bản** và chạy đạt **12/12 PASS** (`local_runs/smoke_007_t037/result.json`, không commit). Sáu kịch bản mới (S7–S11b) kiểm bằng DOM và kiểu tính toán những hợp đồng trước đây chỉ có assert đọc mã nguồn: mặt sáng ba vùng, tên điều hướng tiếng Việt, bong bóng hỏi đáp, bề rộng dòng đáp, canvas đồ thị bằng chứng và trạng thái chờ. Đây là mảnh còn thiếu của T037 (spec 007) — trước đó T037 tự ghi "chưa smoke trình duyệt".
- **Ràng buộc mới phát hiện, cần biết khi chạy smoke**: vòng có trích dẫn và đồ thị **cần một nhà cung cấp câu trả lời**. Trên máy này cầu nối Antigravity `127.0.0.1:8585` không chạy; `cagent_api` cần mạng ra endpoint công ty; `nakazasen_router` cần mạng và nguồn phải được xếp `cloud_safe` (mặc định `machine_only` bị chặn). Nhánh cuối fail-closed: `"Cầu nối Antigravity IDE hiện không khả dụng. Hãy bấm Kết nối lại Gemini Web, rồi gửi lại câu hỏi."` Không có đường trích dẫn nào chạy hoàn toàn cục bộ: `rag_v2/synthesis.py` có bộ tổng hợp trích dẫn cục bộ và sinh chữ `[N]`, nhưng kết quả bị vứt đi (chỉ nằm ở `result["local_synthesis"]["answer"]`, không nơi nào trong Workspace Chat đọc). Vì vậy smoke gieo sẵn dữ liệu hội thoại và dấu vết hợp lệ để kiểm canvas một cách tất định.
- **Hình học canvas đồ thị**: đo ở 1400/1024/820/560/360 px cho canvas rộng 950/574/370/240/240 px, không rail nào phủ lên canvas, không tràn ngang — xác nhận bản sửa `83a62c6` giữ đúng thứ nó tuyên bố.
- **Xác minh đã chạy trong lượt này**: `test_workspace_chat_composer_ui` + `test_workspace_chat_source_selection_owner_flow` + `test_workspace_chat_multi_file_uploader` + `test_workspace_chat_ui_i18n` + `test_flowsint_evidence_atlas` + `test_streamlit_error_safety_config` **135 passed** (21,73 s); `compileall` sạch; `cli audit` `"status": "PASS"`; `import workspace_chat_app` in `IMPORT_OK`.
- **Chưa chạy toàn bộ bộ kiểm thử** trong lượt này. Ghi nhận cũ vẫn đúng: `pytest -q` đầy đủ còn nhóm lỗi có sẵn ngoài phạm vi hình thức.

## Bổ sung ngày 2026-09-23 (tiếp) — Dự phòng tổng hợp cục bộ có trích dẫn (M6)

- **Vấn đề đã bịt**: `rag_v2/synthesis.py` vốn đã tính một đáp án trích xuất cùng nhãn `[N]` trong mỗi lượt truy xuất (`pipeline.py:941-943` luôn chạy vì adapter ghim `enable_provider_synthesis: False`), nhưng kết quả bị vứt đi — chỉ nằm ở `result["local_synthesis"]`, và grep toàn kho xác nhận **không** UI nào đọc. Khi cầu nối chết, người dùng không còn đường trả lời có trích dẫn nào.
- **Đã làm**: thêm đường thứ tư, cục bộ và không nhà cung cấp. `route_workspace_chat_submission` nhận thêm tham số tuỳ chọn `local_synthesis` (mặc định `None`, chữ ký trả về giữ nguyên bốn phần tử nên hơn ba mươi lời gọi hiện có không phải sửa). Khi cả ba đường nhà cung cấp không tới được, hàm trả cùng chuỗi lỗi cũ kèm cờ mời `local_fallback_offered`; **không ghi tin nhắn nào**. Người dùng bấm nút thì `commit_local_grounded_answer` ghi cặp tin nhắn và dựng dấu vết bằng đúng bộ ba của các đường khác.
- **Vì sao không cần cơ chế trích dẫn mới**: nhãn trích dẫn khớp sẵn qua chuỗi `evidence.py:653` (`f"[{rank}]"`) → `bge_subprocess_worker.py:71` → `workspace_chat_rag_v2_adapter.py:2184` → `evidence_trace.py:195-228`. Đã chứng minh bằng probe: dấu vết `status="valid"`, đồ thị dựng được.
- **Phát hiện cần nhớ**: bộ tổng hợp chỉ trích dẫn đoạn nó thật sự dùng làm căn cứ, không trích dẫn mọi đoạn đã truy xuất (đo được: 2 đoạn truy xuất, đáp án chỉ mang `[1]`). Nên `source_count` của huy hiệu tính theo số trích dẫn thật, và điều kiện từ chối chỉ là đáp án rỗng hoặc không có trích dẫn nào.
- **Bảo vệ đã có**: đáp án cục bộ mang nhãn `Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình`, không gắn tên mô hình hay nhà cung cấp; suốt nhánh dự phòng **0 lời gọi mạng** (có kiểm thử tripwire cho `call_cagent_prediction`, `call_antigravity_bridge`, `generate_workspace_ai_answer`).
- **Xác minh đã chạy**: `pytest` sáu tệp liên quan **177 passed, 0 failed** (34,32 s); probe end-to-end `all_pass=true` (offer không ghi gì → commit ghi đúng 2 tin nhắn → dấu vết `valid` → `4 nút · 3 liên kết`); `compileall` sạch; `cli audit` `"status": "PASS"`; `import workspace_chat_app` `IMPORT_OK`; kiểm tra tương đương bản dịch 4/4 khoá cho cả `vi`, `ja`, `zh-CN`; smoke 007 **12/12 PASS** (không hồi quy).
- **Kiểm toán độc lập đã chạy và tìm ra 4 lỗi thật, đã sửa hết**: lượt đầu kiểm toán viên độc lập (vai khác, phiên riêng) kết luận `SC-011`/`SC-012` VERIFIED nhưng **`SC-009`/`SC-010`/`SC-013` FAILED**. Bốn lỗi: (1) lời mời bị ghi thành tin nhắn nên lượt ghi sau tạo cặp hỏi đáp thứ hai; (2) đáp án cục bộ đội header AI (`AI đã trả lời`, `Tên mô hình chưa được xác minh`) thay vì nhãn `chưa qua mô hình`; (3) lỗi lưu dấu vết để lại tin nhắn người dùng mồ côi; (4) dấu vết `insufficient_evidence` vẫn được lưu như thành công. Đã sửa cả bốn, kèm **6 kiểm thử chống tái phát**. Chi tiết và bằng chứng: `specs/antigravity-truthful-bridge/tasks.md` T056.
- **Còn lại**: chưa có lượt kiểm toán độc lập thứ hai xác nhận các sửa đổi trên chính thức đóng `SC-009..SC-013`; trạng thái ghi `M6_AUDITED_AND_FIXED`, không tuyên bố `VERIFIED` cho US7.
- **Chưa chạy toàn bộ `pytest -q`** trong lượt này.
