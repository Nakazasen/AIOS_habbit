# Đặc tả tính năng: Trợ lý công việc khép kín từ vụ việc đến phòng ngừa lỗi

**Mã nhánh tính năng**: `008-evidence-case-loop`  
**Ngày cập nhật**: 05/09/2026

**Trạng thái**: Đã chốt MVP ưu tiên cảnh báo sớm Iris LSU; các đích WorkLens khác vẫn được giữ
**Phạm vi**: Workspace Chat, hồ sơ vụ việc, chuyên gia, bài học, trợ lý tạo đầu ra công việc, điều tra line và thử nghiệm dự đoán có kiểm soát.

## 1. Ý đồ sản phẩm bằng ngôn ngữ đời thường

AIOS không được dừng ở mức “hỏi tài liệu rồi trả lời như chatbot”. Sản phẩm phải là một **trợ lý công việc chủ động nhưng có chốt duyệt**, gần với hình ảnh “Đôrêmon có kiểm soát”:

1. Người dùng đưa vào một vấn đề, log, ảnh, tài liệu và mô tả hiện trường.
2. Hệ thống tự gom thành hồ sơ, dòng thời gian và danh sách bằng chứng.
3. Hệ thống chỉ ra còn thiếu gì, hỏi ngược câu cần thiết và chuyển đúng việc cho người có chuyên môn.
4. Hệ thống tạo đầu ra hữu ích như báo cáo điều tra, SOP, hồ sơ thiết kế công đoạn, bảng kiểm tra hoặc đề xuất thay đổi mã nguồn.
5. Việc đọc-only và có rubric được tự xác nhận để giao sớm; con người chỉ cần can thiệp khi muốn sửa kết quả hoặc áp dụng hành động tác động ngoài đời.
6. Kết quả thực tế đã xác nhận trở thành bài học để lần sau hệ thống hỗ trợ nhanh và đúng hơn.

“Hồ sơ vụ việc” không phải ticket hành chính bắt mọi việc phải xin chữ ký. Nó là bìa hồ sơ chung cho một việc quan trọng, lặp lại, chưa rõ nguyên nhân hoặc cần bàn giao. Việc đơn giản vẫn có thể xử lý trực tiếp trong Workspace Chat mà không tạo hồ sơ.

### 1.1. Nguyên tắc giao sớm nhưng không cắt mất tầm nhìn

- US1–US11 bên dưới là lời hứa sản phẩm dài hạn và không bị xóa chỉ để làm kế hoạch ngắn hơn.
- Mỗi lần chỉ đưa **một đợt vận hành nhỏ** vào `tasks.md`; năng lực tương lai chỉ được kích hoạt khi đạt điều kiện đầu vào của đợt đó.
- Mỗi mốc tách hai kết quả: **hoàn thành kỹ thuật** bằng dữ liệu mẫu đã làm sạch và **được phép vận hành thật** bằng bằng chứng nhà máy. Thiếu dữ liệu thật không được dùng để tuyên bố pilot, nhưng cũng không được ngăn xây và kiểm thử mốc kỹ thuật kế tiếp.
- Giá trị vận hành đầu tiên sau phần nền là một lát cắt Iris LSU thật: nối lot linh kiện → Unit → JIG → kết quả, phát lại lịch sử và tạo cảnh báo shadow để con người đối chiếu.
- Không dựng model, kho dữ liệu, hàng chờ hay lớp trừu tượng chỉ để trình diễn khi chưa có dữ liệu thật hoặc nhu cầu sử dụng thật.
- Kiểm thử tập trung chạy trong từng task; bộ kiểm thử toàn bộ chạy trước khi hợp nhất, phát hành hoặc tuyên bố đóng một đợt.

### 1.2. Ranh giới của đợt 29 nhiệm vụ

