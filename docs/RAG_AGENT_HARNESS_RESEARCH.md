# Nghiên Cứu Khung Điều Phối AI Agent Cho RAG (RAG Agent Harness Research)

Cổng: AIOS-RAG-AGENT-HARNESS-0  
Trạng thái: Chỉ nghiên cứu / thiết kế  
Ngày: 2026-06-28

## Tóm Tắt Tổng Quan (Executive Summary)

AIOS nên tiến hóa từ luồng sổ ghi chép / hỏi đáp cục bộ hữu ích hiện tại thành một hệ thống RAG trí nhớ công việc ưu tiên cục bộ (local-first). Kiến trúc tiếp theo không nên bắt đầu bằng một cơ sở dữ liệu vector hay đồ thị nặng nề. Trước hết, nó phải củng cố khả năng phân tích cú pháp tài liệu, metadata của chunk, truy xuất kết hợp cục bộ (hybrid retrieval), đóng gói bằng chứng, trích dẫn nguồn, chốt chặn quyền riêng tư và kỷ luật đo chuẩn benchmark.

Bài học cốt lõi từ các hệ thống RAG công khai là câu trả lời chất lượng cao bắt nguồn từ toàn bộ chuỗi mắt xích: bộ phân tích cú pháp, bảo toàn bố cục/bảng biểu/OCR, định danh chunk, tìm kiếm kết hợp, xếp hạng lại, gói bằng chứng, nén ngữ cảnh, từ chối trả lời khi thiếu dữ liệu và nhật ký kiểm toán. Lệnh gọi mô hình AI chỉ là một bước duy nhất trong chuỗi.

Bài học cốt lõi từ các công cụ agent/IDE là AIOS nên bắt đầu bằng quy trình an toàn: xuất prompt thủ công và lưu trữ câu trả lời dán ngược lại. Việc tự động hóa công cụ/IDE có thể được đưa vào sau thông qua các cổng phân quyền, sự phê duyệt tường minh, nhật ký kiểm toán và cơ chế hoàn tác (rollback).

## Kiểm Toán Khung Điều Phối và Truy Xuất Hiện Tại Của AIOS

### Nạp Dữ Liệu (Ingest)

Triển khai hiện tại bao gồm các hàm hỗ trợ trích xuất tài liệu cục bộ trong `src/aios_habit/document_extractors.py` và các luồng lập chỉ mục nguồn notebook trong `source_ingest.py`, `notebook_index.py`, cùng mã nguồn chỉ mục cục bộ đặc thù cho MOM.

Điểm mạnh hiện tại:
- Hỗ trợ nội dung nguồn dạng văn bản/markdown trong chỉ mục notebook.
- Bộ trích xuất tài liệu có các hàm xử lý cục bộ cho HTML, PPTX, Excel qua `openpyxl`, hình ảnh, PDF/ảnh với OCR cục bộ có giới hạn qua Tesseract khi có sẵn, và phân tích dựa trên XML/ZIP cho các tài liệu Office.
- Metadata của chunk đã bao gồm tệp nguồn, đường dẫn tương đối, loại tệp, phân đoạn, trang, trang chiếu, sheet, dải hàng, cấp độ bảo mật, tên bộ trích xuất, trạng thái trích xuất, engine OCR và ngôn ngữ OCR.
- Mặc định bảo mật ưu tiên cục bộ cho các chunk được trích xuất.

Hạn chế:
- Chỉ mục notebook hiện sử dụng các chunk cố định theo số ký tự và trích xuất từ khóa đơn giản.
- Cấu trúc tài liệu chưa được chuẩn hóa thành một schema chunk xuyên định dạng ổn định duy nhất cho tất cả các luồng QA phía sau.
- Xử lý Excel chỉ giới hạn ở mức xem trước và chưa mạnh mẽ cho việc truy xuất bảng đa sheet.
- OCR được giới hạn có chủ đích ở cục bộ nhưng chưa phải là một đường ống xử lý tài liệu quét (scanned document) độ trung thực cao.
- Ngữ nghĩa hình ảnh/sơ đồ chưa được hiểu sâu hơn ngoài các đánh dấu OCR/media.
- Chưa đạt tới mức truy xuất nhận biết bố cục tương đương NotebookLM.

