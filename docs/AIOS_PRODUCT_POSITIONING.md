# Định Vị Sản Phẩm AIOS (AIOS Product Positioning)

Canonical cho định vị / giai đoạn / “AIOS không phải”. Nguyên tắc tối cao và PASS/FAIL: `CONSTITUTION.md`. Lối vào agent: `AGENTS.md`. `PRODUCT_NORTH_STAR.md` chỉ là stub về đây.

## Sứ Mệnh (Mission)

AIOS WorkLens / AIOS_habbit là một **hệ điều hành trí nhớ công việc cá nhân, ưu tiên cục bộ (local-first)**. Mục tiêu là biến bằng chứng công việc hằng ngày thành tri thức có thể tái sử dụng:

```text
Vụ việc (Case) → Bằng chứng (Evidence) → Bản đồ (Map) → Hành động (Action) → Học hỏi (Learning) → Bộ nhớ (Memory)
```

AIOS không chỉ đơn thuần là công cụ hỏi đáp tài liệu. AIOS phải giúp người dùng làm việc thực tế với tài liệu, Excel, hình ảnh, log, chat, email, kết quả đầu ra của AI và các sự việc hằng ngày; sau đó lưu lại mô hình làm việc, bài học, bằng chứng (evidence), nhật ký định tuyến (route log), chế độ riêng tư (privacy mode) và công cụ/model đã sử dụng.

## AIOS Không Phải Là

- Không phải là công cụ sao lưu đoạn chat đơn thuần.
- Không phải là chatbot RAG đơn giản.
- Không phải chỉ là bản sao chép (clone) của NotebookLM.
- Không phải là công cụ dự đoán vận hành sản xuất thực tế.
- Không phải là công cụ tải tài liệu công ty lên đám mây.
- Không phải là hệ thống truy xuất nguồn gốc chỉ dành riêng cho LSU.

## Nguyên Tắc Sản Phẩm (Product Principles)

- Không lưu toàn văn hội thoại nếu không cần thiết; ưu tiên lưu tri thức đã được cấu trúc hóa.
- Không chỉ lưu câu chữ bề nổi; lưu trữ mô hình làm việc, quyết định và bài học kinh nghiệm.
- Không phụ thuộc riêng vào ChatGPT, Gemini, Claude, NotebookLM hay DeepSeek.
- Dữ liệu công ty/mật mặc định ở chế độ ưu tiên cục bộ và tuyệt đối không gửi ra ngoài.
- Mọi câu trả lời quan trọng bắt buộc phải truy xuất được nguồn bằng chứng, nhật ký định tuyến, model/công cụ đã dùng và chế độ bảo mật.
- Model mạnh chỉ là một phần; chất lượng thực sự phụ thuộc vào bộ phân tích cú pháp (parser), chỉ mục (index), truy xuất (retrieval), xếp hạng lại (rerank), gói bằng chứng (evidence pack), ngữ cảnh và chốt chặn quyền riêng tư.

## Trạng Thái Hiện Tại (Current Status)

- Giai đoạn 0 — Tầm nhìn & Quản trị: ĐẠT (DONE).
- Giai đoạn 1 — Nền tảng Local Case Cockpit: ĐẠT (DONE).
- Giai đoạn 2 — Nền tảng Tài liệu thực tế / MOM: ĐẠT KÈM CẢNH BÁO (DONE_WITH_WARNINGS).
- Giai đoạn 3 — An toàn Provider + Giao diện hằng ngày: ĐẠT KÈM CẢNH BÁO (DONE_WITH_WARNINGS).
- Vị trí hiện tại: cuối Giai đoạn 3, trước Giai đoạn 4 RAG Engine v2 và Giai đoạn 5 Cầu nối IDE/model.
- P1.0: ĐÃ KHÓA (LOCKED), chưa mở.
- Tương đương năng lực NotebookLM (NotebookLM parity): chưa đạt và tuyệt đối không giả mạo.
- Cầu nối IDE/model: chưa triển khai.

## Lộ Trình Giai Đoạn (Phase Roadmap)

### Giai Đoạn 4 — RAG Engine v2 / Truy Xuất Tương Đương NotebookLM

Trạng thái: KẾ TIẾP (NEXT).

