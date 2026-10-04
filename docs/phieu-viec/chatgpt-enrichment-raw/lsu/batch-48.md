# Mẻ 48 — LSU old + Ver2 vs Ver4 — Q2109–Q2158

- Ngày: 2026-10-04
- Nguồn: Drive LSU → `Sirius LSU/Sirius2_linearity/old/` + `Ver2 vs Ver4/`
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (GPT-5.6 Sol, reasoning Medium)
- 5 file, 50 cặp. **SỰ CỐ: KHÔNG CÓ** — gửi thành công ngay, không cloudflare_challenge, không bị cắt (4m55s).
- **PHÁT HIỆN CẤU TRÚC**: các thư mục `old/*` và `Ver2 vs Ver4/*` KHÔNG chứa workbook bowskew_nano trực tiếp; chúng phân tầng theo máy/điều kiện/version. ChatGPT chọn file `2025_02_UnitTest.csv` ở nhánh dữ liệu chính `1004-1/1004_1`.
- Ngôn ngữ: vi=17, zh=17, ja=16 — ĐÚNG mục tiêu.
- Cách hỏi: đủ 5 cách ×10 (mỗi file 5 cách ×2).
- Quy tắc Raw value: `0`/`--`/`999`/`9999.9` giữ nguyên; không suy diễn nguyên nhân từ giá trị đơn lẻ.
- Các nhánh Sirius2_linearity còn lại: `Ver2 vs Ver4/0`, cấp gốc `1 tape 40.PNG`, `2 Tape 40.PNG` (mẻ 49). Sau đó: `6thA3 LSU/Lỗi JIG BEAM` (9 thư mục theo ngày).
- Nhãn: LSU · Bản thảo — chưa qua chuyên gia duyệt.

---

### File 1: `old/Skew/1004-1/0/New/2025_02_UnitTest.csv` — Q2109–2118

## CÂU HỎI 2109
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận record đầu tiên của thử nghiệm Skew cũ trên máy 1004-1.
- Cách hỏi: trực tiếp
- Hỏi: Record đầu có ngày giờ, S/N, totalTakt và UnitSet bao nhiêu?
- Đáp: `2025/02/06 15:13:02`, S/N `6AE10ZXA9910`, totalTakt `23.1 sec`, UnitSet `9.6 sec`. Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

## CÂU HỎI 2110
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看第一条 Skew 测试的 Black/Cyan 数据。
- Cách hỏi: tình huống
- Hỏi: `15:13:02` 的 Black 与 Cyan Bow `-45/0/+45` 和 Skew 分别是多少？
- Đáp: Black Bow=`20/-4/10 um`、Skew=`-91 um`；Cyan Bow=`18/0/21 um`、Skew=`-90 um`。其中 Cyan Bow 的 `0` 保留为 **Raw value `0`**。Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

## CÂU HỎI 2111
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初の二回の Skew 測定を比較している。
- Cách hỏi: so sánh
- Hỏi: `15:13:02` と `15:18:13` の Black/Cyan Skew はそれぞれいくつですか。
- Đáp: `15:13:02` は Black `-91 um`、Cyan `-90 um`。`15:18:13` は Black `-56 um`、Cyan `-53 um` です。Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

## CÂU HỎI 2112
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy cả Black và Cyan Judge đều NG và cần đọc số đo thực tế.
- Cách hỏi: xử lý sự cố
- Hỏi: Record `15:24:07` có Black/Cyan Bow, Skew và Judge thế nào?
- Đáp: Black Bow `21/-3/9 um`, Skew `-16 um`; Cyan Bow `15/-3/17 um`, Skew `-4 um`; Black Judge `NG`, Cyan Judge `NG`, TotalJudge `NG`. Không suy diễn nguyên nhân chỉ từ một số đo. Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

## CÂU HỎI 2113
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认未参与测量颜色的 Raw value。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 第一条记录的 Magenta/Yellow Judge=`--`、Current=`0`，应分别保留为 Raw value，对吗？
- Đáp: 对。Judge 保存为 **Raw value `--`**，Current 保存为 **Raw value `0`**，不能自行赋予 OK/NG 含义。Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

