# Mẻ MOM 01 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Trạng thái: Bản thảo — chưa qua chuyên gia duyệt. Khối: MOM.
Tài liệu: (1) マテコン操作手順書_v001_生産技術 TV.xlsx, (2) AMS_設計変更.pdf, (3) 伝票発行システムマニュアル_仮(JP).pdf, (4) 生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf, (5) ●_KDC_AMSの取り組み VN - Copy.pptx
Phân bố: vi 17, zh 17, ja 16. Đủ 5 cách hỏi.

## CÂU HỎI 1
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư sản xuất đang cấu hình Matecon trước khi chạy ACR trên line.
- Cách hỏi: trực tiếp
- Hỏi: Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?
- Đáp: ctrlMode quy định trạng thái truyền thông SLMP giữa Matecon, hệ thống cấp trên MOM và thiết bị. ctrlMode = 0 là chế độ sản xuất tự động, truyền thông được kích hoạt; Matecon gửi lệnh input/output đến ACR/CTU theo chỉ thị từ hệ thống cấp trên. ctrlMode = 1 là chế độ thủ công và chặn truyền thông. Nguồn file: マテコン操作手順書_v001_生産技術 TV.xlsx.

## CÂU HỎI 2
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên bảo trì thấy ACR không nhận được điều khiển từ Matecon sau khi khởi động.
- Cách hỏi: xử lý sự cố
- Hỏi: ACR không giao tiếp được với Matecon thì cần kiểm tra những gì trước?
- Đáp: Theo hướng dẫn, trước hết kiểm tra máy tính Matecon có kết nối mạng hay không; tiếp theo kiểm tra AGV mục tiêu đã bật nguồn chưa; kiểm tra địa chỉ IP của AGV đã được đăng ký trong file cấu hình chưa; cuối cùng kiểm tra MQTT Broker có đang hoạt động hay không. Không nên kết luận ngay là lỗi phần cứng ACR khi chưa kiểm tra các mục truyền thông này. Nguồn file: マテコン操作手順書_v001_生産技術 TV.xlsx.

## CÂU HỎI 3
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cài Matecon sang một PC mới trên line.
- Cách hỏi: tình huống
- Hỏi: Tôi copy file _Setting.csv sang PC mới nhưng Matecon không load đúng cấu hình. Điểm nào phải kiểm tra?
- Đáp: Tên file cấu hình phải khớp với tên máy tính. Quy trình trong tài liệu là mở thư mục [Setting] của Matecon rồi mở file _Setting.csv gắn với tên máy tính; tài liệu ghi rõ nếu tên file và tên máy tính không khớp thì file cấu hình sẽ không được load chính xác. Ví dụ tên máy tính được nêu trong tài liệu là AthenaLSU-MCS. Nguồn file: マテコン操作手順書_v001_生産技術 TV.xlsx.

## CÂU HỎI 4
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới chuẩn bị chỉnh bản đồ chạy của AGV tại hiện trường.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Sau khi sửa map hành trình hoặc vị trí kệ, có thể cho hệ thống chạy full ngay nếu file save thành công không?
- Đáp: Không. Tài liệu yêu cầu sau khi thay đổi file cấu hình, bản đồ hành trình, thông tin vị trí kệ hoặc thiết lập khu vực block phải thực hiện kiểm tra vận hành trước khi đưa hệ thống vào hoạt động hoàn toàn. Việc thu thập thông tin bản đồ và vị trí kệ cũng nên thực hiện ở tốc độ thấp và trong điều kiện rủi ro thấp. Nguồn file: マテコン操作手順書_v001_生産技術 TV.xlsx.

## CÂU HỎI 5
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 生产技术人员在KDTVN设置Matecon的工厂参数。
- Cách hỏi: trực tiếp
- Hỏi: Matecon配置中的工厂编号，KDTVN应该设成多少？
- Đáp: 配置文件的工厂参数中，资料定义为：0 = KDC（枚方工厂LSU生产线）、1 = KDC（枚方工厂实验室）、2 = KDC（玉城工厂）、3 = KDTCN、4 = KDTVN。因此KDTVN应设为4。来源文件：マテコン操作手順書_v001_生産技術 TV.xlsx。