### Truy Xuất (Retrieval)

Điểm mạnh hiện tại:
- `notebook_index.py` cung cấp khả năng tải/xây dựng chunk cục bộ và tìm kiếm từ khóa.
- Xếp hạng kết hợp cụm từ chính xác, tiêu đề, tên tệp và điểm tần suất token.
- Đã có các module chỉ mục/benchmark MOM cho việc đánh giá tài liệu chỉ dùng cục bộ.

Hạn chế:
- Chưa có nền tảng SQLite FTS/BM25.
- Chưa có chỉ mục vector.
- Chưa có xếp hạng kết hợp (hybrid ranking), xếp hạng lại (reranking), viết lại truy vấn (query rewrite), mở rộng từ đồng nghĩa hay lập kế hoạch truy vấn đa ngôn ngữ.
- Lọc metadata hạn chế và chưa có kiểm soát tính đa dạng của bằng chứng.
- Nhãn trích dẫn dựa trên nguồn/chunk nhưng chưa đủ ổn định cho việc kiểm chứng câu trả lời có căn cứ nguồn theo phong cách NotebookLM.
- Tìm kiếm nhiều tài liệu / nhiều vụ việc vẫn đang ở trạng thái `NOT_READY`.

### Câu Trả Lời (Answer)

Điểm mạnh hiện tại:
- Tồn tại phương án dự phòng tất định cục bộ.
- Có luồng trả lời qua provider qua `ai_router.py` và `ai_provider_bridge.py` cho tài liệu thường.
- Nhật ký định tuyến bao gồm trạng thái provider/model/lượt thử và liệu nội dung có bị gửi ra ngoài hay không.
- Luồng chuyển từ Hỏi đáp sang Vụ việc bảo tồn tóm tắt định tuyến và tham chiếu bằng chứng.
- Xử lý bảo mật chặn nội dung công ty/mật khỏi các tuyến cloud.

Hạn chế:
- Gói bằng chứng vẫn còn mang tính ngầm định; chưa có đối tượng gói bằng chứng hạng nhất với metadata về độ bao phủ / độ tin cậy / từ chối trả lời.
- Bộ soạn thảo câu trả lời chưa tách bạch rõ ràng sự thật đã biết, suy luận, bằng chứng còn thiếu và bằng chứng được khuyến nghị tiếp theo.
- Việc chấm điểm trích dẫn chưa tường minh.

### Cầu Nối Mô Hình / Agent (Agent / Model Bridge)

Điểm mạnh hiện tại:
- Đã có danh mục provider và router cho việc sử dụng provider có kiểm soát đối với tài liệu thường.
- Tóm tắt định tuyến và các lượt thử provider được theo vết.
- Thư mục gói xuất tồn tại dưới dạng artifact runtime bị bỏ qua, nhưng chưa có triển khai cầu nối IDE được commit.

Còn thiếu:
- Chưa có mô hình ID gói prompt.
- Chưa có quy trình xuất prompt thủ công được commit.
- Chưa có mô hình câu trả lời dán ngược lại với tên model/công cụ, ID prompt, tham chiếu bằng chứng, tóm tắt định tuyến, độ tin cậy và cảnh báo.
- Chưa có tầng adapter công cụ / IDE.
- Chưa có khung điều phối agent với trạng thái tác vụ, phân quyền, nén ngữ cảnh, ủy quyền tác vụ con, hoàn tác hay bàn giao.

