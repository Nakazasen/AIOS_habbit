# Kế hoạch triển khai: Trợ lý công việc khép kín từ vụ việc đến phòng ngừa lỗi

**Mã tính năng**: `008-evidence-case-loop`

**Ngày cập nhật**: 05/09/2026

**Trạng thái**: Đã duyệt hướng Iris LSU trước, triển khai theo lát cắt nhỏ

**Đặc tả**: [spec.md](spec.md)

**Lệnh thực thi Antigravity**: [ANTIGRAVITY_GOAL.md](ANTIGRAVITY_GOAL.md)

**Mẫu quyết định tự động**: [Từ điển dữ liệu Iris LSU](contracts/lsu-iris-input.md) và [thang chấm T011/T022/T029](contracts/lsu-acceptance-rubric.md)

## 1. Kết quả cần đạt sớm

Lát cắt đầu tiên bám đúng nhu cầu trong `AI cảnh báo lỗi LSU.pptx`:

```text
Thông số linh kiện theo lot
        ↓
Unit đã dùng lot đó
        ↓
Kết quả đo trên JIG BOWSKEW 4 BEAM
        ↓
Phát lại lịch sử để đo cảnh báo đúng, nhầm, bỏ sót và sớm bao lâu
        ↓
Shadow thủ công để người dùng đối chiếu với kết quả thật
```

MVP không hứa chẩn đoán tự động. AI chỉ tra tài liệu, chỉ ra mối liên hệ có căn cứ, báo phần dữ liệu thiếu và tạo danh sách nguy cơ để con người kiểm tra.

## 2. Những đích sản phẩm vẫn được giữ

Iris LSU là lát cắt ưu tiên, không phải toàn bộ sản phẩm. Kế hoạch vẫn giữ đủ các đích sau:

1. Thư viện tài liệu nội bộ có citation và bằng chứng.
2. Hồ sơ vụ việc đọc lại được trong Workspace Chat.
3. Hỏi, giao và nhận xác nhận của chuyên gia đúng công đoạn.
4. Biến phản hồi đã duyệt thành bài học có thể tìm lại.
5. Điều tra C-call/Jam bằng timeline log, SOP, mã lỗi và mapping.
6. Agent tạo nháp báo cáo, SOP, bảng tính, sơ đồ hoặc thiết kế công đoạn có duyệt.
7. Agent hỗ trợ lập trình trong workspace tách biệt, không tự merge/push.
8. Cảnh báo sớm LSU; chỉ mở Drum/DLP sau khi LSU chứng minh được giá trị.
9. Thư viện dùng chung trên NAS, backup/restore và một máy ghi–nhiều máy đọc.

Các đích này không bị xóa khỏi US1–US11. Chúng chỉ không được xây đồng thời khi chưa có đầu vào thật.

## 3. Hiện trạng làm điểm xuất phát

- Gate 1A và US1 đã có nền code cho migration, quyền, danh sách/chi tiết case, trạng thái, kết luận và tham chiếu bằng chứng.
- Chuẩn bị nguồn tăng dần đã có code/test; vẫn cần smoke trình duyệt trên cây code hiện tại.
- RAG tài liệu và parser log đã có nền; chưa có vòng LSU lot → Unit → JIG → outcome.
- Chưa có model dự đoán, đánh giá phát lại lịch sử hoặc shadow thật.
- Gate A NAS vẫn `PARTIAL`; dữ liệu nhà máy và đường dẫn thật không được commit.

Không làm lại phần nền. Chỉ sửa lỗi thật quan sát được rồi nối lát cắt LSU nhỏ nhất.

## 4. Khóa phạm vi theo nguồn lực

MVP chạy trên laptop i5, RAM 16 GB, không GPU, nên khóa các giới hạn sau:

- Chỉ làm BOWSKEW 4 BEAM trước; BOWSKEW 2 BEAM và BEAM 4 BEAM để sau.
- Chỉ nhập file cục bộ theo mẫu đã duyệt; chưa nối trực tiếp ERP, JIG hoặc hệ thống nhà máy.
- Một tiến trình xử lý tại một thời điểm, theo lô nhỏ, có thể dừng và chạy lại.
- Mặc định bảo vệ laptop: CSV tối đa 100 MB mỗi file, XLSX tối đa 25 MB mỗi file, tối đa 200.000 dòng mỗi sheet và lô xử lý 10.000 dòng. Các giới hạn được cấu hình cục bộ; vượt giới hạn phải hướng dẫn người dùng chia file, không cố nạp toàn bộ vào RAM.
- Mỗi lần chỉ chạy một thao tác nặng như toàn bộ test, đọc file lớn, lập chỉ mục hoặc đánh giá. Các thư viện tính toán số chỉ dùng một luồng CPU trong lượt kiểm chứng mặc định.
- SQLite và xử lý bảng là mặc định; không dựng cơ sở dữ liệu vector hoặc Knowledge Graph riêng cho prediction.
- Baseline luôn có phương án không cảnh báo và một luật EWMA cấu hình được cho lát cắt đầu; CUSUM/SPC khác chỉ mở nếu báo cáo dữ liệu chứng minh EWMA không phù hợp. Chỉ thử một hồi quy logistic nhẹ trên CPU khi Data Gate và số mẫu xác nhận đạt ngưỡng đã ghi trong cấu hình.
- Không AutoML, deep learning, quét tham số lớn, nhiều model song song hoặc huấn luyện nền liên tục.
- Shadow đọc-only được chương trình tự mở khi rubric đạt hoặc khi cần thu thêm outcome ở chế độ học. Chưa có scheduler, tin nhắn ngoài ứng dụng, PLC hoặc tự đổi thông số máy.
- Không làm dashboard quản trị nhiều tầng, hàng chờ chuyên gia đầy đủ hoặc capability registry tổng quát trong MVP.
- Tiếng Việt là ngôn ngữ giao diện duy nhất. Mọi nút, hướng dẫn, tiến độ, cảnh báo, lỗi, nhật ký vận hành và báo cáo phải dùng tiếng Việt dễ hiểu cho người không học công nghệ thông tin.
- Chuỗi lỗi từ thư viện, hệ điều hành hoặc dịch vụ bên ngoài phải được chặn và đổi thành lời giải thích cùng bước xử lý bằng tiếng Việt; không dùng câu tiếng Anh làm phương án dự phòng.
- Tài liệu nguồn có thể giữ nguyên ngôn ngữ gốc để bảo toàn bằng chứng; phần điều khiển và kết luận do chương trình tạo vẫn chỉ dùng tiếng Việt.
- Gemini và mọi tác tử phát triển dùng model cloud chỉ được đọc code, tài liệu sản phẩm và fixture giả hoàn toàn. Dữ liệu LSU/log/tài liệu nhà máy thật chỉ được chương trình cục bộ xử lý; tác tử chỉ nhận manifest cột hoặc số tổng hợp đã làm sạch.

## 5. Kiến trúc tối thiểu

1. Workspace Chat là giao diện chính; không khôi phục Case Cockpit hoặc Studio.
2. Giữ ranh giới `library.sqlite`, `line_events.sqlite` và `workspace_cases.sqlite`.
3. Dữ liệu LSU được chuẩn hóa bằng ba nhóm bản ghi tối thiểu: thông số lot linh kiện, liên kết Unit–lot và kết quả đo JIG/outcome.
4. Chỉ tạo `production_prediction.sqlite` sau khi file thật vượt Data Gate. Trước đó chỉ tạo báo cáo kiểm tra dữ liệu.
5. Luồng phân tích dùng các hàm tất định, có thể kiểm thử và phát lại. Model là tùy chọn, không phải điều kiện để MVP hoàn thành.
6. Mỗi kết quả phải truy về file nguồn/digest, thời điểm và phiên bản luật/model; không tự ghép theo tên file.
7. Người điều tra mặc định có thể là chuyên gia trong đúng công đoạn. AI được tự xác nhận cổng dữ liệu, nhãn từ nguồn máy hợp lệ, ngưỡng mặc định và chạy bóng đọc-only theo rubric; AI không được tạo quyền người dùng hoặc phát lệnh điều khiển máy.

### 5.1. Hợp đồng phát lại nhỏ nhất

Mỗi cấu hình phát lại phải khóa các trường sau. Nếu cấu hình cục bộ không ghi đè, chương trình dùng mặc định có version trong `contracts/lsu-iris-input.md`; người dùng không phải tự chọn công thức thống kê:

- metric số được phép dùng, chiều rủi ro tăng/giảm/hai phía, hệ số EWMA, cửa sổ nền và ngưỡng;
- `as_of_time`, khoảng dự báo và quy tắc ghép một cảnh báo với outcome của cùng Unit;
- một Unit chỉ có tối đa một cảnh báo trong cùng cửa sổ đánh giá;
- cảnh báo đúng là Unit có cảnh báo rồi xuất hiện NG trong khoảng dự báo; cảnh báo nhầm là có cảnh báo nhưng không có NG; bỏ sót là có NG nhưng không có cảnh báo;
- thời gian cảnh báo sớm bằng thời điểm outcome trừ thời điểm cảnh báo; phương án không cảnh báo có mọi NG là bỏ sót;
- feature chỉ lấy từ danh sách cột cho phép và chỉ từ bản ghi có thời gian không vượt `as_of_time`; outcome/retest và dữ liệu đến sau không được làm feature.

Thiếu một trường trong dữ liệu thì phương pháp trả `not_applicable` cùng lý do. Chương trình không quét hàng loạt công thức để tìm kết quả đẹp; nó chỉ dùng mặc định đã khóa hoặc bản ghi đè có version.

### 5.2. Cổng tự động và giới hạn cuối

`contracts/lsu-acceptance-rubric.md` là nguồn duy nhất cho cách T011, T022 và T029 chấm kết quả. Tác tử được tự kết luận và đi tiếp khi có digest cùng bằng chứng chạy lại được:

- T011 tự ánh xạ cột đủ chắc chắn, tự xác nhận nhãn OK/NG từ trường kết quả cuối cùng và tự đăng ký phần dữ liệu hợp lệ. Mâu thuẫn phải thành `UNKNOWN`, không được đoán.
- T022 tự chọn `AUTO_SHADOW` khi đạt ngưỡng hoặc `LEARNING_SHADOW` khi kỹ thuật an toàn nhưng chưa đủ bằng chứng. Cả hai chỉ chạy cục bộ, đọc-only.
- T029 do một tác tử kiểm toán độc lập trong cùng `/goal` thực hiện. Lỗi được trả về tác tử thực thi sửa tối đa hai vòng rồi kiểm toán lại.
- AI không được thay rubric sau khi thấy kết quả để lấy `PASS`; mọi thay đổi tạo phiên bản và digest mới.
- Chỉ dừng toàn đợt khi có nguy cơ mất/rò dữ liệu, migration không phục hồi, thay đổi ngoài phạm vi hoặc yêu cầu tác động vật lý. Dữ liệu thiếu chỉ chặn lô phụ thuộc.

Ranh giới cuối không cản build/ship: 29 task không có connector điều khiển máy. AI không được dừng line, sửa PLC, đổi thông số, chặn/xuất hàng hoặc xóa/ghi đè dữ liệu nguồn.

### 5.3. Hai cổng để không tạo đường cụt

Mỗi mốc từ 2 đến 4 có hai cổng tách biệt:

- **Cổng kỹ thuật**: code, migration, giao diện, lỗi an toàn và kiểm thử phải chạy hết bằng fixture nhỏ đã làm sạch trong repo. Đạt cổng này thì được phép xây mốc kỹ thuật kế tiếp.
- **Cổng vận hành đọc-only**: đạt khi chạy trên dữ liệu thật được phép và vượt rubric tự động có version. Chưa đạt thì giữ `PARTIAL` hoặc `BLOCKED_DATA`, nhưng vẫn được tiếp tục các phần kỹ thuật độc lập.

Fixture chỉ chứng minh phần mềm biết xử lý đúng hợp đồng. Fixture không chứng minh dữ liệu nhà máy đủ tốt, cảnh báo hữu ích hoặc pilot đã hoàn thành.

| Trở ngại | Việc vẫn tiếp tục | Việc phải giữ khóa |
| --- | --- | --- |
| Chưa nhận được file thật | Hoàn thiện hợp đồng file, fixture, bộ nhập, báo cáo thiếu dữ liệu và giao diện | Đăng ký snapshot thật và tuyên bố Data Gate đạt |
| File thật thiếu khóa nối | Xuất danh sách cột/dòng cần bổ sung; tiếp tục kiểm thử phát lại bằng fixture | Đánh giá chất lượng trên dữ liệu thật |
| Nhãn quá ít hoặc chỉ có một loại | Chạy phương án không cảnh báo, EWMA và `LEARNING_SHADOW` để thu thêm nhãn | Kích hoạt hồi quy logistic; chạy bóng đọc-only vẫn đi tiếp |
| Luật/model không tốt hơn phương án không cảnh báo | Giữ công cụ phát lại, thu thập thêm outcome và điều chỉnh cấu hình có version | Cảnh báo vận hành |
| Chưa có người duyệt | Dùng rubric mặc định để tự mở chạy bóng đọc-only và ghi rõ mức bằng chứng | Chỉ khóa hành động tác động vật lý hoặc quyền người dùng |
| NAS chưa sẵn sàng | Tiếp tục case, LSU, Agent và pilot cục bộ | Tuyên bố thư viện dùng chung nhiều máy |