## CÂU HỎI 6
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 设备维护人员准备手动移动AGV进行故障恢复。
- Cách hỏi: so sánh
- Hỏi: 自动生产模式和手动模式在通信上有什么区别？
- Đáp: ctrlMode = 0为自动生产模式，通信有效，Matecon会根据上位系统MOM的指示向ACR/CTU发送输入输出命令；ctrlMode = 1为手动模式，通信被阻断。因此手动作业时不能把它理解成"仍由MOM正常下发搬送指令"。来源文件：マテコン操作手順書_v001_生産技術 TV.xlsx。

## CÂU HỎI 7
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: AGV在运行过程中发生异常，维修人员准备复归。
- Cách hỏi: xử lý sự cố
- Hỏi: AGV发生错误后，资料规定的基本复归思路是什么？
- Đáp: 首先根据错误信息调查原因。准备重新启动时，需要对AGV执行电源OFF/ON。复归位置应根据发生错误时的行驶方向选择安全的直线轨道位置；例如前进中发生错误时，资料建议选择靠近故障发生地点的地址，前后方向均可。来源文件：マテコン操作手順書_v001_生産技術 TV.xlsx。

## CÂU HỎI 8
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 生産技術の新人がMateconの役割を確認している。
- Cách hỏi: trực tiếp
- Hỏi: Mateconは現場で何をするシステムですか。
- Đáp: MateconはMaterial Handling Controllerの略で、AGV・ACR・CTUに走行指示を出し、稼働状態を監視し、交差点や走行区間を制御するシステムです。本資料は、そのための設定方法と操作方法を説明しています。出典ファイル：マテコン操作手順書_v001_生産技術 TV.xlsx。

## CÂU HỎI 9
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 保全担当者がAGVから異音を確認した直後。
- Cách hỏi: tình huống
- Hỏi: AGVから異音や異臭が出ています。そのまま低速で動かして原因確認してもよいですか。
- Đáp: いいえ。資料では、異音・異臭・異常な動作を確認した場合は、AGVを直ちに停止して原因を調査するよう定めています。また、起動・運転・エラー復旧・手動操作を行う場合は、周辺に作業者がいないことを確認する必要があります。出典ファイル：マテコン操作手順書_v001_生産技術 TV.xlsx。

## CÂU HỎI 10
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 現場担当者がAGVを手動運転しようとしている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: AGVの手動運転は、ライン作業者なら誰でも実施できますか。
- Đáp: できません。資料では、手動モードでの走行は生産技術担当者または設備保全担当者が実施するものとされています。さらに、操作前にはAGV周辺に作業者がいないことを確認する必要があります。出典ファイル：マテコン操作手順書_v001_生産技術 TV.xlsx。

## CÂU HỎI 11
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư MOM đang đối chiếu dữ liệu thay đổi thiết kế từ Teamcenter sang Opcenter.
- Cách hỏi: so sánh
- Hỏi: Trong cấu trúc AMS, BOP lắp ráp bên Teamcenter được ánh xạ sang những đối tượng nào của Opcenter?
- Đáp: Tài liệu mô tả phía Teamcenter có Process, Compound Operation, Parts/Revision, Execution Step, Work Area và BOE. Sang Opcenter, cấu trúc được thể hiện bằng Workflow, ERP Route, ERP BOM, Spec, Operation, Resource Group, Resource, Factory và các thông tin Work Center liên quan. Đây là ánh xạ cấu trúc phục vụ MOM, không phải quan hệ chỉ giữa một bảng với một bảng. Nguồn file: AMS_設計変更.pdf.

