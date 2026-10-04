# Mẻ MOM 04 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Trạng thái: Bản thảo — chưa qua chuyên gia duyệt. Khối: MOM.
Tài liệu: (23) システム構成図r3_2026-4-10.png [thay thế file trùng], (19) AMS概略フロー_入出庫・生産_20250703VN.pdf, (20) Luong xu ly nhap xuat kho AMS.png, (21) Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx, (22) KDTVN_AMS対応でのMES設定箇所 1.pptx
Lưu ý: ChatGPT tự phát hiện 260618_供給指示作成できない調査_FULL_TABLE_for_NotebookLM.pdf trùng nội dung file mẻ 3 → bỏ qua, thay bằng mục 23.

## CÂU HỎI 151
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư hệ thống cần xác nhận server nào chạy Opcenter Application khi điều tra lỗi ST/CO.
- Cách hỏi: trực tiếp
- Hỏi: Opcenter App Server trong sơ đồ KDTVN là server nào và dùng IP nào?
- Đáp: Opcenter App Server là OEXP1VAP, IP 10.170.162.169. Sơ đồ ghi server này chạy Opcenter trên JVM và Windows Server 2019. Nguồn file: システム構成図r3_2026-4-10.png.

## CÂU HỎI 152
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: HT trên line đọc ST/CO nhưng dữ liệu không sang được hệ thống lịch sử sản xuất.
- Cách hỏi: xử lý sự cố
- Hỏi: Theo sơ đồ, từ HT cần kiểm tra server trung gian nào trước khi đi sâu vào Opcenter?
- Đáp: HT Android chạy uni-app gửi ST/CO về KDTVN-PHRSRV tại IP 10.170.151.244. Server này có API WebService, WebServer JAVA/JVM, FTPService và xử lý CSV. Vì vậy nếu HT đã thao tác nhưng dữ liệu không đi tiếp, một điểm cần kiểm tra đầu tiên trong chuỗi là kết nối HT → KDTVN-PHRSRV/API trước khi kết luận lỗi nằm ở Opcenter. Nguồn file: システム構成図r3_2026-4-10.png.

## CÂU HỎI 153
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang phân biệt OPC Server và PAC Server trong đường truyền thiết bị.
- Cách hỏi: so sánh
- Hỏi: OPCP1VAP và PACP1VAP có vai trò và IP khác nhau như thế nào?
- Đáp: OPCP1VAP là OPC Server chạy Windows 11, IP 10.170.151.243. PACP1VAP là PAC Server, IP 10.170.162.172. Sơ đồ thể hiện đường MPI-020/SLMP phía thiết bị tới OPC Server và PAC I/F MPI-020 dùng port 52240 để liên kết sang phía PAC/Opcenter. Nguồn file: システム構成図r3_2026-4-10.png.

## CÂU HỎI 154
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: ST ghi nhận bình thường nhưng CO không cập nhật DB, kỹ sư cần khoanh vùng tầng server.
- Cách hỏi: tình huống
- Hỏi: Nếu cần kiểm tra DB của Opcenter thì sơ đồ chỉ ra server và database nào?
- Đáp: Opcenter DB Server là OEXP1VDB, IP 10.170.162.166, chạy SQL Server 2019 trên Windows Server 2019. Sơ đồ thể hiện ba khu vực DB chính là EXAPP_IF, MIO và MOM; cạnh EXAPP_IF có đánh dấu StatusCodeLinkageTable. Nguồn file: システム構成図r3_2026-4-10.png.

## CÂU HỎI 155
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在确认HT终端是否直接连接Opcenter DB。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: HT的ST/CO数据是直接写入OEXP1VDB数据库，对吗？
- Đáp: 不对。系统图显示HT首先连接KDTVN-PHRSRV（10.170.151.244）的API WebService，再通过周边系统链路与PLC、MIO、Opcenter等进行联携。图中没有表示HT直接连接OEXP1VDB数据库。来源文件：システム構成図r3_2026-4-10.png。