- Giai đoạn ban đầu T001–T029 chỉ triển khai lát cắt của US1, US2, US7, US8 và US9. Đợt hội tụ bổ sung toàn diện T030–T057 đã chính thức kích hoạt tiếp US3, US4, US5, US6, US10 và US11 theo kế hoạch tại tasks.md:325.
- Gemini chỉ dùng mã nguồn, tài liệu sản phẩm và fixture giả hoàn toàn. Gemini không được mở, đọc, tóm tắt hoặc đưa vào ngữ cảnh model bất kỳ file thật nào trong `Tài liệu của tất cả dòng máy/`, `local_cases/`, `local_runs/` của phiên khác hoặc vùng dữ liệu nhà máy.
- T029 và T057 thuộc tác tử kiểm toán độc lập với tác tử đã sửa code, nhưng nằm trong cùng một `/goal`. Tác tử kiểm toán được tự kết luận theo rubric và lệnh thực tế.
- Hoàn thành T001–T057 không đồng nghĩa toàn bộ US1–US11 hoặc quyền điều khiển nhà máy đã hoàn thành. Cổng kỹ thuật, chạy bóng đọc-only và hành động vật lý luôn được báo riêng.

### 1.3. Các đợt đưa vào vận hành

| Đợt | Kết quả sử dụng được | Điều kiện để bắt đầu |
| --- | --- | --- |
| 0 — Khóa phần nền | Chuẩn bị nguồn và hồ sơ đã có được kiểm tra trên trình duyệt, đọc lại được sau khởi động | Code hiện tại, không cần dữ liệu nhà máy mới |
| 1 — Trợ lý LSU có căn cứ | Tra tài liệu LSU, ghi câu hỏi còn thiếu và nhận xác nhận chuyên gia ngay trong case | Nền RAG/case đọc lại ổn định |
| 2 — Nối dữ liệu Iris LSU | Truy ngược được lot linh kiện → Unit → JIG → kết quả cho BOWSKEW 4 BEAM | Có data dictionary và file được phép |
| 3 — Phát lại lịch sử | Baseline cảnh báo sớm được so với kết quả OK/NG thật; chỉ thêm một model CPU nếu dữ liệu đủ | Chuỗi dữ liệu đạt Data Gate |
| 4 — Shadow thủ công | Người dùng nhập lô dữ liệu mới, xem nguy cơ trong Workspace Chat và ghi kết quả thực tế | Phát lại lịch sử vượt rubric tự động hoặc vào chế độ học hỏi đọc-only |
| 5 — Học tiếp và mở rộng | Điều chỉnh ngưỡng/model có version; sau đó mới xét C-call/Jam, NAS, Drum/DLP và Agent | Có phản hồi shadow thật |

## 2. Trạng thái thật tại thời điểm lập kế hoạch

| Nhánh năng lực | Trạng thái đã kiểm chứng |
| --- | --- |
| RAG tài liệu nội bộ | Có nền BGE-M3 hybrid, chunking, citation và evidence. Vận hành thư viện chung trên dữ liệu/NAS thật vẫn `PARTIAL`. |
| Gói bằng chứng điều tra | Đã ghép citation tài liệu với lát log `suspected` từ `line_events.sqlite`. |
| Chuẩn bị nguồn và RAG | Đã có code/test cho tiến độ chuẩn bị nguồn, truy xuất và citation; còn cần smoke trên trình duyệt với nguồn thật. Gate A NAS vẫn `PARTIAL`. |
| Lưu và mở lại hồ sơ từ Workspace Chat | Đã có migration, kho cục bộ, danh sách/chi tiết, trạng thái, kết luận và mở lại trace; còn chờ kiểm chứng trình duyệt và bộ kiểm thử hiện tại trước khi đóng đợt nền. |
| Điều tra lỗi line | Có parser Jam/C-call/LSU và kho log riêng; chưa có pilot thực tế khép kín với SOP, mã lỗi, báo cáo, mapping và chuyên gia xác nhận. |
| Chuyên gia và vòng học | Có model/thẻ học cũ rời rạc; chưa có luồng giao việc–phản hồi–xác nhận–promotion trong Workspace Chat. |
| Agent | Có soạn nháp SOP/báo cáo có duyệt và có nền Agent IDE/task pack; chưa có một luồng sản phẩm thống nhất theo case cho báo cáo, thiết kế công đoạn và lập trình. |
| Dự đoán LSU/Drum/DLP | Chưa có tập lịch sử/nhãn quản trị, model, đánh giá, shadow mode hoặc cảnh báo vận hành. Tên client `prediction` không phải bằng chứng về năng lực dự đoán. |

