# Prompt sửa US1/US2 — đọc nguồn thật, bỏ hardcode

Dán nguyên khối dưới cho GPT/Gemini. Không làm OpenCode. Không BLOCK Goal.

```text
Sửa Goal 009 US1/US2 trong D:\Sandbox\AIOS_habbit, nhánh gate1-local-case-sqlite.

Đọc: specs/009-agent-harness-adoption/GPT_FIX_US1_US2.md, contracts/agent-factory-error-report-v1.md, contracts/agent-process-design-review-v1.md, src/aios_habit/agent_work_artifact.py, tests/test_agent_error_report_artifact.py, tests/test_agent_process_design_review.py.

LỖI HIỆN TẠI (phải xóa):
- Báo cáo lỗi không đọc nội dung log/md. Câu sẵn kiểu «Nhật ký X ghi nhận cảnh báo». Việc tiếp theo hardcode «đầu ép».
- Biểu đồ chỉ chạy nếu cột đúng tên `thời_gian`, `số_lượng_lỗi`, `số_lượng_kiểm`, `đơn_vị`.
- Rà soát công đoạn hardcode nhiệt độ °C (`_first_temperature`) và luôn gắn CHECK-INSPECTION «ngoại quan» — khớp fixture hàn, không generic.
- `create_process_design_review` khai báo trả FactoryErrorReportResult.

VIỆC PHẢI LÀM:
1. US1 — đọc file nguồn thật:
   - .log/.txt/.md: lấy hiện tượng từ đoạn văn bản thật (trích ngắn, ghi tên file). Không bịa.
   - Bảng CSV/Excel: tự nhận cột thời gian/ngày và cột số (tên cột bất kỳ, tiếng Việt hoặc Latin). Đơn vị lấy từ header/ô nếu có. Thiếu số → visuals rỗng, uncertainties nói thiếu gì. Không yêu cầu tên cột cố định.
   - next_actions chỉ từ nguồn, hoặc câu generic không gắn công đoạn cụ thể.
2. US2 — đối chiếu nội dung thật:
   - Vai trò guideline/design/context theo tên file (keyword generic đã có) vẫn được.
   - Đọc text hai phía. Tìm giới hạn/số+đơn vị trong guideline và giá trị tương ứng trong design. Khớp đơn vị thì pass/violate; không tìm thấy thì insufficient. Không hardcode °C, hàn, ngoại quan.
   - Mâu thuẫn phiên bản: chỉ khi nội dung/tiêu đề nguồn nói khác phiên bản, không phải vì có 2 file guideline là gắn sẵn một câu.
   - Đề xuất và câu hỏi bám phát hiện thật. Không sửa file SOP gốc.
3. Giữ UX: «Đã xong», «Mở kết quả», «Hoàn tác», không nút duyệt, không OpenCode/Cline/adapter/fork, không hiện schema trên UI.
4. Sửa/bổ sung test: giữ fixture cũ vẫn xanh; thêm case cột Excel tên Latin (time, defects, inspected, unit) vẫn ra visual; thêm US2 không có °C vẫn violate/insufficient dựa trên số+đơn vị khác (ví dụ mm hoặc %).
5. Ít code. Dùng extract_excel / đọc text hiện có. Không LLM mới, không framework, không đổi antigravity_bridge.

Python: uv run --no-sync --group dev. Chỉ fixture tests/fixtures/agent_harness/. Không giả PASS. Không commit trừ khi owner bảo.

Xong lượt: file đổi, pytest đã chạy (lệnh + số passed), không còn hardcode cột tiếng Việt và _first_temperature.
```
