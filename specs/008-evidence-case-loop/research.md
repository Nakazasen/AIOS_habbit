# Nghiên cứu và quyết định cho chương trình vòng vụ việc có bằng chứng

## 1. Nguồn và phương pháp kiểm chứng

Quyết định trong tài liệu này dựa trên ba lớp bằng chứng:

1. Checkout hiện tại tại commit `2bb7a5f` trên nhánh `gate1-local-case-sqlite`.
2. Truy vấn Graphify với các node `Workspace`, `Case`, `evidence`, `learning_models.py`, `line_log_parser.py`, `call_cagent_prediction()` và các module Agent.
3. Kiểm tra source/test trực tiếp; riêng Cổng 1 đã chạy 80 bài test tập trung và đều đạt.

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

## 9. Quyết định 8: Dự đoán dùng lát cắt LSU/Iris trước, lõi adapter dùng lại

**Quyết định**: xây hợp đồng domain-neutral cho asset, measurement, outcome, dataset, feature, model, prediction; triển khai adapter LSU/Iris và đóng pilot trước khi thêm Drum/DLP.

**Lý do**: làm ba miền đồng thời sẽ che lỗi join/nhãn và không tạo được bằng chứng end-to-end. Adapter chung tránh hard-code LSU trong lõi nhưng không giả định dữ liệu ba miền giống nhau.

**Phương án đã xét**:

- Một model chung cho LSU/Drum/DLP ngay từ đầu: không có cơ sở dữ liệu.
- Ba pipeline hoàn toàn riêng: nhanh lúc đầu nhưng nhân ba audit/migration.
- Lõi quản trị chung + adapter miền + LSU/Iris làm vertical slice: đây là phương án chọn.

## 10. Quyết định 9: Baseline thống kê trước, model có giám sát sau

**Quyết định**: so sánh ít nhất ba nhóm theo cùng giao thức đóng băng:

1. Baseline hiện tại/không cảnh báo.
2. Rule/SPC đã được kỹ sư review, ưu tiên EWMA/CUSUM cho drift nhỏ khi giả định dữ liệu phù hợp.
3. Model có giám sát đơn giản, giải thích được; chỉ thêm dependency `scikit-learn` trong extra riêng sau khi data gate đạt.

**Lý do**: NIST mô tả EWMA/CUSUM là kỹ thuật theo dõi drift từ dữ liệu lịch sử đại diện; scikit-learn cảnh báo dữ liệu time-ordered phải chia theo thời gian để tránh train bằng tương lai. Probability cần được kiểm calibration trên tập tách biệt, không chỉ đo accuracy.

**Nguồn chính thức**:

- [NIST về kỹ thuật kiểm soát quá trình](https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc12.htm)
- [NIST về EWMA](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm)
- [scikit-learn về `TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
- [scikit-learn về calibration xác suất](https://scikit-learn.org/stable/modules/calibration.html)
- [scikit-learn về permutation importance](https://scikit-learn.org/stable/modules/permutation_importance)

Không khóa model thắng trước khi có dataset profile. Model được chọn bằng chi phí vận hành của false alarm/missed detection, lead time, calibration và độ ổn định theo thời gian/máy.

## 11. Quyết định 10: Shadow tự mở case, không tự cảnh báo nhà máy

**Quyết định**: một `RiskAssessment` vượt threshold đã duyệt chỉ tạo/cập nhật case `prediction` trong queue cục bộ, có dedup/cooldown. Nó không gọi PLC, không gửi production alert và không tự tạo nguyên nhân.

**Lý do**: case prediction cần outcome thật để biết cảnh báo đúng/sai và tạo dữ liệu học tiếp theo. Tạo case là hành động tổ chức công việc có thể rollback; điều khiển line thì không.

## 12. Quyết định 11: Các cổng theo phụ thuộc, không dùng một blocker để dừng toàn chương trình

**Quyết định**: hoàn tất tuần tự trong từng track; các track độc lập có thể chuẩn bị tài liệu/test song song nhưng không đóng gate sau nếu gate phụ thuộc chưa đạt.

- Case UI → chuyên gia → learning → line pilot.
- Capability registry → artifact Agent → coding Agent.
- Data contract → LSU dataset → model evaluation → shadow → alert có duyệt → Drum/DLP.
- Gate A NAS chạy độc lập và chỉ ảnh hưởng tuyên bố vận hành thư viện chung.

Thiếu dữ liệu thật có thể chặn prediction/pilot nhưng không chặn việc hoàn thiện case UI, migration hoặc policy Agent.

## 13. Quyết định 12: Giao theo đợt vận hành nhỏ, không kích hoạt toàn bộ backlog

**Quyết định**: giữ US1–US11 làm tầm nhìn đầy đủ, nhưng `tasks.md` chỉ chứa Đợt 0 và Đợt 1 đang đủ điều kiện. Giá trị đầu tiên sau phần nền là một pilot C-call hoặc Jam thật. Learning, prediction, NAS nhiều người, Drum/DLP và Agent lập trình chỉ được tạo task khi đạt điều kiện vào trong `plan.md`.

**Lý do**: danh sách 100 task khiến phần chưa có dữ liệu trông giống công việc đã sẵn sàng, đồng thời đặt hạ tầng chuyên gia/Agent/ML trước bằng chứng vận hành. Chia theo đợt nhỏ giúp hoàn tất và đưa vào dùng sớm mà không xóa mục tiêu dài hạn.

**Giới hạn ban đầu**:

- Người điều tra mặc định có thể đồng thời là chuyên gia đúng công đoạn; người thứ hai là tùy chọn.
- Pilot chỉ tạo báo cáo điều tra và SOP; chưa cần capability registry tổng quát.
- Learning dùng tìm kiếm SQLite đơn giản trước.
- LSU dùng baseline thống kê và tối đa một model bảng nhẹ trên CPU; phát lại lịch sử hoặc shadow thủ công trước scheduler.
