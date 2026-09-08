# Đặc tả: Phỏng vấn chuyên gia và làm giàu tri thức có kiểm soát

**Mã tính năng**: `010-expert-knowledge-acquisition`  
**Nhánh lập kế hoạch**: `gate1-local-case-sqlite`  
**Ngày tạo**: 2026-09-07  
**Trạng thái**: `READY_FOR_TASK_EXECUTION`

## 1. Mục tiêu

Nâng quy trình hỏi–đáp có cấu trúc hiện tại thành một vòng thu nhận tri thức thực tế: hệ thống tìm khoảng trống có bằng chứng, chuẩn bị cuộc phỏng vấn đúng chuyên gia, hỏi tiếp khi câu trả lời còn mơ hồ, chép lời cục bộ khi được đồng ý, trích xuất tri thức dạng ứng viên, rồi chỉ xuất bản nội dung đã được người có thẩm quyền duyệt.

Hệ thống không tự nhận mình đã “phát hiện toàn bộ” khoảng trống, không coi transcript là sự thật, không tự phong người dùng thành chuyên gia và không tự fine-tune từ dữ liệu chưa duyệt.

## 2. Hành trình người dùng và kiểm thử

### US1 — Lập bản đồ khoảng trống tri thức có bằng chứng (P1)

Người quản lý chọn một thư viện, phạm vi công đoạn và bộ câu hỏi kiểm tra. Hệ thống đối chiếu tài liệu, kết quả truy xuất, hồ sơ sự cố và phản hồi chuyên gia để đề xuất các khoảng trống cần làm rõ.

**Kiểm thử độc lập**: dùng corpus fixture có khoảng trống, xung đột và tài liệu lỗi thời đã biết; hệ thống phải tạo đúng ứng viên có dẫn chứng và không tuyên bố bao phủ tuyệt đối.

**Tiêu chí chấp nhận**:

1. Mỗi ứng viên khoảng trống chỉ ra phạm vi, câu hỏi thất bại, nguồn đã kiểm tra, lý do thiếu/xung đột/lỗi thời và mức ưu tiên.
2. Ứng viên không có bằng chứng hoặc chỉ do model suy đoán không được chuyển sang kế hoạch phỏng vấn.
3. Người có quyền có thể gộp, bác bỏ, hoãn hoặc giao ứng viên cho một nhóm chuyên gia.

### US2 — Phỏng vấn nhiều vòng theo chuyên gia và công đoạn (P1)

Chuyên gia đã xác thực nhận một kế hoạch đúng phạm vi của mình, trả lời bằng văn bản hoặc chọn “không biết/không chắc”. Hệ thống hỏi tiếp có giới hạn để làm rõ điều kiện, ngưỡng, ngoại lệ, ví dụ và nguồn xác minh.

**Kiểm thử độc lập**: chạy phiên fixture có câu trả lời rõ, mơ hồ, mâu thuẫn và từ chối; kiểm tra câu hỏi tiếp nối, giới hạn lượt, quyền dừng và khả năng tiếp tục sau restart.

**Tiêu chí chấp nhận**:

1. Danh tính được lấy từ ngữ cảnh xác thực, không từ prompt hay trường tự khai; quyền theo phạm vi được kiểm tra trước mỗi thao tác.
2. Câu hỏi tiếp theo phải liên kết với khoảng trống hoặc câu trả lời trước, không lặp vô hạn và không dẫn dắt chuyên gia xác nhận giả thuyết.
3. Chuyên gia luôn có thể bỏ qua, sửa câu trả lời, đánh dấu không chắc, tạm dừng hoặc kết thúc phiên.
4. Mất kết nối hoặc restart không làm mất câu trả lời đã lưu và không gửi lặp câu hỏi.

### US3 — Ghi âm và chép lời cục bộ có đồng ý (P2)

Khi chuyên gia chủ động đồng ý, hệ thống ghi âm buổi phỏng vấn, hiển thị trạng thái ghi rõ ràng, chép lời trên máy và cho phép sửa các mã máy, thông số, tên riêng trước khi ký xác nhận.

**Kiểm thử độc lập**: chạy audio fixture tiếng Việt có mã thiết bị và số đo, thử đồng ý/từ chối/rút đồng ý, ngắt giữa chừng và chép lời lại; xác minh audio không rời máy và nội dung xuất bản đã được sửa tay.

**Tiêu chí chấp nhận**:

1. Không ghi âm trước đồng ý; rút đồng ý dừng ghi ngay và xử lý dữ liệu theo quyết định lưu giữ đã cấu hình.
2. Audio và transcript thô nằm ngoài Git, ngoài `library.sqlite` và ngoài `workspace_cases.sqlite`; hồ sơ chỉ giữ locator cục bộ, digest và trạng thái đồng ý.
3. Mọi mã máy, đơn vị, ngưỡng và giá trị số trong nội dung sắp xuất bản phải được người duyệt xác nhận.
4. Lỗi thiết bị/chép lời được giải thích bằng tiếng Việt và không làm mất phần phiên đã lưu.

### US4 — Tạo và duyệt SOP/bài học có truy nguyên (P2)

Hệ thống tách câu trả lời thành các phát biểu có nguồn, nhận diện xung đột và tạo bản nháp SOP hoặc bài học. Chuyên gia và người phê duyệt tài liệu xem diff, sửa, bác bỏ hoặc ký duyệt.

**Kiểm thử độc lập**: từ transcript fixture tạo phát biểu, một xung đột, một SOP nháp và bài học; xác minh nội dung chưa duyệt không xuất hiện trong tìm kiếm thường.

**Tiêu chí chấp nhận**:

1. Mọi phát biểu có liên kết tới đoạn transcript/tài liệu/case nguồn, người xác nhận và phiên bản.
2. Hai câu trả lời mâu thuẫn giữ trạng thái `conflicted`; hệ thống không tự chọn bên thắng.
3. SOP/bài học chỉ là `candidate` cho đến khi đủ vai trò và phạm vi phê duyệt.
4. Bản sửa và quyết định duyệt/bác bỏ/thu hồi được ghi append-only và đọc lại sau restart.

### US5 — Xuất bản an toàn vào thư viện và đánh giá sử dụng (P3)

Người quản lý xuất bản gói tri thức đã duyệt vào đúng collection. Hệ thống sao lưu, khóa ghi, nạp phiên bản, kiểm tra SQLite và chạy bộ câu hỏi truy xuất có citation; phiên bản sai có thể thu hồi hoặc thay thế.

**Kiểm thử độc lập**: xuất bản một SOP đã duyệt vào collection fixture, truy vấn được với citation, thử xuất bản ứng viên chưa duyệt bị chặn, rồi thu hồi và xác minh không còn được dùng trong trả lời thường.

**Tiêu chí chấp nhận**:

1. Chỉ `PublicationPackage` đã duyệt, đúng digest và đúng collection mới được nạp qua đường ingest chuẩn.
2. Ghi thư viện dùng writer lease, backup và `quick_check`; lỗi giữa chừng phải hoàn tác hoặc giữ bản cũ sử dụng được.
3. Nội dung bị thu hồi/thay thế không còn được trả như tri thức hiện hành nhưng lịch sử audit vẫn còn.
4. Fine-tune không chạy trong bản đầu; chỉ có báo cáo đủ/không đủ điều kiện sau khi dữ liệu đã duyệt và retrieval baseline được đo.

## 3. Trường hợp biên bắt buộc

- Một người có nhiều vai trò nhưng chỉ được duyệt ở một công đoạn; tài khoản bị vô hiệu hóa giữa phiên.
- Hai chuyên gia cùng cấp đưa ra ngưỡng trái nhau; một người sửa câu trả lời sau khi SOP đã được tạo.
- Corpus không có tài liệu, tài liệu không đọc được, citation hỏng hoặc câu hỏi nằm ngoài phạm vi đã kiểm kê.
- Model hỏi lặp, hỏi dẫn dắt, vượt ngân sách hoặc tạo nội dung không có trong câu trả lời.
- Microphone bị chiếm dụng, audio mất đoạn, có nhiều người nói, tiếng ồn cao hoặc chép sai mã thiết bị.
- Chuyên gia từ chối ghi âm nhưng vẫn muốn trả lời bằng văn bản; rút đồng ý sau buổi phỏng vấn.
- Library đang có writer khác, ổ đĩa đầy, digest thay đổi sau duyệt hoặc nạp thư viện bị ngắt.
- Đường dẫn Windows có khoảng trắng/tiếng Việt; transcript UTF-8 không mojibake.
- Dữ liệu `local_only`, bí mật thương mại hoặc thông tin cá nhân không được gửi qua provider không được phép.

## 4. Yêu cầu chức năng

