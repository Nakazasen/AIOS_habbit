# AIOS Agent Result Import Design

## 1. Mục tiêu & Ranh giới (Goals & Boundaries)

Agent Result Import đóng vai trò là một cổng phân tích và xác minh bằng chứng (validation boundary) để đưa các kết quả từ các tác vụ thay đổi repo của Agent vào hệ thống dữ liệu Case của AIOS.

### Nguyên tắc bảo mật cốt lõi

- **Không tự động tin cậy Agent:** Importer tuyệt đối không công nhận trạng thái `PASS` chỉ vì agent tự khai báo trong report.
- **Không thực thi lệnh:** Importer không thực thi bất kỳ câu lệnh, script hay hướng dẫn đường dẫn nào chứa trong file report nhận được.
- **Không tự động chạy test hoặc lệnh trên importer:** Importer chỉ làm nhiệm vụ parse/validate cấu trúc dữ liệu JSON của report và đối chiếu dữ liệu có sẵn. Importer không tự chạy bất kỳ test hay command nào.
- **Owner-triggered verifier riêng biệt:** Mọi hoạt động chạy thử nghiệm, kiểm tra hoặc kiểm chứng code thực tế trên repo chỉ được thực hiện thông qua một verifier/observer cục bộ độc lập và do owner kích hoạt thủ công (owner-triggered verifier). Nếu không có observed evidence tương ứng do owner-triggered observer tạo ra, verdict tối đa của report chỉ có thể là `REVIEW_REQUIRED`. Tại subgate `AI-GW-A17D`, hệ thống mới được phép tích hợp read-only Git/test observer cố định, tuy nhiên bộ verifier/observer này vẫn phải được kích hoạt trực tiếp bởi owner (owner-triggered) và tuyệt đối không tự động đọc hay thực thi các command trích xuất từ file report của agent.
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
  "task_id": "A17_TASK_EXPORT_001",
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
- **Bản chất của SHA-256:** SHA-256 only provides integrity checking in A17. It is not a digital signature and does not prove author identity. Any authenticity/signing scheme is out of scope for A17 MVP.
- **Tính toán băm:** Tính băm `report_sha256` dựa trên chuỗi JSON canonical (sort keys, compact separators, UTF-8, no BOM) và loại bỏ trường `"report_sha256"` ra trước khi tính.

---

## 3. Khác biệt Giữa Declared Evidence & Observed Evidence

Hệ thống import phân biệt rạch ròi hai loại bằng chứng để chống lại hành vi gian lận (fake PASS):

- **Declared Evidence (Bằng chứng tự khai):** Là toàn bộ thông tin do agent tự ghi nhận trong file report (ví dụ: số lượng test pass, danh sách file đã sửa, commit hash đã tạo). Các dữ liệu tự khai báo này mặc định không đáng tin cậy. Agent self-declared test PASS không bao giờ đủ để công nhận `VERIFIED_PASS`.
- **Observed Evidence (Bằng chứng quan sát độc lập):** Là các dữ liệu kiểm chứng độc lập do local verifier hoặc Git observer cục bộ tạo ra khi được owner kích hoạt (`owner-triggered`).
- **Observed-Evidence Provenance & Receipt Fields:** Để đảm bảo tính toàn vẹn và chứng minh command/test đến từ cấu hình cố định của owner chứ không phải từ report của agent, mỗi observed evidence được ghi nhận bắt buộc phải có các trường provenance sau:
  - `verifier_name`: Tên của verifier thực hiện kiểm chứng.
  - `verifier_version`: Phiên bản của verifier.
  - `observation_time_utc`: Thời gian quan sát thực tế theo giờ UTC.
  - `owner_triggered`: Giá trị boolean (`true`), khẳng định hành động do owner kích hoạt.
  - `owner_triggered_at_utc`: Thời gian owner kích hoạt hành động kiểm chứng theo giờ UTC.
  - `repo_branch`: Nhánh repo hiện tại.
  - `repo_head`: Commit HEAD hiện tại của repo.
  - `validation_config_id`: Định danh của cấu hình kiểm chứng.
  - `validation_config_sha256`: Hash toàn vẹn (SHA-256) của file cấu hình kiểm chứng của owner.
  - `fixed_command_id` hoặc `fixed_test_id`: Định danh lệnh hoặc bài test cố định trong file cấu hình.
  - `command_source`: Nguồn gốc câu lệnh được thực thi. Trường này bắt buộc phải có giá trị `OWNER_APPROVED_FIXED_CONFIG`.
  - `command_from_report`: Bắt buộc phải là `false`. Khẳng định lệnh không lấy từ report của agent.
  - `report_command_ignored`: Bắt buộc phải là `true`. Khẳng định các lệnh do report của agent cung cấp đã bị bỏ qua khi chạy verifier.
  - `exit_code`: Mã thoát của lệnh chạy.
  - `result`: Kết quả kiểm chứng (`PASS` hoặc `FAIL`).
  - `safe_summary`: Bản tóm tắt kết quả an toàn.
  - `output_digest`: Tóm tắt mã hóa (SHA-256 hash) của output đầu ra (nếu có) để đối chiếu toàn vẹn.

