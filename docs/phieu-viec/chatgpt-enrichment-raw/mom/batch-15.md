# Mẻ MOM 15 — 10 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
File: マテコン操作手順書_v001_生産技術 1.xlsx (gốc), câu 599–608. Kết luận: bản tiếng Nhật gốc của TV.xlsx (mẻ 1), cùng spec v0.01 — cần dedup mạnh khi import.
File KDC_AMS pptx: cùng một file ID, chỉ đổi tên — mẻ 1 đã xử lý đúng file. Không có nội dung mới.

## CÂU HỎI 599
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang đối chiếu bản 1.xlsx với TV.xlsx đã dùng trong mẻ 1.
- Cách hỏi: so sánh
- Hỏi: マテコン操作手順書_v001_生産技術 1.xlsx có phải là một spec kỹ thuật khác với bản TV.xlsx không?
- Đáp: Trong phần đối chiếu được, không thấy khác biệt kỹ thuật chính. Cả hai đều là hướng dẫn vận hành マテハンコントローラ（マテコン） cho AGV / ACR / CTU, version 0.01, ngày phát hành đầu tiên 2026-05-01, người lập 堤 和磨 / Kazuma Tsutsumi. Điểm khác rõ nhất là 1.xlsx giữ nội dung tiếng Nhật gốc, còn TV.xlsx là bản tiếng Việt/biên dịch. Nguồn file: マテコン操作手順書_v001_生産技術 1.xlsx, đối chiếu マテコン操作手順書_v001_生産技術 TV.xlsx.

## CÂU HỎI 600
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新工程师准备修改Matecon设定文件。
- Cách hỏi: trực tiếp
- Hỏi: Matecon的Setting文件名有什么规则？
- Đáp: 必须使用PC名 + _Setting.csv，而且文件名必须与实际PC名称一致；不一致时设定文件可能无法正确读取。资料示例PC名为AthenaLSU-MCS。与TV.xlsx对比，此规则相同。来源文件：マテコン操作手順書_v001_生産技術 1.xlsx.

## CÂU HỎI 601
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: KDTVN用Mateconを新規設定している。
- Cách hỏi: tình huống
- Hỏi: locationにはKDTVNの場合どの値を設定しますか。
- Đáp: 4を設定します。定義は0: KDC 枚方LSU、1: KDC 枚方Lab、2: KDC 玉城、3: KDTCN、4: KDTVNです。TV.xlsxでも同じ拠点Code体系です。出典ファイル：マテコン操作手順書_v001_生産技術 1.xlsx.

## CÂU HỎI 602
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Matecon không nhận lệnh từ MOM sau khi chuyển mode để bảo trì.
- Cách hỏi: xử lý sự cố
- Hỏi: Cần kiểm tra ctrlMode như thế nào?
- Đáp: ctrlMode = 0 là 自動生産モード, cho phép giao tiếp với hệ thống cấp trên MOM và thiết bị qua SLMP; Matecon nhận chỉ thị và phát lệnh nhập/xuất cho ACR/CTU. ctrlMode = 1 là マニュアルモード, chặn giao tiếp. Nếu MOM không điều khiển được sau bảo trì, cần xác nhận chưa để nhầm 1. Quy tắc này giống bản TV.xlsx. Nguồn file: マテコン操作手順書_v001_生産技術 1.xlsx.

## CÂU HỎI 603
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较ACR和CTU所需的SQL Table设定。
- Cách hỏi: so sánh
- Hỏi: inventoryTblName和mainProcTblName是否所有Matecon都要设定？
- Đáp: 不是。inventoryTblName只针对Matecon CTU，ACR不在对象范围内；mainProcTblName同样只针对CTU，而且资料注明KDTCNのみ対象。这与TV.xlsx中的技术条件一致。来源文件：マテコン操作手順書_v001_生産技術 1.xlsx.

## CÂU HỎI 604
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Debug用Serial通信を設定している。
- Cách hỏi: trực tiếp
- Hỏi: Serial Interface設定前に必要なSoftwareは何ですか。
- Đáp: com0comとTeraTermを事前にInstallします。DebuggerとTeraTermには、com0comで定義したCOM番号を設定します。TV.xlsxにも同じSoftwareとCOM設定が記載されています。出典ファイル：マテコン操作手順書_v001_生産技術 1.xlsx.

## CÂU HỎI 605
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người vận hành định chạy manual AGV để kiểm tra map mới.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Bất kỳ operator nào cũng có thể chạy AGV ở manual mode để test map, đúng không?
- Đáp: Không. Tài liệu quy định thao tác chạy ở マニュアルモード chỉ do 生産技術担当者 hoặc 設備保全担当者 thực hiện. Khi khởi động, chạy, phục hồi lỗi hoặc thao tác manual phải xác nhận không có người xung quanh. Nội dung an toàn này cũng có trong TV.xlsx; khác biệt chủ yếu là ngôn ngữ trình bày. Nguồn file: マテコン操作手順書_v001_生産技術 1.xlsx.

## CÂU HỎI 606
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: AGV Map和棚位置Master刚被修改，现场准备恢复量产。
- Cách hỏi: xử lý sự cố
- Hỏi: 修改走行Map或棚位置后可以直接恢复正式生产吗？
- Đáp: 不可以。资料要求修改設定ファイル、走行マップ、棚位置情報或閉塞区間設定后，必须先进行动作确认，再投入正式运行；Map和棚位置确认应在低速、低风险条件下进行。与TV.xlsx内容一致。来源文件：マテコン操作手順書_v001_生産技術 1.xlsx.

## CÂU HỎI 607
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 本書の対象範囲と設備保全Manualの範囲を区別している。
- Cách hỏi: so sánh
- Hỏi: この操作説明書にはAGV本体の分解・修理方法まで含まれますか。
- Đáp: 含まれません。適用範囲外として、AGV本体の機構・構造・分解・修理作業、安全装置の詳細仕様、現場Layout変更に伴うRisk Assessmentが明記されています。TV.xlsxも同じ範囲構成です。出典ファイル：マテコン操作手順書_v001_生産技術 1.xlsx.

## CÂU HỎI 608
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần quyết định nên dùng bản 1.xlsx hay TV.xlsx làm nguồn khi thuật ngữ dịch có vẻ không rõ.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Có nên coi các từ dịch khác nhau giữa 1.xlsx và TV.xlsx là thay đổi specification không?
- Đáp: Không. Đối chiếu các phần chính cho thấy cấu trúc, version, ngày revision, controlNum, mã location, ctrlMode, tên SQL table, yêu cầu serial interface và các quy tắc an toàn đều tương ứng. Vì 1.xlsx giữ tiếng Nhật gốc còn TV.xlsx là bản dịch, khi một thuật ngữ tiếng Việt gây mơ hồ nên ưu tiên thuật ngữ tiếng Nhật trong 1.xlsx; chưa có bằng chứng cho thấy đây là hai revision kỹ thuật khác nhau. Nguồn file: マテコン操作手順書_v001_生産技術 1.xlsx, đối chiếu マテコン操作手順書_v001_生産技術 TV.xlsx.

---
Ghi chú dedup: cặp 599–608 trùng nội dung lớn với cặp 1–10 (mẻ 1) — cùng spec, khác ngôn ngữ. Khi import chỉ giữ bản đầy đủ hơn hoặc merge.
KDC_AMS pptx: cùng file ID với mẻ 1 — không sinh thêm cặp.
