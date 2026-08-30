# Quy tắc phát triển và tác tử AIOS WorkLens

Tài liệu này quy định các điều luật bị khóa cứng mà toàn bộ mô hình AI, tác tử phát triển và người chỉnh sửa mã nguồn **bắt buộc** tuân thủ, không có ngoại lệ, khi làm việc trên kho `AIOS_habbit`.

---

## 1. Phân định vai trò mô hình bị khóa

Để ngăn chặn suy thoái mã nguồn, thực thi chắp vá hoặc xác minh PASS giả, nhiệm vụ phát triển được chia theo thế mạnh chuyên môn:

### A. Chuyên gia kiểm toán và đánh giá
- **Vai trò chính:** Kiểm toán chất lượng mã nguồn, đánh giá bảo mật, kiểm tra chống PASS giả và lập luận phân tích kiến trúc.
- **Ràng buộc:**
  - Bắt buộc phải kiểm tra tất cả các tệp đã sửa đổi và chạy các lệnh kiểm tra độc lập.
  - Phải chỉ ra các nguy cơ rò rỉ prompt, quá tải giao diện và sự thiếu hụt bằng chứng xác thực.
  - Không tự tiện commit hoặc viết mã tính năng trừ khi được yêu cầu các chỉnh sửa nhỏ.
- **Mô hình khuyến nghị hiện tại:** Codex GPT-5.5 hoặc tương đương.

### B. Chuyên gia thực thi
- **Vai trò chính:** Triển khai tính năng, sửa lỗi, tái cấu trúc mã nguồn và viết kiểm thử đơn vị.
- **Ràng buộc:**
  - Phải tuân thủ nghiêm ngặt theo bản kế hoạch triển khai đã được người dùng phê duyệt.
  - Không được bỏ qua viết kiểm thử hoặc chạy xác minh lệnh thực tế.
- **Mô hình khuyến nghị hiện tại:** Gemini Flash 3.5 High / Gemini Pro 3.1 hoặc tương đương.

---

## 2. Quy tắc xác minh bắt buộc

Không một pull request hay thay đổi mã nguồn nào được phép gộp hoặc đẩy nếu không đáp ứng đầy đủ:

1. **Kiểm tra biên dịch:** mã phải biên dịch sạch khi chạy `py -3 -m compileall src tests`.
2. **Kiểm thử:** toàn bộ bài kiểm tra hiện có và bài mới phải vượt `py -3 -m pytest -q`.
3. **Kiểm tra audit cục bộ:** `$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit` phải trả `"status": "PASS"`.
4. **Kiểm tra import giao diện chính:** `$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"` phải thành công.
5. **Ranh giới hệ thống cũ:** module Workspace Chat được hỗ trợ không được import `studio` hoặc `case_cockpit`; khi dừng phần cũ phải gỡ đường khởi chạy và kỳ vọng kiểm thử lỗi thời.

---

## 3. Quy tắc bảo mật và quyền riêng tư (bất khả xâm phạm)
- **Không rò lên mây trái phép:** bằng chứng `local_only`, log/bảng tính thô, thẻ học việc chưa xác nhận **không** đưa vào Gemini Web, Nakazasen Router, `gpt`/`copilot`/`notebooklm_safe`, hay gói `cloud_safe`.
- **C-AGENT (Sonnet 4 công ty):** đường được công ty mua và cam kết bảo mật. Khi người dùng **chọn đúng** cầu nối `cagent_api`, được gửi bản vẽ, sơ đồ mạch, log, gói điều tra. Không tự chuyển gói đó sang Gemini/Router.
- **Chỉ AI cục bộ khác:** `local_ai` chỉ khi người dùng chỉ định `include_local_only=True`.
- **Không đưa vào Git:** `local_cases/`, ảnh chụp thật, cơ sở dữ liệu thật, `.env` riêng tư.
- Caption UI chưa đủ: chưa có hard guard chặn file ảnh khi backend là Gemini/Router — đó là việc phải làm, không được coi caption là chặn.

Chi tiết phân loại dữ liệu: `00_governance/DATA_POLICY.md`. Đánh giá tác động quyền riêng tư: `docs/security/PRIVACY_IMPACT_ASSESSMENT.md`. Không sao chép toàn bộ chính sách dữ liệu vào file này.

---

## 4. Luật ngôn ngữ (giao diện và tài liệu) — bất khả xâm phạm

Áp dụng cho mọi người và mọi agent. Không có ngoại lệ “viết nhanh bằng tiếng Anh rồi dịch sau”.

### 4.1 Giao diện người dùng
- Nhãn, hành động, cảnh báo, trạng thái trống, lỗi hiển thị cho người dùng: **100% tiếng Việt**.
- Hằng kỹ thuật bắt buộc giữ nguyên (`local_only`, `redacted_export`, `cloud_allowed`) phải có giải thích tiếng Việt ngay bên cạnh.
- Không lộ traceback thô, đường dẫn hệ thống, secret, hay nội dung `local_only` trên giao diện thường.

### 4.2 Tài liệu sản phẩm (mọi file `.md` thuộc repo, trừ mục 4.4)
- **Câu văn, tiêu đề mục, mô tả, bảng giải thích: tiếng Việt.** Cấm viết đoạn văn hay tiêu đề bằng tiếng Anh.
- Cấm tài liệu song ngữ kiểu “Compilation Check”, “Core Rules”, “Definition of Done” trong tiêu đề.
- Tài liệu **mới** hoặc **đang sửa** không được thêm câu tiếng Anh.
- Khi sửa file cũ còn tiếng Anh: **dịch phần đụng tới** trong cùng lượt, không để nguyên đoạn Anh và không thêm Anh mới.
- Sổ thảo luận sống (`Thảo_luận_AI_dự_đoán_lỗi_LSU.md`), README, spec đang mở, ADR, runbook: cùng luật.

### 4.3 Được giữ nguyên (không phải câu văn)
Chỉ các **token** sau được để tiếng Anh, và phải có nghĩa tiếng Việt gần đó nếu người đọc không phải lập trình viên:
- Đường dẫn file, tên module/lớp/hàm, lệnh chạy (`pytest`, `compileall`).
- Nhãn máy mà công cụ đọc được: `Status:`, `PASS` / `FAIL`, hằng `local_only`.
- Tên sản phẩm đã khóa: Workspace Chat, BGE-M3.

### 4.4 Không bắt buộc dịch lại trong một lượt
`docs/archive/`, `CHANGELOG.md` (lịch sử), báo cáo cổng đã đóng trong `08_audit/`: bằng chứng cũ. **Không viết thêm tiếng Anh.** Không xóa lịch sử. Khi mở file đó để sửa nội dung vận hành, dịch phần đưa ra vận hành.

### 4.5 Mã nguồn
Tên định danh, comment kỹ thuật, commit message: tiếng Anh (không phải tài liệu người đọc).

Chi tiết kiểm soát tài liệu: `docs/DOCUMENTATION_GOVERNANCE.md`. Chi tiết UI: `docs/UI_LANGUAGE_POLICY.md`.

