# Mẻ MOM 10 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Trạng thái: Bản thảo — chưa qua chuyên gia duyệt. Khối: MOM.
2 file map CTU cuối trong 仕様書/マテハン + 3 file trong 仕様書/WMS, mỗi file 10 cặp, câu 429–478. Không file nào bị bỏ qua.

## CÂU HỎI 429
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang đối chiếu map CTU ngày 18/3 với các bản 16/3 và 17/3.
- Cách hỏi: trực tiếp
- Hỏi: Bản 18/3 thể hiện dải SUP_PROCESS nào trên layout?
- Đáp: Bản 18/3 ghi SUP_PROCESS = C3B_YB2200C300** và triển khai các số cuối từ 22 đến 33, tương ứng các nhóm K-1 đến K-12. Nguồn file: CTUマップ再検討20260318.xlsx.

## CÂU HỎI 430
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较3月18日版与前一天Map的布局注记。
- Cách hỏi: tình huống
- Hỏi: 3/18版中有什么明显的修改提示文字？
- Đáp: 当前版面中可直接看到ずらす以及減速用テープ追加两个修改提示。其中后者明确表示增加用于减速的Tape。来源文件：CTUマップ再検討20260318.xlsx.

## CÂU HỎI 431
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 3/17版から3/18版への変更点を確認している。
- Cách hỏi: so sánh
- Hỏi: 3/18版で確認できる変更点は何ですか。
- Đáp: 3/18版のLayoutにはずらすと減速用テープ追加という変更注記が明示されています。一方、前に確認した3/16・3/17版の抽出内容では、この2つの注記は確認されていません。したがって、少なくともLayout上では位置調整と減速用Tape追加が検討・反映対象になっています。出典ファイル：CTUマップ再検討20260318.xlsx.

## CÂU HỎI 432
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: CTU chạy sai tốc độ gần khu vực supply, kỹ sư đang kiểm tra bản 18/3.
- Cách hỏi: xử lý sự cố
- Hỏi: Nếu nghi ngờ điểm giảm tốc bị thiếu, chi tiết nào trong bản 18/3 cần kiểm tra trước?
- Đáp: Kiểm tra vị trí được chú thích 減速用テープ追加. Đây là dấu vết trực tiếp cho thấy bản 18/3 có bổ sung magnetic tape phục vụ giảm tốc. Cần đối chiếu vị trí tape thực tế với layout trước khi sửa Task. Nguồn file: CTUマップ再検討20260318.xlsx.

## CÂU HỎI 433
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为3/18版已经完全改写了所有Task。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 看到"减速用Tape追加"就能判断所有Address Task都被修改了吗？
- Đáp: 不能。文件中明确看到的是Layout上的減速用テープ追加和ずらす注记，而已读取的Map/Task表仍保留与3/16、3/17版大量相同的基本Sequence。因此不能把局部Layout修改解释成全部Task重写。来源文件：CTUマップ再検討20260318.xlsx.

## CÂU HỎI 434
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Address 2のTaskを旧版と照合している。
- Cách hỏi: trực tiếp
- Hỏi: 3/18版のAddress 2はどのTask Sequenceですか。
- Đáp: Address 2は0,151,147,98,79,153,15,65です。このSequenceは前に確認した3/16・3/17版と同じです。出典ファイル：CTUマップ再検討20260318.xlsx.

## CÂU HỎI 435
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai Address dùng pattern tốc độ khác nhau.
- Cách hỏi: so sánh
- Hỏi: Address 3 và Address 4 trong bản 18/3 khác nhau thế nào?
- Đáp: Address 3 = 72,77,142,15,65; Address 4 = 72,77,143,30,65. Khác biệt chính nằm ở Task 142/143 và giá trị 15/30. Nguồn file: CTUマップ再検討20260318.xlsx.

## CÂU HỎI 436
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: CTU在分支Course上异常，工程师确认Address变化规律。
- Cách hỏi: tình huống
- Hỏi: 3/18版不同Course的分支Address是否仍采用9→10、9→11、12→13等变化？
- Đáp: 是。已读取的多个Map表仍可看到9→10、9→11、12→13、13→14、14→15、15→16等Course差异，而后段31～53的共通Sequence基本保持一致。来源文件：CTUマップ再検討20260318.xlsx.

