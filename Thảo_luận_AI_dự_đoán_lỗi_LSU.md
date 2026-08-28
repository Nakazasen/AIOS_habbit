# Thảo luận xây dựng AI dự đoán và phòng ngừa lỗi LSU

## 1. Mục đích của tài liệu

Tài liệu này ghi lại đầy đủ mạch trao đổi giữa người dùng và AI về hướng nâng cấp AIOS_habbit thành một hệ thống hỗ trợ phân tích, dự đoán và phòng ngừa lỗi LSU. Nội dung giữ đồng thời hai cách trình bày:

- **Lớp kỹ thuật:** kiến trúc, dữ liệu, thuật toán, cổng kiểm chứng, giới hạn và lộ trình triển khai.
- **Lớp non-tech:** diễn giải bằng ngôn ngữ gần với cách vận hành trong nhà máy để chuyên gia, quản lý và người không làm phần mềm vẫn có thể đánh giá.

Mục tiêu không phải viết một bản giới thiệu đẹp nhưng thiếu căn cứ. Mọi kết luận phải phân biệt rõ:

- Điều đã quan sát trực tiếp từ tài liệu hoặc log.
- Điều mới chỉ là tương quan.
- Giả thuyết cần chuyên gia hoặc thực nghiệm xác nhận.
- Điều chưa biết do thiếu dữ liệu.

## 2. Bối cảnh và vấn đề người dùng đặt ra

Nguồn tài liệu nội bộ được đặt tại:

```text
D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy
```

Phạm vi trọng tâm về LSU Iris:

```text
D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Iris LSU
```

Bộ dữ liệu thử nghiệm nối thông số linh kiện với log JIG:

```text
D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Iris LSU\thu nghiem 6pcs do thong so va log
```

Người dùng muốn AIOS_habbit có thể trả lời các nhóm câu hỏi thực tế:

1. Một trường hoặc một đoạn log có ý nghĩa gì?
2. Hạng mục đó liên quan đến những dữ liệu nào khác trong log?
3. Hạng mục đó liên quan đến thông số linh kiện nào?
4. Nếu thay đổi max/min của thông số linh kiện thì dữ liệu JIG thay đổi thế nào?
5. Thông số đó tác động đến vị trí khác hay đứng độc lập?

Mục tiêu xa hơn là xây một tool thu log liên tục để AI theo dõi 24/7, phát hiện trong hàng trăm hoặc hàng nghìn trường:

- Điểm dữ liệu nào bất thường.
- Chuỗi dữ liệu nào đang drift.
- Bất thường có thể bị ảnh hưởng bởi linh kiện, JIG, môi trường hay thao tác nào.
- Chuỗi hệ quả có thể dẫn đến lỗi gì nếu xu hướng tiếp diễn.

Khó khăn cốt lõi là tài liệu nền không bao giờ đầy đủ ngay từ đầu. Vì vậy hệ thống không thể chỉ là RAG thụ động đọc tài liệu có sẵn; nó phải có cơ chế phát hiện phần tri thức còn thiếu, hỏi đúng chuyên gia, lưu phản hồi theo mức độ chắc chắn và tích lũy tri thức dần trong quá trình vận hành.

### Diễn giải non-tech

Ta không thể yêu cầu AI đọc một đống tài liệu rồi tự nhiên trở thành kỹ sư LSU. Hệ thống cần giống một kỹ sư mới nhưng có kỷ luật rất cao: biết tra hồ sơ, biết chỉ ra căn cứ, biết khi nào chưa hiểu, biết hỏi người có kinh nghiệm và không biến một câu trả lời chưa kiểm chứng thành sự thật vĩnh viễn.

## 3. Ý tưởng Knowledge Graph và vòng thẩm vấn chuyên gia

Ý tưởng ban đầu được mô tả như sau:

```text
[Log JIG / Linh kiện thô]
           │
           ▼
[Phân tích bất thường + đo độ tự tin]
           │
     ┌─────┴──────────────────────┐
     │ Đủ tri thức                │ Chưa đủ tri thức
     ▼                            ▼
[Báo cáo chẩn đoán]      [Interrogation Engine]
                                      │
                                      ▼
                              [Giao diện chuyên gia]
                              - Chắc chắn
                              - Cần xác nhận
                              - Trả lời sau
                                      │
                                      ▼
                          [Knowledge Base / RAG / Graph]
```

Hệ thống phân loại trạng thái hiểu biết:

- **Known knowns:** đã có lịch sử, tiêu chuẩn và bằng chứng phù hợp.
- **Known unknowns:** biết chính xác mắt xích nào đang thiếu.
- **Conflicting knowledge:** các nguồn hoặc phép đo mâu thuẫn.
- **Data untrusted:** dữ liệu có nhưng chưa thể tin vì schema, sentinel, calibration hoặc chuỗi trace chưa đầy đủ.
- **Unknown unknown candidate:** xuất hiện mẫu bất thường mới chưa khớp các khái niệm hiện có.

Khi thiếu tri thức, hệ thống không hỏi chung chung. Nó phải tạo câu hỏi có dữ kiện:

