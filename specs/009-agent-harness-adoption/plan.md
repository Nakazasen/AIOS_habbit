# Kế hoạch triển khai: Trợ lý thực thi công việc cho kỹ sư

## 1. Tóm tắt

Goal 009 làm Workspace Chat thành trợ lý việc hằng ngày: nói tiếng Việt, nhận file/kết quả, muốn mở lại. Cảm giác Grokbot; dữ liệu ở máy mình.

```text
Chọn nguồn → nói việc → tự làm → «Đã xong» + mở file + hoàn tác
```

Ba việc: báo cáo lỗi dùng được; rà soát Guideline vs thiết kế; sửa mã có test. Hàng đợi nhỏ. Một workspace một việc ghi file tại một thời điểm.

**Cấm over-engineer.** Dùng Chat, extractors, visual, metadata việc hiện có. Một adapter runtime. Không IDE, terminal, DB phiên, scheduler, đa Agent, màn quyền. Hai cách cùng đạt: ít code hơn.

## 2. Bối cảnh kỹ thuật

- **Giao diện chính**: Workspace Chat hiện có.
- **Nguồn AI hiện hành**: giữ `src/aios_habit/antigravity_bridge.py`, gồm tuyến `gemini_web`; không trộn với runtime Agent lập trình.
- **Runtime Agent thử trước**: OpenCode cục bộ, khóa đúng phiên bản đã probe; Cline chỉ là phương án dự phòng.
- **Thực thi**: Git worktree theo nhiệm vụ đối với mã nguồn; thư mục bản nháp cục bộ có checkpoint đối với báo cáo và tài liệu.
- **Tri thức nền**: dùng luồng chọn thư viện, trích xuất tài liệu, RAG/evidence pack và hồ sơ vụ việc hiện có.
- **Trực quan hóa**: dùng lại bộ tạo Mermaid, bản đồ bằng chứng và metadata biểu đồ Excel hiện có; không thêm framework biểu đồ mới ở vòng đầu.
- **Lưu trạng thái**: mở rộng metadata `agent_work`/kho Case hiện có. Runtime tự giữ phiên kỹ thuật; không tạo kho transcript hay database session mới.
- **Ngôn ngữ**: toàn bộ bề mặt người dùng là tiếng Việt dễ hiểu; lỗi runtime được đổi thành lời giải thích và bước xử lý.

## 3. Khoảng trống hiện tại

| Năng lực | Nền có thể dùng lại | Khoảng trống cần làm |
| --- | --- | --- |
| Nguồn AI Workspace Chat | `antigravity_bridge.py`, `ai_provider_bridge.py` | Cần ghi rõ không bị thay bởi runtime Agent |
| Đọc tài liệu và dẫn nguồn | RAG v2, evidence pack, document extractors | Chưa có hợp đồng đầu ra cho phát hiện thiết kế công đoạn |
| Báo cáo và sơ đồ | report import, Mermaid, visual map, Excel chart metadata | Chưa có vòng tạo bản nháp báo cáo có biểu đồ và kiểm tra số liệu |
| Agent lập trình | Task Pack, policy, orchestrator, NVIDIA bridge thử nghiệm | Chưa có OpenCode adapter đọc–sửa–test trong worktree |
| Trải nghiệm không chuyên | Workspace Chat, hồ sơ vụ việc | UI cũ thiên về quyền, `diff`, terminal và checkbox kỹ thuật |
| Đa nhiệm | metadata hồ sơ hiện có | Chưa có hàng đợi bền vững tối thiểu theo workspace |

## 4. Kiểm tra Hiến chương trước thiết kế

| Cổng | Kết quả |
| --- | --- |
| Bằng chứng trước tuyên bố | Đạt về thiết kế: kết luận và biểu đồ phải có nguồn; test phải do hệ thống quan sát |
| Ưu tiên cục bộ | Đạt: tài liệu và đầu ra thô ở cục bộ; provider route vẫn phải tuân chính sách dữ liệu |
| Khả năng thay thế | Đạt: OpenCode là runtime thử trước, không trở thành nguồn tri thức độc quyền |
| Tiếng Việt duy nhất | Đạt: người dùng chỉ thấy câu tiếng Việt đời thường; chi tiết kỹ thuật được thu gọn |
| Chống thiết kế quá mức | Đạt: dùng lại module hiện có, một adapter, một hàng đợi nhỏ, không extension riêng ở MVP |
| Ranh giới legacy | Đạt: chỉ thay cầu nối lập trình NVIDIA cũ; giữ cầu nối Antigravity đang phục vụ Workspace Chat |

