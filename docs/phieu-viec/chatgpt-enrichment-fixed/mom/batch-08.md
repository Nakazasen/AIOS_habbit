# Mẻ MOM 08 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Trạng thái: Bản thảo — chưa qua chuyên gia duyệt. Khối: MOM.
5 file spec thiết bị trong 仕様書/マテハン, mỗi file 10 cặp, câu 329–378. Không file nào bị bỏ qua.

## CÂU HỎI 329
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thiết bị đang xác nhận khả năng chở ORICON của ACR và CTU trước khi chạy thử.
- Cách hỏi: trực tiếp
- Hỏi: ACR và CTU chở được bao nhiêu ORICON và tải tối đa là bao nhiêu?
- Đáp: Theo bảng 商品構成, ACR model 0C1J4A chở 1 ORICON với tải tối đa 20 kg; CTU model 0C1J4B chở 2 ORICON, tải tối đa 20 kg × 2, bố trí hai tầng. Kích thước ORICON áp dụng là 433(W) × 635(L) × 356(H) mm, khối lượng tối đa 20 kg. Nguồn file: ACR_CTU製品仕様書Ver1_20251205.xlsx.

## CÂU HỎI 330
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 设备工程师比较ACR和CTU的主要用途。
- Cách hỏi: so sánh
- Hỏi: ACR和CTU的主要功能有什么区别？
- Đáp: ACR主要搭载1 pcs ORICON，并负责P-RACK最多5层的入库和出库；CTU搭载2 pcs ORICON，主要用于与Conveyor、TRC等设备之间的搬入搬出。来源文件：ACR_CTU製品仕様書Ver1_20251205.xlsx。

## CÂU HỎI 331
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: ARM動作が遅いと感じたため、仕様値と比較している。
- Cách hỏi: tình huống
- Hỏi: ARMの最高速度と減速時の最小速度は何ですか。
- Đáp: ARM移動速度の最高速度は250 mm/s ±10 mm/s、減速時の最小速度は70 mm/s ±5 mm/sです。ストローク移動時間は2.5 sで、資料上は一部T.B.D扱いです。出典ファイル：ACR_CTU製品仕様書Ver1_20251205.xlsx.

## CÂU HỎI 332
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: ACR nâng lên tầng rack nhưng dừng sai vị trí, kỹ sư cần so với spec.
- Cách hỏi: xử lý sự cố
- Hỏi: Spec quy định tốc độ và độ chính xác dừng của cơ cấu nâng ACR như thế nào?
- Đáp: Tốc độ nâng tối đa là 210 mm/s ±10 mm/s; tốc độ giảm tốc là 10 mm/s ±1 mm/s. Độ chính xác dừng được ghi ±2 mm và có chú thích T.B.D. Từ tầng 1 đến tầng 5, thời gian nâng tham chiếu là 10 s; mỗi tầng khoảng 2.5 s. Nguồn file: ACR_CTU製品仕様書Ver1_20251205.xlsx.

## CÂU HỎI 333
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师要确认P-RACK第3层收货位置和出货位置是否设错。
- Cách hỏi: trực tiếp
- Hỏi: P-RACK第3层的荷受位置和荷出位置高度分别是多少？
- Đáp: 第3层荷受位置为1267.5 mm，荷出位置为1282.5 mm。两者相差15 mm。来源文件：ACR_CTU製品仕様書Ver1_20251205.xlsx。

## CÂU HỎI 334
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人がP-RACK各段の荷受けと荷出し位置は同じ高さだと思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: P-RACKの荷受け位置と荷出し位置は同じ高さですか。
- Đáp: いいえ。例えば1段目は荷受け427.5 mm、荷出し442.5 mmです。5段目は荷受け2107.5 mm、荷出し2122.5 mmで、各段とも荷出し側が15 mm高く設定されています。出典ファイル：ACR_CTU製品仕様書Ver1_20251205.xlsx.

## CÂU HỎI 335
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang xác nhận chiều cao bàn CTU để đối chiếu với conveyor.
- Cách hỏi: trực tiếp
- Hỏi: CTU có chiều cao bàn trên và bàn dưới bao nhiêu?
- Đáp: Mục CTU荷台高さ ghi tầng trên 310 mm và tầng dưới 770 mm tính từ mặt đất. Nguồn file: ACR_CTU製品仕様書Ver1_20251205.xlsx.

