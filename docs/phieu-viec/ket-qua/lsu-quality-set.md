# Bộ câu hỏi đo chất lượng câu trả lời LSU (LSU Quality Evaluation Set)

> **BẢN THẢO — CHƯA QUA CHUYÊN GIA DUYỆT**
> 
> - **Vé thực hiện:** `PREP-LSU-QUALITY-PC0575`
> - **Máy thực hiện:** `[CTY] KDTVN-PC0575` (thợ `agy` — Antigravity CLI)
> - **Mục đích:** Chuẩn bị bộ 50 câu hỏi chuẩn hóa và khung rubric chấm điểm khách quan thang 0–3 để thợ OMP chạy đo nghiệm thu ở vé `LSU-QUALITY-PC0575`.
> - **Nguồn dữ liệu:** `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (chỉ lọc đọc, không sửa JSONL, không tự tạo câu hỏi ngoài dữ liệu).

---

## 1. Thống kê dữ liệu thực tế trích xuất

- **Tổng số dòng trong JSONL:** 3392 dòng.
- **Số cặp `category=LSU`:** 1790 cặp (đếm thực tế từ dữ liệu, khớp 100% kỳ vọng 1.790 cặp).
- **Phạm vi mẻ (batch):** 39 mẻ (từ `batch-16` đến `batch-54`), dải ID từ `Q0609` đến `Q2408`.
- **Cơ cấu ngôn ngữ trong tập LSU:** Tiếng Việt: 604 câu (33,7%), Tiếng Nhật: 575 câu (32,1%), Tiếng Trung/Kanji: 611 câu (34,1%).
- **Số câu chọn lọc đo chất lượng:** **50 câu đại diện**, phủ đều 4 nhóm nghiệp vụ sản xuất cốt lõi:
  - **Mã lỗi:** 13 câu (26%)
  - **Nguyên nhân:** 12 câu (24%)
  - **Đối sách:** 12 câu (24%)
  - **Thông số kỹ thuật:** 13 câu (26%)

---

## 2. Khung Rubric chấm điểm chất lượng (Thang 0–3)

Thang điểm chuẩn hóa 4 mức độ từ 0 đến 3 điểm áp dụng cho mô hình/agent trả lời câu hỏi nghiệp vụ LSU:

| Điểm | Mức độ | Định nghĩa tiêu chuẩn | Tiêu chí đánh giá cụ thể |
|:---:|:---|:---|:---|
| **0** | **Sai trọng tâm / Không đạt** | - Trả lời sai sự thật, bịa đặt số liệu (hallucination).<br>- Lạc đề, không trả lời đúng câu hỏi đặt ra.<br>- Báo lỗi hệ thống hoặc từ chối trả lời vô lý. | Không trúng câu hỏi; đưa ra phán đoán ngược hoàn toàn với tài liệu kỹ thuật; tự ý kết luận nguyên nhân/trạng thái khi dữ liệu không cho phép. |
| **1** | **Gần đúng / Thiếu ý chính** | - Đề cập đúng chủ đề nhưng thiếu các thông số kỹ thuật then chốt.<br>- Thiếu điều kiện biên, thiếu bước thao tác quan trọng.<br>- Không nêu được ranh giới rõ ràng giữa dữ liệu đo và suy diễn. | Trả lời được ý khái quát nhưng sai lệch số liệu nhỏ; thiếu 1 trong các bước đối sách bắt buộc; chưa phân biệt được ngưỡng cảnh báo và ngưỡng hỏng. |
| **2** | **Đúng / Đạt chuẩn** | - Trả lời chính xác, đầy đủ các ý chính của đáp án tham chiếu.<br>- Nêu đúng các thông số số liệu, đơn vị đo, màu sắc, máy/JIG liên quan.<br>- Giữ đúng nguyên tắc kỹ thuật: phân định rõ sự thật thực đo và giả định. | Đầy đủ nội dung cốt lõi; đúng toàn bộ thông số then chốt (số dot, mm, µm, mA, thời gian, tên linh kiện, tên JIG); giải thích logic phù hợp với đáp án tham chiếu. |
| **3** | **Xuất sắc / Có trích dẫn nguồn** | - Đạt toàn bộ tiêu chuẩn của **Mức 2**.<br>- **Đồng thời trích dẫn chính xác tên tài liệu nguồn** (`.xlsx`, `.pptx`, `.csv`, `.pdf`...) làm bằng chứng kiểm chứng. | Đáp ứng hoàn hảo Mức 2 và có câu dẫn nguồn minh bạch (ví dụ: `Nguồn file: Sirius 2 _ C7620_報告版 4.pptx` hoặc `2026_08_Spec.csv`), giúp kỹ sư nhà máy tra cứu ngay tài liệu gốc. |

### Hướng dẫn chấm điểm đặc thù theo từng nhóm:
1. **Nhóm Mã lỗi:** Bắt buộc phải đúng mã lỗi (ví dụ `C7620`, `BowOverAdjustment`), màu sắc phát sinh lỗi (Magenta, Cyan, Yellow), tỷ lệ NG và điều kiện phát sinh.
2. **Nhóm Nguyên nhân:** Đánh giá cao câu trả lời biết tôn trọng tính khách quan của dữ liệu — nếu dữ liệu ghi 'chưa đủ căn cứ khẳng định một nguyên nhân duy nhất' thì câu trả lời cũng phải khẳng định tương tự, không được tự suy đoán bừa bãi.
3. **Nhóm Đối sách:** Bắt buộc đúng quy cách kỹ thuật (ví dụ dán SIM tape 40 µm tại điểm 119.h2, re-correlation Jig 1035 trước khi chỉnh Unit) và đúng quy tắc bảo toàn dữ liệu đo (giữ nguyên Raw value 0, 999, 9999.9, `--`).
4. **Nhóm Thông số kỹ thuật:** Bắt buộc đúng số liệu danh định (nominal), dung sai (tolerance), cận trên/cận dưới và đơn vị đo (mm, µm, dot, mA, rpm, °C).

---

## 3. Bảng 50 câu hỏi đo chất lượng LSU chi tiết

### 3.1. Nhóm Mã lỗi (13 câu)
*Các câu hỏi về nhận diện mã lỗi (C7620, BowOverAdjustment, Beam NG, Tilt NG...), phân loại lỗi, phân bố lỗi theo màu, theo thời gian, tỷ lệ lỗi trên JIG và phán định trạng thái sản xuất.*

| STT | ID | Câu hỏi | Đáp án tham chiếu | Nguồn file trích dẫn | Trọng tâm kiểm tra (Tiêu chí đạt Mức 2 & 3) |
|:---:|:---:|:---|:---|:---|:---|
| 1 | **Q0699** | C7620中Magenta相对Black的副扫描色差达到多少会成为NG？ | 资料说明色补正后，M（Magenta）相对Bk（Black）的副扫描方向色差超过`70 dot`时判定NG；`70 dot以内`为OK范围。来源文件：`Sirius 2 _ C7620_報告版 4.pptx`. | `lsu/batch-17.md` (Batch 17) | Ngưỡng lệch màu phụ C7620判定 NG giữa Magenta và Black (quá 70 dot) |
| 2 | **Q0700** | C23とC24ではどのような発生Trendでしたか。 | `2月19日`にC23/C24でNG率が同じTrendで同時に上昇し、発生色は`Magenta`です。出典ファイル：`Sirius 2 _ C7620_報告版 4.pptx`. | `lsu/batch-17.md` (Batch 17) | Xu hướng phát sinh lỗi C7620 tại C23 và C24 ngày 19/2 ở màu Magenta |
| 3 | **Q0703** | B距離が長くなる想定状態は何ですか。 | ①Mの光路高さが通常よりプラス側へずれる、②Bkの光路高さがマイナス側へずれる、③その両方が同時にずれる、という3状態が示されています。B距離が長いほどC7620 M色Errorが出やすいとしています。出典ファイル：`Sirius 2 _ C7620_報告版 4.pptx`. | `lsu/batch-17.md` (Batch 17) | Trạng thái khoảng cách B dài ra làm phát sinh lỗi C7620 màu Magenta |
| 4 | **Q0708** | 光路高さ1.15 mmを超えると必ずCamera読取不能になりますか。 | いいえ。資料では`1.15 mm以上`はC7620発生可能性があるLevelで、Camera読取範囲外になる目安は`1.24以上`と記載されています。この2つのThresholdを区別する必要があります。出典ファイル：`Sirius 2 _ C7620_報告版 4.pptx`. | `lsu/batch-17.md` (Batch 17) | Phân biệt ngưỡng rủi ro lỗi 1.15 mm và ngưỡng mất tín hiệu Camera 1.24 mm |
| 5 | **Q0849** | File có bao nhiêu record lỗi và phạm vi ngày nào? | Có`3.153 record`, từ`2026/08/01` đến`2026/08/25`, liên quan tới`1.252 Serial` khác nhau. Tất cả record có Abstract=`BowOverAdjustment`. Nguồn file: `2026_08_Error_BowOverAdjust.csv`. | `lsu/batch-21.md` (Batch 21) | Số lượng record lỗi và phạm vi ngày của log BowOverAdjustment |
| 6 | **Q0850** | Yellow、Cyan、Magenta分别有多少件？ | Yellow=`1304件`、Cyan=`1035件`、Magenta=`814件`。Yellow最多。来源文件：`2026_08_Error_BowOverAdjust.csv`. | `lsu/batch-21.md` (Batch 21) | Phân bố số lượng lỗi theo màu Yellow, Cyan, Magenta trong file BowOverAdjust |
| 7 | **Q0851** | このFileにはBlackのErrColorもありますか。 | ありません。ErrColorとして確認できるのはYellow、Cyan、Magentaの3色で、Blackは`0件`です。出典ファイル：`2026_08_Error_BowOverAdjust.csv`. | `lsu/batch-21.md` (Batch 21) | Kiểm tra sự xuất hiện của lỗi ErrColor màu Black trong BowOverAdjust (0件) |
| 8 | **Q1029** | Error Fileには何Record、何Serialありますか。 | `183 Record`、`109個の異なるSerial`があり、期間は`2026/08/01～2026/08/26`です。Modeは全183件で`Error`です。出典ファイル：`2026_08_Error.csv`. | `lsu/batch-25.md` (Batch 25) | Tổng số record lỗi và serial trong 2026_08_Error.csv (183 record, 109 serial) |
| 9 | **Q1034** | 哪一天Error Record最多？ | `2026/08/11`最多，有`34笔`；之后为`08/12=22`、`08/18=16`、`08/21=12`、`08/25=10`。来源文件：`2026_08_Error.csv`. | `lsu/batch-25.md` (Batch 25) | Ngày phát sinh số lượng record lỗi nhiều nhất trong tháng 8 (11/08/2026) |
| 10 | **Q0620** | 2026年3月のBOWSKEW 4 BEAM NG率はいくつですか。 | 資料ではIris Jig BOWSKEW 4 BEAMが25.42%から上昇し、2026年3月に49.49%へ達したと説明されています。出典ファイル：AI cảnh báo lỗi LSU.pptx. | `lsu/batch-16.md` (Batch 16) | Tỷ lệ NG của JIG trọng điểm BOWSKEW 4 BEAM tháng 3/2026 (49.49%) |
| 11 | **Q0621** | Tỷ lệ NG của ba JIG trọng điểm khác nhau thế nào? | Tháng 03/2026, BOWSKEW 4 BEAM = 49,49%, BOWSKEW 2 BEAM = 25,04%, và BEAM 4 BEAM = 20,56%. Vì vậy BOWSKEW 4 BEAM có mức NG cao nhất. Nguồn file: AI cảnh báo lỗi LSU.pptx. | `lsu/batch-16.md` (Batch 16) | So sánh tỷ lệ NG giữa 3 JIG Iris trọng điểm (BOWSKEW 4, BOWSKEW 2, BEAM 4) |
| 12 | **Q0824** | `61C1068E7022`は8月12日と13日で判定Patternが変わりましたか。 | 変わっていません。両方ともTotal=`NG`、Black=`OK`、Magenta=`OK`、Cyan=`NG`、Yellow=`OK`です。出典ファイル：`2026_08_UnitTest.csv`. | `lsu/batch-21.md` (Batch 21) | Thay đổi pattern phán định của serial 61C1068E7022 giữa ngày 12 và 13/8 |
| 13 | **Q0689** | Điểm bất thường được phát hiện ở Jig nào và vị trí Camera nào? | Bất thường được ghi nhận trên `Jig Bow_Skew 1035` tại vị trí `Camera +140`: đường kính tia Beam có dấu hiệu to lên trong vùng đánh giá Beam diameter. Nguồn file: `Y_BeamH_Camera 140_to bất thường.pptx`. | `lsu/batch-17.md` (Batch 17) | Bất thường đường kính Beam tại Camera +140 trên Jig Bow_Skew 1035 |

### 3.2. Nhóm Nguyên nhân (12 câu)
*Các câu hỏi điều tra nguyên nhân gốc rễ (RCA), cơ chế gây lỗi, phân tích tương quan dữ liệu, tránh quy kết sai lầm từ dữ liệu đơn lẻ và làm rõ bản chất vật lý/quang học.*

| STT | ID | Câu hỏi | Đáp án tham chiếu | Nguồn file trích dẫn | Trọng tâm kiểm tra (Tiêu chí đạt Mức 2 & 3) |
|:---:|:---:|:---|:---|:---|:---|
| 14 | **Q0704** | Sau ngày bảo dưỡng khuôn 14/2, Housing màu Magenta có điểm gì đáng chú ý? | Tài liệu ghi góc MIRROR của Magenta sau ngày bảo dưỡng khuôn `14/2` đã ra ngoài range của thời kỳ ổn định ở cả ba vị trí `MIRROR A`, `MIRROR BOW` và `MIRROR C`. Nguồn file: `Sirius 2 _ C7620_報告版 4.pptx`. | `lsu/batch-17.md` (Batch 17) | Hiện tượng góc Mirror Magenta ra ngoài dải ổn định sau bảo dưỡng khuôn 14/2 |
| 15 | **Q0701** | Hiện tượng tại LSU Line được mô tả như thế nào? | Khi bắt đầu điều chỉnh trên BOWSKEW jig, chiều cao quang lộ lệch thêm về phía dương nên `Camera -90` không đọc được vị trí Beam. Vấn đề xảy ra trên LSU Magenta. Nguồn file: `Sirius 2 _ C7620_報告版 4.pptx`. | `lsu/batch-17.md` (Batch 17) | Chiều cao quang lộ lệch dương khiến Camera -90 không đọc được tại line LSU |
| 16 | **Q0718** | File có xác nhận chênh lệch DMT–PMT chính là nguyên nhân duy nhất gây NG không? | Không. File cung cấp dữ liệu Skew, chênh lệch giữa DMT/CN/PMT và quy luật Light Path, nhưng phần dữ liệu đọc được không xác nhận đây là nguyên nhân duy nhất của NG. Nguồn file: `sirius2 beam径確認_240202.xlsx`. | `lsu/batch-18.md` (Batch 18) | Phân tích chênh lệch DMT–PMT có phải nguyên nhân duy nhất gây NG không |
| 17 | **Q0828** | Có thể khẳng định Black Skew là nguyên nhân duy nhất của mọi Total NG trong file không? | Không. Có record Total NG nhưng Black vẫn `OK`, ví dụ `61C1068E6778` hoặc `61C1068E7022`; lỗi có thể nằm ở Cyan/Yellow. File không xác nhận Black Skew là nguyên nhân duy nhất. Nguồn file: `2026_08_UnitTest.csv`. | `lsu/batch-21.md` (Batch 21) | Phân tích Black Skew có phải nguyên nhân duy nhất của mọi Total NG không |
| 18 | **Q0858** | Yellow nhiều record nhất có đồng nghĩa Yellow là nguyên nhân gốc duy nhất không? | Không. File chỉ ghi log lỗi `BowOverAdjustment` theo màu và số liệu liên quan; Yellow có số record cao nhất nhưng tài liệu không xác nhận nó là root cause duy nhất của mọi NG. Nguồn file: `2026_08_Error_BowOverAdjust.csv`. | `lsu/batch-21.md` (Batch 21) | Yellow nhiều record nhất có đồng nghĩa là nguyên nhân gốc duy nhất không |
| 19 | **Q0685** | Bracketの測定値を見るだけで斜め光NG原因を確定できますか。 | このFileだけでは確定できません。NG/OK UNITの差分は箇所ごとに正負が混在し、例えばNo.1-3差は約`0.002`、No.9-11差は約`0.015`などです。因果関係の確定までは記載されていません。出典ファイル：`OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx`. | `lsu/batch-17.md` (Batch 17) | Đánh giá số đo LD Bracket đơn lẻ có đủ để kết luận nguyên nhân lỗi quang lộ xiên |
| 20 | **Q0688** | このDataから原因候補を評価する時に何を注意しますか。 | LENS CO、LD BRACKETとも複数回・複数PointのNG/OK比較が必要です。単一Pointだけでは差の方向が一定ではないため、Fileが示す実測差を使って再現性を確認し、資料にない因果関係を推測で確定しないことが必要です。出典ファイル：`OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx`. | `lsu/batch-17.md` (Batch 17) | Nguyên tắc đánh giá nguyên nhân từ dữ liệu thực đo LENS CO và LD BRACKET |
| 21 | **Q0695** | Dữ liệu hiện tại ủng hộ lỗi chung của 1004 và 1035 hay lỗi riêng của 1035? | Dữ liệu ủng hộ vấn đề riêng ở `1035`: Camera +140 trên 1035 đọc Beam lớn bất thường, hiện tượng không có trên 1004 và NanoScan lại khớp với 1004. Nguồn file: `Y_BeamH_Camera 140_to bất thường.pptx`. | `lsu/batch-17.md` (Batch 17) | Phân biệt bất thường Beam H là lỗi chung của cả 2 Jig hay là lỗi riêng của Jig 1035 |
| 22 | **Q0632** | LENS COLLIMATEの取付位置がずれると何が問題になりますか。 | LENS COLLIMATEはLaser Diodeから出る拡散光を平行光へ変換します。Laser Diodeの組付け位置やCOLLIMATE LensのHousing位置が正しくない場合、光が設定方向へ進まなくなると説明されています。出典ファイル：Tài liệu đào tạo LSU_2019.01.18_K.pptx. | `lsu/batch-16.md` (Batch 16) | Ảnh hưởng của sai lệch vị trí lắp đặt LENS COLLIMATE tới chùm sáng song song |
| 23 | **Q0635** | Laser Powerはなぜ画像中央だけでなく周辺も確認する必要がありますか。 | 資料では画像中央付近、つまりF Lens中央部で光量が基本的に最大となり、中央から離れるほど弱くなるためです。差が大きい場合、画像両端の濃度が薄くなるため、周辺光量を測定して補正します。出典ファイル：Tài liệu đào tạo LSU_2019.01.18_K.pptx. | `lsu/batch-16.md` (Batch 16) | Nguyên nhân phải kiểm tra quang lượng Laser (Laser Power) ở cả vùng biên F Lens |
| 24 | **Q0636** | Polygon Motor có chỉ tạo chuyển động quay mà không ảnh hưởng đường quét Laser không? | Không. Bề mặt gương của MOTOR POLYGON phản xạ tia Laser; mỗi mặt gương thực hiện quét từ đầu tới cuối DRUM. Vì vậy Polygon Motor liên quan trực tiếp tới quá trình scanning và chất lượng hình ảnh. Nguồn file: Tài liệu đào tạo LSU_2019.01.18_K.pptx. | `lsu/batch-16.md` (Batch 16) | Cơ chế quét và phản xạ chùm tia Laser của từng mặt gương Polygon Motor |
| 25 | **Q1798** | Có được nhìn BeamV Black `97` ở record `09:37:13` rồi tự kết luận riêng giá trị đó là nguyên nhân NG không? | Không. File ghi BeamV_M35_K = `97` và Judge của record là NG, nhưng nguồn không chứng minh riêng giá trị `97` là nguyên nhân; không được tự suy diễn quan hệ nhân quả. Nguồn file: 2025_02_UniteTest.csv | `lsu/batch-41.md` (Batch 41) | Nguyên tắc không tự quy kết giá trị BeamV Black 97 đơn lẻ là nguyên nhân gây NG |

### 3.3. Nhóm Đối sách (12 câu)
*Các biện pháp khắc phục (countermeasures), quy trình can thiệp kỹ thuật (dán SIM tape, căn chỉnh JIG, kiểm tra 4M), trình tự ưu tiên xử lý và quy tắc ứng xử với dữ liệu đặc biệt.*

| STT | ID | Câu hỏi | Đáp án tham chiếu | Nguồn file trích dẫn | Trọng tâm kiểm tra (Tiêu chí đạt Mức 2 & 3) |
|:---:|:---:|:---|:---|:---|:---|
| 26 | **Q0671** | Kết quả kiểm tra bằng tấm OHP trước đối sách là bao nhiêu? | Kiểm tra OHP phát hiện `43/98 pcs NG = 43,9%`. Nguồn file: `Bong TAPE COVER GLASS Rev.00 VN.pptx`. | `lsu/batch-17.md` (Batch 17) | Đo kiểm tỷ lệ NG bằng tấm OHP trước khi thực hiện đối sách (43.9% NG) |
| 27 | **Q0674** | Kết quả xác nhận 4M có phát hiện bất thường không? | Không. Tài liệu ghi thao tác không có bất thường, không có thay đổi 4M và lực bám dính của TAPE COVER GLASS trên LOT tồn kho được xác nhận `OK`. Nguồn file: `Bong TAPE COVER GLASS Rev.00 VN.pptx`. | `lsu/batch-17.md` (Batch 17) | Kết quả xác nhận các yếu tố 4M đối với bất thường bong Tape Cover Glass |
| 28 | **Q0677** | Tăng thời gian ép từ 3 giây lên 6 giây có hiệu quả không? | Không. Hiện tại `3 s` cho kết quả khe hở NG và thử nghiệm `6 s` cũng vẫn NG. Nguồn file: `Bong TAPE COVER GLASS Rev.00 VN.pptx`. | `lsu/batch-17.md` (Batch 17) | Đánh giá hiệu quả của đối sách tăng thời gian ép tape từ 3s lên 6s |
| 29 | **Q0706** | SIM追加後のMagenta光路高さとC7620発生率はどうなりましたか。 | SIM追加後、Magenta光路高さ平均は`0.7 mm`となり、発生実績は`3/517 = 0.58% NG`です。資料では3台を分析中としています。出典ファイル：`Sirius 2 _ C7620_報告版 4.pptx`. | `lsu/batch-17.md` (Batch 17) | Hiệu quả của đối sách bổ sung SIM tape (giảm quang lộ xuống 0.7mm, NG còn 0.58%) |
| 30 | **Q0707** | SIM tape được dán ở đâu, dày bao nhiêu và trình tự thao tác thế nào? | Dán SIM tape dày `40 µm` tại điểm đỡ `119.h2` của `MIRROR C`. Trình tự: ⓪ tháo LID → ① tháo Spring → ② dán SIM, dùng vật tư chung `302HS19850` → ③ cố định lại Spring → ④ lắp LID → ⑤ điều chỉnh và đo. Nguồn file: `Sirius 2 _ C7620_報告版 4.pptx`. | `lsu/batch-17.md` (Batch 17) | Vị trí, quy cách độ dày SIM tape (40 µm tại 119.h2) và 5 bước thao tác đối sách |
| 31 | **Q0693** | NanoScan比较后，需要重新Correlation的是哪台Jig？ | 需要重新Correlation的是`Jig Bow_Skew 1035`。来源文件：`Y_BeamH_Camera 140_to bất thường.pptx`. | `lsu/batch-17.md` (Batch 17) | Xác định JIG cần thực hiện đối sách Re-Correlation sau khi đối chiếu NanoScan (1035) |
| 32 | **Q0696** | 排查时应先调整Unit还是确认Jig相关性？ | 根据资料证据，应先确认Jig相关性。因为NanoScan与1004一致，而1035存在异常读值，所以文件提出`需要重新Correlation Bow_Skew 1035`。来源文件：`Y_BeamH_Camera 140_to bất thường.pptx`. | `lsu/batch-17.md` (Batch 17) | Trình tự ưu tiên: Xác nhận Jig Correlation trước khi can thiệp điều chỉnh Unit |
| 33 | **Q0633** | Linh kiện nào cần kiểm tra nếu nghi vấn liên quan đến giới hạn đường kính beam? | Cần kiểm tra APERTURE. Chức năng của APERTURE là kiểm soát diện tích/đường kính beam đi qua và hạn chế nhiễu xạ. Tài liệu nêu ví dụ aperture có đường kính lớn NG ở LSU A3 có thể làm beam diameter khi điều chỉnh bị thấp. Nguồn file: Tài liệu đào tạo LSU_2019.01.18_K.pptx. | `lsu/batch-16.md` (Batch 16) | Linh kiện cần kiểm tra đối sách khi có nghi vấn về giới hạn đường kính beam (Aperture) |
| 34 | **Q0787** | Có thể xử lý 999 như một giá trị Beam diameter thông thường không? | Không nên. File không định nghĩa ý nghĩa của `999`; vì vậy không có căn cứ để xem nó tương đương các giá trị Beam khoảng `60–70 µm`. Nguồn file: `2026_07_Yellow_depth.csv`. | `lsu/batch-19.md` (Batch 19) | Quy tắc xử lý giá trị ngoại lai 999 trong dữ liệu Beam diameter (giữ nguyên Raw value) |
| 35 | **Q1777** | `Takt_WorkFixSolid` và `Takt_UVBond` của record đầu ghi bao nhiêu và nên xử lý thế nào? | Cả hai ghi **Raw value `0`**. Không tự suy ra rằng công đoạn bị bỏ qua hoặc NG nếu nguồn không định nghĩa. Nguồn file: 2025_02_Master.csv | `lsu/batch-41.md` (Batch 41) | Quy tắc xử lý giá trị Takt_WorkFixSolid và Takt_UVBond bằng 0 trong dữ liệu đo |
| 36 | **Q1827** | Các cột `-8` đến `-3` và `+2` đến `+8` ghi `--`; phải xử lý thế nào? | Giữ nguyên **Raw value `--`**; không tự suy ra OK/NG hoặc trạng thái đo. Nguồn file: 2025_02_Magenta_Depth_UniteTest.csv | `lsu/batch-42.md` (Batch 42) | Quy tắc xử lý ký tự -- trong dữ liệu Depth UnitTest (giữ nguyên Raw value --) |
| 37 | **Q2157** | Các giá trị `9999.9` của Magenta/Yellow LightPath phải xử lý thế nào? | Giữ nguyên **Raw value `9999.9`**; không tự đổi thành giá trị đo khác hoặc gán trạng thái OK/NG. Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv | `lsu/batch-48.md` (Batch 48) | Quy tắc xử lý giá trị 9999.9 của Magenta/Yellow LightPath (giữ nguyên Raw value 9999.9) |

### 3.4. Nhóm Thông số kỹ thuật (13 câu)
*Các thông số định lượng chuẩn, giá trị danh định (nominal), dung sai (tolerance), dải đo, quy đổi đơn vị (µm sang dot), giới hạn dòng điện, tốc độ quay và thông số vật lý.*

| STT | ID | Câu hỏi | Đáp án tham chiếu | Nguồn file trích dẫn | Trọng tâm kiểm tra (Tiêu chí đạt Mức 2 & 3) |
|:---:|:---:|:---|:---|:---|:---|
| 38 | **Q0662** | Các mục tham khảo số 13–16 có nominal và dung sai thế nào? | No.13 tại `12A` có nominal `123.5 ±0.2`; No.14 tại `12A` là `103.5 ±0.2`; No.15 tại `13A` là `83.5 ±0.2`; No.16 tại `13A` là `63.5 ±0.2`. Cả bốn đều được phán định `O`. Nguồn file: `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx`. | `lsu/batch-17.md` (Batch 17) | Nominal và dung sai kích thước các mục 13–16 trên bản vẽ MOUNT LD BLOCK |
| 39 | **Q0665** | Kích thước tại các điểm Y73–Y104 có giới hạn bao nhiêu? | Nominal là `39`, dung sai `+0.08 / -0.05`, tương ứng giới hạn trên `39.08` và dưới `38.95`. Các điểm từ Y73 tới Y104 hiển thị trong bảng đều được phán định `O`. Nguồn file: `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx`. | `lsu/batch-17.md` (Batch 17) | Kích thước nominal và giới hạn trên/dưới tại các điểm Y73–Y104 (39 +0.08/-0.05) |
| 40 | **Q0668** | g1 và g2 có nominal và giới hạn nào? | Cả g1 và g2 dùng nominal `13.81`, dung sai `+0.12 / -0.05`, tức giới hạn trên `13.93`, giới hạn dưới `13.76`. Các giá trị đọc được khoảng `13.845–13.856`, đều được đánh giá `O`. Nguồn file: `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx`. | `lsu/batch-17.md` (Batch 17) | Thông số nominal và giới hạn dung sai của g1 và g2 (13.81 +0.12/-0.05) |
| 41 | **Q0705** | 正常Magenta光路高度和色差平均值是多少，余量多少？ | BOWSKEW治具上正常Magenta光路高度平均约`1.1 mm`，与Bk的色偏平均为`64.09 dot`。相对70-dot上限，剩余余量约`5.9 dot`。来源文件：`Sirius 2 _ C7620_報告版 4.pptx`. | `lsu/batch-17.md` (Batch 17) | Thông số chiều cao quang lộ Magenta (1.1 mm), độ lệch màu (64.09 dot), margin (5.9 dot) |
| 42 | **Q0709** | Trong bảng quy đổi Skew, Black, Cyan, Magenta và Yellow lần lượt có giá trị µm và dot bao nhiêu? | Black=`0 µm / 0 dot`; Cyan=`-34 µm / -0.8095 dot`; Magenta=`81 µm / 1.9286 dot`; Yellow=`125 µm / 2.9762 dot`. Nguồn file: `sirius2 beam径確認_240202.xlsx`. | `lsu/batch-18.md` (Batch 18) | Bảng quy đổi Skew sang µm và dot cho 4 màu Black, Cyan, Magenta, Yellow |
| 43 | **Q0843** | Cặp giới hạn Current phổ biến nhất là bao nhiêu? | Cặp phổ biến nhất là Lower=`370 mA`, Upper=`520 mA`, xuất hiện trong`4.399 record`. Nguồn file: `2026_08_Spec.csv`. | `lsu/batch-21.md` (Batch 21) | Cặp giới hạn dòng điện Current (Lower 370 mA, Upper 520 mA) phổ biến nhất |
| 44 | **Q0864** | BeamPosX=3024,6 µm cách hai giới hạn bao nhiêu? | So với Lower 2890, nó cao hơn`134,6 µm`; so với Upper 3190, nó còn khoảng`165,4 µm`. Nguồn file: `2026_08_CamPos.csv`. | `lsu/batch-21.md` (Batch 21) | Khoảng cách từ vị trí BeamPosX = 3024.6 µm tới giới hạn Lower (2890) và Upper (3190) |
| 45 | **Q0680** | Phương pháp tính độ lệch trái–phải của LENS CO trong file là gì? | Đo khoảng cách từ các điểm đánh dấu đỏ tới `基準軸` – trục chuẩn, sau đó tính chênh lệch trái–phải của LENS CO. Nguồn file: `OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx`. | `lsu/batch-17.md` (Batch 17) | Phương pháp đo khoảng cách từ điểm đánh dấu đỏ tới trục chuẩn (基準軸) của LENS CO |
| 46 | **Q0684** | NG UNIT与OK UNIT的Bracket测量值大致在哪个范围？ | 两者原始数值都集中在约`43.95～44.03`附近。NG UNIT示例为约`43.956～43.999`，OK UNIT示例可到约`44.030`。来源文件：`OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx`. | `lsu/batch-17.md` (Batch 17) | Dải thông số đo LD Bracket của NG UNIT và OK UNIT (khoảng 43.95 ~ 44.03 mm) |
| 47 | **Q0924** | Cam-140、LD1_1のIndex 150ではBeam HとVはいくつですか。 | Beam H=`1.59750681`、Beam V=`2.103347`で、Raw値ではVの方が約`0.506`大きいです。出典ファイル：`2026_08_Magenta_Profile.csv`. | `lsu/batch-23.md` (Batch 23) | Thông số Beam H (1.5975) và Beam V (2.1033) tại Cam-140, LD1_1 của Index 150 |
| 48 | **Q0630** | Hướng quét chính và hướng quét phụ khác nhau thế nào? | Hướng quét chính là hướng tia Laser quét ngang trên DRUM. Hướng quét phụ là hướng chuyển động của giấy và hướng quay của DRUM. Nguồn file: Tài liệu đào tạo LSU_2019.01.18_K.pptx. | `lsu/batch-16.md` (Batch 16) | Định nghĩa thông số hướng quét chính (Main-scan) và hướng quét phụ (Sub-scan) |
| 49 | **Q0652** | Hai loại Motor Polygon được tài liệu phân biệt như thế nào? | Loại dùng cho đời cao 2LV, 2P6 có phần màu xanh phủ hết tấm kim loại và tốc độ quay 48.384 vòng/phút. Loại dùng cho các đời khác có phần xanh không phủ hết tấm kim loại và tốc độ 40.042 vòng/phút. Nguồn file: LSU UNIT (V) Lần 2.ppt. | `lsu/batch-16.md` (Batch 16) | Phân biệt 2 loại Motor Polygon theo tốc độ quay (48.384 vs 40.042 vòng/phút) |
| 50 | **Q0658** | Keo UV phải được quản lý và kiểm tra thế nào trước khi sử dụng? | Tài liệu yêu cầu bảo quản keo UV ở 0–15°C. Trước khi làm việc phải kiểm tra khối lượng keo UV; tài liệu cũng minh họa keo dùng để gắn CO/CY và keo gắn LENS F/APERTURE bằng hệ thống bơm keo. Nguồn file: LSU UNIT (V) Lần 2.ppt. | `lsu/batch-16.md` (Batch 16) | Thông số nhiệt độ bảo quản keo UV (0–15°C) và điều kiện kiểm tra trước khi thao tác |

---

## 4. Hướng dẫn dành cho thợ OMP (Vé LSU-QUALITY-PC0575)

1. **Đầu vào kiểm thử:** Đọc danh sách 50 câu hỏi từ bảng trên theo đúng thứ tự STT 1–50 (hoặc dùng mã ID `Qxxxx`).
2. **Phương thức chạy:** Gửi từng câu hỏi vào Workspace Chat / C-Agent API của AIOS.
3. **Ghi nhận kết quả:**
   - Lưu câu trả lời thực tế của C-Agent.
   - Chấm điểm từng câu theo thang 0–3 dựa trên rubric Mục 2.
   - Ghi chú lý do nếu bị trừ điểm (thiếu ý, thiếu thông số, thiếu nguồn).
4. **Chỉ số tổng hợp:**
   - Tổng điểm: /150 điểm (50 câu x 3 điểm tối đa).
   - Điểm trung bình (GPA) = Tổng điểm / 50.
   - Tỷ lệ câu đạt chuẩn (Điểm ≥ 2) = (Số câu ≥ 2 / 50) x 100%.
   - Tỷ lệ trích dẫn nguồn chuẩn xác (Điểm = 3) = (Số câu = 3 / 50) x 100%.
   - Phân tích điểm chi tiết theo 4 nhóm để chỉ ra điểm mạnh / điểm yếu của RAG hiện tại.

---
*Báo cáo được lập tự động và chuẩn hóa bởi thợ agy KDTVN-PC0575.*