## CÂU HỎI 12
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra master của một Workflow sản xuất trước khi phát hành lệnh.
- Cách hỏi: trực tiếp
- Hỏi: Ví dụ Workflow sản xuất 3A2V900630 trong tài liệu có Revision và Status là gì?
- Đáp: Ví dụ trong tài liệu ghi Workflow sản xuất có Name = 3A2V900630, Revision = 0010 và Status = Active. Trong cùng ví dụ, StepName/Spec/RouteStep dùng ID công đoạn Y302V900010101. Nguồn file: AMS_設計変更.pdf.

## CÂU HỎI 13
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên quản lý thay đổi cần chọn cách chuyển từ revision cũ sang mới.
- Cách hỏi: tình huống
- Hỏi: Nếu thay đổi được chỉ định chuyển đúng vào một ngày cụ thể thì thiết lập kiểu chuyển nào?
- Đáp: Bảng chuyển đổi trong tài liệu có trường hợp 期日切替 với ngày dạng YYYY/MM/DD và chỉ thị The day: đến ngày chỉ định thì chuyển từ cấu hình cũ sang mới. Ngoài ra còn có After, Before, RC và OR cho các kiểu chuyển khác. Nguồn file: AMS_設計変更.pdf.

## CÂU HỎI 14
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: MOM工程师确认供给Workflow的命名规则。
- Cách hỏi: trực tiếp
- Hỏi: 供给用Workflow的Name在资料示例中是怎么组成的？
- Đáp: 资料示例中的供给Workflow名称为302ND19100_0010_YB1000320004，其构成为"品目 + _ + 供给先Work Center"。资料同时说明供给用Workflow与制造用Workflow的命名及Route/Spec结构不同，检查时应按供给侧规则确认。来源文件：AMS_設計変更.pdf。

## CÂU HỎI 15
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 生产计划人员准备确认设计变更后的旧部品、新部品切换。
- Cách hỏi: xử lý sự cố
- Hỏi: 部品REV UP时，旧REV和新REV都存在，MOM侧应关注什么切换状态？
- Đáp: 资料示例中，部品REV UP时通过Is ROR控制使用对象：切换前旧部品-01为True、新部品-02为False；切换后旧部品变为False，新部品变为True。同时流程中还要确认仓库库存、部品消耗计划和设计变更切换条件。来源文件：AMS_設計変更.pdf。

## CÂU HỎI 16
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师在检查制造品目变更后的MFG Order。
- Cách hỏi: so sánh
- Hỏi: 部品REV UP和生产品目变更时，MFG Order侧的处理有什么不同？
- Đáp: 资料中，部品REV UP主要切换ERP BOM内相关部品的Is ROR状态；生产品目变更时，则示例为MFG Order的Workflow和ERP BOM从生产品目A的-01切到-02，并将旧Workflow的Is ROR从True切为False、新Workflow从False切为True。来源文件：AMS_設計変更.pdf。

## CÂU HỎI 17
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人正在确认BOP变更是否只需要修改部品Revision。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 只要部品REV发生变化，Process和Operation也一定要REV UP，对吗？
- Đáp: 不对。资料的BOP变更示例明确区分"部品のみREVUP"和Process/Operation变更。仅部品REV UP时，并不能据此认定Process和Operation也必须同时REV UP；而品目或工程结构发生变化时，Process/Operation侧可能需要相应的Revision变化。来源文件：AMS_設計変更.pdf。

## CÂU HỎI 18
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 製造技術担当者が設変切替前にOpcenterのマスタを確認している。
- Cách hỏi: trực tiếp
- Hỏi: 製造Workflowの例では、SpecとRouteStepには何が設定されていますか。
- Đáp: 資料の製造Workflow例では、Workflow Nameは3A2V900630、Revisionは0010、StatusはActiveです。StepName、Spec、RouteStepには例としてY302V900010101が設定されています。出典ファイル：AMS_設計変更.pdf。

## CÂU HỎI 19
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 設変切替で旧品在庫が残っているか確認している。
- Cách hỏi: tình huống
- Hỏi: 切替日になったら、在庫確認をせずに新REVへ切り替えてよいですか。
- Đáp: 資料の設変切替フローでは、指図取込、BOP割当、倉庫在庫確認、部品消費予定時間算出、製造計画、供給計画などを確認した上で切替を進めます。したがって、切替日だけを見て在庫確認を省略する運用とは記載されていません。出典ファイル：AMS_設計変更.pdf。

