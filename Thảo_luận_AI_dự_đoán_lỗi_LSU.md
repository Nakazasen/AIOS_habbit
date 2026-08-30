# Thảo luận: một hệ AIOS (tri thức → điều tra line → dự đoán unit → agent)

**Đọc mục “Một hệ thống” dưới đây.** Mục 1–29 phía sau là **nhật ký**; nhiều đoạn đã bị thay. Không tạo file kế hoạch mới. Ý mới: **sửa bản đồ này**, không thêm mục 30, 31, 32…

Luật sản phẩm vẫn: `AGENTS.md` → `CONSTITUTION.md` / `AGENT_RULES.md` → `ARCHITECTURE.md`.

## Một hệ thống (còn hiệu lực — 2026-08-30)

Bốn việc **không rời**: cùng vòng *vụ việc → bằng chứng → đề xuất → người duyệt → bài học*. Khác **tủ dữ liệu** và **cầu nối AI**.

```text
                    ┌─ Thư viện chữ + mô tả ảnh (SOP, MOM, ISO, mã lỗi, báo cáo đã duyệt)
  Câu hỏi / vụ      ┤
                    ├─ Bảng số / log có cột (Jam, Engine, JIG, serial) — không embed từng dòng
                    └─ Hồ sơ vụ (ảnh lỗi, đã thử gì)
                              │
                    Kernel RAG + parser log + gói bằng chứng
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     (1) Hỏi–đáp nội bộ  (3) Điều tra line  (2) Dự đoán unit
         chống mất tri thức   C/Jam pilot      LSU → Drum/DLP
                              │
                              ▼
                    (4) Agent = tay (báo cáo, SOP nháp, lệnh)
                         phải duyệt; không xóa file nhà máy
```

**Cầu nối:** Router / Gemini Web = chữ, không bản vẽ. C-AGENT Sonnet 4 công ty = được gửi sơ đồ/log (luật `AGENT_RULES.md`). Caption UI **chưa** chặn file — chưa được coi là đã an toàn.

**Kho:** sổ trỏ thư viện. Snapshot SQLite xong mới đổi con trỏ. Chỗ mới có kho khác thì chặn. Một writer (lease). WAL ổ mạng nhiều máy: chưa hỗ trợ.

### Việc đang làm (một hàng đợi)

1. **Gate A thư viện chung — Sol `PARTIAL`.** Identity theo nội dung chữ. Chủ repo test hai máy/NAS sau. Không tự PASS.
2. **Gate B — Sol `PASS`.** Thư viện chữ từ chối CSV; Excel SOP vẫn nạp được.
3. **Gate C — Sol `PASS`.** Gemini/Router không gửi ảnh/bản vẽ; C-AGENT được. Caption không thay thế chặn.
4. **Parser log Jam/C-call — Sol `PASS`.** CSV vào `line_events.sqlite`, không embed, provenance `suspected`.
5. **RAG chữ:** overlap cắt đoạn ~15%, cửa sổ retrieval/citation rộng hơn, ingest BGE gom lô 8–16. Không dùng LLM để embed. Index cũ không tự rebuild.
5. Agent IDE / SOP / dự đoán LSU: sau evidence pack.

Không: bốn nhánh song song; E3; LightRAG tuần này; “vài serial là shadow prediction”.

## Nhật ký — cái nào còn, cái nào bỏ

| Mục | Trạng thái |
|---|---|
| 1–11, 15–16 | **Nền LSU / nhân quả / Golden Knowledge** — còn hướng, chưa triển khai |
| 12 | RAG audit — còn (BGE-M3, không thay LightRAG ngay) |
| 13–14 LightRAG, R1–R5 | **Challenger sau** — không làm lúc này |
| 17 kết luận cũ | Bị **28 + bản đồ trên** thay |
| 18–21 | Còn: LSU không khóa sản phẩm; RAG + điều tra + agent một vòng |
| 22.1 đo E1/E2 | Còn (số đo lịch sử) |
| 22.6 hàng đợi cũ | **Hết** — dùng hàng đợi trong bản đồ trên |
| 23–24 docs tiếng Việt | Còn (luật ngôn ngữ) |
| 25 giữ sqlite cũ | **Hết** — đại tu mục 26 |
| 26–27 chỗ lưu / đổi chỗ | Còn |
| 28 bốn nhánh | Còn, đọc cùng bản đồ trên |
| 29 Drive cấm tuyệt đối | **Hết** — thay bằng 3 cầu nối (C-AGENT được gửi bản vẽ) |

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

Máy này dùng BGE-M3 hybrid trên CPU. Không có lựa chọn local tốt hơn trên i5 / 16 GB / không GPU.

Loader chỉ bật cho người dùng thường khi `activation_state = activated`. Chủ sở hữu đã bật. File báo cáo benchmark cũ trong `local_runs` có thể đã bị xóa; cửa còn lại là thư mục model + checksum/revision. Không đổi model.

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

