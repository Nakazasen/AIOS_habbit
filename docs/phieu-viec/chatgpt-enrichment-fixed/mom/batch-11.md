# Mẻ MOM 11 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Trạng thái: Bản thảo — chưa qua chuyên gia duyệt. Khối: MOM.
5 file trong 仕様書, mỗi file 10 cặp, câu 479–528. Không file nào bị bỏ qua.
Lưu ý: AGV通信仕様.xlsx là file riêng (v0.64, full revision history 0.1→0.64), khác với AGV通信仕様_260206.xlsx ở mẻ 8 — cần dedup khi import.

## CÂU HỎI 479
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xóa hoàn toàn dữ liệu của một ORICON đã nhập kho để tái kiểm chứng.
- Cách hỏi: trực tiếp
- Hỏi: Dữ liệu nhập kho đã hoàn tất phải được xóa hoặc điều chỉnh ở những hệ thống nào?
- Đáp: Tài liệu yêu cầu xử lý ở cả 3 nơi: ① bảng xử lý nhập kho, ② WMS, ③ Opcenter. Chỉ xử lý một phía là chưa đủ để đồng bộ trạng thái của ORICON. Nguồn file: 入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 480
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师准备从入库接口表删除测试ORICON。
- Cách hỏi: trực tiếp
- Hỏi: 入库处理Table中应该删除哪一类数据？
- Đáp: 应从T_PARTS_RECEIVE中DELETE对应ORICON ID的数据。资料把这一步列为"1. 入庫処理テーブル"的处理。来源文件：入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 481
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: WMS側で入庫済み在庫を取り消したい。
- Cách hỏi: tình huống
- Hỏi: WMSではどの画面から対象在庫を調整しますか。
- Đáp: 在庫一覧画面へ移動し、対象の在庫Dataを選択して調整画面へ進みます。その後、調整数と調整理由を入力して実行します。出典ファイル：入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 482
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Trong WMS có 1 đơn vị tồn kho test cần loại bỏ.
- Cách hỏi: tình huống
- Hỏi: Nếu muốn giảm tồn kho WMS từ 1 xuống 0 thì nhập số lượng điều chỉnh bao nhiêu?
- Đáp: Ví dụ trong tài liệu sử dụng 調整数量 = -1, nhập thêm lý do điều chỉnh rồi nhấn nút thực thi. Nguồn file: 入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 483
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: WMS库存已经调成0，但Opcenter中Container仍然存在。
- Cách hỏi: xử lý sự cố
- Hỏi: Opcenter侧应如何把该ORICON数量调整为0？
- Đáp: 在ChangeQty画面显示目标ORICON，输入调整数量；资料示例为-1，并把AdjustReason设为Inv Adjustment，然后执行Submit。来源文件：入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 484
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: WMSとOpcenterの在庫取消方法を比較している。
- Cách hỏi: so sánh
- Hỏi: WMS側とOpcenter側では数量調整の操作がどう違いますか。
- Đáp: WMS側では在庫一覧から対象Dataを選び、調整画面で調整数と理由を入力します。Opcenter側ではChangeQtyでORICONを表示し、AdjustQty相当の数量とAdjustReason = Inv Adjustmentを設定してSubmitします。出典ファイル：入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 485
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: ORICON test đã được đưa quantity về 0 và kỹ sư chuẩn bị dùng lại cùng ORICON ID.
- Cách hỏi: xử lý sự cố
- Hỏi: Sau ChangeQty, còn phải làm gì với tên Container?
- Đáp: Mở ContainerRename, đổi tên Container theo quy tắc RenameYYYYMMDD_連番 rồi Submit. Điều này tránh để Container cũ tiếp tục giữ tên ORICON ID cũ. Nguồn file: 入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 486
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人只删除T_PARTS_RECEIVE后就准备重新入库。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 从T_PARTS_RECEIVE删除ORICON记录后，就算全部清理完成了吗？
- Đáp: 不对。资料明确要求同时处理入庫処理テーブル、WMS和Opcenter三个位置。只删接口表可能导致WMS库存或Opcenter Container仍然残留。来源文件：入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 487
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Test Data削除の順序を確認している。
- Cách hỏi: trực tiếp
- Hỏi: 資料では削除処理をどの3区分で説明していますか。
- Đáp: 1. 入庫処理テーブル、2. WMS、3. Opcenterの3区分です。各Systemに残るDataを個別に処理する構成です。出典ファイル：入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 488
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so với quy trình clear dữ liệu đầy đủ đã dùng trước đó.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File này có mô tả cả bước Unload MaterialQueue và xóa SUPPLY_ORDER như file clear dữ liệu hoàn toàn không?
- Đáp: Không. File này tập trung vào dữ liệu đã hoàn tất nhập kho và mô tả xử lý T_PARTS_RECEIVE, WMS, ChangeQty và ContainerRename. Trong nội dung đọc được không có bước Unload MaterialQueue hay xóa SUPPLY_ORDER; không nên tự bổ sung chúng vào quy trình của file này. Nguồn file: 入庫済みデータ削除_20260213.xlsx.