## CÂU HỎI 156
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 现场需要确认Oricon Gate与统括PLC的地址。
- Cách hỏi: trực tiếp
- Hỏi: 图中的Oricon Gate和Conveyor PLC分别使用什么IP？
- Đáp: Oricon Gate标注为10.170.155.250，Conveyor PLC标注为10.170.155.249。两者位于统括PLC／设备侧区域。来源文件：システム構成図r3_2026-4-10.png。

## CÂU HỎI 157
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: PAC通信异常，工程师正在确认网络边界。
- Cách hỏi: xử lý sự cố
- Hỏi: MPI-020 PAC I/F在图中使用哪个Port？
- Đáp: 图中MPI-020 PAC I/F明确标注Port 52240。因此在PAC通信故障排查时，可以把该Port以及OPCP1VAP、PACP1VAP之间的通信路径作为确认对象之一。来源文件：システム構成図r3_2026-4-10.png。

## CÂU HỎI 158
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: MOM周辺サーバの役割を新人へ説明している。
- Cách hỏi: so sánh
- Hỏi: MIOP1VAPとOEXP1VAPは同じServerですか。
- Đáp: 同じではありません。MIOP1VAPはMIO ServerでIPは10.170.162.162、OEXP1VAPはOpcenter App ServerでIPは10.170.162.169です。図ではそれぞれ別ServerとしてOpcenter DB側へ接続されています。出典ファイル：システム構成図r3_2026-4-10.png。

## CÂU HỎI 159
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 生産履歴登録システムのHT側IPを現場で確認している。
- Cách hỏi: tình huống
- Hỏi: HT端末のIPとして図に記載されている値は何ですか。
- Đáp: HT欄には10.170.155.228と10.170.155.229の2つが記載されています。HTはAndroid／uni-app構成で、生産履歴登録システムおよび着完工登録システムに使用される構成として示されています。出典ファイル：システム構成図r3_2026-4-10.png。

## CÂU HỎI 160
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者がST/CO異常時の切り分け方法を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: ST/CO異常が出た場合、Opcenter App Serverだけを確認すれば十分ですか。
- Đáp: 十分ではありません。図ではHT、KDTVN-PHRSRV、統括PLC、OPC Server、PAC Server、MIO Server、Opcenter App Server、Opcenter DB Serverが連携しています。異常箇所に応じて、HT/API、SLMP、PLC、PAC/MIO、App、DBのどこまでデータが到達しているかを順に確認する必要があります。出典ファイル：システム構成図r3_2026-4-10.png.