## CÂU HỎI 2114
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Skew 測定時の電気・環境条件を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: `15:13:02` の Black/Cyan Current、Voltage、Temperature、Humidity は何ですか。
- Đáp: Black `157.5 mA`、Cyan `166.25 mA`、Voltage `3.35 V`、Temperature `21.7`、Humidity `50.6%` です。Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

## CÂU HỎI 2115
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xác nhận Timing đi kèm phép đo Skew đầu.
- Cách hỏi: tình huống
- Hỏi: Record `15:13:02` có Timing Black và Timing Cyan bao nhiêu?
- Đáp: Timing Black `-0.742 mm`, Timing Cyan `-1.434 mm`. Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

## CÂU HỎI 2116
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较三次测量的 totalTakt。
- Cách hỏi: so sánh
- Hỏi: `15:13:02`、`15:18:13`、`15:24:07` 的 totalTakt 分别是多少？
- Đáp: 分别为 `23.1 sec`、`15.2 sec`、`34.5 sec`。Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

## CÂU HỎI 2117
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Magenta の Bow に 999 があるため取扱いを確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: Magenta Bow:-45 と Bow:0 の `999` はどう扱いますか。
- Đáp: どちらも **Raw value `999`** として保持します。ファイルが意味を定義していないため OK/NG を推定しません。Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

## CÂU HỎI 2118
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Black Skew thay đổi từ -91 lên -16 qua ba lần đo.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Chỉ từ các giá trị Black Skew `-91`, `-56`, `-16 um` chưa thể kết luận nguyên nhân thay đổi, đúng không?
- Đáp: Đúng. File chỉ ghi các số đo và Judge tương ứng, không định nghĩa nguyên nhân của biến động. Nguồn file: old/Skew/1004-1/0/New/2025_02_UnitTest.csv

---

### File 2: `old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv` — Q2119–2128

## CÂU HỎI 2119
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 Light Path 第一次测试记录。
- Cách hỏi: trực tiếp
- Hỏi: 第一条记录的日期、时间、S/N、totalTakt 和 TotalJudge 是什么？
- Đáp: `2025/02/06 15:13:02`，S/N `6AE10ZXA9910`，totalTakt `23.1 sec`，TotalJudge `NG`。Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2120
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Black の LightPath 5点をラインで確認している。
- Cách hỏi: tình huống
- Hỏi: `15:13:02` の Black LightPath `-90/-45/0/+45/+90` は何ですか。
- Đáp: `0.57 / 0.58 / 0.53 / 0.53 / 0.51 mm` です。Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2121
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh LightPath Black và Cyan tại vị trí trung tâm.
- Cách hỏi: so sánh
- Hỏi: Tại `15:13:02`, LightPath vị trí `0` của Black và Cyan lần lượt bao nhiêu?
- Đáp: Black `0.53 mm`; Cyan `-0.71 mm`. Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2122
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师排查 `15:36:45` 时 LightPath 分布变化较大的记录。
- Cách hỏi: xử lý sự cố
- Hỏi: `15:36:45` 的 Black LightPath 五点是多少？
- Đáp: `-90/-45/0/+45/+90 = 0.69 / 0.49 / 0.23 / 0.01 / -0.24 mm`。文件没有定义这些数值变化的具体原因。Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2123
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Magenta/Yellow LightPath の特殊値を誤解しないよう確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Magenta と Yellow の LightPath が `9999.9` の場合、Raw value として保持するのが正しいですか。
- Đáp: はい。各点の `9999.9` は **Raw value `9999.9`** として保持し、OK/NG や測定状態を推定しません。Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2124
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đọc trực tiếp Cyan LightPath đầu phép thử.
- Cách hỏi: trực tiếp
- Hỏi: Cyan LightPath tại `-90/-45/0/+45/+90` ở `15:13:02` là bao nhiêu?
- Đáp: `-0.71 / -0.69 / -0.71 / -0.69 / -0.72 mm`. Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2125
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看 OK 记录的 LightPath。
- Cách hỏi: tình huống
- Hỏi: `15:28:39` 的 Black 与 Cyan LightPath 在位置 `0` 分别是多少？
- Đáp: Black=`0.59 mm`，Cyan=`-0.68 mm`；该记录 TotalJudge=`OK`。Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2126
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Black の中心 LightPath を時間で比較している。
- Cách hỏi: so sánh
- Hỏi: Black LightPath:0 は `15:13:02` と `15:32:19` でそれぞれいくつですか。
- Đáp: `0.53 mm` と `0.61 mm` です。Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2127
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Cyan LightPath chuyển từ âm sang dương ở phía +45/+90.
- Cách hỏi: xử lý sự cố
- Hỏi: Record `15:36:45` có Cyan LightPath năm điểm bao nhiêu?
- Đáp: `-1.11 / -0.57 / -0.06 / 0.49 / 0.99 mm`. Không suy diễn nguyên nhân chỉ từ dãy giá trị này. Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2128
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 LightPath 的变化与 NG 原因不能直接画等号。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Black LightPath:+90 从 `0.51` 变到 `-0.24 mm`，仅凭这两个值不能确定 NG 原因，对吗？
- Đáp: 对。文件记录测量值与 Judge，但没有定义该变化的具体原因。Nguồn file: old/Light Path/1004-1/Lần 1/New/2025_02_UnitTest.csv

