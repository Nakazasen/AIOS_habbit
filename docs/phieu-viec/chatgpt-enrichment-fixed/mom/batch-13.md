# Mẻ MOM 13 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Trạng thái: Bản thảo — chưa qua chuyên gia duyệt. Khối: MOM.
5 file trong 仕様書 (4 xlsx xuất kho line ngoài AMS + 通函管理システム.pptx), mỗi file 10 cặp, câu 539–588. Không file nào bị bỏ qua.

## CÂU HỎI 539
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần hiểu mục đích của chức năng tự động xuất kho từ AMS sang các line hiện hữu ngoài AMS.
- Cách hỏi: trực tiếp
- Hỏi: Component 既存ライン出庫連携自動処理 được thiết kế để làm gì?
- Đáp: Chức năng nhận thông tin chỉ thị xuất kho manual được đăng ký từ VN-MES qua 既存ライン出庫MOMStagingテーブル, tìm hàng có thể xuất trong kho tự động AMS theo FIFO, sau đó tự động thực hiện xử lý tương đương ライン外出庫処理 của manual shipping. ライン外出庫処理 là xử lý đã có từ Phase3 để đưa hàng tới 選別場所（Location：0106）. Nguồn file: KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 540
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: KDTVN bổ sung các line C21–C25 vào chức năng xuất kho ngoài AMS.
- Cách hỏi: tình huống
- Hỏi: Các line C31–C35 và C21–C25 sử dụng ERPLocation nào?
- Đáp: Tài liệu ghi 5 line hiện hữu C31/C32/C33/C34/C35, mỗi line 8 block, dùng ERPLocation 30C3. Nhóm bổ sung C21/C22/C23/C24/C25, cũng mỗi line 8 block, dùng ERPLocation 30C4. Nguồn file: KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 541
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang phân biệt chức năng chọn hàng với chức năng thực hiện giao dịch xuất.
- Cách hỏi: so sánh
- Hỏi: Bước AMS自動倉庫品引き当て処理 và 既存ライン出庫連携自動処理 khác nhau thế nào?
- Đáp: AMS自動倉庫品引き当て処理 dùng thông tin chỉ thị để tìm và reserve hàng có thể xuất trong AMS theo FIFO; quy tắc là một chỉ thị xuất sẽ chọn một thùng theo FIFO. Sau đó 既存ライン出庫連携自動処理 thực hiện tự động xử lý line-out shipping tới line hiện hữu được chỉ định. Nguồn file: KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 542
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: VN-MES đã ghi một record mới nhưng MOM không chạy tự động.
- Cách hỏi: xử lý sự cố
- Hỏi: Điều kiện trigger đầu tiên của chức năng này là gì và cần kiểm tra input nào?
- Đáp: Trigger là thời điểm một record được đăng ký vào 既存ライン出庫MOMStagingテーブル. Các input từ VN-MES được tài liệu yêu cầu gồm 品目, 供給ライン, 供給工程 và 作成日時; cả bốn được ghi là bắt buộc, nhưng nếu thời gian tạo bị bỏ qua thì table default đặt system time. Nguồn file: KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 543
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查自动出库处理内部Task是否按设计执行。
- Cách hỏi: trực tiếp
- Hỏi: Component设计中的5个主要Task是什么？
- Đáp: 5个Task为：①从既存Line出库MOM Staging Table取得自动联携出库指示；②根据取得信息，从AMS自动仓库按FIFO搜索并分配出库品；③把处理条件／结果更新到Staging Table；④执行CompoundTxn kdcRenameShipChangeQty；⑤根据执行结果向T_PARTS_OUT登记1条Record。来源文件：KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 544
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在确认CompoundTxn内部处理顺序。
- Cách hỏi: tình huống
- Hỏi: kdcRenameShipChangeQty连续执行哪些处理？
- Đáp: 设计书明确写明CompoundTxn kdcRenameShipChangeQty连续执行Ship → ChangeQty → ContainerRename。之后再根据执行结果向T_PARTS_OUT登记1条Record。来源文件：KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 545
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为Phase3的选别Location 0106可以直接代表所有既存Line。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 新功能可以只使用Phase3既有的OutLine_Resource / Location 0106而不新增Line Master吗？
- Đáp: 不可以。资料说明，因为出库目的地是多个既存Line，需要另外建立各Line对应的Master来保存出库先信息。未来增加既存Line时，也需要追加相应Master。来源文件：KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 546
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: FIFO引き当て方式を確認している。
- Cách hỏi: so sánh
- Hỏi: 一つの出庫指示で複数箱をまとめて引き当てる方式ですか。
- Đáp: いいえ。設計書ではひとつの出庫指示に対してFIFOの観点に則りひと箱を引き当てて出庫する方式と明記されています。出典ファイル：KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 547
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 既存Line用Masterを追加する際にResource名称を確認している。
- Cách hỏi: trực tiếp
- Hỏi: 既存Line出庫用ResourceのNaming Ruleは何ですか。
- Đáp: ExistingLine_Resource_XXX形式で、XXXにはLine情報を入れます。資料例はC31やC21です。ERPLocationもLineに応じてMasterへ設定する必要があります。出典ファイル：KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 548
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: MOM側の処理周期をTimer Batchだと思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: この自動出庫処理は一定時間ごとのBatch実行ですか。
- Đáp: 設計書ではそうではありません。既存ライン出庫MOMStagingテーブルにデータレコードが登録される都度実行する構成です。出典ファイル：KDC_P3MOM_MCO-309_コンポーネント設計.xlsx.