## 5. Kiến trúc được chọn

```text
Workspace Chat
  ├─ giao việc + chọn nguồn + xem hàng đợi
  └─ thẻ kết quả: đã làm / căn cứ / kiểm tra / dùng / hoàn tác
                 ↓
Workspace Agent Orchestrator hiện có
  ├─ phân loại: báo cáo | rà soát công đoạn | sửa mã
  ├─ khóa một writer theo workspace
  ├─ checkpoint + trạng thái tiếp tục
  └─ receipt đã làm sạch
          ↓                         ↓
OpenCode adapter              Dịch vụ AIOS hiện có
đọc/sửa/chạy test             RAG + evidence + visual map
          └──────────┬──────────────┘
                     ↓
Worktree hoặc thư mục bản nháp cục bộ
                     ↓
Verifier theo loại đầu ra
```

### 5.1 Ranh giới hai cầu nối

- `antigravity_bridge.py` là tuyến nguồn AI cho Workspace Chat và phải được giữ nguyên hành vi.
- `workspace_agent_bridge_client.py` là cầu nối lập trình NVIDIA cũ. Nó chỉ được ngừng sau khi OpenCode vượt probe đọc–sửa–test–tiếp tục–hoàn tác và đường mới có kiểm thử thay thế.
- Không cho hai cầu nối gọi chéo hoặc cùng sở hữu policy. AIOS giữ quyết định dữ liệu và phạm vi; runtime chỉ thao tác trong vùng đã cấp.

### 5.2 Quyền tự động trong vòng thử nghiệm

Không dùng `deny` cho mọi thứ. Dùng quyền theo vùng:

- **Tự động cho phép**: đọc/tìm trong nguồn đã chọn; tạo/cập nhật file bản nháp; sửa mã trong worktree; chạy lệnh test đã khai báo; đọc trạng thái Git.
- **Luôn từ chối**: thoát workspace, đọc `.env`/secret/vùng cấm, quyền quản trị, sửa hệ thống, gửi dữ liệu sai tuyến, commit, push, merge và deploy.
- **Tạm chưa hỗ trợ**: xóa/đổi tên hàng loạt, thay tài liệu công đoạn chính thức, thay thông số vận hành thật.

Người dùng không phê duyệt từng tool call và không duyệt từng finding. Báo cáo lỗi là file dùng được, tự lưu và hiện «Đã xong». Với mã nguồn, xong trong worktree khi test quan sát được đạt; «Hoàn tác» luôn có; «Đưa vào thư mục đang làm» tùy chọn khi không xung đột. `diff` đóng mặc định.

### 5.3 Ba loại đầu ra

#### Báo cáo lỗi kỹ thuật

- File kết quả dùng được, không phải bản nháp chờ ban hành. Mẫu tối thiểu: hiện tượng, phạm vi ảnh hưởng, bằng chứng, phân tích, giả thuyết, hành động tiếp theo.
- Tạo bảng và biểu đồ khi dữ liệu có trục, đơn vị, phạm vi và nguồn rõ.
- Mỗi biểu đồ lưu nguồn dữ liệu, phép lọc/tổng hợp và cảnh báo thiếu dữ liệu.
- Nếu không đủ số liệu, xuất bảng hoặc mô tả thay vì vẽ biểu đồ trang trí.

#### Rà soát thiết kế công đoạn

- Gán nguồn: Guideline/tiêu chuẩn = luật; bản thiết kế/SOP nháp = đối tượng; MOM/log/bản vẽ = ngữ cảnh. Chi tiết [agent-process-design-review-v1.md](contracts/agent-process-design-review-v1.md).
- Mỗi điều luật: `pass` / `violate` / `insufficient` kèm locator.
- Năm phần: hiện trạng; phát hiện; ảnh hưởng; đề xuất; câu hỏi cần xác nhận.
- Sơ đồ Mermaid hiện tại/đề xuất nếu hữu ích.
- Bản nháp tự xong; không sửa SOP/JIG/tiêu chuẩn chính thức; không chờ người tick.

#### Sửa mã nguồn

- OpenCode đọc và sửa trong worktree; test chạy tự động.
- AIOS tự đọc filesystem/Git và exit code. Test đạt = việc xong trong worktree, không chờ bấm duyệt.
- Một checkpoint cho cả nhiệm vụ; hoàn tác một nhịp.
- Workspace chính xung đột: giữ worktree, giải thích, không ghi đè.