## CÂU HỎI 489
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人第一次参加PLM基础培训。
- Cách hỏi: trực tiếp
- Hỏi: PLM是什么？
- Đáp: PLM是Product Lifecycle Management，日文为製品ライフサイクル管理。资料将其定义为：在产品整个Lifecycle中统一管理Master Data及其Process，并以Object为单位管理信息以及Object之间的关系。来源文件：PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 490
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần giải thích vì sao PLM không chỉ quản lý giai đoạn thiết kế.
- Cách hỏi: tình huống
- Hỏi: Product lifecycle trong tài liệu bao gồm những giai đoạn chính nào?
- Đáp: Tài liệu chia thành 5 giai đoạn: 製品開発期 – phát triển sản phẩm, 導入期 – giới thiệu, 成長期 – tăng trưởng, 成熟期 – trưởng thành và 衰退期 – suy thoái. PLM quản lý thông tin sản phẩm xuyên suốt dòng đời này. Nguồn file: PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 491
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 生産実績と品目情報の違いをPLM視点で説明している。
- Cách hỏi: so sánh
- Hỏi: マスターデータとトランザクションデータはどう違いますか。
- Đáp: マスターデータは品番、名称、仕様、社員、取引先など会社業務の基盤となる比較的静的な情報で、正確性と一貫性が求められます。工程計画、生産実績、在庫量、経費実績など、継続的に追加・変化するDataはトランザクションデータです。出典ファイル：PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 492
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 管理者说明为什么公司导入PLM。
- Cách hỏi: trực tiếp
- Hỏi: 资料把PLM的主要效果归纳为什么？
- Đáp: 主要归纳为QCD提升：Q为产品质量提高，C为设计／制造成本降低，D为业务效率提升和Lead Time缩短。来源文件：PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 493
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới nghĩ PLM chỉ có chức năng BOM.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: PLM chỉ dùng để quản lý BOM, đúng không?
- Đáp: Không. Tài liệu liệt kê các chức năng đại diện gồm マスターデータ管理, BOM管理, 設計変更管理, ワークフロー管理 và プロジェクト管理. Trong vận hành thực tế, nhiều chức năng thường được sử dụng kết hợp. Nguồn file: PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 494
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: BOMという言葉を新人へ説明している。
- Cách hỏi: trực tiếp
- Hỏi: BOMは何の略で、一般的に何を指しますか。
- Đáp: BOMはBill of Materialの略で、日本語では部品表または部品構成表です。資料では一般的にBOMは構成情報を指すと説明しています。出典ファイル：PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 495
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要解释BOM为什么会影响采购和库存。
- Cách hỏi: tình huống
- Hỏi: BOM除了设计用途外，为什么对生产和采购也重要？
- Đáp: 资料说明BOM用于有效管理生产所需部品，可以支持采购、交期和库存的准确掌握，防止原材料／部品缺料及漏采购；进入生产阶段后，也可用于按工序掌握需要的部品、组装顺序和生产顺序。来源文件：PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 496
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang phân biệt EBOM với cấu trúc dành cho sản xuất.
- Cách hỏi: so sánh
- Hỏi: EBOM được tài liệu mô tả như thế nào?
- Đáp: EBOM là Engineering BOM, còn được gọi là BOM thiết kế hoặc BOM kỹ thuật. Nó được bộ phận thiết kế sử dụng để làm rõ ý đồ thiết kế và specification của sản phẩm. Nguồn file: PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 497
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: BOPの意味をMOM担当へ説明している。
- Cách hỏi: tình huống
- Hỏi: BOPではどのような製造情報を定義しますか。
- Đáp: 資料ではBOPを、ある製品をあるLineで生産する際に「どの工程で何をするか」「どの部品・材料を使うか」「工程場所はどこか」「どの設備・工具を使うか」を定義するものとして説明しています。出典ファイル：PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 498
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人把PN和PS都理解为"部品编号"。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: PN和PS是完全相同的信息吗？
- Đáp: 不是。资料总结指出BOM由PN的品目信息和PS的构成信息组成，并特别强调理解和区分PN／PS、品目信息／构成信息，是理解PLM的重要基础。来源文件：PLMシステム基礎講習_20250918 2.pptx.