Vì sao model miễn phí / cấp thấp là chưa đủ:
- Tài liệu công việc phức tạp sẽ thất bại khi bộ phân tích, chia chunk, truy xuất hoặc lựa chọn bằng chứng bị yếu.
- Model miễn phí / cấp thấp hữu ích cho ghi chú công khai rủi ro thấp nhưng không thể bảo đảm phân tích có căn cứ cho bảng biểu, tài liệu scan, vụ việc đa bước (multi-hop) hay quy trình công ty/mật.
- Model mạnh nên được sử dụng thông qua các gói prompt có căn cứ bằng chứng và nhận biết quyền riêng tư, không phải tải lên tài liệu thô.

## Ma Trận Mẫu Thiết Kế / Repository Bên Ngoài

| Mục tiêu | Mục đích | Ý tưởng hữu ích cho AIOS | Không sao chép | Độ khó | Rủi ro quyền riêng tư | Độ phù hợp Cục bộ | Giá trị |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RAGFlow | RAG tài liệu chuyên sâu với parsing, hybrid search, rerank, citations | Parsing ưu tiên bố cục/bảng biểu/OCR, tìm kiếm kết hợp, xếp hạng lại, trích dẫn có thể theo vết | Không sao chép mã nguồn hay triển khai stack nặng nề một cách mù quáng | CAO | TRUNG BÌNH | TRUNG BÌNH | CAO |
| kotaemon | UI/Framework QA tài liệu riêng tư / cục bộ | Triển khai cục bộ, truy xuất kết hợp, UX trích dẫn PDF, các thành phần module hóa | Không sao chép UI hay cấu hình provider | TRUNG BÌNH | TRUNG BÌNH | CAO | CAO |
| Microsoft GraphRAG | Suy luận tập văn bản toàn cục / cục bộ dựa trên đồ thị | Tóm tắt cộng đồng, tìm kiếm toàn cục vs cục bộ, đồ thị như một tầng làm sau | Không đưa Graph DB vào lúc này | CAO | CAO nếu lập chỉ mục LLM bằng cloud | TRUNG BÌNH | TB-CAO sau này |
| LightRAG | Truy xuất vector + đồ thị gọn nhẹ | Ý tưởng hai tầng, truy xuất quan hệ thực thể | Không thêm vector/graph trước cổng FTS cục bộ | TRUNG BÌNH | TRUNG BÌNH | TRUNG BÌNH | TRUNG BÌNH |
| LlamaIndex | Framework quy trình RAG/Agent | Lập kế hoạch truy vấn, bộ truy xuất, trừu tượng bộ nhớ, workflows | Không import framework cồng kềnh khi chưa cần | TRUNG BÌNH | TRUNG BÌNH | TRUNG BÌNH | CAO (tham chiếu thiết kế) |
| Haystack | Các thành phần pipeline RAG sản xuất | Ranh giới pipeline/component, kỷ luật đánh giá | Không thiết kế thừa quá sớm | TRUNG BÌNH | TRUNG BÌNH | CAO với thành phần cục bộ | CAO |
| Docling | Chuyển đổi tài liệu với bố cục/bảng biểu/OCR | Biểu diễn tài liệu thống nhất, đường ống bố cục/bảng biểu/OCR | Không thêm cloud OCR hay model nặng theo mặc định | TRUNG BÌNH | THẤP nếu chạy cục bộ | CAO | CAO |
| Unstructured | Đường ống nạp / phân vùng dữ liệu | Phân vùng thành các phần tử định kiểu, chunk giàu metadata | Không gửi tài liệu nhạy cảm lên dịch vụ cloud | TRUNG BÌNH | TRUNG BÌNH | CAO nếu chạy cục bộ | CAO |
| OpenHands | Nền tảng coding agent tự hành | Runtime cô lập, task logs, ranh giới thực thi công cụ | Không cho phép ghi tự hành | CAO | CAO | TRUNG BÌNH | TRUNG BÌNH |
| Aider | Trợ lý lập trình terminal bản địa Git | Vòng lặp thay đổi nhận biết Git, kỷ luật diff/commit | Không tự động commit việc của người dùng khi chưa có gate | THẤP-TB | TRUNG BÌNH | CAO | TRUNG BÌNH |
| Cline | Agent IDE với Plan/Act và phân quyền | Phê duyệt rõ ràng cho chỉnh sửa tệp, lệnh, hành động trình duyệt | Không bỏ qua sự phê duyệt của con người | TRUNG BÌNH | TB-CAO | CAO | CAO |
| Continue | Framework trợ lý tích hợp IDE | Bộ cung cấp ngữ cảnh, định tuyến model, tích hợp IDE | Không rò rỉ tệp nhạy cảm vào ngữ cảnh | TRUNG BÌNH | TRUNG BÌNH | CAO | TB-CAO |
| Goose | Agent độc lập với trình biên tập | Ủy quyền tác vụ, trừu tượng hóa công cụ | Không cấp quyền công cụ quá rộng | TRUNG BÌNH | CAO | TRUNG BÌNH | TRUNG BÌNH |
| OpenCode | Các mẫu coding agent terminal/IDE | Quy trình CLI và ranh giới công cụ nếu liên quan | Không ghép chặt AIOS vào một công cụ | TRUNG BÌNH | TRUNG BÌNH | TRUNG BÌNH | THẤP-TB |
| LangGraph | Đồ thị agent đa tác nhân có trạng thái | State machine, checkpointing, các nút phê duyệt của con người | Chưa thêm runtime đồ thị phức tạp | TRUNG BÌNH | TRUNG BÌNH | CAO nếu chạy cục bộ | CAO (tham chiếu thiết kế) |
| Semantic Kernel | Plugin, bộ nhớ, trừu tượng lập kế hoạch | Hợp đồng plugin và ranh giới kỹ năng/công cụ | Không tạo đường dẫn plugin cloud cho dữ liệu công ty/mật | TRUNG BÌNH | TRUNG BÌNH | TRUNG BÌNH | TRUNG BÌNH |
| Cognee | Đồ thị / RAG ưu tiên bộ nhớ | Pipeline Cognify, ý tưởng bộ nhớ đồ thị | Không thêm Graph DB trước khi có nhu cầu bằng chứng | CAO | TRUNG BÌNH | TRUNG BÌNH | TRUNG BÌNH sau này |
| Letta/MemGPT | Hệ điều hành bộ nhớ cho Agent | Các tầng bộ nhớ và khái niệm bộ nhớ tự chỉnh sửa | Không để agent tự ý sửa bộ nhớ trong âm thầm | CAO | CAO | TRUNG BÌNH | CAO về mặt khái niệm |

