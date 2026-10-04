# Mẻ MOM 02 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Tài liệu: (6) MOMデータ連携説明_20251220.pdf, (7) MES_MOM説明資料_20251031.pdf, (8) ST CO.png, (9) 拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf, (10) Hướng dẫn tạo kế hoạch công đoạn APS.pptx
Phân bố: vi 18, zh 17, ja 15. Đủ 5 cách hỏi.

## CÂU HỎI 51
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư MOM đang giải thích cho người mới vì sao hệ thống phải quản lý cả dữ liệu sản xuất và tồn kho.
- Cách hỏi: trực tiếp
- Hỏi: MES trên line có những nhiệm vụ chính nào liên quan trực tiếp đến sản xuất?
- Đáp: MES hiển thị chỉ thị công việc tại terminal hiện trường và ghi nhận bắt đầu/hoàn thành; ghi chính xác vật liệu投入・消費 rồi đối chiếu tồn kho; ghi lỗi và kết quả kiểm tra để có thể dừng công đoạn sau hoặc kích hoạt xử lý; thu thập dữ liệu vận hành thiết bị để tính nguyên nhân dừng và tỷ lệ sử dụng; đồng thời lưu lịch sử sản xuất của từng sản phẩm như ai làm, khi nào, bằng thiết bị nào và dùng linh kiện nào. Nguồn file: MOMデータ連携説明_20251220.pdf.

## CÂU HỎI 52
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra trường hợp linh kiện đã qua cổng xuất nhưng chưa thấy tồn kho công đoạn trên Opcenter.
- Cách hỏi: xử lý sự cố
- Hỏi: Theo luồng dữ liệu, sau khi linh kiện qua cổng xuất thì Opcenter phải xử lý gì?
- Đáp: Theo sơ đồ liên kết nhập/xuất, khi qua cổng xuất có liên kết PAC, Opcenter tự động thực hiện 出庫トランザクション, sau đó đăng ký linh kiện xuất kho thành 工程在庫, tức tồn kho công đoạn có thể tiêu thụ. Nếu đã xác nhận qua cổng nhưng chưa có工程在庫 thì cần kiểm tra chuỗi PAC liên kết → transaction xuất kho → đăng ký工程在庫; tài liệu này không đưa mã lỗi cụ thể nên nguyên nhân chi tiết chưa thể kết luận chỉ từ file này. Nguồn file: MOMデータ連携説明_20251220.pdf.

## CÂU HỎI 53
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên QLSX đang đối chiếu vì sao thời điểm xuất kho phải được tính từ kế hoạch sản xuất.
- Cách hỏi: tình huống
- Hỏi: APS xác định kế hoạch xuất linh kiện dựa trên các bước nào trước khi chọn box xuất?
- Đáp: Tài liệu mô tả chuỗi: ① tạo kế hoạch công đoạn, ② tạo kế hoạch tiêu thụ, ③ phân bổ tồn kho kho, từ đó xác định thời điểm bắt đầu sản xuất, thời điểm tiêu thụ linh kiện và box cần xuất; ④ tạo kế hoạch xuất kho. Thời gian vận chuyển được dùng để tính ngược thời điểm phải qua cổng xuất để linh kiện tới điểm cấp đúng lúc. Nguồn file: MOMデータ連携説明_20251220.pdf.

## CÂU HỎI 54
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới kiểm tra dữ liệu nhập kho trong bảng giao tiếp.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Trong T_PARTS_RECIEVE, cứ RECEIVE_TYPE = 1 là nhập kho thông thường đúng không?
- Đáp: Không. Trong layout bảng T_PARTS_RECIEVE, RECEIVE_TYPE là varchar dài 1 ký tự; giá trị rỗng '' là nhập kho thông thường, còn '1' là マニュアル入庫, tức nhập kho thủ công và không thuộc đối tượng kiểm thu. Bảng này còn có ORICON_ID, ITEM_CODE, ITEM_REV, INNER_QTY và các trường PO/EDI khác. Nguồn file: MOMデータ連携説明_20251220.pdf.