- **FR-001**: Hệ thống phải kiểm kê phạm vi tài liệu và định nghĩa bộ câu hỏi/tiêu chí bao phủ trước khi đề xuất khoảng trống.
- **FR-002**: Mỗi `KnowledgeGapCandidate` phải có evidence, loại khoảng trống, phạm vi, mức ưu tiên và trạng thái duyệt.
- **FR-003**: Hệ thống phải lập `InterviewPlan` theo khoảng trống, công đoạn, vai trò chuyên gia, thời lượng và tiêu chí kết thúc.
- **FR-004**: Phiên phỏng vấn phải là máy trạng thái hữu hạn, có giới hạn lượt/thời gian/token và checkpoint để tiếp tục an toàn.
- **FR-005**: Hệ thống phải hỏi tiếp khi thiếu điều kiện, ngưỡng, ngoại lệ, ví dụ, phản ví dụ, độ chắc chắn hoặc nguồn; không hỏi tiếp ngoài phạm vi.
- **FR-006**: Mỗi câu hỏi và câu trả lời phải có ID, thứ tự, thời điểm, nguồn kích hoạt và digest chống ghi lặp.
- **FR-007**: Hệ thống phải hỗ trợ `unknown`, `uncertain`, `skip`, `pause`, `stop` mà không ép chuyên gia trả lời.
- **FR-008**: Chế độ nhiều người dùng phải fail-closed nếu không ánh xạ được danh tính xác thực tới hồ sơ chuyên gia và phạm vi quyền.
- **FR-009**: Bản đầu phải dùng ranh giới `IdentityProvider`; ưu tiên danh tính Windows/OS hoặc SSO doanh nghiệp, không tự xây kho mật khẩu.
- **FR-010**: Ghi âm là tùy chọn, cần đồng ý rõ ràng, chỉ báo đang ghi và khả năng rút đồng ý.
- **FR-011**: Chép lời phải chạy cục bộ theo adapter có phiên bản; lựa chọn engine chỉ được khóa sau benchmark tiếng Việt có thuật ngữ công đoạn.
- **FR-012**: Audio/transcript thô phải ở vùng `local_only` ngoài Git; kho case chỉ giữ metadata, locator và digest.
- **FR-013**: Hệ thống phải cho sửa transcript theo đoạn và lưu cả bản máy, bản sửa cùng người sửa để truy nguyên.
- **FR-014**: Hệ thống phải trích xuất `KnowledgeClaim` có nguồn đoạn, độ chắc chắn, phạm vi hiệu lực và trạng thái mâu thuẫn.
- **FR-015**: SOP/bài học được tạo tự động luôn ở trạng thái ứng viên và không được dùng như tri thức chính thức trước phê duyệt.
- **FR-016**: Phê duyệt phải kiểm tra actor, vai trò, phạm vi, digest và phiên bản; title tự khai không tạo quyền.
- **FR-017**: Nội dung mâu thuẫn phải được giữ nguyên và chuyển người có thẩm quyền; model không tự hòa giải thành sự thật.
- **FR-018**: Gói xuất bản phải là Markdown/JSON có version, source digest, quyết định duyệt và collection đích.
- **FR-019**: Nạp vào `library.sqlite` phải dùng API ingest hiện có, writer lease, backup, kiểm tra toàn vẹn và khả năng rollback.
- **FR-020**: Chỉ nội dung đã duyệt và chưa bị thu hồi mới xuất hiện trong retrieval thường; candidate/conflicted phải bị lọc.
- **FR-021**: Mỗi lần xuất bản phải chạy bộ câu hỏi chấp nhận và lưu receipt citation/truy xuất.
- **FR-022**: Hệ thống phải hỗ trợ thu hồi, thay thế và truy ngược phiên bản mà không xóa audit trail.
- **FR-023**: Fine-tune phải tắt mặc định; chỉ lập báo cáo điều kiện khi có đủ mẫu đã duyệt, ẩn danh, quyền sử dụng và baseline retrieval chứng minh nhu cầu.
- **FR-024**: Không được đưa audio/transcript thô, dữ liệu `local_only` hoặc nội dung chưa duyệt vào tập fine-tune.
- **FR-025**: Toàn bộ chữ người dùng nhìn thấy phải là tiếng Việt đời thường, gồm nhãn, nút, trạng thái, hướng dẫn, lỗi, tiến độ và báo cáo; cấm từ kỹ thuật tiếng Anh, traceback, tên engine/provider, tên trạng thái nội bộ và đường dẫn hệ thống trên giao diện.

## 5. Thực thể chính

