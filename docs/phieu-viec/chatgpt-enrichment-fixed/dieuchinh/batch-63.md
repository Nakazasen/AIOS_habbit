# Mẻ 63 — Điều-tra-lỗi — Q2642–Q2671 (30 cặp)

- Ngày: 2026-10-05 ~00:09 +07
- Nguồn: 10 file trong `SƠ đồ điện/` của ZIP Điều tra lỗi (shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt, không cần nhắn "tiếp tục"
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược=6 (mỗi file 3 cách khác nhau luân phiên)
- Quy tắc Raw value: tuân thủ (OPEN/Not Mount/未実装 giữ nguyên; không suy diễn nguyên nhân từ giá trị đơn lẻ; giữ đúng title block kể cả khác tên file)
- Điểm khác biệt vs mẻ trước: `2XC_PA1166B_FRONT DRIVE_HIGH_回路図_190717.pdf` → ASSY=`T02XC01050` (khác tên file); `Iris2020High_302XC45010_Ver2.0.pdf` ở link này là Model=`EUK9MQD83HA` ngày 2019.07.03 (khác bản 縦基板 Ver2.0 Model MDKZZQ101 ở mẻ 60)

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 2642
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận đúng APC board Mono trước khi tra tín hiệu laser.
- Cách hỏi: trực tiếp
- Hỏi: Title block của file ghi ASSY, Rev., PWB No. và số trang thế nào?
- Đáp: `P.W.B APC ASSY`, ASSY=`302XF47250`, Rev.=`01`, PWB No.=`7PA1318AAP+GH01`; tài liệu có `12` trang. Nguồn file: 302XF47250-01.pdf

## CÂU HỎI 2643
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师按照 Rev.1.6 记录确认一组电阻的装配变更。
- Cách hỏi: tình huống
- Hỏi: Rev.1.6 对 R45、R46、R47、R48、R63、R64、R65、R66 做了什么变更？
- Đáp: `2021/2/1` 的 Rev.1.6 将这8个电阻从 `Not Mount` 改为安装 `51Ω`。`Not Mount` 仅按源文件记录，不自行解释为 NG。 Nguồn file: 302XF47250-01.pdf

## CÂU HỎI 2644
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 水晶マッチング後と調達対応後のC13/C14値を比較している。
- Cách hỏi: so sánh
- Hỏi: Rev.1.7 と Rev.1.8 で C13/C14 はどのように変わりましたか。
- Đáp: Rev.1.7（`2021/2/24`）で `C13:10p→15p`、`C14:12p→15p`。Rev.1.8（`2021/3/1`）では `C13:15p→10p`、`C14:15p→12p` に変更されています。 Nguồn file: 302XF47250-01.pdf

## CÂU HỎI 2645
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra fuse của Image Drive High sau một thay đổi revision.
- Cách hỏi: xử lý sự cố
- Hỏi: Change history ngày 2021/10/26 ghi thay đổi gì đối với YF8, và có thể từ đó kết luận YF8 từng gây lỗi không?
- Đáp: Rev.7.0 ngày `2021/10/26` ghi `Sheet17 YF8 1206FA 5A → 1206FA 7A`. Đây là thay đổi thiết kế; không đủ để kết luận YF8 là nguyên nhân của một lỗi thực tế. Nguồn file: IMAGE DRIVE_HIGH_20211105.pdf

## CÂU HỎI 2646
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认当前 Image Drive High 是否为最新 title block 版本。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 当前文件是 ASSY=`3V2XC47040`、Rev.=`08`、PWB=`7PA1171ECZ+GH01`、日期=`2021/11/5`，对吗？
- Đáp: 对。Rev.8.0 的记录也写明 `TittleBlock Rev/Date/PWB No. 修正`，并将 PWB1 从 `7PA1171D` 改为 `7PA1171E`。 Nguồn file: IMAGE DRIVE_HIGH_20211105.pdf

## CÂU HỎI 2647
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 回路図作成ルールを直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: この資料で基本の Pull-up / Pull-down 抵抗値はいくつと記載されていますか。
- Đáp: 基本的な Pull-up は `10kΩ`、Pull-down は `47kΩ` と記載されています。 Nguồn file: IMAGE DRIVE_HIGH_20211105.pdf

## CÂU HỎI 2648
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư nhận một bản Front Drive High cũ và cần xác nhận đúng revision.
- Cách hỏi: tình huống
- Hỏi: Title block thực tế của file ghi mã nào?
- Đáp: File ghi `P.W.BOARD ASSY FRONT DRIVE HIGH`, ASSY=`T02XC01050`, Rev.=`1.4`, PWB=`7PA1166BCZ+GH01`, ngày=`2019/7/17`; tổng cộng `11` trang. Nguồn file: 2XC_PA1166B_FRONT DRIVE_HIGH_回路図_190717.pdf

## CÂU HỎI 2649
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 Front Drive High 的 Rev.1.2 与 Rev.1.3。
- Cách hỏi: so sánh
- Hỏi: Rev.1.2 和 Rev.1.3 的主要修改分别是什么？
- Đáp: Rev.1.2（`2019/7/13`）：`YC7` 改为表面安装类型，`RA1/RA10/RA22` 从 ARRAY 改为单独 chip resistor，并交换 `U2 pin37/pin39`。Rev.1.3（`2019/7/16`）：增加 `TP179～TP183`，并将 `RA12` 左右镜像反转。 Nguồn file: 2XC_PA1166B_FRONT DRIVE_HIGH_回路図_190717.pdf

## CÂU HỎI 2650
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 変更履歴に削除部品があるため、不良扱いしないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: Rev.1.1 の `R38/R46/R54/R109` と `TP95/TP130/TP133/TP143` の削除をNGと判断してよいですか。
- Đáp: いいえ。Rev.1.1（`2019/7/9`）にはそれらを「削除」と記載しているだけです。削除記録を故障やNGへ自動変換しません。 Nguồn file: 2XC_PA1166B_FRONT DRIVE_HIGH_回路図_190717.pdf

## CÂU HỎI 2651
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận bản vẽ HV Mono trước khi lần mạch.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model của sơ đồ là `EUK9MQD86HA`, Drawing No.=`151-EUK9MQD86HA-C01`, ngày=`2019.10.07`, đúng không?
- Đáp: Đúng. File có `2` trang và title block thể hiện các giá trị trên. Nguồn file: Iris2020Mono_302XF45010Ver2.1.pdf

## CÂU HỎI 2652
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认 Mono K 通道的控制与监视信号。
- Cách hỏi: trực tiếp
- Hỏi: 图中 K 通道可以明确读到哪些控制/监视标签？
- Đáp: 可以读到 `DRM_AC_CNT_K`、`DRM_DC_CNT_K` 和 `DRM_ISENS_K`。 Nguồn file: Iris2020Mono_302XF45010Ver2.1.pdf

## CÂU HỎI 2653
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 高圧トランス周辺の巻線ラベルを追っている。
- Cách hỏi: tình huống
- Hỏi: 図面で `H.V` 側を追うと、読み取れる巻線端子ラベルには何がありますか。
- Đáp: `NC_S 1`、`NC_F 2`、`NS_F 9` などのラベルが確認できます。これらは接続名であり、単独では故障原因を示しません。 Nguồn file: Iris2020Mono_302XF45010Ver2.1.pdf

## CÂU HỎI 2654
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh cấu hình lower với upper được dùng làm nền khi thiết kế.
- Cách hỏi: so sánh
- Hỏi: Change history Rev.1.0 ghi những thay đổi chính nào khi chuyển từ upper sang lower?
- Đáp: File ghi lower được sửa từ mạch upper Rev.1.0: `PWB1` đổi từ upper sang lower; sửa port/mạch quanh điều khiển HV; `YC2` đổi `CZ20pin → CZW40pin` để thêm HV IF và `YC4` bị xóa; các phần HV control không cần thiết được loại bỏ. Nguồn file: IMAGE_3V2XD47040-02.pdf

## CÂU HỎI 2655
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到低位 Image Drive 删除了一些高压相关器件，避免直接判断故障。
- Cách hỏi: xử lý sự cố
- Hỏi: Rev.1.0 记录 `QD1～11` 删除部分不需要的高压控制器件时，可以把这些删除解释为 NG 吗？
- Đáp: 不可以。文件仅记录低位板不需要的部分被删除并修改网络；不能把设计上的删除自动解释为 NG 或故障原因。 Nguồn file: IMAGE_3V2XD47040-02.pdf

## CÂU HỎI 2656
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 下位Image Drive資料の識別情報を再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: この資料は ASSY=`3V2XD47040`、Rev.=`02`、PWB=`7PA1172BCZ+GH01`、全18ページで合っていますか。
- Đáp: はい。タイトルブロックの日付は `2019/11/3` です。 Nguồn file: IMAGE_3V2XD47040-02.pdf

## CÂU HỎI 2657
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận đúng bản High Ver2.0 thay vì dựa vào tên gần giống của tài liệu khác.
- Cách hỏi: trực tiếp
- Hỏi: Model, Drawing No., ngày và số trang của file là gì?
- Đáp: Model=`EUK9MQD83HA`, Drawing No.=`151-EUK9MQD83HA-C01`, ngày=`2019.07.03`; file có `5` trang. Nguồn file: Iris2020High_302XC45010_Ver2.0.pdf

## CÂU HỎI 2658
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师沿 High 电路确认电源和各色 DC 控制块。
- Cách hỏi: tình huống
- Hỏi: 图中可明确读到哪些供电和 DC 控制标签？
- Đáp: 供电可读到 `15V`、`24V1`、`24V2`；控制块可读到 `KDC`、`CDC`、`YDC`、`MDC`。 Nguồn file: Iris2020High_302XC45010_Ver2.0.pdf

## CÂU HỎI 2659
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 部品値とOPEN表記を比較し、意味を追加しないよう確認している。
- Cách hỏi: so sánh
- Hỏi: 図面で値が記載されたコンデンサと `OPEN` 表記は同じ意味として扱えますか。
- Đáp: いいえ。例えば `C221=100V 0.047` など数値が記載された部品がある一方、別の位置には **Raw value `OPEN`** が記載されています。`OPEN` を0やOK/NGへ置き換えません。 Nguồn file: Iris2020High_302XC45010_Ver2.0.pdf

## CÂU HỎI 2660
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra touch panel trong điều kiện thử nghiệm và cần đối chiếu đúng tiêu chuẩn nguồn.
- Cách hỏi: xử lý sự cố
- Hỏi: Điều kiện chuẩn về nhiệt độ, độ ẩm và áp suất khí quyển trong tài liệu là bao nhiêu?
- Đáp: Nhiệt độ=`20±10°C`, độ ẩm=`55±30%RH`, áp suất khí quyển=`96±10kPa`. Đây là điều kiện chuẩn thử nghiệm, không phải ngưỡng OK/NG tự suy diễn cho lỗi máy. Nguồn file: Tab led cam ung.pdf

## CÂU HỎI 2661
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认触摸板的产品类型与尺寸。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 该产品是 `302VH45011-01`、10.1 inch 的4线电阻式 Touch Panel，对吗？
- Đáp: 对。文件的 Scope 明确说明这是 `4 wires Touch Panel`，产品表中尺寸为 `10.1 inch`。 Nguồn file: Tab led cam ung.pdf

## CÂU HỎI 2662
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: タッチ操作荷重の仕様値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Finger と Finger pulp の初期操作荷重は何ですか。
- Đáp: Finger は `0.02～0.78N`、Finger pulp は `0.02～1N`（Typ. `0.3N`）です。試験後はいずれも上限 `1.47N` と記載されています。 Nguồn file: Tab led cam ung.pdf

## CÂU HỎI 2663
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần chọn đúng trang khi điều tra giao tiếp Video board.
- Cách hỏi: tình huống
- Hỏi: File chia các trang chức năng chính như thế nào?
- Đáp: File có `8` trang: INDEX; `MEDUSA(FIRST)`; `MEDUSA(SECOND)`; `ENGINE IF`; `MAIN IF/FIERY IF`; `APC IF`; `POWER`; và `CHANGE_HISTORY`. Title block ghi ASSY=`302XC47110`, Rev.=`01`, PWB=`7PA1169BCZ+GH01`. Nguồn file: T02XC47110_PWB VIDEO ASSY_DMT回路図.pdf

## CÂU HỎI 2664
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 B版中水晶匹配与KSS波形调整的电阻/电容修改。
- Cách hỏi: so sánh
- Hỏi: `2019/06/25` B版中，水晶匹配和KSS波形调整分别改了哪些值？
- Đáp: 水晶匹配：`R21 1.2kΩ→220Ω`、`C160 10pF→8pF`、`C161 12pF→8pF`。KSS 波形调整：`RA11/R112/R113 33Ω→100Ω`，`C166/C167/C168/C169 33pF→100pF`。 Nguồn file: T02XC47110_PWB VIDEO ASSY_DMT回路図.pdf

## CÂU HỎI 2665
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: B版変更前の未実装表記を不良状態と誤認しないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `R102 未実装⇒100Ω` の「未実装」をNGとして扱ってよいですか。
- Đáp: いいえ。ソース上では未実装状態から `100Ω` 実装への設計変更です。「未実装」をNGや故障原因へ自動変換しません。 Nguồn file: T02XC47110_PWB VIDEO ASSY_DMT回路図.pdf

## CÂU HỎI 2666
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận board OPC trước khi tra DLP/Drum.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Đây là `P.W.BOARD ASSY DRUM/DLP CONNECT (OPC)`, ASSY=`302XD47060`, Rev.=`04`, đúng không?
- Đáp: Đúng. PWB No.=`7PA1179BCZ+GH01`, ngày=`2019/9/17`, tài liệu có `4` trang. Nguồn file: 302XD47060-04.pdf

## CÂU HỎI 2667
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看 DMT 版本中 2019/7/1 的实装变更。
- Cách hỏi: trực tiếp
- Hỏi: `2019/7/1` 的记录中，哪些部件实装、未实装和新增？
- Đáp: 实装=`R53`；未实装=`R20, QD1, QD2`；新增=`R54, R55, R56, TP36, TP37`。其中"未实装"保持源文件原义，不自动判定 NG。 Nguồn file: 302XD47060-04.pdf

## CÂU HỎI 2668
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DLPユニットの通信・温度・FAN系を図面で追っている。
- Cách hỏi: tình huống
- Hỏi: DLP関連で図面上確認できる代表的な信号は何ですか。
- Đáp: `DLP_TH`、`EEP_SDA`、`EEP_SCL`、`DLP_FAN_BK/M/C/Y`、`+3.3V2_F1`、`24V2_F1` などが確認できます。これらの単一信号だけで故障原因は決めません。 Nguồn file: 302XD47060-04.pdf

## CÂU HỎI 2669
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai revision thay linh kiện analog trên APC board màu.
- Cách hỏi: so sánh
- Hỏi: Rev.1.3 và Rev.1.4 thay đổi những giá trị nào?
- Đáp: Rev.1.3 (`2021/1/7`) đổi `RTH 4.7k→1k`, `RETA 4.7k→1.96k`, `PDO 249→232`, `X1 20.0704MHz→16.52MHz`, `RA11 10k→47k`. Rev.1.4 (`2021/1/12`) thêm center pad pin49 nối GND cho U1–U8, đổi `U10/U12` từ `S-24C02DI-T8T1U5` sang `S-24C08DI-T8T1U5`, và `R139/R153 100→1k`. Nguồn file: 302XC47250-01.pdf

## CÂU HỎI 2670
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到 DEMITAS 电容从未实装改成实装，避免推断先前存在故障。
- Cách hỏi: xử lý sự cố
- Hỏi: Rev.1.5 中 `C23～C29：未実装⇒実装` 可以解释为之前这些位置是 NG 吗？
- Đáp: 不可以。文件只记录设计/装配状态从"未实装"改为"实装"；不能自行增加 OK/NG 或故障原因含义。 Nguồn file: 302XC47250-01.pdf

## CÂU HỎI 2671
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: APC Color資料の識別情報を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: このファイルは `P.W.B APC ASSY`、ASSY=`302XC47250`、Rev.=`01`、PWB=`7PA1318AAP+GH01`、全12ページで合っていますか。
- Đáp: はい。Model欄は `02XC`、タイトルブロックの日付は `2021/3/1` です。 Nguồn file: 302XC47250-01.pdf
