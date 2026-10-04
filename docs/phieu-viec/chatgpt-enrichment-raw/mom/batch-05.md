# Mẻ MOM 05 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Tài liệu: (24) Lưu trình_lỗi phát sinh khi sản xuất AMS.txt, (25) ERD_Kho_Van.html, (26) ORICON_STATUS_早見表_検証済み版.pdf, (27) 生産履歴登録システム_変更確認チェックリスト_20260914.xlsx, (28) ORICON STAUS早見表.xlsx
Không có file bị bỏ qua/thay thế.

## CÂU HỎI 201
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra lỗi MOM→R3 khi một lệnh sản xuất có khoảng 150 linh kiện tiêu hao.
- Cách hỏi: trực tiếp
- Hỏi: Vì sao dữ liệu thực tích tiêu hao khoảng 150 item có thể không insert được vào T_IF_PROD_RESULT?
- Đáp: Trong stored procedure tạo XML, dữ liệu đang được ép kiểu nvarchar(4000). Khi VN liên kết khoảng 150 item tiêu hao, XML vượt 4000 ký tự nên xử lý lỗi trước khi ghi vào bảng. Bản thân cột T_IF_PROD_RESULT là NVARCHAR(MAX), nên điểm cần kiểm tra không chỉ là kiểu dữ liệu của bảng mà còn là biến và kiểu dữ liệu trung gian trong stored procedure. Nguồn file: Lưu trình_lỗi phát sinh khi sản xuất AMS.txt.

## CÂU HỎI 202
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Mfg Order chưa Complete sau khi ST và CO đều đã đăng ký.
- Cách hỏi: xử lý sự cố
- Hỏi: Theo lưu trình ST→CO, cần kiểm tra lần lượt các bước nào để tìm vị trí đang bị dừng?
- Đáp: Chuỗi kiểm tra gồm: ① kế hoạch công đoạn vào ScheduledProductionOrderInfo; ② đăng ký ST; ③ Container Start trên Opcenter; ④ đăng ký CO; ⑤ Opcenter hoàn tất thu thập thực tích; ⑥ Mfg Order chuyển complete; ⑦ dữ liệu MES tiến độ được ghi vào T_IF_PROD_RESULT; ⑧ MES tiến độ nhận hoàn thành chỉ thị; ⑨ tạo kế hoạch tiếp theo. Nếu Mfg Order chưa Complete thì đặc biệt kiểm tra bước ⑤ trước, vì thực tích dừng giữa chừng sẽ làm bước ⑥ không hoàn thành. Nguồn file: Lưu trình_lỗi phát sinh khi sản xuất AMS.txt.

## CÂU HỎI 203
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Toàn line đột ngột không thu thập được thực tích dù ST/CO vẫn thao tác được.
- Cách hỏi: tình huống
- Hỏi: Ngoài dữ liệu sản xuất, cần kiểm tra những thành phần hệ thống nào?
- Đáp: Tài liệu nêu case ngày 15/07/2026 có liên quan MIO, license và CNMOM. Cần kiểm tra trạng thái MIO Server, license của MIO/CEP2004, BrokerTxnDate trong StagingDB, log CNMOM và MaterialQueue được gửi trong XML. Có trường hợp license sai thời hạn làm MIO không chạy, và trường hợp XML gửi tới MaterialQueue chưa được modeling gây lỗi move-in. Nguồn file: Lưu trình_lỗi phát sinh khi sản xuất AMS.txt.

## CÂU HỎI 204
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较数据库字段容量与Stored Procedure中的变量容量。
- Cách hỏi: so sánh
- Hỏi: T_IF_PROD_RESULT的字段容量和XML生成程序中的容量有什么区别？
- Đáp: T_IF_PROD_RESULT数据库字段本身是NVARCHAR(MAX)，资料说明理论上可保存非常大的文字量；但生成XML的Stored Procedure中曾使用nvarchar(4000)，因此约150个部品消耗实绩时XML超过4000字符，就在写入表之前发生错误。也就是说，目标表足够大并不代表中间变量不会截断。来源文件：Lưu trình_lỗi phát sinh khi sản xuất AMS.txt。

