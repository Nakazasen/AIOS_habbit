# Mẻ 62 — Điều-tra-lỗi — Q2612–Q2641 (30 cặp)

- Ngày: 2026-10-04 ~23:58 +07
- Nguồn: 10 file trong `SƠ đồ điện/` của ZIP Điều tra lỗi (shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, phản hồi không bị cắt, không chạm giới hạn Plus
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Quy tắc Raw value: tuân thủ (Q2620 giữ OPEN; Q2635/Q2640 giữ 未実装; Q2615/Q2633 giữ đúng title block không tự đổi theo tên file; Q2619/Q2625/Q2630 không suy diễn nguyên nhân từ nhãn đơn lẻ)
- Điểm khác biệt vs mẻ trước: 3 file title block khác tên file (303V401010_main PF.pdf→ASSY 303V447010; 302XD47070-04.pdf→ASSY 302XD01070; 3V3TC01010_Drive Assy.pdf→ASSY 303TD47030) — giữ đúng title block; bản 転写 "Ver1.2" ở link này title block giống Ver1.1 (EUK9MQD84HA), KHÁC bản Ver1.2 ở mẻ 57 (EUK9MQD85HA)

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 2612
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư mở sơ đồ PF MAIN và cần xác nhận mã board thực tế thay vì dựa vào tên file.
- Cách hỏi: trực tiếp
- Hỏi: Title block của file ghi ASSY, Rev., PWB No. và ngày nào?
- Đáp: ASSY=`303V447010`, Rev.=`05`, PWB No.=`7PA1215BCZ+GH01`, ngày=`2020/08/31`. Nguồn file: 303V401010_main PF.pdf

## CÂU HỎI 2613
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师用 PF 判别端口确认 Iris 的 500×2 PF。
- Cách hỏi: tình huống
- Hỏi: `3RB/3V4:500×2_PF` 的 SET0、SET1、SET2 和机种是什么？
- Đáp: SET0=`H`、SET1=`H`、SET2=`H`，机种=`Iris`。Nguồn file: 303V401010_main PF.pdf

## CÂU HỎI 2614
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: PF MAIN のDMT版と最新変更内容を比較している。
- Cách hỏi: so sánh
- Hỏi: 2019/8/26 と 2020/8/31 の変更内容はどう違いますか。
- Đáp: `2019/8/26` の Rev.2.0 は `RA20 33→100Ω` の定数変更、`2020/8/31` の Rev.5.0 は `VBAT端子をVDD接続に変更` です。Nguồn file: 303V401010_main PF.pdf

## CÂU HỎI 2615
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Tên file và mã ASSY trong bản vẽ khác nhau nên kỹ sư cần tránh tự sửa dữ liệu.
- Cách hỏi: xử lý sự cố
- Hỏi: File tên `302XD47070-04.pdf` nhưng title block ghi mã nào; có nên tự đổi theo tên file không?
- Đáp: Title block ghi ASSY=`302XD01070`, Rev.=`04`, PWB=`7PA1200AVP+GH01`. Phải giữ đúng giá trị đọc từ bản vẽ, không tự đổi ASSY thành `302XD47070`. Nguồn file: 302XD47070-04.pdf

## CÂU HỎI 2616
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核 CCD 板的 Power Table。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Power Table 包含 `+12V`、`+12V2`、`+5.1V`、`+10VL`、`+3.3VL`、`+1.8VL`，对吗？
- Đáp: 对。其中 `+10VL`、`+3.3VL`、`+1.8VL` 在文件中标有 `(LDO)`。Nguồn file: 302XD47070-04.pdf

## CÂU HỎI 2617
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: CCD基板資料のページ構成を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: このPDFは何ページで、主な回路ページは何ですか。
- Đáp: 全 `5` ページです。主な回路は `CCD(TCD2724DG),CCDdrv`、`AFE(AK8446),CAP`、`IF,POWER` です。Nguồn file: 302XD47070-04.pdf

## CÂU HỎI 2618
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần phân biệt tài liệu High này với bản Ver2.1 khác đã xử lý trước đó.
- Cách hỏi: tình huống
- Hỏi: Model, Drawing No. và ngày đọc được trên sơ đồ này là gì?
- Đáp: Model=`EUK9MQD83HA`, Drawing No.=`151-EUK9MQD83HA-C01`, ngày=`2019.10.7`. Nguồn file: Iris2020High_302XC45010_Ver2.1.pdf

## CÂU HỎI 2619
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较输入控制标签与变压器周边标签。
- Cách hỏi: so sánh
- Hỏi: 图中控制侧和高压变压器侧分别能读到哪些主要标签？
- Đáp: 控制侧可读到 `DRM_AC_CNT_K`、`24V2`、`15V`；T101 周边可读到 `NC1`、`NC2`、`H.V` 和 `M-K`。这些只是原图标签，不代表故障判断。Nguồn file: Iris2020High_302XC45010_Ver2.1.pdf

## CÂU HỎI 2620
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 回路図に複数のOPEN表記があり、データ化方法を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: この図面の `OPEN` 表記は故障や0として扱ってよいですか。
- Đáp: いいえ。図面中の `OPEN` は **Raw value `OPEN`** のまま保持します。故障、0、OK/NGなどの意味を追加しません。Nguồn file: Iris2020High_302XC45010_Ver2.1.pdf

## CÂU HỎI 2621
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra lại nhận dạng FRONT DRIVE LOW trước khi dùng sơ đồ.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Đây là `P.W.BOARD ASSY FRONT DRIVE LOW`, ASSY=`3V2XD47050`, Rev.=`02`, đúng không?
- Đáp: Đúng. PWB No.=`7PA1166BCZ+GH01`, ngày=`2019/10/18`, tổng cộng `11` trang. Nguồn file: 3V2XD47050-02.pdf

## CÂU HỎI 2622
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师想快速定位风扇和排出相关电路页。
- Cách hỏi: trực tiếp
- Hỏi: INDEX 中 EXIT、FAN 和 Container Solenoid 分别在哪些页面？
- Đáp: `PAGE07=EXIT1`、`PAGE08=EXIT2`、`PAGE09=FAN`、`PAGE10=CONTAINER SOLENOID`。`PAGE11` 为 `DEMITAS`。Nguồn file: 3V2XD47050-02.pdf

## CÂU HỎI 2623
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: FRONT DRIVE LOW のRev.1.2変更後にコネクタ周辺を確認している。
- Cách hỏi: tình huống
- Hỏi: Rev.1.2（2019/7/13）では YC7、RA1/RA10/RA22、U2 に何の変更がありますか。
- Đáp: `YC7` は表面実装タイプへ変更、`RA1/RA10/RA22` はARRAY品から単独チップ抵抗へ変更、`U2` は `37pinと39pinの入れ替え` です。Nguồn file: 3V2XD47050-02.pdf

## CÂU HỎI 2624
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh nhãn điều khiển đầu vào với nhãn đầu ra của mạch transfer.
- Cách hỏi: so sánh
- Hỏi: Đường điều khiển và đường output K được ghi khác nhau thế nào?
- Đáp: Đường điều khiển được ghi `T1CNT(K)`; phía output đọc được `T1(K)` và tại phần mạch khác có nhãn `T1+`. Nguồn file: Iris2020_302XC45020(転写)_Ver1.2.pdf

## CÂU HỎI 2625
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师排查24V输入路径，先按原图确认保险丝。
- Cách hỏi: xử lý sự cố
- Hỏi: `24V` 输入附近的 `F101` 标注什么额定值？能否仅凭保险丝位置判定故障原因？
- Đáp: `F101` 标注为 `250V 1.6A`。图中只给出电路连接和额定值，不能仅凭该位置认定具体故障原因。Nguồn file: Iris2020_302XC45020(転写)_Ver1.2.pdf

## CÂU HỎI 2626
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: ファイル名のVer表記だけでなく図面内情報を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: このファイルの図面内Modelは `EUK9MQD84HA`、Drawing No.は `151-EUK9MQD84HA-C01`、日付は `2019.9.26` ですね。
- Đáp: はい。今回のリンク先ファイルではその値が読めます。Nguồn file: Iris2020_302XC45020(転写)_Ver1.2.pdf

## CÂU HỎI 2627
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư mở sơ đồ nguồn một trang để xác định các rail chính.
- Cách hỏi: trực tiếp
- Hỏi: Những nhãn nguồn đầu vào và đầu ra nào đọc được rõ trên sơ đồ?
- Đáp: Đầu vào đọc được `AC-L`, `AC-N`, `LIVE`, `NEUTRAL`, `PFC+`; phía output có `5VO` và các rail `24V1`, `24V2`, `24V3`, `24V4`. Nguồn file: 302XD45010-full-38.pdf

## CÂU HỎI 2628
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师沿 AC 输入段检查保护元件。
- Cách hỏi: tình huống
- Hỏi: AC 输入区域中可以明确读到哪些保险丝编号？
- Đáp: 可以读到 `F001` 和 `F002`。图中同时可见 `AC-L`、`AC-N`、`LIVE`、`NEUTRAL` 与 `PFC+`。Nguồn file: 302XD45010-full-38.pdf

## CÂU HỎI 2629
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 5V系と24V系の出力表記を比較している。
- Cách hỏi: so sánh
- Hỏi: 出力側の5V系と24V系はどのように表記されていますか。
- Đáp: 5V系は `5VO`、24V系は `24V1/24V2/24V3/24V4` と表記されています。図面日付は `2021-09-29` です。Nguồn file: 302XD45010-full-38.pdf

## CÂU HỎI 2630
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xử lý Feed Drive và thấy lịch sử có thay đổi tụ sense của lift motor.
- Cách hỏi: xử lý sự cố
- Hỏi: Bản DMT ngày 2019/6/6 thay đổi C28/C29 thế nào, và có thể từ thay đổi này kết luận nguyên nhân lỗi lift motor không?
- Đáp: C28/C29 được đổi từ `0.1uF → 1uF` để đáp ứng định mức IC theo ghi chú nguồn. Đây là thay đổi thiết kế; không đủ để kết luận một lỗi thực tế do riêng C28/C29 gây ra. Nguồn file: FEED_3V2XC47030-02.pdf

## CÂU HỎI 2631
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认最终文件品号的变更记录。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 2019/11/3 的记录把品号从 `TV2XC01030` 改成 `3V2XC47030`，对吗？
- Đáp: 对。文件写明这是为了上传电路图而进行的品号修正。Nguồn file: FEED_3V2XC47030-02.pdf

## CÂU HỎI 2632
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: FEED DRIVE資料の構成を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: このPDFは何ページで、ASSY/PWB/Rev.は何ですか。
- Đáp: 全 `12` ページ、ASSY=`3V2XC47030`、PWB=`7PA1170BCZ+GH01`、Rev.=`02` です。Nguồn file: FEED_3V2XC47030-02.pdf

## CÂU HỎI 2633
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Tên file khác mã trong title block nên kỹ sư kiểm tra board thực tế trước khi dùng.
- Cách hỏi: tình huống
- Hỏi: Nội dung thật của file xác định board này là gì?
- Đáp: Title block ghi `PWB DP DRIVER ASSY`, dành cho `CIS付き用 DP DRIVER基板`, ASSY=`303TD47030`, Rev.=`01`, PWB=`7PA1187CCZ+GH01`, ngày=`2019/05/15`; file có `11` trang. Nguồn file: 3V3TC01010_Drive Assy.pdf

## CÂU HỎI 2634
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 DEMITAS 相关两次修改记录。
- Cách hỏi: so sánh
- Hỏi: `2019/6/17` 与 `2019/6/18` 对 DEMITAS 电容的记录有什么区别？
- Đáp: `2019/6/17` 记录为增加 `Demitasコンデンサ(DEMI_CAP)`；`2019/6/18` 则记录一组 DEMITAS 电容为 `未実装`，包括 `C115,C148,C149,C153,C119,C121,C137,C142`。Nguồn file: 3V3TC01010_Drive Assy.pdf

## CÂU HỎI 2635
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DEMITAS部品の未実装記録を不良判定と混同しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: `C115,C148,C149,C153,C119,C121,C137,C142：未実装` をNGと扱ってよいですか。
- Đáp: いいえ。ソースにある「未実装」のまま保持し、OK/NGや故障原因を追加しません。Nguồn file: 3V3TC01010_Drive Assy.pdf

## CÂU HỎI 2636
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận lại mã DP MAIN trước khi kết nối jig.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi `PWB DP MAIN ASSY`, ASSY=`303V24701X`, Rev.=`01`, PWB=`7PA1216ACZ+GH01`, đúng không?
- Đáp: Đúng. Ngày ghi trên title block là `2019/7/29`; file có `6` trang. Nguồn file: 7PA1216A_回路図_190729.pdf

## CÂU HỎI 2637
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认 DP MAIN 的 Power Table。
- Cách hỏi: trực tiếp
- Hỏi: Power Table 中列出了哪些电源？
- Đáp: `+24V`、`+24VF1`、`+24VIL`、`+3.3V`、`+3.3VSLP`，Ground=`GND`。Nguồn file: 7PA1216A_回路図_190729.pdf

## CÂU HỎI 2638
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: CPUリセット関連を確認するためFLASH WRITTERコネクタを追っている。
- Cách hỏi: tình huống
- Hỏi: `YC8` の4本の信号は何ですか。
- Đáp: `3.3V`、`GND`、`RESET`、`MODE` です。近傍のRESET ICは `U2=XC6119N27ANR-G` と記載されています。Nguồn file: 7PA1216A_回路図_190729.pdf

## CÂU HỎI 2639
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai nhóm thay đổi trong lịch sử MAIN board.
- Cách hỏi: so sánh
- Hỏi: Thay đổi ngày 2019/9/18 và 2019/9/26 khác nhau thế nào?
- Đáp: `2019/9/18` ghi `R266` đổi hằng số; `YC12` chưa lắp, `U34/YC24` và các linh kiện liên quan chưa lắp, `C267` đổi hằng số. `2019/9/26` ghi `PWB1: 1137B → 1235B`. Nguồn file: MAIN_3V2XF47010_04.pdf

## CÂU HỎI 2640
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到 MAIN 板变更履历中 `YC12` 标记为未实装。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以把 `YC12：未実装` 自动判断为故障或 NG 吗？
- Đáp: 不可以。必须按原文件保留"未实装"状态；不能自行赋予 OK/NG，也不能仅凭这一项推断故障原因。Nguồn file: MAIN_3V2XF47010_04.pdf

## CÂU HỎI 2641
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: MAIN基板資料の全体構成を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: この資料は全42ページで、ASSY=`3V2XF47010`、Rev.=`04`、PWB=`7PA1235CMF+GH01`、さらに `PANTHER LSU_IF_1` と `PANTHER LSU_IF_2` のページを含みますね。
- Đáp: はい。その通りです。INDEXでは `PANTHER LSU_IF_1` が項目19、`PANTHER LSU_IF_2` が項目20として記載されています。Nguồn file: MAIN_3V2XF47010_04.pdf
