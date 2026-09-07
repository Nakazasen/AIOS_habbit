# Lệnh thực thi T001–T029 bằng Antigravity

Tệp này là prompt hoàn chỉnh để sao chép vào Antigravity Desktop sau khi commit kế hoạch hiện tại đã sạch. Nó không thay `spec.md`, `plan.md` hoặc `tasks.md`.

## Điều kiện trước khi dán lệnh

1. Nhánh hiện tại là `gate1-local-case-sqlite`.
2. Toàn bộ thay đổi kế hoạch đã được commit; `git status --short` không còn file ngoài `.brain/` đã bị bỏ qua.
3. Không chạy một phiên `/goal` khác trên cùng worktree.
4. Dữ liệu nhà máy thật không mở trong phiên Gemini.

## Prompt sao chép nguyên khối

```text
/goal

MỤC TIÊU

Trong D:\Sandbox\AIOS_habbit, thực hiện trọn T001–T029 của specs/008-evidence-case-loop/tasks.md trong một goal, liên tục theo thứ tự phụ thuộc, vừa làm vừa ghi checklist và biên nhận. Sau T028, chuyển sang một tác tử kiểm toán độc lập thực hiện T029; lỗi được trả lại tác tử thực thi tự sửa tối đa hai vòng rồi kiểm toán lại. Kết thúc khi đạt TECHNICAL_COMPLETE hoặc đã ghi blocker không thể xử lý an toàn.

TÀI LIỆU PHẢI ĐỌC TRƯỚC KHI LÀM

1. AGENTS.md
2. CONSTITUTION.md
3. AGENT_RULES.md
4. specs/008-evidence-case-loop/spec.md
5. specs/008-evidence-case-loop/plan.md
6. specs/008-evidence-case-loop/tasks.md
7. specs/008-evidence-case-loop/data-model.md
8. specs/008-evidence-case-loop/contracts/workspace-evidence-loop.md
9. specs/008-evidence-case-loop/quickstart.md
10. specs/008-evidence-case-loop/owner-decisions.example.yaml
11. specs/008-evidence-case-loop/contracts/lsu-iris-input.md
12. specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md

RANH GIỚI KHÔNG ĐƯỢC VI PHẠM

- Chỉ làm US1, US2, US7, US8 và US9 theo T001–T029. Không tự mở US3, US4, US5, US6, US10, US11, Drum/DLP, NAS, scheduler, PLC, ERP/JIG connector, AutoML, deep learning hoặc dashboard quản trị.
- Không mở, đọc, tóm tắt, tải lên hoặc đưa vào ngữ cảnh model bất kỳ file thật nào trong Tài liệu của tất cả dòng máy/, local_cases/, local_runs/ của phiên khác, .env, ảnh thật, DB thật, log thật hoặc dữ liệu local_only.
- Chỉ dùng code, tài liệu sản phẩm, tests/fixtures/ và manifest đã được làm sạch. Không dùng fixture để tuyên bố pilot hoặc độ chính xác thật.
- Không xóa hoặc ghi đè dữ liệu nguồn. Không chạy git reset --hard, git checkout --, git clean hoặc lệnh xóa đệ quy.
- Không dùng git add -A. Không stage .brain/, local_cases/, local_runs/, dữ liệu thật, screenshot hoặc file bí mật.
- Không commit, push, merge hoặc đổi nhánh. Việc commit chỉ thực hiện sau kiểm toán khi chủ sở hữu yêu cầu riêng.
- Toàn bộ giao diện, launcher, tiến độ, cảnh báo, lỗi, nhật ký vận hành và báo cáo người dùng thấy phải là tiếng Việt dễ hiểu. Không lộ traceback, đường dẫn máy, tên engine/model hoặc câu lỗi tiếng Anh.
- Được tự xác nhận cổng kỹ thuật, Data Gate, nhãn OK/NG có nguồn máy hợp lệ và chạy bóng đọc-only theo rubric có version. Không được tự tạo/nâng quyền người dùng, sửa nhãn mâu thuẫn bằng suy đoán hoặc phát lệnh tác động máy/line.

PHÂN VAI VÀ CHỐNG XUNG ĐỘT

- Dùng một tác tử điều phối, tối đa hai tác tử thực thi và một tác tử kiểm toán độc lập.
- Không spawn một tác tử cho mỗi task.
- Chỉ tác tử điều phối được ghi state.json, CHECKLIST.md, execution_log.jsonl, PROJECT_HANDOVER.md và chạy lệnh Git.
- Mỗi tác tử thực thi chỉ ghi receipts/Txxx.json của task mình và sửa các file được điều phối cấp. Không cho hai tác tử sửa cùng file đồng thời.
- Chỉ chạy một tác vụ nặng tại một thời điểm: toàn bộ pytest, đọc file lớn, lập chỉ mục hoặc đánh giá.
- Tác tử kiểm toán thực hiện T029 không được là tác tử vừa sửa nhóm file đang chấm. Nó được tự kết luận bằng lệnh thật và rubric, không tin báo cáo tự khai của tác tử thực thi.

KHỞI TẠO NHẬT KÝ

Tạo một mã run theo UTC và thư mục:

local_runs/evidence_case_loop_goal/<run_id>/

Chỉ tạo đúng các mục cần thiết:

- state.json
- CHECKLIST.md
- execution_log.jsonl
- RISK_REGISTER.md
- receipts/
- WORK_HANDOFF.md
- CONTINUE_PROMPT.md
- AUDIT_REPORT.md
- runtime/

state.json phải có: run_id, branch, input_commit, python_version, current_task, completed_tasks, blocked_tasks, open_risk_count, highest_open_risk, operational_status_by_milestone, updated_at.

CHECKLIST.md phải chứa đúng T001–T029. Mỗi dòng có: mã task, trạng thái, phụ thuộc, tiêu chí đạt ngắn gọn, đường dẫn receipt, mã rủi ro liên quan và bước tiếp theo. Trạng thái chỉ gồm chưa làm/đang làm/đạt kỹ thuật/một phần/bị chặn/thất bại. T029 chỉ được đổi trạng thái bởi tác tử kiểm toán độc lập.

Mỗi dòng execution_log.jsonl phải là JSON hợp lệ và có: thời gian UTC, task_id, vai trò tác tử, loại sự kiện, lệnh hoặc thao tác đã làm sạch, mã thoát, receipt liên quan và mã rủi ro nếu có. Không ghi dữ liệu thô, secret hoặc đường dẫn nguồn thật.

Mỗi receipts/Txxx.json phải có:

- task_id và trạng thái;
- vai trò thực hiện;
- thời gian bắt đầu/kết thúc;
- commit đầu vào;
- file được giao và file đã sửa;
- lệnh đã chạy cùng mã thoát;
- tên test và số đạt/trượt;
- kiểm tra dữ liệu riêng tư;
- kiểm tra tiếng Việt nếu có bề mặt người dùng;
- blocker và hành động tiếp theo.

Chỉ tác tử điều phối tổng hợp receipt vào checklist. Không cho nhiều tác tử cùng nối thêm vào một file nhật ký.

RISK_REGISTER.md là một bảng duy nhất, không tạo hệ thống quản trị rủi ro mới. Mỗi rủi ro có: mã, task phát hiện, nhóm dữ liệu/bảo mật/tính đúng đắn/hiệu năng/giao diện/migration/đóng gói, khả năng xảy ra thấp-vừa-cao, ảnh hưởng thấp-vừa-cao, bằng chứng, biện pháp xử lý, người hoặc tác tử chịu trách nhiệm, trạng thái mở/đã giảm/đã đóng và rủi ro còn lại. Rủi ro cao về mất dữ liệu, rò dữ liệu, migration không phục hồi hoặc tác động máy phải dừng; rủi ro khác chỉ chặn đúng nhánh phụ thuộc.

T001 — TIỀN KIỂM BẮT BUỘC

1. Xác nhận nhánh gate1-local-case-sqlite và ghi HEAD/upstream.
2. Chạy git status --short. Nếu còn thay đổi ngoài runtime bị bỏ qua, dừng trước khi viết code, ghi WORK_HANDOFF.md và báo chủ sở hữu cần tạo commit kế hoạch sạch.
3. Xác nhận interpreter là Python 3.11. Không dùng py -3 vì máy có thể chọn Python 3.13.
4. Ưu tiên môi trường uv hiện có nếu hoạt động. Nếu .venv bị khóa hoặc sai phiên bản, tạo môi trường mới tại local_runs/evidence_case_loop_goal/<run_id>/.venv bằng UV_PROJECT_ENVIRONMENT; không xóa hoặc sửa quyền .venv cũ.
5. Chạy các lệnh đường cơ sở trong tasks.md/quickstart.md và ghi mã thoát thật.
6. Import và smoke ứng dụng với runtime/ là thư mục hiện hành để Path.cwd()/local_cases nằm trong phiên thử nghiệm, không chạm dữ liệu người dùng.
7. Trước và sau toàn bộ pytest, so sánh git status để phát hiện test làm bẩn file tracked.

THỨ TỰ THỰC HIỆN

- Đợt 0: T001.
- Đợt 1: T002 và T003 chỉ song song khi danh sách file không giao nhau; sau đó T004 rồi T005.
- Đợt 2: T006 → T007 → T008 → T009 → T010.
- Đợt 3: T011 → T012 → T013 → T014 → T015 → T016 → T017.
- Đợt 4: T018 → T019 → T020 → T021 → T022.
- Đợt 5: T023 → T024 → T025 → T026 → T027.
- Đợt 6: T028 → đóng băng danh sách file → tác tử kiểm toán độc lập thực hiện T029 → tác tử thực thi sửa nếu cần → kiểm toán lại.

QUY TẮC CHO DỮ LIỆU VÀ MODEL

- T011 dùng `contracts/lsu-iris-input.md` và `contracts/lsu-acceptance-rubric.md`. Chỉ tiến trình cục bộ được đọc file LSU thật; tác tử chỉ được xem manifest/số tổng hợp đã làm sạch và kết luận từng quy tắc, không xem dòng dữ liệu, đường dẫn, serial hoặc giá trị đo.
- Nếu bí danh nguồn cục bộ chưa được cấu hình, không dò toàn ổ đĩa và không hỏi lại giữa goal; hoàn tất mọi cổng bằng fixture, ghi đúng `OPERATIONAL_PARTIAL` rồi tiếp tục đến T029.
- Cổng kỹ thuật Mốc 2–4 phải đi hết bằng fixture dù cổng vận hành thiếu dữ liệu.
- Phát lại phải dùng đúng protocol đã khóa: metric, chiều rủi ro, tham số EWMA, cửa sổ nền, as_of_time, khoảng dự báo, quy tắc ghép outcome, feature allowlist và phép chia thời gian/Unit.
- Dùng mặc định có version trong hợp đồng cho metric, feature, threshold, khoảng dự báo và EWMA. Không quét nhiều công thức để chọn kết quả đẹp; cấu hình cục bộ chỉ được ghi đè bằng phiên bản mới có lý do.
- T020: nếu Data Gate thật/công thức cỡ mẫu trong rubric chưa đạt, hoàn thiện đường not_applicable và baseline; không thêm dependency máy học. Nếu tự đạt điều kiện mới thêm đúng một hồi quy logistic nhẹ.
- File đầu vào shadow không được chứa outcome/retest tương lai trong feature. Outcome được ghi ở bước phản hồi riêng.
- Khóa chống trùng dùng digest lô dữ liệu và cửa sổ đánh giá, không dùng thời điểm đồng hồ lúc chạy.

GIỚI HẠN LAPTOP

- CSV tối đa mặc định 100 MB/file; XLSX 25 MB/file; 200.000 dòng/sheet; lô 10.000 dòng.
- Đặt OMP_NUM_THREADS=1, MKL_NUM_THREADS=1 và OPENBLAS_NUM_THREADS=1 khi chạy phần tính toán dự đoán.
- Không chạy đồng thời full pytest, Streamlit và tác vụ lập chỉ mục nặng.
- Vượt giới hạn phải trả thông báo tiếng Việt hướng dẫn chia file; không cố nạp toàn bộ vào RAM.

SAU MỖI TASK

1. Chạy test tập trung của task và git diff --check.
2. Tạo receipt riêng.
3. Điều phối kiểm tra receipt, diff, file ngoài phạm vi và cập nhật RISK_REGISTER.md trước khi đổi checklist.
4. Nếu đạt code/test fixture, ghi TECHNICAL_PASS.
5. Nếu thiếu dữ liệu, ghi trạng thái do rubric trả về nhưng tiếp tục task kỹ thuật độc lập. Không dừng chỉ vì thiếu một bước duyệt thủ công cho hoạt động đọc-only.
6. Cập nhật state.json và CONTINUE_PROMPT.md để phiên khác có thể tiếp tục từ task kế tiếp mà không chạy lại từ đầu.

XỬ LÝ LỖI

- Lỗi kỹ thuật do thay đổi mới: tác tử kiểm toán tạo phiếu lỗi, tác tử thực thi sửa và chạy lại test liên quan tối đa hai vòng cho cùng nguyên nhân.
- Lỗi công cụ/môi trường: chẩn đoán rồi tự sửa trong phạm vi repo hoặc thử lại tối đa hai lần. Không tự xóa môi trường hoặc đổi quyền hệ thống.
- Lỗi phụ thuộc quyền máy, dữ liệu thật hoặc dịch vụ ngoài repo: ghi BLOCKED với lệnh tái hiện và tiếp tục nhánh độc lập.
- Sau hai vòng chưa sửa được cùng một nguyên nhân, đánh dấu đúng task bị chặn, ghi CONTINUE_PROMPT.md và tiếp tục mọi task không phụ thuộc. Chỉ tổng hợp blocker ở cuối goal, không dừng toàn bộ giữa chừng.
- Nếu có nguy cơ mất/rò dữ liệu, migration không thể phục hồi hoặc diff ngoài phạm vi: dừng ngay, ghi WORK_HANDOFF.md và không tiếp tục ghi.
- Không xóa test, hạ assertion, tắt bộ quét hoặc đổi PASS giả để đi tiếp.

ĐIỀU KIỆN KẾT THÚC GOAL

Sau T028, chạy bằng Python 3.11:

uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python scripts/check_docs.py
git diff --check
git diff --cached --check

Chạy import Workspace Chat trong runtime thử nghiệm theo quickstart.md. Chạy scripts/check_user_facing_vietnamese.py và smoke trình duyệt trên fixture. Ghi nguyên lệnh, mã thoát, số test và phần chưa kiểm chứng; không chỉ ghi chữ PASS.

Sau các lệnh trên, tác tử kiểm toán thực hiện T029 theo rubric. Nếu mọi phần kỹ thuật đạt, state.json dùng trạng thái TECHNICAL_COMPLETE. Nếu còn lỗi sau hai vòng sửa hoặc cần quyền ngoài repo, dùng HANDOFF_WITH_BLOCKERS. Chạy bóng đọc-only được tự xác nhận; không dùng kết quả này để tuyên bố quyền điều khiển máy.

BÀN GIAO CUỐI GOAL

WORK_HANDOFF.md và AUDIT_REPORT.md phải có:

- nhánh, input commit và git status cuối;
- T001–T029 task nào đạt kỹ thuật, một phần, bị chặn hoặc thất bại;
- trạng thái vận hành riêng của Mốc 0–4;
- file đã sửa theo từng task;
- migration và cách rollback;
- toàn bộ lệnh kiểm chứng cùng mã thoát/số test;
- lỗi còn lại và lệnh tái hiện;
- kiểm tra không có dữ liệu thật/.brain/local_runs trong staged diff;
- kiểm tra tiếng Việt, lỗi ngoài và tên model/engine;
- rubric/digest đã dùng cho T011, T022 và T029;
- bảng rủi ro đã đóng, rủi ro còn lại, bằng chứng và ảnh hưởng thực tế;
- việc ngoài đọc-only còn cần chủ sở hữu quyết định.

Khi đã ghi đủ bàn giao và T029 đã được tác tử kiểm toán độc lập kết luận, dừng. Không commit, push hoặc merge.
```

## Kết quả đúng của lệnh

Lệnh đạt mục tiêu khi Gemini đi hết T001–T029 trong một goal, tự chấm đúng rubric, tự sửa lỗi kỹ thuật tối đa hai vòng, không dừng toàn bộ chỉ vì thiếu dữ liệu vận hành và tạo đủ nhật ký để người dùng kiểm tra lại toàn bộ hành trình.