## CÂU HỎI 499
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: ORICON Gateで読める現品票を新たに発行したい。
- Cách hỏi: trực tiếp
- Hỏi: 伝票発行システムの主な目的は何ですか。
- Đáp: オリコンゲートで入庫処理できる伝票を発行するアプリケーションです。EDI未対応取引先や新形式へ未切替の取引先、非ORICON入荷品をORICONへ詰替えた場合などに対応します。出典ファイル：伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 500
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người dùng chuẩn bị kết nối vào ứng dụng phát hành phiếu từ PC mới.
- Cách hỏi: tình huống
- Hỏi: Trước khi remote access vào ứng dụng cần cài certificate nào?
- Đáp: Cần lưu certificate server.crt do 製造技術31課 phát hành, mở quản lý chứng chỉ người dùng và import vào vùng certificate tin cậy theo hướng dẫn. Nguồn file: 伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 501
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 管理员准备登记可从画面选择的Item Master。
- Cách hỏi: trực tiếp
- Hỏi: Item Master登记在哪个DB Table中进行？
- Đáp: 使用SQL Server Management Studio连接各据点Server，进入Databases → MOM_IF → Tables，对dbo.t_item master执行Edit Top 200 Rows进行登记，并可通过Select Top 1000 Rows确认保存结果。来源文件：伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 502
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 現品票が無い部品に対してDummy Barcodeを作成している。
- Cách hỏi: so sánh
- Hỏi: 3N3情報と3N4情報には何を入れますか。
- Đáp: 3N3は架空の注文番号＋明細番号＋枝番＋納品数量、3N4は品目＋Revision＋箱入数です。Dummy Barcodeは1品目につきこの2種類が必要です。出典ファイル：伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 503
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Công nhân có Item/Revision nhưng không có phiếu đúng format.
- Cách hỏi: xử lý sự cố
- Hỏi: Quy trình tạo dummy barcode cơ bản như thế nào?
- Đáp: Chọn tab バーコード発行, nhập Item và Revision rồi chọn 生成; kiểm tra preview, chọn 印刷, sau đó in từ màn hình print setting. Nguồn file: 伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 504
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 操作员要按Item直接批量发行标签。
- Cách hỏi: tình huống
- Hỏi: 从Item选择发行传票时怎样操作？
- Đáp: 从菜单选择複数枚発行，选择Item并输入数量后执行生成。系统会显示生成的传票张数和明细；确认Preview后执行打印。订单编号根据制作日期生成，并分配箱连续编号。来源文件：伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 505
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 既存Dラベルの情報を複製して新しい伝票を発行したい。
- Cách hỏi: trực tiếp
- Hỏi: Dラベル複製ではどのCodeを読み取りますか。
- Đáp: Menuからハンディターミナルを選択し、複製元現品票の39_3N3と3N4を順に読み取ります。読取情報とLabel出力情報が表示され、必要に応じて数量編集やLOT入力を行って生成・印刷します。出典ファイル：伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 506
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới cho rằng LOT bắt buộc phải nhập khi copy D-label.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Khi phát hành bằng cách copy D-label, chỉnh Qty và nhập LOT có bắt buộc không?
- Đáp: Không. Tài liệu ghi bước chỉnh quantity và nhập LOT là ※任意作業, tức thao tác tùy chọn nếu cần; sau đó mới chọn 生成. Nguồn file: 伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 507
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较三种传票发行入口。
- Cách hỏi: so sánh
- Hỏi: 资料中的传票发行方法主要有哪些？
- Đáp: 包括：①从已登记的Item Master选择并发行；②从D Label读取3N3/3N4信息后复制发行；③使用Dummy Barcode进行发行。具体使用哪种方式取决于现场是否已有可读取现品票和Master数据。来源文件：伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 508
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人がこのSystemはすべての仕入先に必須だと思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 全取引先が必ずこのSystemで伝票を発行する必要がありますか。
- Đáp: 資料はそのようには説明していません。主な対象理由は、入庫処理可能な伝票へ未切替の取引先、EDI未対応取引先、非ORICONからORICONへ詰替えるケースです。出典ファイル：伝票発行システムマニュアル_仮.pptx.