## CÂU HỎI 161
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 生产管理人员正在确认从生产指令到现场开工的整体流程。
- Cách hỏi: trực tiếp
- Hỏi: 从生产指令到开始生产，资料中涉及哪些主要系统？
- Đáp: 流程中包括R3发行生产指令、APS制作工程计划、进度管理分配Serial、IF工具按Serial单位分割指令、Opcenter接收计划并制作供给计划，再把工程计划和供给计划联携到设备。现场读取Serial Barcode后，由着完工登记系统生成生产开始信息，并由Opcenter执行生产开始处理。来源文件：AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 162
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: Line-Out后设备完成修理，现场准备恢复生产。
- Cách hỏi: tình huống
- Hỏi: Line-Out后的修理和Line恢复信息通过什么系统记录？
- Đáp: 流程中Line-Out由着完工登记系统生成Line停止信息，同时生产履历登记系统生成Line-Out信息。修理后，生产履历登记系统记录修理履历并生成Line恢复信息，着完工登记系统再生成Line重新运行信息。来源文件：AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 163
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较生产开始登记和生产实绩收集的处理。
- Cách hỏi: so sánh
- Hỏi: 生产开始和生产完成阶段，Opcenter分别做什么？
- Đáp: 生产开始阶段，现场读取Barcode后生成生产开始信息，Opcenter执行生产开始处理。生产完成侧，Opcenter收集实绩并生成Traceability信息以及指令完成信息；之后IF工具生成R/3联携数据和进度管理联携数据。来源文件：AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 164
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程库存数量与现场实物不一致，需要修正。
- Cách hỏi: xử lý sự cố
- Hỏi: 流程图中工程库存修正由哪个系统执行？
- Đáp: 流程明确显示由Opcenter执行工程在庫修正，并与库存管理表关联。资料同时显示生产实绩侧存在自动库存扣减，因此发生差异时需要区分自动扣减结果与人工库存修正。来源文件：AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 165
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới cho rằng AMS chỉ quản lý kho tự động, không liên quan luồng sản xuất.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: AMS trong tài liệu chỉ gồm WMS và kho tự động, không liên quan MOM trên line sản xuất, đúng không?
- Đáp: Không. Tài liệu thể hiện cả luồng sản xuất lẫn logistics: R3, APS, MOM/Opcenter, MES, WMS, PLC và Logistics đều liên quan. Phía sản xuất có phát hành lệnh, lập kế hoạch công đoạn/cấp phát, ST/CO, Line-Out, thực tích và traceability; phía kho có nhận hàng, nhập kho, cấp phát, hoàn nhập và chuyển tồn kho. Nguồn file: AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 166
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên kho cần xác nhận thông tin nào được đăng ký tại Oricon Gate khi nhập kho.
- Cách hỏi: trực tiếp
- Hỏi: Khi ORICON qua gate nhập kho, hệ thống đăng ký những loại thông tin nào?
- Đáp: Tài liệu ghi đăng ký thông tin QR của phiếu hiện vật ngoài các dữ liệu PO/Item/Qty, số giá và Timestamp ngày nhập kho. Luồng này liên quan bảng xử lý nhập kho và ID ORICON trước khi hàng được chuyển đến vị trí bảo quản được chỉ định. Nguồn file: AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 167
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Nhân viên kho đang so sánh cấp phát bằng xe đẩy và cấp phát tự động.
- Cách hỏi: so sánh
- Hỏi: Cấp phát bằng xe đẩy và cấp phát từ kho tự động khác nhau ở điểm nào?
- Đáp: Luồng xe đẩy dùng hệ thống hiển thị yêu cầu theo mã hàng,棚番 và Picking Cart, chỉ định PO theo thông tin FIFO quản lý bởi VN-MES, sau đó đọc QR thùng đã Picking và đưa lên cart. Với kho tự động AMS, MOM tạo chỉ thị xuất kho theo kế hoạch công đoạn và chỉ định ORICON ID, sau đó hệ thống thiết bị/CTU thực hiện cấp phát. Nguồn file: AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 168
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 補充入庫でFIFO管理が必要か確認している。
- Cách hỏi: tình huống
- Hỏi: 補充入庫用のORICONにもFIFO管理は必要ですか。
- Đáp: 資料には「補充入庫に使用するORICONにもFIFOが必要」と記載されています。また、自動倉庫側ではItemごとの在庫確認や閾値による補充指示、棚番指定などの流れが示されています。出典ファイル：AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 169
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 製造ラインで余剰部品が発生し、倉庫へ戻す必要がある。
- Cách hỏi: xử lý sự cố
- Hỏi: 余剰部品を返却する時はどのような流れですか。
- Đáp: 製造側から返却要求を行い、生産履歴登録システムで現品票をPhoneで読み取り、「返却」を選択して数量を入力します。その後、返却伝票を発行・貼付し、在庫修正および再入庫の処理につなげる流れが示されています。出典ファイル：AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 170
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 新人が完成実績を登録すればR/3更新までOpcenter単独で行うと思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Opcenterが実績を収集した時点でR/3連携まで完了しますか。
- Đáp: いいえ。資料ではOpcenterが実績を収集し、Traceability／指図完了情報を作成した後、I/FツールがR/3連携データと進度管理連携データを作成する流れになっています。したがって、Opcenter実績収集とR/3連携は同一処理ではありません。出典ファイル：AMS概略フロー_入出庫・生産_20250703VN.pdf.