## CÂU HỎI 20
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者が設変の切替パターンを理解しているか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 切替指示は日付指定のThe dayだけですか。
- Đáp: いいえ。資料には、指定日に切り替えるThe dayのほか、期日以降のAfter、期日までのBefore、旧品使用後のRC、切替生産を可能にするORのパターンが記載されています。それぞれ旧・新の優先条件が異なるため、切替条件を確認する必要があります。出典ファイル：AMS_設計変更.pdf。

## CÂU HỎI 21
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Công nhân kho cần phát phiếu để ORICON gate có thể xử lý nhập kho.
- Cách hỏi: trực tiếp
- Hỏi: Hệ thống phát hành phiếu này dùng để làm gì?
- Đáp: Đây là ứng dụng phát hành phiếu có thể được xử lý nhập kho tại ORICON gate. Tài liệu nêu ba trường hợp chính cần hệ thống: nhà cung cấp chưa chuyển sang phiếu hỗ trợ xử lý nhập kho, nhà cung cấp chưa hỗ trợ EDI, và hàng về bằng non-ORICON sau đó được chuyển sang ORICON nên cần tạo phiếu nhập kho mới. Nguồn file: 伝票発行システムマニュアル_仮(JP).pdf.

## CÂU HỎI 22
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người dùng mới chưa truy cập được ứng dụng phát hành phiếu từ PC.
- Cách hỏi: xử lý sự cố
- Hỏi: Trước khi dùng ứng dụng từ xa, chứng chỉ phải được cài như thế nào?
- Đáp: Đầu tiên lưu chứng chỉ server.crt vào một thư mục bất kỳ; chứng chỉ được bộ phận 製造技術31課 phát cho người dùng. Mở quản lý chứng chỉ người dùng, vào 信頼されたルート証明機関 → 操作 → すべてのタスク → インポート, chọn file server.crt, sau đó chọn kho chứng chỉ tin cậy và hoàn tất wizard import. Nguồn file: 伝票発行システムマニュアル_仮(JP).pdf.

## CÂU HỎI 23
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên kho muốn phát nhiều phiếu bằng cách chọn trực tiếp mã hàng.
- Cách hỏi: tình huống
- Hỏi: Tôi biết mã hàng và số lượng, không có D-label. Phát phiếu theo cách nào?
- Đáp: Chọn tab 複数枚発行, sau đó chọn 品目, nhập số lượng và nhấn 生成. Hệ thống hiển thị số phiếu sẽ tạo và nội dung phân bổ; số đơn hàng được sinh dựa trên ngày tạo và số thứ tự box cũng được gán. Tiếp theo xem preview → chọn 印刷, tại màn hình thiết lập in chọn 印刷 lần nữa để hoàn tất. Nguồn file: 伝票発行システムマニュアル_仮(JP).pdf.

## CÂU HỎI 24
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 仓库人员拿到D标签，需要复制标签信息重新发行传票。
- Cách hỏi: tình huống
- Hỏi: 从D标签复制信息发行传票时，条码应该按什么顺序读取？
- Đáp: 在菜单中选择ハンディターミナル，然后依次读取现品票上的Code39 3N3和3N4。读取后画面会显示读取信息和标签输出信息。必要时可编辑数量并输入LOT，这两项属于任意操作；之后按生成，确认预览，再执行打印。来源文件：伝票発行システムマニュアル_仮(JP).pdf。

## CÂU HỎI 25
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 品目没有规定格式的现品票，现场需要制作可用于AMS的二维码来源条码。
- Cách hỏi: trực tiếp
- Hỏi: Dummy Barcode一共需要几个？分别包含什么信息？
- Đáp: 每个品目需要两个Dummy Barcode。一个是3N3信息，由虚拟订单号＋明细号＋枝番＋交货数量组成；另一个是3N4信息，由品目＋Revision＋箱入数构成。这两个条码作为使用手持终端等生成AMS对应QR码的基础信息。来源文件：伝票発行システムマニュアル_仮(JP).pdf。

