# Mẻ MOM 09 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
5 file map CTU trong 仕様書/マテハン, mỗi file 10 cặp, câu 379–428. Không file nào bị bỏ qua.

## CÂU HỎI 379
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang kiểm tra layout tầng 3 trước khi thiết kế tuyến chạy CTU.
- Cách hỏi: trực tiếp
- Hỏi: Layout tầng 3 được chia theo hệ tọa độ nào để xác định khu vực?
- Đáp: Layout thể hiện trục ngang đánh số từ 1 đến 25 và các hàng khu vực bằng chữ như A, B, C, D, E, F, G, H... Các ký hiệu này dùng làm mốc vị trí trên mặt bằng khi đối chiếu đường chạy và khu vực thiết bị. Nguồn file: CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 380
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在确认自动仓库区域在不同楼层的物流方向。
- Cách hỏi: tình huống
- Hỏi: 自动仓库的大型Pallet在1F和2F/3F的南侧使用方式有什么区别？
- Đáp: Layout注记写明：1Fは南側より格納し、2F、3Fでは南側より出庫。也就是说，1F从南侧进行入库，而2F和3F从南侧进行出库。来源文件：CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 381
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: CTU走行経路を決める前に、3階Layout上の設備を確認している。
- Cách hỏi: trực tiếp
- Hỏi: Layout上にはどのような設備・エリア表記がありますか。
- Đáp: 抽出できる表記として、自動倉庫の大物パレット管理、EPS、複数のEV、製品エリア、バーチなどがあります。出典ファイル：CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 382
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới nhìn layout và cho rằng toàn bộ tầng 3 chỉ là hành lang CTU.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Có thể coi toàn bộ mặt bằng trong file này chỉ là đường chạy CTU không?
- Đáp: Không. File là layout tổng thể tầng 3, trong đó có các khu vực 製品, EV, EPS, バーチ và khu tự động kho lớn. Vì vậy khi thiết kế tuyến CTU phải phân biệt khu vực lưu trữ/thiết bị với phần hành lang có thể dùng cho chạy. Nguồn file: CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 383
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较楼层物流方向，避免把入库方向配置反。
- Cách hỏi: so sánh
- Hỏi: 1F与3F在自动仓库南侧的物流方向是否相同？
- Đáp: 不相同。1F南侧用于格納，而3F南侧用于出庫；2F也与3F相同，从南侧出库。来源文件：CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 384
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: CTU経路を追加する場所にEV表記があるため干渉確認をしている。
- Cách hỏi: xử lý sự cố
- Hỏi: 経路候補付近にEVがある場合、Layout確認で何に注意しますか。
- Đáp: このFileには複数のEV位置が明示されています。したがって、CTU経路を設定する際はEVエリアを通常通路として扱わず、実際の通路境界や設備干渉を別途確認する必要があります。File自体からEV通過可否までは確定できません。出典ファイル：CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 385
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn xác định một điểm trên layout nhưng chỉ nhớ khu vực chữ.
- Cách hỏi: tình huống
- Hỏi: Chỉ biết khu vực F thì đã đủ để xác định chính xác một điểm chạy CTU chưa?
- Đáp: Chưa. Layout dùng kết hợp hàng chữ và cột số; hàng F chỉ xác định một dải khu vực. Cần thêm vị trí theo cột số hoặc mốc thiết bị trên mặt bằng để xác định điểm chính xác. Nguồn file: CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 386
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师要把Map Address与物理楼层布局对应起来。
- Cách hỏi: trực tiếp
- Hỏi: 这张3F Layout本身是否直接给出了CTU的Address/Task表？
- Đáp: 当前可读取的主要内容是物理布局、行列坐标和设备／区域标识，并不是Address/Task命令表。具体Address与Task应与后面的CTU Map文件进行对应。来源文件：CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 387
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: LayoutとMapの役割を新人に説明している。
- Cách hỏi: so sánh
- Hỏi: このLayout FileとCTU Map Fileは何を確認する目的が違いますか。
- Đáp: Layout Fileは3階の物理配置、設備、エリアや通路位置を確認するための資料です。一方、CTU Map FileはAddressやTask、速度変更・停止ポイントなどの走行設定を確認するために使います。出典ファイル：CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 388
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư định kết luận một tuyến CTU đi qua được chỉ vì trên Excel không thấy vật cản.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Chỉ dựa vào layout này có thể khẳng định tuyến đó chạy CTU an toàn không?
- Đáp: Không. Layout cho biết bố trí mặt bằng và các khu vực/thiết bị chính, nhưng không cung cấp đầy đủ điều kiện an toàn, khoảng cách clearance hay logic điều khiển CTU. Cần đối chiếu thêm map chạy và kiểm chứng thực tế. Nguồn file: CTU 3階の通路レイアウト_251211.xlsx.