## CÂU HỎI 509
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần giải thích tổng thể luồng inspection report của linh kiện.
- Cách hỏi: trực tiếp
- Hỏi: Hệ thống liên kết chứng nhận kiểm tra linh kiện có những thành phần chính nào?
- Đáp: Sơ đồ thể hiện các thành phần như supplier, tạo 検査成績書, 検査成績書アップロードツール, cloud storage, RPA, 数据采集模块, 后台服务模块, 数据管理模块, quản lý X-R, chuyển dữ liệu về trụ sở và bộ phận 品管 tại các site. Nguồn file: 部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 510
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 供应商完成部品制造后，需要确认检验成绩书如何进入系统。
- Cách hỏi: tình huống
- Hỏi: 供应商侧生成检验成绩书后，资料中有哪些上传／联携方式？
- Đáp: 图中包含検査成績書アップロードツール、クラウドストレージ以及RPA等路径。供应商生成检验成绩书后，根据对象部品和据点通过这些机制进入后续数据管理／品质管理流程。来源文件：部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 511
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: AMS部品とIris2020部品の検査成績書経路を確認している。
- Cách hỏi: so sánh
- Hỏi: 資料では検査成績書をどのような対象区分で分けていますか。
- Đáp: Iris2020、AMS、上記以外の部品という区分が記載されています。また別の表記としてAMS、Iris2020をまとめた検査成績書経路も示されています。出典ファイル：部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 512
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn biết RPA làm gì trong luồng inspection report.
- Cách hỏi: trực tiếp
- Hỏi: Vai trò của RPA được ghi như thế nào?
- Đáp: Tài liệu ghi rõ RPAにより検査成績書を所定フォルダへ保存, tức RPA lưu inspection report vào folder được chỉ định. Nguồn file: 部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 513
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: KDTCN进行测量数据管理，工程师确认相关功能。
- Cách hỏi: tình huống
- Hỏi: KDTCN侧的图中显示了哪些测量／管理环节？
- Đáp: 图中标有パイプフレーム、測定治具、データ取得以及X-R管理，并连接到数据采集和后台／数据管理模块。来源文件：部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 514
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 部品品管が対象部品の範囲を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: この連携は全ての部品に同じ条件で適用されると断定できますか。
- Đáp: 断定できません。図には※3DA対応部品、※データトレサ対象部品という対象条件の注記があり、さらにAMS、Iris2020、その他部品で経路が区分されています。出典ファイル：部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 515
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang phân biệt luồng KDTVN/枚方 với KDTCN.
- Cách hỏi: so sánh
- Hỏi: Sơ đồ có thể hiện việc chuyển dữ liệu giữa các site không?
- Đáp: Có. Sơ đồ ghi 拠点転送 cho KDTVN/枚方 và 本社転送 ở phía KDTCN, cho thấy inspection report được chuyển giữa site/trụ sở trong luồng liên kết. Nguồn file: 部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 516
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 品管人员没有在预期Folder看到RPA保存的成绩书。
- Cách hỏi: xử lý sự cố
- Hỏi: 根据这张总览图，排查时至少应确认哪些节点？
- Đáp: 可沿着检验成绩书生成 → Upload Tool／Cloud Storage → RPA → 指定Folder → 数据采集／管理模块 → 品管逐段确认。图只给出总体联携结构，没有提供具体Log、Folder路径或重试操作，因此这些细节不能从该文件推断。来源文件：部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 517
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 石龍部品品管の処理を他拠点と比較している。
- Cách hỏi: tình huống
- Hỏi: 石龍部品品管について資料にはどのような記載がありますか。
- Đáp: 石龍部品品管の独自システムという独自Systemが図中に記載されています。ただし、この資料にはそのSystem内部仕様までは説明されていません。出典ファイル：部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 518
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者がこの1枚だけでInterface仕様を確定しようとしている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: この資料だけで各System間のAPI、File Format、通信周期まで確定できますか。
- Đáp: できません。この資料は全体概要であり、System・拠点・Upload Tool・RPA・Cloud Storage・データ管理などの関係を示すものです。API仕様、File Format、通信周期などの詳細は記載されていないため未確認です。出典ファイル：部品検査成績書システム連携の全体概要 2.pptx.

## CÂU HỎI 519
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận tài liệu giao tiếp AGV đang dùng.
- Cách hỏi: trực tiếp
- Hỏi: AGV通信仕様.xlsx hiện ghi version nào?
- Đáp: Trang đầu ghi AGV通信仕様 version 0.64. Tài liệu do 生産技術14課／技術推進21課 tạo. Nguồn file: AGV通信仕様.xlsx.

