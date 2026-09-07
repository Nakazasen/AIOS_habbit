# Nghiên cứu và quyết định cho chương trình vòng vụ việc có bằng chứng

## 1. Nguồn và phương pháp kiểm chứng

Quyết định trong tài liệu này dựa trên ba lớp bằng chứng:

1. Checkout hiện tại trên nhánh `gate1-local-case-sqlite` và các đặc tả 005/007/008.
2. Truy vấn Graphify với các node `Workspace`, `Case`, `evidence`, `learning_models.py`, `line_log_parser.py`, `call_cagent_prediction()` và các module Agent.
3. Kiểm tra source/test trực tiếp; số test chỉ được ghi vào handover sau lần chạy hiện tại.
4. Bảy trang trong `AI cảnh báo lỗi LSU.pptx`: ưu tiên BOWSKEW 4 BEAM, nối thông số linh kiện theo lot với Unit/JIG, phát lại lịch sử, shadow và đo cảnh báo đúng/nhầm/bỏ sót.

Graphify đang dùng package `0.9.32` trong khi skill là `0.9.50`, nên graph chỉ dùng để định vị; kết luận trạng thái phải được xác nhận bằng source/test hiện tại.

## 2. Quyết định 1: Dùng Workspace Chat làm một cửa vào duy nhất

**Quyết định**: thêm mục “Hồ sơ vụ việc” ngay trong Workspace Chat, không khôi phục Case Cockpit hay Studio.

**Lý do**: ADR-0002 khóa Workspace Chat là giao diện được hỗ trợ. Người khác phải mở danh sách case, không hỏi lại RAG để dò case cũ.

**Phương án đã xét**:

- Khôi phục Case Cockpit: có màn hình cũ nhưng phá ranh giới legacy và tạo hai tuyến sản phẩm.
- Chỉ cho tìm case bằng chat: ít UI hơn nhưng không quản lý được trạng thái, assignment, review và timeline.
- Mục “Hồ sơ vụ việc” trong Workspace Chat: giữ một tuyến, hiển thị vòng công việc rõ; đây là phương án chọn.

## 3. Quyết định 2: Giữ kho hồ sơ riêng và bổ sung migration có version

**Quyết định**: tiếp tục dùng `local_cases/workspace_cases.sqlite`, tách khỏi `library.sqlite` và `line_events.sqlite`; trước khi thêm bảng/trường phải có `schema_migrations`, online backup, kiểm tra toàn vẹn và rollback.

**Lý do**: Cổng 1 đã có transaction tốt nhưng schema hiện được tạo bằng `CREATE TABLE IF NOT EXISTS`, chưa đủ cho tương thích dài hạn. `docs/contracts/PERSISTED_DATA_COMPATIBILITY.md` yêu cầu version migration trước khi tuyên bố tương thích tại chỗ.

**Phương án đã xét**:

- Tiếp tục thêm cột khi khởi động: nhanh nhưng khó rollback và dễ lệch schema.
- Chuyển toàn bộ sang JSONL: không phù hợp quan hệ case/review/lesson/prediction và transaction nhiều bảng.
- Migration SQLite tuần tự, backup trước đổi schema: thêm công việc nhưng kiểm toán và phục hồi rõ; đây là phương án chọn.

## 4. Quyết định 3: Case là bộ điều phối công việc, không phải kho chat

**Quyết định**: case lưu metadata, state, assignment, digest và con trỏ; câu hỏi/câu trả lời/đoạn trích gốc vẫn nằm ở store tương ứng và được phân giải qua `trace_id`.

**Lý do**: chính sách dữ liệu ưu tiên mã băm/tham chiếu thay vì lưu toàn văn. Nếu trace mất, UI phải nói thiếu bằng chứng thay vì copy hoặc tái tạo bằng AI.

**Phương án đã xét**:

- Copy toàn bộ chat vào case: dễ xem nhưng nhân đôi dữ liệu nhạy cảm và lệch chính sách.
- Chỉ lưu case ID: quá ít để vận hành.
- Lưu metadata + con trỏ + digest + timeline: cân bằng khả năng dùng và quyền riêng tư; đây là phương án chọn.

## 5. Quyết định 4: Phản hồi chuyên gia là record quyền hạn append-only

**Quyết định**: tạo `ExpertRequest` và `ExpertReview` gắn role/scope cấu hình cục bộ. AI chỉ tạo draft/request; service mới có quyền transition sau khi kiểm role, scope, reason và evidence digest.

**Lý do**: `learning_models.py` và `agent_learning.py` có mầm candidate/review nhưng chưa nối vào case/UI. Boolean `approved` từ caller không đủ làm thẩm quyền.

**Phương án đã xét**:

- Tin trạng thái UI: đơn giản nhưng dễ giả quyền.
- Dùng prompt yêu cầu AI tự xác nhận vai trò: không phải bảo mật.
- Role/scope registry cục bộ + service guard + audit append-only: đây là phương án chọn.

## 6. Quyết định 5: Vòng học là case-memory retrieval riêng, không phải tự huấn luyện

**Quyết định**: bài học `promoted` được lập chỉ mục trong kho case-memory riêng và truy xuất có citation đến case/review/evidence. Không ghi vào `library.sqlite`, không tự fine-tune, không dùng candidate như sự thật.

**Lý do**: nếu chỉ lưu thẻ mà Workspace Chat không tìm lại được thì chưa có vòng học. Nếu trộn bài học với SOP chuẩn thì người dùng dễ nhầm kinh nghiệm case với tài liệu quy chuẩn.

**Phương án đã xét**:

- Ghi thẳng vào thư viện RAG: dễ reuse nhưng làm lẫn thẩm quyền.
- Chỉ có màn hình danh sách bài học: an toàn nhưng không hỗ trợ case mới.
- Retriever riêng, nhãn “Bài học đã xác nhận”, provenance đầy đủ: đây là phương án chọn.

## 7. Quyết định 6: Điều tra line là trợ lý chủ động, không phải bộ chẩn đoán

**Quyết định**: xây timeline, nhóm lặp, gap checklist và câu hỏi chuyên gia từ log/tài liệu; mọi event giữ `suspected` cho đến khi con người review relevance. Mapping sơ đồ là adapter có version và phê duyệt riêng.

**Lý do**: `line_log_parser.py` đã có parser/kho log nhưng fallback event gần nhất có thể tạo liên quan giả. Pilot phải chứng minh từ case thật đến báo cáo đã duyệt.

**Phương án đã xét**:

- Cho LLM kết luận nguyên nhân: không có bằng chứng và nguy hiểm.
- Chỉ hiển thị log thô: không tạo giá trị hơn công cụ xem log.
- Gom manh mối, hỏi phần thiếu, hỗ trợ review và báo cáo: tạo giá trị công việc mà vẫn giữ con người làm thẩm quyền; đây là phương án chọn.

## 8. Quyết định 7: Tách Agent thành hai miền quyền

**Quyết định**:

1. **Agent artifact theo case**: tạo báo cáo, SOP, hồ sơ thiết kế công đoạn, bảng tính và sơ đồ mới trong output root có version; không sửa nguồn nhà máy.
2. **Agent kỹ thuật phần mềm**: dùng task pack, workspace code riêng, proposal diff/command và observed test; có thể áp dụng patch sau phê duyệt nhưng không được truy cập dữ liệu nhà máy mặc định.

**Lý do**: repo đã có `agent_draft_sop.py`, `agent_task_pack.py`, `agent_result_import.py` và nền Workspace Agent proposal/approval. Gộp hai miền sẽ biến quyền sửa code thành đường tắt chạm dữ liệu/line.

**Phương án đã xét**:

- Chỉ cho Agent viết Markdown: an toàn nhưng không đạt ý đồ trợ lý công việc.
- Một Agent có toàn quyền: mạnh nhưng không kiểm toán và không phù hợp nhà máy.
- Capability registry theo loại artifact/risk tier/verifier/approver, hai workspace tách biệt: đây là phương án chọn.

## 9. Quyết định 8: BOWSKEW 4 BEAM là lát cắt đầu tiên

**Quyết định**: bám đúng chuỗi nghiệp vụ trong PowerPoint: thông số linh kiện theo lot → Unit đã lắp lot → phép đo JIG → outcome. Target đầu tiên là BOWSKEW 4 BEAM; target nằm trong cấu hình, không hard-code vào lõi. BOWSKEW 2 BEAM, BEAM 4 BEAM, Drum và DLP chỉ mở sau.

**Lý do**: đây là loại lỗi được PowerPoint xác định có tỷ lệ NG cao và là ưu tiên số một. Một chuỗi dữ liệu thật khép kín tạo giá trị sớm hơn một hợp đồng “dùng chung mọi miền” nhưng chưa chạy được.

**Phương án đã xét**:

- Một model chung cho LSU/Drum/DLP ngay từ đầu: không có cơ sở dữ liệu.
- Ba pipeline hoàn toàn riêng: nhanh lúc đầu nhưng nhân ba kiểm toán/migration.
- Một bộ kiểu dữ liệu tối thiểu, target cấu hình được và Iris LSU làm lát cắt đầu: đây là phương án chọn.

## 10. Quyết định 9: Baseline thống kê trước, model có giám sát sau

**Quyết định**: so sánh ít nhất ba nhóm theo cùng giao thức đóng băng:

1. Baseline hiện tại/không cảnh báo.
2. EWMA dùng tham số mặc định có version; nếu dữ liệu không có chuỗi thời gian dùng được thì ghi không áp dụng, không tự chuyển sang nhiều luật khác.
3. Hồi quy logistic có giám sát, giải thích được; chỉ thêm dependency `scikit-learn` trong extra riêng sau khi cổng dữ liệu và ngưỡng mẫu đạt.

**Lý do**: NIST mô tả EWMA/CUSUM là kỹ thuật theo dõi drift từ dữ liệu lịch sử đại diện; scikit-learn cảnh báo dữ liệu time-ordered phải chia theo thời gian để tránh train bằng tương lai. Probability cần được kiểm calibration trên tập tách biệt, không chỉ đo accuracy.

**Nguồn chính thức**:

- [NIST về kỹ thuật kiểm soát quá trình](https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc12.htm)
- [NIST về EWMA](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm)
- [scikit-learn về `TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
- [scikit-learn về calibration xác suất](https://scikit-learn.org/stable/modules/calibration.html)
- [scikit-learn về permutation importance](https://scikit-learn.org/stable/modules/permutation_importance)

Không giả định hồi quy logistic sẽ thắng. Phương pháp được tự chọn cho `AUTO_SHADOW` khi cảnh báo nhầm/bỏ sót, thời gian cảnh báo sớm và độ ổn định đạt rubric có version; nếu chưa đủ bằng chứng nhưng kỹ thuật an toàn thì dùng `LEARNING_SHADOW` đọc-only.

## 11. Quyết định 10: Shadow do người dùng chủ động chạy

**Quyết định**: người dùng chọn lô file mới và bấm chạy. Một `RiskAssessment` vượt threshold đã khóa bởi rubric chỉ tạo/cập nhật case `prediction` cục bộ bằng idempotency key. Nó không gọi PLC, không gửi cảnh báo ngoài ứng dụng và không tự tạo nguyên nhân.

**Lý do**: case prediction cần outcome thật để biết cảnh báo đúng/sai. Chạy thủ công đủ để chứng minh vòng giá trị, tránh phải xây scheduler, worker và outbox trước khi người dùng biết tín hiệu có hữu ích không.

## 12. Quyết định 11: Các cổng theo phụ thuộc, không dùng một blocker để dừng toàn chương trình

**Quyết định**: hoàn tất tuần tự trong từng nhánh; các nhánh độc lập có thể chuẩn bị tài liệu/test song song. Mỗi mốc tách cổng kỹ thuật dùng fixture đã làm sạch và cổng vận hành dùng bằng chứng thật; cổng vận hành bị chặn không được chặn xây mốc kỹ thuật hoặc nhánh độc lập khác.

- Case UI → xác nhận chuyên gia tối thiểu; learning mở khi đã có phản hồi thật.
- Capability registry → artifact Agent → coding Agent.
- Chuỗi lot–Unit–JIG → phát lại lịch sử → shadow thủ công → cảnh báo có duyệt → target/miền mới.
- Pilot C-call/Jam mở riêng khi bộ dữ liệu và người phụ trách sẵn sàng.
- Gate A NAS chạy độc lập và chỉ ảnh hưởng tuyên bố vận hành thư viện chung.

Thiếu dữ liệu thật có thể chặn prediction/pilot nhưng không chặn việc hoàn thiện case UI, migration hoặc policy Agent.

## 13. Quyết định 12: Giao theo đợt vận hành nhỏ, không kích hoạt toàn bộ backlog

**Quyết định**: giữ US1–US11 làm tầm nhìn đầy đủ, nhưng `tasks.md` chỉ chứa đường MVP trực tiếp: khóa nền → xác nhận chuyên gia tối thiểu → chuỗi dữ liệu BOWSKEW 4 BEAM → phát lại lịch sử → shadow thủ công. C-call/Jam, learning, NAS nhiều người, Drum/DLP và Agent chỉ mở khi đạt điều kiện trong `plan.md`.

**Lý do**: danh sách 100 task khiến phần chưa có dữ liệu trông giống công việc đã sẵn sàng, đồng thời đặt hạ tầng chuyên gia/Agent/ML trước bằng chứng vận hành. Chia theo đợt nhỏ giúp hoàn tất và đưa vào dùng sớm mà không xóa mục tiêu dài hạn.

**Giới hạn ban đầu**:

- Người điều tra mặc định có thể đồng thời là chuyên gia đúng công đoạn; người thứ hai là tùy chọn.
- Khi mở pilot C-call/Jam, chỉ tạo báo cáo điều tra và SOP; chưa cần capability registry tổng quát.
- Learning dùng tìm kiếm SQLite đơn giản trước.
- LSU dùng file cục bộ, baseline thống kê và tối đa một model bảng nhẹ trên CPU; phát lại lịch sử rồi shadow thủ công trước scheduler.

## 14. Quyết định 13: Chỉ dùng tiếng Việt trên mọi bề mặt người dùng

**Quyết định**: tiếng Việt là ngôn ngữ giao diện duy nhất. Nút, hướng dẫn, tiến độ, cảnh báo, lỗi, nhật ký vận hành và báo cáo phải dùng câu ngắn, dễ hiểu cho người không học công nghệ thông tin. Lỗi từ thư viện hoặc hệ điều hành phải được chặn và đổi thành lời giải thích tiếng Việt trước khi hiển thị.

**Lý do**: người sử dụng sản phẩm không dùng tiếng Anh. Một câu lỗi hoặc trạng thái tiếng Anh khiến họ không biết hệ thống đang làm gì và phải xử lý thế nào, dù chức năng bên dưới vẫn chạy đúng.

**Ranh giới**: tài liệu nguồn ngoại ngữ, mã máy, mã lỗi và tên tệp có thể giữ nguyên để không làm sai bằng chứng. Chúng phải được phân biệt với câu chữ do chương trình tạo và được giải thích bằng tiếng Việt khi cần.

## 15. Quyết định 14: Gemini không đọc dữ liệu nhà máy thật

**Quyết định**: tác tử phát triển dùng model cloud chỉ đọc code, tài liệu sản phẩm, fixture giả hoàn toàn và manifest đã làm sạch. File LSU/log/tài liệu thật được chương trình cục bộ xử lý; chủ sở hữu chỉ bàn giao schema hoặc số tổng hợp không chứa dữ liệu thô.

**Lý do**: “file có sẵn cục bộ” không đồng nghĩa được phép đưa nội dung file vào ngữ cảnh Gemini. Ranh giới này vẫn cho phép xây và kiểm thử toàn bộ pipeline bằng fixture mà không làm chậm nhánh kỹ thuật.

## 16. Quyết định 15: Khóa nghĩa của một cảnh báo trước khi viết thuật toán

**Quyết định**: protocol bắt buộc chỉ ra metric, chiều rủi ro, tham số EWMA, cửa sổ nền, `as_of_time`, khoảng dự báo, quy tắc ghép outcome, feature allowlist và phép chia thời gian/Unit. Mỗi Unit có tối đa một cảnh báo trong một cửa sổ; đúng/nhầm/bỏ sót và lead time được tính theo cùng protocol đóng băng.

**Lý do**: nếu không khóa các trường này, hai implementation cùng “EWMA” vẫn có thể cho kết luận khác nhau. Dùng một cấu hình nhỏ có digest đơn giản hơn dựng framework đánh giá tổng quát.

## 17. Quyết định 16: Phục hồi hai kho bằng ba trạng thái, không dựng outbox

**Quyết định**: assessment dùng `pending_case_link`, `linked`, `retryable_error`. Khóa idempotency lấy từ dataset, phương pháp, threshold, digest lô, Unit và cửa sổ đánh giá; không dùng thời điểm đồng hồ lúc chạy. Chạy lại tìm case cũ trước rồi tiếp tục bước thiếu.

**Lý do**: SQLite không có transaction chung cho hai file. Ba trạng thái và khóa bất biến đủ cho thao tác thủ công một tiến trình; scheduler/outbox chỉ cần khi có tải nền thật.

## 18. Quyết định 17: Một goal thực thi, vai trò kiểm toán tách biệt

**Quyết định**: Gemini chạy T001–T029 và ghi biên nhận trong một `/goal`; T029 thuộc tác tử kiểm toán độc lập với tác tử thực thi. Chỉ tác tử điều phối ghi trạng thái chung và chạy Git, tối đa hai tác tử thực thi không sửa cùng file. Mọi lệnh dùng Python 3.11 và smoke chạy trong runtime tách khỏi dữ liệu người dùng.

**Lý do**: tự kiểm tra của model viết code không thay được kiểm toán độc lập. Một điều phối, hai người thực thi và biên nhận từng task đủ để phục hồi phiên dài mà không cần hệ điều phối mới trong code sản phẩm.

## 19. Quyết định 18: Rubric tự động thay các nút chờ duyệt đọc-only

**Quyết định**: T011 dùng từ điển dữ liệu và rubric cố định để tự ánh xạ, xác nhận nhãn có nguồn máy và đăng ký snapshot. T022 tự mở `AUTO_SHADOW` hoặc `LEARNING_SHADOW`. T029 do tác tử kiểm toán độc lập tự kết luận và điều phối tối đa hai vòng sửa lỗi.

**Lý do**: chạy bóng chỉ đọc không tác động thiết bị nên việc bắt người dùng tự chọn công thức SPC, cỡ mẫu và ngưỡng trước khi phần mềm chạy sẽ kéo dài thời gian giao hàng mà không tăng an toàn vật lý. Mọi mặc định đều có version, digest, nút tắt và rollback.

**Ranh giới**: AI không được đổi rubric sau khi xem kết quả để lấy `PASS`, không tự sửa dữ liệu nguồn, không cấp quyền người dùng và không phát lệnh tác động máy/line. Gói Kyocera chỉ được đăng ký bằng bí danh cục bộ cho US4 sau này; đợt hiện tại không đọc hoặc triển khai nghiệp vụ đó.