## CÂU HỎI 549
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 接口工程师正在确认该设计书的范围。
- Cách hỏi: trực tiếp
- Hỏi: KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx主要说明什么？
- Đáp: 该文档说明项目中构建的Custom Interface功能，OOB功能不在范围内。主要Sheet包括ConnectionMecanisum、ErrorHandling、INSERT_ManualShip_Auto、kdcRenameShipChangeQty、Master等。来源文件：KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 550
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: SQL Trigger执行失败，需要确认错误记录位置。
- Cách hỏi: xử lý sự cố
- Hỏi: Database Inbound的Trigger错误如何检测？
- Đáp: 资料规定使用SQL Trigger的TRY-CATCH，发生错误时向EventViewer输出Error。来源文件：KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 551
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: Staging数据已经送到Opcenter，但登记处理失败。
- Cách hỏi: tình huống
- Hỏi: Opcenter登记发生错误时，Staging Table如何表示失败？
- Đáp: 当Inbound Database Adapter向Opcenter登记Data发生错误时，会把Error Message写入Staging Table的错误信息Column，并把Status设为-1，表示因执行结果Error而失败。来源文件：KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 552
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较SQL Trigger错误与Opcenter登记错误。
- Cách hỏi: so sánh
- Hỏi: 两种错误的确认位置有什么区别？
- Đáp: SQL Trigger本身的更新Error通过TRY-CATCH输出到EventViewer；而Inbound Adapter向Opcenter登记后发生的Error，则写入Staging Table的Error Message字段，并把Status更新为-1。来源文件：KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 553
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: VN-MES chuẩn bị đăng ký một chỉ thị xuất kho mới vào staging.
- Cách hỏi: trực tiếp
- Hỏi: Các trường business bắt buộc VN-MES phải truyền vào ManualShipping_ExistingLineAuto_InboundDownload là gì?
- Đáp: Các trường được đánh dấu bắt buộc gồm Item_Code – 品目, Sup_Line – 供給ライン, Process_Id – 供給工程 và CreatedTxnDate – 作成日時. Nguồn file: KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 554
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy TransactionType trống trong dữ liệu gửi từ VN-MES.
- Cách hỏi: tình huống
- Hỏi: VN-MES có phải tự truyền TransactionType không?
- Đáp: Theo thiết kế, TransactionType được phía Opcenter cập nhật bằng giá trị cố định ManualShipping_ExistingLineAuto. Nó không được mô tả là trường business bắt buộc do VN-MES nhập. Nguồn file: KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 555
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Chỉ thị được ghi vào staging nhưng không thể xử lý xuất kho.
- Cách hỏi: xử lý sự cố
- Hỏi: Ngoài việc record tồn tại trong staging, điều kiện master nào phải được thỏa mãn?
- Đáp: Các master liên quan đến Item và đặc biệt dữ liệu Workflow関連 của đối tượng xuất kho phải được đăng ký trước. Tài liệu ghi việc insert vào table tự nó không bị giới hạn, nhưng đây là điều kiện tiên quyết để xử lý hoạt động bình thường. Nguồn file: KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 556
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: ProcessInventoryControlから一時TableへのTrigger条件を確認している。
- Cách hỏi: trực tiếp
- Hỏi: Temporary_ProcessInventoryControlへの登録条件は何ですか。
- Đáp: ProcessInventoryControlにSTATUS = 03かつ数量Check値がNULLのRecordが登録／更新された時です。対象DataをTemporary_ProcessInventoryControlへ登録し、ProcStatus = 0を設定します。出典ファイル：KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 557
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Staging TableへXMLを誰が作るか確認している。
- Cách hỏi: so sánh
- Hỏi: XMLDocumentはVN-MESが直接生成して登録しますか。
- Đáp: いいえ。設計書ではOpcenter側がStaging Tableへ登録された出庫指示情報を基にXMLを生成します。形式はkdcRenameShipChangeQtyシートのSourceMAP形式を使用します。出典ファイル：KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 558
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: VN-MESからStagingにRecordを入れればMaster無しでも処理できると思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Staging Tableへの登録自体が成功すれば自動出庫も必ず成功しますか。
- Đáp: いいえ。Tableへの登録自体には制限がありませんが、対象品目に紐づくWorkflow等のMasterが事前登録済みであることが正常動作の前提条件です。出典ファイル：KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx.