### 5.4 Hàng đợi tối thiểu

- Dùng record `agent_work` hiện có để lưu mục tiêu, loại việc, workspace, trạng thái, output locator và checkpoint.
- Một writer lock theo workspace; không xây scheduler tổng quát.
- Người dùng có thể thêm việc mới khi việc khác đang chạy.
- Sau restart, việc đang chạy được đối chiếu trạng thái runtime và filesystem; không tự lặp thao tác ghi chưa rõ kết quả.

### 5.5 Trải nghiệm người dùng: Triết lý Grokbot (Conversational Omnibar & Interactive Artifact Card)

Loại bỏ hoàn toàn các nút bấm chức năng cố định (`_render_local_work_tools`) và bảng quản trị hàng đợi thô kệch ở chân trang. Giao diện trở về sự tinh giản và hấp dẫn tối đa theo triết lý Grokbot:

1. **Một đầu nhập duy nhất (Single Conversational Omnibar)**:
   - Khung chat trung tâm tiếp nhận mọi loại yêu cầu: tra cứu tri thức, tạo báo cáo lỗi (US1), rà soát thiết kế công đoạn (US2), hoặc yêu cầu sửa mã nguồn (US3).
   - Hệ thống tự động nhận diện ý định (Intent Routing) dựa trên từ khóa hành động và tệp đã chọn.
   - Khi thiếu tệp nguồn cần thiết, Trợ lý phản hồi đối thoại tự nhiên (ví dụ: *"Tôi đã sẵn sàng lập báo cáo lỗi. Bạn vui lòng tích chọn ít nhất một tệp log/Excel trong danh sách tài liệu bên trên nhé!"*), tuyệt đối không đẻ form hay làm tê liệt nút bấm.

2. **Thẻ tác vụ thông minh trong dòng chat (Inline Interactive Artifact Card)**:
   - Kết quả công việc hiển thị như một thẻ tương tác trực quan (Interactive Card) ngay tại bong bóng tin nhắn của Trợ lý.
   - Thẻ bao gồm: Tiêu đề tác vụ kèm biểu tượng, huy hiệu trạng thái `✅ Đã xong`, bản tóm tắt phát hiện chính, bảng dữ liệu / biểu đồ Mermaid trực quan khớp 100% tài liệu gốc.
   - Tích hợp cụm hành động nhanh ngay trên thẻ: `[👁️ Xem toàn văn]` `[📥 Tải .md]` `[↩️ Hoàn tác]`.

3. **Hàng đợi công việc vô hình (Invisible Queue)**:
   - Khi người dùng giao việc mới trong lúc việc cũ đang chạy, hệ thống tự động ghi nhận vào hàng đợi bền vững `agent_work` và phản hồi tin nhắn tự nhiên: *"⏳ Tác vụ của bạn đã được xếp hàng (vị trí X) và sẽ tự động chạy ngay sau khi việc hiện tại hoàn tất."*
   - Toàn bộ chi tiết kỹ thuật (`diff`, terminal, worktree, ID nội bộ) được ẩn hoàn toàn vào phần "Chi tiết kỹ thuật" đóng mặc định.

## 6. Cổng triển khai rút gọn

| Cổng | Phạm vi | Điều kiện ra |
| --- | --- | --- |
| G0 | Đồng bộ đặc tả, kế hoạch, task và tài liệu canonical | Phạm vi mới được ghi nhất quán; không còn read-only MVP hoặc bắt duyệt toàn bộ diff |
| G1 | Probe OpenCode đã pin trên fixture Windows | Đạt đọc–sửa–test thì ghi nhận. Thiếu undo/deny = `PARTIAL`, hoãn US3, **không BLOCK Goal**. US1/US2 vẫn làm |
| G2 | Lát cắt báo cáo lỗi có biểu đồ | Tạo file báo cáo dùng được, kiểm tra nguồn số liệu, mở được và hoàn tác được |
| G3 | Lát cắt rà soát thiết kế công đoạn | Phát hiện mâu thuẫn/thiếu/sai có nguồn, tạo sơ đồ và không sửa tài liệu chính thức |
| G4 | Lát cắt sửa mã | Sửa bug fixture, test thật, dùng kết quả/hoàn tác, không mất thay đổi có trước |
| G5 | Hàng đợi và UX tiếng Việt | Ba việc giữ đúng trạng thái qua restart; chi tiết kỹ thuật đóng mặc định |
| G6 | Kiểm tra an toàn và quality gate | Privacy, secret, path, Unicode, xung đột và lệnh quality gate repo đạt. `TECHNICAL_PASS` khi lệnh xanh; không chờ người ngồi duyệt hay kiểm toán độc lập để tiếp tục. `DONE` vận hành là việc sau, không chặn Gemini |