## CÂU HỎI 437
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Layout変更がSUP_PROCESS番号にも影響したか確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: 3/18版でSUP_PROCESS番号自体が22～33以外へ変更されたと確認できますか。
- Đáp: 確認できません。読み取れたLayoutでは22～33とK-1～K-12が表示されており、番号体系を別範囲へ変更した証拠はありません。出典ファイル：CTUマップ再検討20260318.xlsx.

## CÂU HỎI 438
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Quản lý muốn báo cáo chính xác thay đổi ngày 18/3.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Có thể báo cáo rằng ngày 18/3 đã thay đổi toàn bộ route CTU không?
- Đáp: Không. Có thể xác nhận [CHÍNH THỨC] bản 18/3 có chú thích ずらす và 減速用テープ追加; nhưng nhiều Task sequence vẫn giống bản trước. Vì vậy chỉ nên báo các thay đổi layout đã thấy, không khẳng định toàn bộ route đã thay đổi. Nguồn file: CTUマップ再検討20260318.xlsx.

## CÂU HỎI 439
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认3月30日版的供给地点范围。
- Cách hỏi: trực tiếp
- Hỏi: 3/30版Map包含哪些SUP_PROCESS编号和K区域？
- Đáp: SUP_PROCESS采用C3B_YB2200C300**格式，编号为22～33；顶部对应K-1到K-12。来源文件：CTUマップ再検討20260330.xlsx.

## CÂU HỎI 440
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 3/30版の速度制御記号を確認している。
- Cách hỏi: trực tiếp
- Hỏi: RFIDの停止・減速・加速・速度維持はどの記号ですか。
- Đáp: －＝RFID停止、↓＝RFID減速、↑＝RFID加速、→＝RFID速度維持です。出典ファイル：CTUマップ再検討20260330.xlsx.

## CÂU HỎI 441
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so bản 30/3 với bản sửa 6/4.
- Cách hỏi: so sánh
- Hỏi: Layout 30/3 và bản CTUマップ修正20260406 có những thành phần chung nào?
- Đáp: Cả hai đều thể hiện SUP_PROCESS C3B_YB2200C300**, nhóm K-1～K-12, ký hiệu RFID 停止/減速/加速/速度維持, magnetic tape, オリコン引き取り口, 空オリコン引き取り口 và 充電位置. Vì vậy cấu trúc layout chính giữa 30/3 và 6/4 rất gần nhau trong phần đọc được. Nguồn file: CTUマップ再検討20260330.xlsx.

## CÂU HỎI 442
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: CTU无法正确到达回收位置，工程师检查3/30版。
- Cách hỏi: xử lý sự cố
- Hỏi: 3/30版是否区分普通ORICON取货口和空ORICON取货口？
- Đáp: 是。布局中分别标有オリコン 引き取り口和空オリコン 引き取り口，另外还标出了充電位置。排查时不能把两个取货口当成同一位置。来源文件：CTUマップ再検討20260330.xlsx.

## CÂU HỎI 443
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: RFIDと磁気Tapeの制御を混同している新人へ説明している。
- Cách hỏi: so sánh
- Hỏi: 3/30版ではRFIDと磁気Tapeの速度制御を別に記載していますか。
- Đáp: はい。RFIDには停止・減速・加速・速度維持、磁気Tapeには停止・減速・加速が別々に記載されています。出典ファイル：CTUマップ再検討20260330.xlsx.

## CÂU HỎI 444
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: CTU giảm tốc không đúng gần điểm nối đường chạy.
- Cách hỏi: tình huống
- Hỏi: Bản 30/3 có đánh dấu điểm nối trên tuyến không?
- Đáp: Có. Layout có chú thích 継ぎ目, tức điểm nối/joint trên tuyến. Đây là một mốc cần đối chiếu khi điều tra vị trí tape hoặc thay đổi tốc độ gần đoạn nối. Nguồn file: CTUマップ再検討20260330.xlsx.

