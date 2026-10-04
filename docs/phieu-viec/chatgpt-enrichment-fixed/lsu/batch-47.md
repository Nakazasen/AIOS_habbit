# Mẻ 47 — LSU New + Step 8 — Q2059–Q2108

- Ngày: 2026-10-04
- Nguồn: Drive LSU → `Sirius LSU/Sirius2_linearity/New/` + `Step 8/`
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (GPT-5.6 Sol, reasoning Medium)
- 5 file, 50 cặp. **SỰ CỐ: KHÔNG CÓ** — gửi thành công ngay, không cloudflare_challenge, không bị cắt (5m26s).
- **PHÁT HIỆN CẤU TRÚC**: ba nhánh `New/-500`, `New/0`, `New/500` KHÔNG chứa bowskew_nano.xlsm trực tiếp; bên trong tách theo `Cover Glassあり/なし` rồi theo máy. ChatGPT dùng file tổng hợp `2025_02_UnitTest.csv` của nhánh `Cover Glassあり/1004_1` cho cả ba điều kiện. Step 8 dùng `1004-1/Ver.4/2025_02_UnitTest.csv` cho từng điều kiện Cover Glassあり/なし. Đều là file dữ liệu thật, không phải file tạm.
- Ngôn ngữ: vi=18, zh=17, ja=15 (lệch nhẹ so với mục tiêu 17/17/16: thừa 1 vi, thiếu 1 ja — chấp nhận được, không cần sửa).
- Cách hỏi: đủ 5 cách ×10 (mỗi file 5 cách ×2).
- Quy tắc Raw value: `0`/`--`/`0.0` giữ nguyên; không suy diễn nguyên nhân từ giá trị đơn lẻ (kể cả Skew lớn như -958/2019 um).
- Các nhánh Sirius2_linearity còn lại: `old` (Skew, Light Path, Timming), `Ver2 vs Ver4` (-500/500/0), cấp gốc `1 tape 40.PNG`, `2 Tape 40.PNG`.
- Nhãn: LSU · Bản thảo — chưa qua chuyên gia duyệt.

---

### File 1: `New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv` — Q2059–2068

## CÂU HỎI 2059
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận record UnitTest đầu tiên của nhánh New/-500 trước khi đối chiếu Bow/Skew.
- Cách hỏi: trực tiếp
- Hỏi: Record đầu được ghi ngày giờ nào, S/N, totalTakt và UnitSet là bao nhiêu?
- Đáp: `2/3/2025 7:30:16`, S/N `6AE1051C8416`, `totalTakt = 14.4 sec`; `takt:UnitSet` là **Raw value `0`**. Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2060
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师在产线上检查第一条记录的 Black Bow 和 Skew。
- Cách hỏi: tình huống
- Hỏi: S/N `6AE1051C8416` 的 Black Bow `-45/0/+45` 和 Skew 分别是多少？
- Đáp: Bow 为 `15 / 5 / 12 um`，Skew 为 `21 um`。Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2061
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初の二つの UnitTest の takt を比較している。
- Cách hỏi: so sánh
- Hỏi: `7:30:16` と `8:05:38` の totalTakt と UnitSet はそれぞれいくつですか。
- Đáp: `7:30:16` は totalTakt `14.4 sec`、UnitSet は **Raw value `0`**。`8:05:38` は totalTakt `37.2 sec`、UnitSet `23.9 sec` です。Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2062
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra record có TotalJudge NG nhưng không muốn suy diễn nguyên nhân từ một giá trị.
- Cách hỏi: xử lý sự cố
- Hỏi: Record `8:07:43`, S/N `6AE1051C8907` có Black/Cyan Judge và các Skew bao nhiêu?
- Đáp: Black Judge `OK`, Cyan Judge `NG`, TotalJudge `NG`; Black Skew `22 um`, Cyan Skew `3 um`. Dữ liệu chỉ ghi các giá trị này, không tự kết luận nguyên nhân NG. Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2063
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核 Magenta 和 Yellow Judge 的特殊值。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 第一条记录的 Judge:Magenta 和 Judge:Yellow 都是 `--`，因此只能按 Raw value 保存，对吗？
- Đáp: 对。两者均为 **Raw value `--`**，不能自行赋予 OK/NG 含义。Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2064
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đọc trực tiếp thông số điện và môi trường của record đầu.
- Cách hỏi: trực tiếp
- Hỏi: S/N `6AE1051C8416` có Current Black/Cyan, Voltage, Temperature và Humidity bao nhiêu?
- Đáp: Current Black `161.25 mA`, Cyan `168.75 mA`, Voltage `3.35 V`, Temperature `21.7`, Humidity `58.6%`. Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2065
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 同じ S/N `6AE1051C8907` の二回測定を確認している。
- Cách hỏi: tình huống
- Hỏi: `8:09:21` の Black Skew、Cyan Skew、Voltage は何ですか。
- Đáp: Black Skew `23 um`、Cyan Skew `80 um`、Voltage `3.34 V` です。Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2066
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较同一 S/N 的两次 Cyan Skew。
- Cách hỏi: so sánh
- Hỏi: S/N `6AE1051C8907` 在 `8:07:43` 与 `8:09:21` 的 Cyan Skew 分别是多少？
- Đáp: 分别为 `3 um` 和 `80 um`。文件没有说明变化原因。Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2067
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư gặp Current Magenta/Yellow bằng 0 trong log UnitTest.
- Cách hỏi: xử lý sự cố
- Hỏi: Current Magenta và Yellow của record đầu phải xử lý thế nào?
- Đáp: Cả hai là **Raw value `0`**. Không tự diễn giải là không hoạt động, OK hoặc NG nếu file không định nghĩa. Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2068
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra không gán nguyên nhân NG từ riêng Cyan Skew.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Cyan Skew=`80 um` ở `8:09:21` không đủ để tự kết luận nguyên nhân NG nếu chỉ dựa trên một giá trị, đúng không?
- Đáp: Đúng. File ghi Cyan Skew `80 um` và TotalJudge `NG`, nhưng không định nghĩa riêng giá trị đó là nguyên nhân. Nguồn file: New/-500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

