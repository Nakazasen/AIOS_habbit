# Mẻ 64 — Điều-tra-lỗi — Q2672–Q2701 (30 cặp)

- Ngày: 2026-10-05 ~00:20 +07
- Nguồn: 10 file trong `SƠ đồ điện/` của ZIP Điều tra lỗi (shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược=6 (mỗi file 3 cách khác nhau luân phiên)
- Quy tắc Raw value: tuân thủ (0/未実装/OPEN giữ nguyên; không suy diễn nguyên nhân từ giá trị đơn lẻ; giữ đúng title block kể cả khác tên file)
- PHÁT HIỆN QUAN TRỌNG: `302XD47250-01.pdf` (file 10) TRÙNG nội dung với `APC_302XD47250-01.pdf` (file 9) — hai file raw cùng kích thước, cùng SHA-256. Q2699–2701 không lặp lại Q2696–2698, mà hỏi về sự trùng lặp (Q2699), R1=0 giữ Raw value (Q2700), và Rev.3.0/4.0 (Q2701)

---

## CÂU HỎI 2672
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận đúng MAIN board màu trước khi tra tín hiệu.
- Cách hỏi: trực tiếp
- Hỏi: Title block của MAIN board này ghi ASSY, PWB, Rev. và số trang thế nào?
- Đáp: ASSY=`3V2XC47010`, PWB=`7PA1235CMF+GH01`, Rev.=`04`, Model=`02XC`; tài liệu có `42` trang và ngày title block là `2019/10/8`. Nguồn file: MAIN_3V2XC47010_04.pdf

## CÂU HỎI 2673
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师根据2019/9/18的改版记录检查元件状态。
- Cách hỏi: tình huống
- Hỏi: `2019/09/18` 的记录中，R266、YC12、C342 和 C267 分别怎样变更？
- Đáp: 文件记录 `R266：定数変更`、`YC12：未実装`、`C342：未実装`、`C267：定数変更`。其中"未実装"保持源文件状态，不自行判定为 NG。 Nguồn file: MAIN_3V2XC47010_04.pdf

## CÂU HỎI 2674
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: MAIN基板のB版からC版への変更内容を比較している。
- Cách hỏi: so sánh
- Hỏi: B-01 と C-03 では変更の中心がどう違いますか。
- Đáp: B-01（`2019/8/30`）では `RA59/RA60`、`R293/R649`、`R1034`、`3.3V4_SSD_EN_N`、`RA58`、`U64/QD50/R1035/R1036` などの追加・実装変更があります。C-03（`2019/10/2`）では `LIGHT_SEQ3`、`R1038/R1039/TP1535` を追加し、`LIGHT_SEQ1 → LIGHT_SEQ3` に変更しています。 Nguồn file: MAIN_3V2XC47010_04.pdf

## CÂU HỎI 2675
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xem thay đổi AFE khi điều tra SHD nhưng không muốn suy diễn thành nguyên nhân lỗi.
- Cách hỏi: xử lý sự cố
- Hỏi: Mục 대응 thiếu nguồn cung AFE ghi những thay đổi chính nào?
- Đáp: Change history mục `2021/1/8` ghi đổi board `PA1206B → PA1334A`; `U6/U7/U8 AK8446B → U28/U29/U30 LM98620`; xóa `U18`, đổi device `U20`, thay đổi các mạch xung quanh và đổi `U4 → U31` từ buffer đảo sang buffer không đảo. Đây là thay đổi thiết kế/nguồn linh kiện, không tự kết luận là nguyên nhân của một lỗi máy. Nguồn file: SHD_7PA1334A.pdf

## CÂU HỎI 2676
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认当前打开的SHD图纸身份。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 该文件是 ASSY=`303TC47021`、PWB=`7PA1334AVP+GH01`、Rev.=`01`、共12页，对吗？
- Đáp: 对。Title block 的日期为 `2021/1/7`，Parts Text Model 为 `03TC/3TD`。 Nguồn file: SHD_7PA1334A.pdf

## CÂU HỎI 2677
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: SHDのクロック/LVDS設計値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 外部発振周波数とLVDSラインのインピーダンスはいくつですか。
- Đáp: 外部発振周波数は `11.3324 MHz`、LVDSラインは `100Ω` のインピーダンスコントロールと記載されています。 Nguồn file: SHD_7PA1334A.pdf

## CÂU HỎI 2678
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư nhận MAIN board lower và cần tránh dùng nhầm PWB của bản màu.
- Cách hỏi: tình huống
- Hỏi: Title block thực tế của bản 02XD ghi mã nào?
- Đáp: ASSY=`3V2XD47010`, Model=`02XD`, PWB=`7PA1137CMF+GH01`, Rev.=`04`, ngày=`2019/10/8`; file có `42` trang. Nguồn file: MAIN_3V2XD47010_04.pdf

## CÂU HỎI 2679
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较MAIN 02XD改版记录中的"未实装"项目。
- Cách hỏi: so sánh
- Hỏi: `2019/09/18` 的记录中，除了 YC12 和 C342 外，还有哪组器件标为未实装？
- Đáp: `P.25 U34/YC24等 未実装` 也明确记录在本文件中。YC12、U34/YC24等、C342 的"未实装"都只是源文件状态，不自动等于 NG。 Nguồn file: MAIN_3V2XD47010_04.pdf

## CÂU HỎI 2680
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 未実装記録から故障原因を決めないよう、調査ルールを確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `U34/YC24等 未実装` だけを見てMAIN基板不良と判断できますか。
- Đáp: できません。これは変更履歴に記載された実装状態です。単独の「未実装」記録からOK/NGや故障原因を追加しません。 Nguồn file: MAIN_3V2XD47010_04.pdf

## CÂU HỎI 2681
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra xem đang dùng đúng ENGINE bản mono 02XF hay không.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File này là `P.W.B ENGINE ASSY`, ASSY=`3V2XF47020`, PWB=`7PA1168CCZ+GH01`, Rev.=`03`, đúng không?
- Đáp: Đúng. Model=`02XF`, ngày title block=`2019/10/23`, tổng cộng `18` trang. Nguồn file: ENGINE_3V2XF47020_03.pdf

## CÂU HỎI 2682
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师想直接定位ENGINE图纸中的接口页面。
- Cách hỏi: trực tiếp
- Hỏi: PAGE07 到 PAGE10 分别是什么功能？
- Đáp: `PAGE07=APC/WTNR/LVU`、`PAGE08=DRIVE EUSS`、`PAGE09=FEED DRIVE/MOTOR CPU`、`PAGE10=IMAGE DRIVE`。 Nguồn file: ENGINE_3V2XF47020_03.pdf

## CÂU HỎI 2683
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DMT改造時の0Ω部品について、値をそのまま記録している。
- Cách hỏi: tình huống
- Hỏi: Rev.2.7 の D10 に関するDMT改造はどのように記載されていますか。
- Đáp: DMTではダイオードの代わりに `2012サイズの0Ω抵抗` を手改造実装してA-C間をショートすると記載され、その後 `D10:実装⇒未実装` とあります。`0Ω` は **Raw value `0`** に相当する設計値として保持し、OK/NGを付与しません。 Nguồn file: ENGINE_3V2XF47020_03.pdf

## CÂU HỎI 2684
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đối chiếu hai model lower được ghi trên trang bìa workbook.
- Cách hỏi: so sánh
- Hỏi: Trong bảng model COLOR, mã `02XD` và `02YP` tương ứng với tốc độ nào?
- Đáp: Cover ghi `35/35 → 02XD` và `25/25 → 02YP`. Workbook xác định phần wiring lower cho `[02XD/02YP]`. Nguồn file: 全体配線図_下位_DMT機.xlsx

## CÂU HỎI 2685
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师按变更履历调查CCD与FUSER线束品号是否正确。
- Cách hỏi: xử lý sự cố
- Hỏi: `2019/7/3` 的记录对 CCD 和 WIRE IH EARTH 分别怎样修正？
- Đáp: `2 LSU・ISU` 中 CCD 品目代码从 `302RH01070 → 302XD01070`；`9 FUSER` 中 WIRE IH EARTH 从 `302K946AD0-01 → 302LC46AD0-02`。这是品号修正记录，本身不表示旧品号对应NG。 Nguồn file: 全体配線図_下位_DMT機.xlsx

## CÂU HỎI 2686
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Excel配線図の実際のシート構成を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: このworkbookは17シートで、`1 HVU`～`14 OPTION` の14配線シートに加えて `表紙`、`変更履歴`、`ハーネス品番` がある、という理解で合っていますか。
- Đáp: はい。実際に17シートあります。なお表紙のOPTION行はソース上 `ALL WIRING DIAGRAM [13/14] OPTION` と記載されているため、その表記を勝手に `[14/14]` へ修正しません。 Nguồn file: 全体配線図_下位_DMT機.xlsx

## CÂU HỎI 2687
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận ENGINE lower 02XD trước khi so sánh với 02XF.
- Cách hỏi: trực tiếp
- Hỏi: ASSY, model, PWB và Rev. của file là gì?
- Đáp: ASSY=`3V2XD47020`, Model=`02XD`, PWB=`7PA1168CCZ+GH01`, Rev.=`03`; ngày=`2019/10/23`, tổng cộng `18` trang. Nguồn file: ENGINE_3V2XD47020_03.pdf

## CÂU HỎI 2688
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师追踪相位判定在DMT与PMT阶段的bit变化。
- Cách hỏi: tình huống
- Hỏi: Rev.2.6 和 Rev.2.9 对 phase detection bit0/bit1 分别如何记录？
- Đáp: Rev.2.6（`2019/7/18`）记录 `bit0 L→H`、`bit1 H→L`；Rev.2.9（`2019/9/6`）的 PMT 对应则记录 `bit0 H→L`、`bit1 L→H`。 Nguồn file: ENGINE_3V2XD47020_03.pdf

## CÂU HỎI 2689
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Rev.2.7とRev.2.8のDMT対応内容を比較している。
- Cách hỏi: so sánh
- Hỏi: Rev.2.7 と Rev.2.8 では D10 の扱いがどう変わっていますか。
- Đáp: Rev.2.7（`2019/8/22`）ではDMTでD10位置に `0Ω` 抵抗を手改造実装する説明があり、同時に `D10:実装⇒未実装` と記載。Rev.2.8（`2019/8/30`）では `D10削除` と記載されています。 Nguồn file: ENGINE_3V2XD47020_03.pdf

## CÂU HỎI 2690
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy nhiều tụ đổi từ chưa lắp sang giá trị cụ thể và cần tránh coi trạng thái cũ là lỗi.
- Cách hỏi: xử lý sự cố
- Hỏi: Rev.2.3 ghi thay đổi EMI đối với C103/C104/C108/C109 như thế nào?
- Đáp: Cả bốn tụ được ghi `未実装 → 220p`. Trạng thái `未実装` trước thay đổi không được tự gán là NG hay nguyên nhân lỗi; đây là thay đổi thiết kế trong source. Nguồn file: ENGINE_3V2XC47020_03.pdf

## CÂU HỎI 2691
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认彩色ENGINE图纸身份。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 该图纸的 ASSY=`3V2XC47020`、Model=`02XC`、PWB=`7PA1168CCZ+GH01`、Rev.=`03`，对吗？
- Đáp: 对。Title block 日期为 `2019/10/23`，文件共有 `18` 页。 Nguồn file: ENGINE_3V2XD47020_03.pdf

## CÂU HỎI 2692
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: ENGINE基板の電源構成を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: POWER TABLE に記載されている代表的な電源を挙げてください。
- Đáp: `+3.3V0_F1`、`+3.3V2_F1`、`FSR_3.3V2_THCUT`、`+3.3V3_F1`、`+5V0`、`+5V2_F1`、`+5V4_IL_F1`、`+12V5_F1`、`+24V3_IL1_F1_F1`、`+24V4`、`+24V4_F1` が記載されています。 Nguồn file: ENGINE_3V2XC47020_03.pdf

## CÂU HỎI 2693
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư chọn sơ đồ IMAGE・FRONT theo đúng model mono.
- Cách hỏi: tình huống
- Hỏi: Cover chia mục `4 IMAGE・FRONT` cho `02XF` và các model mono còn lại thế nào?
- Đáp: Cover ghi `4-1 ALL WIRING DIAGRAM [4/13] IMAGE・FRONT` cho `02XF`; `4-2` dùng cho `02YP/02YS/02YT`. Nguồn file: 全体配線図_モノクロ_DMT機 MONO.xlsx

## CÂU HỎI 2694
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较单色LSU和FRONT两次与连接器相关的修改。
- Cách hỏi: so sánh
- Hỏi: `2019/6/13` 与 `2019/8/19` 的变更重点有什么不同？
- Đáp: `2019/6/13`：单色板无 thermistor，因此将 `YC7` 改为未实装，并把 harness `302ND46690-02 → 302ND46020-01`。`2019/8/19`：FRONT板 `YC7` 改为表面安装型，`B08B-CZHK-B-1 → BM08B-CZSS-1-TF(LF)(SN)`，并将 YC7 的 pin `5`、`7` loop连接。 Nguồn file: 全体配線図_モノクロ_DMT機 MONO.xlsx

## CÂU HỎI 2695
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: HVUハーネス品番を確認しているが、品番変更だけから故障原因を決めないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: 2019/9/10 の HVU変更では、どのハーネス品番が変更されていますか。
- Đáp: 現像ユニット－高圧基板間のハーネスが `302L746040-01 → 302XC46400` に変更されています。これは品目変更記録であり、旧品番をNGや故障原因とは扱いません。 Nguồn file: 全体配線図_モノクロ_DMT機 MONO.xlsx

## CÂU HỎI 2696
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận APC lower board trước khi kiểm tra laser driver.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Đây là `P.W.B APC ASSY`, ASSY=`302XD47250`, PWB=`7PA1328AAP+GH01`, Rev.=`01`, đúng không?
- Đáp: Đúng. Model=`02XD`, ngày title block=`2020/12/25`; tài liệu có `8` trang. Nguồn file: APC_302XD47250-01.pdf

## CÂU HỎI 2697
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接核对Rev.2.0的电阻与EEPROM变更。
- Cách hỏi: trực tiếp
- Hỏi: Rev.2.0 对 R14/R27/R41 和 EEPROM 做了什么修改？
- Đáp: Rev.2.0（`2021/2/15`）将 `R14/R27/R41：33Ω→100Ω`，并将 `S-24C02DI-T8T1U5 → S-24C08DI-T8T1U5`。 Nguồn file: APC_302XD47250-01.pdf

## CÂU HỎI 2698
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: APCのカスケードクロック経路を確認している。
- Cách hỏi: tình huống
- Hỏi: この資料でFREFOのカスケード接続順番はどう記載されていますか。
- Đáp: `K ⇒ M ⇒ C ⇒ Y` と記載されています。これは配線・カスケード順の情報であり、単独で不具合原因を示すものではありません。 Nguồn file: APC_302XD47250-01.pdf

## CÂU HỎI 2699
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Hai tên file khác nhau được lưu trong thư mục nên kỹ sư cần biết có khác revision hay không.
- Cách hỏi: so sánh
- Hỏi: `302XD47250-01.pdf` khác gì so với `APC_302XD47250-01.pdf` vừa kiểm tra?
- Đáp: Không thấy khác biệt nội dung: cả hai có cùng title block `302XD47250 / 7PA1328AAP+GH01 / Rev.01 / 8 trang` và file raw tải xuống có cùng SHA-256. Vì vậy đây được xử lý như hai bản sao của cùng tài liệu, không suy diễn có revision khác chỉ từ tên file. Nguồn file: 302XD47250-01.pdf; APC_302XD47250-01.pdf

## CÂU HỎI 2700
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在K通道看到R1标记为0，需要按Raw value规则录入。
- Cách hỏi: xử lý sự cố
- Hỏi: K通道中的 `R1=0` 应怎样记录？
- Đáp: 保持为 **Raw value `0`**；图中同时标有尺寸 `1005`。不能把 `0` 自动解释成 OK、NG、短路故障或测量异常。 Nguồn file: 302XD47250-01.pdf

## CÂU HỎI 2701
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: APC基板のRev.3.0から4.0への変更を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Rev.3.0では C12/C13 を15pFへ変更し、Rev.4.0では元の値へ戻したうえでRA2/RA3も変更している、という理解で合っていますか。
- Đáp: はい。Rev.3.0（`2021/2/25`）で `C12:10pF→15pF`、`C13:12pF→15pF`。Rev.4.0（`2021/3/1`）で `C12:15pF→10pF`、`C13:15pF→12pF`、さらに `RA2:1k→100Ω`、`RA3:47k→4.7kΩ` へ変更しています。 Nguồn file: 302XD47250-01.pdf