## CÂU HỎI 445
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为3/30版就是3/18版完全相同的复制。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 可以确认3/30版与3/18版完全相同吗？
- Đáp: 不能。3/18版的读取内容中明确出现ずらす和減速用テープ追加注记；3/30版当前Layout则显示完整的RFID／磁气Tape控制图例、取货口和充电位置。两者有大量共通结构，但不能称为完全相同。来源文件：CTUマップ再検討20260330.xlsx.

## CÂU HỎI 446
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 3/30版から4/6修正版への変更範囲を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: 3/30→4/6でTask全体が変更されたと判断できますか。
- Đáp: 現在読み取れたLayoutだけでは判断できません。主要なSUP_PROCESS、K区分、RFID／磁気Tape記号、取出口、充電位置は共通しています。正式な差分はCell単位比較が必要です。出典ファイル：CTUマップ再検討20260330.xlsx.

## CÂU HỎI 447
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần dùng các giá trị 3, 10, 15, 20, 30 trên layout.
- Cách hỏi: trực tiếp
- Hỏi: Có thể khẳng định đơn vị của các số 3/10/15/20/30 chỉ từ file map này không?
- Đáp: Không. Các số này xuất hiện tại nhiều điểm điều khiển tốc độ, nhưng file map không ghi rõ đơn vị trong phần nội dung đọc được. Muốn diễn giải chính xác phải đối chiếu AGVタスク一覧.xlsx hoặc AGV通信仕様_260206.xlsx. Nguồn file: CTUマップ再検討20260330.xlsx.

## CÂU HỎI 448
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 管理者要总结3/18、3/30、4/6三版Map的演变。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 可以把3/18的"减速Tape追加"直接解释成4/6最终规格吗？
- Đáp: 不能直接这样断定。3/18版明确有減速用テープ追加修改注记；3/30和4/6版都保留速度控制Layout。但没有一张Revision表明确说明该注记何时正式批准，因此只能确认版本间的可见变化，不能把推测当成最终规格。来源文件：CTUマップ再検討20260330.xlsx.

## CÂU HỎI 449
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: MOM/WMS検証を初めて実施する担当者が基本Scenarioを確認している。
- Cách hỏi: trực tiếp
- Hỏi: 基本シナリオではどこからどこまでを検証しますか。
- Đáp: イレギュラーの無いPatternとして、マスター設定 → 部品入庫 → 生産計画 → 部品出庫 → 生産完了まで一連で確認します。出典ファイル：手順書付シナリオ.xlsx.

## CÂU HỎI 450
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Line đã xuất linh kiện xong nhưng kế hoạch sản xuất được đổi sang ngày mai.
- Cách hỏi: tình huống
- Hỏi: Scenario 計画変更① kiểm chứng tình huống nào?
- Đáp: Sau khi hoàn thành xuất linh kiện theo basic scenario, kế hoạch sản xuất được đổi sang ngày hôm sau và ngày hiện tại giữ line stop. Đây là scenario No.2. Nguồn file: 手順書付シナリオ.xlsx.

## CÂU HỎI 451
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 生产已经开始后发生异常，需要比较两种计划变更场景。
- Cách hỏi: so sánh
- Hỏi: 計画変更③和計画変更④有什么区别？
- Đáp: 两者都从"生产开始后因故障Line Stop"出发。計画変更③验证把生产调整到明天和星期六；計画変更④验证取消当天加班。另有計画変更⑤用于验证当天追加加班。来源文件：手順書付シナリオ.xlsx.

## CÂU HỎI 452
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Revision Up部品の切替方法を検証している。
- Cách hỏi: so sánh
- Hỏi: 設計変更①と設計変更②の違いは何ですか。
- Đáp: 設計変更①は期日指定で朝から新品へ切替し、旧品在庫を倉庫へ戻すScenarioです。設計変更②は一日の途中でRevision Up部品へRunning Changeし、旧品在庫を使い切ってから新品へ切替します。両方ともBOPとセットで検証する注記があります。出典ファイル：手順書付シナリオ.xlsx.