## CÂU HỎI 389
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在检查2026-04-06修正版Map的供给地点编号。
- Cách hỏi: trực tiếp
- Hỏi: 该Map中SUP_PROCESS使用什么命名形式？
- Đáp: 文件顶部标有SUP_PROCESS以及C3B_YB2200C300**，并展开了22、23、24、25、26、27、28、29、30等供给地点编号。来源文件：CTUマップ修正20260406.xlsx.

## CÂU HỎI 390
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 4月6日版Mapの速度制御記号を確認している。
- Cách hỏi: trực tiếp
- Hỏi: RFIDの4種類の記号は何を意味しますか。
- Đáp: －はRFID（停止）、↓はRFID（減速）、↑はRFID（加速）、→はRFID（速度維持）を表します。出典ファイル：CTUマップ修正20260406.xlsx.

## CÂU HỎI 391
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: CTU giảm tốc sai vị trí, kỹ sư đang phân biệt RFID và magnetic tape.
- Cách hỏi: so sánh
- Hỏi: Map này có định nghĩa riêng ký hiệu cho RFID và băng từ không?
- Đáp: Có. RFID có các trạng thái 停止 / 減速 / 加速 / 速度維持. Băng từ (磁気テープ) cũng được ghi riêng với 停止, 減速, 加速. Vì vậy khi điều tra điểm thay đổi tốc độ phải xác định tín hiệu đến từ RFID hay magnetic tape. Nguồn file: CTUマップ修正20260406.xlsx.

## CÂU HỎI 392
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: CTU到达ORICON取货区域，需要确认Map上的物理标记。
- Cách hỏi: tình huống
- Hỏi: 4月6日版Map中是否明确标出了ORICON取货口？
- Đáp: 是。图中明确标有オリコン 引き取り口，另外还有独立的空オリコン 引き取り口，两者不是同一个标识。来源文件：CTUマップ修正20260406.xlsx.

## CÂU HỎI 393
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 空ORICON回収ルートを通常ORICONルートと混同している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: オリコン引き取り口と空オリコン引き取り口は同一ポイントですか。
- Đáp: 同一表記ではありません。Map上では通常のオリコン 引き取り口と空オリコン 引き取り口が別の場所として記載されています。出典ファイル：CTUマップ修正20260406.xlsx.

## CÂU HỎI 394
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: CTU không về điểm sạc đúng, kỹ sư kiểm tra layout map.
- Cách hỏi: xử lý sự cố
- Hỏi: File có chỉ rõ vị trí sạc để dùng làm mốc điều tra không?
- Đáp: Có. Map có nhãn 充電位置. Khi CTU không về đúng vùng sạc, có thể dùng vị trí này làm mốc vật lý để đối chiếu đường chạy, nhưng file không cung cấp đầy đủ logic command sạc trong phần layout được trích xuất. Nguồn file: CTUマップ修正20260406.xlsx.

## CÂU HỎI 395
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现某些路段反复标有3和30，正在判断是否为速度参数。
- Cách hỏi: tình huống
- Hỏi: 可以仅凭这张Map断定3和30的单位是什么吗？
- Đáp: 不能完全断定。Map中在RFID速度控制点附近反复出现3、15、20、30等数值，但该文件本身没有在抽取内容中明确给出这些数字的单位。若要确定速度单位，应再对照Task/AGV通信规格。来源文件：CTUマップ修正20260406.xlsx.

## CÂU HỎI 396
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 4月6日版の供給先グループを確認している。
- Cách hỏi: trực tiếp
- Hỏi: Map上にはどのK系統が表示されていますか。
- Đáp: 抽出範囲ではK-1、K-2、K-3、K-4、K-5、K-6、K-7、K-8、K-9などが表示されています。出典ファイル：CTUマップ修正20260406.xlsx.

## CÂU HỎI 397
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so map 4/6 với map cũ để tìm thay đổi đường chạy.
- Cách hỏi: so sánh
- Hỏi: Điểm nổi bật của file CTUマップ修正20260406.xlsx so với các map task kiểu Address/Task là gì?
- Đáp: File 4/6 thể hiện trực tiếp layout theo SUP_PROCESS, các nhóm K, điểm RFID/magnetic tape, ORICON pickup, empty ORICON pickup và charging position. Các file map 12/15–3/17 lại có các bảng Map / Task với chuỗi task số. Nguồn file: CTUマップ修正20260406.xlsx.