## Kiến Trúc Công Cụ Truy Xuất AIOS v2 (Retrieval Engine v2)

### 1. Bộ Chuyển Đổi Phân Tích Tài Liệu (Document Parser Adapter)

Mục tiêu: chuyển đổi đầu vào thành các phần tử cục bộ có định kiểu trong khi vẫn bảo tồn cấu trúc.

Yêu cầu:
- Các đánh dấu: trang, phần, tiêu đề, đoạn văn, bảng, sheet, ô, trang chiếu, hình ảnh và OCR;
- ID tài liệu và đường dẫn nguồn ổn định;
- Các trường trạng thái bộ trích xuất và cảnh báo;
- Mặc định chỉ dùng cục bộ cho dữ liệu công ty/mật;
- Không dùng cloud OCR trừ khi được phê duyệt rõ ràng và không nhạy cảm.

Bước đầu tiên khuyến nghị: điều chỉnh đầu ra hiện tại của `document_extractors.py` thành một schema phần tử chuẩn hóa mà không cần thay thế toàn bộ stack trích xuất.

### 2. Bộ Xây Dựng Chunk & Metadata (Chunk & Metadata Builder)

Metadata bắt buộc:
- ID chunk ổn định;
- ID tài liệu nguồn;
- Tiêu đề nguồn và đường dẫn tương đối;
- Dải trang / sheet / phân đoạn / trang chiếu / bảng / ô;
- Cờ văn bản / bảng / hình ảnh / OCR;
- Chế độ riêng tư (privacy mode);
- Thời gian tạo;
- Mã băm / checksum của nguồn;
- Nhãn trích dẫn;
- Bộ trích xuất và trạng thái;
- ID chunk cha / lân cận để mở rộng phân đoạn.