## CÂU HỎI 26
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 管理员发现画面上无法选择某个品目发行传票。
- Cách hỏi: xử lý sự cố
- Hỏi: 品目选择画面中找不到目标品目时，应先确认哪个Master？
- Đáp: 通过画面选择品目发行传票之前，必须预先登记Master。资料要求管理员使用Microsoft SQL Server Management Studio连接各据点指定Server，打开Databases → MOM_IF → Tables，编辑dbo.t_item master，保存后再用Select Top 1000 Rows确认修改内容已保存。来源文件：伝票発行システムマニュアル_仮(JP).pdf。

## CÂU HỎI 27
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 作業者が現品票なしの部品をオリコンに詰め替えて入庫しようとしている。
- Cách hỏi: trực tiếp
- Hỏi: ダミーバーコードから伝票を発行する最初の操作は何ですか。
- Đáp: メニュータブからカメラ/手入力を選択し、スキャン開始を押します。その後、ダミーバーコードの3N3、3N4を順に読み取り、数量を入力します。LOT入力は任意です。生成後にプレビューを確認し、印刷設定画面から印刷して完了します。出典ファイル：伝票発行システムマニュアル_仮(JP).pdf。

## CÂU HỎI 28
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人がDラベル複製方式と品目選択方式の違いを確認している。
- Cách hỏi: so sánh
- Hỏi: 「品目を選択して発行」と「Dラベルから複製して発行」の違いは何ですか。
- Đáp: 品目選択方式は複数枚発行から品目と数量を指定し、注文番号と箱連番をシステム側で生成して発行します。Dラベル複製方式はハンディターミナルで元の現品票の3N3、3N4を読み取り、その情報をもとにラベルを生成します。後者では必要に応じて数量編集とLOT入力も可能です。出典ファイル：伝票発行システムマニュアル_仮(JP).pdf。

## CÂU HỎI 29
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者がマスター登録手順を理解しているか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 品目マスターは伝票を発行した後に登録すればよいですか。
- Đáp: いいえ。画面で品目を選択して伝票を発行する場合は、事前にマスター登録が必要です。資料ではMOM_IFデータベースのdbo.t_item masterを編集し、保存後にSelect Top 1000 Rowsで登録内容を確認する手順が示されています。出典ファイル：伝票発行システムマニュアル_仮(JP).pdf。

## CÂU HỎI 30
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 現場で非オリコン入荷品をオリコンへ詰め替える作業をしている。
- Cách hỏi: xử lý sự cố
- Hỏi: 元の現品票が規定フォーマットではない場合、伝票発行をあきらめる必要がありますか。
- Đáp: いいえ。資料では、規定フォーマットと異なる現品票、または現品票がない場合に備えてダミーバーコード方式が定義されています。品目ごとに3N3情報と3N4情報の2つのダミーバーコードを用意し、それを読み取ってAMS対応の伝票を生成できます。出典ファイル：伝票発行システムマニュアル_仮(JP).pdf。

## CÂU HỎI 31
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Quản lý line muốn biết chức năng nào của hệ thống lịch sử sản xuất đã hoàn tất kiểm chứng.
- Cách hỏi: trực tiếp
- Hỏi: Trong 6 chức năng yêu cầu, chức năng nào được ghi là đã kiểm chứng xong?
- Đáp: Trong bảng yêu cầu chức năng, mục ❺ 戻入／分割入庫単作成 — tạo phiếu nhập kho cho trả lại/chia tách — được ghi là 検証完了 (đã hoàn tất kiểm chứng). Các mục line-out/return, nhập nội dung sửa chữa, dừng/khôi phục cấp linh kiện và sửa 工程在庫 được ghi 検証中; đăng ký nhân lực sản xuất đang ở trạng thái 仕様DR中. Nguồn file: 生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf.

