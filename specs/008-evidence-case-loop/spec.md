# Đặc tả tính năng: Trợ lý công việc khép kín từ vụ việc đến phòng ngừa lỗi

**Mã nhánh tính năng**: `008-evidence-case-loop`  
**Ngày cập nhật**: 30/08/2026

**Trạng thái**: Chủ sở hữu đã duyệt Gate 1A + US1 để triển khai
**Phạm vi**: Workspace Chat, hồ sơ vụ việc, chuyên gia, bài học, trợ lý tạo đầu ra công việc, điều tra line và thử nghiệm dự đoán có kiểm soát.

## 1. Ý đồ sản phẩm bằng ngôn ngữ đời thường

AIOS không được dừng ở mức “hỏi tài liệu rồi trả lời như chatbot”. Sản phẩm phải là một **trợ lý công việc chủ động nhưng có chốt duyệt**, gần với hình ảnh “Đôrêmon có kiểm soát”:

1. Người dùng đưa vào một vấn đề, log, ảnh, tài liệu và mô tả hiện trường.
2. Hệ thống tự gom thành hồ sơ, dòng thời gian và danh sách bằng chứng.
3. Hệ thống chỉ ra còn thiếu gì, hỏi ngược câu cần thiết và chuyển đúng việc cho người có chuyên môn.
4. Hệ thống tạo đầu ra hữu ích như báo cáo điều tra, SOP, hồ sơ thiết kế công đoạn, bảng kiểm tra hoặc đề xuất thay đổi mã nguồn.
5. Con người xem, sửa và phê duyệt theo mức rủi ro trước khi đầu ra được áp dụng.
6. Kết quả thực tế đã xác nhận trở thành bài học để lần sau hệ thống hỗ trợ nhanh và đúng hơn.

“Hồ sơ vụ việc” không phải ticket hành chính bắt mọi việc phải xin chữ ký. Nó là bìa hồ sơ chung cho một việc quan trọng, lặp lại, chưa rõ nguyên nhân hoặc cần bàn giao. Việc đơn giản vẫn có thể xử lý trực tiếp trong Workspace Chat mà không tạo hồ sơ.

## 2. Trạng thái thật tại thời điểm lập kế hoạch

| Nhánh năng lực | Trạng thái đã kiểm chứng |
|---|---|
| RAG tài liệu nội bộ | Có nền BGE-M3 hybrid, chunking, citation và evidence. Vận hành thư viện chung trên dữ liệu/NAS thật vẫn `PARTIAL`. |
| Gói bằng chứng điều tra | Đã ghép citation tài liệu với lát log `suspected` từ `line_events.sqlite`. |
| Lưu hồ sơ từ Workspace Chat | Đã có commit Cổng 1 lưu metadata và tham chiếu bằng chứng vào `local_cases/workspace_cases.sqlite`; bộ test tập trung hiện tại đạt 80 bài. Chưa có danh sách/màn hình mở lại hồ sơ. |
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

- Không có người nhận hợp lệ, phạm vi quyền hoặc lý do thì không thể xác nhận.
- Mọi phản hồi là append-only; sửa ý kiến phải tạo bản mới.
- Hai ý kiến trái chiều được giữ nguyên và chuyển sang trạng thái cần phân xử.

### US3 — Học từ phản hồi đã xác nhận và dùng lại có truy vết (P1)

Quản lý chọn một thẩm định `confirmed`, tạo bài học ứng viên, sửa nội dung và promotion thành bài học chính thức. Lần sau Workspace Chat có thể tìm bài học liên quan trong kho case-memory riêng và luôn dẫn về case/review/evidence gốc.

- Không tự huấn luyện lại model và không ghi bài học vào `library.sqlite`.
- Bài học chưa promotion không được dùng như sự thật.
- Bài học bị thu hồi không xuất hiện trong kết quả dùng lại thông thường.

### US4 — Trợ lý điều tra line chủ động (P1)

Trong một hồ sơ điều tra, hệ thống gom log, SOP, ảnh/biên bản được phép, dựng dòng thời gian, nhóm hiện tượng lặp lại và sinh danh sách câu hỏi còn thiếu. Chuyên gia xác nhận tính liên quan của từng manh mối trước khi kết luận.

- Log luôn bắt đầu là `suspected`; không match thì không tự lấy năm event mới nhất làm bằng chứng.
- CSV thô không đi vào RAG.
- Mapping sơ đồ chỉ hiển thị khi nguồn mapping có phiên bản và đã được chuyên gia duyệt.
- Pilot chỉ đạt khi có ít nhất một case thật đi từ mở hồ sơ đến báo cáo được duyệt và kết luận outcome.