---

### File 2: `New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv` — Q2069–2078

## CÂU HỎI 2069
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 New/0 条件下第一条 UnitTest。
- Cách hỏi: trực tiếp
- Hỏi: 第一条记录的日期、时间、S/N、totalTakt 和 TotalJudge 是什么？
- Đáp: `2025/02/03 07:30:16`，S/N `6AE1051C8416`，totalTakt `14.4 sec`，TotalJudge `OK`。Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2070
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初の Cyan Bow をラインで確認している。
- Cách hỏi: tình huống
- Hỏi: S/N `6AE1051C8416` の Cyan Bow `-45/0/+45` と Skew は何ですか。
- Đáp: Bow は `-1 / -17 / 3 um`、Skew は `17 um` です。Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2071
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh Black và Cyan current của record đầu.
- Cách hỏi: so sánh
- Hỏi: Current Black và Cyan ở `07:30:16` lần lượt bao nhiêu?
- Đáp: Black `161.25 mA`, Cyan `168.75 mA`. Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2072
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师调查 S/N `6AE1051C8907` 的第一次 NG 记录。
- Cách hỏi: xử lý sự cố
- Hỏi: `08:07:43` 的 Black/Cyan Bow `-45/0/+45` 分别是多少？
- Đáp: Black 为 `0 / -25 / 0 um`；Cyan 为 `9 / -12 / 9 um`。其中数值 `0` 按 **Raw value `0`** 保存。Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2073
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: `--` の Judge を正しく扱えているか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Judge:Magenta と Judge:Yellow が `--` の場合、NG と読み替えてはいけませんね。
- Đáp: はい。両方とも **Raw value `--`** として保持します。Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2074
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看规格栏。
- Cách hỏi: trực tiếp
- Hỏi: 文件中的 Spec:Bow、Black Skew Lower/Upper、Cyan Skew Lower/Upper 分别是多少？
- Đáp: Spec:Bow=`25 um`；Black Skew=`17–43 um`；Cyan Skew=`4–30 um`。Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2075
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra record `09:48:15` sau nhiều lần UnitTest.
- Cách hỏi: tình huống
- Hỏi: S/N `6AE1051C9131` có Black Skew, Cyan Skew và Humidity bao nhiêu?
- Đáp: Black Skew `25 um`, Cyan Skew `34 um`, Humidity `42.3%`. Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2076
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 同一 S/N `8802` の二回測定を比較している。
- Cách hỏi: so sánh
- Hỏi: `13:41:39` と `13:43:00` の Cyan Current と Skew はそれぞれいくつですか。
- Đáp: `13:41:39` は `168.75 mA / 6 um`、`13:43:00` は `167.5 mA / 5 um` です。Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2077
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理 UnitSet 为零的记录。
- Cách hỏi: xử lý sự cố
- Hỏi: 第一条记录的 UnitSet=`0.0` 应如何保存？
- Đáp: 保存为 **Raw value `0.0`**，不能自行解释为某工序未执行或 NG。Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2078
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Cyan Skew thay đổi mạnh giữa hai lần đo cùng S/N.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Cyan Skew từ `3` lên `80 um` không cho phép tự suy diễn lý do thay đổi, đúng không?
- Đáp: Đúng. File chỉ ghi hai giá trị `3` và `80 um`; không có trường định nghĩa nguyên nhân. Nguồn file: New/0/Cover Glassあり/1004_1/2025_02_UnitTest.csv