---

### File 3: `old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv` — Q2129–2138

## CÂU HỎI 2129
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Timing 検証の最初のレコードを確認している。
- Cách hỏi: trực tiếp
- Hỏi: `15:13:02` の Black Timing、Cyan Timing、totalTakt は何ですか。
- Đáp: Black Timing `-0.742 mm`、Cyan Timing `-1.434 mm`、totalTakt `23.1 sec` です。Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2130
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra Timing ở lần đo thứ hai.
- Cách hỏi: tình huống
- Hỏi: Record `15:18:13` có Black Timing, Cyan Timing và UnitSet bao nhiêu?
- Đáp: Black Timing `-0.716 mm`, Cyan Timing `-1.448 mm`, UnitSet `1.7 sec`. Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2131
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较两次 Timing 测量。
- Cách hỏi: so sánh
- Hỏi: `15:24:07` 与 `15:28:39` 的 Black/Cyan Timing 分别是多少？
- Đáp: `15:24:07` 为 `-0.686 / -1.481 mm`；`15:28:39` 为 `-0.663 / -1.493 mm`。Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2132
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Timing が大きく変化した記録を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `15:36:45` の Black/Cyan Timing と Judge は何ですか。
- Đáp: Black Timing `-1.501 mm`、Cyan Timing `-2.565 mm`、Black/Cyan/TotalJudge はすべて `NG` です。原因はこの二つの値だけから推定しません。Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2133
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra cách lưu Current của Magenta/Yellow trong thử Timing.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Current Magenta và Yellow bằng `0` phải giữ là Raw value `0`, đúng không?
- Đáp: Đúng. Cả hai lưu là **Raw value `0`**, không tự suy ra trạng thái. Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2134
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看一条 OK 记录。
- Cách hỏi: trực tiếp
- Hỏi: `15:28:39` 的 totalTakt、UnitSet、Black/Cyan Judge 是什么？
- Đáp: totalTakt=`14.6 sec`，UnitSet=`1.2 sec`，Black Judge=`OK`，Cyan Judge=`OK`，TotalJudge=`OK`。Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2135
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 15:40台の Timing をラインで確認している。
- Cách hỏi: tình huống
- Hỏi: `15:40:51` の Black Timing、Cyan Timing、Black/Cyan Skew は何ですか。
- Đáp: Black Timing `-0.689 mm`、Cyan Timing `-1.841 mm`、Black Skew `5 um`、Cyan Skew `661 um` です。Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2136
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh Timing đầu và Timing tại record 15:40:51.
- Cách hỏi: so sánh
- Hỏi: Black/Cyan Timing ở `15:13:02` và `15:40:51` lần lượt là bao nhiêu?
- Đáp: `15:13:02`: `-0.742 / -1.434 mm`; `15:40:51`: `-0.689 / -1.841 mm`. Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2137
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现 Bow 中有原始值 0。
- Cách hỏi: xử lý sự cố
- Hỏi: `15:28:39` 的 Black Bow:0=`0` 应如何保存？
- Đáp: 保留为 **Raw value `0`**。该字段的零值不能自行转换成状态标签。Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