### 3. Chỉ Mục Kết Hợp Cục Bộ (Local Hybrid Index)

Giai đoạn 4 nên bắt đầu với SQLite FTS/BM25 và các bảng metadata.

Thiết kế ban đầu:
- Bảng `documents`;
- Bảng `chunks`;
- Bảng ảo `chunk_fts`;
- Bảng `chunk_metadata` hoặc cột JSON;
- Tái tạo cục bộ và cập nhật tăng dần theo mã băm nguồn;
- Tuyệt đối không gửi embedding lên cloud cho dữ liệu công ty/mật.

Tìm kiếm vector tùy chọn chỉ nên đưa vào sau khi đã đo lường được các khoảng cách của đo chuẩn benchmark FTS/BM25.

### 4. Bộ Lập Kế Hoạch Truy Vấn (Query Planner)

Trách nhiệm:
- Chuẩn hóa các thuật ngữ Tiếng Việt / Tiếng Nhật / Tiếng Anh;
- Mở rộng từ đồng nghĩa chuyên ngành cho MOM/WMS/Opcenter/InterStock;
- Sinh ra nhiều biến thể truy vấn;
- Quyết định xem câu hỏi thuộc dạng tra cứu, so sánh, quy trình, nguyên nhân gốc rễ, tóm tắt hay truy vấn thiếu bằng chứng;
- Chọn bộ lọc metadata và giới hạn ứng viên.

### 5. Bộ Truy Xuất + Bộ Xếp Hạng Lại (Retriever + Reranker)

Truy xuất ban đầu:
- Tìm kiếm ứng viên bằng FTS/BM25;
- Tăng điểm (boost) cho tên tệp / tiêu đề / nguồn;
- Bộ lọc metadata;
- Tăng điểm cho mã định danh chính xác;
- Mở rộng phân đoạn;
- Loại bỏ trùng lặp;
- Đảm bảo tính đa dạng xuyên tài liệu / trang / sheet.

Xếp hạng lại sau này:
- Bộ xếp hạng lại cục bộ dạng cross-encoder hoặc heuristic gọn nhẹ trước tiên;
- Xếp hạng lại bằng provider tùy chọn chỉ dành cho tài liệu không nhạy cảm và có phê duyệt rõ ràng.

### 6. Bộ Xây Dựng Gói Bằng Chứng (Evidence Pack Builder)

Các trường trong gói bằng chứng:
- ID gói;
- Câu truy vấn;
- Các đoạn trích bằng chứng hàng đầu;
- ID trích dẫn;
- Tham chiếu nguồn;
- Chi tiết điểm số;
- Tóm tắt độ bao phủ;
- Cảnh báo thiếu bằng chứng;
- Cờ chưa đủ bằng chứng;
- Chế độ riêng tư;
- Tuyến trả lời được phép.

Gói này trở thành đầu vào cho câu trả lời cục bộ, câu trả lời provider, xuất prompt và chuyển từ Hỏi đáp sang Vụ việc.

### 7. Bộ Soạn Thảo Câu Trả Lời (Answer Composer)

Định dạng câu trả lời:
- Câu trả lời trực tiếp;
- Sự thật có bằng chứng chứng minh;
- Suy luận / giả thuyết được gắn nhãn rõ ràng;
- Trích dẫn cho từng tuyên bố;
- Mục bằng chứng còn thiếu / không thể trả lời;
- Thông tin provider/model trong nhật ký định tuyến;
- Tóm tắt đính kèm vào vụ việc.

Quy tắc:
- Từ chối trả lời nếu chưa đủ bằng chứng;
- Tuyệt đối không tuyên bố tương đương NotebookLM cho đến khi benchmark đạt;
- Tuyệt đối không gửi bằng chứng công ty/mật ra bên ngoài.