## CÂU HỎI 171
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: ORICONをAMS倉庫へ入庫する前に、最初のデータ確認をしている。
- Cách hỏi: trực tiếp
- Hỏi: 入庫前にORICONについて何をScan／確認しますか。
- Đáp: フローではORICON ID、PO、品目、数量、重量をScan／確認してからConveyor／ACR-Matecon側の入庫ゲートへ投入します。その後、T_PARTS_RECEIVEに有効な入庫Recordが存在するかを確認します。出典ファイル：Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 172
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: ORICONをGateへ投入したがT_PARTS_RECEIVEにRecordがない。
- Cách hỏi: xử lý sự cố
- Hỏi: T_PARTS_RECEIVEに有効な入庫Recordがない場合、何を照合しますか。
- Đáp: NG分岐では、入庫Recordがない、またはORICON_ID／POが不正な可能性を確認し、ORICON_ID、PO_NO、PO_DETAIL_NO、PO_SEP_KEY、CASE_SEQNO、品目などを照合する流れです。出典ファイル：Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 173
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 入庫Commandは出ているがACRが棚まで搬送しない。
- Cách hỏi: tình huống
- Hỏi: ACRが正しいShelfまで搬送しない時は、どの情報を確認しますか。
- Đáp: フローではACR通信／Matecon入庫命令を確認し、必要に応じてConveyor上のWaiting指図をClearし、HOUSE_START_FLGのRecordをClearして再実行、Matecon再起動やLog取得を行う対応が示されています。出典ファイル：Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 174
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: WMS上の入庫完了と実際のACR動作が一致しない。
- Cách hỏi: so sánh
- Hỏi: 入庫完了判定ではWMSだけを確認すればよいですか。
- Đáp: いいえ。図ではWMS、MOM／Opcenter、ACR Logの状態が整合しているかを確認します。HOUSE_START_FLG、HOUSE_FINISH_FLG、Shelfなどの状態が各システムで一致しない場合は、片側だけ完了している可能性があります。出典ファイル：Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 175
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为ORICON进到Rack就等于入库成功。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: ORICON物理上已经进入Rack，就可以马上判定"入库OK"，对吗？
- Đáp: 不对。流程要求确认WMS／MOM／Opcenter状态是否一致，并确认相关HOUSE_START_FLG、HOUSE_FINISH_FLG和Shelf状态。只有系统状态与实物入库完成一致后，才进入"入库OK、AMS存在可用于出库的库存"状态。来源文件：Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 176
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: APS已经制作了工程计划，工程师确认自动出库指示是如何生成的。
- Cách hỏi: trực tiếp
- Hỏi: 自动供给计划到T_PARTS_OUT之间是什么流程？
- Đáp: 图中先由APS／生产顺序表／MES SHINDO生成生产计划，APS再生成工程计划和供给计划，之后由SQA_partsout / PlanSupply输出出库指示，并确认T_PARTS_OUT是否已经生成出库Record。来源文件：Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 177
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: Supply Plan已经有了，但T_PARTS_OUT中没有出库Record。
- Cách hỏi: xử lý sự cố
- Hỏi: Supply Plan未写入T_PARTS_OUT时，流程建议怎么处理？
- Đáp: NG分支写明"Supply Plan还没有写入T_PARTS_OUT"。对应措施是删除旧Plan并重新生成，或者使用Manual Supply Line进行临时处理。来源文件：Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 178
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 自动Supply和Manual Supply都可以选择Container，工程师要比较两种方式。
- Cách hỏi: so sánh
- Hỏi: Auto Supply和Manual Supply在线路上有什么不同？
- Đáp: Auto Supply从T_PARTS_OUT把指示送到Matecon，再由ACR／CTU执行搬送；Manual Supply Line则由操作员手动选择Container并执行出库。两条路径之后都会进入"Container是否能正确显示／选择"的检查以及ACR／CTU／Matecon实际取箱流程。来源文件：Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 179
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: ACR đã đưa thùng ra khỏi rack nhưng xuất kho không hoàn thành.
- Cách hỏi: tình huống
- Hỏi: Khi ORICON đã ra khỏi rack nhưng Delivery chưa complete, flow chia lỗi thành những nhóm nào?
- Đáp: Flow chia ít nhất 5 nhóm: ① không có chỉ thị/không ghi T_PARTS_OUT; ② sai SUP_PROCESS hoặc MaterialQueue/CTU mapping; ③ sai Revision hoặc IsROR, Manual Supply không lấy đúng thùng; ④ ACR/Matecon báo hoàn thành sai hoặc mất tín hiệu; ⑤ dữ liệu ORICON/Rack không khớp hoặc kẹt vật lý. Nguồn file: Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 180
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Sau xử lý lỗi, kỹ sư định bật lại chế độ auto ngay dù chưa xác nhận delivery.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Sửa dữ liệu xong là có thể tiếp tục auto ngay không?
- Đáp: Không. Flow yêu cầu kiểm tra lại "Sau đối ứng xuất kho hoàn thành?" Nếu có thì cập nhật hoàn thành và khôi phục luồng xuất kho. Nếu chưa hoàn thành thì không tiếp tục auto khi chưa xác nhận, mà phải tiếp tục điều tra log/DB. Nguồn file: Luong xu ly nhap xuat kho AMS.png.

