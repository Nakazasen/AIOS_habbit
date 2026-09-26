# Ticket E1 — Điều tra khâu tổng hợp làm rớt dữ kiện

Ngày chạy: 2026-09-26. Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Mã nguồn lúc chạy: `ae3901125f446ee2c66c024b5582736fa1795d74`.

## Kết luận

- **B1 và B3:** dữ kiện đúng có trong các chunk thân đã truy xuất và nằm trong evidence pack. Không bị loại bởi lọc sau retrieval, rerank hay cắt ngắn đoạn đáp án. Khâu tổng hợp cục bộ chỉ phát tối đa 5 claim; 5 claim đầu đều lấy từ 5 `document_summary` được chèn lên đầu kết quả. Vì vậy các chunk thân chứa đáp án không được chọn. Với B3, ngay cả phần summary cũng có câu Nhật `nvarchar(4000)`, nhưng bộ chọn đoạn ưu tiên phần mô tả tiếng Việt khớp từ truy vấn hơn.
- **B5:** không phải chunking cắt mất và cũng không phải chunk đáp án không tồn tại. Chunk 371 ký tự chứa trọn `HOUSE_METHOD`, `'0'` và `'1'`, được đánh dấu retrievable và có vector ONNX. Nhưng truy vấn hybrid không đưa chunk này vào tập kết quả. Truy vấn lexical đầy đủ xếp chunk ở hạng **467**, trong khi cửa sổ lexical của lượt hybrid là 100 ứng viên. Đây là hụt ở tầng lấy/xếp hạng ứng viên; không có reranker chạy sau đó.
- **Prompt:** không có prompt nào được gửi đến mô hình bên ngoài. Lượt chạy dựng yêu cầu tổng hợp, nhưng bộ định tuyến chặn trước khi gửi vì không xác định chắc loại tài liệu. Kết quả cuối đến từ bộ tổng hợp trích xuất cục bộ, không phải câu trả lời do mô hình viết. Vì vậy không thể quy B1/B3 cho một prompt LLM đã thực sự được gửi.
- Không sửa mã, không ingest, không ghi index. Chỉ đề xuất hướng sửa ở cuối báo cáo.

## Cấu hình và xác nhận chỉ đọc