## CÂU HỎI 2138
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Cyan Timing の変化から原因を断定しないよう確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Cyan Timing が `-1.434` から `-2.565 mm` に変化しても、その原因はこのファイルだけでは特定できませんね。
- Đáp: はい。測定値と Judge はありますが、変化原因の定義はありません。Nguồn file: old/Timming/1004-1/Lần 1/New/2025_02_UnitTest.csv

---

### File 4: `Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv` — Q2139–2148

## CÂU HỎI 2139
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận dữ liệu Ver4 ở điều kiện -500 trước khi đối chiếu version.
- Cách hỏi: trực tiếp
- Hỏi: Record đầu có thời gian, S/N, totalTakt và Judge gì?
- Đáp: `2025/02/06 15:13:02`, S/N `6AE10ZXA9910`, totalTakt `23.1 sec`; Black/Cyan/TotalJudge đều `NG`. Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2140
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看 -500/Ver4 第一条 Bow/Skew。
- Cách hỏi: tình huống
- Hỏi: 第一条记录的 Black/Cyan Bow 与 Skew 分别是多少？
- Đáp: Black Bow=`20/-4/10 um`、Skew=`-91 um`；Cyan Bow=`18/0/21 um`、Skew=`-90 um`。Cyan 中的 `0` 为 **Raw value `0`**。Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2141
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: OK になる前後のレコードを比較している。
- Cách hỏi: so sánh
- Hỏi: `15:24:07` と `15:28:39` の Black/Cyan Skew と TotalJudge は何ですか。
- Đáp: `15:24:07` は `-16/-4 um`、TotalJudge `NG`。`15:28:39` は `19/22 um`、TotalJudge `OK` です。Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2142
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra record có Skew rất lớn trong Ver4/-500.
- Cách hỏi: xử lý sự cố
- Hỏi: Record `15:36:45` có Black/Cyan Bow, Skew và Timing bao nhiêu?
- Đáp: Black Bow `34/6/15 um`, Skew `-958 um`, Timing `-1.501 mm`; Cyan Bow `9/0/24 um`, Skew `2019 um`, Timing `-2.565 mm`. Không suy diễn nguyên nhân từ riêng các giá trị lớn. Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2143
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 Magenta/Yellow 的特殊原始值。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Magenta Bow=`999`、Judge=`--`、Current=`0` 都必须原样保留，对吗？
- Đáp: 对。分别保留为 **Raw value `999`**、**Raw value `--`** 和 **Raw value `0`**。Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2144
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Ver4/-500 の OK レコードを直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: `15:28:39` の Current Bk/C、Voltage、Humidity は何ですか。
- Đáp: Bk `158.75 mA`、C `166.25 mA`、Voltage `3.35 V`、Humidity `50.6%` です。Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2145
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra LightPath tại record OK của Ver4/-500.
- Cách hỏi: tình huống
- Hỏi: `15:28:39` có Black LightPath `-90/-45/0/+45/+90` bao nhiêu?
- Đáp: `0.57 / 0.61 / 0.59 / 0.62 / 0.62 mm`. Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2146
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较两条记录的 Current。
- Cách hỏi: so sánh
- Hỏi: `15:13:02` 与 `15:24:07` 的 Black/Cyan Current 分别是多少？
- Đáp: `15:13:02 = 157.5/166.25 mA`；`15:24:07 = 156.25/167.5 mA`。Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2147
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: LightPath の Magenta/Yellow に 9999.9 があるため処理方法を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `9999.9` を実測値として意味付けしてもよいですか。
- Đáp: いいえ。ファイルに意味定義がないため **Raw value `9999.9`** として保持します。Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2148
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Cyan Skew từ -90 đến 2019 qua các record.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Khoảng biến động Cyan Skew lớn không cho phép tự suy ra nguyên nhân nếu không có trường nguyên nhân trong file, đúng không?
- Đáp: Đúng. File chỉ có số đo và Judge, không có định nghĩa nguyên nhân cho từng biến động. Nguồn file: Ver2 vs Ver4/-500/1004_1/Ver4/2025_02_UnitTest.csv

