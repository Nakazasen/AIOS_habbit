# Mẻ LSU 24 — 50 cặp (ChatGPT GPT-5.6 Sol, 2026-10-04)
Trạng thái: Bản thảo — chưa qua chuyên gia duyệt. Khối: LSU.
5 CSV đầu của `Iris LSU/thu nghiem 6pcs do thong so va log/2ND-1002_JIG BEAM`, mỗi file 10 cặp, câu 959–1008.
(#1_2026_08_xyAdjust_Log.csv, 2026_08_Black_Depth_Master.csv, 2026_08_Black_Depth_UniteTest.csv, 2026_08_Black_Depth.csv, 2026_08_Cyan_Depth_Master.csv)
1 lần "Phân tích bị lỗi" nhưng ChatGPT tự phục hồi, đủ 50 cặp. Không gián đoạn, không giới hạn Plus.
Lưu ý kỹ thuật: giá trị 999/0/-- không được file định nghĩa — các cặp ghi nhận nguyên văn như Raw value, không tự gán ý nghĩa.

## File 1 — `#1_2026_08_xyAdjust_Log.csv` → Q959–968

## CÂU HỎI 959
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang xác nhận quy mô log XY Adjustment của Jig Beam #1.
- Cách hỏi: trực tiếp
- Hỏi: File có bao nhiêu record, bao nhiêu Serial và phạm vi ngày nào?
- Đáp: File có `2.982 record`, gồm `2.799 Serial` khác nhau, từ `2026/08/01` đến `2026/08/26`. Toàn bộ record dùng JigNumber=`#1`. Nguồn file: `#1_2026_08_xyAdjust_Log.csv`.

## CÂU HỎI 960
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较XY Adjustment Log中的Unit Type分布。
- Cách hỏi: so sánh
- Hỏi: `Color_2Beam`、`Color_4Beam`、`Mono_4Beam`分别有多少笔？
- Đáp: `Color_2Beam = 1,514笔`、`Color_4Beam = 1,187笔`、`Mono_4Beam = 281笔`。来源文件：`#1_2026_08_xyAdjust_Log.csv`.

## CÂU HỎI 961
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 8月1日の最初のXY調整Recordを確認している。
- Cách hỏi: tình huống
- Hỏi: 最初のRecordのUnit TypeとSerialは何ですか。
- Đáp: `2026/08/01 06:23:18`、UnitType=`Color_2Beam`、Serial=`C9P1068V0819`です。出典ファイル：`#1_2026_08_xyAdjust_Log.csv`.

## CÂU HỎI 962
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra quá trình điều chỉnh K của record đầu tiên.
- Cách hỏi: xử lý sự cố
- Hỏi: Giá trị K thay đổi thế nào từ Init tới RoughAdj1 và địa chỉ Stage cuối?
- Đáp: Record đầu có `X_Init_K=6427`, `Y_Init_K=2934`; sau RoughAdj1 là `6404/2938`. Địa chỉ Stage ban đầu là X=`-2500`, Y=`-53150`, còn khi OK là X=`-2362`, Y=`-53569`, tức chênh X=`+138`, Y=`-419`. Nguồn file: `#1_2026_08_xyAdjust_Log.csv`.

## CÂU HỎI 963
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较首笔记录中四色最终Stage地址变化。
- Cách hỏi: so sánh
- Hỏi: K、M、C、Y从Init到OK的Stage Address变化量分别是多少？
- Đáp: 第一笔记录中：K=`X +138 / Y -419`；M=`X +40 / Y -418`；C=`X +39 / Y +187`；Y=`X +257 / Y -305`。来源文件：`#1_2026_08_xyAdjust_Log.csv`.

## CÂU HỎI 964
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: RoughAdj2がどの色で多く使われているか確認している。
- Cách hỏi: trực tiếp
- Hỏi: RoughAdj2が0以外になっているRecord数は色別にいくつですか。
- Đáp: K=`885件`、M=`800件`、C=`559件`、Y=`695件`です。全2,982件に対して約`29.7% / 26.8% / 18.7% / 23.3%`です。出典ファイル：`#1_2026_08_xyAdjust_Log.csv`.

## CÂU HỎI 965
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tìm Unit được đo lặp nhiều nhất để kiểm tra tính lặp lại.
- Cách hỏi: tình huống
- Hỏi: Serial nào xuất hiện nhiều nhất?
- Đáp: Serial `61C1068E7477` xuất hiện `6 lần`, nhiều nhất trong file. Tiếp theo là `61C1068E7782` và `61C1068E8399`, mỗi Serial `5 lần`. Nguồn file: `#1_2026_08_xyAdjust_Log.csv`.

## CÂU HỎI 966
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师分析哪一天XY调整量最大。
- Cách hỏi: xử lý sự cố
- Hỏi: 哪一天的Record数最多？
- Đáp: `2026/08/06`最多，共`190笔`；之后是`08/13=187`、`08/19=184`、`08/22=183`、`08/18=181`。来源文件：`#1_2026_08_xyAdjust_Log.csv`.

## CÂU HỎI 967
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 新人がRoughAdj2=0を「調整失敗」と判断しようとしている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: RoughAdj2が0なら、その色は調整失敗と判断できますか。
- Đáp: できません。FileにはRoughAdj2値とStage Addressはありますが、`0 = 調整失敗`という定義はありません。例えば最初のRecordではK/M/CのRoughAdj2が0でも最終OK Stage Addressが記録されています。出典ファイル：`#1_2026_08_xyAdjust_Log.csv`.

## CÂU HỎI 968
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn kiểm tra record cuối của chuỗi log.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File kết thúc ngày 25/8 phải không?
- Đáp: Không. Record cuối là `2026/08/26 09:41:13`, UnitType=`Color_2Beam`, Serial=`C9P1068V6694`. Nguồn file: `#1_2026_08_xyAdjust_Log.csv`.

---

## File 2 — `2026_08_Black_Depth_Master.csv` → Q969–978

## CÂU HỎI 969
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认Black Master Depth文件的规模。
- Cách hỏi: trực tiếp
- Hỏi: 文件共有多少个Master测量Block、多少个Serial？
- Đáp: 共`28个Master Block`，涉及`2个Serial`：`61C1047Z3311`和`61C1047Z3321`。日期范围为`2026/08/01～2026/08/22`。来源文件：`2026_08_Black_Depth_Master.csv`.

## CÂU HỎI 970
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Master Serial別の測定回数を比較している。
- Cách hỏi: so sánh
- Hỏi: 2つのSerialはそれぞれ何回測定されていますか。
- Đáp: `61C1047Z3311 = 15回`、`61C1047Z3321 = 13回`です。出典ファイル：`2026_08_Black_Depth_Master.csv`.

## CÂU HỎI 971
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra record Master Black đầu tiên tại Camera trung tâm.
- Cách hỏi: tình huống
- Hỏi: BeamLd1H tại `CAM_PM0` có giá trị -2, -1 và ±0 bao nhiêu?
- Đáp: Record đầu `2026/08/01 06:02:06`, Serial=`61C1047Z3311`: BeamLd1H tại CAM_PM0 có `-2=56`, `-1=55`, `±0=56`. Nguồn file: `2026_08_Black_Depth_Master.csv`.

## CÂU HỎI 972
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较第一笔Master中LD1的H/V。
- Cách hỏi: so sánh
- Hỏi: CAM_PM0、±0位置的BeamLd1H和BeamLd1V分别是多少？
- Đáp: BeamLd1H=`56`，BeamLd1V=`64`，V比H大`8`。来源文件：`2026_08_Black_Depth_Master.csv`.

## CÂU HỎI 973
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 4つのLDの中心H値を比較している。
- Cách hỏi: trực tiếp
- Hỏi: 最初のMasterでCAM_PM0、±0のLD1～LD4 Hはいくつですか。
- Đáp: LD1H=`56`、LD2H=`56`、LD3H=`56`、LD4H=`58`です。出典ファイル：`2026_08_Black_Depth_Master.csv`.

## CÂU HỎI 974
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn biết mức dao động của điểm trung tâm Master Black.
- Cách hỏi: xử lý sự cố
- Hỏi: BeamLd1H tại CAM_PM0, ±0 dao động trong khoảng nào trên 28 block?
- Đáp: Giá trị nhỏ nhất=`53`, lớn nhất=`57`, trung bình khoảng`54,96`. Đây là thống kê Raw value của trường này; file không tự định nghĩa ngưỡng OK/NG cho phép đo này. Nguồn file: `2026_08_Black_Depth_Master.csv`.

## CÂU HỎI 975
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看最后一个Black Master Block。
- Cách hỏi: tình huống
- Hỏi: 最后一笔的Serial、时间以及BeamLd1H中心值是什么？
- Đáp: 最后一笔为`2026/08/22 06:20:16`、Serial=`61C1047Z3321`；CAM_PM0的BeamLd1H为`-2=58、-1=55、±0=53`。来源文件：`2026_08_Black_Depth_Master.csv`.

## CÂU HỎI 976
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初と最後のLD1H中心値を比較している。
- Cách hỏi: so sánh
- Hỏi: CAM_PM0、±0のBeamLd1Hは最初と最後でどう変化しましたか。
- Đáp: 最初は`56`、最後は`53`で、Raw値では`3`小さくなっています。出典ファイル：`2026_08_Black_Depth_Master.csv`.

## CÂU HỎI 977
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Người mới thấy `--` ở nhiều Depth và muốn coi đó là NG.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Có thể kết luận `--` trong bảng Depth là NG không?
- Đáp: Không. File sử dụng `--` ở nhiều vị trí Depth nhưng không định nghĩa `-- = NG`. Chỉ nên ghi nhận đây là giá trị hiển thị trong log cho tới khi có spec giải thích. Nguồn file: `2026_08_Black_Depth_Master.csv`.

## CÂU HỎI 978
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 新人认为Black Master只测LD1。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Master文件只包含LD1的Beam数据吗？
- Đáp: 不是。完整Block包含`BeamLd1H/V、BeamLd2H/V、BeamLd3H/V、BeamLd4H/V`，即4个LD、H/V两个方向。来源文件：`2026_08_Black_Depth_Master.csv`.

---

## File 3 — `2026_08_Black_Depth_UniteTest.csv` → Q979–988

## CÂU HỎI 979
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Black Unit Test Depthの全体構成を確認している。
- Cách hỏi: trực tiếp
- Hỏi: このFileには何Block、何Serialありますか。
- Đáp: `99 Block`、`88個の異なるSerial`があり、期間は`2026/08/01～2026/08/26`です。出典ファイル：`2026_08_Black_Depth_UniteTest.csv`.

## CÂU HỎI 980
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư phân biệt hai Mode Unit Test trong file.
- Cách hỏi: so sánh
- Hỏi: `UnitTestAllColor` và `UnitTestOneColor` có bao nhiêu block?
- Đáp: `UnitTestAllColor=57 block`, `UnitTestOneColor=42 block`. Nguồn file: `2026_08_Black_Depth_UniteTest.csv`.

## CÂU HỎI 981
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看第一笔OneColor测试。
- Cách hỏi: tình huống
- Hỏi: 第一笔记录是什么时间、Serial以及中心BeamLd1H值？
- Đáp: `2026/08/01 06:35:40`，Serial=`C9P1068V0820`，Mode=`UnitTestOneColor`；CAM_PM0的BeamLd1H为`-2=61、-1=63、±0=69`。来源文件：`2026_08_Black_Depth_UniteTest.csv`.

## CÂU HỎI 982
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初のUnitTestでLD1 H/Vを比較している。
- Cách hỏi: so sánh
- Hỏi: CAM_PM0、±0のBeamLd1HとBeamLd1Vはいくつですか。
- Đáp: BeamLd1H=`69`、BeamLd1V=`66`で、Raw値ではHの方が`3`大きいです。出典ファイル：`2026_08_Black_Depth_UniteTest.csv`.

## CÂU HỎI 983
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy có block dài và ngắn khác nhau.
- Cách hỏi: xử lý sự cố
- Hỏi: File có hai cấu trúc block chính nào?
- Đáp: Có`73 block` dài khoảng`49 dòng` và`25 block` dài khoảng`25 dòng`; ngoài ra block cuối có`24 dòng` do kết thúc file. Block 25 dòng chứa các mục BeamLd1H/V và BeamLd2H/V; block 49 dòng có thêm LD3H/V và LD4H/V. Nguồn file: `2026_08_Black_Depth_UniteTest.csv`.

## CÂU HỎI 984
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师想确认Block长度是否等同于测试Mode。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 25行Block是否全部都是UnitTestOneColor？
- Đáp: 不是。25行Block中有`19个UnitTestAllColor`和`6个UnitTestOneColor`。因此不能仅根据Block长度判断Mode。来源文件：`2026_08_Black_Depth_UniteTest.csv`.

## CÂU HỎI 985
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Unit Testが集中した日を確認している。
- Cách hỏi: trực tiếp
- Hỏi: Block数が最も多い日はいつですか。
- Đáp: `2026/08/13`と`2026/08/18`がそれぞれ`10 Block`で最多です。出典ファイル：`2026_08_Black_Depth_UniteTest.csv`.

## CÂU HỎI 986
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra record cuối của Black Unit Test.
- Cách hỏi: tình huống
- Hỏi: Record cuối có thông tin gì?
- Đáp: Record cuối là`2026/08/26 04:47:32`, Serial=`C9P1068V6538`, Mode=`UnitTestAllColor`; CAM_PM0 BeamLd1H có `-2=60`, `-1=61`, `±0=63`. Nguồn file: `2026_08_Black_Depth_UniteTest.csv`.

## CÂU HỎI 987
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现中心值中出现999。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以把BeamLd1H中心统计中的`999`直接算作正常Beam径吗？
- Đáp: 不应这样处理。文件中确实存在`999`，但没有定义它的业务含义；因此分析时必须保留为未解释的Raw值，不能自行归类为正常、NG或真实Beam径。来源文件：`2026_08_Black_Depth_UniteTest.csv`.

## CÂU HỎI 988
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 新人が同じSerialは必ず1回だけ測定されると思っている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: UnitTest Fileでは各Serialは必ず1回だけですか。
- Đáp: いいえ。99 Blockに対して異なるSerialは88個で、複数回登場するSerialがあります。例えば`61C1068E6482`や`61C1068E6549`などは各`2回`記録されています。出典ファイル：`2026_08_Black_Depth_UniteTest.csv`.

---

## File 4 — `2026_08_Black_Depth.csv` → Q989–998

## CÂU HỎI 989
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang xác nhận quy mô Black Depth tổng của Jig Beam #1.
- Cách hỏi: trực tiếp
- Hỏi: File có bao nhiêu block và bao nhiêu Serial khác nhau?
- Đáp: File có`2.596 block`, gồm`2.517 Serial` khác nhau, từ`2026/08/01` đến`2026/08/26`. Nguồn file: `2026_08_Black_Depth.csv`.

## CÂU HỎI 990
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Black Depth中的Auto和Master。
- Cách hỏi: so sánh
- Hỏi: 两种Mode分别有多少Block？
- Đáp: `Auto=2,452 Block`，`Master=144 Block`。来源文件：`2026_08_Black_Depth.csv`.

## CÂU HỎI 991
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初のAuto測定を確認している。
- Cách hỏi: tình huống
- Hỏi: 最初のRecordは何時、どのSerialですか。
- Đáp: `2026/08/01 06:19:22`、Serial=`C9P1068V0819`、Mode=`Auto`です。出典ファイル：`2026_08_Black_Depth.csv`.

## CÂU HỎI 992
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đọc BeamLd1H của record đầu tại Camera trung tâm.
- Cách hỏi: trực tiếp
- Hỏi: Giá trị -2, -1 và ±0 tại CAM_PM0 là bao nhiêu?
- Đáp: BeamLd1H có `-2=61`, `-1=63`, `±0=68`. Nguồn file: `2026_08_Black_Depth.csv`.

## CÂU HỎI 993
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较首笔Black的H/V。
- Cách hỏi: so sánh
- Hỏi: CAM_PM0、±0的BeamLd1H和BeamLd1V分别是多少？
- Đáp: BeamLd1H=`68`，BeamLd1V=`67`，相差`1`。来源文件：`2026_08_Black_Depth.csv`.

## CÂU HỎI 994
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 日別Block数が急増した日を調べている。
- Cách hỏi: xử lý sự cố
- Hỏi: 最もBlock数が多い日はいつですか。
- Đáp: `2026/08/06`で`176 Block`です。次に`08/19=172`、`08/07=158`、`08/13=155`、`08/21=154`です。出典ファイル：`2026_08_Black_Depth.csv`.

## CÂU HỎI 995
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xem cấu trúc dữ liệu LD trong toàn file.
- Cách hỏi: so sánh
- Hỏi: Block ngắn và block đầy đủ phân bố thế nào?
- Đáp: Có`1.411 block` khoảng25 dòng và`1.184 block` khoảng49 dòng; block cuối có24 dòng. Block ngắn chủ yếu chứa LD1/LD2 H/V, còn block đầy đủ có LD1–LD4 H/V. Nguồn file: `2026_08_Black_Depth.csv`.

## CÂU HỎI 996
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看最后一笔Auto数据。
- Cách hỏi: tình huống
- Hỏi: 最后一笔记录是什么时间、Serial和中心值？
- Đáp: `2026/08/26 09:36:14`，Serial=`C9P1068V6694`，Mode=`Auto`；CAM_PM0 BeamLd1H为`-2=60、-1=61、±0=63`。来源文件：`2026_08_Black_Depth.csv`.

## CÂU HỎI 997
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 全Blockの中心BeamLd1H分布を確認している。
- Cách hỏi: trực tiếp
- Hỏi: CAM_PM0、±0のBeamLd1HのRaw値範囲はいくつですか。
- Đáp: 全2,596 Blockでは最小=`54`、最大=`108`、平均約=`62.38`です。これはRaw値の集計であり、このFile単独ではOK/NG閾値を示していません。出典ファイル：`2026_08_Black_Depth.csv`.

## CÂU HỎI 998
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Người mới thấy Mode Master nằm trong file Black Depth chung và cho rằng tất cả block đều là sản phẩm sản xuất.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Có thể coi toàn bộ 2.596 block đều là Auto production data không?
- Đáp: Không. File gồm`2.452 Auto` và`144 Master` block, nên phải tách Mode trước khi phân tích production trend. Nguồn file: `2026_08_Black_Depth.csv`.

---

## File 5 — `2026_08_Cyan_Depth_Master.csv` → Q999–1008

## CÂU HỎI 999
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认Cyan Master Depth的数据规模。
- Cách hỏi: trực tiếp
- Hỏi: Cyan Master共有多少Block、多少Serial？
- Đáp: 共`28个Master Block`，涉及`2个Serial`：`61C1047Z3311`和`61C1047Z3321`，期间为`2026/08/01～2026/08/22`。来源文件：`2026_08_Cyan_Depth_Master.csv`.

## CÂU HỎI 1000
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Serial別のMaster測定回数を比較している。
- Cách hỏi: so sánh
- Hỏi: 3311と3321はそれぞれ何回測定されていますか。
- Đáp: `61C1047Z3311=15回`、`61C1047Z3321=13回`です。出典ファイル：`2026_08_Cyan_Depth_Master.csv`.

## CÂU HỎI 1001
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đọc record Cyan Master đầu tiên.
- Cách hỏi: tình huống
- Hỏi: Record đầu có thời gian và Serial nào?
- Đáp: `2026/08/01 06:03:27`, Serial=`61C1047Z3311`, Mode=`Master`. Nguồn file: `2026_08_Cyan_Depth_Master.csv`.

## CÂU HỎI 1002
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认第一笔Cyan Master的中心BeamLd1H。
- Cách hỏi: trực tiếp
- Hỏi: CAM_PM0的-2、-1、±0值分别是多少？
- Đáp: BeamLd1H为`-2=54、-1=55、±0=57`。来源文件：`2026_08_Cyan_Depth_Master.csv`.

## CÂU HỎI 1003
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最初のCyan MasterでLD1 H/Vを比較している。
- Cách hỏi: so sánh
- Hỏi: CAM_PM0、±0のBeamLd1HとVはいくつですか。
- Đáp: BeamLd1H=`57`、BeamLd1V=`66`で、VのRaw値が`9`大きいです。出典ファイル：`2026_08_Cyan_Depth_Master.csv`.

## CÂU HỎI 1004
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so 4 LD tại điểm trung tâm của record đầu.
- Cách hỏi: trực tiếp
- Hỏi: Beam H của LD1–LD4 tại CAM_PM0, ±0 lần lượt bao nhiêu?
- Đáp: LD1H=`57`, LD2H=`55`, LD3H=`54`, LD4H=`55`. Nguồn file: `2026_08_Cyan_Depth_Master.csv`.

## CÂU HỎI 1005
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师监控Cyan Master中心值的波动。
- Cách hỏi: xử lý sự cố
- Hỏi: 28个Block中BeamLd1H在CAM_PM0、±0的范围是多少？
- Đáp: 最小=`55`、最大=`59`、平均约=`56.71`。这些是Raw测量值，文件本身没有给出该字段的OK/NG界限。来源文件：`2026_08_Cyan_Depth_Master.csv`.

## CÂU HỎI 1006
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 最終Master Recordを確認している。
- Cách hỏi: tình huống
- Hỏi: 最後のRecordの日時、Serial、LD1H中心値は何ですか。
- Đáp: `2026/08/22 06:21:40`、Serial=`61C1047Z3321`。CAM_PM0 BeamLd1Hは`-2=54、-1=55、±0=55`です。出典ファイル：`2026_08_Cyan_Depth_Master.csv`.

## CÂU HỎI 1007
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so record đầu và cuối Cyan Master.
- Cách hỏi: so sánh
- Hỏi: BeamLd1H tại CAM_PM0, ±0 thay đổi thế nào?
- Đáp: Record đầu=`57`, record cuối=`55`, tức Raw value cuối thấp hơn`2`. Nguồn file: `2026_08_Cyan_Depth_Master.csv`.

## CÂU HỎI 1008
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 新人看到Master文件中的0和`--`后准备直接判NG。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 可以把文件中的`0`或`--`直接定义成NG吗？
- Đáp: 不可以。该CSV记录了`0`和`--`，但没有在文件内定义它们的判定含义。必须依据另外的Jig规格或Log定义确认，不能自行赋予NG含义。来源文件：`2026_08_Cyan_Depth_Master.csv`.

## Kiểm tra chất lượng (ChatGPT tự báo)
- Phân bố ngôn ngữ: vi 17 / zh 17 / ja 16 (trộn đều).
- Mỗi file 10 cặp, đủ cả 5 cách hỏi.
- Không file nào bị bỏ qua; không bịa số liệu.
- Giá trị 999/0/-- được ghi nhận nguyên văn như Raw value, không tự gán ý nghĩa nghiệp vụ.
