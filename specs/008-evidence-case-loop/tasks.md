# Bảng danh mục công việc: Vòng khép kín từ Hồ sơ sự vụ – Thẩm định chuyên gia – Bài học thực tế

**Tài liệu căn cứ**: `spec.md`, `plan.md`, `data-model.md`, `contracts/workspace-evidence-loop.md`.

**Quy tắc thực hiện nghiêm ngặt**:
- Tuyệt đối không làm song song giữa các Cổng kiểm soát. Cổng trước phải được nghiệm thu và chạy kiểm thử xanh 100% thì mới được bắt đầu Cổng sau.
- Toàn bộ mã nguồn phải được phát triển trên nhánh riêng, không commit trực tiếp vào nhánh `main`. Tiêu đề commit viết bằng tiếng Anh ngắn gọn, chuẩn xác.
- Tuyệt đối không commit các thư mục dữ liệu nhạy cảm của nhà máy: `local_cases/`, dữ liệu thô, `tailieugoc`, `Tài liệu của tất cả dòng máy`, tệp cấu hình `.env` chứa mật khẩu.

---

## 🚪 Cổng 0: Xác nhận các điều kiện thực tế từ Chủ sở hữu (Ngoài phạm vi code)

- [ ] **T001**: Chủ sở hữu hệ thống cung cấp bằng chứng nghiệm thu cho Gói 1 (nạp tài liệu thật không nhạy cảm) và Gói 2 (chế độ một người ghi / nhiều người đọc trên ổ đĩa mạng thật); ghi nhận kết quả và rủi ro vào `PROJECT_HANDOVER.md`.
- [ ] **T002**: Chủ sở hữu chốt danh sách chức danh chuyên gia thẩm định (ai duyệt công đoạn nào, ai có quyền phê duyệt bài học kinh nghiệm, ai có quyền phát hành quy trình SOP); lưu tệp cấu hình mẫu không chứa bí mật công nghệ trước khi lập trình Cổng 2.
- [ ] **T003**: Chủ sở hữu cung cấp tệp dữ liệu log máy mẫu của dây chuyền (kèm định dạng cột, múi giờ, danh mục mã lỗi); nếu muốn thử nghiệm dự đoán lỗi LSU thì cung cấp thêm bộ dữ liệu mẫu có nhãn lỗi và người giám sát thử nghiệm bóng. Nếu chưa có thì ghi nhận trạng thái `BLOCKED`, tuyệt đối không tự bịa dữ liệu giả để qua cổng.

*👉 Điểm kiểm tra an toàn*: Thiếu T001 thì không tuyên bố hệ thống đa máy sẵn sàng; thiếu T002 thì dừng ở cổng chuyên gia; thiếu T003 thì tạm dừng Cổng 4 và Cổng 5 nhưng vẫn cho phép làm Cổng 1.

---

## 🚪 Cổng 1: Xây dựng tính năng Lưu trữ Hồ sơ sự vụ cục bộ thật (US1)

**Mục tiêu**: Thay thế nút bấm mô phỏng "Lưu vào hồ sơ" trước đây bằng chức năng lưu trữ cơ sở dữ liệu thật trên máy tính, không để lộ dữ liệu nhạy cảm.

- [X] **T004 [US1]**: Viết các bài kiểm thử cơ sở dữ liệu trong `tests/test_workspace_case_store.py`: Kiểm tra lưu hồ sơ kèm tham chiếu bằng chứng trọn vẹn trong một lần ghi, tự động hủy bỏ nếu có lỗi ghi đĩa, tắt mở lại ứng dụng vẫn đọc đúng dữ liệu, ghi nhật ký kiểm toán nối tiếp.
- [X] **T005 [US1]**: Viết bài kiểm thử dịch vụ và giao diện trong `tests/test_workspace_case_service.py`: Tự động từ chối nếu bằng chứng thiếu nguồn trích dẫn, không lưu thông tin mật cá nhân/CSV thô, nút bấm trên màn hình chỉ tạo đúng 1 hồ sơ duy nhất.
- [X] **T006 [US1]**: Xây dựng cấu trúc dữ liệu `src/aios_habit/workspace_case_models.py` theo đúng bảng `CaseRecord` và `EvidenceReference`.
- [X] **T007 [US1]**: Xây dựng tầng lưu trữ cơ sở dữ liệu `src/aios_habit/workspace_case_repository.py` sử dụng SQLite cục bộ, đảm bảo tính toàn vẹn và không làm ảnh hưởng đến thư viện tri thức chung `library.sqlite`.
- [X] **T008 [US1]**: Xây dựng tầng xử lý nghiệp vụ `src/aios_habit/workspace_case_service.py`, chỉ giữ mã phiên, mã câu trả lời, mã trace và tham chiếu bằng chứng đã có; từ chối lưu hồ sơ nếu thiếu nguồn trích dẫn.
- [X] **T009 [US1]**: Cập nhật nút bấm và thông báo trên giao diện `src/aios_habit/workspace_chat_app.py` sang lưu và mở hồ sơ thật bằng tiếng Việt rõ ràng, không hiển thị lỗi mã nguồn phức tạp.
- [X] **T010 [US1]**: Cập nhật lại các bài kiểm thử giao diện trong `tests/test_workspace_chat_ui_copy.py`, không xóa bớt điều kiện kiểm tra để lấy kết quả đạt giả tạo.
- [X] **T011 [US1]**: Chạy kiểm tra biên dịch (`compileall`), chạy toàn bộ test Cổng 1, kiểm tra import ứng dụng và kiểm tra không có xung đột mã nguồn trước khi đóng Cổng 1.