> Log thông số A của LSU đang là X, khác vùng thông thường Y. Giới hạn NG được ban hành theo tài liệu hoặc thực nghiệm nào? Hiện tượng này liên quan đến lỗi quang học nào? Cần kiểm tra thêm dữ liệu nào để loại trừ sai lệch của JIG?

### Phân cấp phản hồi chuyên gia

- **Chắc chắn / Verified:** có phạm vi áp dụng và căn cứ; đủ điều kiện bước vào quy trình xét duyệt Golden Knowledge.
- **Cần xác nhận / Tentative:** lưu thành Candidate Rule, chưa dùng để kết luận chắc chắn.
- **Trả lời sau / Deferred:** đưa vào backlog, ghi rõ người/phòng ban và bằng chứng cần bổ sung.
- **Mâu thuẫn:** mở review; không ghi đè tri thức cũ âm thầm.
- **Không thuộc chuyên môn:** chuyển đúng nhóm chuyên gia.

### Diễn giải non-tech

Mỗi câu trả lời của chuyên gia giống một phiếu ý kiến kỹ thuật, không phải ngay lập tức là luật nhà máy. Phiếu đó phải ghi ai trả lời, áp dụng cho model/JIG nào, dựa trên tài liệu hay kinh nghiệm, chắc chắn đến đâu và khi nào cần xem lại.

## 4. Kết quả đọc và đối chiếu tài liệu Iris LSU

### 4.1. Quy mô dữ liệu

Lượt kiểm kê đầu tiên ghi nhận:

- Thư mục tất cả dòng máy: khoảng 888 file, hơn 1,1 GB.
- Thư mục Iris LSU: 61 file, khoảng 261 MB.
- Bộ thử nghiệm 6 pcs: 46 file, khoảng 224 MB.
- Định dạng gồm CSV, XLS/XLSX/XLSM, PPT/PPTX, MSG, ảnh và một số database.

Đây mới là lượt đọc có trọng tâm, không phải tuyên bố đã hiểu toàn bộ 888 file.

### 4.2. Sáu mẫu thử nghiệm

`Barcode_List.xlsx` ánh xạ:

| Serial | Vị trí mẫu |
|---|---|
| 61C1068E9521 | Shot 1 đầu lot |
| 61C1068E9522 | Shot 2 đầu lot |
| 61C1068E9523 | Shot 3 giữa lot |
| 61C1068E9524 | Shot 4 giữa lot |
| 61C1068E9525 | Shot 5 cuối lot |
| 61C1068E9526 | Shot 6 cuối lot |

Các mẫu dùng FRAME LOT ngày 18/8/2026 và LENS LOT 6516. Danh sách ghi JIG Beam `2ND-1002-1`, JIG Bow/Skew `1004/1035`.

### 4.3. Mắt xích bằng chứng còn thiếu

Cả sáu serial được tìm thấy trong log 1004 và 1035. Tuy nhiên chưa tìm thấy các serial này trong nhóm log 1002 hiện có, dù bảng barcode ghi có chạy JIG Beam 1002-1.

Kết luận đúng phải là:

> Đã nối được serial với JIG 1004 và 1035. Có chỉ dấu rằng sản phẩm phải đi qua JIG 1002-1, nhưng chưa có bản ghi 1002 tương ứng trong nguồn hiện có.

Hệ thống không được tự suy rằng dữ liệu 1004/1035 đã đại diện cho toàn bộ chuỗi đo.

### Diễn giải non-tech

Giống như hồ sơ nói một sản phẩm đã qua ba cửa kiểm tra, nhưng ta chỉ tìm thấy vé của hai cửa. AI phải báo thiếu vé cửa thứ ba, không được tự đánh dấu rằng sản phẩm chắc chắn đã đi qua đầy đủ.

### 4.4. Ngưỡng được ghi trong JIG

Spec log của JIG 1004 có các giá trị:

- Bow: 25 µm.
- Skew: 25 µm.
- Current: 370–520 mA.
- Voltage: 4–7 V.

Đây là bằng chứng rằng JIG được cấu hình với các giới hạn đó. Nó chưa phải bằng chứng về nguồn kỹ thuật ban hành giới hạn, công thức vật lý hoặc phạm vi revision áp dụng.

Phải phân biệt hai claim:

1. “Log JIG đang ghi ngưỡng 25 µm.” — đã có bằng chứng trực tiếp.
2. “25 µm là giới hạn đúng do cơ chế quang học X.” — chưa đủ bằng chứng.

### 4.5. Sai khác giữa JIG 1004 và 1035

Tài liệu `Y_BeamH_Camera 140_to bất thường.pptx` cho biết:

- Beam H Yellow tại Camera +140 của JIG 1035 có dấu hiệu to lên.
- Hiện tượng không xuất hiện tương tự ở JIG 1004.
- NanoScan cho kết quả khớp JIG 1004.
- Tài liệu kết luận cần tương quan/hiệu chỉnh lại JIG 1035.

Đây là bằng chứng rất quan trọng: một giá trị bất thường có thể do hệ đo, không nhất thiết do sản phẩm.