## CÂU HỎI 181
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư mới cần đối chiếu cấu trúc BOP giữa Teamcenter và Opcenter.
- Cách hỏi: trực tiếp
- Hỏi: Process và CompoundOperation của Teamcenter được biểu diễn thế nào ở Opcenter?
- Đáp: Teamcenter dùng Process làm nút cha và có các CompoundOperation theo từng công đoạn; CompoundOperation gồm Parts, WorkArea, Execution Step và các khái niệm liên quan. Trong Opcenter, thông tin Process được định nghĩa bằng Workflow + ERP BOM + ERP Route; Workflow là cấu trúc BOP, ERP BOM là BOM, ERP Route là thứ tự công đoạn. Thông tin CompoundOperation được biểu diễn bằng Spec + Operation + Resource Group. Nguồn file: Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 182
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Hệ thống đăng ký着完工 yêu cầu nhập ID công đoạn.
- Cách hỏi: tình huống
- Hỏi: Với đăng ký bắt đầu/hoàn thành công đoạn, phải nhập ID nào?
- Đáp: Phải dùng Spec Name của Opcenter, tương ứng với Compound Operation Name của Teamcenter. Ví dụ tài liệu dùng Y302YL93020100, là ID 14 ký tự bắt đầu bằng Y3. Vì着完工 là đăng ký Move In/Move, cần chỉ định Spec nơi Container sẽ di chuyển tới. Nguồn file: Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 183
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang phân biệt ID dùng cho着完工 và ID dùng cho xuất kho manual.
- Cách hỏi: xử lý sự cố
- Hỏi: Spec Name và WorkCenter Name được dùng khác nhau thế nào?
- Đáp: Spec Name dùng cho 着完工/Line-Out vì Move In/Move cần chỉ định Spec nơi Container sẽ di chuyển tới; WorkCenter Name dùng cho xuất kho manual vì cần WorkCenter Name làm input để xác định Ship vào Workflow cấp hàng nào. Nguồn file: Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 184
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Xuất kho manual không ghi đúng vị trí cấp hàng.
- Cách hỏi: xử lý sự cố
- Hỏi: Workflow cấp hàng được đặt tên theo quy tắc nào để kiểm tra WorkCenter?
- Đáp: Ví dụ trong tài liệu là C3B_YB2200C30034_3V2ND00160, tức WorkCenter Name_Item Code. Với xuất kho manual, hệ thống cần WorkCenter Name làm input để xác định Ship vào Workflow cấp hàng nào. Nguồn file: Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 185
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为着完工和Manual出库都输入同一个Process ID。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 着完工和Manual出库都使用Spec Name作为输入，对吗？
- Đáp: 不对。着完工／Line-Out使用Spec Name，因为Move In/Move需要指定目标Spec；Manual出库使用WorkCenter Name，因为需要确定供给地点以及Ship到哪个供给Workflow。来源文件：Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 186
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要确认生产履历登记系统的Master层级。
- Cách hỏi: trực tiếp
- Hỏi: 生产履历登记系统的Master层级是什么？
- Đáp: 资料中的层级为：Line名称C3B → Unit名称FK-8570 → 工程名称Y3～ → 供给地点名称C3B_YB～ → 品目，例如3V2ND00160。来源文件：Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 187
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新版本生产履历登记系统进行回归验证。
- Cách hỏi: tình huống
- Hỏi: 着完工登记应该如何验证新版本是否与以前一致？
- Đáp: 验证项目要求确认着完工仍能像以前一样登记；输出目标为StatusCodeLinkage_Ver00，评价方法是与以前的登记信息进行比较。资料没有确定"必须完全一致还是允许差异"，这一点被列为后续确认事项。来源文件：Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 188
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: マニュアル出庫機能の新Version検証を実施している。
- Cách hỏi: xử lý sự cố
- Hỏi: マニュアル出庫ではどのTableへの登録を確認しますか。
- Đáp: 入力情報の登録先としてCEPStagingDB.dbo.ManualShipping_ExistingLineAuto_InboundDownload、出庫指示の登録先としてT_PARTS_OUTを確認します。評価項目は、T_PARTS_OUTへ正常に登録されることと、FIFO順に沿って登録されることです。出典ファイル：Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 189
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: TeamcenterとOpcenterで工程情報の表現方法を比較している。
- Cách hỏi: so sánh
- Hỏi: TeamcenterのCompoundOperationとOpcenter側の構成要素は何ですか。
- Đáp: TeamcenterのCompoundOperationは工程単位で、Parts、WorkArea、Execution Stepなどの概念を持ちます。Opcenter側ではCompoundOperation情報をSpec、Operation、Resource Groupで構成します。ただし、これらが1対1対応か複数Specになるかは資料上「確認事項」であり、確定していません。出典ファイル：Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 190
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者がFIFO検証条件を確定済みだと思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: FIFOの判定基準はこの資料ですでに確定していますか。
- Đáp: いいえ。資料では「FIFOの判定基準は指示時刻か、登録時刻か、供給場所単位か」が確認事項として残っています。したがって、どれか一つを正式仕様として断定することはできません。出典ファイル：Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx.