## CÂU HỎI 205
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: CTU读取T_PARTS_OUT后无法找到交货地点。
- Cách hỏi: xử lý sự cố
- Hỏi: 出库指示中SUP_PROCESS错误时应该从哪些地方开始核对？
- Đáp: 应核对MOM/BOP-MOM中的WorkCenter、T_PARTS_OUT中的SUP_PROCESS、Matecon/CTU的Mapping以及Stand棚位置。如果BOP-MOM联携时WorkCenter被错误变更，SUP_PROCESS也可能错误；即使MOM上的SUP_PROCESS正确，如果Matecon侧没有相应Mapping，CTU仍然无法确定交货坐标。来源文件：Lưu trình_lỗi phát sinh khi sản xuất AMS.txt。

## CÂU HỎI 206
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 某一条错误出库记录卡在Queue前端，后面的正常指示也不执行。
- Cách hỏi: tình huống
- Hỏi: 为什么一条错误记录可能影响后续正常出库？
- Đáp: 资料记录，当错误指示无法完成时，DELIVERY_FIN_FLG不会变成1，该记录可能停留在Queue前端并阻塞后续有效指示。因此不能只确认"是否有出库计划"，还要检查Queue前端是否存在未完成错误记录以及DELIVERY_FIN_FLG状态。来源文件：Lưu trình_lỗi phát sinh khi sản xuất AMS.txt。

## CÂU HỎI 207
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人看到MES进度未完成，就直接判断为MES侧故障。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: MES进度没有显示完成，就可以直接判定MES进度系统本身有问题吗？
- Đáp: 不可以。应从ST→Container Start→CO→Opcenter实绩收集→Mfg Order Complete→T_IF_PROD_RESULT→MES进度逐步反查。资料中既有Opcenter实绩中途停止，也有Mfg Order不Complete、T_IF_PROD_RESULT未登记以及MES进度未接收完成的不同故障点。来源文件：Lưu trình_lỗi phát sinh khi sản xuất AMS.txt。

## CÂU HỎI 208
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: MIO復旧後に同じ問題が再発しないか確認している。
- Cách hỏi: trực tiếp
- Hỏi: MIO／CEP2004のLicense問題では、どのような対応で復旧しましたか。
- Đáp: 資料では、適用していたLicenseの有効期限設定に問題がある可能性があり、Licenseを再発行して再適用した後、MIOが再び動作したと記録されています。復旧確認ではMIO Server状態、License、StagingDBのBrokerTxnDateも確認対象です。出典ファイル：Lưu trình_lỗi phát sinh khi sản xuất AMS.txt。

## CÂU HỎI 209
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: BOP変更後にCTUが新しい供給場所へ搬送できなくなった。
- Cách hỏi: so sánh
- Hỏi: MOM側のWorkCenter更新とMatecon側Mapping更新は同じ作業ですか。
- Đáp: 同じではありません。BOP-MOM側ではWorkCenter／供給場所がSUP_PROCESSの元になります。一方、Matecon／CTU側ではそのSUP_PROCESSに対応する搬送先Mappingが必要です。MOM側だけ更新してMatecon Mappingが旧状態のままだと、CTUは搬送先を特定できません。出典ファイル：Lưu trình_lỗi phát sinh khi sản xuất AMS.txt。

## CÂU HỎI 210
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者がXML長エラーの原因をDB Column不足と説明している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: XMLが4000文字を超えたエラーは、T_IF_PROD_RESULT列が4000文字制限だから発生したのですか。
- Đáp: いいえ。資料ではT_IF_PROD_RESULT自体はNVARCHAR(MAX)です。問題はXML生成処理のStored Procedure内でnvarchar(4000)を指定していたことです。約150品目の消費実績でXMLが4000文字を超えた時に、その中間処理でErrorになりました。出典ファイル：Lưu trình_lỗi phát sinh khi sản xuất AMS.txt。

## CÂU HỎI 211
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: DB担当者が品質異常の履歴テーブル構造を確認している。
- Cách hỏi: trực tiếp
- Hỏi: QualityInformationLinkageにはどのような主な項目がありますか。
- Đáp: 主な項目はID、DATE_TIME、S_NO、LATEST_FLAG、PROCESS_ID、DEFECT_ITEM_01、DEFECT_ITEM_02、CAUSE、TREATMENT、MANAGER、STATUS、DETAILです。S_NOは機番を表し、ERDではStatusCodeLinkage_Ver00.NOと関連付けられています。出典ファイル：ERD_Kho_Van.html。