## 3. Các loại hồ sơ phải hỗ trợ

### 3.1. Hồ sơ điều tra

Lỗi đã xảy ra hoặc hiện tượng đã xuất hiện. Hệ thống gom bằng chứng, tạo dòng thời gian, hỏi phần còn thiếu, hỗ trợ chuyên gia xác nhận và tạo báo cáo.

### 3.2. Hồ sơ dự đoán

Lỗi chưa xảy ra. Một rule hoặc model đã được duyệt ở chế độ thử nghiệm bóng phát hiện rủi ro và tạo phiếu cần kiểm tra. Phiếu phải nêu rõ khoảng thời gian dự báo, mức rủi ro, dữ liệu hỗ trợ, độ không chắc chắn và bước kiểm tra đề nghị. Nó không được nói “chắc chắn hỏng” và không được tự dừng máy.

### 3.3. Hồ sơ công việc Agent

Người dùng giao một đầu ra cụ thể: báo cáo, SOP, hồ sơ thiết kế công đoạn, bảng tính, sơ đồ hoặc thay đổi mã nguồn. Agent tạo bản nháp/đề xuất, chạy kiểm tra trong phạm vi cho phép và chờ người có thẩm quyền duyệt. Hồ sơ này tách rõ với hồ sơ điều tra và hồ sơ dự đoán nhưng có thể liên kết qua cùng bằng chứng.

## 4. Câu chuyện người dùng và tiêu chí nghiệm thu

### US1 — Xem và quản lý hồ sơ trong Workspace Chat (P1)

Người dùng mở mục **Hồ sơ vụ việc**, lọc danh sách, bấm một hồ sơ để xem trạng thái, người phụ trách, dòng thời gian, bằng chứng, việc còn thiếu và mở lại trace/câu trả lời gốc.

- Không cần hỏi lại RAG để tìm một hồ sơ đã lưu.
- Hồ sơ vẫn đọc được sau khi khởi động lại ứng dụng.
- Không sao chép câu hỏi, câu trả lời hoặc đoạn trích nguồn thô vào kho hồ sơ; UI phân giải chúng qua `trace_id` khi còn tồn tại.
- Nếu trace gốc không còn, UI hiển thị bằng chứng bị thiếu thay vì bịa nội dung.
- Người có quyền có thể gắn thêm tham chiếu ảnh, SOP, tài liệu hoặc log vào hồ sơ hiện hữu; kho hồ sơ chỉ giữ locator đã làm sạch, digest và provenance, không sao chép nội dung thô.

### US2 — Giao và nhận thẩm định chuyên gia (P1)

Người điều tra tạo câu hỏi cụ thể cho chuyên gia, chỉ định phạm vi, người nhận và hạn mong muốn. Chuyên gia mở hàng chờ của mình, xem bằng chứng rồi chọn `confirmed`, `rejected` hoặc `needs_more_evidence` kèm lý do.

- Mặc định người được giao điều tra đồng thời là người xác nhận đúng công đoạn. Chỉ tạo giao việc cho chuyên gia thứ hai khi có người theo dõi công đoạn riêng hoặc cần phân xử.
- Pilot đầu tiên được dùng màn hình xác nhận ngay trong chi tiết case; hàng chờ nhiều người chỉ mở khi xuất hiện nhu cầu giao nhận thật.
- Không có người nhận hợp lệ, phạm vi quyền hoặc lý do thì không thể xác nhận.
- Mọi phản hồi là append-only; sửa ý kiến phải tạo bản mới.
- Hai ý kiến trái chiều được giữ nguyên và chuyển sang trạng thái cần phân xử.

### US3 — Học từ phản hồi đã xác nhận và dùng lại có truy vết (P1)

Quản lý chọn một thẩm định `confirmed`, tạo bài học ứng viên, sửa nội dung và promotion thành bài học chính thức. Lần sau Workspace Chat có thể tìm bài học liên quan trong kho case-memory riêng và luôn dẫn về case/review/evidence gốc.