## CÂU HỎI 32
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Thiết bị NG được đưa ra khỏi line và kỹ sư cần đăng ký yêu cầu sửa chữa.
- Cách hỏi: tình huống
- Hỏi: Khi tạo yêu cầu sửa chữa cho một máy bị Line-Out, cần nhập những thông tin chính nào?
- Đáp: Màn hình yêu cầu sửa chữa yêu cầu các thông tin: Line, công đoạn và 工程ID; số máy/機番; phân loại lỗi và chi tiết; bộ phận xử lý và người yêu cầu; đồng thời có thể đính kèm ảnh và video. Quy trình sau đó đi qua sửa chữa, xác nhận kết quả và trả thiết bị về line. Nguồn file: 生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf.

## CÂU HỎI 33
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: QC xác nhận thiết bị sau sửa chữa nhưng kết quả vẫn NG.
- Cách hỏi: xử lý sự cố
- Hỏi: QC xác nhận kết quả NG thì thiết bị có được trả thẳng về line không?
- Đáp: Không. Bước 修理結果確認 ghi rõ phải nhập người xác nhận, kết quả NG/OK và bộ phận xử lý. Nếu OK thì chuyển sang Line返却; nếu NG thì bị trả lại để sửa tiếp. Chỉ sau khi kết quả được chấp nhận mới thực hiện trả thiết bị về line. Nguồn file: 生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf.

## CÂU HỎI 34
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư dữ liệu đang đối chiếu bản ghi Line-Out và Line-In trong bảng liên kết trạng thái.
- Cách hỏi: so sánh
- Hỏi: Status code của Line-Out và Line復帰 trong bảng trạng thái là gì?
- Đáp: Tài liệu quy định bản ghi Line-Out dùng STATUS1 = LO, còn Line復帰 dùng STATUS1 = LI. Hai loại bản ghi đều có các trường như REVISION, DESTINATION, DATE_TIME, STATUS1, STATUS2, PROCESS_ID, NO, DATA_NAME và DATA_VALUE. Nguồn file: 生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf.

## CÂU HỎI 35
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: QC人员在看板上跟踪设备异常处理进度。
- Cách hỏi: trực tiếp
- Hỏi: 看板可以显示哪些异常处理信息？
- Đáp: 资料规定看板可在PC、HT和现场Monitor上实现可视化，内容包括Line-Out履历管理、APP版本管理及发行、照片/视频预览以及多语言切换。异常照片和异常视频可以点击预览，并显示状态、异常内容和修理内容。来源文件：生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf。

## CÂU HỎI 36
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 修理人员完成调查，准备把状态更新为处理完成。
- Cách hỏi: tình huống
- Hỏi: 品质联携表中，"调查中"和"处理完成"的STATUS分别是什么？
- Đáp: 在品质联携表中，调查开始时资料标记STATUS = 0：调查中；处理完成时标记STATUS = 1：処置完了。表中还包括S_NO、LATEST_FLAG、PROCESS_ID、DEFECT_ITEM_01/02、CAUSE、TREATMENT、MANAGER和DETAIL等字段，调查进展过程中可随时登记。来源文件：生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf。

## CÂU HỎI 37
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 生产技术人员登记修理内容，发生了部品更换。
- Cách hỏi: xử lý sự cố
- Hỏi: 修理过程中更换了部品，只记录修理备注就够了吗？
- Đáp: 不够。资料在修理内容输入中要求记录部品交换、不良现象、修理内容、修理担当、确认部门以及照片/视频等附件。另外状态联携设计中，部品交换使用PC：部品交換，并登记品目和数量。资料还把Unit/Assy/部品SN绑定和Lot作为课题列出，因此这些绑定细节尚不能当作已完成正式功能。来源文件：生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf。

## CÂU HỎI 38
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 製造領班がLine-Out後の処理フローを新人に説明している。
- Cách hỏi: trực tiếp
- Hỏi: Line-Outした機器は、どのような流れでラインへ戻しますか。
- Đáp: 資料では、製造によるLine-Out後、製造・QCで調査／修理し、必要に応じてIEやKDC技術も対応します。HTでは「機器修理申請」→「修理内容登録」→「修理結果確認」→「機器ライン返却」の順で登録します。QC等の確認でOKとなった後、製造領班がライン返却を行います。出典ファイル：生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf。

