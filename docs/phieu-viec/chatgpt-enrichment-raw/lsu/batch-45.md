# Mẻ 45 — LSU file sót thư mục con + NanoScan XLSM — Q1959–Q2008

- Ngày: 2026-10-04
- Nguồn: Drive LSU → `Sirius LSU/Sirius2_linearity/Log/[1002-2]/[1001-2]` + cấp gốc `Sirius2_linearity`
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (GPT-5.6 Sol, reasoning Medium)
- 5 file, 50 cặp. SỰ CỐ: KHÔNG CÓ — không cloudflare_challenge, không bị cắt (9m33s).
- BƯỚC 1 (re-list 24s): [1002-1] 9/9 hết; [1001-2] còn 1 file; [1001-1] 10/10 hết; [1002-2] còn 2 file. → **5 thư mục con Log/ XONG 100%.**
- BƯỚC 2: 3 file sót + 2 file XLSM mới do ChatGPT tự chọn ở cấp gốc Sirius2_linearity (cùng S/N 6AE10ZXA9910, điều kiện -500 và 500; nhiều sheet Bk/C/M/Y với dữ liệu NanoScan/B.W. số cụ thể):
  - `bowskew_nano_6AE10ZXA9910_250227_-500.xlsm` → Q1989–1998 (Drive: https://drive.google.com/file/d/19Yd4-lJiVwjjHbqHHHI3bRkNxeHpHh4-/view)
  - `bowskew_nano_6AE10ZXA9910_250227_500.xlsm` → Q1999–2008 (Drive: https://drive.google.com/file/d/1smm5wdWICvUOL0dZ6yqhNokpWXMrB32j/view)
- Ngôn ngữ: vi=17, zh=17, ja=16. Cách hỏi: đủ 5 cách ×10 (mỗi file 5 cách ×2).
- Quy tắc Raw value: `0` giữ nguyên (các ô AU16/AU17/AT5 trên các sheet), không tự gán OK/NG.
- Inventory các nhánh Sirius2_linearity còn lại (ChatGPT liệt kê trên Drive):
  - `NanoScan (Step 7)`: thư mục `6AE10ZXA9910_6 mat motor`; các file bowskew_nano_..._250221_Step 7 (Skew -500/500/0).xlsm (`~$...` là file tạm, bỏ qua).
  - `New`: các nhánh -500/0/500.
  - `Step 8`: Cover Glassあり/Cover Glassなし.
  - `old`: Skew, Light Path, Timming.
  - `Ver2 vs Ver4`: -500/500/0.
  - Cấp gốc: `1 tape 40.PNG`, `2 Tape 40.PNG`, `bowskew_nano_6AE10ZXA9910_250227_0.xlsm`, `sa.xlsx` (`~$sa.xlsx` là file tạm).
- Nhãn: LSU · Bản thảo — chưa qua chuyên gia duyệt.

---

### File 1: `[1002-2] 2025_02.csv` — Q1959–1968

## CÂU HỎI 1959
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận record Auto đầu tiên của log #2_KM trước khi phân tích Judge.
- Cách hỏi: trực tiếp
- Hỏi: Record đầu được ghi lúc nào, S/N, TaktTime và các Judge là gì?
- Đáp: `2025/02/03 06:54:45`, S/N `6AE1052D0309`, TaktTime `88`, TotalJudge `NG`, Black_TotalJudge `OK`, Magenta_TotalJudge `NG`. Nguồn file: 2025_02.csv

## CÂU HỎI 1960
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看第一条产品记录的 Black 与 Magenta BeamH。
- Cách hỏi: tình huống
- Hỏi: `06:54:45` 的 Black 和 Magenta BeamH `M75/M35/P35/P80` 分别是多少？
- Đáp: Black 为 `75/78/80/78`；Magenta 为 `83/90/74/72`。Nguồn file: 2025_02.csv

## CÂU HỎI 1961
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初の二台の製品ログを比較している。
- Cách hỏi: so sánh
- Hỏi: S/N `0309` と `0311` の Judge と Current はどう違いますか。
- Đáp: `0309` は Total/Black/Magenta=`NG/OK/NG`、Current `226.3`。`0311` は `NG/NG/OK`、Current `225.0` です。Nguồn file: 2025_02.csv

## CÂU HỎI 1962
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra record NG của S/N `6AE1052D0320`.
- Cách hỏi: xử lý sự cố
- Hỏi: Record `07:23:47` có Magenta BeamH và BeamV M75/M35/P35/P80 bao nhiêu?
- Đáp: BeamH Magenta `79/85/74/73`; BeamV Magenta `83/85/76/76`. Record có TotalJudge `NG`, Black `OK`, Magenta `NG`. Nguồn file: 2025_02.csv

## CÂU HỎI 1963
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认两个 takt 字段为零时的保存规则。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 第一条记录的 `Takt_WorkFixSolid=0`、`Takt_UVBond=0` 只能作为 Raw value 保存，对吗？
- Đáp: 对。两者均为 **Raw value `0`**；文件没有定义时不能自行赋予 OK/NG 或工序状态含义。Nguồn file: 2025_02.csv

## CÂU HỎI 1964
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: OK レコードを直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: `07:03:08` の S/N、TaktTime、Judge は何ですか。
- Đáp: S/N `6AE1052D0313`、TaktTime `89`、TotalJudge/Black/Magenta はすべて `OK` です。Nguồn file: 2025_02.csv

## CÂU HỎI 1965
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tra vị trí XY của Black và Magenta trên sản phẩm đầu.
- Cách hỏi: tình huống
- Hỏi: S/N `0309` có Black XY và Magenta XY bao nhiêu?
- Đáp: Black `1473/2845`; Magenta `1616/2627`. Nguồn file: 2025_02.csv

## CÂU HỎI 1966
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较前两条记录的 Magenta M35。
- Cách hỏi: so sánh
- Hỏi: Magenta BeamH M35 在 S/N `0309` 与 `0311` 分别是多少？
- Đáp: `0309 = 90`，`0311 = 83`。Nguồn file: 2025_02.csv

## CÂU HỎI 1967
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: NG レコードで環境条件も併せて確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `07:23:47` の Current、Voltage、Temperature、Humidity は何ですか。
- Đáp: Current `227.5`、Voltage `3.4`、Temperature `24.3`、Humidity `50.6` です。これらの値だけから NG 原因は推定しません。Nguồn file: 2025_02.csv

## CÂU HỎI 1968
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tránh gán nguyên nhân NG từ giá trị BeamH cao riêng lẻ.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Magenta BeamH M35=`90` ở S/N `0309` không đủ để kết luận đây là nguyên nhân NG, đúng không?
- Đáp: Đúng. File ghi giá trị `90` và Judge nhưng không định nghĩa `90` là nguyên nhân của NG. Nguồn file: 2025_02.csv

---

### File 2: `[1001-2] 2025_02_UniteTest.csv` — Q1969–1978

## CÂU HỎI 1969
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 #2_CY 第一条 UnitTest。
- Cách hỏi: trực tiếp
- Hỏi: 第一条记录的日期、时间、S/N、TaktTime 和 Judge 是什么？
- Đáp: `2025/02/03 08:03:30`，S/N `6AE1052D0332`，TaktTime `29`，Total/Cyan/Yellow Judge 均为 `OK`。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1970
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初の UnitTest で Cyan と Yellow の BeamH を確認している。
- Cách hỏi: tình huống
- Hỏi: Cyan と Yellow の BeamH `M75/M35/P35/P80` は何ですか。
- Đáp: Cyan `78/77/80/78`、Yellow `78/81/81/79` です。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1971
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai UnitTest đầu của jig #2_CY.
- Cách hỏi: so sánh
- Hỏi: S/N `0332` và `0338` có Current và Cyan BeamH M75 lần lượt bao nhiêu?
- Đáp: `0332`: Current `210.0`, M75=`78`; `0338`: Current `228.8`, M75=`74`. Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1972
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师调查 S/N `6AE1052D0499` 的 NG 记录。
- Cách hỏi: xử lý sự cố
- Hỏi: `13:18:16` 的 Judge 和 Cyan BeamH `M75/M35/P35/P80` 是什么？
- Đáp: TotalJudge `NG`，Cyan `NG`，Yellow `OK`；Cyan BeamH 为 `87/77/78/77`。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1973
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: UnitTest の 0 値を誤解しないよう確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `Takt_WorkFixSolid` と `Takt_UVBond` の `0` は Raw value として扱うのが正しいですか。
- Đáp: はい。両方とも **Raw value `0`** として保持し、意味を追加しません。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1974
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra record có LDLotNo đặc biệt cuối ca.
- Cách hỏi: trực tiếp
- Hỏi: Record `18:03:51`, S/N `6AE1052D0642` có LDLotNo và Judge gì?
- Đáp: LDLotNo là **Raw value `---`**; TotalJudge `NG`, Cyan `OK`, Yellow `NG`. Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1975
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师核对 S/N `0512` 的光束参考与 cavity。
- Cách hỏi: tình huống
- Hỏi: `13:33:48` 的 FlensCavNo_C/Y 和 Ref Beam X/Y 是多少？
- Đáp: FlensCavNo_C/Y=`21/21`，Ref Beam X/Y=`2479/2316`。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1976
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 同じ S/N `0499` の二回の測定を比較している。
- Cách hỏi: so sánh
- Hỏi: `13:18:16` と `13:19:05` の Cyan XY と Current はどう変わっていますか。
- Đáp: Cyan XY は `1769/2859` → `1776/2930`、Current は `231.3` → `232.5` です。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1977
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư chuẩn hóa log trước khi đưa vào kho tri thức.
- Cách hỏi: xử lý sự cố
- Hỏi: LDLotNo=`---` ở S/N `0642` có được thay bằng một mã lot giả định không?
- Đáp: Không. Phải giữ nguyên **Raw value `---`**, không tạo giá trị không có trong nguồn. Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1978
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到 Cyan BeamH M75=`93` 后想判断 NG 原因。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: S/N `0512` 的 M75=`93` 不能单独作为 Cyan NG 原因，对吗？
- Đáp: 对。文件记录 M75=`93` 和 Cyan Judge=`NG`，但没有定义单一值 `93` 是原因。Nguồn file: 2025_02_UniteTest.csv

---

### File 3: `[1002-2] 2025_02_UniteTest.csv` — Q1979–1988

## CÂU HỎI 1979
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: #2_KM の最初の UnitTest を確認している。
- Cách hỏi: trực tiếp
- Hỏi: 最初の記録の日時、S/N、TaktTime、Judge は何ですか。
- Đáp: `2025/02/03 06:56:20`、S/N `6AE1052D0309`、TaktTime `28`、Total/Black/Magenta Judge はすべて `OK` です。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1980
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra BeamH Black và Magenta của UnitTest đầu.
- Cách hỏi: tình huống
- Hỏi: BeamH M75/M35/P35/P80 của Black và Magenta là bao nhiêu?
- Đáp: Black `75/78/80/78`; Magenta `79/82/75/74`. Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1981
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较第一、第二台 UnitTest 的位置数据。
- Cách hỏi: so sánh
- Hỏi: S/N `0309` 与 `0311` 的 Black XY 和 Current 分别是多少？
- Đáp: `0309`: XY=`1469/2851`、Current=`225.0`；`0311`: XY=`1508/2811`、Current=`225.0`。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1982
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 同一 S/N `0389` の NG 測定を切り分けている。
- Cách hỏi: xử lý sự cố
- Hỏi: `09:43:01` の Judge と Black BeamV `M75/M35/P35/P80` は何ですか。
- Đáp: TotalJudge `NG`、Black `NG`、Magenta `OK`。Black BeamV は `262/270/260/247` です。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1983
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tránh kết luận nguyên nhân từ dãy BeamV lớn.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Dãy `262/270/260/247` không tự động chứng minh nguyên nhân của Black NG, đúng không?
- Đáp: Đúng. File ghi Judge và các giá trị đó nhưng không định nghĩa quan hệ nguyên nhân. Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1984
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认同一 S/N 的下一次测量。
- Cách hỏi: trực tiếp
- Hỏi: S/N `6AE1052D0389` 在 `09:49:04` 的 Judge 和 Black XY 是什么？
- Đáp: Total/Black/Magenta Judge 均为 `OK`，Black XY=`1505/2747`。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1985
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: S/N `0401` の環境条件をラインで確認している。
- Cách hỏi: tình huống
- Hỏi: `10:35:53` の Current、Voltage、Temperature、Humidity は何ですか。
- Đáp: `227.5`、`3.4`、`24.3`、`42.3` です。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1986
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai lần đo của cùng S/N `0389`.
- Cách hỏi: so sánh
- Hỏi: Black BeamV M75 thay đổi thế nào giữa `09:43:01` và `09:49:04`?
- Đáp: Từ `262` xuống `83`; TotalJudge đồng thời từ `NG` sang `OK`, nhưng file không định nghĩa quan hệ nguyên nhân. Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1987
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理 UnitTest 中两个值为 0 的 takt 栏。
- Cách hỏi: xử lý sự cố
- Hỏi: `Takt_WorkFixSolid=0`、`Takt_UVBond=0` 应如何保存？
- Đáp: 均保存为 **Raw value `0`**，不自行赋予工序或 OK/NG 含义。Nguồn file: 2025_02_UniteTest.csv

## CÂU HỎI 1988
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 再測定で値が下がった理由を推定しないよう確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: BeamV M75 が `262` から `83` に変わった理由は、このファイルだけでは特定できませんね。
- Đáp: はい。二つの値と Judge は記録されていますが、変化原因は定義されていません。Nguồn file: 2025_02_UniteTest.csv

---

### File 4: `bowskew_nano_6AE10ZXA9910_250227_-500.xlsm` — Q1989–1998

## CÂU HỎI 1989
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư mở sheet `Bk` để kiểm tra NanoScan theo các vị trí -90 đến +90.
- Cách hỏi: trực tiếp
- Hỏi: Trên sheet `Bk`, tại cột `0` của bảng 主走査, các giá trị cho hàng `-90/-45/0/45/90` là bao nhiêu?
- Đáp: Lần lượt `91.89 / 86.77 / 86.01 / 85.81 / 86.23`. Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

## CÂU HỎI 1990
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师在 `C` sheet 检查主扫描数据。
- Cách hỏi: tình huống
- Hỏi: `C` sheet 在 `-90/-45/0/45/90` 五个位置、表中 `0` 列的数值分别是多少？
- Đáp: `84.02 / 83.12 / 82.73 / 84.75 / 85.72`。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

## CÂU HỎI 1991
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Bk と C の同じ -90 位置を比較している。
- Cách hỏi: so sánh
- Hỏi: `-90` 行の `0` 列は Bk と C でそれぞれいくつですか。
- Đáp: Bk=`91.89`、C=`84.02` です。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

## CÂU HỎI 1992
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra sheet M vì dữ liệu tập trung ở một số hàng.
- Cách hỏi: xử lý sự cố
- Hỏi: Trên sheet `M`, cột `0` có giá trị nào tại hàng `-108` và hàng `0`?
- Đáp: Hàng `-108` là `89.26`; hàng `0` là `81.53`. Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

## CÂU HỎI 1993
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 M sheet 中的零值不能被误判。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `M` sheet 的相关结果栏中出现 `0` 时，只应保存为 Raw value，对吗？
- Đáp: 对。例如 `AU16`、`AU17` 等为 **Raw value `0`**；工作簿未在这些单元格定义 OK/NG 含义。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

## CÂU HỎI 1994
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Y sheet の主走査データを直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: `Y` sheet の `-90/-45/0/45/90` 行、`0` 列の値は何ですか。
- Đáp: `92.47 / 89.07 / 84.81 / 83.18 / 82.65` です。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

## CÂU HỎI 1995
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra cột `B.W.-` trên sheet Bk.
- Cách hỏi: tình huống
- Hỏi: `B.W.-` ở các hàng `-90/-45/0/45/90` của Bk lần lượt là bao nhiêu?
- Đáp: `4255.182861328125 / 4253.2916015625 / 4249.0275390625 / 4249.93974609375 / 4252.664013671875`. Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

## CÂU HỎI 1996
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 Y sheet 两端位置的 B.W.-。
- Cách hỏi: so sánh
- Hỏi: `Y` sheet 在 `-90` 和 `90` 行的 `B.W.-` 分别是多少？
- Đáp: `-90 = 4253.472705078125`，`90 = 4248.560205078125`。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

## CÂU HỎI 1997
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Bk sheet 上部の補助計算値を確認している。
- Cách hỏi: trực tiếp
- Hỏi: Bk の `AT5` と `AU5` の値は何ですか。
- Đáp: `AT5 = -0.625`、`AU5 = -1.5113312090758668` です。この二つの値だけから原因や状態は推定しません。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

## CÂU HỎI 1998
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra ô số 0 trong vùng B.W. trước khi nhập dữ liệu.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Giá trị `AU13=0` trên Bk chỉ nên giữ là Raw value, không tự coi là OK/NG, đúng không?
- Đáp: Đúng. `AU13` là **Raw value `0`**; workbook không định nghĩa trạng thái cho riêng giá trị này. Nguồn file: bowskew_nano_6AE10ZXA9910_250227_-500.xlsm

---

### File 5: `bowskew_nano_6AE10ZXA9910_250227_500.xlsm` — Q1999–2008

## CÂU HỎI 1999
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看条件 `500` 下 M sheet 的有效测量点。
- Cách hỏi: trực tiếp
- Hỏi: `M` sheet 的 `-108` 行在 `0` 列和 `B.W.-` 列分别是多少？
- Đáp: `0` 列=`89.31`，`B.W.-=4245.74638671875`。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm

## CÂU HỎI 2000
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: M sheet の像高 0 付近をライン確認している。
- Cách hỏi: tình huống
- Hỏi: `M` sheet の行 `0` では、`0` 列と `B.W.-` はそれぞれいくつですか。
- Đáp: `0` 列=`83.09`、`B.W.-=4244.099267578125` です。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm

## CÂU HỎI 2001
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai vị trí có số liệu trên sheet M.
- Cách hỏi: so sánh
- Hỏi: Giá trị tại cột `0` của hàng `-108` và hàng `0` trên M khác nhau thế nào?
- Đáp: Hàng `-108 = 89.31`; hàng `0 = 83.09`. Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm

## CÂU HỎI 2002
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现 Bk 的结果栏连续为零，正在整理数据。
- Cách hỏi: xử lý sự cố
- Hỏi: Bk 的 `AU16/AU17/AU18` 应如何记录？
- Đáp: 三个单元格均为 **Raw value `0`**；不能自行解释为 OK、NG 或"无测量"。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm

## CÂU HỎI 2003
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: C sheet の 0 値の扱いを確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: C sheet の `AU16` と `AU20` は両方 Raw value `0` として保持するのが正しいですか。
- Đáp: はい。両方とも **Raw value `0`** で、状態の意味は追加しません。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm

## CÂU HỎI 2004
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra các giá trị tham chiếu ở đầu sheet Bk.
- Cách hỏi: trực tiếp
- Hỏi: Bk có giá trị tại `AJ4` và `AJ5` là bao nhiêu?
- Đáp: `AJ4 = 79.01`; `AJ5 = 78.89`. Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm

## CÂU HỎI 2005
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看 Y sheet 第 6 行的一组连续数值。
- Cách hỏi: tình huống
- Hỏi: Y sheet 的 `AG6:AP6` 数值依次是什么？
- Đáp: `82.67 / 85.27 / 88.75 / 93.1 / 99.63 / 111.3 / 154.78 / 171.31 / 181.3 / 191.02`。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm

## CÂU HỎI 2006
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Y sheet の同じ数値列の中央と端を比較している。
- Cách hỏi: so sánh
- Hỏi: `Y!AJ6` と `Y!AP6` はそれぞれいくつですか。
- Đáp: `AJ6 = 93.1`、`AP6 = 191.02` です。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm

## CÂU HỎI 2007
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra hai kết quả số trên sheet M nhưng không muốn suy diễn nguyên nhân.
- Cách hỏi: xử lý sự cố
- Hỏi: M có `AJ14=89.31` và `AV14=4245.74638671875`; có thể từ hai số này tự kết luận trạng thái không?
- Đáp: Không. Hai giá trị nguồn là `89.31` và `4245.74638671875`; workbook không định nghĩa từ riêng hai giá trị này một trạng thái OK/NG hay nguyên nhân. Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm

## CÂU HỎI 2008
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师最后确认条件 500 文件中的零值规则。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 即使 Bk、C、Y 的多个结果栏为 `0`，也不能自行判断这些 sheet 为 NG，对吗？
- Đáp: 对。应保留 **Raw value `0`**；文件没有定义这些单独零值对应 NG。Nguồn file: bowskew_nano_6AE10ZXA9910_250227_500.xlsm