## CÂU HỎI 453
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Trong ORICON bị thiếu 1 linh kiện nhưng không có hàng lỗi thực tế.
- Cách hỏi: xử lý sự cố
- Hỏi: Trường hợp này thuộc scenario nào?
- Đáp: Thuộc 員数不足 No.10: số lượng linh kiện trong ORICON bị thiếu, sản xuất trong ngày thiếu 1 cái và không có hiện phẩm lỗi. Khác với 加工中不良 No.9 là có hiện phẩm lỗi. Nguồn file: 手順書付シナリオ.xlsx.

## CÂU HỎI 454
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 仓库里留下了当前暂时不需要的多余部品。
- Cách hỏi: tình huống
- Hỏi: 这种情况对应哪个验证Scenario？
- Đáp: 对应No.11 員数過多。定义为ORICON内部品数量过多，导致当前不需要的部品留在手边。来源文件：手順書付シナリオ.xlsx.

## CÂU HỎI 455
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 改造部品をAMS外Lineへ供給する検証を計画している。
- Cách hỏi: trực tiếp
- Hỏi: オフライン改造はどのScenarioですか。
- Đáp: No.13 改造②です。自動倉庫のORICONから改造用部品をAMS外Lineへ供給するScenarioです。No.12 改造①は改造用BOPを作成してSystemを使うOnline改造です。出典ファイル：手順書付シナリオ.xlsx.

## CÂU HỎI 456
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: ACR đưa ORICON vào kho nhưng kỹ sư muốn xác nhận đủ nội dung kiểm chứng.
- Cách hỏi: xử lý sự cố
- Hỏi: Hạng mục ACR入庫 yêu cầu kiểm tra những gì?
- Đáp: Cần xác nhận ACR đưa ORICON vào đúng kệ chỉ định; nhiều ACR có thể chạy đồng thời; thời gian xử lý nằm trong dự kiến; và trạng thái communication không có vấn đề. Hướng dẫn còn yêu cầu biết cách xem shelf chỉ định trên Matecon, lấy/check communication log và xác nhận tồn kho trên Opcenter. Nguồn file: 手順書付シナリオ.xlsx.

## CÂU HỎI 457
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: CTU已收到部品，但工程师只确认"箱子有移动"就准备判定Pass。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: CTU工程搬送只要实际移动了ORICON就可以判定OK吗？
- Đáp: 不可以。Scenario要求确认分岐Stand→CTU移载正常、CTU搬送到预定工程、搬送时间符合预期、CTU与分岐Stand能够互相等待，而且Matecon上的供给先与实际供给先一致。来源文件：手順書付シナリオ.xlsx.

## CÂU HỎI 458
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: ACR出庫検証とC棟移動後確認を比較している。
- Cách hỏi: so sánh
- Hỏi: ACR出庫とC棟移動では確認Pointがどう違いますか。
- Đáp: ACR出庫では正しい棚番から取り出すこと、複数台同時稼働、処理速度、Stand→Conveyor押出しTimingを確認します。C棟移動後は出庫結果がMOMへ反映されること、OpcenterのContainerNameが注文番号になっていること、工程在庫へ登録されていることなどを確認します。出典ファイル：手順書付シナリオ.xlsx.