*👉 Điểm kiểm tra an toàn*: Tạo và mở lại hồ sơ sự vụ thành công 100%; thiếu bằng chứng hoặc lỗi đĩa không sinh ra hồ sơ lỗi dở dang; thư viện tri thức chung `library.sqlite` giữ nguyên 100%.

---

## 🚪 Cổng 2: Màn hình Chuyên gia thẩm định & Ký duyệt kết luận (US2)

**Mục tiêu**: Mọi ý kiến do AI hoặc người dùng dự thảo chỉ ở mức ứng viên; chỉ khi chuyên gia có thẩm quyền ký duyệt kèm lý do thì kết luận mới có giá trị.

- [ ] **T012 [US2]**: Viết bài kiểm thử `tests/test_workspace_case_expert_review.py`: Ý kiến dự thảo không tự động biến thành đã xác nhận; nếu thiếu tên chuyên gia, chức danh, lý do hoặc mã bằng chứng bị sai lệch thì hệ thống từ chối ngay lập tức; khi có 2 ý kiến trái chiều thì lưu giữ cả hai; tắt mở lại ứng dụng vẫn giữ nguyên nhật ký đánh giá.
- [ ] **T013 [US2]**: Mở rộng cấu trúc dữ liệu `src/aios_habit/workspace_case_models.py` với bảng `ExpertReview` và bảng quy tắc chuyển trạng thái tự động khóa an toàn (fail-closed).
- [ ] **T014 [US2]**: Mở rộng tầng lưu trữ và dịch vụ (`workspace_case_repository.py`, `workspace_case_service.py`) để lưu nhật ký đánh giá nối tiếp (append-only) và kiểm tra lại mã băm của tài liệu trích dẫn trong cùng một lần ghi.
- [ ] **T015 [US2]**: Bổ sung giao diện tiếng Việt cho màn hình thẩm định trong `src/aios_habit/workspace_chat_app.py`, chỉ tiếp nhận danh sách chức danh chuyên gia do Cổng 0 cung cấp; tuyệt đối không để AI tự động bấm duyệt thay con người.
- [ ] **T016 [US2]**: Chạy kiểm tra biên dịch, chạy bộ test Cổng 1 + Cổng 2, kiểm tra import ứng dụng và kiểm tra không có xung đột mã nguồn trước khi đóng Cổng 2.

*👉 Điểm kiểm tra an toàn*: Ý kiến chuyên gia truy vết được về đúng hồ sơ sự vụ và tài liệu trích dẫn; người không có thẩm quyền không thể mở khóa bài học hay đề xuất hành động.

---

## 🚪 Cổng 3: Cơ chế Đúc kết Bài học kinh nghiệm vào Sổ tay (US3)

**Mục tiêu**: Chuyển các thẩm định đã được chuyên gia xác nhận thành bài học kinh nghiệm chính thức, có nguồn gốc rõ ràng, không tự ý huấn luyện lại mô hình AI.