- Chỉ mở đợt này sau khi có ít nhất một case thật đã được xác nhận và kết luận.
- Bản đầu dùng tìm kiếm chính xác/từ khóa trên SQLite; chưa cần embedding, vector database hoặc tự huấn luyện.
- Không tự huấn luyện lại model và không ghi bài học vào `library.sqlite`.
- Bài học chưa promotion không được dùng như sự thật.
- Bài học bị thu hồi không xuất hiện trong kết quả dùng lại thông thường.

### US4 — Trợ lý điều tra line chủ động (P2)

Trong một hồ sơ điều tra, hệ thống gom log, SOP, ảnh/biên bản được phép, dựng dòng thời gian, nhóm hiện tượng lặp lại và sinh danh sách câu hỏi còn thiếu. Chuyên gia xác nhận tính liên quan của từng manh mối trước khi kết luận.

- Log luôn bắt đầu là `suspected`; không match thì không tự lấy năm event mới nhất làm bằng chứng.
- CSV thô không đi vào RAG.
- Mapping sơ đồ chỉ hiển thị khi nguồn mapping có phiên bản và đã được chuyên gia duyệt.
- Pilot chỉ đạt khi có ít nhất một case thật đi từ mở hồ sơ đến báo cáo được duyệt và kết luận outcome.

### US5 — Agent tạo đầu ra công việc có kiểm soát (P2)

Từ một case có đủ bằng chứng, người dùng yêu cầu Agent tạo báo cáo, SOP, hồ sơ thiết kế công đoạn, bảng tính hoặc sơ đồ mới. Agent phải cho xem nguồn đã dùng, bản khác biệt giữa các phiên bản và người phê duyệt.

- Pilot đầu chỉ hỗ trợ hai đầu ra cụ thể là báo cáo điều tra và SOP. Chỉ tổng quát hóa thành danh mục năng lực khi có ít nhất ba loại đầu ra thật cần dùng lại.
- Chỉ tạo artifact mới trong vùng output được phép; không xóa hoặc ghi đè nguồn nhà máy.
- Mỗi loại artifact có template, bộ kiểm tra và vai trò duyệt riêng.
- “Kiến thức được đào tạo” trong phạm vi này nghĩa là tài liệu và bài học đã xác nhận được truy xuất có citation, không phải tự fine-tune từ chat thô.

### US6 — Agent hỗ trợ lập trình trong workspace tách biệt (P3)

Người dùng giao một task lập trình có phạm vi file và lệnh kiểm thử rõ. Agent đọc code, đề xuất diff, chạy lệnh trong sandbox/workspace được tin cậy và chờ phê duyệt trước khi áp dụng thay đổi.

- Không dùng workspace lập trình để truy cập `local_cases/`, dữ liệu nhà máy hoặc điều khiển line.
- Mọi patch/command có proposal bất biến, diff hiển thị, allowlist và audit event.
- PASS chỉ được ghi khi có observed evidence từ test thật; AI không tự merge/push nếu chưa có quyền riêng.

### US7 — Nối dữ liệu lot–Unit–JIG cho Iris LSU (P1)

Kỹ sư nạp thông số linh kiện theo lot, liên kết lot đã dùng cho từng Unit, dữ liệu đo trên JIG và outcome OK/NG đã xác nhận vào kho dự đoán cục bộ có version. Lát cắt đầu tiên là Iris LSU BOWSKEW 4 BEAM; BOWSKEW 2 BEAM và BEAM 4 BEAM là ưu tiên kế tiếp nhưng chưa triển khai đồng thời.

