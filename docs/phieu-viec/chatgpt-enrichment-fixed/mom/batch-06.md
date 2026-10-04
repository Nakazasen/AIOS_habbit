# Mẻ MOM 06 — 30 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Trạng thái: Bản thảo — chưa qua chuyên gia duyệt. Khối: MOM.
Tài liệu: (29) ORICON_STATUS_変換ツール_完成版.xlsx, (30) Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Google Doc), (34) ERD_Kho_Van_NEW.html
BỎ QUA: 仕様書.rar — ChatGPT liệt kê được 35 mục bên trong nhưng không giải nén/đọc được nội dung (thiếu backend RAR) → bỏ qua đúng chỉ dẫn.

## CÂU HỎI 251
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Công nhân tại ORICON Gate nhận một mã STATUS dài và cần tra nhanh lỗi đang phát sinh.
- Cách hỏi: trực tiếp
- Hỏi: Dùng ORICON_STATUS_変換ツール_完成版.xlsx như thế nào để tra lỗi?
- Đáp: Nhập giá trị HEX của ORICON STATUS vào ô B3 dưới dạng chuỗi 16 ký tự. Ô đã được đặt định dạng Text (@), vì vậy số 0 ở đầu được giữ nguyên và không cần thêm dấu nháy đơn ở đầu. Sau khi nhập, công cụ tự động tách bit và trả về nội dung lỗi tương ứng trong cùng sheet. Nguồn file: ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 252
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư nhập STATUS 0201000080000000 để điều tra ORICON bị đẩy NG.
- Cách hỏi: tình huống
- Hỏi: Với 0201000080000000, tool xác định những lỗi nào?
- Đáp: Tool xác định 3件該当, tức 3 lỗi: Bit 31 = 照合QR右_NG, cần kiểm tra QR phía phải và đưa ORICON vào Gate lại; Bit 48 = CAM処理失敗, cần xác nhận Camera/Opcenter; Bit 57 = 格納指示FLG_Error, cần xác nhận trạng thái Opcenter. Nguồn file: ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 253
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người vận hành muốn phân biệt lỗi QR mặt phải với lỗi xử lý Camera.
- Cách hỏi: so sánh
- Hỏi: Bit 31 và Bit 48 khác nhau thế nào?
- Đáp: Bit 31 là 照合QR右_NG, tức lỗi đối chiếu QR phía phải của ORICON; hướng xử lý là kiểm tra QR bên phải và tái đưa ORICON vào Gate. Bit 48 là CAM処理失敗, tức Camera xử lý thất bại; hướng xử lý liên quan kiểm tra Camera và trạng thái Opcenter. Nguồn file: ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 254
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 操作员输入16进制STATUS后发现前导0消失，结果无法正确解析。
- Cách hỏi: xử lý sự cố
- Hỏi: 输入STATUS时怎样避免前面的0丢失？
- Đáp: 应在B3单元格中以16位HEX字符串直接输入。该单元格已经设定为Text格式@，因此前导0会被保留，不需要在前面添加apostrophe。来源文件：ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 255
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人看到工具显示"全てOK"，准备直接判定整个入库流程结束。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 工具显示"全てOK"就表示品质和入库流程全部正常，对吗？
- Đáp: 不对。文件明确注明，"全てOK"只表示ORICON STATUS中没有检测到错误，并不代表品质得到保证，也不能单独证明Opcenter、搬送或实际入库流程已经全部完成。来源文件：ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 256
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在手算ORICON STATUS的Bit位置。
- Cách hỏi: trực tiếp
- Hỏi: 16位HEX值与64bit之间如何换算？
- Đáp: 规则是1个16进制字符对应4bit，因此16位HEX共64bit。最右边的HEX位对应Bit 0～3，最左边对应Bit 60～63。来源文件：ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 257
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: Gate出现QR前面和QR后面的不同异常，需要快速区分。
- Cách hỏi: so sánh
- Hỏi: Bit 29和Bit 30分别代表什么？
- Đáp: Bit 29为照合QR前_NG，需要检查ORICON前面QR；Bit 30为照合QR後_NG，需要检查ORICON后面QR。两种情况都要求确认对应QR后重新投入ORICON Gate。来源文件：ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 258
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 格納指示が出ず、Status変換結果でBit 57が検出された。
- Cách hỏi: xử lý sự cố
- Hỏi: Bit 57が出た場合、何を確認しますか。
- Đáp: Bit 57は格納指示FLG_Errorです。正常時はHOUSE_ORDERへ書き込む処理に関係し、処置欄ではOpcenter状態確認必要となっています。したがって、Gate側だけでなくOpcenter側の格納指示処理も確認します。出典ファイル：ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 259
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 重量判定で複数のBitが同時に検出された。
- Cách hỏi: tình huống
- Hỏi: Bit 49、50、51が同時に出た場合、どう切り分けますか。
- Đáp: Bit 49は重量_箱入数不一致、Bit 50は重量_重量不一致、Bit 51は重量_処理失敗です。Bit 50と51については処置欄にOpcenter状態確認必要と記載されています。出典ファイル：ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 260
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者がSTATUS値を1つの代表エラーだけで報告しようとしている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 1つのHEX STATUSには必ず1種類のErrorしか含まれませんか。
- Đáp: いいえ。1つの64bit STATUSで複数Bitが同時に1になる場合があります。例として0201000080000000ではBit 31、48、57の3件が同時に該当します。そのため、代表エラー1件だけで報告せず、全該当Bitを確認する必要があります。出典ファイル：ORICON_STATUS_変換ツール_完成版.xlsx.