## CÂU HỎI 336
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 设备准备投入长时间运行，工程师确认电气和续航规格。
- Cách hỏi: tình huống
- Hỏi: 额定输入和额定运行时间是多少？
- Đáp: 额定输入为24 V DC、额定电流5 A，资料中标有T.B.D。额定负载条件下的运行时间记录为8小时，同样附有T.B.D注记。来源文件：ACR_CTU製品仕様書Ver1_20251205.xlsx。

## CÂU HỎI 337
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 保全担当が予防保全周期を確認している。
- Cách hỏi: so sánh
- Hỏi: 日常点検と定期メンテナンスの周期はどう違いますか。
- Đáp: 日常点検はユーザーメンテナンスとして使用前点検、定期メンテナンスは6ヵ月ごとと記載されています。定期メンテナンスの所要時間は1時間、セットアップは開梱から動作準備まで20分です。出典ファイル：ACR_CTU製品仕様書Ver1_20251205.xlsx.

## CÂU HỎI 338
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn chạy ACR trong khu vực nóng và tối hơn bình thường.
- Cách hỏi: xử lý sự cố
- Hỏi: Điều kiện môi trường sử dụng nào cần kiểm tra trước khi kết luận thiết bị hoạt động ngoài spec?
- Đáp: Phạm vi nhiệt độ là 5°C–35°C, độ ẩm 20–80%, độ nghiêng sàn -0.8° đến +0.8° và ánh sáng môi trường tối thiểu 120 lux. Chỉ số độ nghiêng có chú thích áp dụng khi dùng camera detection stop và AGV C1J. Nguồn file: ACR_CTU製品仕様書Ver1_20251205.xlsx.

## CÂU HỎI 339
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在读取ACR地图中的Task序列。
- Cách hỏi: trực tiếp
- Hỏi: Address 1在Task表中使用什么基本序列？
- Đáp: 表中Address 1记录为R, GL, AC, 3, EE, 3, SP, 10, GO。该文件以Address和Task命令串的形式定义路线。来源文件：ACRマップ再検討20260105.xlsx。

## CÂU HỎI 340
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Address 2とAddress 4の設定を比較している。
- Cách hỏi: so sánh
- Hỏi: Address 2と4のTask列は何が違いますか。
- Đáp: 両方ともM, GL, AC, 3, EE, 3までは同じですが、Address 2はSP, 30, GO、Address 4はSP, 10, GOです。主な差はSP値です。出典ファイル：ACRマップ再検討20260105.xlsx.

## CÂU HỎI 341
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang điều tra tại sao AGV quay ở Address 5.
- Cách hỏi: tình huống
- Hỏi: Address 5 có chuỗi lệnh nào liên quan đến quay?
- Đáp: Address 5 có chuỗi M, SS, TR, 90, RD, 0, GL, AC, 3, EE, 3, SP, 10, GO. Trong file này, lệnh quay xuất hiện dưới dạng TR, 90; ý nghĩa chi tiết của từng mã cần đối chiếu với file đặc tả command nếu cần giải thích sâu hơn. Nguồn file: ACRマップ再検討20260105.xlsx.

## CÂU HỎI 342
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 现场发现Address 3的任务和旧版本不一致。
- Cách hỏi: xử lý sự cố
- Hỏi: Address 3在其中一个路线表中包含哪些UC参数？
- Đáp: 可看到SS, UC, 8, 134, 0, 129, 0, 137, 1，后续接GL, AC, 4, EE, 3, SP, 30, GO。文件中也存在另一个版本的Address 3仅使用基本移动命令，因此排查时必须确认当前使用的是哪一个地图版本。来源文件：ACRマップ再検討20260105.xlsx。

## CÂU HỎI 343
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Address 12のUC設定を比較している。
- Cách hỏi: so sánh
- Hỏi: Address 12にはどのようなUCパラメータ差分がありますか。
- Đáp: 一例ではUC, 8, 132, 1, 142, 0, 133, 1, 137, 1、別例ではUC, 8, 132, 0, 141, 0, 133, 0, 137, 1となっています。Map検討Fileには複数案があるため、値だけを見て現行確定仕様と判断しないことが必要です。出典ファイル：ACRマップ再検討20260105.xlsx.