## CÂU HỎI 459
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xóa hoàn toàn một Container thử nghiệm đã nhập kho.
- Cách hỏi: trực tiếp
- Hỏi: Trước khi chỉnh số lượng Container về 0, bước đầu tiên cần làm gì nếu Container vẫn nằm trong MaterialQueue?
- Đáp: Phải Unload Container khỏi MaterialQueue trước. Tài liệu ghi rõ đây là bước phải làm trước vì nếu thay đổi quantity khi Container vẫn ở Queue thì có thể phát sinh vấn đề do hệ thống đang xử lý. Nguồn file: MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 460
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 测试Container还带着供给指示，需要彻底清除。
- Cách hỏi: tình huống
- Hỏi: 如何找到并删除该Container对应的MfgOrder供给指示？
- Đáp: 在ContainerAttribute中找到SUPPLY_ORDER并复制其Value；转到Mfg Order画面粘贴该Value进行搜索，再执行Delete。之后回到ContainerAttribute，选中SUPPLY_ORDER属性，点击垃圾桶并Submit，把Container上的供给指示属性也删除。来源文件：MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 461
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Container数量1を0へ補正する操作を行っている。
- Cách hỏi: trực tiếp
- Hỏi: ChangeQtyで数量1を0にする場合、AdjustQtyはいくつですか。
- Đáp: -1を入力します。ChangeQty画面でContainer名を入力し、AdjustReasonとAdjustQtyを設定してSubmitします。出典ファイル：MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 462
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Sau ChangeQty, kỹ sư cần xác nhận Container đã được vô hiệu hóa đúng.
- Cách hỏi: xử lý sự cố
- Hỏi: Trạng thái nào được xem là OK sau khi quantity được đưa về 0?
- Đáp: Tìm Container và kiểm tra ContainerStatus. Nếu STATUS = Inactive và INNER_QTY = 0 thì tài liệu đánh giá OK. Nguồn file: MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 463
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师已经把旧Container设为Inactive，准备结束清理。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 只把Container数量变成0，不Rename也没有问题，对吗？
- Đáp: 不对。资料要求继续执行Rename，因为Container名使用ORICON ID；如果同名Container保留，下次同一个ORICON再次入库时可能因为同名Container残留而发生错误。来源文件：MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 464
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Test ContainerをRenameして再利用時の重複を防ぎたい。
- Cách hỏi: tình huống
- Hỏi: Rename後の名前はどの形式に統一しますか。
- Đáp: RenameYYYYMMDD_連番形式に統一して入力し、Submitします。出典ファイル：MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 465
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Container mới chỉ ở trạng thái Acceptance Start, chưa hoàn tất nhập kho.
- Cách hỏi: trực tiếp
- Hỏi: Muốn đưa RMAcceptanceStart sang trạng thái Completed thì thao tác theo trình tự nào?
- Đáp: Chọn Container mục tiêu, vào ShopFloorTxns, chọn Move Non Std..., sau đó chọn Move và xác nhận Operation trở thành RMAcceptanceCompleted. Nguồn file: MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 466
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较"已入库Container清理"和"处理中Container清理"的步骤。
- Cách hỏi: so sánh
- Hỏi: 所有Container都必须完整执行相同的清理步骤吗？
- Đáp: 不一定。资料明确写明，根据Container目前处于"已出库、已入库到哪一步"等不同状态，有些工程可以跳过。但如果在MaterialQueue中，应优先Unload；如果存在SUPPLY_ORDER，还需要删除MfgOrder和ContainerAttribute。来源文件：MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 467
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 入庫済みTest ContainerをContainer Searchで探している。
- Cách hỏi: xử lý sự cố
- Hỏi: 入庫済みDataを検索する時の目印は何ですか。
- Đáp: Container SearchでContainer名を5%として検索すると入庫済みDataがHitし、Operation = RMAcceptanceCompletedが入庫完了Dataの目印と記載されています。出典ファイル：MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 468
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới muốn đổi quantity trước rồi mới unload vì thao tác nhanh hơn.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Có thể ChangeQty trước rồi Unload MaterialQueue sau không?
- Đáp: Không nên. Tài liệu ghi rõ MaterialQueueからのUnload phải làm trước vì thay đổi số lượng trong lúc Container còn nằm trên Queue có thể gây lỗi do đang ở trạng thái xử lý. Nguồn file: MOMおよびWMSデータ完全クリア方法.xlsx.

## CÂU HỎI 469
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: WMS工程师正在确认C栋3F Block2的棚番编码。
- Cách hỏi: trực tiếp
- Hỏi: Block2棚番的开头格式是什么？
- Đáp: Block2记录以C3A02...开头。例如最前面的棚番为C3A02010101、C3A02010102、C3A02010103等。来源文件：TANABAN_Master.xlsx.

## CÂU HỎI 470
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: WMS棚番MasterのWarehouse Codeを確認している。
- Cách hỏi: trực tiếp
- Hỏi: C棟3F Block2の棚番に設定されている倉庫Codeは何ですか。
- Đáp: 表示されている棚番には倉庫Code 30C5が設定されています。出典ファイル：TANABAN_Master.xlsx.