Mỗi cổng là một lát cắt dùng được. Không làm G5 thành hệ điều phối tổng quát và không xây extension Code-OSS trước khi G2–G4 chứng minh giá trị.

## 7. Cấu trúc dự kiến tối thiểu

```text
src/aios_habit/
├── workspace_agent_orchestrator.py  # mở rộng vòng đời và hàng đợi nhỏ
├── workspace_agent_policy.py        # quyền theo vùng và loại nhiệm vụ
├── opencode_runtime_adapter.py      # tạo sau khi G1 đạt
├── agent_work_artifact.py           # bản nháp, nguồn, biểu đồ và kết quả dễ hiểu
└── workspace_chat_app.py            # thẻ giao việc, hàng đợi và kết quả

scripts/probe_opencode_runtime.py
tests/fixtures/agent_harness/
tests/test_agent_runtime_capabilities.py
tests/test_agent_error_report_artifact.py
tests/test_agent_process_design_review.py
tests/test_agent_code_worktree.py
tests/test_agent_work_queue_ui.py
```

Không tạo package harness mới, extension Code-OSS mới hoặc database mới ở vòng đầu. `agent_work_artifact.py` là một module mỏng dùng lại trình đọc tài liệu và bộ trực quan hóa hiện có, không phải framework artifact mới.

## 8. Tương thích và di chuyển

- Giữ reader của Task Pack và report schema cũ; không đổi nghĩa artifact lịch sử.
- Giữ `antigravity_bridge.py` và các test phụ thuộc.
- Cầu nối NVIDIA chỉ bị deprecate sau khi test mới chứng minh OpenCode thay được đúng đường Agent lập trình.
- Khối Agent hiện ẩn chỉ mở theo lát cắt đã vượt gate; không khôi phục checkbox tự khai PASS.
- Không tự đổi tài liệu công đoạn thật hoặc dữ liệu `local_only` trong quá trình migration.

## 9. Rủi ro và biện pháp

| Rủi ro | Biện pháp |
| --- | --- |
| OpenCode tự động duyệt quá rộng | Allow theo task root và lệnh test; deny rõ secret, ngoài root và hành động phát hành |
| Biểu đồ gây hiểu nhầm | Bắt buộc provenance số liệu và phép tổng hợp; thiếu dữ liệu thì không vẽ |
| AI phán thiết kế công đoạn như sự thật | Tách phát hiện có nguồn, suy luận, đề xuất và câu hỏi cần xác nhận |
| Nhiều task ghi đè nhau | Một writer theo workspace, checkpoint riêng, phát hiện xung đột trước khi dùng kết quả |
| UX lại biến thành công cụ cho lập trình viên | Thẻ kết quả đời thường; chi tiết kỹ thuật đóng mặc định; test với người không chuyên |
| Mở rộng thành nền tảng Agent quá sớm | Chỉ ba loại nhiệm vụ, một runtime thử trước, dùng lại storage và visual hiện có |

## 10. Kiểm tra Hiến chương sau thiết kế

Thiết kế giữ dữ liệu cục bộ, không giả PASS, có nguồn cho kết luận và biểu đồ, giữ tiếng Việt trên bề mặt người dùng, có hoàn tác và giảm đáng kể độ phức tạp so với kế hoạch tám cổng cũ. Không có ngoại lệ Hiến chương được yêu cầu.

## 11. Thứ tự thực hiện

1. Khóa fixture và probe OpenCode đọc–sửa–test–hoàn tác.
2. Làm báo cáo lỗi có biểu đồ như lát cắt đầu tiên.
3. Dùng cùng nền nguồn/bản nháp cho rà soát thiết kế công đoạn.
4. Nối vòng sửa mã trong worktree.
5. Thêm hàng đợi nhỏ và thẻ kết quả non-tech.
6. Chạy kiểm tra an toàn, Unicode, restart và quality gate độc lập.

Không triển khai tất cả cùng lúc. Mỗi bước phải tạo ra một hành vi nhìn thấy và kiểm thử độc lập trước khi mở bước tiếp theo.