## CÂU HỎI 559
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Staging TableのStatusを監視して自動出庫の進捗を確認している。
- Cách hỏi: trực tiếp
- Hỏi: TransactionStatusの0、1、2、3は何を意味しますか。
- Đáp: 0＝処理中（処理実行待ち）、1＝処理中（出庫指示Data取込）、2＝処理中（自動出庫処理実行）、3＝正常終了です。出典ファイル：ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 560
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 自動出庫がError終了したRecordを分類している。
- Cách hỏi: so sánh
- Hỏi: TransactionStatus = -1と-9はどう違いますか。
- Đáp: -1は実行結果Errorによる異常終了、-9はMaster値不正または出庫可能在庫が存在しない場合の異常終了です。出典ファイル：ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 561
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: VN-MESがC31向け出庫指示を作成している。
- Cách hỏi: tình huống
- Hỏi: サンプルではC31向けにどのようなDataを登録していますか。
- Đáp: サンプルではItem 3A2V900860、Rev 01、供給Line C31、供給工程１ブロック、作成日時2023/10/30 12:34:56が示されています。出典ファイル：ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 562
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 処理後にC31とC32のStaging Recordを比較している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 正常処理後もOricon_Idは空欄のままですか。
- Đáp: いいえ。実行後のサンプルではC31側にOricon001、C32側にOricon002が入り、TransactionStatus = 3になっています。出典ファイル：ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 563
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang thiết kế monitor cho staging table.
- Cách hỏi: trực tiếp
- Hỏi: Những timestamp nào có thể dùng để theo dõi quá trình xử lý?
- Đáp: Table có CreatedTxnDate, StartedTxnDate, BrokerTxnDate, MOMProductTxnDate, CompletedTxnDate và RetryTxnDate. Ngoài ra còn có RetryCount, ResponseMsg và ErrorMsg để hỗ trợ điều tra. Nguồn file: ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 564
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Một record mới vừa được VN-MES ghi vào staging.
- Cách hỏi: tình huống
- Hỏi: TransactionStatus ban đầu được đặt bao nhiêu?
- Đáp: Khi tạo record, TransactionStatus được tự động đặt default là 0, nghĩa là 処理中（処理実行待ち）. Nguồn file: ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 565
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so dữ liệu do VN-MES nhập với dữ liệu được Opcenter bổ sung sau khi allocation.
- Cách hỏi: so sánh
- Hỏi: Oricon_Id, ContainerName, BoxSequenceNo và Qty do hệ thống nào cập nhật?
- Đáp: Các trường này được phía Opcenter cập nhật khi thực hiện auto shipping và đã xác định Container được allocation cho chỉ thị. Oricon_Id lưu ORICON ID, ContainerName lưu tên Container, BoxSequenceNo dùng làm ContainerName cho rename, và Qty lưu quantity của Container được chọn. Nguồn file: ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 566
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认供给Line字段长度。
- Cách hỏi: trực tiếp
- Hỏi: Sup_Line和Process_Id的数据类型及长度是多少？
- Đáp: Sup_Line为NVarChar(4)，Process_Id为NVarChar(20)。该版本示例中Sup_Line包含C31～C35，Process_Id示例为１ブロック～4ブロック。来源文件：ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 567
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 自动处理失败，需要判断是普通执行错误还是Master／库存错误。
- Cách hỏi: xử lý sự cố
- Hỏi: 应优先看哪个字段区分-1和-9？
- Đáp: 先查看TransactionStatus。-1表示执行结果Error，-9表示Master值不正确或不存在可出库库存；再结合ErrorMsg、ResponseMsg、RetryCount等字段调查详细原因。来源文件：ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 568
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为这个旧版Staging规格已经包含后续新增的C21～C25。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 这份20231107见直版明确列出了C21～C25吗？
- Đáp: 没有。在本文件已读取的Sup_Line说明中，Vietnam想定值列出的是C31、C32、C33、C34、C35。后续增加C21～C25的内容出现在更新后的Component／补充资料中，因此不能把它倒推成本文件当时已明确的规格。来源文件：ステージングテーブル_ライン外出庫連携自動処理用 (1).xlsx.