- Kho dự đoán chỉ được tạo sau khi Data Gate LSU/Iris đủ điều kiện; Drum/DLP chưa thuộc lát cắt đang triển khai.
- Từ một `unit_serial` phải truy ngược được `component_lot_id`, thông số linh kiện, `jig_id`, lần đo, thời điểm và outcome cuối cùng.
- MVP chỉ nhận file cục bộ theo mẫu đã duyệt; chưa tích hợp tự động với máy/JIG, ERP hoặc hệ thống nhà máy.
- Khóa join, đơn vị, múi giờ, thời điểm sự kiện và thời điểm dữ liệu đến phải tường minh.
- Nhãn tối thiểu gồm `confirmed`, `false_alarm`, `unknown`; kết quả cuối cùng OK/NG có khóa và digest hợp lệ được xác nhận tự động, còn mâu thuẫn thành `unknown`. Không suy ra nhãn từ tên file.
- Dữ liệu thiếu hoặc có nguy cơ rò rỉ outcome làm gate bị `blocked`.

### US8 — Phát lại lịch sử và đánh giá cảnh báo sớm (P1)

Nhóm kỹ thuật chạy phương án không cảnh báo, EWMA và hồi quy logistic tùy chọn trên snapshot dữ liệu đóng băng, chia theo thời gian/nhóm thiết bị, so sánh với cùng giao thức và ghi phiếu mô tả phương pháp.

- Báo riêng precision, recall, false alarm, missed detection, lead time, calibration và độ ổn định theo máy/ca/thời gian.
- Không chọn model chỉ vì accuracy trung bình cao.
- Model, feature schema, dataset digest, code version và threshold đều có version/rollback.
- Nếu dữ liệu chưa đủ cho hồi quy logistic, hệ thống vẫn phải hoàn thành báo cáo Data Gate cùng phương án không cảnh báo/EWMA; không tạo model giả để trình diễn.
- MVP so sánh baseline với tối đa một model bảng nhẹ chạy CPU, không AutoML hoặc quét tham số lớn.

### US9 — Chạy shadow thủ công và tạo hồ sơ dự đoán (P1)

Baseline hoặc model vượt rubric tự động được chạy shadow cục bộ, không phát cảnh báo vận hành. Trường hợp chưa đủ mẫu nhưng kỹ thuật an toàn được chạy ở chế độ học hỏi đọc-only. Người dùng chủ động nhập lô dữ liệu mới; scheduler chỉ được thêm khi việc chạy lặp lại đã ổn định. Khi vượt threshold, hệ thống tạo hoặc cập nhật hồ sơ dự đoán có dedup/cooldown để kỹ sư xem. Kết quả kiểm tra thực tế được gắn là đúng, sai hoặc chưa đủ dữ liệu.

- Không có lệnh PLC, không tự dừng máy, không tự đổi thông số.
- Mọi dự đoán lưu snapshot feature tại thời điểm dự báo để ngăn nhìn trước tương lai.
- Shadow đọc-only được tự mở theo rubric có version; chỉ việc tác động máy, đổi thông số hoặc quyết định chặn/xuất hàng mới cần một đặc tả và quyền vận hành riêng.

### US10 — Cảnh báo có duyệt và đề xuất phòng ngừa (P3)

Sau khi shadow đạt gate, hệ thống mới được mở cảnh báo trong Workspace Chat cho người được ủy quyền và tạo đề xuất kiểm tra/phòng ngừa từ thư viện hành động đã duyệt.

- Mỗi cảnh báo có nút xác nhận, bác bỏ, tạm ẩn và mở case.
- Hành động vẫn là proposal; người có thẩm quyền quyết định áp dụng.
- LSU/Iris phải hoàn tất pilot trước khi bật adapter Drum/DLP.

### US11 — Vận hành thư viện công ty chung và pilot tổ chức (P3)

Chủ sở hữu nghiệm thu NAS/thư viện thật, backup/restore, một writer–nhiều reader và một pilot liên ca có bàn giao case giữa người dùng.

- Kiểm tra NAS, pilot nhiều người và mở rộng Drum/DLP là ba điều kiện độc lập; không gộp chúng thành một lần phát hành bắt buộc.
- Nếu thiếu dữ liệu hoặc môi trường thật, trạng thái giữ `PARTIAL`, không dùng test tổng hợp để thay thế.
- Dữ liệu thật không được commit và không xuất hiện trong report kiểm thử.

## 5. Yêu cầu chức năng