## 18. Hướng mở rộng: LSU là lát cắt đầu tiên, không phải sản phẩm bị khóa cứng theo LSU

Mục tiêu dài hạn không phải một ứng dụng chỉ chẩn đoán LSU. AIOS phải vẫn giữ năng lực hỏi đáp tài liệu nội bộ, đồng thời có thể điều tra và dự đoán lỗi cho nhiều unit như LSU, drum, DLP, DP và cuối cùng là toàn bộ máy.

Vì vậy không nên thiết kế theo chuỗi bị khóa cứng:

```text
LSU RAG → LSU Graph → LSU Prediction
```

Thiết kế đúng là một platform trung lập với từng unit, trên đó LSU là vertical slice đầu tiên để kiểm chứng bằng dữ liệu công nghiệp thật:

```text
AIOS Diagnostic Platform
├─ Evidence RAG: BGE-M3 hybrid, citation, provenance
├─ Query planner: intent, entity, subquestion, required source type
├─ Case + EvidencePack: hồ sơ điều tra chung
├─ Typed evidence graph: candidate / verified / conflicting / unknown
├─ Expert review + Golden Knowledge lifecycle
├─ Structured log + time-series analysis
├─ Evaluation, shadow prediction, drift và rollback
└─ Machine topology: Machine → Unit → Subsystem → Component

Domain packs
├─ LSU pack
├─ Drum pack
├─ DLP pack
└─ DP pack
```

Mỗi domain pack mang phần đặc thù: schema log, defect taxonomy, JIG/instrument, giới hạn kỹ thuật, rule và KPI đánh giá. Core chỉ giữ các abstraction có thể tái dùng giữa nhiều unit.

### 18.1. Contract dữ liệu dùng chung

Machine topology cần mô tả được:

```text
Machine
└─ Unit: LSU | Drum | DLP | DP
   └─ Subsystem
      └─ Component
         └─ Parameter / lot / firmware / configuration
```

Mọi bằng chứng/sự kiện dùng contract chung:

```text
Measurement | LogEvent | Alarm | Maintenance | Retest
| ConfigurationChange | OperatorObservation | Experiment
```

Mỗi record bắt buộc có phạm vi asset, thời gian, nguồn, evidence coordinate, chất lượng dữ liệu và trạng thái tri thức. Ví dụ JIG-specific threshold thuộc LSU pack, nhưng khái niệm chung `measurement + spec limit + instrument/configuration + retest` thuộc core.

Nguyên tắc tổng quát hóa:

> Chỉ đưa vào core khi khái niệm đã xuất hiện ở ít nhất hai unit, hoặc chắc chắn thuộc cấu trúc vật lý chung của máy.

### 18.2. Contract dự đoán dùng chung

Model cho LSU và drum có thể khác nhau hoàn toàn; không nên ép dùng chung một model. Nhưng đầu ra và governance phải thống nhất:

```text
risk_of: defect/failure mode
asset_scope: machine / unit / component
horizon: thời gian hoặc số cycle
confidence + calibration
supporting evidence
known unknowns
recommended verification action
```

Nhờ đó ingestion, evidence, graph, expert review, shadow mode, drift monitoring và UI được tái sử dụng; khi thêm unit mới chủ yếu là thêm domain pack và model/feature pipeline riêng, không phải viết lại AIOS.

## 19. AIOS phải giữ đồng thời RAG nội bộ, điều tra kỹ thuật và Agent tools

Sản phẩm đích là một AI workspace duy nhất, không phải lựa chọn giữa RAG, industrial diagnosis và coding agent:

```text
Một UI / một chat
├─ Hỏi đáp tài liệu nội bộ (RAG)
├─ Điều tra kỹ thuật, case và dự đoán lỗi máy
└─ Agent gọi tool để thực hiện tác vụ có kiểm soát
```

RAG vẫn là lớp nền knowledge. Nó phục vụ các câu hỏi như quy trình bảo trì, SOP của drum/DLP, lịch sử incident hoặc tài liệu kỹ thuật; không bị thay bởi LSU engine. Điều tra LSU chỉ là một loại query có thêm structured data, time-series, graph và domain rules.

### 19.1. Ba mặt phẳng quyền

Không được để Agent có thể suy luận từ RAG rồi tự ý thực hiện hành động bất kỳ. Cần tách ba mặt phẳng:

| Mặt phẳng | Năng lực | Quyền mặc định |
|---|---|---|
| Knowledge | hỏi/đáp tài liệu, retrieval và citation | chỉ đọc |
| Investigation | phân tích case, graph, log, dự báo và đề xuất | chỉ đọc, tạo đề xuất |
| Action | tạo/sửa/xóa file, chạy lệnh, gọi hệ thống | chặn hoặc yêu cầu duyệt |

Luồng chuẩn:

```text
Người dùng hỏi hoặc mở case
→ RAG/structured engines lấy evidence
→ Investigation tạo giả thuyết và mức tin cậy
→ Agent tạo action proposal có scope rõ ràng
→ Policy kiểm tra quyền, rủi ro và target boundary
→ người dùng phê duyệt khi cần
→ tool thực thi trong sandbox/worktree
→ audit log và evidence cập nhật lại case
```

### 19.2. Agent giống IDE nhưng không có quyền vô hạn

Agent có thể đọc/tìm file, tạo report, sinh patch, sửa file hoặc chạy tool như các IDE hiện đại. Tuy nhiên quyền cần theo cấp:

| Cấp | Hành động | Chính sách |
|---|---|---|
| 0 | đọc file, search, RAG | tự động |
| 1 | tạo draft/report/patch trong sandbox | tự động hoặc thông báo |
| 2 | sửa file trong workspace/worktree | yêu cầu duyệt hoặc policy rõ ràng |
| 3 | xóa file, lệnh nguy hiểm, deploy, thao tác ngoài workspace | xác nhận rõ ràng và audit bắt buộc |

`/deep-dev` là ví dụ cho action cấp 2: tạo patch có boundary, kiểm thử trong worktree cách ly và trả evidence; không tự sửa main worktree. Cách này cho phép AIOS trở thành agent workspace mạnh mà vẫn giữ được provenance, khả năng rollback và trách nhiệm giải trình cần thiết cho dữ liệu nội bộ lẫn môi trường sản xuất.

## 20. Hệ quả cho lộ trình

LSU Evidence Case vẫn là bước thực thi đầu tiên vì nó buộc platform chứng minh các abstraction cốt lõi. Nhưng mọi schema, API và UI mới phải được review theo câu hỏi: đây là `AIOS Core` hay chỉ là `LSU pack`? Chỉ phần core mới được dùng chung; phần còn lại phải nằm trong pack/version riêng để không làm hỏng hoặc bắt viết lại hệ RAG và các unit khác trong tương lai.

## 21. Agent tools: nối kiến thức, điều tra và hành động thành một vòng có kiểm soát

Agent tools là “tay chân” của AIOS. RAG là trí nhớ có evidence; diagnostic/prediction engines là bộ phân tích định lượng; tool adapter là khả năng quan sát và thực hiện tác vụ. Không thành phần nào nên tự thay thế hai thành phần còn lại.

```text
Người dùng / kỹ sư
        ↓
AIOS Agent Orchestrator
        ├─ RAG: SOP, manual, incident, tài liệu nội bộ
        ├─ Tools: log, MES/QMS/PLC, ảnh, ticket, report
        ├─ Diagnosis: rule, correlation, graph, time-series
        ├─ Prediction: risk, horizon, calibration
        └─ Action policy: đề xuất / xin duyệt / thực thi có audit
        ↓
Case + EvidencePack + Audit trail chung
```

### 21.1. Giá trị cho điều tra lỗi line máy in

Ví dụ kỹ sư hỏi: “LSU-03 đang fail ở JIG 1035, kiểm tra giúp.” Agent có thể:

1. Gọi tool chỉ đọc để lấy serial, lot linh kiện, firmware, cấu hình JIG, log gần nhất, lịch sử retest và maintenance.
2. Dùng RAG tìm SOP, spec limit, tài liệu vendor và case tương tự.
3. Gọi engine phân tích để so sánh 1004/1035, kiểm tra drift và khác biệt theo lot/ca/operator.
4. Tạo hoặc cập nhật Case với từng kết luận được gắn trạng thái `verified`, `suspected`, `conflicting` hoặc `unknown`.
5. Đưa kết luận có điều kiện cùng evidence: ví dụ nghi ngờ JIG/configuration nhưng chưa đủ bằng chứng để kết luận component lỗi.
6. Tạo action proposal: report, ticket kỹ sư, yêu cầu re-test theo SOP hoặc một experiment/DOE được phê duyệt.

Kết quả không chỉ là câu trả lời ngôn ngữ tự nhiên mà là một hồ sơ điều tra có thể audit, tiếp tục bởi ca khác và dùng lại trong lần sau.

### 21.2. Giá trị cho dự đoán lỗi unit

Ví dụ: “Unit nào có rủi ro lỗi cao trong 24 giờ tới?” Agent lấy telemetry/time-series qua adapter, gọi prediction engine để chấm risk, dùng RAG để bổ sung bối cảnh kỹ thuật rồi trả về:

```text
rủi ro / failure mode
asset scope
horizon
confidence và calibration
evidence hỗ trợ
known unknowns
hành động kiểm tra đề xuất
```

Prediction không được tự biến thành kết luận nguyên nhân. Nó chỉ xếp ưu tiên kiểm tra; causal conclusion vẫn đòi hỏi evidence, chuyên gia và khi cần là đối chứng/DOE.

### 21.3. Giá trị cho hỏi đáp tài liệu nội bộ