## CÂU HỎI 261
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新任エンジニアがKDTVNのMOM周辺システム全体像を理解しようとしている。
- Cách hỏi: trực tiếp
- Hỏi: KDTVNのMOMは、どの主要システムと連携していますか。
- Đáp: 資料ではMOM／Siemens Opcenterを中心に、設計側のTeamcenter／TC2412、計画側のAPS、倉庫側のWMS／Inter-Stock、搬送制御のMatecon、ACR／CTU／AGVなどの設備、そしてR3やMES進度管理などの周辺システムが連携する全体像が示されています。出典ファイル：Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 262
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: PLMデータ変更後に製造側へどのデータが影響するか確認している。
- Cách hỏi: so sánh
- Hỏi: EBOM、MBOM、BOPの役割はどう違いますか。
- Đáp: EBOMは設計視点の製品構造で、CAD／3DAを元に技術Variantを管理します。MBOMは実際の製造視点で部品を組立単位・工程に配置した構造です。BOPは製造工程の順番、Work Center、作業手順などを定義し、EBOM／MBOMと工程を結びつける情報です。出典ファイル：Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 263
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: TC2412で他担当者が作成したBOMが検索できない。
- Cách hỏi: xử lý sự cố
- Hỏi: Advanced Searchで他ユーザーのBOMが出ない場合、最初にどこを確認しますか。
- Đáp: Owner Filterを確認します。資料では検索時にOwnerへ現在User自身がDefault設定されるため、そのままでは他担当者のデータが検索結果に出ません。共通データや他担当者のBOMを検索する場合はOwner条件をクリアする必要があります。出典ファイル：Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 264
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư mới chưa hiểu vì sao TC2412 phải chuyển 150%BOM thành 100%BOM.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 150%BOM có phải là BOM cuối cùng đưa thẳng xuống sản xuất không?
- Đáp: Không. 150%BOM chứa toàn bộ các biến thể có thể có của sản phẩm. Kỹ sư áp dụng điều kiện biến thể (điện áp, nơi giao hàng, kích thước…) để lọc ra cấu trúc cần thiết cho điều kiện hiện tại, tạo thành 100%BOM rồi mới đưa xuống sản xuất. Nguồn file: Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 265
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đối chiếu hai revision BOM trước khi cập nhật BOP.
- Cách hỏi: tình huống
- Hỏi: Trong TC2412, màu cam và màu đỏ khi Compare BOM chỉ điều gì?
- Đáp: Màu cam chỉ khác biệt thuộc tính giữa hai bên như Qty, điều kiện biến thể, mô tả mã hàng hoặc Revision. Màu đỏ chỉ dòng chỉ tồn tại ở một bên (thêm mới hoặc đã xóa). Nguồn file: Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 266
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: QLSX đang lập lịch APS và muốn hiểu ảnh hưởng của thời gian nghỉ.
- Cách hỏi: trực tiếp
- Hỏi: Trong APS, On Shift và Off Shift / Short Break được tính Efficiency thế nào?
- Đáp: On Shift là thời gian sản xuất và Efficiency cùng Cost Factor được đặt 100%. Off Shift hoặc Short Break là thời gian nghỉ, Efficiency được đặt 0% nên APS không xếp lịch sản xuất vào khoảng thời gian này. Nguồn file: Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 267
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang phân biệt vai trò WMS và Matecon khi ACR không lấy được ORICON.
- Cách hỏi: so sánh
- Hỏi: WMS và Matecon có vai trò khác nhau thế nào trong logistics AMS?
- Đáp: WMS/Inter-Stock quản lý thông tin tồn kho và tọa độ kệ. Matecon là tầng điều khiển vận chuyển, nhận chỉ thị từ WMS/MOM và điều khiển ACR/CTU/AGV thực hiện搬送 vật lý. Khi ACR không lấy được ORICON, cần phân biệt lỗi thông tin tồn kho (WMS) với lỗi điều khiển搬送 (Matecon/thiết bị). Nguồn file: Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 268
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 生产计划已经在APS生成，但现场还没有收到物料。
- Cách hỏi: xử lý sự cố
- Hỏi: 从系统生态来看，不能只检查APS的原因是什么？
- Đáp: 因为物料供给经过多个系统：APS负责工程计划和供给计划，MOM／Opcenter生成并管理生产执行与出库要求，WMS管理库存和货架位置，Matecon再控制ACR／CTU／AGV实际搬送。因此APS有计划但现场无料时，需要按链路逐段排查，而不只是看APS。来源文件：Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 269
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在说明PLM到现场制造的基本数据链。
- Cách hỏi: trực tiếp
- Hỏi: Teamcenter中的数据如何与MOM制造执行关联？
- Đáp: 资料说明Teamcenter集中管理EBOM、MBOM和BOP。EBOM从CAD设计数据形成，MBOM根据制造条件展开，BOP把部品结构与工程、Work Center及BOE等制造信息连接起来，再联携到MOM／Opcenter执行生产。来源文件：Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 270
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为MOM只是一个生产实绩数据库。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: MOM只是一个保存生产实绩的数据库，对吗？
- Đáp: 不对。资料把MOM／Opcenter描述为整个制造生态的核心执行系统，它连接PLM、APS、WMS、搬送控制和现场设备，不仅保存实绩，还参与工程计划执行、物料供给、生产过程、Traceability和品质管理。来源文件：Siêu Báo Cáo - Hệ Sinh Thái MOM & Các Vệ Tinh (Kyocera KDTVN).