- **FR-001**: Workspace Chat phải có điểm vào “Hồ sơ vụ việc” với danh sách, lọc và màn hình chi tiết.
- **FR-002**: Kho hồ sơ phải có schema migration có version, backup trước migration và rollback được.
- **FR-003**: Case phải hỗ trợ ba loại `investigation`, `prediction`, `agent_work` cùng state machine được kiểm tra phía service.
- **FR-004**: Evidence, review, activity, approval và outcome phải append-only hoặc versioned; không cập nhật phá hủy lịch sử.
- **FR-005**: Quyền người dùng/chuyên gia phải dựa trên cấu hình role/scope do chủ sở hữu cung cấp, không tin boolean từ UI. Cổng rubric tự động dùng vai trò hệ thống riêng và không được tự tạo hoặc nâng quyền con người.
- **FR-006**: Hệ thống phải hỗ trợ yêu cầu thêm bằng chứng, assignment và xung đột ý kiến.
- **FR-007**: Bài học chỉ được promotion từ review `confirmed` và được truy xuất từ kho riêng có provenance.
- **FR-008**: Pilot line phải bảo toàn `suspected`, provenance nguồn và relevance review.
- **FR-009**: Artifact Agent phải được phân loại theo loại đầu ra, risk tier, template, verifier và approver.
- **FR-010**: Agent lập trình phải dùng task pack, phạm vi file/lệnh, proposal, observed tests và workspace tách biệt.
- **FR-011**: Kho dự đoán phải tách khỏi `library.sqlite`, `line_events.sqlite` và `workspace_cases.sqlite`, nhưng liên kết bằng ID/digest bất biến.
- **FR-012**: Dataset/model/prediction phải có version, digest, thời gian hiệu lực và đường rollback.
- **FR-013**: Đánh giá model phải chống outcome leakage và dùng phép chia theo thời gian/nhóm phù hợp.
- **FR-014**: Shadow prediction chỉ tạo hồ sơ/queue cục bộ; production alert và plant control mặc định bị cấm.
- **FR-015**: Kết quả chuyên gia `confirmed`, `false_alarm`, `unknown`, `effective`, `ineffective` phải quay về thành outcome có provenance.
- **FR-016**: Mọi câu chữ người dùng hoặc người vận hành thấy phải là tiếng Việt dễ hiểu: giao diện, hướng dẫn, tiến độ, trạng thái, cảnh báo, lỗi, thông báo, nhật ký vận hành và báo cáo; không dùng câu tiếng Anh làm phương án dự phòng.
- **FR-017**: `local_only` không được rời máy qua Gemini Web/Nakazasen Router hoặc qua tác tử phát triển dùng model cloud; C-AGENT chỉ được dùng theo policy và đồng ý hiện có. Tác tử cloud chỉ được dùng fixture giả hoàn toàn hoặc manifest đã làm sạch.
- **FR-018**: Không module Workspace Chat được hỗ trợ nào import `studio` hoặc `case_cockpit`.
- **FR-019**: Dịch vụ hồ sơ phải cho phép gắn thêm tham chiếu bằng chứng vào case hiện hữu theo kiểu append-only, kiểm tra role/scope, digest, provenance và optimistic version.
- **FR-020**: `tasks.md` chỉ được chứa task của đợt đang thực thi; đợt T001–T029 chỉ thực thi US1, US2, US7, US8 và US9. Các US chưa đủ điều kiện vẫn phải còn trong đặc tả và kế hoạch dưới dạng backlog có điều kiện.
- **FR-021**: Luồng xác nhận phải cho phép người điều tra kiêm chuyên gia trong đúng phạm vi công đoạn; chuyên gia thứ hai là tùy chọn. Nhãn có nguồn máy hợp lệ được xác nhận tự động, còn sửa/bác bỏ của con người phải append-only và có lý do.
- **FR-022**: Dữ liệu Iris LSU phải liên kết tường minh `component_lot_id → unit_serial → jig_id → measurement → outcome`; bản ghi không nối được phải vào báo cáo thiếu dữ liệu, không được tự ghép theo tên file.
- **FR-023**: Lát cắt đầu tiên phải cấu hình cho BOWSKEW 4 BEAM và không hard-code vào lõi dùng chung; các JIG/Unit khác chỉ mở sau khi lát cắt đầu hoạt động.
- **FR-024**: MVP phải có đường hoàn thành khi dữ liệu chưa đủ cho học máy: phương án không cảnh báo/EWMA và báo cáo thiếu dữ liệu là đầu ra hợp lệ; tuyệt đối không tạo model hoặc độ chính xác giả.
- **FR-025**: Tiếng Việt là ngôn ngữ giao diện duy nhất; lỗi tiếng Anh từ thư viện, hệ điều hành hoặc dịch vụ phải được chặn và đổi thành lời giải thích cùng bước xử lý bằng tiếng Việt trước khi hiển thị. Mã thiết bị, tên tệp và hằng máy đọc chỉ là định danh, không được dùng thay cho câu giải thích.
- **FR-026**: Mỗi mốc phải có gói dữ liệu mẫu đã làm sạch, runtime thử nghiệm tách khỏi dữ liệu người dùng, kiểm thử độc lập và đầu ra kỹ thuật có thể chạy lại trên Python 3.11. Một cổng vận hành thiếu dữ liệu, người duyệt hoặc môi trường thật chỉ chặn việc kích hoạt nhánh phụ thuộc; không được chặn sửa nền, xây giao diện trạng thái, hoàn thiện công cụ kiểm tra hoặc triển khai nhánh độc lập khác.
- **FR-027**: T011, T022 và T029 phải dùng rubric có version/digest để tự kết luận; tác tử không được đổi ngưỡng sau khi thấy kết quả. T029 phải do tác tử kiểm toán khác tác tử thực thi và được phép tự đóng cổng kỹ thuật sau tối đa hai vòng sửa–kiểm tra lại.
- **FR-028**: AI được tự đăng ký snapshot hợp lệ, chọn `AUTO_SHADOW` hoặc `LEARNING_SHADOW` và xác nhận outcome từ nguồn máy đủ provenance. AI không được điều khiển máy, sửa PLC, đổi thông số, chặn/xuất hàng hoặc xóa/ghi đè nguồn.