### 8. Khung Đo Chuẩn Benchmark (Benchmark Harness)

Các tầng đo chuẩn:
- Smoke 20 câu hỏi;
- Cổng 50 câu hỏi;
- Hồi quy 100 câu hỏi.

Chỉ số đo lường:
- Độ chính xác;
- Độ chính xác của trích dẫn;
- Tỷ lệ ảo giác (hallucination);
- Độ bao phủ;
- Khả năng phát hiện thiếu bằng chứng;
- Hành vi bảo mật;
- Độ trễ;
- Tính hữu ích của câu trả lời.

So sánh:
- So sánh AIOS vs NotebookLM chỉ trên cùng tài liệu / câu hỏi công khai / không nhạy cảm;
- Không đưa ra tuyên bố tương đương giả mạo.

## Kiến Trúc Cầu Nối Câu Trả Lời IDE Của AIOS

### Chế Độ A — Xuất Prompt (Prompt Export)

AIOS tạo một gói prompt có căn cứ bằng chứng bao gồm:
- Mục tiêu / câu hỏi;
- Gói bằng chứng;
- Tham chiếu nguồn;
- Các hành động được phép;
- Chế độ riêng tư;
- Định dạng câu trả lời kỳ vọng;
- Cảnh báo và các phi mục tiêu.

Quyền riêng tư:
- Công ty/mật: chỉ dùng cục bộ / model tin cậy; chặn xuất ra bên ngoài trừ khi người dùng đánh dấu an toàn tường minh;
- Tài liệu thường: cho phép xuất prompt an toàn cho cloud.

### Chế Độ B — Dán Ngược Câu Trả Lời (Paste-back Answer)

Người dùng dán kết quả đầu ra từ Codex/Gemini/Claude/GPT/Opus/IDE.

AIOS lưu trữ:
- Tên model / công cụ;
- ID gói prompt;
- Câu trả lời;
- Tham chiếu bằng chứng;
- Tóm tắt định tuyến;
- Đã dùng AI ngoài hay chưa (Có/Không);
- Cảnh báo / Độ tin cậy;
- Liên kết vụ việc;
- Thời gian tạo.

### Chế Độ C — Adapter Công Cụ / IDE Sau Này

Các adapter có thể bao gồm:
- Adapter CLI Codex;
- Adapter API/CLI Gemini;
- Adapter API/CLI Claude;
- Adapter tương thích OpenAI;
- Adapter chỉ dùng cục bộ.

Quy tắc:
- Cổng phê duyệt trước khi chỉnh sửa tệp / hành động;
- Không tự động ghi tệp khi chưa có sự phê duyệt của người dùng;
- Không để lộ secret thô trong log;
- Không gọi provider cho dữ liệu công ty/mật trừ khi thỏa mãn quy tắc tin cậy / cục bộ.

### Chế Độ D — Khung Điều Phối Agent (Agent Harness)

Trạng thái khung điều phối:
- Trạng thái tác vụ;
- Trạng thái bằng chứng;
- Quyền công cụ;
- Nén ngữ cảnh;
- Ủy quyền tác vụ con;
- Nhật ký kiểm toán;
- Hoàn tác / Bàn giao;
- Danh mục kiểm tra nghiệm thu cuối cùng.

Nguyên tắc thiết kế: AIOS nên học hỏi từ các vòng lặp kiểu Claude-Code, cổng phê duyệt của Cline, kỷ luật Git của Aider, tính cô lập của OpenHands, trạng thái của LangGraph và các tầng bộ nhớ của Letta mà không sao chép mã nguồn hay đánh mất quyền kiểm soát ưu tiên cục bộ.

## Mô Hình Quyền Riêng Tư (Privacy Model)

Các chế độ riêng tư:
- `local_only`: tuyệt đối không xuất lên cloud / provider;
- `cloud_safe`: cho phép đối với tài liệu thường;
- `trusted_internal`: chỉ cho phép đối với endpoint cục bộ / tin cậy được cấu hình rõ ràng;
- `redacted_export`: chỉ các đoạn trích đã làm sạch mới được xuất.