## CÂU HỎI 271
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 数据库工程师需要确认品质异常与Traceability的关联字段。
- Cách hỏi: trực tiếp
- Hỏi: QualityInformationLinkage和StatusCodeLinkage_Ver00通过什么字段对应？
- Đáp: ERD中定义两者通过QualityInformationLinkage.S_NO = StatusCodeLinkage_Ver00.NO进行关联。前者保存不良、原因、处置和QC状态，后者保存生产Traceability信息。来源文件：ERD_Kho_Van_NEW.html.

## CÂU HỎI 272
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 手动出库后实物没有搬走，工程师检查T_PARTS_OUT。
- Cách hỏi: tình huống
- Hỏi: 在T_PARTS_OUT中可以用哪些Flag判断搬送进度？
- Đáp: 可检查MOVE_ORDER_FLG、MOVE_FIN_FLG和DELIVERY_FIN_FLG。此外还有GATEOUT_ORDER_TIME及DATA_IF_TIME1、DATA_IF_TIME2等时间字段，可追踪从指示发行到完成的狀態。来源文件：ERD_Kho_Van_NEW.html.

## CÂU HỎI 273
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较工程库存表和出库指示表的Item字段。
- Cách hỏi: so sánh
- Hỏi: 两张表的ITEM_CODE长度一样吗？
- Đáp: 不一样。ProcessInventoryControl.ITEM_CODE定义为varchar(12)，而T_PARTS_OUT.ITEM_CODE为varchar(20)。进行接口开发或数据复制时需要注意长度差异，避免截断。来源文件：ERD_Kho_Van_NEW.html.

## CÂU HỎI 274
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 出庫IFでMOVE_ORDER_FLGへ文字列を設定するProgramを確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: MOVE_ORDER_FLGにONを書き込む設計は問題ありませんか。
- Đáp: 問題があります。ERDではMOVE_ORDER_FLGはvarchar(1)です。2文字のONを入れるとLength超過となり、資料ではString or binary data would be truncatedエラーの例が示されています。1文字のFlag値を設計する必要があります。出典ファイル：ERD_Kho_Van_NEW.html.