## 6. Tiêu chí thành công đo được

SC-001–SC-003, SC-007–SC-009 và SC-011–SC-015 áp dụng cho đợt T001–T029 theo phần năng lực đã kích hoạt. SC-004–SC-006 và SC-010 là tiêu chí của các đợt sau; chúng được giữ để không mất đích nhưng không được dùng để ép Gemini mở rộng phạm vi hiện tại.

- **SC-001**: Người dùng mở một case đã lưu trong tối đa ba thao tác từ Workspace Chat mà không hỏi lại RAG.
- **SC-002**: 100% loại bản ghi đã được kích hoạt trong đợt hiện tại đọc lại được sau restart trong test và không có bản ghi nửa vời khi fault injection; lesson/artifact chỉ áp dụng khi đợt tương ứng được mở.
- **SC-003**: 100% transition trái quyền, thiếu evidence, sai digest hoặc thiếu lý do bị từ chối phía service.
- **SC-004 — đợt sau**: 100% bài học dùng lại truy vết được đến case, review và evidence digest gốc.
- **SC-005 — đợt sau**: Pilot line thật hoàn thành ít nhất một case end-to-end với báo cáo được duyệt; kết quả vẫn được mô tả là hỗ trợ điều tra, không phải chẩn đoán tự động.
- **SC-006 — đợt sau**: 100% artifact chính thức có phiên bản, evidence digest, reviewer và không ghi đè nguồn.
- **SC-007**: Báo cáo phát lại chứa số cảnh báo đúng/nhầm/bỏ sót, lead time, temporal split và dataset/phương pháp digest; calibration chỉ bắt buộc khi phương pháp tạo xác suất và có đủ mẫu để đo.
- **SC-008**: Trong shadow, 100% risk signal có snapshot đầu vào, phiên bản phương pháp, threshold version và outcome review; không có hành động điều khiển máy.
- **SC-009**: Full quality gates của repo đạt trước mỗi lần đóng gate; thiếu lệnh hoặc timeout được ghi `PARTIAL`/`BLOCKED`, không phải PASS.
- **SC-010 — đợt sau**: Gate A NAS chỉ chuyển khỏi `PARTIAL` sau smoke thật có bằng chứng backup/restore và một writer–nhiều reader.
- **SC-011**: Với mỗi Unit đủ dữ liệu trong pilot, người dùng truy được lot linh kiện, thông số đầu vào, JIG/lần đo và outcome cuối trong một màn hình mà không dò thủ công nhiều file.
- **SC-012**: Một lượt phát lại lịch sử xuất được số cảnh báo đúng, cảnh báo nhầm, bỏ sót và thời gian cảnh báo sớm so với cùng một baseline; thiếu dữ liệu được báo rõ thay vì bỏ qua.
- **SC-013**: Trong shadow thủ công, người dùng nhập một lô dữ liệu mới, nhận danh sách nguy cơ có căn cứ và ghi kết quả thực tế mà không có lệnh điều khiển máy hoặc gửi dữ liệu ra ngoài.
- **SC-014**: Với mọi luồng thuộc MVP, kiểm thử bao phủ trạng thái bình thường, trống, chờ, thành công, cảnh báo và lỗi; khi cố ý tạo lỗi bên ngoài, không có câu tiếng Anh, traceback hoặc thuật ngữ kỹ thuật không giải thích xuất hiện trước người dùng.
- **SC-015**: Mốc 2–4 đều chạy hết đường kỹ thuật bằng fixture đã làm sạch khi chưa có dữ liệu thật; báo cáo phân biệt rõ `TECHNICAL_PASS`, `OPERATIONAL_PARTIAL` và `OPERATIONAL_BLOCKED`, không dùng kết quả fixture để thay bằng chứng pilot.

