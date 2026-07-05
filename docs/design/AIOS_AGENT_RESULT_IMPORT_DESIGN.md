# AIOS Agent Result Import Design

## 1. Mục tiêu & Ranh giới (Goals & Boundaries)

Agent Result Import đóng vai trò là một cổng phân tích và xác minh bằng chứng (validation boundary) để đưa các kết quả từ các tác vụ thay đổi repo của Agent vào hệ thống dữ liệu Case của AIOS.

### Nguyên tắc bảo mật cốt lõi

- **Không tự động tin cậy Agent:** Importer tuyệt đối không công nhận trạng thái `PASS` chỉ vì agent tự khai báo trong report.
- **Không thực thi lệnh:** Importer không thực thi bất kỳ câu lệnh, script hay hướng dẫn đường dẫn nào chứa trong file report nhận được.
- **Không nội suy shell (No shell interpolation):** Không thực hiện nội suy chuỗi hoặc các phép chạy lệnh từ dữ liệu của report để tránh các tấn công chèn lệnh (command injection).
- **Đường dẫn không tin cậy:** Các đường dẫn do report cung cấp đều ở trạng thái không tin cậy cho tới khi được hệ thống cục bộ chuẩn hóa và xác minh ranh giới dự án.
- **Định dạng có thẩm quyền:** Định dạng JSON của report là tài liệu có thẩm quyền cao nhất (authoritative format). Các mô tả bằng định dạng Markdown (nếu có) chỉ đóng vai trò trình bày trực quan và không có giá trị xác minh.

---

## 2. Thiết kế Report Schema (`aios_agent_report_v1`)

Mỗi report gửi về từ agent bắt buộc tuân thủ cấu trúc JSON schema dưới đây.

### Cấu trúc Schema JSON

```json
{
  "schema_version": "aios_agent_report_v1",
  "task_id": "uuid-v4-task-identifier",
  "task_pack_sha256": "computed-sha256-hash-of-original-task-pack",
  "agent_class": "implementation | audit-only | push-safety | smoke-test",
  "model_tool_name": "Gemini-3.5-Pro-High-via-Antigravity",
  "declared_status": "PASS | FAIL | REVIEW_REQUIRED",
  "baseline": {
    "branch": "main",
    "head": "f3a9b6c42d2aa40f2cd225f1684d70c06e9dc039"
  },
  "final_state": {
    "branch": "main",
    "head": "68b0686b04dd611931cd58a005d9eb7946ddd84a",
    "commit_hash": "68b0686b04dd611931cd58a005d9eb7946ddd84a",
    "push_status": "NOT_PUSHED"
  },
  "declared_files": {
    "changed": [
      "src/aios_habit/workspace_chat_app.py"
    ],
    "staged": [],
    "untracked": [],
    "committed": [
      "src/aios_habit/workspace_chat_app.py"
    ]
  },
  "declared_commands": [
    {
      "command": "uv run pytest tests/test_workspace_chat_app.py -q",
      "exit_code": 0,
      "safe_output_summary": "1 passed in 0.12s"
    }
  ],
  "declared_tests": [
    {
      "command": "uv run pytest tests/test_workspace_chat_app.py -q",
      "result": "PASS",
      "collected": 1,
      "passed": 1,
      "failed": 0,
      "skipped": 0
    }
  ],
  "risks": [
    "No immediate security risks identified"
  ],
  "blockers": [],
  "rollback": {
    "performed": false,
    "strategy_details": "N/A"
  },
  "reason_codes": [],
  "report_sha256": "computed-sha256-hex-hash-excluding-this-field"
}
```

### Quy tắc băm toàn vẹn (Hash Rules)

- **Thuật toán băm toàn vẹn:** Sử dụng **SHA-256** làm hàm băm duy nhất. **Tuyệt đối không dùng MD5** làm integrity hash.
- **Tính toán băm:** Tính băm `report_sha256` dựa trên chuỗi JSON canonical (sort keys, compact separators, UTF-8, no BOM) và loại bỏ trường `"report_sha256"` ra trước khi tính.

---

## 3. Khác biệt Giữa Declared Evidence & Observed Evidence

Hệ thống import phân biệt rạch ròi hai loại bằng chứng để chống lại hành vi gian lận (fake PASS):

- **Declared Evidence (Bằng chứng tự khai):** Là toàn bộ thông tin do agent tự ghi nhận trong file report (ví dụ: số lượng test pass, danh sách file đã sửa, commit hash đã tạo).
- **Observed Evidence (Bằng chứng quan sát độc lập):** Là các dữ liệu mà local verifier / Git observer cục bộ tự quét và truy vấn được trực tiếp từ môi trường repo thực tế (ví dụ: truy vấn `git diff`, kiểm tra danh sách file dirty thực tế, chạy lại test suite cục bộ độc lập).

### Quy tắc ra phán quyết (Verdict Logic)

- **Thiếu Observed Evidence:** Nếu không thể kiểm chứng độc lập observed evidence (ví dụ: môi trường repo không khả dụng hoặc bị lỗi), phán quyết (verdict) tối đa chỉ có thể là `REVIEW_REQUIRED`. Không bao giờ tự động chuyển trạng thái thành `VERIFIED_PASS`.
- **Chỉ công nhận VERIFIED_PASS khi và chỉ khi:** Có sự khớp nối 100% giữa declared evidence và observed evidence, đảm bảo scope sạch, không có tệp cấm bị sửa đổi, toàn bộ required tests chạy thành công trên máy cục bộ và được phê duyệt bởi owner.

