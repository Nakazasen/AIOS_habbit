# Kế hoạch Triển khai Kỹ thuật: 014-large-library-nonblocking-chat

**Branch**: `014-large-library-nonblocking-chat` | **Ngày**: 2026-09-14 | **Đặc tả**: [specs/014-large-library-nonblocking-chat/spec.md](file:///d:/Sandbox/AIOS_habbit/specs/014-large-library-nonblocking-chat/spec.md)

**Đầu vào**: Tối ưu hóa hiệu năng và trải nghiệm trò chuyện trên thư viện tài liệu lớn, chuyển cơ chế All-or-Nothing sang Graceful Degradation, gỡ bỏ eager enqueue 988 nguồn khi tải trang, tuân thủ đặc tả FR-006 & FR-011, và giảm áp lực polling SQLite.

---

## Tóm tắt Giải pháp Kỹ thuật

1. **Loại bỏ Eager Enqueue toàn thư viện khi tải trang**:
   - Tại `src/aios_habit/workspace_chat_app.py` (L2180-2183), gỡ bỏ lệnh gọi `reconcile_and_enqueue_workspace_chat_sources(prep_context_sources)` trên toàn bộ 988 nguồn trong sidebar và biến `prep_status_map` thừa.
   - Tại L3464-3467, chỉ lập lịch chuẩn bị nền cho các nguồn đang được bật trong cuộc trò chuyện (`enabled_ctx_sources`), thay vì toàn bộ `ctx_all_sources`.
2. **Chuyển cơ chế All-or-Nothing sang Graceful Degradation**:
   - Trong `_pending_source_submission_state` (L758-765): Nếu một số nguồn hoàn thành và một số nguồn bị `failed`, hệ thống chuyển sang trạng thái `ready` để tiếp tục câu hỏi trên các nguồn sẵn sàng, thay vì hủy toàn bộ câu hỏi.
   - Nếu tất cả các nguồn yêu cầu bị lỗi chuẩn bị vector nhưng vẫn có văn bản nguồn, cho phép chuyển sang `ready` để bộ điều phối trả lời qua văn bản nguồn hoặc cầu nối Gemini.
   - Trong luồng gửi câu hỏi (L2957-3062): Bỏ qua các nguồn `failed`, cho phép câu hỏi tiếp tục chạy với `query_relevant_sources = ready_sources`.
   - Nếu không có nguồn vector nào sẵn sàng, chuyển sang chế độ fallback trực tiếp qua nội dung văn bản nguồn (`retrieval_applied = False`) thay vì chặn đứng với thông báo lỗi đỏ.
3. **Chuẩn hóa xử lý Broad Query tuân thủ FR-006 & FR-011**:
   - Trong nhánh Broad Query (L3004-3060), nếu có `ready_sources`, thực hiện tra cứu trên các nguồn đã sẵn sàng.
   - Nếu chưa có nguồn nào sẵn sàng và có nhiều hơn 1 nguồn chưa chuẩn bị: Không đưa toàn bộ danh sách vào hàng đợi ưu tiên tương tác; hiển thị thông báo hướng dẫn người dùng thu hẹp câu hỏi hoặc chọn tài liệu cụ thể theo FR-006.
   - Nếu chỉ có đúng 1 nguồn: Đưa đúng 1 nguồn đó vào hàng đợi ưu tiên theo FR-011.
4. **Tối ưu hóa Polling Giao diện & SQLite**:
   - Chuyển `_live_preparation_progress_panel` sang theo dõi `enabled_ctx_sources` (thay vì 988 tài liệu), giãn chu kỳ từ 2.5s lên 4.0s.
5. **Nâng cấp Fallback Ngữ cảnh tại Cầu nối AI**:
   - Trong `src/aios_habit/antigravity_bridge.py`, khi `evidence_items` rỗng nhưng `packed_sources` có dữ liệu văn bản, tự động trích xuất trích đoạn văn bản nguồn vào `context_blocks` để cấp ngữ cảnh cho Gemini Web Bridge.

---

## Bối cảnh Kỹ thuật

- **Ngôn ngữ / Phiên bản**: Python 3.11
- **Phụ thuộc chính**: Streamlit 1.40+, SQLite3, `aios_habit.workspace_chat_rag_v2_adapter`, `aios_habit.antigravity_bridge`
- **Lưu trữ**: SQLite Ledger (`workspace_chat_preparation_ledger.db`), JSONL cho Chat History
- **Kiểm thử**: `pytest`, `compileall`, `aios_habit.cli audit`
- **Ràng buộc Kiến trúc**:
  - Không import `studio` hoặc `case_cockpit` vào `workspace_chat_app.py`.
  - Giữ vững tính toàn vẹn của các test assertion tĩnh trong `test_workspace_chat_source_selection_owner_flow.py`.
  - Thông báo giao diện hoàn toàn bằng tiếng Việt chuẩn mực.

---

## Kiểm tra Hiến pháp (Constitution Check)

| Tiêu chuẩn | Kết quả | Chi tiết |
|:---|:---:|:---|
| **P1: An toàn Dữ liệu & Riêng tư** | **PASS** | Không gửi tài liệu ra ngoài mà không có xác nhận; giữ nguyên nhãn `local_only` / `cloud_safe`. |
| **P2: Trung thực & Không Fake PASS** | **PASS** | Không che giấu lỗi nguồn; nguồn lỗi vẫn hiển thị rõ ràng trên từng dòng nguồn kèm nút bấm "Thử chuẩn bị lại". |
| **P3: Chính sách Ngôn ngữ** | **PASS** | 100% tiếng Việt cho các thông báo giao diện, cảnh báo và nhật ký vận hành. |
| **P4: Ranh giới Hệ thống** | **PASS** | Không phá vỡ luồng RAG v2 Canary, giữ nguyên các cổng an toàn của adapter. |

---

## Cấu trúc Tệp Thay đổi

```text
specs/014-large-library-nonblocking-chat/
├── spec.md              # Đặc tả kịch bản và tiêu chí nghiệm thu
├── plan.md              # Kế hoạch kỹ thuật này
└── tasks.md             # Danh sách đầu việc chi tiết

src/aios_habit/
├── workspace_chat_app.py      # Loại bỏ eager enqueue, sửa All-or-Nothing, tối ưu polling
└── antigravity_bridge.py      # Bổ sung fallback văn bản nguồn khi vector rỗng
```