## CÂU HỎI 398
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 新人认为文件名叫"修正"就能知道具体修改项目。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 只根据文件名CTUマップ修正20260406就能确定4月6日到底修改了哪一个旧Address吗？
- Đáp: 不能。文件内容可以确认4月6日版的当前布局和控制点，但在已读取内容中没有完整的"旧值→新值"Revision表。因此具体修改哪个旧Address必须与前一版逐项比较后才能确认。来源文件：CTUマップ修正20260406.xlsx.

## CÂU HỎI 399
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 2025年12月15日版でp-Stand供給時の減速Pointを確認している。
- Cách hỏi: trực tiếp
- Hỏi: このMapにはp-Stand供給時の減速Pointについてどのような注記がありますか。
- Đáp: 磁気テープ追加（3m/minへの減速用）という注記があり、※p-Stand供給時の減速ポイントとして各Courseに対応するPoint番号が記載されています。出典ファイル：CTUマップ再検討20251215.xlsx.

## CÂU HỎI 400
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần biết điểm giảm tốc của Course 01 và 02.
- Cách hỏi: trực tiếp
- Hỏi: Course_01 và Course_02 dùng điểm giảm tốc nào?
- Đáp: Cả Course_01 và Course_02 đều được ghi là điểm 9. Nguồn file: CTUマップ再検討20251215.xlsx.

## CÂU HỎI 401
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Course 03～06的减速点。
- Cách hỏi: so sánh
- Hỏi: Course_03、04、05、06的减速Point分别是多少？
- Đáp: Course_03 = 12、Course_04 = 13、Course_05 = 14、Course_06 = 15。来源文件：CTUマップ再検討20251215.xlsx.

## CÂU HỎI 402
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Course 10と11が同じ減速Pointを使用するか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Course_10とCourse_11は異なる減速Pointですか。
- Đáp: いいえ。両方ともPoint 21と記載されています。出典ファイル：CTUマップ再検討20251215.xlsx.

## CÂU HỎI 403
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: CTU chạy Course 15 và cần xác nhận vị trí giảm tốc.
- Cách hỏi: tình huống
- Hỏi: Course_15 được đặt điểm giảm tốc bao nhiêu?
- Đáp: Course_15 = 29. Các course liền trước được ghi Course_12 = 24, Course_13 = 26, Course_14 = 27. Nguồn file: CTUマップ再検討20251215.xlsx.

## CÂU HỎI 404
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在检查Map Address 2的Task序列。
- Cách hỏi: xử lý sự cố
- Hỏi: Address 2的Task包含哪些特殊Task编号？
- Đáp: Address 2的序列为0, 151, 147, 98, 79, 153, 15, 65。其中包含Task 151和153，在AGV通信资料中分别对应QR照合等待及Arm HP复归相关序列。来源文件：CTUマップ再検討20251215.xlsx.

## CÂU HỎI 405
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Map Address 3と4のTask差分を見ている。
- Cách hỏi: so sánh
- Hỏi: Address 3と4のTaskはどこが違いますか。
- Đáp: Address 3は72,77,142,15,65、Address 4は72,77,143,30,65です。142/143と速度値15/30が異なります。出典ファイル：CTUマップ再検討20251215.xlsx.

## CÂU HỎI 406
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới thấy nhiều sheet map và tưởng chúng là bản sao hoàn toàn.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Các bảng Map trong file 12/15 có cùng một Address sequence không?
- Đáp: Không. Phần đầu giống nhau ở Address 1–8, nhưng đoạn sau thay đổi theo course. Ví dụ một bảng dùng Address 9→10, bảng khác 9→11, rồi các bảng kế tiếp lần lượt 12→13, 13→14, 14→15, 15→16... Nguồn file: CTUマップ再検討20251215.xlsx.

## CÂU HỎI 407
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: CTU在Address 53附近出现路线问题。
- Cách hỏi: tình huống
- Hỏi: Address 53的Task序列是什么？
- Đáp: Address 53记录为0, 90, 10, 64, 72, 79, 143, 10, 65。来源文件：CTUマップ再検討20251215.xlsx.

## CÂU HỎI 408
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 12月15日版の各Courseの終了処理を確認している。
- Cách hỏi: trực tiếp
- Hỏi: 各Map表の末尾はどのように終了しますか。
- Đáp: 抽出された各Map表では、最後にMap 1 / Task 0があり、その次にEndが記載されています。出典ファイル：CTUマップ再検討20251215.xlsx.