## CÂU HỎI 55
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: MOM工程师正在向仓库人员解释入库和出库在Opcenter中的处理差异。
- Cách hỏi: so sánh
- Hỏi: 入库和出库通过Gate后，在Opcenter中的处理有什么区别？
- Đáp: 入库Gate通过后，资料描述为通过PAC联携自动执行入库Transaction，然后登记为仓库库存；出库Gate通过后，则自动执行出库Transaction，并把出库部品登记为可消费的工程库存。两者都是Gate/PAC与Opcenter联携，但最终库存位置的业务含义不同。来源文件：MOMデータ連携説明_20251220.pdf。

## CÂU HỎI 56
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 生产技术人员发现ORICON入库记录中的品目数据为空。
- Cách hỏi: xử lý sự cố
- Hỏi: T_PARTS_RECIEVE 中的 ITEM_CODE 为空，就一定是数据异常吗？
- Đáp: 不能直接判断为异常。资料对 ITEM_CODE 注明其来源为供应商现品票信息，并说明"EDIのみは空白"，即仅有EDI信息的情况可以为空。ITEM_REV、INNER_QTY 等字段也有类似的供应商现品票来源说明。因此应先确认该入库是否属于EDI-only场景。来源文件：MOMデータ連携説明_20251220.pdf。

## CÂU HỎI 57
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人正在确认MOM系统与WMS、APS、PLC之间的关系。
- Cách hỏi: trực tiếp
- Hỏi: MOM系统概要中，APS、WMS和PLC分别与MOM做什么联携？
- Đáp: 资料中APS负责详细Scheduling，并与MOM联携工程计划；WMS负责仓库棚番和入库顺序指定等仓库业务；生产线侧通过PLC/中间DB以及Process Automation Control（PAC）与MOM进行数据联携。MOM中还包括ERP联携、工程／品目定义、实绩登记・输出・参照等功能。来源文件：MOMデータ連携説明_20251220.pdf。

## CÂU HỎI 58
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 現場担当者が「トランザクション」の意味を確認している。
- Cách hỏi: trực tiếp
- Hỏi: MOM資料でいうトランザクションとは何ですか。
- Đáp: トランザクションは、ITシステムで行われる一連の処理を「ひとまとまりの仕事の単位」として扱う考え方です。資料では、複数の処理をまとめて成功させるか、まとめて失敗させる単位として説明しています。途中の一部だけ成功した状態を避けるための考え方です。出典ファイル：MOMデータ連携説明_20251220.pdf。

## CÂU HỎI 59
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 出庫計画と搬送時間の関係をライン担当者が確認している。
- Cách hỏi: tình huống
- Hỏi: 部品の消費時刻だけを見て、その時刻に出庫ゲートを通せばよいですか。
- Đáp: いいえ。資料では、出庫先までの搬送時間を考慮し、必要な到着時刻から出庫ゲート通過時刻を算出します。APS側で工程計画、消費計画、倉庫在庫割当、出庫対象箱を決め、搬送時間に間に合うよう出庫計画を作成する流れです。出典ファイル：MOMデータ連携説明_20251220.pdf。

## CÂU HỎI 60
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者が新人にMESとMOMの理解を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: MESとMOMはまったく同じ範囲を管理するシステムですか。
- Đáp: いいえ。資料では、MESは主に現場での実行、作業指示、実績記録、進捗、設備稼働などに特化します。一方、MOMは製造スケジュール、品質、在庫、パフォーマンス分析、トレーサビリティなどを含む「製造全体の統括」を担う位置付けです。出典ファイル：MOMデータ連携説明_20251220.pdf。

## CÂU HỎI 61
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新入职工程师需要理解ERP、MES和PLC在工厂中的层次关系。
- Cách hỏi: so sánh
- Hỏi: ERP、MES和PLC分别属于哪一层？
- Đáp: 资料把制造业信息管理分为三个层次：计划层、执行层、控制层。ERP是计划层的代表，负责生产计划、需求、库存等企业资源管理；MES位于执行层，把计划转换为现场可执行的制造指示并管理实绩；PLC和IoT Sensor等属于控制层，直接控制设备并把现场数据传递给MES。来源文件：MES_MOM説明資料_20251031.pdf。