## CÂU HỎI 212
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 工程在庫から出庫指示へ追跡するため、DB関係を確認している。
- Cách hỏi: tình huống
- Hỏi: ProcessInventoryControlとT_PARTS_OUTは何をキーに関連付けていますか。
- Đáp: ERDではProcessInventoryControlとT_PARTS_OUTをPO_NOで直接関連付けています。両方にPO_NOがあり、さらにPO_DETAIL_NO、PO_SEP_KEY、CASE_SEQNO、Item、ORICONなど、出庫／在庫追跡に使える関連項目も存在します。出典ファイル：ERD_Kho_Van.html。

## CÂU HỎI 213
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 出庫指示が作成されているが搬送完了にならない。
- Cách hỏi: xử lý sự cố
- Hỏi: T_PARTS_OUTで出庫・搬送状態を調べる時、どのFlagを確認できますか。
- Đáp: ERDにはMOVE_ORDER_FLG（移動指示Flag）、MOVE_FIN_FLG（移動完了Flag）、DELIVERY_FIN_FLG（配送完了Flag）が定義されています。またGATEOUT_ORDER_TIMEや複数のDATA_IF_TIMEもあるため、指示発行から完了までの状態と時刻を追跡できます。出典ファイル：ERD_Kho_Van.html。

## CÂU HỎI 214
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư lập trình chuẩn bị ghi giá trị trạng thái vào MOVE_ORDER_FLG.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Có thể ghi chuỗi "ON" vào MOVE_ORDER_FLG để dễ đọc hơn không?
- Đáp: Không. ERD định nghĩa MOVE_ORDER_FLG là varchar(1), chỉ cho phép độ dài 1 ký tự. File còn minh họa rằng nếu gửi "ON" gồm 2 ký tự, DB có thể báo lỗi String or binary data would be truncated. Nguồn file: ERD_Kho_Van.html.

## CÂU HỎI 215
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần phân biệt dữ liệu tồn kho công đoạn và dữ liệu lệnh xuất kho.
- Cách hỏi: so sánh
- Hỏi: ProcessInventoryControl và T_PARTS_OUT lưu thông tin khác nhau thế nào?
- Đáp: ProcessInventoryControl tập trung vào tồn kho như SUP_LINE, PROCESS_ID, ITEM_CODE, ITEM_REV, ORICON_ID, PO, QTY, STATUS, CHECK_QTY. T_PARTS_OUT tập trung vào lệnh cấp/xuất như SUP_PROCESS, thời gian ra lệnh, OUT_SHELF, trọng lượng ORICON, các thời điểm interface, MOVE_ORDER_FLG, MOVE_FIN_FLG và DELIVERY_FIN_FLG. Nguồn file: ERD_Kho_Van.html.

## CÂU HỎI 216
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: QC cần đối chiếu Line-Out với lịch sử sửa chữa của cùng một máy.
- Cách hỏi: tình huống
- Hỏi: Trong ERD, bảng chất lượng được liên kết với bảng traceability bằng trường nào?
- Đáp: ERD định nghĩa QualityInformationLinkage }|--|| StatusCodeLinkage_Ver00 với quan hệ S_NO = NO. Vì vậy khi tra lịch sử một máy, có thể dùng QualityInformationLinkage.S_NO để đối chiếu với StatusCodeLinkage_Ver00.NO. Nguồn file: ERD_Kho_Van.html.

## CÂU HỎI 217
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要查看AGV当前状态对应的数据库结构。
- Cách hỏi: trực tiếp
- Hỏi: T_MAIN_PROCESS中保存哪些主要AGV状态信息？
- Đáp: T_MAIN_PROCESS包含MACHINE_NUMBER、ADDRESS、CELL、PROCESS_STATUS和SEQ。其中MACHINE_NUMBER为AGV编号主键，ADDRESS表示当前位置，CELL表示工程名称，PROCESS_STATUS是状态Flag，SEQ为顺序值。来源文件：ERD_Kho_Van.html。

