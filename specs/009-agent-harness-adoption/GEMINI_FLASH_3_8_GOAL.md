# Goal cho Gemini Flash 3.8: Trợ lý thực thi công việc cho kỹ sư

Nguồn thực thi: [spec.md](spec.md), [plan.md](plan.md), [tasks.md](tasks.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md), [research.md](research.md) và thư mục [contracts/](contracts/).

## Prompt khởi chạy để dán vào Gemini

```text
Tiếp tục Goal `009-agent-harness-adoption` trong repo `D:\Sandbox\AIOS_habbit` với vai trò Execution Specialist, Gemini Flash 3.8, suy luận cao.

Đọc `AGENTS.md`, `CONSTITUTION.md`, `AGENT_RULES.md` rồi toàn bộ `specs/009-agent-harness-adoption/`, bắt buộc gồm `GEMINI_FLASH_3_8_GOAL.md`, `tasks.md`, `contracts/agent-factory-error-report-v1.md`, `contracts/agent-process-design-review-v1.md`, `contracts/agent-runtime-protocol.md` và `contracts/agent-error-report-v1.md`. Kiểm tra Git; không reset, không đụng diff người dùng. Bắt đầu từ task `[ ]` ID nhỏ nhất (T000 nếu còn). Làm tuần tự G1→G6. Sau mỗi task: test thật, ghi evidence, đánh `[x]` chỉ khi lệnh đã chạy.

Hai schema «báo cáo lỗi» khác nhau:
- `agent-factory-error-report-v1.md` = US1 báo cáo lỗi xưởng (log/Excel).
- `agent-error-report-v1.md` = khi chính Agent gãy. Không trộn.

UX khóa: người không chuyên không duyệt từng lệnh, từng diff, từng finding. Báo cáo lỗi xưởng là file dùng được: tự lưu, hiện «Đã xong». Rà soát công đoạn tự lưu kết quả, không ghi đè SOP/JIG gốc. «Hoàn tác» luôn có. «Cần bạn bổ sung» chỉ khi thiếu nguồn hoặc file không đọc được. Sửa mã xong trong worktree là đã xong việc; «Đưa vào thư mục đang làm» là tùy chọn. Cấm: secret, ra ngoài root, admin, commit, push, merge, deploy, ghi đè SOP/JIG/tiêu chuẩn gốc. Không dự đoán lỗi line. Không watcher 24/7.

CẤM OVER-ENGINEER. Mục tiêu: người dùng muốn dùng lại như trợ lý hàng ngày (cảm giác Grokbot, local). Không framework Agent, không IDE, không terminal nhúng, không DB phiên, không scheduler, không extension, không đa Agent, không màn quyền, không hiện schema/OpenCode/worktree/verifier trên UI. Dùng module hiện có. Hai cách cùng đạt: ít code hơn. Giữ `antigravity_bridge.py`. Chỉ thay cầu nối lập trình NVIDIA sau G1 OpenCode đạt. G1 fail thì Cline cùng fixture, không fork.

Python 3.11 qua `uv run --no-sync --group dev`. Chỉ fixture `tests/fixtures/agent_harness/`. Không gửi `local_only` ra cloud. Không giả PASS. Không commit/push trừ khi owner ra lệnh.

Cổng kỹ thuật (pytest, compileall, audit) đủ để tiếp tục cổng sau. Không dừng chờ người ngồi duyệt hay kiểm toán độc lập. TECHNICAL_PASS khác DONE vận hành.

Trước khi kết thúc lượt: task đã xong, lệnh và mã thoát, file đổi, blocker thật, task kế.
```

## 1. Mục tiêu duy nhất

Làm T000–T030 để Workspace Chat trở thành trợ lý việc hằng ngày: nói một câu, nhận kết quả dùng được, muốn mở lại.

1. Báo cáo lỗi xưởng — file dùng được, có bảng/biểu đồ đúng nguồn (US1).
2. Rà soát Guideline vs bản thiết kế — đạt/lệch/thiếu bằng chứng (US2).
3. Sửa mã, test thật, hoàn tác (US3).
4. Giao tiếp việc khi việc trước còn chạy (US4).

## 2. Cấm over-engineer

- Ưu tiên sửa module hiện có.
- Không framework Agent, app, database, package harness, IDE, terminal, scheduler, đa Agent.
- Không làm cổng sau trước khi cổng hiện tại test xanh.
- Không nhét tên kỹ thuật lên UI.
- Hai phương án cùng đạt: ít code hơn. Thừa lớp = lệch Goal.

## 3. Khóa trải nghiệm (không bắt người duyệt)

- Không checkbox quyền, không duyệt hunk, không hỏi từng tool call.
- US1: verifier đạt → file báo cáo `completed` → UI «Đã xong». Không gọi đó là bản nháp chờ ban hành.
- US2: verifier đạt → `verified_draft` → UI «Đã xong»; không ghi đè SOP gốc.
- US3: test quan sát được đạt → việc xong trong worktree. Không bắt bấm «Dùng kết quả» mới tính hoàn tất.
- Hoàn tác luôn hiện. Chi tiết kỹ thuật đóng mặc định.
- Điều kiện ra G1–G5 là lệnh trong [quickstart.md](quickstart.md). G6 là quality gate repo, không phải người ngồi xác nhận.

## 4. Thứ tự bắt buộc

T000 đọc tài liệu → T001–T005 G1 (dừng sớm nếu probe fail) → T006–T010 nền → T011–T015 US1 → T016–T019 US2 → T020–T023 US3 → T024–T026 US4 → T027–T030 G6.

## 5. Việc không làm

Dự đoán lỗi; tự lấy dữ liệu line khi chưa nạp file; tự ban hành SOP; clone Grok/Cline/IDE; xóa test fail; tuyên bố ngang OpenCode trên giấy.