## CÂU HỎI 62
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 生产管理人员想确认ERP是否负责现场每一道作业的详细执行。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: ERP已经有生产计划，所以现场的作业开始、完成和追溯全部由ERP直接管理，对吗？
- Đáp: 不对。资料中ERP主要位于计划层，负责企业资源、生产计划、采购、库存等广泛业务；MES位于执行层，接收ERP计划后负责各工程制造指示、小日程计划、生産実績、品质和Traceability等现场执行管理。来源文件：MES_MOM説明資料_20251031.pdf。

## CÂU HỎI 63
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: Line发生品质异常，工程师需要判断MES能够提供什么支持。
- Cách hỏi: tình huống
- Hỏi: 现场发现不良时，MES除了记录NG数量还能做什么？
- Đáp: 资料说明MES可记录不良和检查结果，并能够立即停止后工程或启动纠正措施；同时保存制造履历，例如谁在何时、使用什么设备和部品进行生产。这些数据可用于追溯和品质问题分析。来源文件：MES_MOM説明資料_20251031.pdf。

## CÂU HỎI 64
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 管理者正在确认KDC所采用的MES软件。
- Cách hỏi: trực tiếp
- Hỏi: KDC导入的MES Package是什么？
- Đáp: 资料明确写明，KDC此次导入的是Siemens的OPCENTER Execution CORE Package Software。来源文件：MES_MOM説明資料_20251031.pdf。

## CÂU HỎI 65
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: ラインで設備データは取れているが、生産実績側に反映されない問題を切り分けている。
- Cách hỏi: xử lý sự cố
- Hỏi: 制御層とMESの間では、どのようなデータの流れを確認すべきですか。
- Đáp: 資料では、PLCなどの制御装置がMESからの指示を設備へ伝え、逆に設備やセンサーから収集したデータをMESへ渡す役割を持ちます。したがって、設備側だけでなく、PLC／制御層からMES実行層へのデータ連携を確認する必要があります。具体的な通信エラーコードはこの資料には記載されていません。出典ファイル：MES_MOM説明資料_20251031.pdf。

## CÂU HỎI 66
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人がMOMとMESの範囲を比較している。
- Cách hỏi: so sánh
- Hỏi: MOMとMESの役割はどう違いますか。
- Đáp: MESは現場レベルの作業指示、実行記録、進捗確認、設備稼働監視など「現場での実行」に重点があります。MOMはそれより広く、生産計画、作業指示、実行、品質管理、最適化までを一貫して管理する「製造オペレーション全体の統括」という位置付けです。出典ファイル：MES_MOM説明資料_20251031.pdf。

## CÂU HỎI 67
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 生産遅延の原因を分析するため、現場で収集すべき情報を確認している。
- Cách hỏi: trực tiếp
- Hỏi: MESでは設備についてどのような実績を収集しますか。
- Đáp: 資料では、機械の稼働データを収集し、停止原因や利用率を算出するとしています。また、製品ごとに、誰が・いつ・どの設備で・どの部品を使ったかという製造履歴も残します。出典ファイル：MES_MOM説明資料_20251031.pdf。

## CÂU HỎI 68
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư mới đang phân loại dữ liệu nào thuộc ERP và dữ liệu nào thuộc MES.
- Cách hỏi: trực tiếp
- Hỏi: ERP trong tài liệu quản lý những nghiệp vụ chính nào?
- Đáp: ERP liên kết các nghiệp vụ nền tảng như tài chính, mua hàng, tồn kho, sản xuất, bán hàng và nhân sự trên một nền tảng. Với sản xuất, tài liệu liệt kê các lĩnh vực như kế hoạch sản xuất, quản lý kho, mua hàng/nhập hàng, chất lượng, thông tin sản phẩm, tài chính/giá thành, nhân sự, supply chain/demand planning và bảo trì thiết bị. KDC đang dùng SAP R/3 và tài liệu ghi đang thực hiện dự án chuyển sang SAP S/4HANA. Nguồn file: MES_MOM説明資料_20251031.pdf.

