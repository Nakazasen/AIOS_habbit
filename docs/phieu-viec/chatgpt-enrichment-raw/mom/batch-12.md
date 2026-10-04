# Mẻ MOM 12 — 10 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
File: 仕様書/MOM/MOMのRevUp手作業方法_20260324.pptx, câu 529–538. Không file nào bị bỏ qua.
Phần A — listing mới: オリコン (通函管理システム.pptx, 通函管理流れ.pptx, Link); AMS以外のラインからの出庫指示 (4 xlsx + Link).

## CÂU HỎI 529
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư MOM chuẩn bị thực hiện RevUp thủ công sau khi dữ liệu version mới đã được chuẩn bị.
- Cách hỏi: trực tiếp
- Hỏi: RevUp thủ công trong tài liệu yêu cầu thay đổi những đối tượng nào?
- Đáp: Tài liệu ghi rõ 変更内容は３つ: Workflow, ERP Route và ERP BOM. Đây là ba đối tượng cần thực hiện thao tác RevUp thủ công theo hướng dẫn. Nguồn file: MOMのRevUp手作業方法_20260324.pptx.

## CÂU HỎI 530
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师第一次执行MOM手工RevUp，需要确认基本操作顺序。
- Cách hỏi: trực tiếp
- Hỏi: 手工RevUp的4个操作步骤是什么？
- Đáp: 资料规定4个步骤：①打开目标Modeling；②打开目标Rev；③勾选IsROR；④点击Save按钮。来源文件：MOMのRevUp手作業方法_20260324.pptx.

## CÂU HỎI 531
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 対象Revisionを変更する前に、操作順を確認している。
- Cách hỏi: tình huống
- Hỏi: 最初にRevを直接開けばよいですか。
- Đáp: 資料の順序では、まず対象のModelingを開く、その後に対象のRevを開くとなっています。Revを開く前に対象Modelingを選択する手順です。出典ファイル：MOMのRevUp手作業方法_20260324.pptx.

## CÂU HỎI 532
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đã mở đúng Modeling và Revision nhưng chưa biết cần đổi thuộc tính nào.
- Cách hỏi: xử lý sự cố
- Hỏi: Sau khi mở đúng Rev, thuộc tính nào phải được thao tác?
- Đáp: Bước thứ 3 là đánh dấu IsROR. Sau đó phải thực hiện bước thứ 4 là nhấn Save để lưu thay đổi. Nguồn file: MOMのRevUp手作業方法_20260324.pptx.

## CÂU HỎI 533
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为Workflow RevUp与ERP Route／ERP BOM使用完全不同的手工流程。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Workflow、ERP Route和ERP BOM分别需要不同的4套操作步骤，对吗？
- Đáp: 资料没有这样区分。文件列出3个变更对象Workflow / ERP Route / ERP BOM，同时统一说明4个操作：打开目标Modeling、打开目标Rev、勾选IsROR、Save。因此不能从该文件推断三种对象存在不同操作流程。来源文件：MOMのRevUp手作業方法_20260324.pptx.

## CÂU HỎI 534
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: RevUp作業でIsROR設定と保存処理の役割を区別している。
- Cách hỏi: so sánh
- Hỏi: IsRORにチェックとSaveは同じ操作ですか。
- Đáp: 同じではありません。IsRORにチェックは3番目の操作で、対象Revの設定を変更するStepです。Saveボタンを押すは4番目の操作で、その変更を保存するStepです。出典ファイル：MOMのRevUp手作業方法_20260324.pptx.

## CÂU HỎI 535
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đã tick IsROR nhưng đóng màn hình ngay để chuyển sang object tiếp theo.
- Cách hỏi: xử lý sự cố
- Hỏi: Tick IsROR xong có thể chuyển ngay sang object khác không?
- Đáp: Theo tài liệu thì chưa hoàn tất. Sau bước IsRORにチェック, bước tiếp theo bắt buộc trong quy trình được mô tả là Saveボタンを押す. Vì vậy phải Save trước khi coi thao tác trên Rev đó đã xong. Nguồn file: MOMのRevUp手作業方法_20260324.pptx.

## CÂU HỎI 536
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在确认RevUp对象数量和操作步骤数量，避免漏作业。
- Cách hỏi: so sánh
- Hỏi: "变更对象数量"和"操作步骤数量"分别是多少？
- Đáp: 变更对象有3个：Workflow、ERP Route、ERP BOM。操作步骤有4个：打开Modeling、打开Rev、勾选IsROR、Save。两者是不同概念。来源文件：MOMのRevUp手作業方法_20260324.pptx.

## CÂU HỎI 537
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者がRevUp手作業の完了条件を確認している。
- Cách hỏi: tình huống
- Hỏi: 対象Revを開いただけでRevUp作業完了と判断できますか。
- Đáp: いいえ。対象Revを開くのは2番目の操作です。その後にIsRORにチェックし、最後にSaveする必要があります。出典ファイル：MOMのRevUp手作業方法_20260324.pptx.

## CÂU HỎI 538
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới muốn thêm các bước xóa Revision cũ và tạo Revision mới vào quy trình vì nghĩ đó là RevUp tiêu chuẩn.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File này có yêu cầu xóa Rev cũ hoặc tự tạo Rev mới trước khi tick IsROR không?
- Đáp: Không. Nội dung file chỉ xác nhận 4 thao tác: mở Modeling mục tiêu → mở Rev mục tiêu → tick IsROR → Save. Tài liệu không mô tả bước xóa Rev cũ hay tạo Rev mới, nên các thao tác đó là chưa xác nhận từ nguồn này. Nguồn file: MOMのRevUp手作業方法_20260324.pptx.