- [ ] **T017 [US3]**: Viết bài kiểm thử `tests/test_workspace_case_learning.py`: Ý kiến chưa duyệt hoặc bị từ chối thì không thể nâng cấp thành bài học; bài học đã duyệt đọc lại đầy đủ thông tin nguồn gốc; thư viện tri thức `library.sqlite` hoàn toàn không bị xáo trộn.
- [ ] **T018 [US3]**: Xây dựng cầu nối tương thích với các định dạng thẻ học cũ nếu có, chỉ đọc dữ liệu cũ khi có yêu cầu rõ ràng, không tự tiện gộp dữ liệu bừa bãi.
- [ ] **T019 [US3]**: Mở rộng cấu trúc dữ liệu và dịch vụ cho bảng `LearningRecord` và thao tác phê duyệt bài học; tuyệt đối không gọi các lệnh huấn luyện mô hình hay thay đổi tài liệu gốc.
- [ ] **T020 [US3]**: Bổ sung giao diện tiếng Việt trong `workspace_chat_app.py` để Quản lý chất lượng xem xét nguồn gốc và bấm nút duyệt đưa vào sổ tay bài học (bắt buộc nhập lý do).
- [ ] **T021 [US3]**: Chạy kiểm tra biên dịch, chạy bộ test Cổng 1 $\rightarrow$ Cổng 3, kiểm tra các bài test nạp tài liệu Gate B, kiểm tra import ứng dụng và kiểm tra không có xung đột mã nguồn trước khi đóng Cổng 3.

*👉 Điểm kiểm tra an toàn*: Mỗi bài học đều truy vết được về đúng nhận định của chuyên gia, đúng hồ sơ sự vụ và đúng tài liệu tiêu chuẩn ban đầu.

---

## 🚪 Cổng 4: Ghép nối Dữ liệu Log máy vào Hồ sơ điều tra (US4)

**Điều kiện tiên quyết**: Đã có tệp dữ liệu log mẫu và quy chuẩn cột do Cổng 0 cung cấp. Nếu chưa có, ghi nhận trạng thái `BLOCKED` và không lập trình phỏng đoán.

- [ ] **T022 [US4]**: Viết bài kiểm thử `tests/test_workspace_case_line_pilot.py`: Chỉ đính kèm các sự kiện log từ `line_events.sqlite` mang nhãn "Nghi vấn (`suspected`)"; nếu không tìm thấy sự kiện khớp thì không được tự tiện lấy bừa 5 sự kiện gần nhất; không xuất hiện bất kỳ câu chữ khẳng định chẩn đoán nào; tệp CSV không bị nạp vào thư viện tri thức đọc hiểu.
- [ ] **T023 [US4]**: Bổ sung mã băm kiểm chứng nguồn và phiên bản thu thập trong `src/aios_habit/line_log_parser.py`, giữ nguyên khả năng phân tích các định dạng log Jam/C-call/LSU hiện có.
- [ ] **T024 [US4]**: Mở rộng dịch vụ và giao diện để cho phép đính kèm sự kiện log vào hồ sơ và yêu cầu chuyên gia kiểm tra tính liên quan; toàn bộ câu chữ trên màn hình dùng từ "Nghi vấn / Cần đối chứng".
- [ ] **T025 [US4]**: Viết và chạy các bài kiểm tra bảo mật dữ liệu (`test_workspace_chat_connector_guard.py`, `test_line_log_parser.py`), đảm bảo dữ liệu log nội bộ không bị gửi ra ngoài qua các kết nối Gemini/Router.
- [ ] **T026 [US4]**: Chạy kiểm tra biên dịch, chạy bộ test Cổng 1 $\rightarrow$ Cổng 4, kiểm tra các bài test bảo mật Gate B/C, kiểm tra import ứng dụng trước khi đóng Cổng 4.

*👉 Điểm kiểm tra an toàn*: Sự kiện log chỉ đóng vai trò là dữ liệu nghi vấn phục vụ điều tra, không tự ý vẽ sơ đồ phán đoán hay kết luận hỏng cảm biến.

---

## 🚪 Cổng 5: Kiểm tra độ sẵn sàng cho Dự đoán lỗi LSU (US5)

**Điều kiện tiên quyết**: Đã có bộ dữ liệu mẫu, quy chuẩn nhãn lỗi và người chịu trách nhiệm do Cổng 0 cung cấp. Nếu thiếu, hệ thống chỉ kiểm tra trạng thái `blocked` và không lập trình mô hình dự đoán.

- [ ] **T027 [US5]**: Viết bài kiểm thử `tests/test_lsu_readiness.py`: Thiếu bất kỳ điều kiện nào đều trả về `blocked` kèm danh sách mục còn thiếu; đủ điều kiện chỉ trả về `ready_for_shadow` (chạy thử nghiệm ngầm); tuyệt đối không có kết quả đưa vào sản xuất thật hay lệnh can thiệp máy móc.
- [ ] **T028 [US5]**: Mở rộng cấu trúc dữ liệu và dịch vụ với bảng `LsuReadinessManifest` và logic kiểm tra 6 tiêu chí an toàn.
- [ ] **T029 [US5]**: Bổ sung màn hình tiếng Việt hiển thị bảng kiểm tra độ sẵn sàng và danh sách các mục còn thiếu cho người quản lý xem; không thêm bất kỳ nút bấm kích hoạt mô hình dự đoán production nào.
- [ ] **T030 [US5]**: Chạy kiểm tra biên dịch, chạy bộ test Cổng 1 $\rightarrow$ Cổng 5, kiểm tra các bài test Gate B/C trước khi đóng Cổng 5.