## CÂU HỎI 69
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Quản lý muốn biết MES giúp ích gì khi line thường xuyên chậm tiến độ và khó truy nguyên lỗi.
- Cách hỏi: tình huống
- Hỏi: MES mang lại những lợi ích nào mà line có thể thấy trực tiếp?
- Đáp: Tài liệu chia lợi ích lớn thành 4 nhóm: nâng cao chất lượng sản phẩm bằng thu thập/phân tích dữ liệu chất lượng theo thời gian thực; giảm chi phí sản xuất bằng trực quan hóa loss và cải thiện quản lý giá thành; rút ngắn lead time bằng tối ưu lịch và sản xuất đúng thời điểm; tăng liên kết giữa các bộ phận nhờ chia sẻ dữ liệu, giúp điều tra lỗi và phối hợp nhanh hơn. Nguồn file: MES_MOM説明資料_20251031.pdf.

## CÂU HỎI 70
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang điều tra vì kế hoạch ERP đã có nhưng terminal hiện trường chưa có chỉ thị sản xuất.
- Cách hỏi: xử lý sự cố
- Hỏi: Theo mô hình 3 lớp, nên kiểm tra luồng nào khi ERP đã có kế hoạch nhưng hiện trường chưa nhận chỉ thị?
- Đáp: Cần kiểm tra luồng từ lớp kế hoạch ERP sang lớp thực thi MES, vì MES nhận kế hoạch từ ERP rồi chuyển thành chỉ thị sản xuất theo công đoạn hoặc kế hoạch chi tiết để gửi xuống hiện trường. Nếu MES đã có chỉ thị mà thiết bị vẫn không thực hiện thì tiếp tục kiểm tra lớp điều khiển PLC/thiết bị. File này mô tả kiến trúc chức năng, không cung cấp thủ tục kiểm tra interface cụ thể nên bước kỹ thuật chi tiết cần tài liệu liên kết khác. Nguồn file: MES_MOM説明資料_20251031.pdf.

## CÂU HỎI 71
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: APSで計画済みのシリアルをHTでST登録する直前。
- Cách hỏi: trực tiếp
- Hỏi: ST登録前に最初に確認すべき計画データは何ですか。
- Đáp: フローでは、APS／生産計画／MES SHINDOで計画を作成し、ScheduledProductionOrderInfo / APS Planまで連携した後、そのシリアルに計画データがあるかを確認します。計画データがある場合は、さらにOpcenter側にMfgOrderまたは有効なシステムデータがあるかを確認してからST登録へ進みます。出典ファイル：ST CO.png。

## CÂU HỎI 72
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: シリアルにはAPS計画があるが、Opcenter側のデータが不足している。
- Cách hỏi: xử lý sự cố
- Hỏi: MfgOrderやProcess_IDを特定できない状態でST登録を続けてもよいですか。
- Đáp: いいえ。フローではOpcenterにMfgOrderまたは有効なシステムデータが無く、MfgOrder／Process_IDを特定できない場合はSTOPとなり、STを登録しない流れです。必要データを確認・復旧してから先へ進む必要があります。出典ファイル：ST CO.png。

## CÂU HỎI 73
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: ST登録後に、生産履歴登録システムのProcess_IDが正しいか確認している。
- Cách hỏi: tình huống
- Hỏi: Backendが返したProcess_IDが現在のPhantomと一致しない場合はどうなりますか。
- Đáp: フローではNG扱いとなり、STが旧Process_IDまたは誤ったPhantomへ書き込まれた状態として扱われます。Process_IDが現在のPhantomと一致した場合のみST記録を進め、OpcenterのStart Containerへ進みます。出典ファイル：ST CO.png。

## CÂU HỎI 74
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 操作员已经完成ST，准备进行CO。
- Cách hỏi: trực tiếp
- Hỏi: ST正常登记后，到CO和下一工程的标准流程是什么？
- Đáp: 流程图显示：ST记录成功后，Opcenter执行Start Container；随后HT登记CO，生产履历登记系统接收CO；之后记录CO以及后续工程的ST/CO，Opcenter通过Move Container收集实绩。Container Move成功后，进入Mfg Order Complete。来源文件：ST CO.png。

