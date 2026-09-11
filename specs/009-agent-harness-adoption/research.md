# Nghiên cứu và quyết định

## 1. Giữ cầu nối AI, chỉ thay cầu nối Agent lập trình cũ

**Quyết định**: giữ `antigravity_bridge.py` cùng các tuyến `gemini_web`, `cagent_api` và `nakazasen_router`. Goal 009 chỉ thay `workspace_agent_bridge_client.py`, tức cầu nối NVIDIA thử nghiệm cho thao tác lập trình.

**Lý do**: Workspace Chat đang import và gọi trực tiếp cầu nối Antigravity. Xóa nó sẽ làm mất nguồn AI hiện hành và phá nhiều kiểm thử. Cầu nối NVIDIA là tuyến khác, truyền việc sang tool lập trình cũ và chưa có worktree, resume hay hàng đợi bền vững.

**Phương án đã loại**: gom hai cầu nối thành một. Cách này trộn nhiệm vụ “AI trả lời” với “Agent tác động file”, làm policy và quyền riêng tư khó hiểu hơn.

## 2. Probe OpenCode phải đọc và sửa, không phải chỉ đọc

**Quyết định**: G1 dùng fixture vô hại để chứng minh health/version, session/event, read/search, create/edit, chạy test, resume và undo. Các thao tác trong task root được tự động cho phép; negative test chứng minh thao tác ngoài root và lệnh cấm bị từ chối.

**Lý do**: mục tiêu của sản phẩm là hoàn thành công việc. Probe chỉ đọc không kiểm chứng được năng lực quan trọng nhất và đẩy rủi ro sang giai đoạn sau. OpenCode đã có server cục bộ, session, file API, event và permission; AIOS cần kiểm chứng đúng bản được pin thay vì tự viết lại vòng agent.

**Phương án đã loại**:

- Fork OpenCode ngay: tăng chi phí bảo trì trước khi biết adapter có thiếu gì.
- Tích hợp OpenCode và Cline đồng thời: nhân đôi test và adapter.
- Dùng bridge NVIDIA làm runtime chính: tiếp tục phụ thuộc đường cũ chưa đủ contract.