```text
Giá trị bất thường
       ├── Sản phẩm bất thường
       ├── JIG mất tương quan
       ├── Sensor/camera/căn chỉnh thay đổi
       ├── Công thức hoặc software revision khác
       └── Dữ liệu thiếu/sentinel/parser sai
```

Do đó kiến trúc phải có **Measurement Trust Gate** trước cổng chẩn đoán sản phẩm.

### 4.6. Đo lại và trạng thái không ổn định

Trong log 1004, serial `61C1068E9526` có chuỗi ví dụ:

```text
Lần đầu: OK
Lần sau: Cyan NG / Total NG
Lần kế tiếp: OK
```

Đây không thể bị nén thành một nhãn cuối cùng mà bỏ lịch sử. Cần giữ từng lần đo, thứ tự thời gian, thao tác giữa các lần đo và quy tắc chấp nhận kết quả retest.

### 4.7. Bẫy dữ liệu

Đã quan sát các vấn đề:

- `999` và `9999.9` có khả năng là sentinel, chưa thể coi là số đo vật lý.
- `Temperature=0`, `Humidity=0` có thể là thiếu dữ liệu, không nhất thiết là điều kiện thật bằng 0.
- Log có từ hàng trăm tới hơn một nghìn cột.
- Một số CSV có phần preamble trước header.
- Cùng serial có nhiều lần đo.
- 1004 và 1035 có schema và bối cảnh phép đo khác nhau.

Vì vậy không thể dùng một CSV parser chung rồi đưa trực tiếp toàn bộ dữ liệu cho LLM.

## 5. AIOS phải trả lời năm loại câu hỏi như thế nào

### 5.1. “Log này có ý nghĩa gì?”

Trả lời theo bốn tầng:

```text
Tên trường
→ giá trị và đơn vị
→ JIG/bước đo sinh ra nó
→ ý nghĩa kỹ thuật đã được chứng minh
```

Nếu chỉ biết cấu hình JIG mà chưa biết căn cứ, phải nói rõ phần thiếu.

### 5.2. “Liên quan dữ liệu nào khác?”

Truy vấn quan hệ theo schema, serial, thời gian, màu, camera, JIG và tài liệu. ExcaliFlow hiển thị graph để người dùng mở từng bằng chứng.

### 5.3. “Liên quan thông số linh kiện nào?”

Phải phân cấp cạnh:

- `verified_relation`
- `observed_correlation`
- `suspected_relation`
- `unknown`

Không được đổi tương quan thành nguyên nhân.

### 5.4. “Thay đổi max/min thì JIG thay đổi thế nào?”

Chỉ trả lời định lượng khi có công thức, DOE, dữ liệu lịch sử đủ mạnh hoặc xác nhận chuyên gia đã kiểm chứng. Sáu mẫu đầu/giữa/cuối lot chỉ thích hợp proof-of-concept, chưa đủ chứng minh nhân quả.

### 5.5. “Thông số tác động vị trí khác hay đứng một mình?”

Graph phải phân biệt:

```text
A --tài liệu quy định--> B
A --chuyên gia xác nhận--> B
A --dữ liệu cho thấy tương quan--> B
A --thực nghiệm chứng minh ảnh hưởng--> B
```

## 6. Kiến trúc hệ thống đề xuất

```text
Log linh kiện / JIG / tài liệu / phản hồi chuyên gia
                         │
                         ▼
              Chuẩn hóa + kiểm tra dữ liệu
     schema, unit, sentinel, serial, time, JIG version
                         │
                         ▼
                Measurement Trust Gate
       calibration, retest, sensor, missing evidence
                         │
                         ▼
             Evidence-backed Knowledge Graph
       Entity ─ Measurement ─ Claim ─ Evidence ─ Expert
                         │
                         ▼
                Epistemic Decision Engine
       Supported / Conflicting / Insufficient / Unknown
                  │                     │
                  ▼                     ▼
          Báo cáo có bằng chứng     Câu hỏi chuyên gia
                                          │
                                          ▼
                          Candidate knowledge / Golden record
```

### Diễn giải non-tech

Trước khi AI nói sản phẩm có lỗi, nó phải kiểm tra “cái thước có đáng tin không”. Sau đó nó mới tra hồ sơ, nối các dấu vết và quyết định rằng đã đủ căn cứ hay cần hỏi người phụ trách.

## 7. Điều kiện để đạt dự đoán lỗi đáng tin cậy

### 7.1. Hồ sơ số theo serial

Mỗi LSU cần một digital thread:

```text
Serial
 ├── model/revision
 ├── lot linh kiện và nhà cung cấp
 ├── thông số linh kiện
 ├── line/máy/ca/thời gian
 ├── JIG ID/software/calibration
 ├── toàn bộ lần đo và retest
 ├── kết quả công đoạn sau
 ├── kết quả in/burn-in
 └── lỗi thị trường nếu có
```

### 7.2. Định nghĩa nhãn lỗi cụ thể

Không huấn luyện mục tiêu mơ hồ “LSU lỗi”. Phải chọn rõ:

- Bow/Skew NG.
- Beam diameter bất thường.
- Lỗi màu/vệt khi in.
- Lỗi ở công đoạn cuối.
- JIG drift/mất tương quan.
- Lỗi ngoài thị trường trong một cửa sổ thời gian.