## CÂU HỎI 75
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 最终工程结束后Container没有成功Move，现场正在判断是否可以Complete。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 最终工程已经做完，所以即使Container Move失败，也可以先把Mfg Order Complete，对吗？
- Đáp: 不对。流程明确把Container move 实绩 OK?作为Complete前的判断条件。失败时进入NG分支，显示"Container不能Move，实绩未完成"，需要根据错误类型处理；只有应对完成并确认实绩OK后，才进入Mfg Order Complete。来源文件：ST CO.png。

## CÂU HỎI 76
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: Container Move失败，工程师需要选择恢复方向。
- Cách hỏi: xử lý sự cố
- Hỏi: Container Move失败时，图中列出的恢复方法有哪些？
- Đáp: 图中列出4类处理方向：①最终工程执行Manual Move；②修正ST/CO或Process_ID后重新确认；③修正源数据后重新执行；④调查Opcenter的log／DB／route。处理后还必须再次判断实绩是否OK，未确认OK时不能Complete。来源文件：ST CO.png。

## CÂU HỎI 77
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较"没有APS计划"和"有计划但Opcenter数据不完整"两种情况。
- Cách hỏi: so sánh
- Hỏi: Serial没有计划数据，与有计划但Opcenter缺MfgOrder时，ST处理有什么不同？
- Đáp: 流程图中，Serial没有计划数据的分支直接流向HT读取barcode并登记ST；而当Serial有计划数据时，还必须检查Opcenter是否有MfgOrder或有效系统数据，以及Process_ID／Phantom是否确认正确。如果无法确定MfgOrder／Process_ID，则STOP且不登记ST。来源文件：ST CO.png。

## CÂU HỎI 78
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra điều kiện để hoàn tất Mfg Order sau công đoạn cuối.
- Cách hỏi: trực tiếp
- Hỏi: Sau khi Mfg Order Complete, dữ liệu hoàn thành được đẩy về MES qua đâu?
- Đáp: Theo sơ đồ, sau Mfg Order Complete, bảng T_IF_PROD_RESULT ghi dữ liệu liên kết MES. Sau đó hệ thống MES進度管理 nhận dữ liệu hoàn thành, chỉ thị được hoàn tất và có thể lập bước kế hoạch APS tiếp theo. Nguồn file: ST CO.png.

## CÂU HỎI 79
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Trên line phát hiện ST ghi nhầm Process_ID cũ.
- Cách hỏi: xử lý sự cố
- Hỏi: Nếu ST đã ghi vào Process_ID cũ thì có nên tiếp tục CO để không dừng line không?
- Đáp: Không nên tiếp tục như một luồng bình thường. Sơ đồ đánh dấu trường hợp Process_ID backend không khớp Phantom hiện tại là NG và nêu ST có thể vẫn bị ghi vào Process_ID cũ/Phantom sai. Ở nhánh xử lý lỗi, một phương án là sửa ST/CO hoặc Process_ID rồi xác nhận lại; chỉ khi thực tích được xác nhận OK mới được Complete. Nguồn file: ST CO.png.

## CÂU HỎI 80
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Quản lý kiểm tra xem kỹ sư có hiểu điểm chặn an toàn dữ liệu trước ST hay không.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Chỉ cần Serial có kế hoạch APS là có thể đăng ký ST ngay, đúng không?
- Đáp: Không. Khi Serial có dữ liệu kế hoạch, sơ đồ còn yêu cầu kiểm tra Opcenter có MfgOrder hoặc dữ liệu hệ thống hợp lệ hay không, sau đó kiểm tra Process_ID / Phantom đã xác nhận đúng chưa. Nếu không đủ dữ liệu để xác định MfgOrder/Process_ID hoặc Process_ID/Phantom chưa đúng thì phải STOP/recovery trước khi tiếp tục. Nguồn file: ST CO.png。

## CÂU HỎI 81
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên kho đang xác nhận vị trí lưu ORICON nặng tại p-Rack.
- Cách hỏi: trực tiếp
- Hỏi: ORICON từ 10 kg trở lên phải ưu tiên đặt ở tầng nào?
- Đáp: Quy tắc trong tài liệu quy định ORICON từ 10 kg trở lên đặt ở tầng 1; trong cách đánh mã棚番, trường hợp hàng nặng từ 10 kg trở lên thì Chiều cao ① = 01. Với hàng thông thường, ưu tiên giá trị chiều cao nhỏ nhất khác 01, tức xếp từ tầng thấp nhất không phải tầng 1. Nguồn file: 拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf.