## CÂU HỎI 218
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 看板上的AGV编号与车辆状态记录不一致。
- Cách hỏi: xử lý sự cố
- Hỏi: Kanban与AGV状态表之间应如何关联检查？
- Đáp: ERD中KanbanTable与T_MAIN_PROCESS通过AGV编号关联，关系说明为AGV = MACHINE_NUMBER。因此可比较KanbanTable.AGV与T_MAIN_PROCESS.MACHINE_NUMBER，同时查看Kanban的STATE以及车辆的PROCESS_STATUS、ADDRESS等。来源文件：ERD_Kho_Van.html。

## CÂU HỎI 219
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Traceability表与品质表的数据长度限制。
- Cách hỏi: so sánh
- Hỏi: StatusCodeLinkage_Ver00.PROCESS_ID和QualityInformationLinkage.PROCESS_ID长度一样吗？
- Đáp: 不一样。ERD中StatusCodeLinkage_Ver00.PROCESS_ID为varchar(16)，而QualityInformationLinkage.PROCESS_ID为varchar(20)。进行程序联携或数据复制时，需要注意这两个字段长度并不相同。来源文件：ERD_Kho_Van.html。

## CÂU HỎI 220
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为ERD中的关系都代表数据库真实Foreign Key约束。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: ERD画出的业务关联就一定代表数据库中已经建立了物理Foreign Key吗？
- Đáp: 文件只明确画出了关系，例如S_NO = NO、PO_NO、AGV = MACHINE_NUMBER等业务关联，但没有给出实际数据库DDL或Foreign Key Constraint定义。因此只能确认ERD中的关联设计，不能仅凭该HTML断定所有关系都已作为物理FK约束建立。此部分应标记为"尚未确认"。来源文件：ERD_Kho_Van.html。

## CÂU HỎI 221
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên kho nhận ORICON_STATUS và cần xác định bit lỗi đang bật.
- Cách hỏi: trực tiếp
- Hỏi: ORICON STATUS được mã hóa theo cấu trúc bao nhiêu bit và đọc từ phía nào?
- Đáp: ORICON STATUS là chuỗi HEX 16 chữ số, tương đương 64 bit. Chữ số HEX ngoài cùng bên phải tương ứng Bit 0–3, còn chữ số HEX ngoài cùng bên trái tương ứng Bit 60–63. File gốc chuyển giá trị HEX thành từng bit và đánh dấu các bit có giá trị 1. Nguồn file: ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 222
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: ORICON hiển thị 全OK nhưng thực tế chưa vào được kho tự động.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 全OK trong ORICON STATUS có nghĩa toàn bộ quá trình nhập kho Opcenter–InterStock–ACR đã hoàn thành không?
- Đáp: Không. Tài liệu ghi rõ 全OK chỉ là kết quả phán định của ORICON STATUS và không bảo đảm toàn bộ quá trình nhập kho gồm Opcenter, InterStock và ACR đã hoàn thành. Nếu ORICON vẫn chưa vào kho cần kiểm tra tiếp các hệ thống sau gate. Nguồn file: ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 223
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Gate báo 0201000010000000 và kỹ sư cần giải thích các bit lỗi.
- Cách hỏi: tình huống
- Hỏi: STATUS 0201000010000000 tương ứng những bit và lỗi nào?
- Đáp: Theo phép giải mã trong bản kiểm chứng, các bit bật là 28, 48, 57, tương ứng 照合RFID_NG, CAM処理失敗 và 格納指示FLG_Error. Vì vậy không nên chỉ mô tả đây là một lỗi RFID đơn lẻ. Nguồn file: ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 224
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người vận hành phân biệt lỗi QR mặt trước và mặt sau.
- Cách hỏi: so sánh
- Hỏi: Bit 29 và Bit 30 khác nhau thế nào?
- Đáp: Bit 29 là 照合QR前_NG, tức đối chiếu QR mặt trước NG; xử lý là kiểm tra QR phía trước rồi đưa ORICON vào gate lại. Bit 30 là 照合QR後_NG, tức đối chiếu QR mặt sau NG; xử lý tương tự nhưng tập trung vào QR phía sau. Nguồn file: ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 225
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: Gate出现4200000000000000，工程师准备按VendorShippingInfo不一致处理。
- Cách hỏi: xử lý sự cố
- Hỏi: 4200000000000000可以直接认定为VendorShippingInfo不一致吗？
- Đáp: 不能完全直接认定。资料下方示例写成"VendorShippingInfoとの照合不一致"，但按原Excel公式展开后实际Bit 57和Bit 62为1，分别是格納指示FLG_Error和MPI-010NG Result=-1 or ShippingData=2。而VendorShippingInfo详细注记又出现在Bit 37，因此文件明确要求正式规格需向系统负责人确认。来源文件：ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 226
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: ORICON Gate读取现品票失败。
- Cách hỏi: trực tiếp
- Hỏi: Bit 8和Bit 9分别代表什么？
- Đáp: Bit 8为現品票読込NG，处理是确认QR是否异常后重新投入ORICON Gate；Bit 9为RFID読込みNG，处理是确认RFID异常后重新投入Gate。来源文件：ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 227
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: EDI现品票与Vendor现品票品目不一致。
- Cách hỏi: tình huống
- Hỏi: 哪个Bit表示EDI与Vendor现品票品目不一致，应如何处理？
- Đáp: Bit 35为EDI_ベンダー現品票品目不一致。资料要求确认EDI现品票与Vendor现品票内容是否一致，然后重新投入ORICON Gate。来源文件：ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 228
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 重量判定NGの内容を切り分けている。
- Cách hỏi: so sánh
- Hỏi: Bit 49、50、51はどのように違いますか。
- Đáp: Bit 49は重量_箱入数不一致、Bit 50は重量_重量不一致、Bit 51は重量_処理失敗です。Bit 50と51については資料にOpcenter状態確認必要と記載されています。出典ファイル：ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 229
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: STATUS解析で格納指示関連のErrorを確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: Bit 57が1の場合、何を意味しますか。
- Đáp: Bit 57は格納指示FLG_Errorで、資料には「OK時はHOUSE_ORDERに書込み」と記載されています。処置はOpcenter状態の確認です。したがって、Gate側だけでなくOpcenter側の格納指示処理も確認します。出典ファイル：ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 230
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人がORICON STATUSの説明文だけを見て原因を確定しようとしている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: STATUSのサンプル説明とbit展開結果が違う場合、説明文をそのまま正式仕様として使ってよいですか。
- Đáp: いいえ。検証済み版では4200000000000000の説明とbit位置に不一致があることを明記し、正式仕様はシステム担当者への確認が必要としています。説明文、bit展開、個別bit注記が一致しない場合は「未確認」として扱う必要があります。出典ファイル：ORICON_STATUS_早見表_検証済み版.pdf.