## CÂU HỎI 344
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới thấy nhiều bảng task trong cùng file và nghĩ chúng hoàn toàn giống nhau.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Các bảng Task trong file map này có cùng một cấu hình không?
- Đáp: Không. Có nhiều bảng/phiên bản với khác biệt ở Address, lệnh UC, giá trị SP, góc TR và các Address trung gian. Ví dụ có bảng dùng Address 6/7/10/11/12, trong khi bảng khác dùng 8/9/40/41/42; có phiên bản dùng TR,90, có đoạn dùng TR,180. Nguồn file: ACRマップ再検討20260105.xlsx.

## CÂU HỎI 345
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认路线结束时的Task写法。
- Cách hỏi: trực tiếp
- Hỏi: 路线表的末尾如何表示结束？
- Đáp: Task列表末尾明确出现End。在结束前还可看到返回Address 1的记录，如R, SS, E1, 20, RD, 3。来源文件：ACRマップ再検討20260105.xlsx。

## CÂU HỎI 346
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 旋回角度が90°の想定なのに実機が180°動いたためMapを確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: このFileにはTR,180を使う経路もありますか。
- Đáp: はい。一部のMap案ではAddress 71や107付近にSS, TR, 180が記載されています。一方、他の経路ではTR,90です。したがって異常調査では対象AddressとMap版を一致させて確認する必要があります。出典ファイル：ACRマップ再検討20260105.xlsx.

## CÂU HỎI 347
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn đối chiếu hai khu vực map dùng nhóm Address khác nhau.
- Cách hỏi: so sánh
- Hỏi: Có ví dụ nào cho thấy cùng một pattern task được áp dụng ở dải Address khác nhau không?
- Đáp: Có. Một nhóm sử dụng 1–7, 10–12, 35–37, 110–113; nhóm khác dùng 1–5, 8–9, 40–42, 69–71, 110–113. Điều này cho thấy file đang chứa các phương án map khác nhau chứ không chỉ một chuỗi tuyến duy nhất. Nguồn file: ACRマップ再検討20260105.xlsx.

## CÂU HỎI 348
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人想仅凭Map文件解释GL、AC、EE等命令的技术含义。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 只看这个Map文件就能确定所有命令代码的详细含义吗？
- Đáp: 不能。该文件主要记录Address与Task命令序列，如GL/AC/EE/SP/GO/UC/TR等，但并没有在每个Map表中完整解释所有命令语义。详细定义应结合AGV任务表或通信／Command Spec确认。来源文件：ACRマップ再検討20260105.xlsx。

## CÂU HỎI 349
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: AGV Task Code表から停止Commandを確認している。
- Cách hỏi: trực tiếp
- Hỏi: Code 0x00は何を意味しますか。
- Đáp: Decimal Code 0、HEX 00は停止です。出典ファイル：AGVタスク一覧.xlsx.

## CÂU HỎI 350
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn biết nhóm mã tốc độ được định nghĩa thế nào.
- Cách hỏi: tình huống
- Hỏi: Các code từ 0x01 đến 0x3C chủ yếu có ý nghĩa gì?
- Đáp: Trong bảng control, nhiều code từ decimal 1 đến 60 tương ứng HEX 01–3C được ghi là 速度指定, tức chỉ định tốc độ. Nguồn file: AGVタスク一覧.xlsx.

## CÂU HỎI 351
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: AGV到达分岔点，需要确认直行、右转、左转对应的Code。
- Cách hỏi: trực tiếp
- Hỏi: 分岐直进、右转和左转分别是什么Code？
- Đáp: 0x47 = 分岐 直進，0x48 = 分岐 右折，0x49 = 分岐 左折。来源文件：AGVタスク一覧.xlsx。

## CÂU HỎI 352
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: AGVの旋回動作とスピンターンを区別して確認している。
- Cách hỏi: so sánh
- Hỏi: スピンターンと通常旋回のCodeはどう違いますか。
- Đáp: 0x43はスピンターン 右回り、0x44はスピンターン 左回りです。通常旋回は0x45が旋回 右回り、0x46が旋回 左回りです。出典ファイル：AGVタスク一覧.xlsx.