## CÂU HỎI 82
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên kiểm chứng WMS thấy rack 01 chưa đầy nhưng hệ thống đề xuất rack 03.
- Cách hỏi: xử lý sự cố
- Hỏi: Theo rule, rack 01 chưa đầy mà chuyển sang rack 03 có đúng không?
- Đáp: Không đúng với nguyên tắc cơ bản được mô tả. Tài liệu yêu cầu xếp đầy rack phía trước; ưu tiên hàng rack số lẻ từ giá trị nhỏ nhất, bắt đầu rack 01, chỉ sau khi hoàn tất toàn bộ các tầng của rack 01 mới chuyển sang rack 03, rồi tiếp tục các rack lẻ khác. Sau khi nhóm lẻ đầy mới chuyển sang hàng chẵn. Nguồn file: 拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf.

## CÂU HỎI 83
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm chứng cách WMS phân bổ giữa các block A, B, C.
- Cách hỏi: tình huống
- Hỏi: Có A01, A02, B01, B02, C01 thì thứ tự phân bổ block được đề xuất thế nào?
- Đáp: Ví dụ trong tài liệu phân bổ theo vòng vùng A → B → C rồi mới sang số phụ tiếp theo: A01 → B01 → C01 → A02 → B02. Logic là chọn area nhỏ nhất, trong area chọn sub-number nhỏ nhất tiếp theo; sau C nếu không còn area tiếp theo thì quay lại A và chọn sub-number tiếp theo. Nguồn file: 拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf.

## CÂU HỎI 84
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới đọc mã棚番 C2A01010101 và cần hiểu từng phần.
- Cách hỏi: trực tiếp
- Hỏi: Các phần số trong mã棚番 được tài liệu định nghĩa như thế nào?
- Đáp: Ví dụ C2A01010101 được phân tách theo các thành phần: Chiều cao ①, Số cột giá ②, Số hàng giá ③, Số bổ trợ vùng ④, Số vùng ⑤, Số tầng ⑥, Số của tòa nhà ⑦. Khi kiểm tra rule đề xuất棚番 phải xét đúng các thành phần này, không chỉ nhìn toàn bộ chuỗi như một số duy nhất. Nguồn file: 拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf.

## CÂU HỎI 85
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 仓库工程师比较棚内的行、列和高度选择规则。
- Cách hỏi: so sánh
- Hỏi: 棚行、棚列和高度的优先规则分别是什么？
- Đáp: 资料规定：棚行③从最小奇数行开始，奇数行全部完成后再转偶数行；高度①原则上选除01以外的最小值，但10 kg以上ORICON使用高度01；棚列②选择最小值，也就是从左向右存放。来源文件：拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf。

## CÂU HỎI 86
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 跨日后棚番推荐控制重新开始，操作员担心顺序被破坏。
- Cách hỏi: tình huống
- Hỏi: 控制中断或跨日后，可以从最小棚番重新开始吗？
- Đáp: 可以。资料写明，在跨日或处理中断导致控制困难时，从步骤①的最小棚番重新开始也没有问题，并说明不要求过度严格控制。但如果过于频繁回到步骤①，就会接近没有控制的状态，因此不应频繁重置。来源文件：拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf。

## CÂU HỎI 87
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: WMS测试时系统持续推荐同一区域，工程师检查Area Group轮转逻辑。
- Cách hỏi: xử lý sự cố
- Hỏi: 如果上次已经推荐A01，下一次仍不断推荐A01，符合资料中的基本分散规则吗？
- Đáp: 一般不符合资料示例的分散思路。资料要求根据上次推荐的Block按升序选择下一个Group，例如从A01后选择下一Group，再按A、B、C循环；示例中也有 A01 → B01 → C01 → A02 → B02 的分配方式。除非发生跨日/处理中断后允许重新从最小棚番开始，否则不应持续固定在A01。来源文件：拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf。