---

### File 3: `New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv` — Q2079–2088

## CÂU HỎI 2079
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: New/500 の最初の UnitTest を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 最初の記録の日時、S/N、totalTakt、TotalJudge は何ですか。
- Đáp: `2025/02/03 07:30:16`、S/N `6AE1051C8416`、totalTakt `14.4 sec`、TotalJudge `OK` です。Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2080
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra Black Bow của sản phẩm đầu trong điều kiện New/500.
- Cách hỏi: tình huống
- Hỏi: Black Bow tại `-45/0/+45` và Black Skew của S/N `8416` là bao nhiêu?
- Đáp: Bow `15 / 5 / 12 um`; Skew `21 um`. Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2081
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较两条 OK 记录的 totalTakt。
- Cách hỏi: so sánh
- Hỏi: S/N `8416` 与 `6AE104YA6307` 的 totalTakt 分别是多少？
- Đáp: `8416 = 14.4 sec`，`6AE104YA6307 = 37.2 sec`。Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2082
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Cyan Judge NG の行で測定値を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `08:07:43` の Cyan Bow と Skew は何ですか。
- Đáp: Cyan Bow は `9 / -12 / 9 um`、Skew は `3 um`、Cyan Judge は `NG` です。ただし単独値から原因は推定しません。Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2083
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra các Current bằng 0 của hai màu chưa có Judge cụ thể.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Current Magenta=`0` và Yellow=`0` phải giữ là Raw value, đúng không?
- Đáp: Đúng. Cả hai là **Raw value `0`**, không tự gán trạng thái OK/NG. Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2084
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 電源条件を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: `08:05:38` の Black Current、Cyan Current、Voltage は何ですか。
- Đáp: Black `160 mA`、Cyan `168.75 mA`、Voltage `3.35 V` です。Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2085
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看 S/N `9131` 的 Bow 数据。
- Cách hỏi: tình huống
- Hỏi: `09:48:15` 的 Black Bow 与 Cyan Bow `-45/0/+45` 分别是多少？
- Đáp: Black=`8 / -3 / 4 um`；Cyan=`-3 / -19 / 0 um`，其中最后一个 `0` 保留为 **Raw value `0`**。Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2086
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai lần đo liên tiếp của S/N `8802`.
- Cách hỏi: so sánh
- Hỏi: totalTakt và Black Skew lúc `13:41:39` so với `13:43:00` là bao nhiêu?
- Đáp: `13:41:39`: totalTakt `15.1 sec`, Black Skew `19 um`; `13:43:00`: `14.6 sec`, `20 um`. Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2087
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: `--` を機械的に NG へ変換しないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: Judge:Magenta=`--`、Judge:Yellow=`--` を NG に置換してよいですか。
- Đáp: いいえ。両方とも **Raw value `--`** のまま保持します。Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