- Index: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`.
- Mô hình: BGE-M3 ONNX fp32, revision `5617a9f61b028005a4858fdac845db406aefb181`, fingerprint `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`.
- Cờ chạy: `BGE_BACKEND=onnx`, `AIOS_RAG_V2_SUMMARY_FIRST=1`, `AIOS_RAG_V2_SUMMARY_PROVENANCE=1`, `index_read_only=True`, `ensure_embeddings_on_open=False`.
- 74 nguồn đã có trong index được chọn làm phạm vi truy vấn; không gọi ingest.
- Khởi tạo mô hình: 31,14 giây. B1: 2,68 giây; B3: 1,37 giây; B5 kiểm tra thêm: 1,04 giây.
- Trước và sau: 29.851.648 byte, 1.272 chunk, 1.064 chunk retrievable, 74 tài liệu; `integrity_check=ok`. Ảnh chụp trước/sau giống hệt.
- Nhật ký JSONL đầy đủ, gồm mọi kết quả, chunk ID và toàn văn evidence pack, contract, ngữ cảnh prompt dựng tại chỗ và câu trả lời: `C:/Users/Admin/AppData/Local/Temp/e1_rerun_b1b3b5.jsonl`. Nhật ký không đưa vào Git vì chứa toàn văn tài liệu nguồn. Lượt chạy dùng `D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe scratch/e1_rerun_b1b3.py`; script chỉ dùng cho lượt điều tra và đã xóa sau đó.

## B1 — Dữ kiện có trong evidence nhưng không thành câu trả lời

Câu hỏi: Trong sự cố đâm đụng robot ACR xảy ra ngày 16–17/6/2026 khi xuất kho thủ công, hai thùng Oricon cũ còn nằm thực tế trên giá là mã nào và thùng Oricon mới bị robot đẩy đâm vào là mã nào?

- Hybrid trả 15 kết quả, tạo 20 mục kết quả sau xử lý ngữ cảnh; evidence pack giữ 18 mục. Đường chạy `hybrid`; `reranker_requested=False`, `reranker_applied=False`.
- Hai chunk có đáp án là `[6]` `53bf4f4f8cf30142035122b9c651f1a1aadd5338155498baeb36b7be2ee5e593` (742 ký tự) và `[7]` `719282451ec7800ba771f470c0901fb3b27023d8632430a9d0402644288566d1` (958 ký tự). Cả hai đều nằm trong evidence pack. Nội dung nêu `11922`, `12860`, `12626`.
- Năm mục đầu của evidence pack đều là summary của năm tài liệu khác nhau. Kết quả cục bộ chỉ cite `[1]`–`[5]`, không cite `[6]`/`[7]`.

Trích dẫn dưới đây cho thấy các mã cần thiết trong chunk thân; phần văn bản được lược bớt. Nhật ký JSONL lưu nguyên văn toàn bộ evidence pack:

```text
[719282451ec7800ba771f470c0901fb3b27023d8632430a9d0402644288566d1]
Trang tính: Xuất kho A1=Chi tiết lỗi Xuất kho thủ công | F1=Ngày 16,17/6/2026 A3=Ban đầu: Thùng Oricon ....11922 và ...12860 đang nằm trên giá kệ, hệ thống quản lý kho WMS (Inter-Stock) ghi nhận tọa độ này đang "Có hàng". A5=1. Xuất kho thủ công: Dùng chức năng "Manual Supply Line" trên Opcenter để xuất 2 thùng này. […]