## CÂU HỎI 231
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新版本生产履历登记系统开始验证前，负责人确认测试范围。
- Cách hỏi: trực tiếp
- Hỏi: 测试用生产指令准备多少个、多少台？
- Đáp: 在C3B Line准备2个测试指令：302XD93101为2台，302YL93021为2台，总计4台。APS只制作工程计划，不制作自动出库计划，并且这4台不计入实际生产数量。来源文件：生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 232
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: ST登记完成后，工程师需要验证数据库记录是否正确。
- Cách hỏi: tình huống
- Hỏi: ST后在StatusCodeLinkage_Ver00要检查哪些内容？
- Đáp: 要确认STATUS1 = ST，并检查登记时间、Line、Process ID和Serial No.是否正确。计划时间为8:35，在此之前8:30完成4台测试机的ST登记。来源文件：生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 233
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在比较ST验证和CO验证项目。
- Cách hỏi: so sánh
- Hỏi: ST数据确认和CO数据确认的检查项有什么差别？
- Đáp: ST确认要求STATUS1 = ST，并检查登记时间、Line、Process ID和Serial No.；CO确认要求STATUS1 = CO，并检查登记时间、Process ID和Serial No.。此外，ST后还单独确认Container是否进入正确的Process ID、Unit／Phantom和工程。来源文件：生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 234
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 测试开始后出现严重问题，需要决定是否继续新版本。
- Cách hỏi: xử lý sự cố
- Hỏi: 新版本出现问题时，Checklist规定如何准备回退？
- Đáp: 在验证开始前8:00就要与CN侧确认旧版本回退步骤。验证完成后13:00根据结果决定继续使用新版本还是回退旧版本。因此回退方案必须在测试前准备，而不是出问题后才临时决定。来源文件：生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 235
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: マニュアル出庫検証で実在庫への影響を避けたい。
- Cách hỏi: trực tiếp
- Hỏi: マニュアル出庫テストでは何を使用しますか。
- Đáp: 実在庫へ影響させないため、ダミー現品票と試験用オリコンを使用します。その後、Item、C3B、供給場所を選択してマニュアル出庫を登録します。出典ファイル：生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 236
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: マニュアル出庫登録後にStaging DBと出庫Tableを照合している。
- Cách hỏi: tình huống
- Hỏi: アプリ入力後、どの2段階で登録内容を確認しますか。
- Đáp: まずManualShipping_ExistingLineAuto_InboundDownloadで、入力したItem、Line、供給場所が正しく登録されていることを確認します。次にT_PARTS_OUTで、出庫指示、対象ORICON、棚番、供給先が正しいことを確認します。出典ファイル：生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 237
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: FIFO検証と出庫指示確認を同じ作業だと思っている新人へ説明している。
- Cách hỏi: so sánh
- Hỏi: T_PARTS_OUT確認とFIFO確認は同じ検証ですか。
- Đáp: 同じではありません。T_PARTS_OUT確認では出庫指示が生成され、ORICON、棚番、供給先が正しいことを確認します。FIFO確認ではOpcenter画面のORICON表示順と、実際に出庫対象として選択されたORICONがFIFO順になっているかを照合します。出典ファイル：生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 238
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn test xuất kho nhưng không muốn ORICON đi qua gate thật.
- Cách hỏi: xử lý sự cố
- Hỏi: Checklist yêu cầu dừng ORICON ở đâu trong test manual xuất kho?
- Đáp: Sau khi xác nhận lệnh xuất, ORICON phải được lấy khỏi băng tải trước khi đi qua cổng xuất. Hạng mục này dự kiến lúc 10:15, nhằm kiểm tra logic xuất kho mà không để luồng test tiếp tục ảnh hưởng hệ thống kho thực tế. Nguồn file: 生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 239
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kết thúc test 4 máy, kỹ sư chuẩn bị trả line về vận hành thật.
- Cách hỏi: tình huống
- Hỏi: Sau kiểm chứng cần dọn những dữ liệu nào trước khi sản xuất lại?
- Đáp: IT phải xóa thực tích của 2 lệnh, tổng 4 máy test trong MES SHINDO để không ảnh hưởng tiến độ và sản lượng. Sau đó kiểm tra Opcenter/WMS không còn Container test, tồn kho test hoặc chỉ thị xuất không cần thiết. Trước khi line C3B sản xuất lại khoảng 14:00, phải xác nhận ứng dụng, PLC và các hệ thống liên quan sử dụng được. Nguồn file: 生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 240
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới định tạo luôn kế hoạch xuất kho tự động trên APS cho 4 máy test.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Trong bài test này có được tạo kế hoạch xuất kho tự động APS không?
- Đáp: Không. Checklist quy định chỉ tạo kế hoạch công đoạn cho 2 lệnh test, tổng 4 máy; không tạo kế hoạch xuất kho tự động APS. Trước khi test còn phải xác nhận ScheduledProductionOrderInfo có Serial và dữ liệu kế hoạch công đoạn nhưng không có kế hoạch xuất tự động. Nguồn file: 生産履歴登録システム_変更確認チェックリスト_20260914.xlsx.