Phạm vi:
- Bộ chuyển đổi parser tốt hơn
- Chunk dữ liệu nhận biết cấu trúc
- SQLite FTS / BM25
- Embedding tùy chọn sau này
- Tìm kiếm kết hợp (hybrid search)
- Xếp hạng lại (rerank)
- Viết lại câu truy vấn (query rewrite)
- Gói bằng chứng (evidence pack)
- Chấm điểm trích dẫn (citation scoring)
- Đo chuẩn benchmark theo phong cách NotebookLM

Chưa được phép:
- Sử dụng Vector DB nặng nề khi chưa có quyết định kiến trúc
- Gửi embedding lên cloud đối với dữ liệu công ty / bí mật
- Tuyên bố giả mạo về việc đạt độ tương đương với NotebookLM

### Giai Đoạn 5 — Cầu Nối Mô Hình Mạnh / IDE (IDE / Strong Model Answer Bridge)

Trạng thái: KẾ TIẾP SONG SONG (NEXT_PARALLEL).

Phạm vi:
- Xuất gói prompt
- Sử dụng Codex/Gemini/Claude/GPT/Opus trong IDE/chat bên ngoài
- Dán câu trả lời ngược trở lại (paste-back)
- Lưu tên model/công cụ đã sử dụng
- Lưu tham chiếu bằng chứng
- Lưu tóm tắt định tuyến
- Chốt chặn bảo vệ quyền riêng tư

Chưa được phép:
- Gọi API trực tiếp lên cloud đối với dữ liệu công ty / bí mật
- Để lộ API key thô trong UI/log
- Cho phép AI tự động chỉnh sửa mà không có sự phê duyệt

### Các Giai Đoạn Tiếp Theo

- Giai đoạn 6 — Bộ nhớ vụ việc theo quy mô lớn (Case Memory at Scale).
- Giai đoạn 7 — Bản đồ luồng công việc / Đồ thị tri thức (Work Stream Map / Knowledge Graph).
- Giai đoạn 8 — Học tập chuyên sâu / Hệ điều hành cá nhân (Senior Learning / Personal OS).
- Giai đoạn 9 — Nền tảng truy xuất nguồn gốc sản xuất (xem [Tầm nhìn trí tuệ sản xuất](design/PRODUCTION_INTELLIGENCE_VISION.md); chỉ là tài liệu tham khảo thiết kế, chưa mở).
- Giai đoạn 10 — Sẵn sàng phát hành Production P1.0.

## Nguồn Tham Khảo Nghiên Cứu Thiết Kế Tương Lai

Chỉ sử dụng các mẫu thiết kế công khai; tuyệt đối không sao chép mã nguồn rò rỉ / độc quyền.

- RAGFlow
- kotaemon
- Microsoft GraphRAG
- LightRAG
- LlamaIndex
- Haystack
- Docling
- Unstructured
- OpenHands
- Aider
- Cline
- Continue
- Goose
- Cognee
- Letta / MemGPT
- LangGraph
- Semantic Kernel

## Hàng Đợi Cổng Tiếp Theo (Next Gate Queue)

Trước mắt:
1. `AIOS-RAG-AGENT-HARNESS-0` — nghiên cứu các mẫu khung điều phối RAG + Claude-Code, chỉ tài liệu.
2. `AIOS-RAG-INGEST-1` — cải thiện metadata bộ phân tích/chunk, chưa dùng vector DB.
3. `AIOS-RAG-SEARCH-1` — nền tảng tìm kiếm kết hợp cục bộ, SQLite FTS/BM25, lọc metadata, ID trích dẫn.
4. `AIOS-RAG-EVIDENCE-PACK-1` — bộ tạo gói bằng chứng, chấm điểm nguồn, từ chối trả lời khi thiếu dữ liệu.
5. `AIOS-IDE-BRIDGE-1` — xuất prompt thủ công, dán câu trả lời ngược lại, lưu log model/công cụ/bằng chứng/tuyến.

Sau này:
6. `AIOS-RAG-RERANK-1`
7. `AIOS-RAG-BENCHMARK-1`
8. `AIOS-CASE-SCALE-1`
9. `AIOS-WORKSTREAM-MAP-1`
10. `AIOS-P1-READINESS-CHECKLIST`