### 7.3. Dữ liệu huấn luyện và đánh giá

Cần cả OK và NG, nhiều lot, nhiều JIG, nhiều ca và revision. Chia train/validation/test theo thời gian; không để cùng serial hoặc lot lọt sang cả train và test.

So sánh model với baseline:

- Giới hạn max/min hiện hành.
- SPC/EWMA.
- Rule chuyên gia.
- Anomaly detector đơn giản.

Chỉ coi AI có giá trị khi tốt hơn baseline theo KPI nghiệp vụ: recall lỗi thật, precision, false alarm mỗi ngày, lỗi bỏ sót, thời gian cảnh báo sớm và chi phí hành động sai.

### 7.4. Shadow mode

Triển khai theo cấp:

```text
Shadow → Advisory → Human approval → Limited automation
```

Trong shadow mode, AI dự đoán trước nhưng không tác động line. Sau nhiều tuần mới đối chiếu dự đoán với kết quả thật.

### Diễn giải non-tech

Trước khi cho AI quyền cảnh báo hoặc chặn hàng, để nó “đứng bên cạnh” dự đoán trong im lặng. Nếu dự đoán đúng ổn định và không báo động giả quá nhiều thì mới tăng quyền.

## 8. Làm thế nào chứng minh quan hệ nhân quả linh kiện → JIG

Knowledge Graph phải phân biệt:

```text
correlated_with
suspected_cause_of
experimentally_affects
verified_cause_of
```

Muốn nâng một cạnh lên `verified_cause_of`, cần:

- Cơ chế kỹ thuật hợp lý.
- DOE có kiểm soát.
- Giữ các biến gây nhiễu ổn định.
- Random hóa thứ tự đo.
- Đo lặp trên JIG và JIG đối chứng.
- Ghi điều kiện môi trường.
- Kiểm tra calibration trước/sau.
- Gauge R&R để biết sai số hệ đo.
- Phân tích phản ví dụ.
- Chuyên gia phê duyệt phạm vi áp dụng.

Nếu sai số JIG lớn hơn tín hiệu cần phát hiện, model không thể học quan hệ đáng tin dù thuật toán mạnh.

## 9. Vòng đời Golden Knowledge

```text
Expert Answer
      ↓
Captured Claim
      ↓
Candidate Knowledge
      ↓
Cross-check tài liệu/dữ liệu/chuyên gia
      ↓
Validated Rule
      ↓
Golden Knowledge
      ↓
Theo dõi drift, hết hạn và mâu thuẫn
```

Mỗi claim cần lưu:

- Nội dung claim.
- Model/JIG/software/revision áp dụng.
- Người trả lời và thời điểm.
- Loại căn cứ.
- Mức chắc chắn.
- Ca xác nhận và phản ví dụ.
- Ngày hiệu lực và ngày review.
- Rule cũ bị thay thế nếu có.

Không xóa hoặc ghi đè tri thức cũ âm thầm; phải version hóa và lưu lý do thay đổi.

## 10. Theo dõi 24/7 ở quy mô sản xuất

LLM không nên trực tiếp đọc hàng nghìn cột liên tục. Kiến trúc phù hợp:

```text
JIG/File/DB/Message Queue
          │
          ▼
    Log Collectors
          │
          ▼
Schema validation + normalization
          │
          ▼
Time-series / Feature Store
          │
          ├── Rule/SPC Engine
          ├── Anomaly Models
          ├── Prediction Models
          └── Knowledge Graph lookup
                    │
                    ▼
             Incident/Case Engine
                    │
                    ▼
           LLM giải thích + hỏi chuyên gia
```

LLM phù hợp để tổng hợp, giải thích, truy xuất bằng chứng và sinh câu hỏi. Các module xác định phải đảm nhiệm đọc log, tính toán, retry, alert, audit và lưu trữ.

Một bất thường phải được gom thành incident thay vì bắn cảnh báo theo từng điểm:

```text
Incident IRIS-...
 ├── JIG và thời gian bắt đầu
 ├── trường/chuỗi đang drift
 ├── số sản phẩm bị ảnh hưởng
 ├── lot/revision liên quan
 ├── JIG đối chứng
 ├── trạng thái calibration
 ├── giả thuyết được xếp hạng
 └── hành động xác minh tiếp theo
```

Hệ thống phải fail-safe: AIOS hỏng không làm JIG dừng, không mất log, không tự đổi spec và không tự phán OK khi chưa rõ.

## 11. Vai trò của ExcaliFlow trong AIOS_habbit

ExcaliFlow trong bài toán này không dùng để phân tích source code của AIOS_habbit. Nó là giao diện trực quan hóa tri thức sản xuất:

- Bản đồ một serial LSU.
- Linh kiện → phép đo → JIG → kết quả → lỗi.
- So sánh 1004 và 1035.
- Timeline retest.
- Mắt xích bằng chứng còn thiếu.
- Quan hệ mâu thuẫn.
- Candidate và Golden Knowledge.
- Cạnh được tô theo mức độ chứng cứ.