## CÂU HỎI 353
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: AGV đang chờ nhưng không tiếp tục chạy, kỹ sư cần xác định loại wait.
- Cách hỏi: xử lý sự cố
- Hỏi: Các code wait 0x3D, 0x3E, 0x3F khác nhau như thế nào?
- Đáp: 0x3D là 待機（コントローラ指示待ち）, chờ chỉ thị controller; 0x3E là 待機（START-SW押下待ち）, chờ nhấn START-SW; 0x3F là 待機（外部通信待ち）, chờ giao tiếp bên ngoài. Nguồn file: AGVタスク一覧.xlsx.

## CÂU HỎI 354
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要区分CTU上段和下段的收货／放货Task。
- Cách hỏi: so sánh
- Hỏi: 上段和下段荷受け／荷置き对应哪些Code？
- Đáp: 0x62 = 上段荷受け，0x63 = 上段荷置き，0x64 = 下段荷受け，0x65 = 下段荷置き。另外0x66 = 上荷置き、下荷受け，0x67 = 上荷受け、下荷置き。来源文件：AGVタスク一覧.xlsx。

## CÂU HỎI 355
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: P-RACK 5段目へLiftを移動させるTaskを確認している。
- Cách hỏi: trực tiếp
- Hỏi: 棚5段目の荷受け位置と荷置き位置へのLift移動Codeは何ですか。
- Đáp: 0x7Eがリフト移動（棚5段目 荷受け位置）、0x7Fがリフト移動（棚5段目 荷置き位置）です。出典ファイル：AGVタスク一覧.xlsx.

## CÂU HỎI 356
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn thay đổi tham số khoảng cách sensor phía trước.
- Cách hỏi: tình huống
- Hỏi: Code 91–93 dùng cho mục đích gì và đơn vị thiết lập là gì?
- Đáp: Decimal Code 91/92/93, tương ứng HEX 5B/5C/5D, dùng để đặt khoảng cách sensor phía trước, bên phải và bên trái. Tài liệu ghi tham số có thể đặt trong phạm vi 1–255, đơn vị khoảng cách là 5 cm. Nguồn file: AGVタスク一覧.xlsx.

## CÂU HỎI 357
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为Code 90～95都是普通固定动作，不带参数。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Code 90～95都只是固定动作Code，对吗？
- Đáp: 不对。文件明确说明这些项目可指定任意参数值。Code 90的给电时间单位为秒；91～93的前方检测Sensor距离单位为5 cm；94的磁气Tape忽略距离单位为10 mm；95的走行Line忽略距离单位为10 mm。来源文件：AGVタスク一覧.xlsx。

## CÂU HỎI 358
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: ORICON照合とArm原点復帰のTaskを確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: ORICON ID照合とARM HP復帰のCodeは何ですか。
- Đáp: Decimal 134、HEX 86がオリコンID照合、Decimal 153、HEX 99がアームHP復帰です。出典ファイル：AGVタスク一覧.xlsx.

## CÂU HỎI 359
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang xác nhận revision hiện hành của tài liệu giao tiếp AGV.
- Cách hỏi: trực tiếp
- Hỏi: File AGV通信仕様_260206.xlsx đang ghi version nào?
- Đáp: Trang đầu tài liệu ghi AGV通信仕様 version 0.64. Nguồn file: AGV通信仕様_260206.xlsx.

## CÂU HỎI 360
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师要确认v0.64相对前一版新增了什么。
- Cách hỏi: tình huống
- Hỏi: Version 0.64增加了哪些动作序列？
- Đáp: 2025-11-12的v0.64在AGV_ACR・CTU間通信_動作シーケンス中增加了Task 151 QR照合_オリコン待機和Task 153 アームHP復帰的Sequence。来源文件：AGV通信仕様_260206.xlsx。