---

## 4. Bảng Phán Quyết Phân Loại (Verdict Taxonomy)

Mọi hoạt động import sẽ kết thúc bằng một trong bốn phán quyết hữu hạn dưới đây. Chi tiết lỗi hoặc cảnh báo cụ thể sẽ được ghi nhận chi tiết trong danh sách `reason_codes[]`.

### Bốn Verdict Hữu Hạn

1. **`VERIFIED_PASS`:** Report hợp lệ, khớp nối hoàn hảo với observed evidence trên môi trường local và đáp ứng toàn bộ tiêu chí của task pack.
2. **`FAIL`:** Xác định có vi phạm bảo mật nghiêm trọng (forbidden file bị sửa đổi, leak API key, lệnh cấm chạy, hoặc test bắt buộc bị fail).
3. **`REVIEW_REQUIRED`:** Có sự sai lệch nhẹ giữa report và thực tế (ví dụ: lệch baseline head nhưng không ghi đè mã nguồn nguy hiểm, hoặc thiếu observed evidence để kiểm chứng). Cần owner xác nhận thủ công.
4. **`INVALID_REPORT`:** File report bị lỗi cú pháp, sai định dạng JSON, sai schema version, dung lượng quá tải, hoặc sai chữ ký băm SHA-256.

### Danh sách Reason Codes chuẩn hóa

- `TASK_ID_MISMATCH`
- `PACK_HASH_MISMATCH`
- `SCHEMA_VERSION_UNSUPPORTED`
- `BASELINE_MISMATCH`
- `FORBIDDEN_FILE_TOUCHED`
- `UNTRACKED_FILES_PRESENT`
- `RUNTIME_DIRTY`
- `MISSING_REQUIRED_TEST`
- `TEST_EXIT_CODE_MISSING`
- `DECLARED_PASS_WITHOUT_OBSERVED_EVIDENCE`
- `PATH_TRAVERSAL_DETECTED`
- `REPORT_TOO_LARGE`
- `REPORT_TOO_DEEP`
- `SECRET_PATTERN_DETECTED`
- `UNAUTHORIZED_COMMIT`
- `UNAUTHORIZED_PUSH`
- `ROADMAP_STALE`
- `MOJIBAKE_DETECTED`

---

## 5. Kiểm Soát An Toàn Khi Import (Import Safety Controls)

Để đảm bảo sandbox an toàn tuyệt đối khi phân tích report, importer áp dụng các chốt chặn:

- **Path Containment & No Path Traversal:** Chuẩn hóa mọi đường dẫn (normalize) và kiểm tra ranh giới thư mục dự án. Cấm mọi ký tự di chuyển thư mục `../` hoặc sử dụng các symlink độc hại để trỏ ra ngoài repo.
- **Thư mục lưu trữ cục bộ cô lập:** Mọi tệp tin vào/ra của Bridge được lưu trữ tại:

  `local_runs/agent_bridge/outbox/`
  `local_runs/agent_bridge/inbox/`
  `local_runs/agent_bridge/processed/`
  *(Thư mục `local_runs/` này bị ignore hoàn toàn bởi Git).*

- **Giới hạn dung lượng và độ sâu:** Giới hạn kích thước file report tối đa (ví dụ: 1MB) và độ sâu lồng nhau của JSON tối đa (ví dụ: 5 cấp) để phòng ngừa tấn công từ chối dịch vụ.
- **UTF-8 Strict & No BOM:** Phải đọc file ở chế độ UTF-8 nghiêm ngặt, không tự động sửa mojibake im lặng, và từ chối xử lý nếu file chứa Byte Order Mark (BOM).
- **Atomic Writes:** Sử dụng ghi file nguyên tử (atomic writes) khi cập nhật dữ liệu case cục bộ để tránh lỗi hỏng dữ liệu khi mất điện hoặc crash nửa chừng.
- **UI/Log Safe Summary:** Các lỗi bảo mật hoặc thông tin nhạy cảm không được in thô (raw print) lên UI/Log; chỉ in các thông báo lỗi fixed tiếng Việt an toàn đã được che giấu thông tin chi tiết của hệ thống đĩa cứng hay secrets.

---

## 6. Kế Hoạch Subgate (Subgate Plan)

Ba tài liệu thiết kế thống nhất kế hoạch phân chia subgates như sau:

1. **AI-GW-A17-DESIGN:** Docs-only design gate (gate hiện tại, chỉ thiết lập tài liệu kiến trúc, không chạy code).
2. **AI-GW-A17A:** Task Pack Export MVP (phát triển bộ xuất file tác vụ có ký số SHA-256).
3. **AI-GW-A17B:** Result Import MVP (phát triển parser và validation checks cho report).
4. **AI-GW-A17C:** Workspace Chat export/import helper (tích hợp helper UI).
5. **AI-GW-A17D:** Git observer / validation receipt / anti-fake hardening (xác minh observed evidence).
6. **RM-SYNC-A17:** Master roadmap sync after A17 (đồng bộ và cập nhật trạng thái Phase 5 thành DONE hoàn toàn sau khi A17 hoàn tất).

> [!IMPORTANT]
> - `AI-GW-A17-DESIGN` là gate thiết kế tài liệu duy nhất. Các subgate tiếp theo chưa được mở và hoạt động implementation chưa bắt đầu.
> - Bất kỳ hoạt động sửa đổi mã nguồn (`src/`) hoặc kiểm thử (`tests/`) nào cho A17 đều bị nghiêm cấm trong gate này.