## CÂU HỎI 88
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: WMS拠点検証で空棚の提案順を確認している。
- Cách hỏi: trực tiếp
- Hỏi: Area Group内の空棚は、どの順序で提案しますか。
- Đáp: 資料では、Area Group内の空棚提案は棚番の1～6桁を昇順に並べ、その中で最小の空棚を提案する考え方です。棚行は小さい奇数を優先し、奇数側完了後に偶数へ移り、棚列は小さい値から、つまり左から右へ格納します。出典ファイル：拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf。

## CÂU HỎI 89
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人が重量物と通常ORICONの高さルールを混同している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: すべてのORICONは高さ01から格納するルールですか。
- Đáp: いいえ。通常は高さ①について01以外の最小値を選び、1段目以外の低い段から格納します。例外として、10 kg以上の重量ORICONは高さ①=01、つまり1段目を使用します。出典ファイル：拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf。

## CÂU HỎI 90
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 拠点検証で棚番提案の順番と実際の格納位置を比較している。
- Cách hỏi: so sánh
- Hỏi: Rack 01とRack 03では、どちらを先に使用しますか。
- Đáp: Rack 01を先に使用します。資料では、前側のRackから満杯にし、棚行③の小さい奇数を優先するため、まず01を全段完了してから03へ移る例が示されています。その後も奇数側を優先し、奇数が埋まってから偶数側へ進みます。出典ファイル：拠点検証準備リスト_手順説明_WMS_棚番採番(VN-JP).pdf。

## CÂU HỎI 91
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: QLSX人员准备从生产顺序表开始制作APS工程计划。
- Cách hỏi: trực tiếp
- Hỏi: APS出库计划相关流程一共有几个步骤？
- Đáp: 资料列出7个步骤：①MES进度管理登记，②生产顺序表登记，③APS工作日历登记，④APS工程计划作成，⑤APS→MOM联携，⑥ORICON入库完成，⑦供给／出库计划作成。目前QLSX负责除第⑥步以外的步骤，第⑥步由仓库、KTCT等通知完成情况。来源文件：Hướng dẫn tạo kế hoạch công đoạn APS.pptx。

## CÂU HỎI 92
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新订单已经导入APS，工程师需要确认订单数据是否完整。
- Cách hỏi: tình huống
- Hỏi: 执行 IMPORT ORDER 后应立即做什么确认？
- Đáp: IMPORT ORDER 会自动导入新订单并删除APS中的旧订单。出现提示后按 Done，然后必须到Order中确认新订单是否已经出现、数量是否正确等，再进入 Generate Schedule 制作工程计划。来源文件：Hướng dẫn tạo kế hoạch công đoạn APS.pptx。

## CÂU HỎI 93
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: APS工程计划制作后时间不正确，需要重做。
- Cách hỏi: xử lý sự cố
- Hỏi: 当前资料中，如果APS工程计划做错了，应该怎么修改？
- Đáp: 资料写明目前只能从头重做。先在APS主画面的 Orders 选择目标订单，右键用 Deletes 删除；此时刚生成的工程Group也会被删除。然后再次执行 Import Order 恢复订单，并从资料指定的计划作成步骤重新执行。来源文件：Hướng dẫn tạo kế hoạch công đoạn APS.pptx。

## CÂU HỎI 94
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: APSで工程計画を作成したが、OpcenterへReleaseする前の確認をしている。
- Cách hỏi: trực tiếp
- Hỏi: 工程計画を作成する時の基本操作順は何ですか。
- Đáp: 資料では、必要なOrderを準備し、Peg materialsで部品をPegした後、Schedule Despite Shortage、Foward by Sequence、Foward by Due Dateの順で計画を作成します。通常は2回程度実行しないと計画が作成されない場合があると記載されています。作成後はOverviewとEditorで時間を確認してからSaveします。出典ファイル：Hướng dẫn tạo kế hoạch công đoạn APS.pptx。