## CÂU HỎI 361
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: v0.63とv0.64の変更内容を比較している。
- Cách hỏi: so sánh
- Hỏi: v0.63とv0.64の主な変更点は何ですか。
- Đáp: v0.63ではC3A_UDWR_UDRQにユーザーID0x0009を追加し、ACR・CTU間通信のオプションError Code取得データ数を変更しています。v0.64ではTask 151と153の動作Sequence追加が中心です。出典ファイル：AGV通信仕様_260206.xlsx.

## CÂU HỎI 362
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Jetson không trả đúng trạng thái, kỹ sư cần xác định command lấy status.
- Cách hỏi: xử lý sự cố
- Hỏi: Command nào dùng để lấy trạng thái Jetson và mode được chỉ định thế nào?
- Đáp: Jetson ステイタス取得 dùng command 0x0360 với 1 tham số mode: 0 để lấy Status và 1 để lấy Error Code. Response của 0x0360 trả trạng thái 0: IDLE, 1: Busy, -1: ERROR hoặc số Error Code tùy mode. Nguồn file: AGV通信仕様_260206.xlsx.

## CÂU HỎI 363
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 维护人员需要读取Jetson软件版本。
- Cách hỏi: trực tiếp
- Hỏi: Jetson软件版本读取和版本取得分别使用什么Command？
- Đáp: Jetson ソフトバージョン読み取り为0x0362，其应答为OK / ERROR；Jetson ソフトバージョン取得为0x0363，应答数据长度为16，返回软件版本。来源文件：AGV通信仕様_260206.xlsx。

## CÂU HỎI 364
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Jetsonの画像処理Commandを比較している。
- Cách hỏi: so sánh
- Hỏi: 0x0367と0x0368はパラメータがどう違いますか。
- Đáp: 0x0367のJetson イメージプロセス指示は1データで動作モードを指定します。0x0368のJetson イメージプロセス2指示はデータ数29で、動作モード、オリコンIDを送る仕様です。出典ファイル：AGV通信仕様_260206.xlsx.

## CÂU HỎI 365
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới nghĩ command shutdown Jetson sẽ trả về trạng thái Busy/Idle.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Jetson システムシャットダウン có trả response dạng IDLE/Busy không?
- Đáp: Không. Command shutdown là 0x0366, response được ghi là OK. Trạng thái 0: IDLE / 1: Busy / -1: ERROR thuộc response Jetson ステイタス取得 0x0360. Nguồn file: AGV通信仕様_260206.xlsx.

## CÂU HỎI 366
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要给Jetson设置设备编号和系统时间。
- Cách hỏi: tình huống
- Hỏi: 号机编号和系统时间分别对应什么Command？
- Đáp: Jetson 号机编号指示使用0x0364，Jetson システム時間指示使用0x0365；两者的响应都记录为OK。来源文件：AGV通信仕様_260206.xlsx。

## CÂU HỎI 367
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Jetson起動確認とStatus取得を混同している。
- Cách hỏi: so sánh
- Hỏi: Jetson 起動確認とJetson ステイタス取得は何が違いますか。
- Đáp: 起動確認は0x0361で、応答はOK / ERRORです。Status取得は0x0360で、Modeを指定し、IDLE / Busy / ERRORまたはError Code番号を取得します。出典ファイル：AGV通信仕様_260206.xlsx.

## CÂU HỎI 368
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Jetson image process không phản hồi như mong đợi.
- Cách hỏi: xử lý sự cố
- Hỏi: Khi kiểm tra chuỗi command Jetson image process, những command nào cần đối chiếu?
- Đáp: Có thể đối chiếu 0x0367 = Image Process chỉ thị, 0x0368 = Image Process 2 chỉ thị và 0x0369 = Image Process Status lấy trạng thái. Response của 0x0367/0368 là OK / ERROR; 0x0369 trả Status 0: IDLE, 1: Busy, -1: ERROR hoặc Error Code tương ứng. Nguồn file: AGV通信仕様_260206.xlsx.

## CÂU HỎI 369
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在确认Atlas Command Spec的文档版本。
- Cách hỏi: trực tiếp
- Hỏi: Atlas_Command_Spec_v023 1.xlsm的Command Spec版本是什么？
- Đáp: 首页记录Command Spec Version <0.23>，Revision History中v0.23日期为2025-11-13。来源文件：Atlas_Command_Spec_v023 1.xlsm。