## CÂU HỎI 191
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư KDTVN chuẩn bị cấu hình điều kiện để lệnh sản xuất được liên kết sang MOM.
- Cách hỏi: trực tiếp
- Hỏi: Hệ thống dùng tiêu chí nào để quyết định một chỉ thị có được liên kết sang MOM?
- Đáp: Việc phán định sử dụng MRP管理者 và 製造バージョン thông qua master M_MOMIF_CRITERIA. Tài liệu ghi phía VN2 thực hiện trên TESTSVRVN2 / VN2BIPCSVR3. Nguồn file: KDTVN_AMS対応でのMES設定箇所 1.pptx.

## CÂU HỎI 192
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Một mã đã đăng ký trong master phụ thuộc với cờ DEPENDENT_FLG = 1.
- Cách hỏi: tình huống
- Hỏi: Khi DEPENDENT_FLG = 1, dữ liệu được xử lý thế nào khi liên kết MOM?
- Đáp: Nếu đã đăng ký trong M_MOMIF_UNIT_MRPADMIN và flag bằng 1, đối tượng được coi là 従属品; dữ liệu có thể liên kết sang MOM mà không cần phụ thuộc vào bảng thứ tự sản xuất. Tài liệu cũng ghi đối tượng đăng ký trong master này được thực tích dưới dạng OPTION品. Nguồn file: KDTVN_AMS対応でのMES設定箇所 1.pptx.

## CÂU HỎI 193
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh cách xử lý sản phẩm thường và sản phẩm phụ thuộc.
- Cách hỏi: so sánh
- Hỏi: DEPENDENT_FLG = 1 và DEPENDENT_FLG = 0 khác nhau thế nào?
- Đáp: 1 nghĩa là従属品 và có thể liên kết MOM mà không cần quan tâm bảng thứ tự sản xuất. 0 nghĩa là sản phẩm; trường hợp flag 0 hoặc không có đăng ký trong master thì được xử lý như sản phẩm và muốn liên kết MOM phải có bảng thứ tự sản xuất. Nguồn file: KDTVN_AMS対応でのMES設定箇所 1.pptx.