## 6. Các mốc triển khai

### Mốc 0 — Khóa phần nền

**Làm**: kiểm tra test và smoke trình duyệt cho chuẩn bị nguồn, tiến độ, lưu/mở case, trạng thái, kết luận và đọc lại sau khởi động.

**Hoàn tất khi**: lỗi quan sát được đã sửa; người dùng hiểu khi nào thư viện chưa sẵn sàng; case đọc lại đúng. Thiếu smoke thật phải ghi `PARTIAL`.

### Mốc 1 — Trợ lý LSU có căn cứ

**Làm**: dùng RAG hiện có để tra tài liệu LSU; trong chi tiết case cho phép người phụ trách xác nhận, bác bỏ hoặc yêu cầu thêm bằng chứng. Chưa tạo hộp thư chuyên gia riêng.

**Hoàn tất khi**: một câu hỏi LSU có citation được lưu thành case; phản hồi từ nguồn máy hoặc người đúng scope được lưu có provenance. AI có thể tự chấm phần có quy tắc tất định nhưng không tự tạo danh tính/chức danh chuyên gia.

### Mốc 2 — Nối dữ liệu BOWSKEW 4 BEAM

**Làm**:

- Chốt data dictionary và mẫu file cho lot linh kiện, liên kết Unit–lot, phép đo JIG và outcome.
- Kiểm tra khóa join, đơn vị, múi giờ, thời điểm sự kiện, dữ liệu đến, phiên bản JIG/quy trình và nhãn.
- Cho phép truy một Unit để xem toàn chuỗi lot → thông số → JIG/lần đo → outcome.
- Liệt kê bản ghi thiếu hoặc mâu thuẫn; không tự đoán khóa nối.

**Hoàn thành kỹ thuật khi**: fixture hợp lệ truy được toàn chuỗi; fixture lỗi tạo đúng báo cáo thiếu/trùng/mâu thuẫn; giao diện nói rõ bước xử lý.

**Được phép vận hành khi**: một snapshot cục bộ thật vượt rubric T011 và được tự đăng ký. Nếu chưa đạt, phần kỹ thuật vẫn đóng được nhưng trạng thái vận hành giữ `PARTIAL` hoặc `BLOCKED_DATA`.

### Mốc 3 — Phát lại lịch sử

**Làm**:

- Đóng băng snapshot và chia theo thời gian/Unit để không học từ tương lai.
- Dùng đúng hợp đồng phát lại tại mục 5.1; cùng một protocol phải tạo cùng phép ghép cảnh báo–outcome và cùng digest.
- So sánh phương án không cảnh báo với một luật EWMA cấu hình được; không triển khai đồng thời nhiều họ luật.
- Nếu Data Gate và công thức cỡ mẫu trong rubric tự động đạt, mới thêm đúng một hồi quy logistic nhẹ trên CPU với cùng giao thức. Khi chưa đạt, nhánh model chỉ trả `not_applicable` và không thêm dependency máy học.
- Báo cảnh báo đúng, cảnh báo nhầm, bỏ sót, thời gian cảnh báo sớm và kết quả theo giai đoạn/JIG.

**Hoàn thành kỹ thuật khi**: công cụ phát lại chạy lại cho cùng kết quả trên fixture, chặn rò rỉ tương lai và xuất đủ số đúng/nhầm/bỏ sót/thời gian sớm.

**Được phép vận hành khi**: báo cáo trên snapshot thật tự nhận `AUTO_SHADOW` hoặc `LEARNING_SHADOW` theo rubric. Dữ liệu chưa đủ cho model không chặn EWMA hoặc chạy bóng học hỏi; chỉ lỗi schema, rò rỉ tương lai hoặc không tái lập mới chặn lô thật.

### Mốc 4 — Shadow thủ công

**Làm**: người dùng chọn một lô file mới không chứa outcome tương lai tại thời điểm dự báo, chạy phân tích, xem danh sách Unit có nguy cơ cùng lý do/bằng chứng trong Workspace Chat, rồi ghi kết quả kiểm tra thực tế ở bước riêng sau đó. Người dùng cũng có thể ghi một Unit NG bị bỏ sót dù trước đó Unit không có cảnh báo.