## 7. Ranh giới không thương lượng

- Không tự kết luận nguyên nhân gốc rễ chỉ từ tương quan, log hoặc output model.
- Không tự chạy hành động nhà máy, sửa PLC, dừng line, chặn/xuất hàng hoặc đổi thông số.
- Không xóa/ghi đè dữ liệu nguồn; artifact mới phải versioned và rollback được.
- Không dùng chat thô, output AI hoặc tên client làm nhãn/bằng chứng.
- Không bật cảnh báo vận hành trước khi shadow vượt rubric có version và có nút tắt; chạy bóng đọc-only không phải hành động vận hành máy.
- Không mở Drum/DLP chỉ để “đủ phạm vi” trước khi lát cắt LSU/Iris hoàn thành và adapter lõi được chứng minh.
- Không phát hành màn hình, thông báo hoặc nhật ký vận hành còn câu tiếng Anh; nguồn bằng chứng có thể giữ nguyên ngôn ngữ gốc nhưng phần điều khiển và giải thích của chương trình phải là tiếng Việt.

## 8. Mặc định tự động và trường hợp mới cần chủ sở hữu

T011 và T022 dùng thẳng mẫu từ điển dữ liệu cùng rubric có version; không chờ người dùng tự nghĩ metric, công thức SPC, cỡ mẫu hoặc ngưỡng chạy bóng. Cấu hình cục bộ có thể ghi đè về sau và luôn có đường quay lại.

Chỉ các quyết định sau vẫn cần chủ sở hữu vì có tác động ngoài phạm vi đọc-only:

1. Cấp hoặc nâng quyền cho một người/chuyên gia thật.
2. Xóa dữ liệu, thay chính sách lưu giữ hoặc phục hồi đè lên kho đang dùng.
3. Cho phép tài liệu/log nhạy cảm rời khỏi vùng cục bộ.
4. Bật cảnh báo ra ngoài ứng dụng hoặc hành động làm thay đổi máy, line, thông số, chặn/xuất hàng.

Thiếu các quyết định này không chặn T001–T029, Data Gate, phát lại hay chạy bóng đọc-only. Hệ thống tiếp tục bằng mặc định an toàn và ghi rõ việc nào chưa được phép tác động ngoài đời.