### Diễn giải non-tech

ExcaliFlow là màn hình cho con người kiểm tra “AI biết điều đó bằng cách nào”, không chỉ là một sơ đồ đẹp.

## 12. Audit RAG hiện tại của AIOS_habbit

### 12.1. Kết luận tổng quát

RAG hiện tại có thể làm **retrieval kernel** cho LSU nhưng chưa đủ làm toàn bộ nền tảng chẩn đoán công nghiệp.

Nên giữ lại:

- BGE-M3 dense embedding.
- BGE-M3 learned sparse.
- Lexical retrieval.
- RRF fusion.
- Reranker adapter.
- Evidence Pack, citation và provenance.
- Privacy label và fail-closed deployment.
- Structured Excel query.
- Evidence Graph/ExcaliFlow.

Còn thiếu:

- Query planner chuyên ngành.
- Multi-intent decomposition đáng tin.
- Chunking được benchmark trên tài liệu LSU.
- Structured log/time-series retrieval.
- LSU schema registry.
- Measurement trust layer.
- Typed Knowledge Graph.
- Expert interrogation lifecycle.
- Judged LSU evaluation set.

### 12.2. Trạng thái BGE-M3

Manifest production tại thời điểm audit ghi:

```text
activation_state = rolled_back
requested_profile = bge_m3_hybrid
reranker_enabled = false
```

Loader chỉ dùng deployment production khi state là `activated`.

Tuy nhiên local pilot trả về:

```text
enabled = True
profile = bge_m3_hybrid
adaptive_enabled = True
model_configured = True
reranker_configured = True
runtime = local_runs/workspace_chat_rag_v2_canary
```

Kết luận: BGE-M3 hybrid có đường local pilot/canary hoạt động, nhưng production manifest đã rollback; không được gọi là production-qualified.

Các test tập trung chunking, query planning và deployment loader đã chạy:

```text
45 passed in 0.99s
```

Test contract không thay thế benchmark recall trên tài liệu LSU.

### 12.3. Chunking hiện tại

Chunker cắt tuần tự toàn bộ văn bản; không bỏ phần giữa. Điểm yếu thật là `zero-overlap`:

- Child khoảng 900–1.000 ký tự.
- Cắt theo `. `, xuống dòng hoặc khoảng trắng.
- Không có overlap.
- Chưa nhận diện đầy đủ dấu câu CJK như `。！？`.
- Parent 3.000–8.000 ký tự được tạo nhưng `retrievable=False`.
- Neighbor/parent expansion chỉ được dùng ở profile expand, không phải hybrid thường.

Vì vậy quan hệ nằm qua ranh giới có thể bị chia đôi.

### Diễn giải non-tech

Máy không làm mất trang giấy, nhưng có thể cắt một câu giải thích làm hai mảnh rồi chỉ tìm thấy một mảnh. Khi đó AI đọc được nửa nguyên nhân hoặc nửa kết quả.

### 12.4. Query decomposition và intent

Facet deterministic hiện chủ yếu tách theo:

- Xuống dòng.
- Dấu chấm phẩy.
- Bullet.

Nó không tách tốt câu nhiều ý dùng dấu phẩy, `và`, nhiều dấu hỏi hoặc đánh số trên cùng dòng.

Thử nghiệm trực tiếp:

- Câu nhiều ý dùng dấu phẩy/`và`: chỉ một query.
- Câu `1... 2... 3...` cùng dòng: chỉ một query.
- Câu dùng dấu `;`: tạo được ba facet.

Intent classifier chủ yếu chỉ có `procedure` và `general`. Nó chưa phân biệt lookup, comparison, diagnosis, causal analysis, anomaly, prediction, spec verification hoặc expert inquiry.

Hệ quả:

```text
Không nhận ra đủ các ý
→ không tạo đủ subquery
→ không tìm đủ loại bằng chứng
→ coverage có thể báo đủ giả
```

### 12.5. Retrieval hiện có

- Dense semantic retrieval.
- Learned sparse retrieval cho mã, thuật ngữ và tên trường.
- Lexical retrieval.
- RRF để hợp nhất thứ hạng.
- Multi-query/facet fusion nếu planner tạo được facet.
- Cross-encoder reranker có adapter và model local.
- Adaptive route và circuit breaker.
- Evidence coverage và missing-facet contract.

Điểm yếu không phải BGE-M3 không tốt, mà là hệ thống chưa luôn đưa cho nó đúng tập subquery và chưa có corpus LSU được gán expected evidence để đo thực tế.

### 12.6. BGE-M3 không thay thế engine phân tích log

BGE-M3 phù hợp để tìm đoạn giải thích, tài liệu, case lịch sử và thuật ngữ. Nó không nên quét hàng triệu dòng time-series, tính drift, correlation có kiểm soát hoặc Gauge R&R.

Cần router nhiều engine:

```text
Câu hỏi tài liệu          → Hybrid RAG
Câu hỏi log định lượng    → SQL/columnar/time-series
Câu hỏi quan hệ xác minh  → Knowledge Graph
Câu hỏi bất thường        → Statistical/anomaly engine
Câu hỏi tổng hợp          → hợp nhất bằng chứng rồi LLM diễn giải
```