## CÂU HỎI 2088
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Cyan Skew が規格値と離れて見える行でも原因推定を避けている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Cyan Skew=`80 um` という一つの値だけで、不具合原因まで断定してはいけませんね。
- Đáp: はい。ファイルは測定値と Judge を記録していますが、単独値から具体的原因を定義していません。Nguồn file: New/500/Cover Glassあり/1004_1/2025_02_UnitTest.csv

---

### File 4: `Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv` — Q2089–2098

## CÂU HỎI 2089
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra record Step 8 đầu tiên của S/N thử nghiệm `6AE10ZXA9910`.
- Cách hỏi: trực tiếp
- Hỏi: Record đầu được ghi lúc nào, totalTakt, UnitSet và TotalJudge là gì?
- Đáp: `2025/02/06 15:13:02`, totalTakt `23.1 sec`, UnitSet `9.6 sec`, TotalJudge `NG`. Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2090
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查 Step 8 第一条 Black/Cyan BowSkew。
- Cách hỏi: tình huống
- Hỏi: `15:13:02` 的 Black 和 Cyan Bow `-45/0/+45`、Skew 分别是多少？
- Đáp: Black Bow=`20/-4/10 um`，Skew=`-91 um`；Cyan Bow=`18/0/21 um`，Skew=`-90 um`。其中 Cyan Bow 中的 `0` 为 **Raw value `0`**。Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2091
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: NG と OK の二つの記録を比較している。
- Cách hỏi: so sánh
- Hỏi: `15:13:02` と `15:28:39` の TotalJudge、Black Skew、Cyan Skew はどう違いますか。
- Đáp: `15:13:02` は `NG / -91 / -90 um`、`15:28:39` は `OK / 19 / 22 um` です。Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2092
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Skew rất lớn tại `15:36:45` và cần ghi đúng dữ liệu gốc.
- Cách hỏi: xử lý sự cố
- Hỏi: Record `15:36:45` có Black Skew, Cyan Skew và các Judge nào?
- Đáp: Black Skew `-958 um`, Cyan Skew `2019 um`; Black Judge `NG`, Cyan Judge `NG`, TotalJudge `NG`. Không suy diễn nguyên nhân chỉ từ hai giá trị Skew này. Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2093
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认未使用颜色的 Judge 占位值。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Magenta/Yellow Judge=`--`、Current=`0` 时，应分别保留为 Raw value `--` 和 Raw value `0`，对吗？
- Đáp: 对。不能把这些原始值自行转换成 OK/NG。Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2094
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đọc trực tiếp điều kiện đo của record OK.
- Cách hỏi: trực tiếp
- Hỏi: Record `15:28:39` có Current Black/Cyan, Voltage và Humidity bao nhiêu?
- Đáp: Black `158.75 mA`, Cyan `166.25 mA`, Voltage `3.35 V`, Humidity `50.6%`. Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2095
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 16時台の NG レコードを確認している。
- Cách hỏi: tình huống
- Hỏi: `16:30:44` の Black/Cyan Bow と Skew は何ですか。
- Đáp: Black Bow=`1/-17/2 um`、Skew=`1028 um`。Cyan Bow=`13/2/24 um`、Skew=`1512 um` です。Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2096
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较两个连续 NG 测量的 Skew。
- Cách hỏi: so sánh
- Hỏi: `16:34:18` 与 `16:38:20` 的 Black/Cyan Skew 分别是多少？
- Đáp: `16:34:18` 为 Black `614 um`、Cyan `1054 um`；`16:38:20` 为 Black `214 um`、Cyan `629 um`。Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2097
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Black Bow 0 bằng 0 ở một record OK.
- Cách hỏi: xử lý sự cố
- Hỏi: Black Bow tại vị trí `0` của record `15:28:39` phải ghi thế nào?
- Đáp: Giá trị là **Raw value `0`**. Không tự gán ý nghĩa OK/NG cho riêng giá trị `0`; Judge của record được đọc riêng từ trường Judge. Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2098
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tránh kết luận nguyên nhân khi Skew thay đổi rất lớn qua các lần đo.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Việc Cyan Skew có lúc `2019 um`, có lúc `22 um` không đủ để tự kết luận nguyên nhân thay đổi nếu file không nêu nguyên nhân, đúng không?
- Đáp: Đúng. File chỉ cung cấp các lần đo cụ thể và Judge tương ứng, không định nghĩa nguyên nhân của biến động. Nguồn file: Step 8/Cover Glassあり/1004-1/Ver.4/2025_02_UnitTest.csv