## CÂU HỎI 409
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang xem bản map ngày 16/3 để xác nhận các khu vực pickup.
- Cách hỏi: trực tiếp
- Hỏi: Layout của bản 16/3 có những mốc pickup nào được ghi rõ?
- Đáp: Có オリコン 引き取り口, 空オリコン 引き取り口 và một vị trí RFID trên layout. Nguồn file: CTUマップ再検討20260316.xlsx.

## CÂU HỎI 410
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查3月16日版Address 1～4的Task。
- Cách hỏi: tình huống
- Hỏi: Address 1～4的Task分别是什么？
- Đáp: Address 1=72,79,143,10,65；Address 2=0,151,147,98,79,153,15,65；Address 3=72,77,142,15,65；Address 4=72,77,143,30,65。来源文件：CTUマップ再検討20260316.xlsx.

## CÂU HỎI 411
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Address 5～7のTaskを比較している。
- Cách hỏi: so sánh
- Hỏi: Address 5、6、7はどのような違いがありますか。
- Đáp: Address 5は73,77,142,15,65、Address 6は73,77,143,15,65、Address 7は73,77,142,15,65です。5と7は同じで、6だけ142ではなく143です。出典ファイル：CTUマップ再検討20260316.xlsx.

## CÂU HỎI 412
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: CTU gặp bất thường ở nhánh đầu của một course.
- Cách hỏi: xử lý sự cố
- Hỏi: Ở một bảng course, Address 9 và 10 được cấu hình như thế nào?
- Đáp: Address 9 là 72,79,143,3,65; Address 10 là 0,102,72,79,143,153,30,65. Đây là một trong các biến thể course trong file 16/3. Nguồn file: CTUマップ再検討20260316.xlsx.

## CÂU HỎI 413
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师怀疑Address 32和34都是普通直行Task。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Address 32和34是否与普通的Address 31/33相同？
- Đáp: 不同。Address 32为0,67,73,77,143,10,65，Address 34为0,67,72,77,143,30,65；而31是73,77,143,10,65，33是72,77,143,10,65。来源文件：CTUマップ再検討20260316.xlsx.

## CÂU HỎI 414
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Address 35～42の繰り返しPatternを確認している。
- Cách hỏi: trực tiếp
- Hỏi: Address 35～42にはどのような交互Patternがありますか。
- Đáp: 35=72,77,142,15,65、36=72,77,143,30,65で、その後37/38、39/40、41/42も同じ2種類のPatternが交互に繰り返されています。出典ファイル：CTUマップ再検討20260316.xlsx.

## CÂU HỎI 415
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh Address 44 và 45 ở đoạn chuyển tuyến.
- Cách hỏi: so sánh
- Hỏi: Address 44 và 45 khác nhau thế nào?
- Đáp: Address 44 là 72,79,143,10,65; Address 45 là 0,101,72,79,143,153,30,65. Address 45 có thêm các task 0, 101, 153 và dùng giá trị 30 thay cho 10. Nguồn file: CTUマップ再検討20260316.xlsx.

## CÂU HỎI 416
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师核对3月16日版与12月15日版的典型Task。
- Cách hỏi: so sánh
- Hỏi: 当前读取到的Address 1～8在3/16版和12/15版有明显变化吗？
- Đáp: 在已读取到的Task表中，Address 1～8的序列与12/15版相同，例如Address 2仍为0,151,147,98,79,153,15,65。因此这部分没有确认到差异。来源文件：CTUマップ再検討20260316.xlsx.

## CÂU HỎI 417
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 日付だけを見て3/16版には必ず大きなTask変更があると思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File名が20260316になっているため、12/15版から全Addressが変更されたと判断できますか。
- Đáp: いいえ。抽出された複数のTask列は12/15版と同じ部分が多く、少なくともAddress 1～8、31～53の代表Patternでは大きな差分を確認できません。日付だけで変更範囲を断定してはいけません。出典ファイル：CTUマップ再検討20260316.xlsx.

## CÂU HỎI 418
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xác nhận kết thúc course trong map 16/3.
- Cách hỏi: trực tiếp
- Hỏi: Các bảng course trong file 16/3 kết thúc bằng cấu trúc nào?
- Đáp: Các bảng trích xuất đều kết thúc bằng Map 1 / Task 0, sau đó là dòng End, giống cấu trúc map được thấy trong bản 12/15. Nguồn file: CTUマップ再検討20260316.xlsx.

## CÂU HỎI 419
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师正在确认3月17日版的基础Address序列。
- Cách hỏi: trực tiếp
- Hỏi: 3/17版Address 1的Task是什么？
- Đáp: Address 1为72,79,143,10,65。来源文件：CTUマップ再検討20260317.xlsx.

