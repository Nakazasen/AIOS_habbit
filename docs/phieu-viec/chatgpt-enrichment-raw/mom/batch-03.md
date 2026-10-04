# Mẻ MOM 03 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Tài liệu: (12) (file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx, (13) Báo cáo lỗi xuất kho AMS.xlsx, (14) (File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx, (15) マテコン操作手順書_v001_生産技術 TV.pdf, (16) 260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf
Phân bố: vi 17, zh 18, ja 15. Đủ 5 cách hỏi.
Lưu ý: file 15 là bản PDF của cùng manual Matecon đã dùng ở mẻ 1 (bản .xlsx) → cặp 131–140 trùng lặp một phần với cặp 1–10. Cần dedup khi import.

## CÂU HỎI 101
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư sản xuất cần kiểm tra nhanh khác biệt BOM giữa hai mã hàng trước khi đánh giá thay đổi.
- Cách hỏi: trực tiếp
- Hỏi: Trong TC2412, muốn so sánh BOM của hai mã hàng thì bắt đầu thao tác như thế nào?
- Đáp: Nhấn 開く để mở màn hình chọn nội dung, chọn コンテンツを開く rồi tìm mã hàng thứ nhất. Sau khi xác nhận đúng mã và cấu trúc BOM, dùng コンテキストを分割 để chia màn hình trái/phải. Ở vùng bên phải chọn ビューを開く, tìm mã hàng thứ hai và xác nhận cả hai cấu trúc BOM đã được tải trước khi chạy 比較. Tài liệu dùng ví dụ 31TEST0001 và 31TEST0002. Nguồn file: (file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx.

## CÂU HỎI 102
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang chuẩn bị đối chiếu revision cũ và mới của linh kiện trên TC2412.
- Cách hỏi: tình huống
- Hỏi: Tôi đã mở mã hàng thứ nhất nhưng muốn nhìn hai BOM song song để tránh chuyển qua lại màn hình. Làm thế nào?
- Đáp: Dùng コンテキストを分割 để chia context thành hai vùng trái và phải. Giữ mã hàng thứ nhất ở bên trái; tại vùng bên phải chọn menu … → ビューを開く, sau đó tìm và mở mã hàng thứ hai. Khi cả hai mã và cấu trúc BOM đều hiển thị đúng thì mới thực hiện so sánh. Nguồn file: (file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx.

## CÂU HỎI 103
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người kiểm tra BOM nhìn thấy các dòng màu cam và màu đỏ sau khi chạy Compare.
- Cách hỏi: so sánh
- Hỏi: Màu cam và màu đỏ trong kết quả so sánh BOM có ý nghĩa khác nhau thế nào?
- Đáp: Màu cam biểu thị có khác biệt về số lượng, biểu thức biến thể, text mã hàng hoặc revision. Màu đỏ biểu thị hạng mục chỉ tồn tại ở một phía và phía còn lại không có mã hàng tương ứng. Nếu khác số lượng, hệ thống hiển thị chênh lệch bằng giá trị số; có thể nhấp từng hạng mục để xem chi tiết thay đổi. Nguồn file: (file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx.

## CÂU HỎI 104
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Trên line chuẩn bị model theo điện áp và destination nhưng 100%BOM hiển thị linh kiện không đúng biến thể.
- Cách hỏi: xử lý sự cố
- Hỏi: Khi 100%BOM hiển thị sai cấu hình điện áp hoặc nơi giao hàng, cần kiểm tra lại bước nào trong TC2412?
- Đáp: Cần kiểm tra Điều kiện áp dụng biến thể. Quy trình gồm 4 bước: ① chọn bộ phận trong danh sách phân cấp, ② nhấn Chỉnh sửa, ③ đánh dấu đúng các thông số cần áp dụng như điện áp, nơi giao hàng, kích thước, ④ nhấn Lưu chỉnh sửa. 150%BOM chứa toàn bộ biến thể; 100%BOM được tạo bằng cách lọc theo các điều kiện biến thể này. Nguồn file: (file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx.

## CÂU HỎI 105
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人正在确认150%BOM和100%BOM的关系。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 150%BOM只包含当前机种实际使用的部品，对吗？
- Đáp: 不对。150%BOM包含所有Variant的部品结构，通过设定Variant适用条件，例如电压、出货地、尺寸等，从150%BOM筛选出当前条件需要的结构，形成100%BOM。资料说明可在150%BOM画面选择对象，再从右侧菜单执行"100%表示"。来源文件：(file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx。

## CÂU HỎI 106
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要把TC2412中的大量数据导出到Excel进行批量处理。
- Cách hỏi: trực tiếp
- Hỏi: TC2412中批量导出Excel使用什么功能？
- Đáp: 使用Excel Round Trip。从菜单选择Excel Round Trip，然后执行"导出到Excel"。资料说明Round Trip可用于在Excel上进行批量编辑，并有效地把修改结果反映回TC2412。来源文件：(file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx。

## CÂU HỎI 107
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: MBOM TOP的Revision发生变化，工程师准备继续使用旧BOP。
- Cách hỏi: tình huống
- Hỏi: MBOM TOP Rev或者BOE TOP Rev发生变化后，原来的BOP关联可以不处理吗？
- Đáp: 不可以直接忽略。资料的AWC EASYPLAN流程明确写明，如果MBOM TOP Rev或BOE TOP Rev发生变化，需要重新与BOP建立关联。之后再将MBOM、BOP、BOE联携到Opcenter，实现与制造管理系统的集成。来源文件：(file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx。

## CÂU HỎI 108
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: PLM担当者がEBOMとMBOMの違いを現場担当者へ説明している。
- Cách hỏi: so sánh
- Hỏi: EBOMとMBOMはどのように使い分けますか。
- Đáp: EBOMは設計側の部品構成で、製品の機能構造や全Variantを管理します。MBOMはEBOMのVariant条件を適用し、製造拠点で実際に使用する部品構成へ展開したものです。資料では、100V/220VやJP/US/EUなどの条件に応じてEBOMから具体的なMBOMを作成する例が示されています。出典ファイル：(file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx。

## CÂU HỎI 109
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 150%BOMを開いたがVariant条件の設定メニューが画面に見当たらない。
- Cách hỏi: xử lý sự cố
- Hỏi: 「Variant適用条件」のメニューが表示されない場合、どこを確認しますか。
- Đáp: 資料では、画面右下の↓ボタンを押して非表示のメニューを表示し、そこから「Variant適用条件」を選択します。その後、左側のNavigation Treeを展開し、中央のPanelで部品構成を確認します。出典ファイル：(file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx。

## CÂU HỎI 110
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人がTC2412でBOPを作ればそのままMOM連携が完了すると理解している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: TC2412でBOPを作成した時点で、Opcenterとの連携まで自動的に完了したと考えてよいですか。
- Đáp: その理解では不十分です。資料の流れでは、CADから150%EBOMを作成し、MBOMを作成し、MBOMとBOEをCOLMINA/VPSへ出力して工程設計を行い、承認済みBOPをTCへ取り込みます。その後、MBOM・BOP・BOEをOpcenterへ連携して初めて製造管理システムとの統合につながります。出典ファイル：(file số 1)TC2412操作マニュアル MBOM検索システム2 2026522 (VN).pptx。

## CÂU HỎI 111
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang tổng hợp kết quả nhập kho AMS bị đẩy sang cổng NG.
- Cách hỏi: trực tiếp
- Hỏi: Đợt lỗi nhập kho AMS trong báo cáo có bao nhiêu thùng bị đẩy ra cổng NG và được chia thành những nhóm nào?
- Đáp: Có tổng cộng 18 thùng bị đẩy ra cổng NG. Trong đó 11 thùng có ORICON_STATUS = 0000000000000001, tức trạng thái được xem là OK nhưng vẫn bị đẩy NG; 7 thùng phát sinh cảnh báo và có ORICON_STATUS khác giá trị trên. Trong 7 thùng cảnh báo, báo cáo phân loại 1 thùng lỗi sai lệch dữ liệu hệ thống và 6 thùng liên quan Camera đọc QR ngoại quan. Nguồn file: Báo cáo lỗi xuất kho AMS.xlsx.

## CÂU HỎI 112
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: ORICON %9702 bị NG và kỹ sư phát hiện dữ liệu EDI có Lot sản xuất.
- Cách hỏi: tình huống
- Hỏi: Với thùng %9702, ngày 17/6 đã xử lý những bước gì và kết quả thế nào?
- Đáp: Nhóm lỗi dữ liệu được xử lý bằng cách in lại EDI sau khi xóa thông tin Lot sản xuất, xóa dữ liệu đã đọc trên SQL và MOM rồi nhập kho lại. Với %9702, 補正後のSTATUS = 4200000000000000, kết quả kiểm tra là VendorShippingInfoとの照合NG kèm 格納指示FLG_Error. Sau xử lý, ORICON_STATUS hiển thị 0000000000000001 nhưng kết quả tái nhập vẫn NG. Nguồn file: Báo cáo lỗi xuất kho AMS.xlsx.

## CÂU HỎI 113
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhóm Camera được cho nhập kho lại sau khi xóa dữ liệu SQL.
- Cách hỏi: so sánh
- Hỏi: Kết quả tái nhập của 6 thùng lỗi Camera ngày 17/6 khác nhau thế nào?
- Đáp: Sau khi xóa dữ liệu SQL và nhập lại, 4 thùng thành công gồm %6880, %7087, %7573, %7715. Hai thùng vẫn NG là %10304 và %11406. %10304 có trạng thái hiệu chỉnh 0201000100000000, QR phía trái đối chiếu NG; %11406 có 02010001A0000000, QR mặt trước, phải và trái đối chiếu NG. Cả hai đều kèm CAM xử lý thất bại và 格納指示FLG_Error. Nguồn file: Báo cáo lỗi xuất kho AMS.xlsx.

## CÂU HỎI 114
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: ORICON %10304重新入库仍然被送到NG Gate，工程师正在确认错误内容。
- Cách hỏi: xử lý sự cố
- Hỏi: %10304的主要异常信息是什么？
- Đáp: %10304的补正后STATUS为0201000100000000。确认结果为左侧QR比对NG，同时发生CAM处理失败以及格納指示FLG_Error。2026年6月17日重新入库的结果仍为NG；重新入库后记录的ORICON_STATUS为0000000000000001。因此仅看到最终ORICON_STATUS为正常值，不能否定前面的Camera/QR异常。来源文件：Báo cáo lỗi xuất kho AMS.xlsx。

## CÂU HỎI 115
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为ORICON_STATUS只要是0000000000000001就一定可以正常入库。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: ORICON_STATUS = 0000000000000001就能保证ORICON不会进入NG Gate，对吗？
- Đáp: 不对。报告记录了11箱虽然ORICON_STATUS为0000000000000001，但仍然被送到NG Gate。另外，%10304和%11406重新入库失败时，最终ORICON_STATUS也记录为该正常值。因此排查时不能只看ORICON_STATUS，还必须结合QR照合、CAM处理和格纳指示FLG等结果。来源文件：Báo cáo lỗi xuất kho AMS.xlsx。

## CÂU HỎI 116
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 操作员使用Opcenter的Manual Supply Line对两个ORICON执行手动出库。
- Cách hỏi: trực tiếp
- Hỏi: ORICON ...11922和...12860发生了什么手动出库异常？
- Đáp: 两个ORICON原本实际位于棚架上，WMS也记录该棚位"有货"。通过Opcenter的Manual Supply Line执行出库后，MOM自动把命令判定为完成，设置MOVE_FIN_FLG = 1并写入时间，但ACR并没有实际运行并取走箱子。随后WMS根据MOM结果删除了棚位库存数据，造成系统显示"空棚"而实物仍在棚上的虚拟库存状态。来源文件：Báo cáo lỗi xuất kho AMS.xlsx。

## CÂU HỎI 117
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: WMS已经把一个实际仍有箱子的棚位判断为空位，又收到新ORICON ...12626的入库命令。
- Cách hỏi: tình huống
- Hỏi: 为什么新ORICON ...12626会发生碰撞风险？
- Đáp: 因为前面的手动出库被系统错误地判定为完成，WMS删除了原棚位库存，所以软件上该位置成为"空棚"；但实际...11922等箱子仍在棚上。之后WMS把新ORICON ...12626分配到这个"空棚"，ACR收到命令后尝试把新箱子推入已经被实物占用的位置，最终导致碰撞。来源文件：Báo cáo lỗi xuất kho AMS.xlsx。

## CÂU HỎI 118
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 手動出庫の「成功扱い」と実際のACR動作不一致に対する暫定対応を確認している。
- Cách hỏi: so sánh
- Hỏi: 調査用の対応と復旧用の暫定対応はそれぞれ何を実施しましたか。
- Đáp: 調査用として、KTSXはORICON ...11922と...12860の出庫時刻のMatecon Logを取得し、KTSX JPへ送付して調査しました。暫定復旧として、KTCT＋KTSXは旧出庫データ、つまり「成功扱いになった誤データ」を削除し、Matecon ACR・CTUをOFF/ONして再認識させ、2026年6月18日に出庫命令を完了させました。出典ファイル：Báo cáo lỗi xuất kho AMS.xlsx。

## CÂU HỎI 119
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 6月18日8:30にOpcenterへアクセスできず、ラインへの部品供給対応が必要になった。
- Cách hỏi: xử lý sự cố
- Hỏi: 6月18日8:30のOpcenterアクセス不可の記録では、何が問題でしたか。
- Đáp: 記録では、ログイン数の上限超過によりOPへアクセスできない状態でした。そのため倉庫へ連絡し、製造ライン外で対応する旨が記載されています。同日、Opcenterの自動出庫だけではライン用部品が不足したため、FKおよびMK向けに手動出庫対応も実施されています。出典ファイル：Báo cáo lỗi xuất kho AMS.xlsx。

## CÂU HỎI 120
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者が6月18日の手動出庫結果を新人へ確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 6月18日のFK向け手動出庫では、3V2ND00160のORICONはNGが残りましたか。
- Đáp: 資料に記載されたFK向け3V2ND00160のORICON 8262、6888、8249、8051、7690はいずれも結果がOKです。同じ表では3W2ND25310の10919もOKと記録されています。出典ファイル：Báo cáo lỗi xuất kho AMS.xlsx。

## CÂU HỎI 121
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới cần tìm nhanh một MBOM khi đã biết ID hoặc mã hàng.
- Cách hỏi: trực tiếp
- Hỏi: Cách tìm kiếm cơ bản hiệu quả nhất trong TC2412 khi đã biết ID hoặc mã hàng là gì?
- Đáp: Nhập trực tiếp ID hoặc code mã hàng vào thanh Search. Kết quả MBOM, ECR và các dữ liệu tương ứng sẽ hiển thị dạng danh sách để mở chi tiết. Tài liệu nêu đây là cách hiệu quả nhất khi đã biết ID hoặc code cần tìm. Nguồn file: (File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx.

## CÂU HỎI 122
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn tìm BOM do đồng nghiệp tạo nhưng Advanced Search không trả kết quả.
- Cách hỏi: tình huống
- Hỏi: Trong Advanced Search, vì sao chỉ thấy dữ liệu của chính mình và phải sửa filter nào?
- Đáp: Trường Chủ sở hữu mặc định tự động điền user hiện tại. Với điều kiện đó, BOM của người khác sẽ không xuất hiện. Nếu muốn tìm dữ liệu do người khác tạo, cần clear nội dung trường Chủ sở hữu rồi chạy tìm kiếm lại. Nguồn file: (File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx.

## CÂU HỎI 123
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần chọn giữa Search thông thường và Advanced Search.
- Cách hỏi: so sánh
- Hỏi: Tìm kiếm cơ bản và tìm kiếm nâng cao trong TC2412 khác nhau thế nào?
- Đáp: Tìm kiếm cơ bản phù hợp khi đã biết ID hoặc code mã hàng và muốn truy cập nhanh. 高度な検索 dùng khi cần kết hợp nhiều điều kiện và thuộc tính như chủ sở hữu, người lập, trạng thái; điều kiện tìm kiếm còn có thể được lưu để dùng lại cho các tra cứu định kỳ. Nguồn file: (File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx.

## CÂU HỎI 124
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师输入品目条件后搜索不到目标数据。
- Cách hỏi: xử lý sự cố
- Hỏi: 用品目代码搜索却没有结果时，资料提醒要检查什么？
- Đáp: 资料提醒搜索条件主要使用英文；使用日文条件时可能找不到结果。若按品目代码搜索，应按Part进行搜索并选择品目Rev；如果使用アイテム作为搜索对象，可能得不到结果。因此要先确认对象类型和搜索语言。来源文件：(File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx。

## CÂU HỎI 125
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为Advanced Search默认会搜索所有用户的数据。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Advanced Search默认会包含所有Owner的数据，对吗？
- Đáp: 不对。资料说明Owner字段默认自动填入当前用户，因此初始条件实际上会限定为本人数据。如果需要搜索其他用户创建的BOM，必须清除Owner字段的默认值。来源文件：(File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx。

## CÂU HỎI 126
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 用户想从自己整理的Folder中系统地打开相关Item和BOM。
- Cách hỏi: trực tiếp
- Hỏi: Explorer中的个人Folder可以做什么？
- Đáp: 打开个人Folder后，可按层级显示与该Folder关联的Item，并使用"打开Item、打开BOM、打开Folder"等基本操作。这样可以按结构查看关联数据。资料同时说明每个人的个人Folder结构可能不同。来源文件：(File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx。

## CÂU HỎI 127
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 部品変更の影響範囲を確認するため、BOMの順方向と逆方向の参照を使い分けている。
- Cách hỏi: so sánh
- Hỏi: 「内容」と「使用先」の機能は何が違いますか。
- Đáp: 「内容」は親品目から子品目へBOM構造を階層表示する順方向展開で、数量・Revision・Statusなどを確認します。「使用先」は、そのデータがどこで使用されているかを逆方向に展開し、変更影響を分析するための機能です。出典ファイル：(File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx。

## CÂU HỎI 128
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 大規模ASSYを3D表示したところTeamcenterの応答が重くなった。
- Cách hỏi: tình huống
- Hỏi: 大きなASSYを3Dで確認する時に注意すべき点は何ですか。
- Đáp: 3D表示は3D図面が登録されている品目で利用できますが、資料では大規模ASSYの表示はServerへ負荷を与えると注意されています。そのため、必要性を確認して使用し、単純な構成確認であればBOMの「内容」など別の表示機能も使い分ける必要があります。出典ファイル：(File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx。

## CÂU HỎI 129
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: データ変更の操作履歴を詳しく調べたい。
- Cách hỏi: xử lý sự cố
- Hỏi: 通常の「履歴」より詳細な操作情報を確認したい場合は何を使いますか。
- Đáp: 監査ログを使用します。資料では「履歴」は作成・更新・Status変更などの履歴を管理し、監査ログは履歴よりさらに詳細な操作Logを記録・確認できる機能とされています。出典ファイル：(File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx。

## CÂU HỎI 130
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人が13機能のすべてをKDCで日常使用すると理解している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: TC2412の13機能はすべてKDCで使用している機能ですか。
- Đáp: いいえ。資料では、例えば「分類」「変更内容」「関係」「報告」などについてKDCでは使用しない項目と明記されています。一方、KDC、概要、内容、3D、使用先、添付、履歴、Workflow、監査ログなどは、それぞれ品目管理や確認に使う機能として説明されています。出典ファイル：(File số 2)TC2412操作マニュアル MBOM検索システム2026522 (VN).pptx。

## CÂU HỎI 131
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cài Matecon cho KDTVN và cần chọn đúng mã nhà máy.
- Cách hỏi: trực tiếp
- Hỏi: Trong cấu hình Matecon, mã site dùng cho KDTVN là bao nhiêu?
- Đáp: Trong mục thông tin hệ thống, site được quy định: 0 = KDC dây chuyền LSU Hirakata, 1 = KDC phòng thí nghiệm Hirakata, 2 = KDC Tamaki, 3 = KDTCN và 4 = KDTVN. Vì vậy KDTVN phải dùng giá trị 4. Nguồn file: マテコン操作手順書_v001_生産技術 TV.pdf.

## CÂU HỎI 132
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Matecon trên PC mới khởi động nhưng không load đúng setting.
- Cách hỏi: tình huống
- Hỏi: File _Setting.csv đã copy vào thư mục Setting nhưng Matecon vẫn không load đúng. Cần kiểm tra gì đầu tiên?
- Đáp: Cần kiểm tra tên file có khớp với tên máy tính hay không. Tài liệu quy định file _Setting.csv phải đi kèm đúng tên PC; nếu không khớp, cấu hình sẽ không được nạp chính xác. Ví dụ tên PC trong tài liệu là AthenaLSU-MCS. Nguồn file: マテコン操作手順書_v001_生産技術 TV.pdf.

## CÂU HỎI 133
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần phân biệt mode chạy tự động với mode thao tác thủ công của Matecon.
- Cách hỏi: so sánh
- Hỏi: ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?
- Đáp: ctrlMode = 0 là chế độ sản xuất tự động, truyền thông SLMP với hệ thống cấp trên MOM và thiết bị được kích hoạt; Matecon gửi lệnh input/output đến ACR/CTU theo chỉ thị từ hệ thống cấp trên. ctrlMode = 1 là chế độ thủ công và chặn truyền thông. Nguồn file: マテコン操作手順書_v001_生産技術 TV.pdf.

## CÂU HỎI 134
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Trong lúc ACR chạy, nhân viên nghe thấy tiếng động bất thường và ngửi thấy mùi lạ.
- Cách hỏi: xử lý sự cố
- Hỏi: Theo quy định an toàn của Matecon, có được tiếp tục chạy chậm để quan sát thêm không?
- Đáp: Không. Khi phát hiện tiếng động, mùi lạ hoặc hành vi bất thường, tài liệu yêu cầu dừng ngay AGV và điều tra nguyên nhân. Ngoài ra, khi khởi động, vận hành, phục hồi lỗi hoặc thao tác thủ công phải bảo đảm không có công nhân ở gần xe. Nguồn file: マテコン操作手順書_v001_生産技術 TV.pdf.

## CÂU HỎI 135
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 普通Line作业员准备切到手动模式移动AGV。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 只要确认周围没人，任何作业员都可以手动驾驶AGV，对吗？
- Đáp: 不对。资料规定，手动模式驾驶只应由生产技术人员或设备保全人员执行。同时，在启动、运行、故障恢复或手动操作前，都必须确认AGV附近没有作业人员。来源文件：マテコン操作手順書_v001_生産技術 TV.pdf。

## CÂU HỎI 136
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 同一系统需要配置第二台、第三台Material Handling Controller。
- Cách hỏi: trực tiếp
- Hỏi: controlNum对于第二台和后续控制器应如何定义？
- Đáp: controlNum用于设定Material Handling Controller的设备编号。资料规定第二台及后续设备应定义为#2、#3等对应编号。来源文件：マテコン操作手順書_v001_生産技術 TV.pdf。

## CÂU HỎI 137
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在比较Matecon ACR和Matecon CTU可配置的SQL项目。
- Cách hỏi: so sánh
- Hỏi: 库存管理表相关设置是否同时适用于ACR和CTU？
- Đáp: 不是。资料对库存表配置明确注明"只有Matecon CTU可以配置，Matecon ACR不包含"。库存表访问参数包括Server、DB、User和Password。类似的AGV Trigger／系统完成表配置也注明仅适用于CTU。来源文件：マテコン操作手順書_v001_生産技術 TV.pdf。

## CÂU HỎI 138
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Atlas AGVとの通信ができず、MQTT設定を確認している。
- Cách hỏi: tình huống
- Hỏi: MQTT Broker設定では、どのIPアドレスを設定する想定ですか。
- Đáp: 資料では、Atlas（AGV）との通信に必要なMQTT Broker情報として、MQTT Broker ServerにMatecon PCのIPアドレスを設定すると記載されています。出典ファイル：マテコン操作手順書_v001_生産技術 TV.pdf。

## CÂU HỎI 139
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: AGVとの定期通信周期を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: stsMonTimeの標準設定値と通信周期は何ですか。
- Đáp: stsMonTimeはAGVとの定期通信時間を設定する項目で、単位はmsです。資料のDefaultは1000で、約1秒間隔で定期通信を行う設定です。値を変更する場合は、この単位を取り違えないよう確認が必要です。出典ファイル：マテコン操作手順書_v001_生産技術 TV.pdf。

## CÂU HỎI 140
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 現場で走行Mapと棚位置情報を変更した直後。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 設定ファイルやMapの保存が正常なら、そのまま本番運転を開始してよいですか。
- Đáp: いいえ。資料では、設定ファイル、走行Map、棚位置情報、Block設定を変更した場合、全面稼働に入る前に必ず動作確認を実施するよう定めています。またMapや棚位置情報の収集は低速・低Risk条件で行うことが推奨されています。出典ファイル：マテコン操作手順書_v001_生産技術 TV.pdf。

## CÂU HỎI 141
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra mã 3V2ND00150 không tạo được chỉ thị xuất kho ngày 18/6.
- Cách hỏi: trực tiếp
- Hỏi: Với 3V2ND00150, bảng điều tra ghi tồn kho và MaterialQueue phân bố ở các WorkCenter thế nào?
- Đáp: Tại thời điểm 18/6 14:30, 3V2ND00150 được ghi có số lượng tồn kho line 80 ở WorkCenter C3B_YB2200C30033, nhưng MaterialQueue tại đó là 0. Ở WorkCenter C3B_YB2200C30034, tồn kho line là 0 nhưng MaterialQueue là 80, và bảng đánh dấu đây là WorkCenter đúng theo ERPBOM. Nguồn file: 260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf.

## CÂU HỎI 142
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: 3V2ND00150 có 80 linh kiện nhưng hệ thống vẫn không tạo được chỉ thị xuất kho.
- Cách hỏi: tình huống
- Hỏi: Bảng điều tra nghi ngờ nguyên nhân gì khi tồn kho nằm ở WorkCenter 33 nhưng ERPBOM lại chỉ về WorkCenter 34?
- Đáp: Bảng ghi dưới dạng nghi vấn rằng có khả năng khi thực hiện xuất kho manual đã chọn WorkCenter phía 33, trong khi WorkCenter đúng theo ERPBOM là C3B_YB2200C30034. [SUY LUẬN] Đây mới là giả thuyết điều tra được ghi trong tài liệu, chưa phải nguyên nhân đã xác nhận cuối cùng; cần đối chiếu thao tác manual và log để kết luận. Nguồn file: 260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf.

## CÂU HỎI 143
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai mã không tạo được chỉ thị xuất kho để tìm pattern sai WorkCenter.
- Cách hỏi: so sánh
- Hỏi: 3V2ND00150 và 3V2ND25400 khác nhau thế nào về WorkCenter nghi ngờ?
- Đáp: Với 3V2ND00150, tồn kho 80 nằm ở C3B_YB2200C30033, trong khi WorkCenter đúng theo ERPBOM được ghi là phía 0034; tài liệu nghi ngờ manual đã chọn phía 33. Với 3V2ND25400, bảng ghi tồn kho 0 tại WorkCenter 0033 nhưng MaterialQueue 1325, còn tồn kho 1325 xuất hiện tại WorkCenter 0035 với MaterialQueue 0; tài liệu nghi ngờ manual đã chọn phía 35. [SUY LUẬN] Các ghi chú này là giả thuyết điều tra, không phải kết luận nguyên nhân cuối. Nguồn file: 260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf.

## CÂU HỎI 144
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 3W2ND25310出现"出库指示数量不足"，工程师检查WorkCenter和MaterialQueue。
- Cách hỏi: xử lý sự cố
- Hỏi: 3W2ND25310的调查数据有什么异常分布？
- Đáp: 表中记录3W2ND25310在WorkCenter C3B_YB2200C30028有Line库存60，MaterialQueue数量为145，并标记该WorkCenter符合ERPBOM；另一条记录在WorkCenter C3B_YB2200C30029有库存145，MaterialQueue为0。资料同时提出"手动出库时可能选择了WorkCenter 29"的调查假设，并记有相关SO也被纳入计算。[SUY LUẬN] WorkCenter 29为根因尚未被文件最终确认。来源文件：260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf。

## CÂU HỎI 145
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为Line库存数量和MaterialQueue数量应该始终相同。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 调查表中Line库存数量和MaterialQueue数量是一一相同的吗？
- Đáp: 不是。例如3V2ND00150在WorkCenter 0033的Line库存为80而MaterialQueue为0，在0034则Line库存为0而MaterialQueue为80。3W2ND25310也存在WorkCenter 0028库存60、MaterialQueue 145以及0029库存145、MaterialQueue 0的差异。因此调查时必须分别确认库存位置和Queue分配。来源文件：260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf。

## CÂU HỎI 146
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在确认FK8570 Workflow中第10工序的Master映射。
- Cách hỏi: trực tiếp
- Hỏi: 第10工序在调查表中的Workflow、Spec和WorkCenter是什么？
- Đáp: 表中第10工序使用Workflow C3B_302YL93021_FK8570，Spec为Y302XDM000C029，WorkCenter为C3B_YB2200C30022。该组合下面关联了多个产品代码和产品Revision。来源文件：260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf。

## CÂU HỎI 147
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 第20工序出现供给对象确认问题，需要与Master表核对。
- Cách hỏi: tình huống
- Hỏi: FK8570的第20工序应该核对哪个Spec和WorkCenter？
- Đáp: 调查表中第20工序仍属于Workflow C3B_302YL93021_FK8570，对应Spec为Y302XDM000C030，WorkCenter为C3B_YB2200C30023。排查时可用该组合与实际MfgOrder、ERPBOM和供给数据进行对照。来源文件：260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf。

## CÂU HỎI 148
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程技术人员需要确认连续工序的Spec和WorkCenter是否错位。
- Cách hỏi: so sánh
- Hỏi: 第10工序和第20工序的Master映射有什么变化？
- Đáp: 两者的Workflow都是C3B_302YL93021_FK8570。第10工序对应Spec Y302XDM000C029、WorkCenter C3B_YB2200C30022；第20工序则对应Spec Y302XDM000C030、WorkCenter C3B_YB2200C30023。因此排查供给指示时不能只看Workflow，还必须核对工序对应的Spec和WorkCenter。来源文件：260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf。

## CÂU HỎI 149
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 供給指示が作成できず、在庫自体は存在しているため原因を切り分けている。
- Cách hỏi: xử lý sự cố
- Hỏi: この調査表を使う場合、在庫数量以外に何を照合すべきですか。
- Đáp: Line在庫数量だけでなく、MfgOrderに紐づくWorkCenter、MaterialQueue数量、ERPBOM上の正しいWorkCenterを並べて確認する必要があります。資料では、在庫が別WorkCenterへ存在する一方、MaterialQueueはERPBOM側WorkCenterへ付いている例があり、Manual出庫時のWorkCenter選択違いも調査仮説として挙げられています。出典ファイル：260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf。

## CÂU HỎI 150
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者が調査表の「原因」欄をそのまま確定原因として報告しようとしている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 「Manual出庫でWorkCenterを間違えた可能性」という記載は、確定原因として扱ってよいですか。
- Đáp: いいえ。資料の原因欄は「可能性がある」「～を選んだのでは？」という調査段階の表現です。[SUY LUẬN] WorkCenter誤選択は有力な仮説ですが、確定原因とするにはManual操作履歴、MfgOrder、ERPBOM、MaterialQueue、関連Logなどを追加照合する必要があります。出典ファイル：260618_調査_バージョンVN_FULL_TABLE_for_NotebookLM.pdf。