---

### File 5: `Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv` — Q2099–2108

## CÂU HỎI 2099
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认无 Cover Glass 条件下的第一条 Step 8 数据。
- Cách hỏi: trực tiếp
- Hỏi: 第一条记录的日期、时间、S/N、totalTakt 和 TotalJudge 是什么？
- Đáp: `2025/02/06 15:13:02`，S/N `6AE10ZXA9910`，totalTakt `23.1 sec`，TotalJudge `NG`。Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2100
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 無し条件で最初の電流値を確認している。
- Cách hỏi: tình huống
- Hỏi: `15:13:02` の Black/Cyan Current、Voltage、Humidity は何ですか。
- Đáp: Black `157.5 mA`、Cyan `166.25 mA`、Voltage `3.35 V`、Humidity `50.6%` です。Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2101
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh record NG đầu với record OK lúc `15:28:39`.
- Cách hỏi: so sánh
- Hỏi: totalTakt, Black Skew và Cyan Skew của hai record này là bao nhiêu?
- Đáp: `15:13:02`: `23.1 sec / -91 / -90 um`; `15:28:39`: `14.6 sec / 19 / 22 um`. Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2102
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师排查 `15:44:51` 的大幅 Skew 数据。
- Cách hỏi: xử lý sự cố
- Hỏi: `15:44:51` 的 Black/Cyan Bow 和 Skew 是多少？
- Đáp: Black Bow=`2/-14/11 um`，Skew=`1439 um`；Cyan Bow=`19/-2/18 um`，Skew=`-444 um`。该记录 TotalJudge=`NG`，但不能仅凭一个值推断原因。Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2103
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Judge の `--` と Current の 0 を区別できているか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Magenta/Yellow は Judge=`--`、Current=`0` なので、それぞれ Raw value のまま保持するのが正しいですか。
- Đáp: はい。Judge は **Raw value `--`**、Current は **Raw value `0`** として保持します。Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2104
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看唯一较早的 OK 记录。
- Cách hỏi: trực tiếp
- Hỏi: `15:28:39` 的 Black/Cyan Judge、Bow 和 Skew 分别是什么？
- Đáp: Black/Cyan Judge 都是 `OK`；Black Bow=`23/0/12 um`、Skew=`19 um`；Cyan Bow=`16/-4/16 um`、Skew=`22 um`。Black Bow 中的 `0` 为 **Raw value `0`**。Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2105
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tra record `15:40:51` để xem Bow và Skew sau một lần NG lớn.
- Cách hỏi: xử lý sự cố
- Hỏi: Record này có Black/Cyan Bow và Skew bao nhiêu?
- Đáp: Black Bow `27/4/15 um`, Skew `5 um`; Cyan Bow `11/-5/18 um`, Skew `661 um`; TotalJudge `NG`. Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2106
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 16時台の二つの測定を比較している。
- Cách hỏi: so sánh
- Hỏi: `16:30:44` と `16:34:18` の Humidity と Black Skew はそれぞれいくつですか。
- Đáp: どちらも Humidity `42.3%`。Black Skew は `1028 um` と `614 um` です。Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2107
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到 Cyan Bow 中心值为 0，准备做数据清洗。
- Cách hỏi: xử lý sự cố
- Hỏi: `15:13:02` 的 Cyan Bow:0=`0` 应如何处理？
- Đáp: 保留为 **Raw value `0`**。不能因为是零值而自行改成 OK、NG 或空白。Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv

## CÂU HỎI 2108
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师最后确认大 Skew 数值与故障原因之间不能直接画等号。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 即使 Black Skew=`1439 um` 或 Cyan Skew=`2019 um`，也不能只凭单个测量值确定具体原因，对吗？
- Đáp: 对。文件记录了这些测量值与 Judge，但没有定义单独数值对应的具体故障原因。Nguồn file: Step 8/Cover Glassなし/1004-1/Ver.4/2025_02_UnitTest.csv