## CÂU HỎI 471
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang xem các location đầu tiên của Block2 để kiểm tra quy luật tầng kệ.
- Cách hỏi: tình huống
- Hỏi: Cùng vị trí C3A020101 có những mã location nào?
- Đáp: Có 5 mã liên tiếp: C3A02010101, C3A02010102, C3A02010103, C3A02010104, C3A02010105. Nguồn file: TANABAN_Master.xlsx.

## CÂU HỎI 472
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较同一棚列的5个Location。
- Cách hỏi: so sánh
- Hỏi: C3A02010201到C3A02010205的主要差异在哪里？
- Đáp: 前面的C3A020102部分相同，最后两位从01到05变化。文件连续列出了这5个棚番，并且都使用仓库Code 30C5。来源文件：TANABAN_Master.xlsx.

## CÂU HỎI 473
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新規棚番が既存MasterのPatternから外れていないか確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: C3A02011506はこの表示Patternから見て登録済みと確認できますか。
- Đáp: 確認できません。読み取れたC3A020115系列は01～05までです。06はこのFileの該当範囲では確認されていないため、登録済みと断定してはいけません。出典ファイル：TANABAN_Master.xlsx.

## CÂU HỎI 474
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn phân biệt nhóm kệ 01xx và 02xx trong Block2.
- Cách hỏi: so sánh
- Hỏi: Sau C3A02012405, dãy mã tiếp theo bắt đầu như thế nào?
- Đáp: Sau nhóm C3A0201..., file chuyển sang C3A02020101, C3A02020102... rồi tiếp tục các nhóm C3A020202xx, C3A020203xx theo cùng pattern 5 mã cuối 01–05. Nguồn file: TANABAN_Master.xlsx.

## CÂU HỎI 475
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人看到每行后面都有数字0，准备解释其业务意义。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 可以仅凭这个文件确定每个棚番后面的0具体代表什么业务状态吗？
- Đáp: 不能。文件中确实在大量棚番记录后显示0，但当前可读取的表头没有明确说明该列的业务含义。因此只能确认值为0，不能擅自解释为可用、空棚或其他状态。来源文件：TANABAN_Master.xlsx.

## CÂU HỎI 476
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 登録済み棚番の見分け方を確認している。
- Cách hỏi: tình huống
- Hỏi: Fileには登録済み棚番をどう示すと書かれていますか。
- Đáp: 冒頭に黄色セル：登録済みと記載されています。したがって色情報を確認できる場合、黄色Cellが登録済みの目印です。出典ファイル：TANABAN_Master.xlsx.

## CÂU HỎI 477
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên chuẩn bị thêm rack mới và muốn tạo mã TANABAN theo cảm tính.
- Cách hỏi: xử lý sự cố
- Hỏi: Có nên tự tạo mã mới chỉ dựa vào việc tăng số cuối lên 06 không?
- Đáp: Không. File hiện thể hiện các nhóm location với hậu tố 01–05, nhưng không có quy tắc chính thức nói rằng có thể tự mở rộng thành 06. Khi thêm rack cần đối chiếu master và quy tắc đăng ký WMS thay vì suy luận từ chuỗi số. Nguồn file: TANABAN_Master.xlsx.

## CÂU HỎI 478
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认棚番Master与实际WMS登记时应该核对哪些值。
- Cách hỏi: trực tiếp
- Hỏi: 从这个Master至少可以直接核对哪些信息？
- Đáp: 至少可以直接核对所属区域如C棟3F_ブロック2、棚番字符串如C3A02010101、仓库Code 30C5、以及文件注记的"黄色Cell为已登记"。没有表头定义的列则不要自行赋予业务含义。来源文件：TANABAN_Master.xlsx.

---
Ghi chú dedup: 伝票発行システムマニュアル_仮.pptx (MOM周辺) có thể trùng nội dung với 伝票発行システムマニュアル_仮(JP).pdf đã dùng ở mẻ 1 — cần dedup khi import.