### US5 — Agent tạo đầu ra công việc có kiểm soát (P1)

Từ một case có đủ bằng chứng, người dùng yêu cầu Agent tạo báo cáo, SOP, hồ sơ thiết kế công đoạn, bảng tính hoặc sơ đồ mới. Agent phải cho xem nguồn đã dùng, bản khác biệt giữa các phiên bản và người phê duyệt.

- Chỉ tạo artifact mới trong vùng output được phép; không xóa hoặc ghi đè nguồn nhà máy.
- Mỗi loại artifact có template, bộ kiểm tra và vai trò duyệt riêng.
- “Kiến thức được đào tạo” trong phạm vi này nghĩa là tài liệu và bài học đã xác nhận được truy xuất có citation, không phải tự fine-tune từ chat thô.

### US6 — Agent hỗ trợ lập trình trong workspace tách biệt (P2)

Người dùng giao một task lập trình có phạm vi file và lệnh kiểm thử rõ. Agent đọc code, đề xuất diff, chạy lệnh trong sandbox/workspace được tin cậy và chờ phê duyệt trước khi áp dụng thay đổi.

- Không dùng workspace lập trình để truy cập `local_cases/`, dữ liệu nhà máy hoặc điều khiển line.
- Mọi patch/command có proposal bất biến, diff hiển thị, allowlist và audit event.
- PASS chỉ được ghi khi có observed evidence từ test thật; AI không tự merge/push nếu chưa có quyền riêng.

### US7 — Nền dữ liệu dự đoán dùng chung cho LSU/Drum/DLP (P2)

Kỹ sư dữ liệu nạp lịch sử đo, serial/asset, phiên bản jig/quy trình và outcome OK/NG đã xác nhận vào kho dự đoán cục bộ có version. Adapter LSU/Iris là lát cắt đầu tiên; Drum và DLP dùng cùng hợp đồng lõi nhưng mapping riêng.

- Khóa join, đơn vị, múi giờ, thời điểm sự kiện và thời điểm dữ liệu đến phải tường minh.
- Nhãn tối thiểu gồm `confirmed`, `false_alarm`, `unknown`; không suy ra nhãn từ tên file.
- Dữ liệu thiếu hoặc có nguy cơ rò rỉ outcome làm gate bị `blocked`.

### US8 — Huấn luyện và đánh giá model dự đoán có trách nhiệm (P2)

Nhóm kỹ thuật chạy baseline rule/SPC và model ứng viên trên snapshot dữ liệu đóng băng, chia theo thời gian/nhóm thiết bị, so sánh với cùng giao thức và ghi model card.

- Báo riêng precision, recall, false alarm, missed detection, lead time, calibration và độ ổn định theo máy/ca/thời gian.
- Không chọn model chỉ vì accuracy trung bình cao.
- Model, feature schema, dataset digest, code version và threshold đều có version/rollback.

### US9 — Chạy thử nghiệm bóng và tạo hồ sơ dự đoán (P2)

Model được duyệt cho shadow chạy cục bộ, không phát cảnh báo vận hành. Khi vượt threshold, nó tạo hoặc cập nhật hồ sơ dự đoán có dedup/cooldown để kỹ sư xem. Kết quả kiểm tra thực tế được gắn là đúng, sai hoặc chưa đủ dữ liệu.

- Không có lệnh PLC, không tự dừng máy, không tự đổi thông số.
- Mọi dự đoán lưu snapshot feature tại thời điểm dự báo để ngăn nhìn trước tương lai.
- Shadow chỉ được nâng cấp khi đủ số case và ngưỡng do chủ sở hữu ký duyệt.

### US10 — Cảnh báo có duyệt và đề xuất phòng ngừa (P3)

Sau khi shadow đạt gate, hệ thống mới được mở cảnh báo trong Workspace Chat cho người được ủy quyền và tạo đề xuất kiểm tra/phòng ngừa từ thư viện hành động đã duyệt.

- Mỗi cảnh báo có nút xác nhận, bác bỏ, tạm ẩn và mở case.
- Hành động vẫn là proposal; người có thẩm quyền quyết định áp dụng.
- LSU/Iris phải hoàn tất pilot trước khi bật adapter Drum/DLP.

### US11 — Vận hành thư viện công ty chung và pilot tổ chức (P3)

Chủ sở hữu nghiệm thu NAS/thư viện thật, backup/restore, một writer–nhiều reader và một pilot liên ca có bàn giao case giữa người dùng.

- Nếu thiếu dữ liệu hoặc môi trường thật, trạng thái giữ `PARTIAL`, không dùng test tổng hợp để thay thế.
- Dữ liệu thật không được commit và không xuất hiện trong report kiểm thử.