## CÂU HỎI 241
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư nhập một chuỗi ORICON STATUS vào file Excel để xem bit lỗi.
- Cách hỏi: trực tiếp
- Hỏi: File ORICON STAUS早見表.xlsx xử lý giá trị STATUS theo độ dài bao nhiêu bit?
- Đáp: File ghi データ長64bit, tức dữ liệu dài 64 bit. Bảng chia theo DM4590 đến DM4593, tương ứng các nhóm Bit 0–15, 16–31, 32–47 và 48–63. Nguồn file: ORICON STAUS早見表.xlsx.

## CÂU HỎI 242
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Gate báo lỗi đọc phiếu hiện vật và công nhân cần biết thao tác nhanh.
- Cách hỏi: tình huống
- Hỏi: Bit 8 現品票読込NG thì thao tác đối ứng được ghi thế nào?
- Đáp: Kiểm tra QR trên phiếu hiện vật có bất thường hay không, sau đó đưa ORICON vào lại ORICON Gate. Bit 8 thuộc nhóm DM4590. Nguồn file: ORICON STAUS早見表.xlsx.

## CÂU HỎI 243
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn phân biệt lỗi đọc RFID ban đầu và lỗi đối chiếu RFID.
- Cách hỏi: so sánh
- Hỏi: Bit 9 và Bit 28 đều liên quan RFID nhưng khác nhau thế nào?
- Đáp: Bit 9 là RFID読込みNG, tức lỗi ngay ở bước đọc RFID. Bit 28 là 照合RFID_NG, tức dữ liệu RFID đã đi tới bước đối chiếu nhưng kết quả so khớp NG. Cả hai đều yêu cầu kiểm tra RFID và tái đưa ORICON vào gate, nhưng vị trí lỗi trong luồng xử lý khác nhau. Nguồn file: ORICON STAUS早見表.xlsx.