## CÂU HỎI 39
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人が「修理」と「確認」の役割を混同している。
- Cách hỏi: so sánh
- Hỏi: 「修理内容入力」と「修理結果確認」は何が違いますか。
- Đáp: 修理内容入力では、部品交換、不良現象、修理内容、修理担当、確認部門、写真・動画などの修理添付情報を登録します。一方、修理結果確認では確認担当、結果（NG/OK）、次の処理部門を登録します。OKならLine返却へ進み、NGなら修理へ返却されます。出典ファイル：生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf。

## CÂU HỎI 40
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者が工程在庫修正機能の用途を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 工程在庫修正は、単純な数量不足だけに使う機能ですか。
- Đáp: いいえ。資料では、工程在庫修正の目的として、加工中不良処理、加工前不良処理、員数過不足処理、MOM管理対象外への在庫移動が記載されています。トリガーも部品不良、員数過不足、別場所への移動など複数あります。出典ファイル：生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf。

## CÂU HỎI 41
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư PLM/MOM mới tham gia dự án AMS cần hiểu luồng dữ liệu master.
- Cách hỏi: trực tiếp
- Hỏi: BOP được xây dựng và đưa sang Opcenter theo luồng hệ thống nào?
- Đáp: Tài liệu mô tả EBOM/MBOM/BOE và thông tin liên quan được quản lý trong chuỗi NX/CAD, VPS MFG, COLMINA và Teamcenter. MBOM và BOE đăng ký trên Teamcenter được liên kết sang COLMINA để định nghĩa master công đoạn sản xuất trên VPS MFG; thay đổi master được quản lý trên COLMINA, liên kết lại Teamcenter và đăng ký thành BOP. Sau đó BOP được liên kết MOM sang Opcenter theo đơn vị ECN để cập nhật kế hoạch công đoạn và thực hiện sản xuất. Nguồn file: ●_KDC_AMSの取り組み VN - Copy.pptx.

## CÂU HỎI 42
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới hỏi tại sao phải có cả MBOM, BOE và BOP trong chuẩn bị sản xuất.
- Cách hỏi: so sánh
- Hỏi: MBOM, BOE và BOP trong tài liệu có vai trò khác nhau như thế nào?
- Đáp: Tài liệu gọi MBOM là BOM chế tạo, BOE là tài nguyên nhà xưởng và BOP là quy trình chế tạo. MBOM và BOE là dữ liệu đầu vào quan trọng để định nghĩa master công đoạn sản xuất; BOP biểu diễn cấu trúc/quy trình chế tạo và là đối tượng được liên kết sang MOM/Opcenter. Tài liệu không mô tả đây là ba tên khác nhau của cùng một dữ liệu. Nguồn file: ●_KDC_AMSの取り組み VN - Copy.pptx.

## CÂU HỎI 43
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra một thay đổi ECN trước khi cập nhật sản xuất.
- Cách hỏi: tình huống
- Hỏi: Sau khi có ECN, BOP có đi thẳng từ Teamcenter ra line sản xuất không?
- Đáp: Không theo sơ đồ trong tài liệu. BOP được liên kết MOM sang Opcenter theo đơn vị ECN. Opcenter là hệ MOM nơi thực hiện cập nhật kế hoạch công đoạn và thực hiện sản xuất. Vì vậy khi đối chiếu thay đổi cần kiểm tra ít nhất BOP/ECN phía PLM và dữ liệu tương ứng đã được liên kết sang Opcenter. Nguồn file: ●_KDC_AMSの取り組み VN - Copy.pptx.