## 5. Yêu cầu chức năng

- **FR-001**: Workspace Chat phải có điểm vào “Hồ sơ vụ việc” với danh sách, lọc và màn hình chi tiết.
- **FR-002**: Kho hồ sơ phải có schema migration có version, backup trước migration và rollback được.
- **FR-003**: Case phải hỗ trợ ba loại `investigation`, `prediction`, `agent_work` cùng state machine được kiểm tra phía service.
- **FR-004**: Evidence, review, activity, approval và outcome phải append-only hoặc versioned; không cập nhật phá hủy lịch sử.
- **FR-005**: Quyền chuyên gia/phê duyệt phải dựa trên cấu hình role/scope do chủ sở hữu cung cấp, không tin boolean từ UI.
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
- **FR-016**: Mọi UI, cảnh báo và lỗi người dùng thấy phải bằng tiếng Việt, không lộ traceback, secret hoặc đường dẫn hệ thống.
- **FR-017**: `local_only` không được rời máy qua Gemini Web/Nakazasen Router; C-AGENT chỉ được dùng theo policy và đồng ý hiện có.
- **FR-018**: Không module Workspace Chat được hỗ trợ nào import `studio` hoặc `case_cockpit`.
- **FR-019**: Dịch vụ hồ sơ phải cho phép gắn thêm tham chiếu bằng chứng vào case hiện hữu theo kiểu append-only, kiểm tra role/scope, digest, provenance và optimistic version.

## 6. Tiêu chí thành công đo được

- **SC-001**: Người dùng mở một case đã lưu trong tối đa ba thao tác từ Workspace Chat mà không hỏi lại RAG.
- **SC-002**: 100% case/review/lesson/artifact/prediction đọc lại được sau restart trong test và không có bản ghi nửa vời khi fault injection.
- **SC-003**: 100% transition trái quyền, thiếu evidence, sai digest hoặc thiếu lý do bị từ chối phía service.
- **SC-004**: 100% bài học dùng lại truy vết được đến case, review và evidence digest gốc.
- **SC-005**: Pilot line thật hoàn thành ít nhất một case end-to-end với báo cáo được duyệt; kết quả vẫn được mô tả là hỗ trợ điều tra, không phải chẩn đoán tự động.
- **SC-006**: 100% artifact chính thức có phiên bản, evidence digest, reviewer và không ghi đè nguồn.
- **SC-007**: Báo cáo model chứa confusion matrix, false-alarm rate, missed-detection rate, lead time, calibration, temporal split và dataset/model digest.
- **SC-008**: Trong shadow, 100% risk signal có feature snapshot, model version, threshold version và outcome review; không có hành động điều khiển máy.
- **SC-009**: Full quality gates của repo đạt trước mỗi lần đóng gate; thiếu lệnh hoặc timeout được ghi `PARTIAL`/`BLOCKED`, không phải PASS.
- **SC-010**: Gate A NAS chỉ chuyển khỏi `PARTIAL` sau smoke thật có bằng chứng backup/restore và một writer–nhiều reader.

## 7. Ranh giới không thương lượng

- Không tự kết luận nguyên nhân gốc rễ chỉ từ tương quan, log hoặc output model.
- Không tự chạy hành động nhà máy, sửa PLC, dừng line, chặn/xuất hàng hoặc đổi thông số.
- Không xóa/ghi đè dữ liệu nguồn; artifact mới phải versioned và rollback được.
- Không dùng chat thô, output AI hoặc tên client làm nhãn/bằng chứng.
- Không bật cảnh báo vận hành trước khi shadow đạt ngưỡng do chủ sở hữu phê duyệt.
- Không mở Drum/DLP chỉ để “đủ phạm vi” trước khi lát cắt LSU/Iris hoàn thành và adapter lõi được chứng minh.

## 8. Quyết định bắt buộc của chủ sở hữu trước từng gate

1. Danh sách role/scope và người có quyền thẩm định, promotion, phát hành artifact, duyệt shadow.
2. Chính sách retention/xóa và backup cho `workspace_cases.sqlite` cùng kho dự đoán.
3. Bộ log/SOP/mapping được phép dùng cho pilot line.
4. Data dictionary, join keys, đơn vị, nhãn và chi phí tương đối của cảnh báo sai/bỏ sót cho LSU/Iris.
5. Loại hồ sơ thiết kế công đoạn cần hỗ trợ đầu tiên và verifier tương ứng.
6. Ngưỡng đóng shadow và điều kiện mở cảnh báo trong Workspace Chat.

Thiếu quyết định nào thì gate phụ thuộc phải giữ `BLOCKED`; các gate độc lập vẫn được tiếp tục theo thứ tự đã phê duyệt.