## CÂU HỎI 569
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang thiết kế master cho line C31.
- Cách hỏi: trực tiếp
- Hỏi: Tài liệu bổ sung yêu cầu master nào cho line C31?
- Đáp: Ví dụ C31 gồm ExistingLine_Resource_C31 với ERPLocation 30C3, ExistingLine_ResourceGroup_C31, ExistingLine_Operation_C31, ExistingLine_Spec_C31, ExistingLine_WorkFlow_C31 và ExistingLine_WorkFlowStep_C31. Workflow Path và Workflow Path Selector để không chỉ định. Nguồn file: 補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 570
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Có hai request cho cùng Item A lần lượt tới C31 và C32.
- Cách hỏi: tình huống
- Hỏi: Ví dụ FIFO trong tài liệu sẽ phân bổ ba Container aaa, bbb, ccc thế nào?
- Đáp: Ba Container Item A có ngày vào lần lượt aaa = 2023-10-01, bbb = 2023-10-02, ccc = 2023-10-03. Request ① tới C31 được allocation aaa; request ② tới C32 được allocation bbb. Đây là ví dụ cho nguyên tắc một request lấy một thùng theo FIFO. Nguồn file: 補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 571
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang so lựa chọn interface trực tiếp T_PARTS_OUT với staging.
- Cách hỏi: so sánh
- Hỏi: Phương thức liên kết từ hệ thống hiện hữu cuối cùng được quyết định thế nào?
- Đáp: Tài liệu từng nêu các phương án như dùng trực tiếp T_PARTS_OUT, staging table hoặc phương thức khác, nhưng sau đó ghi rõ ステージングテーブル経由で連携する方式として確定しました, tức đã quyết định liên kết qua staging table. Nguồn file: 補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 572
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Auto allocation trả về status -9 và line đang chờ linh kiện.
- Cách hỏi: xử lý sự cố
- Hỏi: Những nguyên nhân nào được tài liệu quy định làm xử lý dừng với lỗi -9?
- Đáp: Có hai nhóm chính: ① Master không đúng, ví dụ không tồn tại Item, Revision hoặc Location tương ứng; ② không có tồn kho có thể xuất. Khi xảy ra sẽ xuất Error Code -9 và dừng xử lý. Nguồn file: 補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 573
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: -9原因已经修复，工程师要重新执行。
- Cách hỏi: trực tiếp
- Hỏi: 错误解除后有哪两种方法可以让同一内容重新成为执行对象？
- Đáp: 可以①重新登记相同内容的出库指示Record，或者②把原Record的TransactionStatus更新回0，使其重新成为执行对象。来源文件：補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 574
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认C31～C35的ERP Location。
- Cách hỏi: tình huống
- Hỏi: C31～C35是否各自使用不同ERPLocation？
- Đáp: 不是。资料引用2023/11/2村上氏邮件内容，明确C31～C35に対応するERPLocationは、全て「30C3」で共通。来源文件：補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 575
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为FIFO要一次把所有旧库存全部分配给一个Request。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 一个出库Request会把所有最旧库存一次性全部分配吗？
- Đáp: 不会。资料明确的前提是一リクエストに対してひと箱をFIFOを考慮した状態で引き当てる。示例也是Request①取aaa、Request②再取bbb。来源文件：補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 576
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 既存Line向け出庫でT_PARTS_OUTのLocation設定方法を確認している。
- Cách hỏi: trực tiếp
- Hỏi: T_PARTS_OUTへのLocation設定はなぜ改修が必要ですか。
- Đáp: Phase3ではMasterから固有Keyで取得した値を固定設定する作りでしたが、既存Line出庫では指示された供給Lineに応じてLocationを動的に設定できるように変更する必要があるためです。出典ファイル：補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 577
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Workflow MasterとERPLocationの管理元を比較している。
- Cách hỏi: so sánh
- Hỏi: Workflow定義とERPLocationは同じSystemで決められますか。
- Đáp: 資料では既存Line一時置場用WorkflowはCN4T連携対象外でMES内完結できる認識です。一方、Location（ERPLocation）はSAP側管理のため、MOM側だけでは決定できないと記載されています。出典ファイル：補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 578
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Error解除後にRecordを何も変更せず待てば自動Retryされると思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: -9の原因を直せば、そのまま放置して自動的に再実行されますか。
- Đáp: 資料ではそのようには書かれていません。原因解消後、同じ内容の出庫指示Recordを再登録するか、TransactionStatusを0へ更新して再実行対象にする必要があります。出典ファイル：補足資料_要件内容反映版_20231110.xlsx.