- **ExpertProfile**: ánh xạ danh tính xác thực tới chuyên môn, công đoạn và trạng thái hoạt động; không chứa mật khẩu ứng dụng tự chế.
- **ScopeGrant**: quyền có thời hạn của actor trên công đoạn/hành động, có người cấp và lý do.
- **KnowledgeCoverageMap**: phạm vi, tài liệu đã kiểm kê, bộ câu hỏi và kết quả đo bao phủ.
- **KnowledgeGapCandidate**: khoảng trống đề xuất có evidence và quyết định xử lý.
- **InterviewPlan**: mục tiêu, người phù hợp, câu hỏi nền, ngân sách và tiêu chí kết thúc.
- **InterviewSession**: trạng thái phiên, consent, checkpoint và liên kết tới lượt hỏi–đáp.
- **InterviewTurn**: câu hỏi/câu trả lời, nguồn kích hoạt, mức chắc chắn và digest.
- **TranscriptSegment**: đoạn chép lời có mốc thời gian, bản máy, bản sửa và provenance.
- **KnowledgeClaim**: phát biểu nguyên tử có nguồn, phạm vi, độ chắc chắn và trạng thái xung đột.
- **KnowledgeArtifactCandidate**: bản nháp SOP/bài học có version và diff.
- **PublicationPackage**: gói bất biến đã duyệt để nạp vào collection.
- **PublicationReceipt**: kết quả backup, ingest, kiểm tra toàn vẹn, retrieval và rollback.

## 6. Tiêu chí thành công đo được

- **SC-001**: 100% khoảng trống được đưa vào phỏng vấn có ít nhất một evidence kiểm chứng được; 0 khoảng trống chỉ do model khẳng định.
- **SC-002**: 100% thao tác nhiều người dùng bị từ chối khi danh tính hoặc scope không hợp lệ; các negative test mượn danh đạt toàn bộ.
- **SC-003**: Hoàn thành diễn tập tự động với ít nhất 2 danh tính chuyên gia giả lập thuộc 2 phạm vi, 3 phiên và 5 khoảng trống được xử lý; hệ sẵn sàng nhận người thật mà không đổi code.
- **SC-004**: Xuất bản vào collection fixture tối thiểu 5 đơn vị tri thức và 1 quy trình đã duyệt; 100% phát biểu xuất bản truy ngược tới đoạn/source và danh tính duyệt giả lập.
- **SC-005**: 0 candidate/conflicted/revoked xuất hiện trong retrieval thường; 100% câu hỏi chấp nhận của gói xuất bản trả đúng citation hoặc thừa nhận chưa đủ căn cứ.
- **SC-006**: 100% mã máy, đơn vị, ngưỡng và số liệu trong artifact xuất bản từ audio được người có quyền xác nhận.
- **SC-007**: Audio/transcript thô không xuất hiện trong Git, `library.sqlite`, `workspace_cases.sqlite`, log thường hoặc payload provider ngoài policy.
- **SC-008**: Phiên pause/restart/resume không mất lượt đã lưu, không gửi lặp và không tạo hai artifact cho cùng idempotency key.
- **SC-009**: Full quality gate, E2E Windows đường dẫn tiếng Việt và quét giao diện không còn từ kỹ thuật tiếng Anh đều đạt trước khi chuyển Gate Card sang `DONE`.
- **SC-010**: Fine-tune giữ trạng thái `NOT_APPLICABLE` hoặc có hồ sơ đánh giá riêng được chủ sở hữu phê duyệt; không tự huấn luyện trong feature này.

## 7. Giả định và ranh giới

- Workspace Chat vẫn là giao diện chính; không tạo một sản phẩm họp trực tuyến hoặc hệ quản trị tài liệu mới.
- Phiên bản đầu ưu tiên phỏng vấn văn bản; audio mở sau khi G1 danh tính và G4 consent/retention đạt.
- `workspace_cases.sqlite` giữ workflow metadata/digest; raw audio/transcript dùng vùng cục bộ riêng; `library.sqlite` chỉ nhận artifact đã duyệt.
- Mặc định triển khai đã khóa: danh tính Windows/OS; đồng ý từng phiên; không tự xóa audio/bản chép lời; collection fixture khi kiểm thử và collection đang chọn khi vận hành; fine-tune tắt.
- Goal triển khai kỹ thuật không chờ người thật. Đồng ý ghi âm và duyệt quy trình vẫn là thao tác bắt buộc khi sản phẩm được dùng thật, không phải checkpoint phát triển.
- Gemini Flash 3.8 là vai trò thực thi được yêu cầu; mã model/provider thật phải lấy từ runtime đã cấu hình, không hardcode tên marketing vào code.
- Fine-tune, nhận dạng người nói nâng cao, họp từ xa, lịch mời chuyên gia và tự động ban hành tài liệu là ngoài phạm vi bản đầu.