Các chốt chặn bắt buộc:
- Chế độ an toàn rõ ràng trên từng gói bằng chứng;
- Kiểm tra xuất prompt;
- Gắn nhãn câu trả lời dán ngược lại;
- Nhật ký định tuyến ghi rõ việc gửi ra ngoài (Có/Không);
- Không hiển thị API key;
- Không lưu trữ payload provider thô trừ khi an toàn và được phê duyệt;
- Các artifact runtime bị bỏ qua luôn nằm ngoài theo dõi của Git.

## Các Cổng Triển Khai (Implementation Gates)

1. **AIOS-RAG-INGEST-1**
   - Chỉ cải thiện metadata bộ phân tích / chunk.
   - Chưa dùng Vector DB.
   - Chưa dùng Cloud OCR.
   - Kiểm thử cho tham chiếu PDF/Excel/PPTX/ảnh/nguồn.

2. **AIOS-RAG-SEARCH-1**
   - Nền tảng kết hợp cục bộ SQLite FTS/BM25.
   - Bộ lọc metadata.
   - Kiểm thử xếp hạng.
   - Không phụ thuộc model bên ngoài.

3. **AIOS-RAG-EVIDENCE-PACK-1**
   - Bộ tạo gói bằng chứng.
   - Chấm điểm nguồn.
   - Xử lý khi chưa đủ bằng chứng.
   - Đính kèm gói vào câu trả lời / vụ việc.

4. **AIOS-IDE-BRIDGE-1**
   - Xuất prompt thủ công.
   - Dán ngược câu trả lời.
   - Lưu tóm tắt model/công cụ/bằng chứng/tuyến.
   - Chưa tự động hóa API.

5. **AIOS-RAG-BENCHMARK-1**
   - So sánh AIOS vs NotebookLM trên cùng tài liệu / câu hỏi không nhạy cảm.
   - Không tuyên bố tương đương giả mạo.

Sau này:
- AIOS-RAG-RERANK-1;
- AIOS-CASE-SCALE-1;
- AIOS-WORKSTREAM-MAP-1;
- AIOS-P1-READINESS-CHECKLIST.

## Rủi Ro (Risks)

- Xây dựng thừa thãi stack đồ thị / vector trước khi đo lường đường cơ sở FTS cục bộ.
- Đánh mất tính an toàn ưu tiên cục bộ do đưa cloud OCR / embedding / rerank vào quá sớm.
- Tuyên bố tương đương giả mạo so với NotebookLM trước khi có bằng chứng benchmark.
- Xuất prompt vô tình làm lộ bằng chứng công ty/mật.
- Tự động hóa agent tự ý chỉnh sửa tệp hoặc chạy công cụ mà không có sự phê duyệt.
- Các artifact runtime hoặc secret bị vô tình theo dõi trong Git.

## Các Phi Mục Tiêu Rõ Ràng (Explicit Non-goals)

- Không triển khai mã nguồn trong cổng này.
- Chưa thêm Vector DB hay Graph DB lúc này.
- Không gọi provider / cloud.
- Không đọc hay in API key.
- Không mở P1.0.
- Không tuyên bố tương đương NotebookLM.
- Không sao chép mã nguồn độc quyền / rò rỉ.
- Không dùng công cụ ML / dự đoán.

## Khuyến Nghị (Recommendation)

Tiến hành với `AIOS-RAG-INGEST-1` trước tiên. Bước đi có đòn bẩy cao nhất tiếp theo là chuẩn hóa đầu ra của parser và metadata của chunk để mọi tính năng sau này đều có thể dựa vào ID tài liệu/chunk ổn định, trích dẫn, cờ bảo mật và cấu trúc nguồn. Sau đó thêm tìm kiếm SQLite FTS/BM25, gói bằng chứng, cầu nối IDE thủ công, và chỉ sau đó mới thực hiện đo chuẩn benchmark so với NotebookLM.