---

### File 5: `Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv` — Q2149–2158

## CÂU HỎI 2149
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 500 条件 Ver4 的第一条数据。
- Cách hỏi: trực tiếp
- Hỏi: 第一条记录的时间、S/N、totalTakt、UnitSet 是多少？
- Đáp: `15:13:02`，S/N `6AE10ZXA9910`，totalTakt `23.1 sec`，UnitSet `9.6 sec`。Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2150
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初の Bow/Skew をラインで確認している。
- Cách hỏi: tình huống
- Hỏi: Black/Cyan の Bow `-45/0/+45` と Skew は何ですか。
- Đáp: Black=`20/-4/10 um`、Skew=`-91 um`。Cyan=`18/0/21 um`、Skew=`-90 um` です。Cyan の `0` は **Raw value `0`** です。Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2151
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh record NG và OK trong cùng file Ver4/500.
- Cách hỏi: so sánh
- Hỏi: `15:18:13` và `15:28:39` khác nhau thế nào về Skew và TotalJudge?
- Đáp: `15:18:13`: Black/Cyan Skew `-56/-53 um`, TotalJudge `NG`; `15:28:39`: `19/22 um`, TotalJudge `OK`. Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2152
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师排查 `15:32:19` 的 NG 数据。
- Cách hỏi: xử lý sự cố
- Hỏi: `15:32:19` 的 Black/Cyan Bow、Skew 和 Timing 分别是多少？
- Đáp: Black Bow=`24/0/13 um`、Skew=`59 um`、Timing=`-0.635 mm`；Cyan Bow=`17/-1/18 um`、Skew=`81 um`、Timing=`-1.531 mm`。Black Bow 的 `0` 保留为 **Raw value `0`**。Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2153
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Judge と特殊値を正しく分離して扱えるか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Magenta/Yellow Judge=`--` を Black/Cyan の Judge から推定してはいけませんね。
- Đáp: はい。`--` は **Raw value `--`** のまま保持し、他色の Judge から補完しません。Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2154
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đọc trực tiếp LightPath của Black tại record đầu.
- Cách hỏi: trực tiếp
- Hỏi: Black LightPath `-90/-45/0/+45/+90` ở `15:13:02` là bao nhiêu?
- Đáp: `0.57 / 0.58 / 0.53 / 0.53 / 0.51 mm`. Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2155
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看 `15:40:51` 的测量条件。
- Cách hỏi: tình huống
- Hỏi: `15:40:51` 的 Black/Cyan Current、Voltage、Temperature、Humidity 是多少？
- Đáp: Black=`156.25 mA`，Cyan=`167.5 mA`，Voltage=`3.35 V`，Temperature=`21.7`，Humidity=`50.6%`。Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2156
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Black LightPath の中心値を二つのレコードで比較している。
- Cách hỏi: so sánh
- Hỏi: Black LightPath:0 は `15:13:02` と `15:36:45` でそれぞれいくつですか。
- Đáp: `0.53 mm` と `0.23 mm` です。Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2157
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư gặp LightPath Magenta/Yellow bằng 9999.9 trong dữ liệu version.
- Cách hỏi: xử lý sự cố
- Hỏi: Các giá trị `9999.9` của Magenta/Yellow LightPath phải xử lý thế nào?
- Đáp: Giữ nguyên **Raw value `9999.9`**; không tự đổi thành giá trị đo khác hoặc gán trạng thái OK/NG. Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2158
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到 `15:36:45` 的 Cyan Skew 为 2019 um，准备判断原因。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 即使 Cyan Skew=`2019 um` 且 TotalJudge=`NG`，也不能仅凭该数值确定具体故障原因，对吗？
- Đáp: 对。文件记录 `2019 um` 和 Judge，但没有定义单一 Skew 数值与具体原因之间的因果关系。Nguồn file: Ver2 vs Ver4/500/1004_1/Ver4/2025_02_UnitTest.csv