*Quy tắc bắt buộc:* Bất kỳ kết quả quan sát (observation) nào dựa trên văn bản lệnh lấy trực tiếp từ file report của agent đều bị coi là không hợp lệ và không đủ điều kiện để công nhận trạng thái `VERIFIED_PASS`. Lệnh kiểm chứng bắt buộc phải được lấy từ cấu hình cố định được owner phê duyệt từ trước (`OWNER_APPROVED_FIXED_CONFIG`).

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
4. **`INVALID_REPORT`:** File report bị lỗi cú pháp, sai định dạng JSON, sai schema version, dung lượng quá tải, hoặc sai SHA-256 integrity hash / checksum.

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
- `REPORT_REPLAY_DETECTED`
- `WRONG_TASK_PACK`
- `REPORT_ALREADY_PROCESSED`

---

## 5. Kiểm Soát An Toàn Khi Import (Import Safety Controls)

Để đảm bảo sandbox an toàn tuyệt đối khi phân tích report, importer áp dụng các chốt chặn:

- **Path Containment & No Path Traversal:** Chuẩn hóa mọi đường dẫn (normalize) và kiểm tra ranh giới thư mục dự án. Cấm mọi ký tự di chuyển thư mục `../` hoặc sử dụng các symlink độc hại để trỏ ra ngoài repo.
- **Task ID Allow-List & Regex Policy:** Trường `task_id` trong report bắt buộc phải tuân thủ định dạng regex an toàn và có giới hạn độ dài nghiêm ngặt: `^[A-Z0-9][A-Z0-9_-]{2,80}$`. Hệ thống reject ngay lập tức nếu `task_id` chứa ký tự đặc biệt như slash (`/`), backslash (`\`), dot-dot (`..`), drive letter (ví dụ `C:`), control chars. Tuyệt đối không dùng trực tiếp trường `task_id` để ghép chuỗi tạo đường dẫn tệp tin mà phải thực hiện sanitize và normalize đầy đủ.
- **Schema Version Allow-List:** Hệ thống chỉ chấp nhận các schema version nằm trong danh sách allow-list cố định sau: `aios_agent_task_pack_v1` (đối với Task Pack) và `aios_agent_report_v1` (đối với Report). Bất kỳ schema version nào khác nằm ngoài danh sách này hoặc không xác định sẽ bị coi là không hợp lệ, hệ thống từ chối import và trả về verdict `INVALID_REPORT` kèm reason code `SCHEMA_VERSION_UNSUPPORTED`.
- **Raw-Report Privacy Class & Storage Propagation:** File report thô (raw report) nhận được bắt buộc phải được gắn thẻ phân loại bảo mật (privacy class). Privacy class của raw report được kế thừa theo nguyên tắc strictest-wins (nghiêm ngặt nhất thắng) từ: privacy của task pack tương ứng, privacy tự khai báo của report (nếu có), và chính sách bảo mật của nguồn/owner. Mọi thông tin nhạy cảm hoặc thô trong raw report không được hiển thị trực tiếp mà chỉ in safe summary ra UI/Log. Raw report không được phép xuất hoặc lưu trữ trên cloud nếu privacy class không cho phép. Kho lưu trữ processed storage cục bộ (`local_runs/agent_bridge/processed/`) bắt buộc phải lưu giữ metadata riêng tư (privacy metadata) song song bên cạnh file manifest của report.
- **Symlink Policy & Resolved Containment:** Hệ thống áp dụng chính sách `no-follow` mặc định đối với tất cả các symbolic link (symlink) khi import và xử lý tệp tin. Mọi thao tác kiểm tra đường dẫn phải được resolve đầy đủ về đường dẫn vật lý thực tế bên dưới thư mục lưu trữ gốc hoặc thư mục repo gốc (containment root). Hệ thống reject lập tức nếu resolved path chỉ ra ngoài containment root. Nghiêm cấm sự xuất hiện của symlink trong các thư mục làm việc cục bộ `inbox/`, `outbox/`, hoặc `processed/` trừ khi có một local policy được owner phê duyệt rõ ràng trước đó. Các đường dẫn do report cung cấp tuyệt đối không được dùng để resolve hoặc truy xuất tệp theo ý của report.
- **Replay Ledger & Idempotency Key:** Để chống lại tấn công replay hoặc gửi nhầm report (wrong-pack), hệ thống duy trì processed report ledger tại thư mục cục bộ bị git ignore: `local_runs/agent_bridge/processed/`. Khóa trùng lắp idempotency key được cấu hình là `task_id + task_pack_sha256 + report_sha256`. Mọi report trùng khóa sẽ bị từ chối và trả về lỗi `REPORT_REPLAY_DETECTED` hoặc `REPORT_ALREADY_PROCESSED`. Nếu report không khớp `task_pack_sha256` hoặc gửi sai nhiệm vụ, hệ thống trả về `WRONG_TASK_PACK`.
- **Thư mục lưu trữ cục bộ cô lập:** Mọi tệp tin vào/ra của Bridge được lưu trữ tại:
  - `local_runs/agent_bridge/outbox/`
  - `local_runs/agent_bridge/inbox/`
  - `local_runs/agent_bridge/processed/`
  *(Thư mục `local_runs/` này bị ignore hoàn toàn bởi Git).*

- **Giới hạn dung lượng và độ sâu:** Giới hạn kích thước file report tối đa (ví dụ: 1MB) và độ sâu lồng nhau của JSON tối đa (ví dụ: 5 cấp) để phòng ngừa tấn công từ chối dịch vụ.
- **UTF-8 Strict & No BOM:** Phải đọc file ở chế độ UTF-8 nghiêm ngặt, không tự động sửa mojibake im lặng, và từ chối xử lý nếu file chứa Byte Order Mark (BOM).
- **Atomic Writes:** Sử dụng ghi file nguyên tử (atomic writes) khi cập nhật dữ liệu case cục bộ để tránh lỗi hỏng dữ liệu khi mất điện hoặc crash nửa chừng.
- **UI/Log Safe Summary:** Các lỗi bảo mật hoặc thông tin nhạy cảm không được in thô (raw print) lên UI/Log; chỉ in các thông báo lỗi fixed tiếng Việt an toàn đã được che giấu thông tin chi tiết của hệ thống đĩa cứng hay secrets.

---

## 6. Kế Hoạch Subgate (Subgate Plan)

Ba tài liệu thiết kế thống nhất kế hoạch phân chia subgates như sau:

1. **AI-GW-A17-DESIGN:** Docs-only design gate (gate hiện tại, chỉ thiết lập tài liệu kiến trúc, không chạy code).
2. **AI-GW-A17A:** Task Pack Export MVP (phát triển bộ xuất file tác vụ có hash toàn vẹn/checksum SHA-256).
3. **AI-GW-A17B:** Result Import MVP (phát triển parser và validation checks cho report).
4. **AI-GW-A17C:** Workspace Chat export/import helper (tích hợp helper UI).
5. **AI-GW-A17D:** Git observer / validation receipt / anti-fake hardening (xác minh observed evidence).
6. **RM-SYNC-A17:** Master roadmap sync after A17 (đồng bộ và cập nhật trạng thái Phase 5 thành DONE hoàn toàn sau khi A17 hoàn tất).

> [!IMPORTANT]
> - `AI-GW-A17-DESIGN` là gate thiết kế tài liệu duy nhất. Các subgate tiếp theo chưa được mở và hoạt động implementation chưa bắt đầu.
> - Bất kỳ hoạt động sửa đổi mã nguồn (`src/`) hoặc kiểm thử (`tests/`) nào cho A17 đều bị nghiêm cấm trong gate này.