## 13. LightRAG như một hướng nâng cấp thuật toán có kiểm chứng

### 13.1. Nguồn tham khảo và trạng thái khi đối chiếu

Repo chính thức:

- <https://github.com/HKUDS/LightRAG>
- README được đối chiếu tại commit HEAD `d403abc88f47153ec54ee1a07d30e237a8b5a9ab`.
- License: MIT.

LightRAG tự mô tả là một framework RAG dựa trên Knowledge Graph, kết hợp graph và vector embedding. Giá trị đáng nghiên cứu đối với AIOS không nằm ở việc “có graph” đơn thuần, mà ở cách nó tổ chức nhiều đường truy xuất:

- **local:** tập trung vào entity cụ thể và các thuộc tính/quan hệ trực tiếp.
- **global:** tìm chủ đề lớn và chuỗi quan hệ xuyên nhiều tài liệu.
- **hybrid:** hợp nhất local và global.
- **naive:** truy xuất chunk truyền thống, không dùng graph.
- **mix:** hợp nhất local, global và naive để tăng độ bao phủ.

LightRAG còn hỗ trợ cập nhật tài liệu gia tăng, xóa chọn lọc, lưu vector cho chunk/entity/relation và reranking. README hiện khuyến nghị reranker local như `BAAI/bge-reranker-v2-m3`, trùng với hướng reranker mà AIOS đã có adapter.

### 13.2. LightRAG bổ trợ AIOS ở đâu?

RAG hiện tại của AIOS mạnh ở truy xuất chunk bằng dense+sparse+lexical nhưng yếu khi một câu trả lời cần nối nhiều mảnh nằm ở các tài liệu khác nhau. LightRAG có thể trở thành một **graph retrieval challenger** song song:

```text
                         [Query Planner]
                                │
             ┌──────────────────┼───────────────────┐
             ▼                  ▼                   ▼
     [BGE-M3 Hybrid]     [LightRAG Graph]    [Structured Log]
     đoạn văn chính xác   entity/relationship   SQL/time-series
             │                  │                   │
             └──────────────────┼───────────────────┘
                                ▼
                    [Evidence Fusion + Rerank]
                                ▼
                 [Claim/Citation Sufficiency Gate]
```

Các use case LSU phù hợp:

1. Từ `Beam H Yellow` tìm entity JIG, camera, màu, NanoScan, tài liệu bất thường và các quan hệ trực tiếp.
2. Từ một serial tìm chuỗi lot linh kiện → công đoạn → JIG → retest → kết quả.
3. Tìm quan hệ xuyên tài liệu giữa một trường log, tiêu chuẩn, báo cáo bất thường và phản hồi chuyên gia.
4. Tìm các case có cấu trúc quan hệ tương tự dù câu chữ không giống nhau.
5. Cập nhật graph khi có tài liệu hoặc claim chuyên gia mới mà không xây lại toàn bộ kho từ đầu.

### Diễn giải non-tech

BGE-M3 hiện giống người tìm các trang giấy có nội dung gần câu hỏi. LightRAG bổ sung vai trò giống người lập sơ đồ: trên trang này có linh kiện A, trang kia nói A liên quan phép đo B, báo cáo khác ghi B từng bất thường trên JIG 1035. Hai cách phải hỗ trợ nhau; sơ đồ không thay thế tờ giấy gốc.

### 13.3. Những gì LightRAG không tự giải quyết

Không được coi entity/relation do LLM trích xuất là Golden Knowledge. LightRAG không tự chứng minh:

- Quan hệ là nhân quả thay vì tương quan.
- JIG có đang calibration đúng hay không.
- `9999.9` là sentinel hay giá trị vật lý.
- Câu trả lời chuyên gia có đủ thẩm quyền và căn cứ.
- Một ngưỡng trong log là spec chính thức.
- Dự đoán lỗi đã pass backtest và shadow live.

LightRAG sử dụng LLM để trích xuất entity–relation từ từng chunk. Nếu chunk sai, schema thiếu hoặc model hiểu nhầm thuật ngữ LSU, graph có thể chứa cạnh nghe hợp lý nhưng không có thật. Vì vậy mọi cạnh phải có provenance và trạng thái:

```text
extracted_candidate
observed_correlation
expert_asserted
documented
experimentally_verified
deprecated
```

### 13.4. Không thay BGE-M3 ngay lập tức

Đề xuất không phải:

```text
Bỏ RAG v2 → thay bằng LightRAG
```

Mà là:

```text
Giữ BGE-M3 hybrid làm baseline
          │
          ├── LightRAG chạy challenger
          ├── cùng LSU judged corpus
          ├── cùng privacy/provenance contract
          └── chỉ promote phần có gain được đo
```

Lý do:

- BGE-M3 vẫn cần để tìm đoạn bằng chứng chi tiết và mã kỹ thuật.
- Graph retrieval có thể tăng cross-document recall nhưng cũng tăng chi phí indexing và nguy cơ cạnh sai.
- LightRAG phụ thuộc chất lượng LLM extraction; dữ liệu công ty đòi hỏi local-only hoặc một chính sách redaction được phê duyệt.
- Đổi embedding model sau khi index graph/vector có thể buộc re-embed toàn bộ; README LightRAG cũng cảnh báo điểm này.
- AIOS đã có evidence, privacy và deployment contract; không nên bỏ các cổng kiểm chứng này để chạy theo framework mới.