## CÂU HỎI 420
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: Address 2のQR照合／Arm復帰関連Taskを確認している。
- Cách hỏi: tình huống
- Hỏi: Address 2にはTask 151と153が含まれていますか。
- Đáp: はい。Address 2は0,151,147,98,79,153,15,65です。出典ファイル：CTUマップ再検討20260317.xlsx.

## CÂU HỎI 421
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đối chiếu map 16/3 và 17/3 để tìm thay đổi ngay ngày hôm sau.
- Cách hỏi: so sánh
- Hỏi: Trong phần Task đã đọc được, Address 1–8 của bản 17/3 có khác bản 16/3 không?
- Đáp: Không thấy khác biệt trong phần trích xuất. Cả hai bản đều có cùng chuỗi cho Address 1–8; ví dụ Address 3=72,77,142,15,65, Address 4=72,77,143,30,65, Address 8=72,79,143,30,65. Nguồn file: CTUマップ再検討20260317.xlsx.

## CÂU HỎI 422
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较两个连续Course的分岐Address。
- Cách hỏi: so sánh
- Hỏi: 某两个Course中9→10和9→11有什么区别？
- Đáp: 两个表都先经过Address 9=72,79,143,3,65；一个Course接Address 10=0,102,72,79,143,153,30,65，另一个接Address 11，且Address 11使用相同的Task序列。来源文件：CTUマップ再検討20260317.xlsx.

## CÂU HỎI 423
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 3/17版でCourseごとのAddressシフトを確認している。
- Cách hỏi: tình huống
- Hỏi: Courseが変わると分岐部のAddressはどのように変化しますか。
- Đáp: 抽出された表では、9→10、9→11、12→13、13→14、14→15、15→16のようにCourseごとに分岐部分のAddressがずれていきます。一方、31以降の共通部は同じPatternが多く使われています。出典ファイル：CTUマップ再検討20260317.xlsx.

## CÂU HỎI 424
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: CTU dừng bất thường ở Address 32.
- Cách hỏi: xử lý sự cố
- Hỏi: Address 32 trong bản 17/3 dùng task sequence nào để đối chiếu?
- Đáp: Address 32 dùng 0,67,73,77,143,10,65. Có thể so với Address 31=73,77,143,10,65 để thấy Address 32 có thêm 0,67. Nguồn file: CTUマップ再検討20260317.xlsx.

## CÂU HỎI 425
- Khối: MOM
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认Address 46是否与Address 35的速度Pattern相同。
- Cách hỏi: so sánh
- Hỏi: Address 46与Address 35的Task相同吗？
- Đáp: 不完全相同。Address 46=72,77,142,30,65，而Address 35=72,77,142,15,65；主要差异是数值30与15。来源文件：CTUマップ再検討20260317.xlsx.

## CÂU HỎI 426
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 3/17版でAddress 53の特殊Sequenceを確認している。
- Cách hỏi: trực tiếp
- Hỏi: Address 53にはどのTaskが設定されていますか。
- Đáp: 0,90,10,64,72,79,143,10,65です。通常の短いAddressより多くのTaskを含んでいます。出典ファイル：CTUマップ再検討20260317.xlsx.

## CÂU HỎI 427
- Khối: MOM
- Ngôn ngữ: vi
- Bối cảnh: Người mới cho rằng bản 17/3 chắc chắn đã thay toàn bộ logic của bản 16/3.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Có thể khẳng định bản 17/3 đã thay đổi toàn bộ các tuyến so với 16/3 không?
- Đáp: Không. Trong phần dữ liệu đọc được, nhiều bảng Map/Task của 16/3 và 17/3 giống nhau, từ Address 1–8 đến nhiều pattern Address 31–53. Vì file không có bảng revision chỉ rõ thay đổi, không nên khẳng định phạm vi sửa chỉ dựa vào ngày tên file. Nguồn file: CTUマップ再検討20260317.xlsx.

## CÂU HỎI 428
- Khối: MOM
- Ngôn ngữ: ja
- Bối cảnh: 3/16版と3/17版の変更点を正式報告しようとしている。
- Cách hỏi: xử lý sự cố
- Hỏi: 3/16→3/17の変更点を報告する場合、どのように扱うべきですか。
- Đáp: 現在読み取れたTask表だけでは、代表的なAddress Sequenceに明確な差分を確認できません。したがって「3/17でこのTaskを変更した」と断定せず、変更点は未確認として、Excelの全Sheet・セル差分を直接比較してから確定する必要があります。出典ファイル：CTUマップ再検討20260317.xlsx.