Nguồn tham khảo: [OpenCode server](https://opencode.ai/docs/server/), [OpenCode permissions](https://opencode.ai/docs/permissions/), [OpenCode license](https://github.com/anomalyco/opencode/blob/dev/LICENSE).

## 3. Tự động duyệt trong vùng an toàn

**Quyết định**: bản thử nghiệm không hỏi người dùng sau mỗi tool call. Policy dùng ba nhóm:

- tự động cho phép read/search/create/edit và test trong vùng nhiệm vụ;
- luôn từ chối secret, ngoài root, quyền admin, commit/push/merge/deploy và gửi dữ liệu sai tuyến;
- chưa hỗ trợ xóa/đổi tên hàng loạt hoặc thay tài liệu công đoạn chính thức.

**Lý do**: `ask` liên tục làm mất giá trị tự động hóa và gây khó cho người không chuyên. An toàn đến từ giới hạn vùng, checkpoint, kiểm tra kết quả và hoàn tác, không đến từ việc bắt người dùng xác nhận mọi lệnh.

## 4. Người dùng duyệt kết quả, không duyệt toàn bộ diff

**Quyết định**: màn hình mặc định là thẻ kết quả tiếng Việt gồm mục tiêu, đầu ra, căn cứ, kiểm tra, rủi ro và bước tiếp theo. `diff`, terminal, digest và receipt nằm trong phần chi tiết đóng mặc định.

**Lý do**: người dùng không chuyên không thể đánh giá độ đúng chỉ bằng raw diff. AIOS phải chạy kiểm tra thật và dịch kết quả thành tác động công việc. Với báo cáo/bản nháp, lưu tự động và cho hoàn tác. Với mã nguồn, người dùng chọn “Dùng kết quả” hoặc “Hoàn tác” ở cấp kết quả toàn nhiệm vụ.

**Phương án đã loại**: partial-hunk approval ở MVP. Nó làm tăng mô hình dữ liệu, verifier và tải nhận thức nhưng không giúp người dùng mục tiêu ra quyết định tốt hơn.

## 5. Báo cáo có biểu đồ phải dựa trên số liệu thật

**Quyết định**: dùng lại `document_extractors.py`, metadata chart Excel, Mermaid và visual map hiện có. Mỗi bảng/biểu đồ giữ nguồn, cột, đơn vị, bộ lọc và phép tổng hợp. Thiếu dữ liệu thì dùng bảng hoặc mô tả, không sinh biểu đồ trang trí.

**Lý do**: repo đã đọc được cấu trúc Excel, chart metadata và xuất sơ đồ Mermaid. Tạo thêm framework trực quan hóa ở vòng đầu là không cần thiết. Provenance ngăn biểu đồ đẹp nhưng sai.

## 6. Rà soát thiết kế công đoạn là phân tích có căn cứ, không phải tự phê duyệt

**Quyết định**: dùng evidence pack từ đúng tài liệu người dùng chọn. Đầu ra tách rõ hiện trạng, phát hiện có nguồn, ảnh hưởng, đề xuất và câu hỏi cần xác nhận. Có thể tạo sơ đồ hiện tại/đề xuất nhưng chỉ lưu bản nháp.

**Lý do**: tài liệu công đoạn có thể mâu thuẫn theo phiên bản hoặc phạm vi. AIOS hữu ích khi chỉ ra chỗ sai/thiếu và lý do, nhưng không được tự thay giới hạn sản xuất, SOP hoặc trách nhiệm phê duyệt.

## 7. Worktree cho mã, checkpoint cho artifact

**Quyết định**: task mã nguồn chạy trong Git worktree. Báo cáo và thiết kế công đoạn ghi vào vùng bản nháp cục bộ có snapshot trước/sau. Cả hai trả cùng một kết quả “mở, dùng, hoàn tác”.

**Lý do**: ép mọi tài liệu vào Git worktree sẽ loại các thư viện tài liệu không phải repo. Ngược lại, cho Agent sửa trực tiếp mã nguồn có thể làm mất thay đổi chưa commit. Hai cơ chế thực thi khác nhau nhưng dùng chung trạng thái và UX.

## 8. Hàng đợi nhỏ thay vì nền tảng đa Agent

**Quyết định**: lưu mục hàng đợi bằng record `agent_work` hiện có, khóa một writer theo workspace và cho phép thêm việc trong lúc việc khác chạy. Không xây scheduler phân tán, worker farm hoặc swarm.

**Lý do**: nhu cầu là giao nhiều việc và quay lại xem kết quả. Một hàng đợi bền vững, trạng thái rõ và resume đủ đáp ứng vòng đầu. Kiến trúc lớn hơn chỉ được xét khi có số liệu chứng minh giới hạn.

## 9. Giữ verifier theo loại đầu ra

**Quyết định**:

- mã nguồn: quan sát exit code, Git status, file digest và lệnh test;
- báo cáo: kiểm tra section bắt buộc, citation, bảng/biểu đồ và provenance số liệu;
- thiết kế công đoạn: kiểm tra mọi phát hiện có nguồn hoặc nhãn suy luận/đề xuất, đồng thời chặn promotion thành tài liệu chính thức.

**Lý do**: một verifier chung kiểu “PASS/FAIL” không đủ cho ba loại đầu ra. Tuy nhiên chỉ cần ba bộ quy tắc nhỏ, không cần framework rule engine mới.

## 10. Code-OSS và Cline chưa phải MVP

**Quyết định**: Workspace Chat là giao diện vòng đầu. Người dùng kỹ thuật vẫn có thể mở file/worktree bằng editor hiện có, nhưng không xây extension Code-OSS riêng. Cline chỉ được probe nếu OpenCode không đạt G1.

**Lý do**: extension, marketplace và protocol đa client không trực tiếp chứng minh giá trị tạo báo cáo, phân tích công đoạn hoặc sửa lỗi. Hoãn chúng làm giảm đáng kể số task và bề mặt bảo trì.

## 11. Điểm còn phải khóa bằng bằng chứng thực thi

Các mục sau chưa được tuyên bố đạt chỉ bằng kế hoạch:

- phiên bản và checksum OpenCode được pin;
- auto-approval có thực sự tôn trọng deny trên Windows;
- resume/undo sau khi tiến trình hoặc Workspace Chat restart;
- biểu đồ giữ đúng provenance với dữ liệu Excel/log thực tế;
- hàng đợi không chạy hai writer trên cùng workspace;
- clean-machine và toàn bộ quality gate của repo.