## CÂU HỎI 95
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 計画担当者がAPSからOpcenterへのRelease結果を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: OpcenterでSchedule Statusを確認した時、どの値ならOKですか。
- Đáp: 資料では、Opcenter WebでQueryを実行し、Order数を確認した上で、schedule statusが2または空欄であればOKとしています。それ以外の場合はKDCへ連絡するよう指示されています。出典ファイル：Hướng dẫn tạo kế hoạch công đoạn APS.pptx。

## CÂU HỎI 96
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: QLSX担当者が出庫指示を急いでいるが、ORICON入庫完了連絡がまだ来ていない。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: APS工程計画が完成していれば、入庫完了連絡前でも出庫指示を出してよいですか。
- Đáp: いいえ。資料では、部品管理またはKTCTからORICON入庫完了の連絡を受けてから出庫指示を行うよう定めています。これは部品不足などのエラーを減らすためです。入庫完了確認後に供給計画作成ツールで出庫指示を実行します。出典ファイル：Hướng dẫn tạo kế hoạch công đoạn APS.pptx。

## CÂU HỎI 97
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên QLSX đang tạo calendar cho nhóm công đoạn trên APS.
- Cách hỏi: so sánh
- Hỏi: On Shift, Off Shift và Short Break khác nhau thế nào khi tạo lịch?
- Đáp: Khi tạo Primary Calendar Template, thời gian làm việc chọn On Shift, khi đó Efficiency và Cost Factor tự nhận 100%. Thời gian nghỉ chọn Off Shift; thời gian giải lao có thể chọn Short Break, và với thời gian nghỉ/giải lao Efficiency và Cost Factor tự nhận 0%. Cần chú ý Start Offset, Length và phải Save sau khi thiết lập. Nguồn file: Hướng dẫn tạo kế hoạch công đoạn APS.pptx.

## CÂU HỎI 98
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tạo lịch cho lệnh kéo dài sang ngày hôm sau.
- Cách hỏi: tình huống
- Hỏi: Nếu lệnh chạy quá 1 ngày thì chỉ set calendar cho ngày bắt đầu có đủ không?
- Đáp: Không. Tài liệu yêu cầu set lịch cả ngày liền sau nếu đơn hàng chạy quá một ngày. Với lịch thông thường, đặt Start Time từ 0:00 ngày hiện tại đến End Time 0:00 ngày hôm sau, sau đó áp dụng lịch cho các nhóm công đoạn và tiếp tục thiết lập tương tự cho ngày làm việc kế tiếp để bảo đảm kế hoạch. Nguồn file: Hướng dẫn tạo kế hoạch công đoạn APS.pptx.

## CÂU HỎI 99
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Sau khi bấm実行 tạo kế hoạch xuất kho, phần mềm hiện nhiều dòng WARN.
- Cách hỏi: xử lý sự cố
- Hỏi: Khi tool xuất kho báo WARN thiếu linh kiện thì xử lý thế nào?
- Đáp: Cần báo các dòng WARN cho bên QLLK và KTCT. Sau khi các bên xử lý nhập nốt linh kiện còn thiếu và thông báo nhập kho hoàn thành, phải thực hiện chỉ thị xuất kho lại. Nếu lỗi không phải thiếu linh kiện thì liên hệ KDC xử lý. Sau khi tạo xong cũng nên xác nhận với KTCT xem kế hoạch xuất kho đã link đúng lên thiết bị chưa; file text thực thi được lưu trong thư mục LOG của phần mềm. Nguồn file: Hướng dẫn tạo kế hoạch công đoạn APS.pptx.

## CÂU HỎI 100
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Quản lý kiểm tra bước cuối giữa APS và thiết bị sau khi kế hoạch đã Release.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Bấm Release Schedule trên APS là hoàn tất toàn bộ liên kết với thiết bị rồi đúng không?
- Đáp: Không. Sau Release Schedule, phải đăng nhập web Opcenter để kiểm tra kế hoạch đã phát hành đúng, bao gồm số lượng lệnh và schedule status. Khi kết quả OK mới quay lại APS và bấm Link Scheduler to Equipment để liên kết kế hoạch công đoạn với thiết bị. Đây mới là bước hoàn tất chuỗi tạo, phát hành, kiểm tra và link kế hoạch công đoạn. Nguồn file: Hướng dẫn tạo kế hoạch công đoạn APS.pptx.