### 13.5. Thiết kế pilot LightRAG cho LSU

#### Bước L0 — Threat model và dữ liệu thử

- Chỉ dùng một evidence pack nội bộ nhỏ đã được phép.
- Không gửi raw log/tài liệu công ty ra cloud.
- Chốt model extraction local, embedding BGE-M3 và reranker local.
- Lưu fingerprint của source, model, prompt và schema.

#### Bước L1 — Domain ontology tối thiểu

Định nghĩa trước entity types:

```text
LSU_SERIAL, COMPONENT, COMPONENT_PARAMETER, LOT,
JIG, JIG_SOFTWARE, MEASUREMENT, LOG_FIELD,
SPEC_LIMIT, DEFECT, LOCATION, COLOR,
EXPERIMENT, DOCUMENT, EXPERT_CLAIM
```

Định nghĩa relation types được phép, ví dụ:

```text
MEASURED_BY, HAS_MEASUREMENT, USES_COMPONENT,
FROM_LOT, RETEST_OF, CONFIGURED_LIMIT,
OBSERVED_WITH, CONTRADICTS, SUPPORTED_BY,
SUSPECTED_CAUSE_OF, VERIFIED_CAUSE_OF
```

LLM không được tự tạo relation type mới vào Golden Graph. Loại mới phải vào quarantine để review.

#### Bước L2 — Graph extraction có bằng chứng

Mỗi node/edge phải giữ:

- Source file và fingerprint.
- Page/slide/sheet/row/cell hoặc log coordinates.
- Đoạn evidence chi tiết.
- Extraction model/version.
- Confidence của extraction.
- Epistemic status.
- Thời điểm và phạm vi hiệu lực.

Không có evidence coordinate thì cạnh không được dùng làm bằng chứng kết luận.

#### Bước L3 — So sánh năm chế độ retrieval

Trên cùng LSU judged set, đo:

| Candidate | Mục đích |
|---|---|
| AIOS BGE-M3 hybrid | Baseline hiện tại |
| LightRAG naive | Kiểm tra khác biệt do pipeline/chunk |
| LightRAG local | Entity/detail lookup |
| LightRAG global/hybrid | Cross-document relation |
| LightRAG mix + rerank | Độ bao phủ tối đa với chi phí cao hơn |
| AIOS fusion | BGE-M3 + graph + structured log |

Các metric bắt buộc:

- Expected evidence recall@K theo từng subquestion.
- Entity recall và relation recall.
- Unsupported-edge rate.
- False-sufficiency rate.
- Citation-coordinate validity.
- Latency, RAM, index time và index size.
- Incremental-update correctness.
- Deletion correctness: xóa tài liệu phải loại được evidence phụ thuộc.

#### Bước L4 — Human review pilot

ExcaliFlow hiển thị graph candidate cho chuyên gia:

- Cạnh xanh: documented/verified.
- Cạnh vàng: candidate/expert asserted chưa kiểm chứng.
- Cạnh đỏ: conflicting.
- Cạnh xám: thiếu bằng chứng hoặc hết hạn.

Chuyên gia có thể approve, reject, narrow scope hoặc yêu cầu thử nghiệm. Phản hồi không ghi thẳng vào Golden Graph.

#### Bước L5 — Controlled promotion

Chỉ tích hợp LightRAG vào đường mặc định nếu:

- Tăng recall trên các câu cross-document có ý nghĩa.
- Không giảm precision/citation validity của câu hỏi chi tiết.
- Unsupported-edge rate nằm dưới ngưỡng đã duyệt.
- Pass privacy, deletion và incremental-update tests.
- Có rollback về BGE-M3 baseline.

### 13.6. LightRAG và vòng học hỏi chuyên gia

LightRAG có thể giúp tìm và biểu diễn quan hệ, nhưng lifecycle tri thức vẫn phải do AIOS quản trị:

```text
LightRAG extracted edge
          ↓
Candidate Evidence Graph
          ↓
Expert interrogation / document check / DOE
          ↓
Validated Knowledge Graph
          ↓
Golden Knowledge
```

Điều này giống tư tưởng `/deep-dev` ở điểm: hệ thống tích lũy bài học và dùng lại trong lần sau. Nhưng bài toán LSU nghiêm ngặt hơn vì một quan hệ sai có thể ảnh hưởng quyết định chất lượng sản phẩm. Do đó cần provenance, thẩm quyền chuyên gia, phạm vi áp dụng, phản chứng và version hóa; không chỉ cần “test pass” như trong phát triển phần mềm.

### 13.7. Phán quyết về LightRAG

LightRAG là ứng viên đáng thử cho phần Knowledge Graph retrieval và cross-document reasoning của AIOS_habbit. Nó không phải phép thay thế tự động cho BGE-M3, cũng không phải causal engine hay hệ dự đoán lỗi hoàn chỉnh.