Chunk `[6]` tiếp tục nêu thùng mới `...12626` bị đẩy vào vị trí đang bị chiếm bởi `...11922`; phần sau nêu xử lý tạm thời và hai thùng cũ `...11922`/`...12860`. Xem toàn văn trong JSONL.
```

Câu trả lời thực tế:

```text
- Bộ phận đã tạo raBộ phận Công nghệ Sản xuất Phòng Kỹ thuật Sản xuất số 2, Ban Kỹ thuật Sản xuất 21 Được tạo bởi: Kazuma Tsutsumi Chuỗi tiêu đề Công ty TNHH Giải pháp Tài liệu KYOCERA Văn bản chân trang Bộ điều khiển xử lý vật liệu Phiên bản <0.01> Hướng dẫn sử dụng (Matecon) - Dùng để điều khiển AGV / ACR / CTU - 作成 審査 承認 Confidential © 2022 KYOCERA Document Solutions Inc. [1]
- MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [2]
- Xử lý ngày 17.06.2026: Đối với nhóm 1, in lại EDI(xóa thông tin Lot sản xuất), xóa dữ liệu đã đọc vào trên SQL và MOM, tiến hành nhập kho lại. [3]
- == Thông tin về quy trình sản xuất ST-CO- Đến đăng ký Ngày phát sinh/ghi nhận: Áp dụng cho các lỗi ST/CO và thực tích phát sinh trong quá trình sản xuất AMS; file hiện tại chưa ghi ngày cụ thể cho từng bước. [4]
- à máy" varchar(3) BUILDING "Tòa nhà" varchar(2) FLOOR "Tầng" varchar(5) LINE "Chuyền" varchar(9) WORKER_ID "ID Công nhân" varchar(26) TRACEABILITY_ID "Mã truy vết" varchar(16) PROCESS_ID "Mã công đoạn" varchar(3) PROCESS_NUMBER "Số thứ tự CĐ" varch... [5]
LIMITATIONS: incomplete_query_term_coverage
```

## B3 — Kiểu giới hạn có trong evidence nhưng bị rơi

Câu hỏi: Khi liên kết thực tích tiêu hao khoảng 150 item linh kiện từ MOM sang SAP/R3 qua bảng `T_IF_PROD_RESULT`, lỗi không lưu được dữ liệu phát sinh do kiểu khai báo XML trong stored procedure bị giới hạn ở độ dài bao nhiêu ký tự?

- Hybrid trả 15 kết quả, evidence pack có 15 mục. Đường chạy `hybrid`; không yêu cầu và không áp reranker.
- Evidence `[6]` `5231825b5cc94bf630e36bb3fd40fbb3df7f0f2bd77707cfcbb06a41c6ae7d10` (593 ký tự), `[7]` `174b38784a312bc05f0cdf0e996aadf38c70d7c590ef590efbea49bf295938d4` (227 ký tự) và `[8]` `0a4997ef9757a3421d4e3f7b6f8bf3354c4e4190d7e6b552da063d5209ba2f63` (310 ký tự) đều chứa thông tin về giới hạn. Summary `[4]` `wsc-c0cfb5bb4e58b93f4ac06c76-summary` cũng có đoạn nguồn Nhật ghi `nvarchar(4000)`.
- Câu trả lời chỉ lấy năm summary `[1]`–`[5]`; không lấy chunk thân `[6]`–`[8]`.

Toàn văn chunk tiếng Việt có đáp án:

```text
[5231825b5cc94bf630e36bb3fd40fbb3df7f0f2bd77707cfcbb06a41c6ae7d10]
1. LỖI LIÊN QUAN ĐẾN T_IF_PROD_RESULT VÀ XML TIÊU HAO LINH KIỆN ------------------------------------------------------------ Ngày phát sinh/ghi nhận: Chưa xác định ngày cụ thể trong dữ liệu hiện có; ghi nhận khi VN liên kết khoảng 150 item tiêu hao và XML vượt 4000 ký tự. Hiện tượng: - Khi liên kết thực tích hoàn thành lắp ráp và thực tích tiêu hao linh kiện từ MOM sang R3 thông qua bảng T_IF_PROD_RESULT, dữ liệu XML có thể vượt quá 4000 ký tự. - Trong một số trường hợp VN có khoảng 150 item tiêu hao, XML vượt quá giới hạn nvarchar(4000), dẫn đến lỗi xử lý và không insert được vào bảng.
```

Câu trả lời thực tế:

```text
- &P ↑ Khi bạn nhập văn bản vào một ô trống, tiêu đề và chân trang sẽ được tự động thêm vào. [1]
- MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [2]
- Phải Tên tài liệu: Giao diện truyền thông bảng điều khiển [3]
- Thông tin về bảng T_IF_PROD_RESULT Ngày phát sinh/ghi nhận: Chưa xác định ngày cụ thể trong file hiện tại; lỗi được ghi nhận khi VN liên kết lượng lớn dữ liệu tiêu hao linh kiện. [4]
- Sơ Đồ ERD Ultimate - Hệ Thống Kho Vận Sơ Đồ ERD Ultimate (Có độ dài Data Type) Cập nhật chính xác giới hạn ký tự (Size) cho từng trường varchar/decimal theo đúng thiết kế hệ thống. [5]
LIMITATIONS: incomplete_query_term_coverage
```

## B5 — `HOUSE_METHOD` không đến được evidence pack

- Index có chunk `230dce110f341c0a097a78c2c5363a0a4efe71331c870fa7d906c53fce3fab46`, tài liệu `wsc-ff8304af86028eaa474a1706`, loại `txt`, retrievable=1, dài 371 ký tự. Chunk có ONNX vector fingerprint `016c5255…`.
- Toàn văn chunk:

```text
票情報(必ず登録)箱入数 16 製造ロット MANUFACTUAL_LOT varchar ＥＤＩ現品票情報(必ず登録) 17 インボイス番号 INVOICE_NO varchar ＥＤＩ現品票情報(必ず登録) 18 オリコン状態 ORICON_STATUS varchar オリコンのチェック結果状態を示すコード 19 格納方法 HOUSE_METHOD varchar '0':倉庫へ格納'1':検査 20 荷受(伝票)HTユーザーID SLIP_READ_HTID varchar 21 データ連携時間１ IF_DATE datetime 22 オリコン重量 ORICON_WEIGHT int 単位グラム 23 入庫保管場所 STORAGE_PLACE varchar 24 格納口 HOUSE_ENTRANCE varchar 25
```

- B5 có `candidate_count=200`, `returned_count=15`; sau mở rộng ngữ cảnh có 22 kết quả và evidence pack 20 mục. Chunk định nghĩa không có trong cả kết quả mở rộng lẫn pack. Tra cứu lexical cùng câu hỏi với giới hạn 1.272 cho thấy chunk ở hạng **467**, điểm 1,0, khớp `house_method`. Lượt hybrid dùng cửa sổ lexical 100; vì vậy chunk không vào pool lexical để hợp nhất. Không có rerank sau đó (`reranker_requested=False`, `reranker_applied=False`).
- B5 không được sửa bằng prompt: writer chưa hề nhận định nghĩa. Chunk không bị cắt và có trong index; cần xử lý ở thu hồi ứng viên. Câu trả lời thực tế chỉ gồm summary/chunk chung về nhập kho, không nêu `HOUSE_METHOD` hay hai giá trị.

## Prompt và lý do fallback

Đường tổng hợp có hai phần khác nhau:

1. Adapter `src/aios_habit/rag_v2_synthesis_provider.py` dựng câu hỏi cộng contract citation và context từ toàn bộ snippet evidence. Contract yêu cầu chỉ dùng evidence, dẫn citation cho mọi ý thực tế, không tạo mã/dữ kiện ngoài evidence; có tối đa 8 claim vật chất. System prompt yêu cầu chỉ trả lời theo evidence và nói rõ khi thiếu.
2. Bộ định tuyến trả `auto:blocked` với lý do: “Chưa chắc loại tài liệu, AIOS chọn an toàn và không gửi ra ngoài.” Không có yêu cầu nào được gửi đến dịch vụ bên ngoài. Pipeline dùng fallback trích xuất cục bộ.

Do đó, không có “prompt gửi vào khâu viết câu trả lời cuối” theo nghĩa prompt đã gửi cho LLM. Nhật ký đã lưu nguyên văn `provider_question`, `provider_contract`, `provider_context` và `evidence_prompt` được dựng tại chỗ để đối chiếu. Fallback cục bộ không dùng prompt: `synthesize_evidence` gọi `_compose_grounded_claims` trên evidence pack.

Cấu hình evidence giới hạn mỗi snippet ở 1.500 ký tự. Các chunk đáp án B1 (742/958 ký tự), B3 (593/227/310 ký tự) và B5 (371 ký tự) đều dưới giới hạn. Summary dài 1.551 ký tự có thể bị cắt 51 ký tự trong snippet, nhưng dữ kiện B1/B3 vẫn có trong chunk thân đầy đủ và trong pack. Vì vậy truncate không giải thích việc rớt đáp án.

## Nguyên nhân theo tầng

| Ca | Evidence truy xuất | Bị lọc sau retrieval? | Nguyên nhân quan sát được |
| --- | --- | --- | --- |
| B1 | Có; chunk đáp án là mục `[6]`/`[7]` | Không | `src/aios_habit/rag_v2/synthesis.py`: `synthesize_evidence` mặc định tối đa 5 claim; `_compose_grounded_claims` đi theo thứ tự pack. Năm summary đầu chiếm hết năm claim trước khi tới chunk thân. |
| B3 | Có; các chunk `[6]`–`[8]` chứa `nvarchar(4000)`/4.000 ký tự | Không | Cùng giới hạn và thứ tự như B1. Thêm nữa, `_best_fragment` chấm overlap token trên câu hỏi tiếng Việt; câu summary tiếng Việt chung đạt `(16, -178)`, trong khi câu tiếng Nhật có `nvarchar(4000)` đạt `(0, -57)`. Ngay trong chunk thân `[6]`, câu mô tả chung đạt 21 điểm, cao hơn câu trả lời giới hạn đạt 13 điểm. |
| B5 | Không; chunk đúng còn trong index nhưng không nằm trong kết quả mở rộng (22 mục) | Không có bằng chứng về filter sau retrieval | Hạng lexical 467 vượt cửa sổ 100 ứng viên; chunk không vào evidence pack. Không phải chunking; không có reranker để “cứu” ứng viên đã rớt. |

Trong `src/aios_habit/rag_v2/index.py::hybrid_search_with_summary`, với intent `general`, summary của các tài liệu đã tìm được được đưa lên đầu danh sách (dòng 2420–2427). Ba câu tra cứu chi tiết vẫn có intent `general`, dù `retrieval_mode=full`; đây là lý do summary đứng trước các chunk thân trong B1/B3. Bộ dựng evidence giữ cả chunk thân, nhưng bộ tổng hợp chỉ lấy năm claim.

## Đề xuất sửa cụ thể — chưa thực hiện trong ticket chỉ đọc

1. **B1 và B3 — ưu tiên fact thay vì summary chung.** Sửa `src/aios_habit/rag_v2/synthesis.py`: trong `synthesize_evidence` / `_compose_grounded_claims` / `_best_fragment`, nhận diện nghĩa vụ trả lời tra cứu chi tiết từ câu hỏi; không để năm summary đầu chiếm hết ngân sách claim; ưu tiên đoạn có giá trị/mã đúng với yêu cầu. Khi câu hỏi tiếng Việt nhưng evidence Nhật, dùng mã kỹ thuật hoặc fact literal làm tín hiệu hỗ trợ, không chỉ đếm token cùng ngôn ngữ. Giữ citation tới chunk thực sự chứa đáp án.
2. **Giảm summary chen lên đầu đường chi tiết.** Sửa `src/aios_habit/rag_v2/index.py::hybrid_search_with_summary`: với truy vấn `retrieval_mode=full`, không prepend summary trước chunk thân; hoặc giữ summary làm bổ sung sau kết quả thân. Hiện `general` khiến summary được chèn ngay cả khi routing đã phân loại là `full`.
3. **B5 — thu hồi khóa định danh chính xác.** Sửa `src/aios_habit/rag_v2/index.py::hybrid_search_with_summary` và `search_with_summary` để có nhánh/quota cho exact field/table token như `HOUSE_METHOD`/`T_PARTS_RECIEVE` trước khi cắt cửa sổ lexical 100; đưa ứng viên exact-hit vào hợp nhất hybrid. Câu hỏi hiện bị xếp `general` trong `src/aios_habit/rag_v2/query_planning.py::identity_query_plan` / `_detect_intent_category`; có thể phân loại dạng hỏi mã/giá trị thành lookup cụ thể để áp dụng chính sách đó. Không cần đổi chunking hoặc thêm định nghĩa tay.
4. **Xác minh sau khi được duyệt:** chạy B1/B3/B5 trên bản sao chỉ đọc/fixture kiểm thử; xác nhận mọi mã được hỏi có trong claim và citation trỏ đúng chunk, B5 đưa chunk 230d vào evidence trước synthesis; giữ kiểm tra không ghi index thật.

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`.
- Nhật ký đầy đủ chứa toàn văn evidence và request dựng tại chỗ ở `C:/Users/Admin/AppData/Local/Temp/e1_rerun_b1b3b5.jsonl`; không commit dữ liệu corpus thô.
- Chỉ đọc index; không sửa code, không chạy ingest, không ghi index. Không chạy test vì ticket điều tra; đã chạy lại chính xác đường truy vấn B1/B3 ONNX và kiểm tra B5 lexical trên index read-only.