## CÂU HỎI 275
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: AGVの現在位置と看板表示が一致しないためDBを照合している。
- Cách hỏi: tình huống
- Hỏi: KanbanとAGV状態TableはどのFieldで紐付けますか。
- Đáp: ERDではKanbanTable.AGV = T_MAIN_PROCESS.MACHINE_NUMBERで関連付けています。T_MAIN_PROCESS側ではADDRESS、CELL、PROCESS_STATUSなどでAGVの現在状態を確認できます。出典ファイル：ERD_Kho_Van_NEW.html.

## CÂU HỎI 276
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 工程在庫と出庫指示のDB関係を新人に説明している。
- Cách hỏi: trực tiếp
- Hỏi: ProcessInventoryControlとT_PARTS_OUTは何で関連付けられていますか。
- Đáp: ERD上ではPO_NOで直接関連付けています。両TableにはPO番号だけでなく、PO_DETAIL_NO、PO_SEP_KEY、CASE_SEQNO、Item Revision、ORICON IDなど、出庫／在庫追跡に使える関連項目も存在します。出典ファイル：ERD_Kho_Van_NEW.html.

## CÂU HỎI 277
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 品質履歴側とTraceability側でProcess IDを連携するProgramを設計している。
- Cách hỏi: so sánh
- Hỏi: 両TableのPROCESS_IDは同じLengthですか。
- Đáp: 同じではありません。QualityInformationLinkage.PROCESS_IDはvarchar(20)ですが、StatusCodeLinkage_Ver00.PROCESS_IDはvarchar(16)です。連携ProgramではLength差異によるTruncateに注意が必要です。出典ファイル：ERD_Kho_Van_NEW.html.

## CÂU HỎI 278
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn tra trạng thái AGV đang đứng ở địa chỉ nào và thuộc cell nào.
- Cách hỏi: trực tiếp
- Hỏi: Bảng nào chứa trạng thái trực tiếp của AGV và các trường chính là gì?
- Đáp: Bảng T_MAIN_PROCESS lưu trạng thái AGV. Các trường chính gồm MACHINE_NUMBER là mã AGV, ADDRESS là địa chỉ hiện tại, CELL là tên cell/công đoạn, PROCESS_STATUS là trạng thái, SEQ là số thứ tự. Nguồn file: ERD_Kho_Van_NEW.html.

## CÂU HỎI 279
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần theo dõi một ORICON từ tồn kho công đoạn sang lệnh xuất.
- Cách hỏi: tình huống
- Hỏi: Những trường nào có thể dùng để đối chiếu cùng một thùng giữa tồn kho và xuất kho?
- Đáp: Ngoài quan hệ chính qua PO_NO, cả ProcessInventoryControl và T_PARTS_OUT đều có các thông tin như PO_DETAIL_NO, PO_SEP_KEY, CASE_SEQNO, ITEM_CODE, ITEM_REV, ORICON_ID để đối chiếu cùng một thùng giữa tồn kho công đoạn và lệnh xuất kho. Nguồn file: ERD_Kho_Van_NEW.html.

## CÂU HỎI 280
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới nhìn sơ đồ ERD và cho rằng mọi đường nối đều là Foreign Key thật trong SQL Server.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Có thể khẳng định mọi quan hệ vẽ trong ERD_Kho_Van_NEW.html đều đã được tạo thành Foreign Key Constraint trong DB không?
- Đáp: Không thể khẳng định chỉ từ file này. ERD mô tả các quan hệ logic như S_NO = NO, liên kết qua PO_NO, AGV = MACHINE_NUMBER, nhưng file không cung cấp DDL hay định nghĩa Foreign Key Constraint vật lý. Phần này cần đánh dấu "chưa xác nhận" và kiểm tra DB thực tế. Nguồn file: ERD_Kho_Van_NEW.html.

---

## PHẦN B — Nội dung 2 thư mục con (do ChatGPT liệt kê 2026-10-04)
1) 仕様書 — 6 thư mục con: マテハン, WMS, PLM, MOM周辺, オリコン, K… (tên mục 6 bị che khuất, chưa đọc được đầy đủ)
2) WMS — 16 file ảnh chụp màn hình: Screenshot 2026-03-20 183202.png … 184246.png (16 file)