## CÂU HỎI 244
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: MPI-010相关错误出现，工程师判断是否只检查Gate硬件。
- Cách hỏi: xử lý sự cố
- Hỏi: Bit 36、37出现时应该检查什么系统？
- Đáp: Bit 36为MPI-010_Shipping_Data_NG，Bit 37为MPI-010_NG，两者处理栏都要求确认Opcenter状态。Bit 37还注明可能是VendorShippingInfo表数据与EDI现品票Lot信息或Vendor现品票生产日信息不一致，并要求联系IE。来源文件：ORICON STAUS早見表.xlsx.

## CÂU HỎI 245
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人看到Bit 55后认为是系统错误。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Bit 55 格納方法_検査へ一定代表错误吗？
- Đáp: 不能这样理解。Bit 55的内容是格納方法_検査へ（HOUSE_METHODに書込み），文件没有在处理栏标记"Opcenter状态确认必要"。它表示格纳方式进入检查方向，与Bit 56的格納方法_Error不同。来源文件：ORICON STAUS早見表.xlsx.

## CÂU HỎI 246
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较格纳方式错误和格纳指示Flag错误。
- Cách hỏi: so sánh
- Hỏi: Bit 56和Bit 57分别表示什么？
- Đáp: Bit 56为格納方法_Error，Bit 57为格納指示FLG_Error，后者注记"OK时写入HOUSE_ORDER"。两个Bit的处理栏都要求确认Opcenter状态。来源文件：ORICON STAUS早見表.xlsx.

## CÂU HỎI 247
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 输入示例0205000010000000后，工程师要理解其代表的业务现象。
- Cách hỏi: tình huống
- Hỏi: Excel原表把0205000010000000标记为什么异常？
- Đáp: 原表下方示例将0205000010000000标记为重量不一致。对应Bit表中与重量有关的项目包括Bit 49箱入数不一致、Bit 50重量不一致、Bit 51重量处理失败；若要确认该16进制值实际展开哪些Bit，应以Excel公式展开结果为准。来源文件：ORICON STAUS早見表.xlsx.

## CÂU HỎI 248
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: EDI現品票が複数枚あるためGateでNGになった。
- Cách hỏi: trực tiếp
- Hỏi: Bit 26の内容と処置は何ですか。
- Đáp: Bit 26は1枚_EDI現品票_NGです。処置はEDI現品票を1枚にして、ORICON Gateへ再投入することです。出典ファイル：ORICON STAUS早見表.xlsx.

## CÂU HỎI 249
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: EDI現品票にLot情報がない部品をGateへ投入している。
- Cách hỏi: xử lý sự cố
- Hỏi: Bit 27が発生した場合、何を確認しますか。
- Đáp: Bit 27は1枚_ベンダー現品票_NGです。原表注記では、EDI現品票にLot情報がない場合はVendor現品票が必要です。Vendor現品票QRに異常がないか確認し、ORICON Gateへ再投入します。出典ファイル：ORICON STAUS早見表.xlsx.

## CÂU HỎI 250
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者がExcel下部のSTATUS説明だけを見て原因判定しようとしている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 下部サンプルの説明だけで、16進STATUSの全Error内容を確定できますか。
- Đáp: いいえ。Excelは64bitの各Bitを展開して該当内容を判定する構造です。例えば一つのHEX値で複数Bitが1になる場合があります。そのため、サンプル説明だけでなく、HEX→BIN展開と各Bitの内容を確認する必要があります。出典ファイル：ORICON STAUS早見表.xlsx.