**Hoàn thành kỹ thuật khi**: fixture chạy hết nhập file → danh sách nguy cơ → tạo/cập nhật case không trùng → ghi phản hồi, kể cả lỗi giữa hai kho và chạy lại.

**Được phép vận hành khi**: chạy được ít nhất một lô thật vượt rubric từ nhập file → danh sách nguy cơ → phản hồi đúng/nhầm/bỏ sót; không phát lệnh máy hoặc cảnh báo ra ngoài ứng dụng.

### Mốc 5 — Học tiếp và mở rộng có điều kiện

**Làm**: rubric tự đề xuất và kiểm chứng threshold hoặc model bằng version mới; giữ bản cũ để rollback. Người dùng có thể bác bỏ hoặc ghi đè bằng cấu hình cục bộ có lý do.

Sau đó mới quyết định riêng từng nhánh:

| Nhánh | Điều kiện mở |
| --- | --- |
| BOWSKEW 2 BEAM, BEAM 4 BEAM | BOWSKEW 4 BEAM có chuỗi dữ liệu và shadow dùng được |
| Cảnh báo trong Workspace Chat | Shadow đạt ngưỡng, có người nhận, kill switch và quy trình phản hồi |
| C-call/Jam | Có bộ log/SOP/mapping và người phụ trách sẵn sàng đóng một case thật |
| Bài học đã duyệt | Có case thật với phản hồi chuyên gia đủ provenance |
| NAS nhiều người | Có môi trường thử backup/restore và một máy ghi–nhiều máy đọc |
| Drum/DLP | LSU chứng minh hợp đồng dữ liệu và đánh giá có giá trị; mỗi miền có Data Gate riêng |
| Agent artifact/lập trình | Có nhu cầu thật, workspace/output root và người duyệt rõ ràng |

Mốc 5 không phải một cổng lớn bắt mọi nhánh chờ nhau. Nó là điểm chọn task pack kế tiếp theo năm đường độc lập:

1. Case có review thật → US3 trích xuất và tra cứu bài học kinh nghiệm (Lesson Learned).
2. Log sự kiện dây chuyền và bằng chứng sẵn sàng → US4 trợ lý điều tra line chủ động (Line Investigation & Root Cause Triage).
3. Hồ sơ vụ việc có đủ bằng chứng đã xác nhận → US5 Agent tạo đầu ra công việc có kiểm soát (Controlled Artifacts & SOP Review).
4. Task pack và sandbox sẵn sàng → US6 Agent hỗ trợ lập trình trong workspace tách biệt (Sandbox Scripting & Tool Prototyping).
5. Shadow LSU đạt rubric → US10 cảnh báo trong ứng dụng có duyệt và đề xuất phòng ngừa (In-App Risk Notification).
6. Thư mục chia sẻ và quy trình sao lưu sẵn sàng → US11 thư viện công ty dùng chung và đa tiến trình/NAS an toàn (Multi-User Shared Library).

Nếu một đường chưa đủ đầu vào, chỉ đường đó giữ `PARTIAL`/`BLOCKED`. T028 phải chuẩn bị task pack nhỏ cho đường đã đủ điều kiện; không mở đồng thời tất cả và không bắt đường độc lập chờ nhau.

## 7. Định nghĩa MVP LSU hoàn thành

MVP chỉ được gọi là hoàn thành khi đồng thời có:

- Một target BOWSKEW 4 BEAM được cấu hình, không hard-code vào lõi.
- Một snapshot thật được phép, có báo cáo chất lượng và truy vết lot → Unit → JIG → outcome.
- Một lượt phát lại lịch sử với baseline và số đúng/nhầm/bỏ sót/thời gian cảnh báo sớm.
- Một lượt shadow thủ công được người dùng đối chiếu với outcome thật.
- Giao diện tiếng Việt, không lộ tên engine/model nội bộ hoặc traceback.
- Không có bộ chọn ngôn ngữ khác; mọi trạng thái và nhật ký vận hành người dùng thấy đều là tiếng Việt dễ hiểu, kể cả khi thư viện bên ngoài trả lỗi tiếng Anh.
- Không có hành động điều khiển máy; dữ liệu `local_only` không rời máy và không vào Git.
- Các lệnh kiểm tra bắt buộc của repo được ghi đúng trạng thái; thiếu bằng chứng là `PARTIAL` hoặc `BLOCKED`.