## CÂU HỎI 370
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: v0.23でE1 Commandの修正内容を確認している。
- Cách hỏi: tình huống
- Hỏi: v0.23でE1について何が修正されましたか。
- Đáp: Revision HistoryではE1の誤記を修正し、設定単位を秒に修正したと記載されています。出典ファイル：Atlas_Command_Spec_v023 1.xlsm.

## CÂU HỎI 371
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh các command được thêm ở giai đoạn đầu của Atlas spec.
- Cách hỏi: so sánh
- Hỏi: Version 0.03 đã thêm hoặc thay đổi những command chương trình AGV nào?
- Đáp: v0.03 ghi GN thay đổi spec; thêm BN, BD, GG, BB, WT. Ở nhóm command không công khai cho user, cũng thêm BZ và EZ tại thời điểm đó. Nguồn file: Atlas_Command_Spec_v023 1.xlsm.

## CÂU HỎI 372
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人查看旧资料后仍想使用E5～EC系列Command。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: E5、E6、E7、E8、E9、EA、EC在v0.23中仍然是推荐使用的Command吗？
- Đáp: 不能这样理解。Revision History在v0.11明确记录这些Command被废止，并由UC Command对应。之后v0.12又把UC从用户可用组移到"用户非公开"组。来源文件：Atlas_Command_Spec_v023 1.xlsm。

## CÂU HỎI 373
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: User公開Commandと非公開Commandの変更履歴を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: UC CommandはUser公開Commandとして扱ってよいですか。
- Đáp: v0.11では一度2-1のUser使用可能Commandに追加されましたが、v0.12で2-2 AGVプログラムで使用できるコマンド（ユーザー非公開）へ移動されています。したがってv0.23時点では公開Commandとして扱わない方が資料に整合します。出典ファイル：Atlas_Command_Spec_v023 1.xlsm.

## CÂU HỎI 374
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần biết command nào được thêm cho việc đọc/ghi dữ liệu user.
- Cách hỏi: trực tiếp
- Hỏi: UDWR/UDRQ được thêm từ version nào?
- Đáp: Revision History ghi v0.11 bổ sung UDWR/UDRQ vào nhóm AGV Operation dành cho user, đồng thời thêm mục riêng 3-4. UDWR/UDRQ コマンドについて. Nguồn file: Atlas_Command_Spec_v023 1.xlsm.

## CÂU HỎI 375
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在确认旧版中的BZ/EZ是否还能使用。
- Cách hỏi: tình huống
- Hỏi: BZ和EZ在后续Version中如何处理？
- Đáp: v0.03曾作为用户非公开Command追加，但v0.14的Revision History明确记录BZ/EZ コマンド廃止。因此使用v0.23时不应再按有效Command处理。来源文件：Atlas_Command_Spec_v023 1.xlsm。

## CÂU HỎI 376
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 精密停止Commandの有効性を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: AS（精密停止）を新しいProgramで使用してよいですか。
- Đáp: v0.15でAS（精密停止）コマンドを廃止と記録されています。同VersionでEEとEDの仕様変更も行われています。出典ファイル：Atlas_Command_Spec_v023 1.xlsm.

## CÂU HỎI 377
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần phân biệt thay đổi về command program và operation command của Atlas.
- Cách hỏi: so sánh
- Hỏi: Version 0.16 và 0.17 tập trung vào những loại command khác nhau thế nào?
- Đáp: v0.16 chủ yếu bổ sung operation: thêm PRIN cho AGV Operation dành cho user và LMOP,"PRST" cho line, đồng thời thay đổi spec ngưỡng phát hiện line của PRWR/PRRQ. v0.17 lại bổ sung WM vào AGV program command và thêm phần mô tả về slot number. Nguồn file: Atlas_Command_Spec_v023 1.xlsm.

## CÂU HỎI 378
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师准备按旧Slot 110/111程序直接复制到现场。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Slot 110和111的旧程序可以不确认版本就直接使用吗？
- Đáp: 不建议。v0.23明确记录Slot 110、111的程序错误已被修正，并把原来的Landmark前用／后用程序整合为一个。因此现场使用前应确认当前程序与v0.23修正版一致。来源文件：Atlas_Command_Spec_v023 1.xlsm。