## CÂU HỎI 520
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认v0.64中新增加的动作Sequence。
- Cách hỏi: tình huống
- Hỏi: Version 0.64增加了哪两个Task Sequence？
- Đáp: v0.64在AGV_ACR・CTU間通信_動作シーケンス中增加了Task 151 QR照合_オリコン待機和Task 153 アームHP復帰。来源文件：AGV通信仕様.xlsx.

## CÂU HỎI 521
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so thay đổi của version 0.63 và 0.64.
- Cách hỏi: so sánh
- Hỏi: v0.63 và v0.64 thay đổi trọng tâm khác nhau thế nào?
- Đáp: v0.63 thêm User ID 0x0009 cho C3A_UDWR_UDRQ và thay đổi số data của chức năng lấy Option Error Code. v0.64 bổ sung sequence Task 151/153, cập nhật data item của Data ID 0x0009 và có thay đổi ở phần C3A_UC command. Nguồn file: AGV通信仕様.xlsx.

## CÂU HỎI 522
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: Jetson通信异常，需要确认状态取得Command。
- Cách hỏi: xử lý sự cố
- Hỏi: Jetson状态和Error Code使用哪个Command取得？
- Đáp: 使用0x0360 Jetson ステイタス取得。参数Mode=0时取得Status，Mode=1时取得Error Code。应答Status定义为0: IDLE、1: Busy、-1: ERROR，或者返回Error Code编号。来源文件：AGV通信仕様.xlsx.

## CÂU HỎI 523
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần đọc software version của Jetson.
- Cách hỏi: trực tiếp
- Hỏi: Command đọc và lấy version Jetson là gì?
- Đáp: 0x0362 là Jetson ソフトバージョン読み取り, dùng để yêu cầu đọc version và response là OK / ERROR. 0x0363 là Jetson ソフトバージョン取得, response chứa software version với độ dài 16. Nguồn file: AGV通信仕様.xlsx.

## CÂU HỎI 524
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Jetson两种Image Process指示。
- Cách hỏi: so sánh
- Hỏi: 0x0367和0x0368的输入数据有什么区别？
- Đáp: 0x0367 Jetson イメージプロセス指示的数据数为1，发送動作モード；0x0368 Jetson イメージプロセス2指示的数据数为29，发送動作モード、オリコンID。两者应答均为OK / ERROR。来源文件：AGV通信仕様.xlsx.

## CÂU HỎI 525
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Jetson image processing trả lỗi và kỹ sư cần kiểm tra trạng thái sau khi gửi command.
- Cách hỏi: xử lý sự cố
- Hỏi: Sau khi gửi Image Process command, dùng command nào để xác nhận trạng thái?
- Đáp: Dùng 0x0369 Jetson イメージプロセスステイタス取得, có 1 tham số 動作モード. Response trả trạng thái 0: IDLE, 1: Busy, -1: ERROR hoặc Error Code. Nguồn file: AGV通信仕様.xlsx.

## CÂU HỎI 526
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人把Jetson关机Command和Status取得Command混在一起。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 0x0366的应答也是IDLE／Busy／ERROR吗？
- Đáp: 不是。0x0366是Jetson システムシャットダウン，应答为OK。IDLE／Busy／ERROR属于0x0360以及Image Process Status取得等状态应答。来源文件：AGV通信仕様.xlsx.

## CÂU HỎI 527
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师回顾AGV通信规格早期Revision，确认路线Command如何扩展。
- Cách hỏi: trực tiếp
- Hỏi: v0.22增加了哪些典型路线设定Command？
- Đáp: v0.22增加了待機（START-SW押下待ち）、待機（外部通信待ち）、メロディOFF/ON、JUMP、マーク無視、リフト移動、電動ピン上昇/下降以及ORICON ID照合等项目，同时扩展了AGV-ACR/CTU通信中的电动Pin和ORICON ID照合相关Command。来源文件：AGV通信仕様.xlsx.

## CÂU HỎI 528
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 古い通信仕様を使って現行AGVを設定しようとしている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 初版0.1の内容だけを使って現在のAGV通信を設定してよいですか。
- Đáp: いいえ。現行Fileはv0.64で、0.1以降に待機Command、Sensor距離設定、Touch Panel、ORICON照合、Jetson、ACR/CTU Sequenceなど多数の追加・変更があります。実機設定では現行Revisionを基準にする必要があります。出典ファイル：AGV通信仕様.xlsx.

---
Ghi chú dedup: AGV通信仕様.xlsx (v0.64) có thể trùng nội dung lớn với AGV通信仕様_260206.xlsx (mẻ 8, v0.64) — cần dedup kỹ khi import.
