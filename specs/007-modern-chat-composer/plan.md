# Implementation Plan: Modern Chat Composer

**Branch**: `007-modern-chat-composer` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

**Trạng thái**: `TECHNICAL_PASS` — smoke Playwright 6/6 và test composer tập trung đạt 2026-09-12.

## Summary

Replace the tall question form with a compact, rounded Workspace Chat composer inspired by current AI browser and IDE inputs. Add thumbnail-backed image attachment, browser-confirmed clipboard image paste, and an inline Mô hình AI picker that maps to the existing Gemini Web, C-AGENT and Router backends. Retain question processing, image ingestion, search preference, and pending-source safeguards.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Streamlit 1.60.0 and a small local image clipboard component

**Storage**: Existing local Workspace Chat store; no schema change

**Testing**: pytest, source-level UI contracts, existing Workspace Chat flow tests

**Target Platform**: Local-first browser UI on Windows; responsive from 360 px viewport width

**Project Type**: Local web application

**Performance Goals**: Composer remains immediately interactive; no additional network request or client-side dependency

**Constraints**: Vietnamese-first; preserve local-first privacy behavior; require a user gesture before clipboard read; do not alter the established image allowlist or pending-source lifecycle

**Scale/Scope**: One Workspace Chat composer in `workspace_chat_app.py`, focused tests, and a pinned clipboard component; excludes sidebars, source-library design, provider routing, and data models

## Constitution Check

| Gate | Status | Evidence |
|---|---|---|
| Evidence before assertion | Pass | Acceptance scenarios and source-level regression tests cover the form contract. |
| Local-first privacy and consent | Pass | Reuses current question and image submission path; no new data egress. |
| User-centered Workspace Chat | Pass | Vietnamese-first labels and native accessible controls are retained. |
| Change discipline and verifiable quality | Pass | Spec, plan, tasks, targeted tests, import and audit validation are required. |
| Graph-aware investigation | Pass | Graphify was queried for `workspace_chat_app.py` and its Workspace Chat tests. |

## Project Structure

```text
specs/007-modern-chat-composer/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── composer-ui-contract.md
└── tasks.md

src/aios_habit/
└── workspace_chat_app.py       # composer layout, state and scoped styling

tests/
├── test_workspace_chat_source_selection_owner_flow.py
├── test_workspace_chat_multi_file_uploader.py
├── test_workspace_chat_ui_i18n.py
└── test_workspace_chat_composer_ui.py
```

**Structure Decision**: Modify the existing single Streamlit application module and retain its established submission path. Add a small dedicated UI-contract test module instead of a frontend framework.

## Complexity Tracking

No constitution violations or additional complexity are required.

## Làm giàu nontech 2026-09-21 (không tạo spec mới)

**Phạm vi mở rộng đã duyệt**: giữ composer hiện có, thêm Câu chuyện 7 (composer siêu thân thiện) và Câu chuyện 8 (thẻ JIG, biểu đồ, mail dễ hiểu). Không dựng framework mới, không đổi luồng gửi, không thêm kho dữ liệu.

**Bối cảnh kỹ thuật bổ sung**:

- Ngôn ngữ và nền giữ nguyên: Python 3.11, Streamlit 1.60, một module `workspace_chat_app.py`, dùng lại mô đun `production_prediction` cho thẻ JIG và mô đun gợi ý hiện có.
- Tra cứu `ui-ux-pro-max` đã xác minh: nhãn nhìn thấy, nút bấm tối thiểu 44 px cách nhau 8 px, lỗi cạnh trường, biểu đồ đánh dấu bằng hình và chữ kèm bảng số, luồng trực tiếp có nút Tạm dừng. Tra cứu Streamlit trong skill trả 0 kết quả nên phần triển khai Streamlit dùng mặc định chung và luật repo.
- Quyết định senior: không lưu `design-system/.../MASTER.md` vào repo để giữ kho sạch; dùng kết quả tra cứu viết thẳng vào spec, kế hoạch và hợp đồng 007.

**Kiểm tra hiến chương bổ sung**:

| Cổng | Trạng thái | Bằng chứng |
|---|---|---|
| Tiếng Việt duy nhất cho người không chuyên | Đạt theo thiết kế | FR-014, FR-016, FR-020 bắt buộc nhãn, kết luận và tương phản dễ đọc. |
| An toàn dữ liệu local-first | Đạt theo thiết kế | Dùng lại đường gửi hiện có, không thêm egress; mail chỉ gửi sau khi duyệt. |
| Không fake PASS | Đạt theo quy trình | SC-007 tới SC-010 đo được; smoke trình duyệt và test tập trung bắt buộc. |

## Làm giàu màn hình đáp án 2026-09-21 (không tạo spec mới)

**Phạm vi mở rộng đã duyệt**: Câu chuyện 9 bong bóng hỏi đáp, Câu chuyện 10 ba bước chờ, Câu chuyện 11 cụm trích dẫn gọn. Chỉ CSS và render hiện có trong `workspace_chat_app.py` và `workspace_chat_ui.py`; không đổi luồng RAG, không cắt nội dung đáp án.

**Bối cảnh kỹ thuật bổ sung**:

- Tra cứu `ui-ux-pro-max` đã xác minh: bề rộng dòng 65–75 chữ, giãn dòng 1.5–1.75, bước tiến triển và phản hồi tải khớp thời gian chờ. Mẫu trích dẫn không có match trong kho skill nên dùng mặc định chung và ghi rõ là fallback.
- Bước chờ suy từ trạng thái thật: chờ tài liệu thì bước tìm nguồn chạy, AI đang xử lý thì bước tổng hợp chạy; không phần trăm giả.
- Quyết định senior: trích dẫn gộp một cụm thu gọn có đếm số lượng thay vì nhiều khung mở sẵn; đáp án dài hiện đầy đủ, chỉ giới hạn bề rộng dòng bằng CSS.