Với câu hỏi như “Quy trình thay drum và lỗi thường gặp là gì?”, AIOS chỉ cần RAG và citation. Khi người dùng yêu cầu “tạo checklist bảo trì từ SOP”, Agent có thể sinh draft trong sandbox. Khi yêu cầu ghi vào CMMS/ticketing system hoặc thao tác lên thiết bị, Agent chuyển sang action proposal và áp dụng quyền/approval tương ứng.

Do đó RAG không bị hy sinh khi thêm industrial diagnosis hay Agent IDE; nó vẫn là lớp knowledge chung, còn mỗi task chỉ bật các engine/tool phù hợp.

### 21.4. Một contract vận hành chung

Ba năng lực cần hội tụ vào cùng một object thay vì ba lịch sử rời rạc:

```text
Case
├─ Asset scope: Machine / Unit / Component
├─ Question hoặc task
├─ Evidence: document, log, measurement, image, history
├─ Hypotheses + confidence
├─ Prediction (nếu có)
├─ Action proposals
├─ Human approvals
└─ Audit events
```

Mọi tool phải trả dữ liệu/evidence về Case hoặc EvidencePack; mọi câu trả lời phải liên kết evidence; mọi thao tác ghi, xóa, gửi ticket hoặc gọi hệ thống phải thành ActionProposal có scope, policy decision và audit event. Đây là điểm gộp thật sự của RAG, industrial AI và IDE agent.

### 21.5. Ranh giới an toàn cho tool trong môi trường sản xuất

Đọc dữ liệu máy và hệ thống có thể tự động theo quyền đọc. Các hành động thay đổi trạng thái — reset máy, đổi cấu hình JIG, dừng line, xóa log, gửi lệnh PLC, deploy hoặc thao tác ngoài workspace — phải ở cấp quyền cao, yêu cầu xác nhận của người được ủy quyền, audit bắt buộc và có fail-safe độc lập. Không cho phép một câu trả lời RAG trở thành lệnh trực tiếp điều khiển line.

Kết luận: AIOS nên là một **case-operating system**. RAG cung cấp tri thức, tools cung cấp quan sát/hành động, diagnosis/prediction cung cấp suy luận; policy, approval và audit bảo đảm hệ thống mạnh nhưng không nguy hiểm.

## 22. Phiên 2026-08-29 — Nền RAG, chia kho, ingest, Agent IDE

Phiên này chốt **nền tảng** trước khi mở dự đoán. Không mở cổng Phase 9 / P1.0. Không tạo file kế hoạch mới.

### 22.1. Việc RAG đã đo (corpus công khai bịa, không phải `local_only`)

- E1 baseline trên corpus công khai → E2 cắt câu CJK (`sentence_punctuation_v1`) đo **`improved`** trên corpus v2 (đoạn Nhật/Trung >900 ký tự). Mặc định chunker **ingest mới** dùng chính sách đó; **không** rebuild index Workspace Chat; production RAG vẫn `rolled_back`.
- `vi-002` (bảng Việt) trượt vì fixture ASCII (`nguyen lieu`) vs câu hỏi có dấu. Sửa bảng + `corpus_public_v3.json` → Recall@K **12/12**. Không mở E3 (overlap/summary): không có bằng chứng tóm tắt đẩy mất đoạn chi tiết.
- E2 v3 từng `rejected` vì p95 (một câu `vi-003` ~1006 ms, jitter CPU). Không đảo mặc định cắt câu vì một nhịp. Fingerprint v1/v2/v3 **không so được** với nhau.

Eval: `local_runs/chunk_evaluation/` (gitignored). Chi tiết task: `specs/006-chunking-evaluation/tasks.md`.

### 22.2. Vì sao ingest chậm — và chia sẻ index

BGE-M3 chạy CPU, `batch_size` mặc định 1, dense+sparse từng chunk. Hỏi sau khi có index ~0,7–1 s; phần chậm là **embed lần đầu**.

Quy mô thư mục (chỉ đếm metadata, không đọc nội dung vào git):

- MOM `tailieugoc/`: khoảng 73 file, ~95 MB.
- LSU + log `Tài liệu của tất cả dòng máy/`: khoảng 888 file, ~1,15 GB, trong đó **~783 CSV**.

Hiện Workspace Chat **không** tạo SQL riêng theo sổ. Sổ chat = JSONL trong `local_cases/workspace_chat/`. Index RAG thường **một** `workspace_chat.sqlite` / máy / profile. Nhiều người cùng ingest một thư mục sẽ khóa SQLite (một writer).

Hướng đúng: **một máy ingest thư viện đã lọc → niêm (checksum + model + chunker) → máy khác mở chỉ đọc**. Sản phẩm chưa có nút xuất thư viện. Query path đã `index_read_only`.

### 22.3. CSV log không nhét vào RAG — không làm dự đoán LSU bị cắt

Hai việc khác nhau:

| Việc | Dữ liệu | Kho |
|---|---|---|
| Hỏi–đáp / tra cứu | MOM, SOP, ISO, Excel chuẩn, slide | Index RAG (đoạn văn) |
| Theo dõi / dự đoán LSU | Log JIG, serial, OK/NG, time-series | **Bảng có schema**, không cắt 900 ký tự rồi embed |

Nhét 783 CSV vào cùng index với MOM làm retrieval nhiễu và ingest hàng giờ. Đó **không** phải “vứt log”: log vẫn cần cho LSU, nhưng là engine số liệu. RAG giải thích spec/field; bảng log trả lời “serial X có drift không”.

Sản phẩm hiện tại **chưa** là công cụ dự đoán vận hành (`docs/AIOS_PRODUCT_POSITIONING.md`, `DEPRECATION_PAUSE_LIST.md`). Giai đoạn 0 = trí tuệ tài liệu đáng tin.

### 22.4. Sổ ≠ SQL — đơn vị tách là thư viện (collection)

Tạo sổ MOM **không** ra file SQL riêng.

Đơn vị đúng:

```text
Kernel RAG (converter, chunker, BGE-M3, FTS, evidence, citation)
    ├── sqlite_knowledge     MOM / ISO / tri thức kiểm chứng   ← chia sẻ được
    ├── sqlite_unit_docs     tài liệu LSU / Drum / DLP
    ├── sqlite_lsu_metrics   đo lường / log JIG (bảng)
    └── sqlite_line_dc       điều tra line / điều chỉnh
                             (tham chiếu project phantichphanmemdc)
```

Sổ chat chỉ **trỏ** vào thư viện. Không: một SQL khổng lồ. Không: mỗi sổ một SQL.

Ba nhánh cùng kernel, khác kho:

1. AI dự đoán / phòng ngừa lỗi LSU → sau này Drum, DLP… (bảng số + RAG giải thích).
2. AI điều tra lỗi line (máy, điều chỉnh) — `D:\Sandbox\phantichphanmemdc`.
3. AI tra cứu tri thức nội bộ đã kiểm chứng = RAG.

Bước hiện tại: **nâng nền RAG + chia kho**, vì còn yếu và lưu trữ đang lẫn.

### 22.5. Agent IDE / nvidia-server — nối được, là lớp hành động

Runtime NVIDIA là repo kế thừa (`nvidia-server`), cầu nối mặc định `workspace_agent_bridge_client` → `...\Nvidia\tools\workspace-agent-bridge.mjs`. Policy trong `workspace_agent_policy.py`:

- Cho phép đọc: `list_dir`, `read_file`, search, git status/diff/log, `index_search`…
- Sửa **phải duyệt**: `write_file`, `apply_patch`, `execute_command`
- **Cấm**: `delete_file`, `move_file`, `git_commit`, `git_push`
- Tối đa 8 bước tool / lượt. Giai đoạn 5 IDE bridge chưa mở full; cấm AI tự sửa không duyệt.

Vòng: Bằng chứng (RAG/bảng) → đề xuất → người duyệt → tool → audit → bài học. Không để câu trả lời RAG thành lệnh PLC/đổi spec.

Tự học = phiếu chuyên gia / case eval local, promote tường minh (`agent_learning.py` chỉ hash, không nhúng `local_only`). Không train âm thầm từ một click.

### 22.6. Thứ tự làm (một hàng đợi)

1. Nền RAG + **collection = một SQLite** (sổ là con trỏ). Loại CSV log khỏi thư viện hỏi–đáp.
2. Index nhóm chỉ đọc (một ingest, nhiều người hỏi) trên MOM + tài liệu dòng máy (không CSV).
3. Hoàn thiện Agent IDE có duyệt: báo cáo lỗi, patch, spawn có ngân sách — không swarm vô hạn.
4. Pilot line điều tra (`phantichphanmemdc`) rồi pilot vài serial LSU **có schema**.
5. Cảnh báo / shadow prediction — sau khi Giai đoạn 0–1 đủ bằng chứng. Không mở E3 khi chưa có lỗi overlap đo được. Không reranker mặc định (latency CPU). Không GPU như phụ thuộc sản phẩm.

### 22.7. Quản lý file — đã dọn rác gì, không dọn gì

Dọn (rác runtime / debug, không phải tài liệu canonical):

- `tmp_run_out.log`, `tmp_run_out2.log`, `tmp_run_out3.log`, `tmp_run_out4.log` (đã có trong `.gitignore` `*.log`).
- `scratch/*.py` (script debug index một lần; `/scratch/` đã gitignore nhưng từng bị commit).
- `.antigravityrules` (file rỗng).