Vai trò hợp lý nhất:

> LightRAG làm lớp graph retrieval challenger; BGE-M3 tiếp tục cung cấp passage retrieval; structured engine xử lý log định lượng; AIOS Evidence/Expert Governance quyết định tri thức nào được phép dùng.

## 14. Roadmap nâng cấp RAG cho LSU

### R1 — LSU Retrieval Audit Set

Tạo 50–100 câu hỏi thật. Mỗi câu ghi:

- Các ý độc lập.
- Nguồn phải tìm thấy cho từng ý.
- Field/log/serial bắt buộc.
- Phần nào chưa có tài liệu.
- Khi nào phải hỏi chuyên gia.

Đo subquestion recall, evidence recall@K, field recall, citation support, missing-evidence detection và false-sufficiency rate.

### R2 — Query planner có cấu trúc

Planner phải trả về intent, entities, subquestions và required source types. Mỗi subquery retrieval riêng rồi mới deduplicate/rerank.

### R3 — Benchmark chunking

So sánh:

- Baseline zero-overlap.
- Sentence-aware.
- Bounded overlap 10–20%.
- Small-to-big retrieval.
- Neighbor expansion.
- Parent expansion.
- Table-aware row/column slices.

Chỉ promote chiến lược thắng trên LSU corpus theo recall, citation, latency và index size.

### R4 — Benchmark reranker

So sánh hybrid, hybrid+reranker và hybrid+reranker+context expansion trên cùng judged corpus.

### R5 — Multi-engine retrieval

Thêm structured log, time-series, Knowledge Graph và expert knowledge retrieval; BGE-M3 là một engine, không phải toàn bộ hệ thống.

## 15. Lộ trình triển khai sản phẩm

### Giai đoạn 1 — LSU Evidence Case

- Sáu serial hiện có.
- Nối linh kiện với 1004/1035.
- Hiển thị thiếu 1002.
- Giữ lịch sử retest.
- Đưa bằng chứng NanoScan–1004–1035 lên graph.
- Trả lời năm nhóm câu hỏi với trạng thái tri thức.

### Giai đoạn 2 — Knowledge Acquisition Pilot

- 3–5 chuyên gia.
- 20–50 câu hỏi thật.
- Candidate/Golden workflow.
- Review mâu thuẫn và version hóa.
- Đo tỷ lệ tri thức tái sử dụng.

### Giai đoạn 3 — Historical Monitoring

- Dữ liệu lịch sử nhiều lot/JIG/ca.
- Schema quality.
- SPC/drift detection.
- Gauge R&R.
- False alarm analysis.

### Giai đoạn 4 — Causal Experiments

- Chọn 2–3 quan hệ có giá trị cao.
- DOE và JIG đối chứng.
- Xác minh causal edges.

### Giai đoạn 5 — Shadow Prediction

- Chọn một lỗi cụ thể.
- Train/test theo thời gian.
- Shadow live 4–8 tuần.
- Đánh giá KPI đã thống nhất trước.

### Giai đoạn 6 — Production 24/7

- Streaming ingestion.
- Incident management.
- Observability, drift, rollback và SLA.
- Human approval và fail-safe.

## 16. Tiêu chuẩn để tuyên bố đã đạt cấp độ cao

| Năng lực | Điều kiện tối thiểu |
|---|---|
| Dự đoán đáng tin | Test dữ liệu tương lai, shadow live, xác suất được calibration, KPI nghiệp vụ đạt |
| Quan hệ nhân quả | Cơ chế kỹ thuật, DOE/đối chứng, loại trừ sai lệch JIG, chuyên gia phê duyệt |
| Golden Knowledge | Provenance, scope, review, phản chứng, version và quyền phê duyệt |
| Theo dõi 24/7 | Ingestion bền vững, fail-safe, incident workflow, observability và drift monitoring |

## 17. Kết luận chung của cuộc thảo luận

Ý tưởng của người dùng có giá trị thực tế và không phải bánh vẽ nếu triển khai theo lát cắt nhỏ, có bằng chứng và có cổng chặn.

AIOS_habbit hiện đã có một retrieval kernel đáng giữ, đặc biệt là BGE-M3 dense+sparse, lexical, RRF, evidence/citation và ExcaliFlow. Nhưng nó chưa có research planner, industrial data layer và expert knowledge lifecycle đủ cho chẩn đoán LSU cấp sản xuất.

Ưu tiên đúng không phải thay BGE-M3 bằng model mới. Thứ tự nên là:

```text
LSU judged audit set
→ query decomposition
→ chunking evaluation
→ reranking/context evaluation
→ structured log + time-series
→ typed Knowledge Graph
→ expert interrogation
→ shadow prediction
→ production 24/7
```

Nguyên tắc xuyên suốt:

> Hệ thống phải biết điều gì đã biết, điều gì chỉ là tương quan hoặc giả thuyết, điều gì chưa biết và cần bằng chứng nào để biết thêm. Mỗi ca mới vừa là đối tượng cần chẩn đoán, vừa là cơ hội kiểm chứng và nâng cấp tri thức có kiểm soát.