## CÂU HỎI 579
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 物流人员需要了解通函管理System当前面向Supplier的基本方案。
- Cách hỏi: trực tiếp
- Hỏi: Supplier侧当前采用什么方式管理通函信息？
- Đáp: 资料写明，当时先采用サプライヤー用通函を一覧リスト生成 → メール配布的方式对应，并计划从4月起继续与Supplier讨论必要功能，同时研究未来与AMS联携后的Enhance功能。来源文件：通函管理システム.pptx.

## CÂU HỎI 580
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新通函投入使用，需要确认系统如何登记。
- Cách hỏi: tình huống
- Hỏi: 新通函和空箱在基本功能图中如何进入系统？
- Đáp: 基本功能图中有新規通函（空箱）及MySQL登録，并显示通函新规登记流程；箱体使用RFIDタグ／QRコード进行识别管理。来源文件：通函管理システム.pptx.

## CÂU HỎI 581
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 物流人员比较通函支给与部品入荷的记录方式。
- Cách hỏi: so sánh
- Hỏi: 通函支给和通函入荷是否都需要箱体识别信息？
- Đáp: 是。基本功能图把①通函支給和②通函入荷都放在通函管理流程中，并显示EPC読取、RFID/QR以及MySQL登记，用于记录空箱支给和部品入荷相关的通函流转。来源文件：通函管理システム.pptx.

## CÂU HỎI 582
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: Supplier反馈理论库存与现场数量不一致。
- Cách hỏi: xử lý sự cố
- Hỏi: Supplier收到每日邮件后发现异常，应如何处理？
- Đáp: 流程第4步是サプライヤー受信・確認，如果有异常则联系KDTCN。示例邮件也要求对差异进行确认，并在有不一致时联系相关担当。来源文件：通函管理システム.pptx.

## CÂU HỎI 583
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên logistics muốn biết báo cáo EPC hàng ngày gồm những nhóm tồn nào.
- Cách hỏi: trực tiếp
- Hỏi: Hệ thống tạo những loại EPC list nào?
- Đáp: Có 4 nhóm: ① hàng nhận trong ngày 当日入荷分; ② thùng cấp trong ngày 当日支給分; ③ tồn giữ tại supplier サプライヤー保管分; ④ tồn giữ tại KDTCN KDTCN保管分. Nguồn file: 通函管理システム.pptx.

## CÂU HỎI 584
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần giải thích chuỗi công việc từ quét thùng đến gửi báo cáo.
- Cách hỏi: tình huống
- Hỏi: Luồng リスト生成/メール配布 gồm những bước chính nào?
- Đáp: ① HT đọc thông tin và cập nhật record; ② hệ thống tạo các EPC list; ③ mỗi đêm tự động gửi email; ④ supplier nhận và xác nhận, nếu có bất thường thì liên hệ KDTCN. Nguồn file: 通函管理システム.pptx.

## CÂU HỎI 585
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên muốn biết ai nhận email EPC tự động.
- Cách hỏi: so sánh
- Hỏi: Phía KDTCN và phía supplier nhận email khác nhau thế nào?
- Đáp: Phía KDTCN gồm担当 logistics, 담당 purchasing, các thành viên liên quan project và người phát triển hệ thống. Phía ngoài là サプライヤー窓口, tức đầu mối supplier. Nguồn file: 通函管理システム.pptx.

## CÂU HỎI 586
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 日次Mailのサンプルから回転数を確認している。
- Cách hỏi: trực tiếp
- Hỏi: 2022/3/26のSample Mailでは当日の入荷と支給はいくつですか。
- Đáp: 入荷は10個（YAMATO→京瓷）、支給は20個（京瓷→YAMATO）です。出典ファイル：通函管理システム.pptx.

## CÂU HỎI 587
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 通函の理論在庫をSupplierと照合している。
- Cách hỏi: tình huống
- Hỏi: Sample Mailの理論在庫はいくつですか。
- Đáp: 京瓷側は1,010個、YAMATO側は1,020個です。出典ファイル：通函管理システム.pptx.

## CÂU HỎI 588
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人がこの資料ではすでにAMS完全自動連携まで実装済みだと思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: この資料時点でAMS連携による完全自動読取がすでに完成していたと判断できますか。
- Đáp: いいえ。資料には※AMS連携し、4月から自動読取の方向性を検討、また今後AMSと連携しエンハンス機能を展開検討と記載されています。当時の確定対応はEPC List生成とSupplierへのMail配布を中心とした内容です。出典ファイル：通函管理システム.pptx.