**Không** xóa: `CONSTITUTION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `specs/`, `docs/adr/`, `docs/archive/` (lịch sử), thư mục `tailieugoc/` và `Tài liệu của tất cả dòng máy/` (dữ liệu chủ sở hữu), `architecture_viewer.html` (artifact lớn, hỏi chủ sở hữu trước khi gỡ khỏi git).

Không tạo file kế hoạch mới cho các ý trong mục 22. Cập nhật hành vi sản phẩm thì sửa canonical trong **cùng lượt code**, theo `docs/DOCUMENTATION_GOVERNANCE.md`.

## 23. Phiên 2026-08-29 — Tài liệu phình / phân tán (chờ chủ sở hữu chọn đợt)

Khoảng **320** file `.md` (không kể `.venv` / `local_*` / tài liệu nhà máy). Gốc repo **32** file luật/tư tưởng. `docs/` **149**. `specs/` **68**. `docs/archive/` **48** (đúng là lịch sử). Không tạo chỉ mục cạnh tranh với `docs/PROFESSIONALIZATION_INDEX.md`.

Nguyên nhân AI đọc lần đầu bị lẫn: nhiều file **cùng chủ đề, khác lời** (`CONSTITUTION` vs `PRODUCT_NORTH_STAR` vs `docs/AIOS_PRODUCT_POSITIONING.md`; `ARCHITECTURE.md` vs `WORKLENS_ARCHITECTURE.md`; `AGENT_RULES.md` vs `AGENTS.md` vs `00_governance/`; folder `00_`–`12_` song song `docs/`).

Cách làm (không big-bang): **lớp đọc L0→L3** + archive stub, không xóa lịch sử.

**Đã thực thi đợt 1+2 (cùng ngày):** `AGENTS.md` L0–L3 và danh sách không đọc lần đầu; stub `WORKLENS_ARCHITECTURE.md`, `PRODUCT_NORTH_STAR.md`; `CONSTITUTION.md` §9; `AGENT_RULES.md` dẫn `DATA_POLICY.md`; biển RETIRED trên cây `00_`–`12_`; cập nhật `docs/DOCUMENTATION_GOVERNANCE.md` và `docs/PROFESSIONALIZATION_INDEX.md`. Đợt 3 (gầy specs đã đóng) **chưa** làm.

## 24. Việc tiếp theo và ngôn ngữ tài liệu (2026-08-29)

**Bước sản phẩm tiếp theo (sau nền RAG + gộp lối vào tài liệu):** thiết kế rồi làm **collection = một SQLite** (sổ chat chỉ là con trỏ) và **index nhóm chỉ đọc** — ingest một lần, nhiều người hỏi. Loại CSV log khỏi thư viện hỏi–đáp. Không mở E3. Không rebuild index Workspace Chat cho đến khi có collection. Không kích hoạt production RAG (`rolled_back`).

**Ngôn ngữ (luật khóa, 2026-08-29):** câu văn tài liệu sản phẩm **phải tiếng Việt**. Nguồn: `CONSTITUTION.md` nguyên tắc 6, `AGENT_RULES.md` mục 4, `docs/DOCUMENTATION_GOVERNANCE.md`. Cấm tiêu đề/đoạn văn tiếng Anh; cấm thêm Anh khi sửa file. Token được giữ: đường dẫn, lệnh, tên mã, `Status:`/`PASS`, hằng `local_only`. Không bắt buộc dịch hết `docs/archive/` một lượt; không viết thêm tiếng Anh vào đó.

## 25. Lát đầu collection (2026-08-30)

Sổ chat trỏ `collection_id`. Thư viện mặc định `tri_thuc` = kho `workspace_chat.sqlite` cũ (không rebuild, không bắt ingest lại). Thư viện mới = `collections/<id>/library.sqlite`. Hỏi/nạp nguồn đi theo thư viện của sổ. CSV log vẫn ngoài RAG. Chưa làm nút xuất USB; chưa bảng đo LSU.

## 26. Đại tu vị trí thư viện chung (2026-08-30)

Việc đúng làm trước: **chọn chỗ để tủ**, không giữ kho cũ trộn lẫn và không lấy “xuất file” làm bước 1.

- Bỏ mặc định `workspace_chat.sqlite`. Thư viện có thư mục riêng; `index_filename` chỉ là `library.sqlite`.
- Nút **Vị trí thư viện chung**: chọn/dán thư mục (ổ D, ổ mạng). Kho nằm tại `<thư mục>/aios_thu_vien/library.sqlite`.
- Một máy nạp; máy khác chọn **cùng đường dẫn** rồi hỏi. Xuất USB vẫn hữu ích khi không có ổ mạng — làm sau.
- CSV log vẫn ngoài thư viện hỏi–đáp. Phải nạp lại tài liệu vào thư viện mới (đại tu).

## 27. Đổi chỗ lưu, các case kho, ảnh/bản vẽ, điều tra line (2026-08-30)

Đổi vị trí thư viện: **có**. Lưu chỗ mới thì **copy** `aios_thu_vien` sang; bản cũ giữ. Chỗ mới đã có kho khác → từ chối (không trộn). Máy đồng nghiệp phải chọn đường dẫn mới.

Các case lưu: (1) chỉ máy này, (2) thư mục dùng chung, (3) đổi chỗ = copy, (4) chỗ mới đã có kho khác = chặn, (5) USB/offline = xuất sau, (6) CSV log = kho số liệu riêng, không phải thư viện hỏi–đáp.

Ảnh/sơ đồ/scan: thiếu chữ thì RAG ảo giác. Hướng đúng = lớp đọc ảnh **trước** khi hỏi (OCR/mô tả có cấu trúc đã có mầm trong converter) và **đối chiếu bằng chứng sau**. Không train model riêng. Không gửi bản vẽ `local_only` lên mây. Chữ viết tay/scan kém = người xác nhận.

Điều tra lỗi line (máy in): không “train AI” kiểu nhồi hết file. Tách (a) tài liệu tra cứu: nguyên lý, triển khai, SOP, mã lỗi, báo cáo sự vụ đã duyệt; (b) log có schema; (c) ảnh/bản vẽ → text có cấu trúc rồi mới vào thư viện. `phantichphanmemdc` là lớp điều tra, không nhét chung MOM.

## 28. Bản đồ case tương lai (thời điểm thảo luận 2026-08-30)

Đây là **hình dạng nếu thành hình**, không phải cam kết đã làm xong. Một kernel: thư viện + bằng chứng + người duyệt. Không một SQLite cho tất cả. Không train âm thầm. Không tự chặn xuất hàng.

### 0. Nền dùng chung (mọi nhánh đều cần)

| Case | Việc người dùng | Hệ thống làm |
|---|---|---|
| Thư viện chung | Chọn chỗ lưu (ổ D / mạng) | Kho `aios_thu_vien/library.sqlite` |
| Đổi chỗ lưu | Chọn thư mục mới | Copy kho; bản cũ giữ; chỗ mới đã có kho khác thì chặn |
| Máy khác hỏi | Cùng đường dẫn | Chỉ đọc, không embed lại |
| USB / không chung ổ | (sau) xuất bản sao | Photocopy có niêm checksum |
| Ảnh / scan / bản vẽ | Nạp file | OCR/mô tả có cấu trúc **trước** khi hỏi; đối chiếu bằng chứng **sau**; chữ viết tay người xác nhận |
| CSV / log máy | Không nhét vào hỏi–đáp | Kho số liệu có cột (schema) |
| Người duyệt | Chốt bài học / spec / OK-NG | Mới thành tri thức; một click không train |

---

### 1. Hỏi–đáp tài liệu nội bộ (chống mất tri thức khi người cũ nghỉ)

Mục đích: hỏi được SOP, MOM, ISO, hướng dẫn dòng máy **có trích dẫn**, không phụ thuộc “anh ấy nhớ”.

| Case | Ví dụ |
|---|---|
| Tra cứu quy trình | “Hạng mục nhập kho gồm những mục nào?” |
| Tra cứu spec / ISO | Giới hạn đã ban hành, không đoán |
| Bảng Excel chuẩn | Tiêu chuẩn nguyên liệu, checklist |
| MOM / họp | Quyết định đã ghi, không tin trí nhớ miệng |
| Đa ngôn ngữ | Việt / Nhật / Trung — cắt đúng câu |
| Người mới | Hỏi như người cũ; hệ thống chỉ trả lời có nguồn |
| Chống trôi | File đổi fingerprint → nạp lại đoạn đó, không mất cả thư viện |
| Ảo giác vì thiếu ảnh | Sơ đồ/scan chưa đọc → không bịa; thiếu thì nói thiếu |

**Chưa phải:** chatbot tán gẫu; NotebookLM trên mây; nhét 783 CSV vào cùng tủ.

---

### 2. Dự đoán / phòng chống lỗi unit (LSU, sau này Drum, DLP…)

Mục đích: cảnh báo **có căn cứ** (drift JIG, lô giống lần NG), người quyết. Không phải AI tự dừng chuyền.

| Case | Ví dụ |
|---|---|
| Hồ sơ serial | Thông số ↔ log JIG ↔ OK/NG |
| Cảnh báo sớm | Drift, lô nghi ngờ — mức rủi ro, không phán xuất hàng |
| Phòng ngừa | Gợi ý kiểm tra đã được người duyệt |
| Unit mới | Drum, DLP = **thư viện + bảng số mới**, không fork RAG |
| Thiếu dữ liệu | Nói thiếu; không bịa nguyên nhân gốc |

**Cần trước:** schema log, vài serial có nhãn, thư viện spec. **Cấm:** tự chặn hàng; train từ một click.

---

### 3. Điều tra lỗi phát sinh trên line (máy in, điều chỉnh…)

Mục đích: cùng kỹ sư lần vết — mã lỗi, công đoạn, log, bản vẽ — ra **báo cáo sự vụ có bằng chứng**. Tham chiếu hướng `phantichphanmemdc`.

| Case | Tài liệu / dữ liệu |
|---|---|
| Tra cứu khi dừng máy | SOP, mã lỗi, nguyên lý, tài liệu triển khai (nếu được phép) |
| Log máy / điều chỉnh | CSV có cột, serial, thời điểm — **không** embed từng dòng |
| Ảnh lỗi / bản vẽ scan | OCR + người rà chữ viết tay |
| Hồ sơ vụ | Việc đang làm: đã thử gì, ảnh, serial |
| Báo cáo | Agent soạn phiếu; người ký |
| Bài học | Chỉ báo cáo đã duyệt mới vào thư viện |

**Không:** nhồi mọi log để “train AI điều tra”.

---

### 4. Agent kiểu IDE (tay làm việc, không thay thư viện)

Mục đích: sau khi có bằng chứng, **đề xuất hành động** — báo cáo, SOP nháp, biểu đồ, lệnh — **người duyệt**. NVIDIA/tool đã có mầm; xóa/sửa file nhà máy **cấm** không duyệt.

| Case | Agent được / không |
|---|---|
| Đọc / tìm file, git status | Được |
| Sửa file, chạy lệnh | Phải duyệt |
| Xóa / đổi tên / git push | Cấm |
| Xuất log, vẽ biểu đồ | Đọc bảng số liệu; không nhét CSV vào RAG |
| Báo cáo lỗi / SOP nháp | Soạn từ evidence pack; người ban hành |
| Spawn agent | Có ngân sách bước; không swarm vô hạn |
| Tự học | Phiếu chuyên gia / case eval; không train âm thầm |

---

### Thứ tự nếu thành hình

1. Thư viện hỏi–đáp + chỗ lưu chung + nạp tài liệu (không CSV).
2. Ảnh/scan có kiểm chứng.
3. Agent soạn báo cáo / SOP có duyệt.
4. Log có schema + điều tra line.
5. Cảnh báo / shadow dự đoán LSU → Drum/DLP.

Cùng kernel, khác tủ. Sản phẩm hiện tại **chưa** là công cụ dự đoán vận hành. Tìm kiếm local dùng BGE-M3 hybrid trên CPU.

## 29. Phân tích khả thi ý tưởng điều tra line (file idea.md, 2026-08-30)

Nguồn: trao đổi Vinh–Hải, thí điểm C call / Jam call. Kết luận: **pilot hỗ trợ điều tra làm được** nếu đi đúng cầu nối AI của công ty.

### Ba nguồn AI trong chương trình (chốt 2026-08-30)

Công ty đã mua C-AGENT (Việt Nam), cam kết bảo mật. Không cấm gửi tài liệu kỹ thuật theo kiểu “không được lên mây”; **cấm sai cầu nối**.

| Cầu nối | Gửi gì |
|---|---|
| **1. Nakazasen Router** | Văn bản / hỏi đáp thường. **Không** gửi bản vẽ, sơ đồ mạch, scan bản vẽ. |
| **2. Gemini Web** | Văn bản / hỏi đáp thường. **Không** gửi bản vẽ, sơ đồ mạch. |
| **3. C-AGENT — Sonnet 4 công ty** | **Được gửi đủ:** sơ đồ mạch, log, báo cáo lỗi, tool mô tả, ảnh VPS, Excel IQC. Đây là đường cho gói điều tra line. |

Sao lưu log (K-Box 30 ngày xóa): Drive **nội bộ công ty** hoặc thư viện chung trên ổ D đều được — miễn gói đầy đủ khi hỏi AI thì mở **C-AGENT / Sonnet 4**, không dán bản vẽ vào Router hay Gemini Web.

- **Làm được (hỗ trợ, không thay kỹ sư):** gợi ý hướng điều tra + chuỗi nhân quả *ứng viên* từ log đã parse + mã lỗi + báo cáo cũ; khoanh vùng sơ đồ *nếu có bảng ánh xạ* sensor/mã → vị trí bản vẽ; cứu “mất hiện trạng khi tháo máy” nếu đã lưu log trước khi tháo.
- **Không hứa:** chỉ đúng từng sensor; đọc chữ viết tay IQC (vẫn gõ Excel hoặc bỏ); Jam log “luôn đúng” (Hải đã nói độ tin chưa cao).
- Soft bản mạch / controller phía Thiết kế không cấp: **không bắt buộc** cho pilot. Phân giải **định dạng log + tool đang dùng nội bộ** (so output tool với parser) thì đủ để bắt đầu nhánh C hoặc Jam.
- Thứ tự: (1) Hải tập hợp gói tài liệu, (2) parser Jam hoặc C, (3) thư viện SOP/mã lỗi/báo cáo đã duyệt, (4) bảng ánh xạ sơ đồ, (5) overlay có người xác nhận. Hỏi có bản vẽ → chọn **C-AGENT**. Không nhét log thô vào RAG chữ.