## CÂU HỎI 194
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: MOM联携条件Master登记后，某指令仍然没有被选中。
- Cách hỏi: xử lý sự cố
- Hỏi: M_MOMIF_CRITERIA中应检查哪些关键字段？
- Đáp: 应检查PROD_PLANT、MRP_ADMIN、PROD_LINE以及VALID_FROM / VALID_TO。资料的参考例中PROD_PLANT = 2200；例如制造版本V01-C32时，MRP_ADMIN登记V01，PROD_LINE登记C32；有效期间会与指令的安排开始日进行比较。来源文件：KDTVN_AMS対応でのMES設定箇所 1.pptx.

## CÂU HỎI 195
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为没有登记在従属品Master里的品目不会联携MOM。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 没有登记在M_MOMIF_UNIT_MRPADMIN中的品目就完全不能联携MOM，对吗？
- Đáp: 不对。没有登记或DEPENDENT_FLG = 0时，品目按"产品"处理；这种情况下要联携MOM，需要生产顺序表。只有DEPENDENT_FLG = 1时，才作为従属品不依赖生产顺序表进行联携。来源文件：KDTVN_AMS対応でのMES设置箇所 1.pptx.

## CÂU HỎI 196
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: KDTVN需要登记R3中不存在的生产指令。
- Cách hỏi: trực tiếp
- Hỏi: R3中不存在的指令，资料规定指令号采用什么格式？
- Đáp: 资料写明，对于R3中不存在的指令，指令号采用YYYYMMDDHHMM格式进行登记。当前说明还写明现状没有登记这些指令，需要从进度管理的NEW进行登记。来源文件：KDTVN_AMS対応でのMES設定箇所 1.pptx.

## CÂU HỎI 197
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师准备共享生产顺序CSV，但SQL Agent Job无法读取文件。
- Cách hỏi: tình huống
- Hỏi: ProductionSchedule目录为什么需要共享化？
- Đáp: 资料说明，为了允许外部访问以及执行Job，需要把IF Folder共享化。系统上需要权限的用户是KDTVN\Administator，因为SQL Server Service执行用户→AgentJob执行用户最终需要具备文件操作权限。来源文件：KDTVN_AMS対応でのMES设置箇所 1.pptx.

## CÂU HỎI 198
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 生産順位CSVの格納先を設定している。
- Cách hỏi: trực tiếp
- Hỏi: ProductionScheduleの格納先として資料に記載されているPathは何ですか。
- Đáp: OEXP1VDB上のD:\IF\ProductionScheduleとBackup用のD:\IF\BackUp\ProductionScheduleです。Network Pathとして\\OEXP1VDB\IF\ProductionScheduleおよび\\OEXP1VDB\IF\BackUp\ProductionScheduleが記載されています。出典ファイル：KDTVN_AMS対応でのMES設定箇所 1.pptx.

## CÂU HỎI 199
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: MOM連携Masterと従属品Masterの役割を混同している。
- Cách hỏi: so sánh
- Hỏi: M_MOMIF_CRITERIAとM_MOMIF_UNIT_MRPADMINの役割はどう違いますか。
- Đáp: M_MOMIF_CRITERIAはMRP管理者と製造Versionを使って「その指図をMOM連携対象にするか」を判定します。M_MOMIF_UNIT_MRPADMINはMRP管理者とFlagを使って製品／従属品を判定し、従属品なら生産順位表を意識せずMOM連携するためのMasterです。出典ファイル：KDTVN_AMS対応でのMES設定箇所 1.pptx.

## CÂU HỎI 200
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 管理者がCSV監視Jobの実行周期を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: ProductionSchedule連携のAgentJobは1時間周期ですか。
- Đáp: いいえ。資料にはSQL ServerのAgentJobは1分周期と記載されています。またMail宛先はOEXP1VDB.EXAPP_IF.M_CTRLで設定し、CTL01=Mail、CTL02=AddressのVAL01を使用する構成です。出典ファイル：KDTVN_AMS対応でのMES設定箇所 1.pptx.