MVP không bắt buộc phải có model học máy. Nếu baseline không tạo giá trị hoặc dữ liệu chưa đủ, báo cáo trung thực đó vẫn đóng được mốc nghiên cứu nhưng không mở cảnh báo vận hành.

## 8. Ánh xạ US để không mất đích

| US | Vị trí trong kế hoạch |
| --- | --- |
| US1 | Mốc 0 và tiếp tục làm bìa hồ sơ cho mọi mốc |
| US2 | Mốc 1, xác nhận tối thiểu ngay trong case |
| US3 | Mốc 5 khi đã có phản hồi thật để tạo bài học kinh nghiệm (Lesson Learned) |
| US4 | Nhánh trợ lý điều tra line chủ động (Line Investigation & Root Cause Triage) |
| US5 | Nhánh Agent tạo đầu ra công việc có kiểm soát (Controlled Artifacts & SOP Review) |
| US6 | Nhánh Agent hỗ trợ lập trình trong workspace tách biệt (Sandbox Scripting & Tool Prototyping) |
| US7 | Mốc 2, chuỗi dữ liệu Iris LSU |
| US8 | Mốc 3, phát lại lịch sử và đánh giá |
| US9 | Mốc 4, shadow thủ công |
| US10 | Sau shadow đạt ngưỡng, cảnh báo trong ứng dụng có duyệt và đề xuất phòng ngừa (In-App Risk Notification) |
| US11 | Mốc 5, thư viện công ty dùng chung và đa tiến trình/NAS an toàn (Multi-User Shared Library) |

## 9. Cách kiểm thử và dừng an toàn

- Mỗi task chạy test tập trung và `git diff --check`.
- Mọi lệnh Python chạy bằng Python 3.11 trong môi trường `uv` đã khóa. Nếu `.venv` hiện có lỗi, tạo môi trường mới dưới `local_runs/`; không xóa hoặc sửa quyền môi trường cũ.
- Smoke tự động dùng thư mục làm việc dưới `local_runs/` để toàn bộ `Path.cwd()/local_cases` trỏ vào dữ liệu thử nghiệm. Không mở dữ liệu thật bằng Gemini hoặc tác tử cloud.
- Chỉ tác tử điều phối ghi checklist, trạng thái chung, `PROJECT_HANDOVER.md` và chạy Git. Tác tử thực thi ghi biên nhận riêng; hai tác tử không sửa cùng file đồng thời.
- Gemini thực hiện T001–T029 trong một `/goal`; T029 do tác tử kiểm toán độc lập với tác tử thực thi. Lỗi được trả lại để tự sửa tối đa hai vòng rồi kiểm toán lại.
- Mỗi mốc có kiểm tra restart/readback, quyền riêng tư, quyền hạn và thông báo tiếng Việt liên quan.
- Mỗi luồng giao diện phải kiểm đủ trạng thái bình thường, trống, chờ, thành công, cảnh báo và lỗi; cố ý tạo lỗi tiếng Anh từ bên ngoài để chứng minh lớp hiển thị đã đổi thành tiếng Việt và hướng dẫn cách xử lý.
- Trước hợp nhất, phát hành hoặc đánh dấu hoàn tất mốc: chạy compile, toàn bộ pytest, CLI audit, import Workspace Chat và kiểm tra tài liệu.
- Không dùng fixture để tuyên bố pilot thật. Không đủ dữ liệu thì xuất báo cáo thiếu gì và dừng ở cổng tương ứng.
- Không xóa schema/dữ liệu cũ để làm đẹp. Mọi thay đổi bền vững phải migration, backup và đọc lại được.
- Lỗi công cụ/môi trường được chẩn đoán và thử lại tối đa hai lần. Nếu vẫn không thể sửa an toàn, ghi blocker cụ thể rồi tiếp tục task độc lập; không mở rộng vô hạn sang hệ thống ngoài phạm vi.

## 10. Kiểm tra Hiến chương

- Bằng chứng đi trước tuyên bố: đạt ở mức kế hoạch.
- Ưu tiên cục bộ và an toàn dữ liệu: đạt ở mức kế hoạch.
- Workspace Chat là giao diện chính: giữ nguyên.
- Không fake PASS: có đường kết thúc trung thực khi dữ liệu chưa đủ.
- Không over-engineer: một JIG, file thủ công, baseline trước, tối đa một model CPU, không scheduler/PLC/AutoML trong MVP.
- Không có ngoại lệ Hiến chương được đề xuất.