## CÂU HỎI 44
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: PLM工程师需要向现场说明Teamcenter与Opcenter的分工。
- Cách hỏi: trực tiếp
- Hỏi: Teamcenter和Opcenter在AMS的资料中分别承担什么角色？
- Đáp: Teamcenter被定义为PLM侧，用于产品/设备设计数据以及BOP等制造过程信息的管理；Opcenter被定义为MOM侧，接收按ECN单位联携过来的BOP信息，并用于工程计划更新和制造执行。来源文件：●_KDC_AMSの取り組み VN - Copy.pptx。

## CÂU HỎI 45
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程技术人员核对制造工程Master的数据来源。
- Cách hỏi: so sánh
- Hỏi: VPS MFG和COLMINA在制造工程Master处理中有什么区别？
- Đáp: 资料说明，将Teamcenter中登记的MBOM和BOE联携到COLMINA，用于在VPS MFG上定义制造工程Master；COLMINA负责制造工程Master的变更管理，并把结果联携回Teamcenter，登记为BOP。因此VPS MFG侧重点是制造准备/工程定义，COLMINA侧重点是制造工程Master管理和变更管理。来源文件：●_KDC_AMSの取り組み VN - Copy.pptx。

## CÂU HỎI 46
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 现场发现Opcenter中的工程计划没有反映最新设计变更。
- Cách hỏi: xử lý sự cố
- Hỏi: 最新ECN已经在PLM侧处理，但Opcenter工程计划没更新，应该从什么联携链路开始核对？
- Đáp: 根据资料中的系统关系，应从"Teamcenter中的BOP/ECN → MOM联携（CN4T）→ Opcenter"的链路核对，并确认该BOP变更是否以ECN单位完成联携。资料只给出了系统关系和联携方向，没有给出具体错误代码或数据库排查步骤，因此进一步判断接口失败原因属于尚未由该文件直接确认的内容。来源文件：●_KDC_AMSの取り組み VN - Copy.pptx。

## CÂU HỎI 47
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为BOP只是一张部品清单，主管正在检查其理解。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: BOP就是把EBOM复制成制造用BOM，对吗？
- Đáp: 不对。资料把EBOM定义为设计BOM、MBOM定义为制造BOM，而BOP定义为制造过程。示例BOP包含工程，例如工程1下有01 装着、FRAME、PLATE、SPRING以及02 装着等结构，因此BOP不仅是部品清单，还表达制造工程结构。来源文件：●_KDC_AMSの取り組み VN - Copy.pptx。

## CÂU HỎI 48
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: MOM担当者がPLMからのデータ連携範囲を確認している。
- Cách hỏi: trực tiếp
- Hỏi: BOPはどの単位でOpcenterへ連携されますか。
- Đáp: 資料では、BOPはECN（変更通知）単位でMOM連携され、Opcenterへ反映されます。その後、Opcenter側で工程計画を更新し、製造実行につなげる流れです。出典ファイル：●_KDC_AMSの取り組み VN - Copy.pptx。

## CÂU HỎI 49
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 生産準備担当者がBOP登録前のシステム連携を確認している。
- Cách hỏi: tình huống
- Hỏi: TeamcenterにMBOMとBOEを登録した後、製造工程マスタはどのように作られますか。
- Đáp: 資料では、Teamcenterに登録したMBOMとBOEをCOLMINAへ連携し、VPS MFG上で製造工程マスタを定義します。COLMINAで製造工程マスタの変更管理を行い、その情報をTeamcenterへ連携してBOPとして登録する流れです。出典ファイル：●_KDC_AMSの取り組み VN - Copy.pptx。

## CÂU HỎI 50
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 現場から「最新BOPが反映されていない」と問い合わせがあり、担当者が理解を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: Opcenterに最新BOPが見えない場合、この資料だけで具体的なDBテーブルやリトライ手順まで判断できますか。
- Đáp: できません。この資料から正式に確認できるのは、BOPがECN単位でMOM連携され、Teamcenter側からOpcenter側へつながるシステム構成と役割までです。具体的なDBテーブル、エラーコード、再送・リトライ手順はこの資料には記載されていないため、その部分を断定するのは推論になります。出典ファイル：●_KDC_AMSの取り組み VN - Copy.pptx。