*👉 Điểm kiểm tra an toàn*: Khi thiếu dữ liệu thì báo cáo trung thực là `BLOCKED`; trạng thái "Sẵn sàng chạy thử nghiệm bóng (`ready_for_shadow`)" không đồng nghĩa với việc đã hoàn thành mô hình hay đưa vào sản xuất.

---

## 🚪 Cổng 6: Trợ lý AI Soạn nháp Quy trình & Báo cáo (Con người bấm duyệt) (US6)

**Mục tiêu**: Trợ lý AI hỗ trợ soạn thảo nhanh văn bản từ bằng chứng đã được chuyên gia duyệt, quyền lưu tệp chính thức hoàn toàn do con người bấm duyệt trên màn hình.

- [ ] **T031 [US6]**: Viết bài kiểm thử `tests/test_workspace_action_proposal.py` và bổ sung `tests/test_agent_draft_sop.py`: Hồ sơ chưa có bằng chứng hoặc chưa được chuyên gia xác nhận thì từ chối tạo nháp; nút duyệt trên màn hình gắn chặt với mã hồ sơ và chức danh người duyệt; tắt mở lại ứng dụng vẫn đọc đúng dữ liệu; cấm hoàn toàn các lệnh chạy mã độc hại, cấm sửa PLC, cấm xóa hoặc ghi đè tệp nhà máy.
- [ ] **T032 [US6]**: Mở rộng cấu trúc dữ liệu và dịch vụ với bảng `ActionProposal`, ghi nhật ký nối tiếp.
- [ ] **T033 [US6]**: Khóa chặt API trong `src/aios_habit/agent_draft_sop.py` theo nguyên tắc tự động khóa an toàn (fail-closed): Chỉ cho phép xuất tệp mới vào thư mục được chỉ định khi người dùng bấm duyệt, giữ nguyên luồng xem dự thảo tiếng Việt.
- [ ] **T034 [US6]**: Hoàn thiện giao diện tiếng Việt để kỹ sư đọc bản dự thảo và bấm nút "Duyệt bản nháp" trên màn hình `workspace_chat_app.py`; tuyệt đối không mở các công cụ can thiệp dòng lệnh hay sửa mã nguồn trực tiếp.
- [ ] **T035 [US6]**: Chạy kiểm tra biên dịch, chạy toàn bộ test Cổng 1 $\rightarrow$ Cổng 6, chạy các bài test chính sách an toàn của Agent IDE, kiểm tra import ứng dụng và kiểm tra không có xung đột mã nguồn trước khi đóng Cổng 6.

*👉 Điểm kiểm tra an toàn*: AI chỉ dừng lại ở vai trò soạn thảo văn bản nháp; mọi hành động áp dụng vào thực tế đều do con người thực hiện sau khi đã đọc và ký duyệt văn bản.

---

## 🏁 Bàn giao và Cập nhật tài liệu chính thức

- [ ] **T036**: Cập nhật tài liệu kiến trúc `ARCHITECTURE.md` và tài liệu bàn giao `PROJECT_HANDOVER.md`, nêu rõ những hạng mục đã hoàn tất và những hạng mục còn đang chờ dữ liệu thực tế từ nhà máy; cập nhật mục "Việc đang làm" trong `Thảo_luận_AI_dự_đoán_lỗi_LSU.md`.
- [ ] **T037**: Chạy toàn bộ các lệnh nghiệm thu theo đúng phạm vi, ghi lại kết quả thực tế từ terminal, kiểm tra `git status` và `git diff --check` sạch hoàn toàn.
- [ ] **T038**: Chuyên gia kiểm toán độc lập kiểm tra lại từng commit của Cổng 1 $\rightarrow$ Cổng 6; chỉ lập trình viên sửa các điểm phát hiện có bằng chứng thực tế; chỉ đẩy mã nguồn lên kho chung khi kiểm toán đạt PASS và Chủ sở hữu đồng ý với các hạng mục còn ở trạng thái `BLOCKED`.
