# Nhiệm vụ đang thực thi: MVP cảnh báo sớm Iris LSU

**Mã tính năng**: `008-evidence-case-loop`

**Ngày cập nhật**: 05/09/2026

**Phạm vi**: Mốc 0–4 trong [plan.md](plan.md), chỉ BOWSKEW 4 BEAM

## 1. Cách dùng danh sách 29 nhiệm vụ

- Giữ đúng 29 mã từ T001 đến T029. Các gạch đầu dòng dưới mỗi mã là tiêu chí bắt buộc của cùng một nhiệm vụ, không phải nhiệm vụ mới.
- Mỗi mốc có hai kết quả độc lập:
  - `TECHNICAL_PASS`: phần mềm chạy hết bằng bộ dữ liệu mẫu đã làm sạch (`fixture`), có kiểm thử và có cách phục hồi.
  - `OPERATIONAL_PASS`: đã chạy bằng dữ liệu thật được phép và vượt rubric tự động có phiên bản; không đồng nghĩa được phép điều khiển máy.
- `OPERATIONAL_PARTIAL` hoặc `OPERATIONAL_BLOCKED` chỉ khóa việc sử dụng thật của nhánh phụ thuộc. Nó không khóa việc xây giao diện trạng thái, kiểm thử, công cụ báo thiếu dữ liệu hoặc mốc kỹ thuật kế tiếp.
- Fixture không được dùng để tuyên bố pilot thật, độ chính xác thật hoặc hiệu quả vận hành.
- Dữ liệu thật chỉ dùng cục bộ; không ghi vào Git, nhật ký công khai hoặc prompt cloud.
- Gemini/tác tử cloud không được mở file thật trong `Tài liệu của tất cả dòng máy/`, `local_cases/` hoặc `local_runs/` của phiên khác. Chỉ fixture giả hoàn toàn và manifest đã làm sạch được đưa vào ngữ cảnh phát triển.
- Mỗi thay đổi code phải có bài kiểm thử thất bại trước khi sửa, bài kiểm thử đạt sau khi sửa và `git diff --check` sạch.
- Tiếng Việt là ngôn ngữ giao diện duy nhất. Tài liệu nguồn ngoại ngữ được giữ nguyên làm bằng chứng; câu điều khiển, tiến độ, lỗi, nhật ký vận hành và báo cáo do chương trình tạo phải là tiếng Việt dễ hiểu.
- Không thêm scheduler, PLC, AutoML, deep learning, Knowledge Graph prediction, dashboard quản trị hoặc tích hợp ERP/JIG trong đợt này.
- Trạng thái `DONE`, `PARTIAL`, `BLOCKED` hoặc các trạng thái cổng ở trên chỉ được ghi từ bằng chứng vừa chạy.
- Chỉ tác tử điều phối được ghi `PROJECT_HANDOVER.md`, checklist/trạng thái chung và chạy lệnh Git. Tác tử thực thi ghi biên nhận riêng; không cho hai tác tử sửa cùng file đồng thời và không dùng `git add -A`.
- Chỉ chạy một thao tác nặng tại một thời điểm. Gemini thực thi trọn T001–T029 trong một `/goal`; T029 phải do tác tử kiểm toán độc lập với tác tử đã sửa code thực hiện.
- Hướng dẫn điều phối và prompt sao chép nằm tại [ANTIGRAVITY_GOAL.md](ANTIGRAVITY_GOAL.md).

## 2. Mốc 0 — Khóa phần nền

**Đích độc lập**: chuẩn bị nguồn và hồ sơ hiện tại hoạt động; người dùng luôn biết hệ thống đang chờ gì và phải làm gì tiếp theo.

**Thứ tự**: T001 → T002 và T003 → T004 → T005.

- [x] T001 Ghi đường cơ sở có thể lặp lại vào `PROJECT_HANDOVER.md` và không đưa `.brain/` hoặc dữ liệu thật vào Git
  - Ghi nhánh, `HEAD`, upstream, `git status --short`, danh sách file đang sửa và chủ sở hữu của thay đổi.
  - Chỉ bắt đầu viết code khi commit kế hoạch đã sạch; `.brain/`, `local_cases/`, `local_runs/` và dữ liệu thật không được stage. Nếu cây còn thay đổi không thuộc commit kế hoạch, dừng và bàn giao danh sách file thay vì tự gom.
  - Xác nhận mọi lệnh dùng Python 3.11. Nếu `.venv` hiện có bị khóa/sai phiên bản, tạo môi trường `uv` mới dưới thư mục phiên trong `local_runs/`; không xóa hoặc sửa quyền môi trường cũ.
  - Tạo runtime thử nghiệm riêng dưới `local_runs/evidence_case_loop_goal/<run_id>/runtime`; import/smoke phải chạy với thư mục này là thư mục hiện hành để không chạm `local_cases/` thật.
  - Chạy một lượt đường cơ sở: `compileall`, toàn bộ `pytest`, CLI audit, import Workspace Chat, `scripts/check_docs.py`, `git diff --check`; ghi lệnh, mã thoát, số đạt/trượt, phiên bản Python và thời gian.
  - Tách lỗi đã tồn tại trước đợt này khỏi lỗi do thay đổi mới; mỗi lỗi phải có file/test, cách tái hiện và nhiệm vụ sửa dự kiến là T005 hoặc T029.
  - Đạt khi người thực thi khác có thể chạy lại đúng các lệnh và nhận cùng phạm vi kiểm tra; chưa cần mọi bài kiểm thử đạt ở T001.

- [x] T002 [P] [US1] Khóa hợp đồng test cho migration, kho, quyền, service và giao diện case trong `tests/test_workspace_case_migrations.py`, `tests/test_workspace_case_store.py`, `tests/test_workspace_case_authorization.py`, `tests/test_workspace_case_service.py` và `tests/test_workspace_case_ui.py`
  - Bao phủ tạo/mở case, lọc, đổi trạng thái, kết luận, gắn evidence, optimistic version, trace mất và đọc lại sau restart.
  - Thêm fault injection cho lỗi giữa transaction, migration lỗi, backup/restore và `quick_check`; không được để bản ghi nửa vời.
  - Đạt khi test mô tả đúng hành vi hiện có; lỗi nào xuất hiện phải được ghi bằng tên test cụ thể cho T005.

- [x] T003 [P] Chuyển hợp đồng kiểm thử giao diện từ ba ngôn ngữ sang chỉ tiếng Việt trong `tests/test_workspace_chat_ui_i18n.py`, `tests/test_i18n.py`, `tests/test_multilingual_language_switching.py`, `tests/test_workspace_chat_rag_v2_adapter.py` và thêm bộ quét tại `scripts/check_user_facing_vietnamese.py`
  - Tách danh sách locale giao diện mới chỉ có `vi` khỏi danh sách ngôn ngữ nguồn/locale lịch sử. Không thu hẹp hằng đang được trace schema dùng để đọc dữ liệu Nhật/Trung cũ nếu việc đó làm hỏng tương thích.
  - Cấm hiển thị bộ chọn ngôn ngữ; dữ liệu hội thoại cũ có locale khác vẫn đọc an toàn nhưng UI và câu trả lời mới hiển thị tiếng Việt.
  - Giữ nguyên khả năng đọc và trích dẫn nội dung nguồn Nhật/Trung/Anh; chỉ cấm câu do chương trình tạo trên bề mặt người dùng.
  - Bộ quét phải kiểm tra các lời gọi Streamlit, launcher `.bat`/`.ps1`, thông báo CLI/nhật ký vận hành, khóa dịch thiếu và chuỗi lỗi dự phòng; có danh sách cho phép nhỏ dành cho đường dẫn, mã máy, mã lỗi và hằng kỹ thuật.
  - Giả lập lỗi tiếng Anh từ thư viện, hệ điều hành và provider; kết quả mong đợi là câu tiếng Việt có nguyên nhân đơn giản và bước xử lý.
  - Đạt khi các test mới thất bại đúng trên code đa ngôn ngữ hiện tại và không báo sai nội dung nguồn ngoại ngữ.

- [x] T004 [US1] Lập và chạy ma trận smoke trình duyệt Mốc 0 theo `specs/008-evidence-case-loop/quickstart.md`, lưu kết quả đã làm sạch vào `PROJECT_HANDOVER.md`
  - Kiểm sáu trạng thái: bình thường, trống, chờ, thành công, cảnh báo và lỗi cho chuẩn bị nguồn, tìm kiếm và hồ sơ vụ việc.
  - Kiểm phần trăm tiến độ, số đã xong/đang chờ/lỗi, nút tiếp tục/thử lại và trạng thái sau khi tắt/mở ứng dụng.
  - Tạo case từ câu trả lời có citation; lọc, mở, đổi trạng thái, ghi kết luận, mở trace và đọc lại sau restart trong tối đa ba thao tác.
  - Khởi động bằng lệnh/cổng cố định từ thư mục runtime thử nghiệm của T001; chỉ dùng fixture, đóng đúng tiến trình sau smoke và chụp lại chỉ tên màn hình, bước thao tác, kết quả. Không commit ảnh hoặc dữ liệu thật.
  - Đạt khi mọi lỗi quan sát được có bước tái hiện ổn định để T005 sửa; smoke thật thiếu môi trường được ghi `OPERATIONAL_PARTIAL`, không chặn sửa kỹ thuật.

- [x] T005 [US1] Sửa toàn bộ lỗi Mốc 0 đã tái hiện và đóng vòng kiểm chứng trong `src/aios_habit/i18n.py`, `src/aios_habit/workspace_chat_ui.py`, `src/aios_habit/workspace_chat_app.py`, `RUN_AIOS_WORKSPACE_CHAT.bat`, `scripts/run_workspace_chat.ps1` cùng module case/chuẩn bị nguồn liên quan
  - Buộc UI và ngôn ngữ trả lời mặc định là tiếng Việt; bỏ bộ chọn ngôn ngữ khỏi tuyến được hỗ trợ nhưng không phá dữ liệu hội thoại cũ.
  - Chặn traceback, đường dẫn hệ thống, tên engine/model và câu lỗi ngoài; lưu mã lỗi nội bộ nếu cần nhưng chỉ hiện lời giải thích tiếng Việt.
  - Sửa tiến độ bị đứng, khóa Streamlit trùng, tiếp tục/thử lại và lỗi đường cơ sở thuộc repo; không tắt test hoặc hạ assertion.
  - Launcher chỉ hiện tiếng Việt, ưu tiên môi trường Python 3.11 được hỗ trợ và không gọi Python 3.12/3.13 làm phương án dự phòng.
  - Chạy lại T002–T004, import Workspace Chat và bộ quét tiếng Việt. Nếu còn lỗi đường cơ sở ngoài phạm vi, ghi rõ chủ sở hữu sửa tại T029.
  - Đạt khi Mốc 0 có `TECHNICAL_PASS`; `OPERATIONAL_PASS` chỉ ghi khi smoke thật cũng hoàn tất.

## 3. Mốc 1 — Trợ lý LSU có căn cứ

**Đích độc lập**: một case LSU có câu hỏi thẩm định và phản hồi của người đúng công đoạn; AI không thể tự duyệt.

**Thứ tự**: T006 → T007 → T008 → T009 → T010. Mốc này không phụ thuộc dữ liệu đo LSU.

- [x] T006 [P] [US2] Viết test hợp đồng chuyên gia trong `tests/test_workspace_case_expert_review.py`
  - Bao phủ người điều tra kiêm chuyên gia đúng scope; chuyên gia thứ hai tùy chọn; scope sai/hết hạn; thiếu lý do; digest đã đổi; hai ý kiến trái chiều; review sửa bằng bản kế tiếp.
  - Chứng minh actor lấy từ ngữ cảnh tin cậy, không lấy ID/role tự khai trên form; AI có danh sách quyền rỗng.
  - Bao phủ transaction lỗi và restart/readback; review cũ không có đường sửa hoặc xóa.
  - Đạt khi test thất bại vì API/migration chưa có, không thất bại vì fixture quyền mơ hồ.

- [x] T007 [US2] Thêm migration và kiểu dữ liệu nhỏ nhất cho `ExpertRequest`/`ExpertReview` trong `src/aios_habit/workspace_case_migrations.py` và `src/aios_habit/workspace_case_models.py`
  - Dùng chuỗi migration hiện có, backup trước đổi schema, `user_version`, checksum và `quick_check`; không dùng `CREATE TABLE IF NOT EXISTS` làm migration duy nhất.
  - Ràng buộc decision, rationale, claim/evidence digest, scope, reviewer, thời điểm và `supersedes_review_id`; mọi review append-only.
  - Đạt khi nâng cấp fixture cơ sở dữ liệu cũ, đọc lại dữ liệu cũ và phục hồi bản backup sau fault injection.

- [x] T008 [US2] Triển khai service thẩm định trong `src/aios_habit/workspace_case_service.py`, `src/aios_habit/workspace_case_repository.py` và tái dùng `src/aios_habit/workspace_case_authorization.py`
  - Cài `request_expert_review`, `record_expert_review`, xử lý yêu cầu thêm bằng chứng và xung đột theo contract.
  - Mặc định cho cùng người điều tra/xác nhận khi grant đúng scope; chỉ yêu cầu người thứ hai khi người dùng chọn hoặc có xung đột.
  - Kiểm role/scope, case version, evidence digest và lý do ở service; ghi activity cùng transaction.
  - Đạt khi toàn bộ T006 đạt và mọi đường gọi trái quyền bị từ chối ở service dù UI bị bỏ qua.

- [x] T009 [US2] Gắn khối thẩm định tiếng Việt vào chi tiết case tại `src/aios_habit/workspace_case_ui.py` và tuyến hiện có trong `src/aios_habit/workspace_chat_app.py`
  - Hiện câu hỏi, bằng chứng, người phụ trách, hạn mong muốn và ba hành động: xác nhận, bác bỏ, cần thêm bằng chứng.
  - Chỉ hiện người thứ hai khi được chọn; giải thích rõ trường hợp thiếu quyền, thiếu lý do, digest đổi hoặc đang cần phân xử.
  - Không tạo hộp thư, dashboard hoặc hệ quản trị vai trò mới.
  - Đạt khi test UI bao phủ trống/chờ/thành công/xung đột/lỗi và bộ quét tiếng Việt đạt.

- [x] T010 [US2] Kiểm chứng độc lập Mốc 1 bằng restart/readback và một câu hỏi LSU có citation; ghi bằng chứng đã làm sạch vào `PROJECT_HANDOVER.md`
  - Chạy T006 cùng toàn bộ test case bị ảnh hưởng, migration backup/restore, import Workspace Chat và `git diff --check`.
  - Nếu chưa có tài liệu LSU thật được phép, dùng trace fixture để đóng `TECHNICAL_PASS` và ghi `OPERATIONAL_PARTIAL`; khi có tài liệu thật thì chạy lại đúng smoke mà không đổi code.
  - Đạt khi một người đúng scope phản hồi được trong case, AI không có đường duyệt và mốc dữ liệu LSU vẫn có thể bắt đầu độc lập.

## 4. Mốc 2 — Nối lot, Unit và JIG BOWSKEW 4 BEAM

**Đích độc lập**: phần mềm hiểu đúng hợp đồng file, báo chính xác phần thiếu và truy được chuỗi lot → Unit → JIG → outcome.

**Thứ tự**: T011 → T012 → T013 → T014 → T015 → T016 → T017.

- [x] T011 [US7] Chốt và kiểm thử gói hợp đồng tự quyết định tại `specs/008-evidence-case-loop/contracts/lsu-iris-input.md`, `specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md`, `specs/008-evidence-case-loop/owner-decisions.example.yaml` và `tests/fixtures/lsu_iris/`
  - Gemini không đọc mẫu cục bộ thật. Chỉ tiến trình cục bộ được đọc nguồn thật; Gemini nhận manifest/số tổng hợp đã làm sạch và kết luận từng quy tắc, không nhận dòng dữ liệu, đường dẫn, serial hoặc giá trị đo.
  - Chỉ ghi vào repo tên cột đã được phép, kiểu, đơn vị, timezone, khóa, quy tắc trùng, giá trị rỗng và ba hàng giả hoàn toàn.
  - Chốt ba bảng chuẩn: thông số lot linh kiện, liên kết Unit–lot, kết quả JIG/outcome; chốt khóa `component_lot_id`, `unit_serial`, `jig_id`, `run_id` và thời điểm hiệu lực.
  - Ghi định dạng nhận trực tiếp là CSV/XLSX. Định dạng khác phải được người dùng xuất sang một trong hai dạng chuẩn; không xây bộ đọc file độc quyền trong MVP.
  - Dùng sẵn mặc định trong hợp đồng cho ánh xạ OK/NG/retest, ưu tiên bỏ sót, EWMA, cửa sổ nền, khoảng dự báo, quy tắc ghép outcome, feature allowlist và ngưỡng mẫu. Giá trị nào tài liệu cục bộ xác định rõ thì cấu hình cục bộ được quyền ghi đè có version; không hỏi người dùng về công thức thống kê.
  - Khóa giới hạn mặc định bảo vệ máy: CSV 100 MB, XLSX 25 MB, 200.000 dòng mỗi sheet, lô 10.000 dòng; cho phép chủ sở hữu chỉnh cấu hình cục bộ mà không sửa code.
  - Đạt khi người thực thi có thể tạo fixture hợp lệ, thiếu khóa, trùng và mâu thuẫn không cần hỏi lại; rubric tự trả `PASS`, `PASS_WITH_WARNING` hoặc `BLOCKED_DATA` cùng bước xử lý.

- [x] T012 [P] [US7] Viết test dữ liệu đầu vào trong `tests/test_lsu_iris_data.py` và fixture tại `tests/fixtures/lsu_iris/`
  - Bao phủ CSV/XLSX, UTF-8, số thập phân, ô trống, timezone Việt Nam, chuẩn hóa đơn vị, thời điểm đến muộn, khóa trùng, Unit dùng nhiều lot và nhiều lần retest.
  - Có bộ hợp lệ nhỏ, thiếu cột, sai kiểu, sai đơn vị, khóa mồ côi, bản ghi mâu thuẫn, file hỏng và file lớn theo giới hạn laptop.
  - Kiểm digest theo nội dung, không theo tên/đường dẫn file; không đưa đường dẫn tuyệt đối vào thông báo.
  - Đạt khi test thất bại đúng vì chưa có `production_prediction`, không phụ thuộc dữ liệu nhà máy.

- [x] T013 [US7] Tạo package và kiểu bản ghi cổng dữ liệu trong `src/aios_habit/production_prediction/__init__.py` và `src/aios_habit/production_prediction/models.py`
  - Định nghĩa ba bản ghi đầu vào, `DatasetVersion`, báo cáo readiness và mã lỗi nội bộ ổn định; tách câu tiếng Việt hiển thị khỏi mã máy đọc.
  - Báo cáo phải có tổng dòng, nối được, thiếu, trùng, mâu thuẫn, nhãn dương/âm/chưa xác định và từng hành động khắc phục.
  - Không tạo lớp model tổng quát, registry hay bảng tương lai.
  - Đạt khi các test model/serialization/readback mới trong T012 đạt và báo cáo không chứa dữ liệu thô.

- [x] T014 [US7] Viết bộ đọc, chuẩn hóa và nối chuỗi trong `src/aios_habit/production_prediction/lsu_iris.py`
  - Tách `read`, `normalize`, `validate`, `join`, `trace_unit` thành hàm tất định; xử lý theo lô nhỏ để không giữ toàn bộ file lớn nhiều lần trong RAM.
  - Chỉ nối theo khóa và thời gian hiệu lực đã chốt; không nối theo tên file, vị trí dòng hoặc suy đoán gần giống.
  - File/row lỗi được cô lập vào báo cáo; một dòng xấu không làm mất báo cáo của toàn bộ lô, nhưng lỗi schema bắt buộc phải chặn đăng ký snapshot.
  - Đạt khi T012 đạt, cùng đầu vào cho cùng digest/kết quả và giới hạn bộ nhớ được ghi trong test hiệu năng nhỏ.

- [x] T015 [US7] Tạo migration và kho dự đoán có chốt đăng ký tại `src/aios_habit/production_prediction/migrations.py`, `src/aios_habit/production_prediction/repository.py` và `tests/test_lsu_prediction_repository.py`
  - Luôn xây và kiểm thử kho bằng SQLite tạm dù chưa có dữ liệu thật; runtime chỉ tạo/ghi `local_cases/production_prediction.sqlite` sau readiness thật đạt.
  - Có `schema_migrations`, backup, `user_version`, checksum, `quick_check`, transaction, đóng kết nối và phục hồi khi migration/ghi bị lỗi.
  - `register_lsu_snapshot` phải idempotent theo snapshot/source digest; dữ liệu `blocked` không được ghi bền vững.
  - Đạt khi kho fixture có `TECHNICAL_PASS`; dữ liệu thật chưa đạt chỉ làm đăng ký runtime trả `OPERATIONAL_BLOCKED`, không chặn T016–T021.

- [x] T016 [US7] Gắn màn hình cổng dữ liệu và truy Unit vào Workspace Chat qua `src/aios_habit/prediction_shadow_ui.py` và `src/aios_habit/workspace_chat_app.py`
  - Tạo một điểm vào “Kiểm tra dữ liệu LSU”; không khôi phục Studio/Case Cockpit và không thêm tuyến ứng dụng thứ hai.
  - Hiện trạng thái chưa chọn file, đang đọc, đạt, thiếu khóa, mâu thuẫn, file không hỗ trợ và chưa được phép đăng ký; mỗi trạng thái có bước tiếp theo bằng tiếng Việt.
  - Cho tìm một `unit_serial` và xem chuỗi lot/thông số/JIG/lần đo/outcome; mã kỹ thuật có giải thích gần đó.
  - Đạt khi test UI dùng fixture bao phủ đủ trạng thái, không lộ tên model/traceback/đường dẫn và import Workspace Chat thành công.

- [x] T017 [US7] Đóng cổng Mốc 2 theo hai mức và ghi kết quả vào `PROJECT_HANDOVER.md`
  - Chạy toàn bộ test T012–T016, migration backup/restore, restart/readback, bộ quét tiếng Việt và một lượt fixture từ file đến màn hình.
  - Nếu file thật có sẵn: chạy cục bộ, ghi chỉ số đã làm sạch gồm số dòng/nối được/thiếu/trùng/mâu thuẫn và digest; không ghi dữ liệu thật.
  - Nếu file thật chưa có hoặc không đạt: xuất danh sách chính xác cột/khóa/chủ sở hữu cần bổ sung, ghi `TECHNICAL_PASS` + trạng thái vận hành phù hợp, rồi tiếp tục xây Mốc 3 trên fixture.
  - Tự ghi `OPERATIONAL_PASS` khi snapshot thật truy được ít nhất một Unit trọn chuỗi, vượt rubric T011 và biên nhận không chứa dữ liệu thật; không cần một bước duyệt thủ công riêng.

## 5. Mốc 3 — Phát lại lịch sử

**Đích độc lập**: công cụ đánh giá chạy lại được, không nhìn trước tương lai và cho biết phương án cảnh báo có hơn phương án không cảnh báo hay không.

**Thứ tự**: T018 → T019 → T020 → T021 → T022. Mốc kỹ thuật dùng fixture đã đăng ký; cổng vận hành cần snapshot thật.

- [x] T018 [P] [US8] Viết test giao thức phát lại trong `tests/test_lsu_prediction_evaluation.py`
  - Khóa `as_of_time`; cấm outcome, retest, dữ liệu đến sau hoặc tổng hợp tương lai lọt vào feature.
  - Khóa một cảnh báo tối đa cho mỗi Unit/cửa sổ; cảnh báo đúng, cảnh báo nhầm, bỏ sót và lead time theo hợp đồng tại `plan.md` mục 5.1; `no_alert` phải tính mọi NG là bỏ sót.
  - Khi cấu hình cục bộ không ghi đè, dùng đúng mặc định có version trong hợp đồng T011. Chỉ trả `not_applicable` khi dữ liệu không đủ để áp dụng an toàn, không tự đổi sang công thức khác.
  - Chia theo thời gian và Unit; cùng Unit không được xuất hiện ở cả phần học và phần đánh giá khi protocol cấm.
  - Kiểm cảnh báo đúng, cảnh báo nhầm, bỏ sót, thời gian sớm, trường hợp không có NG, chỉ có NG và mẫu quá ít.
  - Chạy hai lần cùng snapshot/protocol/seed phải cho cùng kết quả và digest.
  - Đạt khi test thất bại trước implementation nhưng fixture đủ cả hai nhãn và ít nhất ba khoảng thời gian.

- [x] T019 [US8] Triển khai hai phương án nền cố định trong `src/aios_habit/production_prediction/evaluation.py`
  - Phương án thứ nhất luôn là không cảnh báo; phương án thứ hai là EWMA với tham số nằm trong cấu hình versioned, không quét lưới tham số.
  - Với nhiều metric, dùng thứ tự và giới hạn trong hợp đồng T011; một Unit có tối đa một cảnh báo/cửa sổ và chỉ giữ ba yếu tố lệch chuẩn hóa lớn nhất.
  - Nếu chuỗi không có thứ tự thời gian, khoảng lấy mẫu không dùng được hoặc thiếu lịch sử nền, EWMA trả `not_applicable` kèm lý do và kế hoạch dữ liệu; không tự chuyển sang luật khác.
  - Chỉ dùng metric/chiều/cửa sổ/threshold trong protocol; tính cùng một bộ chỉ số cho hai phương án và không dùng accuracy trung bình làm tiêu chí duy nhất.
  - Đạt khi T018 cho phần baseline đạt trên CPU và dữ liệu xấu tạo báo cáo, không làm sập chương trình.

- [x] T020 [US8] Khóa nhánh model tùy chọn trong `src/aios_habit/production_prediction/evaluation.py` và `tests/test_lsu_prediction_evaluation.py`; chỉ khi đủ điều kiện mới cập nhật `pyproject.toml` và `uv.lock`
  - Luôn triển khai/kiểm thử đường `not_applicable` để baseline chạy độc lập. Chỉ khi Data Gate thật tự đạt rubric, có cả OK/NG, ít nhất ba khoảng thời gian và đạt công thức cỡ mẫu trong rubric mới thêm dependency và kích hoạt hồi quy logistic.
  - Dùng pipeline cố định: điền thiếu có khai báo, chuẩn hóa số, mã hóa danh mục và `LogisticRegression`; seed và feature schema được đóng băng.
  - Dependency máy học nằm trong extra tùy chọn; ứng dụng không cài extra vẫn chạy đầy đủ Data Gate, baseline và UI.
  - Khi điều kiện thật chưa đạt, không sửa dependency chỉ để trình diễn; T020 vẫn đạt kỹ thuật khi test đường không-model, thiếu nhãn và chống rò rỉ đều đạt. Nếu điều kiện đạt, chạy thêm test có/không dependency trên laptop CPU; không thử model thứ hai.

- [x] T021 [US8] Xuất báo cáo phát lại tiếng Việt tại `src/aios_habit/production_prediction/reporting.py` và kiểm thử tại `tests/test_lsu_prediction_reporting.py`
  - Báo snapshot/protocol/code/threshold digest, số đúng/nhầm/bỏ sót, thời gian sớm, kết quả theo giai đoạn/JIG và giới hạn dữ liệu.
  - So sánh rõ không cảnh báo, EWMA và hồi quy logistic nếu có; mục không áp dụng phải nói vì sao và cần bổ sung gì.
  - Báo cáo chỉ chứa số tổng hợp và định danh đã làm sạch; không chứa hàng dữ liệu thô, đường dẫn tuyệt đối hoặc tên thư viện/model nội bộ trên giao diện.
  - Đạt khi cùng đầu vào tạo báo cáo cùng digest, bộ quét tiếng Việt đạt và mở được khi model tùy chọn không cài.

- [x] T022 [US8] Tự chấm cổng phát lại theo `specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md` và ghi vào `PROJECT_HANDOVER.md`
  - `AUTO_SHADOW`: đủ mẫu và đạt toàn bộ ngưỡng mặc định; tự khóa phương pháp/threshold/rubric digest và mở chạy bóng đọc-only.
  - `LEARNING_SHADOW`: kỹ thuật an toàn nhưng chưa đủ mẫu hoặc hiệu quả; vẫn mở chạy bóng đọc-only để thu outcome và hiện rõ “chưa đủ bằng chứng”.
  - `BLOCKED_DATA` hoặc `FAIL_TECHNICAL`: có rò rỉ tương lai, schema sai hoặc kết quả không tái lập; nêu chính xác việc cần sửa và không chạy trên lô lỗi.
  - Tác tử không được thay ngưỡng sau khi thấy kết quả. Muốn đổi phải tạo phiên bản rubric mới, ghi lý do và chạy lại toàn bộ phát lại.
  - Đạt khi quyết định tái lập được từ digest và không có đường biến chạy bóng thành điều khiển máy hoặc gửi cảnh báo ngoài ứng dụng.

## 6. Mốc 4 — Chạy thử nghiệm bóng thủ công

**Đích độc lập**: người dùng chủ động chọn lô mới, xem danh sách nguy cơ và ghi outcome; chạy lại không tạo case trùng.

**Thứ tự**: T023 → T024 → T025 → T026 → T027.

- [x] T023 [P] [US9] Viết test chạy thử nghiệm bóng trong `tests/test_lsu_manual_shadow.py`
  - Bao phủ rubric hết hạn/sai phiên bản, file hợp lệ/lỗi, `AUTO_SHADOW`, `LEARNING_SHADOW`, không có nguy cơ, có nhiều nguy cơ và người dùng dừng giữa chừng.
  - Kiểm snapshot feature tại `as_of_time`, giải thích yếu tố, threshold digest, dedup/cooldown và bốn outcome đúng/nhầm/bỏ sót/chưa xác định.
  - Chứng minh file dùng để dự báo không đưa outcome/retest tương lai vào feature và có thể ghi một bỏ sót cho Unit không từng có assessment cảnh báo.
  - Fault injection giữa `production_prediction.sqlite` và `workspace_cases.sqlite`; chạy lại phải tìm bản ghi/case cũ trước khi tạo mới.
  - Đạt khi test thất bại trước implementation và không cần scheduler, mạng hoặc dữ liệu thật.

- [x] T024 [US9] Tạo runner thủ công tại `src/aios_habit/production_prediction/shadow.py`
  - Chỉ xử lý file người dùng vừa chọn và dữ liệu có sẵn tại `as_of_time`, theo lô nhỏ, có tiến độ, nút dừng an toàn và khả năng chạy lại; outcome tương lai được nhập ở bước phản hồi riêng.
  - Chế độ fixture kiểm kỹ thuật; chế độ dữ liệu thật phải kiểm kết luận tự động T022, schema, threshold, rubric và phương pháp đúng phiên bản.
  - Không có scheduler, worker nền, gửi tin ngoài ứng dụng, PLC hoặc thay đổi máy.
  - Đạt khi T023 phần runner đạt, dừng giữa chừng không ghi nửa snapshot và lỗi ngoài được đổi thành tiếng Việt.

- [x] T025 [US9] Hoàn thiện màn hình chạy thử nghiệm bóng tại `src/aios_habit/prediction_shadow_ui.py` và điểm vào trong `src/aios_habit/workspace_chat_app.py`
  - Hiện rõ “đang kiểm tra dữ liệu”, “đang chạy bóng để học”, “đang chạy bóng đạt tiêu chí”, “không phát hiện nguy cơ”, “có Unit cần kiểm tra”, “đã dừng”, “có lỗi” và bước xử lý tiếp theo.
  - Với mỗi nguy cơ, hiện thời điểm, yếu tố, nguồn/digest đã làm sạch, phiên bản ngưỡng/phương pháp và câu “cần kiểm tra”; không nói chắc chắn hỏng.
  - Không hiện bộ chọn model, tham số kỹ thuật hoặc nút bật cảnh báo vận hành.
  - Có thao tác ghi Unit NG bị bỏ sót ngay cả khi Unit đó không có cảnh báo trước đó; yêu cầu outcome, bằng chứng, người xác nhận và lý do.
  - Đạt khi test UI và smoke fixture bao phủ đủ trạng thái, tiến độ không đứng im và bộ quét tiếng Việt đạt.

- [x] T026 [US9] Liên kết đánh giá nguy cơ với case dự đoán và outcome trong `src/aios_habit/production_prediction/shadow.py`, `src/aios_habit/workspace_case_service.py` và hai repository liên quan
  - Tạo `idempotency_key` bằng tuần tự hóa chuẩn từ dataset/phương pháp/threshold/digest lô/Unit/cửa sổ đánh giá; không dùng thời điểm đồng hồ lúc chạy nên cùng lô luôn ra cùng khóa.
  - Dùng trình tự ghi có thể phục hồi: `pending_case_link` → tìm/tạo case → `linked`; lỗi giữ `retryable_error`, lần chạy lại tìm case hiện có và tiếp tục bước thiếu thay vì nhân đôi.
  - Outcome từ trường kết quả cuối cùng vượt rubric được ghi tự động với nguồn/digest; kết quả mâu thuẫn là `unknown`. Người dùng vẫn có thể sửa bằng bản ghi append-only có lý do; bỏ sót có thể gắn với Unit không từng tạo cảnh báo.
  - Đạt khi fault injection ở từng bước và restart/readback đều phục hồi đúng mà không cần outbox phân tán.

- [x] T027 [US9] Đóng cổng Mốc 4 theo hai mức và ghi bằng chứng đã làm sạch vào `PROJECT_HANDOVER.md`
  - Luôn chạy một lượt rehearsal bằng fixture từ chọn file → tiến độ → nguy cơ → case → outcome → chạy lại chống trùng để đóng `TECHNICAL_PASS`.
  - Khi T022 trả `AUTO_SHADOW` hoặc `LEARNING_SHADOW`, tự chạy một lô thật được phép nếu đã có nguồn cục bộ; ghi số đúng/nhầm/bỏ sót/chưa xác định và giới hạn, không ghi dữ liệu thô.
  - Nếu chưa có lô mới hoặc dữ liệu bị chặn, ghi chính xác điều còn thiếu và trạng thái tương ứng; không chặn T028–T029 hoặc task pack của nhánh độc lập khác.
  - Chỉ ghi `OPERATIONAL_PASS` khi ít nhất một lô thật hoàn tất và outcome được xác nhận tự động từ nguồn hợp lệ hoặc được người dùng sửa có bằng chứng.

## 7. Đóng đợt và mở đường cho các đợt sau

**Thứ tự**: tác tử thực thi hoàn tất T028; tác tử kiểm toán độc lập trong cùng `/goal` thực hiện T029. Lỗi được trả lại cho tác tử thực thi sửa rồi tác tử kiểm toán chạy lại.

- [x] T028 Đồng bộ trạng thái và tạo bản đồ kích hoạt đợt kế tiếp trong `ROADMAP.md`, `ARCHITECTURE.md`, `PROJECT_HANDOVER.md` và phần backlog của `specs/008-evidence-case-loop/tasks.md`
  - Ghi riêng `TECHNICAL_PASS` và trạng thái vận hành cho từng mốc; không dùng một trạng thái chung che mất nhánh đang chờ.
  - Với từng nhánh US3, US4, US5, US6, US10 và US11, ghi đủ bốn mục: đầu vào tối thiểu, người quyết định, đầu ra nhỏ nhất dùng được và lệnh/test đầu tiên của task pack kế tiếp.
  - Mở task pack kế tiếp theo dữ liệu sẵn sàng, không bắt buộc thứ tự giữa learning, C-call/Jam, Agent và NAS; Drum/DLP vẫn phụ thuộc hợp đồng LSU, còn cảnh báo thật vẫn phụ thuộc shadow.
  - Đăng ký hai bí danh nguồn cục bộ `KHO_LSU_CUC_BO` và `GOI_KYOCERA_CUC_BO`; chỉ tạo hợp đồng kiểm kê an toàn cho gói mở rộng Kyocera, không đọc nội dung Kyocera hoặc mở gói Kyocera/Drum/DLP trong đợt hiện tại (US4 chuẩn là trợ lý điều tra line theo `spec.md`).
  - Đạt khi không có giới hạn của một nhánh được mô tả như blocker toàn chương trình và không có năng lực dài hạn nào biến mất khỏi lộ trình.

- [x] T029 Kiểm toán độc lập toàn đợt, thực hiện vòng sửa–kiểm toán lại và chỉ đóng các cổng có bằng chứng hiện tại
  - Task này thuộc tác tử kiểm toán độc lập trong cùng `/goal`; không được dùng chính tác tử đã sửa nhóm file đang chấm. Tác tử kiểm toán được tự đánh dấu checkbox theo rubric và bằng chứng lệnh thật.
  - Người kiểm toán chạy `scripts/check_user_facing_vietnamese.py`, các test T002–T026, toàn bộ `pytest`, `compileall`, CLI audit, import Workspace Chat, `scripts/check_docs.py`, `git diff --check` và `git diff --cached --check`.
  - Kiểm trình duyệt tất cả bề mặt vừa sửa; cố ý tạo lỗi tiếng Anh bên ngoài; không cho qua nếu còn bộ chọn ngôn ngữ, traceback, tên engine/model hoặc câu không phải tiếng Việt do chương trình tạo.
  - Lỗi test nền hoặc đóng gói đã biết vẫn phải được phân loại và sửa tận gốc nếu tái hiện trong môi trường Python 3.11 được hỗ trợ; không xóa test, hạ ngưỡng hoặc miễn trừ để lấy PASS. Người kiểm toán ghi phiếu lỗi, người thực thi sửa tối đa hai vòng cho cùng nguyên nhân, sau đó người kiểm toán chạy lại. Lỗi phụ thuộc quyền máy/dịch vụ ngoài repo được ghi `BLOCKED` với lệnh tái hiện và không được kéo phạm vi sang hệ thống khác.
  - Kiểm dữ liệu thật không vào Git/cloud; migration có backup/restore; module được hỗ trợ không import Studio/Case Cockpit; model extra không làm hỏng đường không-model.
  - Kiểm đủ 29 dòng checklist, mỗi task đã làm có receipt/lệnh/mã thoát; đối chiếu `RISK_REGISTER.md` để mọi rủi ro cao đã đóng hoặc dừng đúng chốt và mọi rủi ro còn lại có ảnh hưởng cùng bước xử lý rõ.
  - Đạt khi toàn bộ cổng chất lượng repo PASS. Thiếu bằng chứng vận hành chỉ giữ đúng cổng vận hành ở `PARTIAL`/`BLOCKED`, không phủ nhận `TECHNICAL_PASS` đã kiểm chứng và không chặn tạo task pack của nhánh độc lập.

## 8. Phụ thuộc và đường đi tiếp

```text
Mốc 0 ──> Mốc 1
  │
  └─────> Mốc 2 kỹ thuật ──> Mốc 3 kỹ thuật ──> Mốc 4 kỹ thuật
                    │                 │                 │
                    └─ dữ liệu thật ──┴─ rubric đạt ───┴─ shadow thật ──> US10

Mốc 1 có review thật ──> US3
Log/SOP/mapping sẵn sàng ──> US4 ──> US5
Workspace code tách biệt ──> US6
Môi trường nhiều máy sẵn sàng ──> US11
Hợp đồng LSU đã chứng minh ──> BOWSKEW khác ──> Drum/DLP
```

- T002 và T003 có thể làm song song sau T001.
- T006 có thể chuẩn bị khi T004 đang smoke, nhưng T007 chỉ bắt đầu sau khi T005 khóa migration nền.
- T012 có thể viết fixture/test ngay sau T011; không chờ file thật.
- T018 và T023 có thể thiết kế test từ contract sau khi model dữ liệu ổn định; implementation vẫn theo thứ tự mốc.
- US3, US4, US5, US6 và US11 là các nhánh độc lập về dữ liệu. Chỉ điều kiện riêng của từng nhánh mới được phép giữ khóa nhánh đó.

## 9. Backlog có điều kiện — Bản đồ kích hoạt task pack kế tiếp

Các nhánh bên dưới hoàn toàn độc lập về dữ liệu và tiến độ. Không bắt buộc thứ tự phụ thuộc giữa chúng, ngoại trừ Drum/DLP cần tái dùng hợp đồng chuẩn hóa và cảnh báo vận hành thật phụ thuộc kết quả chạy bóng.

### 9.1 Đăng ký bí danh nguồn dữ liệu cục bộ (Local Storage Aliases)

- `KHO_LSU_CUC_BO`: Đường dẫn thư mục dữ liệu thật của LSU tại nhà máy (ví dụ trên máy xưởng: `D:\Data\LSU_Prod`). Tuyệt đối không commit vào Git, luôn tuân thủ nhãn `local_only`.
- `GOI_KYOCERA_CUC_BO`: Đường dẫn lưu trữ tài liệu kỹ thuật và mẫu log dòng máy Kyocera cục bộ. Chỉ dùng để kiểm kê cấu trúc, không đọc nội dung hoặc mở task pack khi chưa duyệt.

### 9.2 Bản đồ kích hoạt 6 nhánh độc lập (Mỗi nhánh đủ 4 tiêu chí bắt buộc theo chuẩn canonical spec.md)

1. **Nhánh US3 — Trích xuất và tra cứu bài học kinh nghiệm (Lesson Learned)**:
   - **Đầu vào tối thiểu**: Tối thiểu một hồ sơ vụ việc (case) đã giải quyết xong với thẩm định chuyên gia `confirmed`, đủ nguồn dẫn chứng và nhãn `local_only`.
   - **Người quyết định**: Trưởng bộ phận Kỹ thuật / Quản lý QC xưởng.
   - **Đầu ra nhỏ nhất dùng được**: Bảng tổng hợp các bài học khuyến nghị hiển thị trong Workspace Chat khi xử lý sự cố tương tự.
   - **Lệnh/test đầu tiên của task pack kế tiếp**: `uv run --no-sync --group dev pytest tests/test_case_knowledge_lessons.py -k test_lesson_extraction_contract`

2. **Nhánh US4 — Trợ lý điều tra line chủ động (Line Investigation & Root Cause Triage)**:
   - **Đầu vào tối thiểu**: Dữ liệu log sự kiện dây chuyền (parser đã có) liên kết phạm vi máy/mã lỗi/thời gian của case, bằng chứng và nguồn dẫn chứng `local_only`.
   - **Người quyết định**: Kỹ sư phụ trách dây chuyền & Trưởng ca sản xuất.
   - **Đầu ra nhỏ nhất dùng được**: Giao diện timeline sự kiện nghi ngờ, nhóm hiện tượng lặp và danh sách dữ kiện còn thiếu với cơ chế xác nhận liên quan của chuyên gia.
   - **Lệnh/test đầu tiên của task pack kế tiếp**: `uv run --no-sync --group dev pytest tests/test_line_investigation.py -k test_line_investigation_timeline`

3. **Nhánh US5 — Agent tạo đầu ra công việc có kiểm soát (Controlled Artifacts & SOP Review)**:
   - **Đầu vào tối thiểu**: Hồ sơ vụ việc có đủ bằng chứng đã xác nhận và mẫu template báo cáo điều tra / SOP có kiểm soát.
   - **Người quyết định**: Trưởng bộ phận Kỹ thuật & Người duyệt quy trình chất lượng (SOP Approver).
   - **Đầu ra nhỏ nhất dùng được**: Luồng tạo nháp Markdown, so sánh khác biệt phiên bản, phê duyệt và xuất bản sao có kiểm soát trong output root cục bộ.
   - **Lệnh/test đầu tiên của task pack kế tiếp**: `uv run --no-sync --group dev pytest tests/test_controlled_artifacts_sop.py -k test_report_sop_drafting`

4. **Nhánh US6 — Agent hỗ trợ lập trình trong workspace tách biệt (Sandbox Scripting & Tool Prototyping)**:
   - **Đầu vào tối thiểu**: Task pack lập trình có mục tiêu, file cho phép/cấm rõ ràng, lệnh kiểm thử allowlist và môi trường workspace/sandbox tách biệt.
   - **Người quyết định**: Kiến trúc sư phần mềm (Technical Architect) & Kỹ sư trưởng hệ thống.
   - **Đầu ra nhỏ nhất dùng được**: Proposal bất biến gồm diff và lệnh dự kiến, cơ chế người duyệt cấp phép trước khi áp dụng và nhập kết quả có bằng chứng quan sát được.
   - **Lệnh/test đầu tiên của task pack kế tiếp**: `uv run --no-sync --group dev pytest tests/test_sandbox_coding_proposal.py -k test_immutable_proposal_contract`

5. **Nhánh US10 — Cảnh báo trong ứng dụng có duyệt và đề xuất phòng ngừa (In-App Risk Notification)**:
   - **Đầu vào tối thiểu**: Chạy bóng thực địa hoàn tất ít nhất một lô sản xuất thật, outcome được xác nhận và người dùng bật quyền nhận cảnh báo.
   - **Người quyết định**: Trưởng ca vận hành sản xuất.
   - **Đầu ra nhỏ nhất dùng được**: Banner thông báo nguy cơ hiển thị an toàn trên đầu màn hình Workspace Chat kèm nút tắt/ẩn tạm thời (không nối mạng điều khiển máy).
   - **Lệnh/test đầu tiên của task pack kế tiếp**: `uv run --no-sync --group dev pytest tests/test_in_app_risk_notification.py -k test_notification_banner_render`

6. **Nhánh US11 — Thư viện công ty dùng chung và đa tiến trình/NAS an toàn (Multi-User Shared Library)**:
   - **Đầu vào tối thiểu**: Thư mục mạng SMB/NAS nội bộ có cơ chế cấp quyền đọc/ghi cấp hệ điều hành và quy trình sao lưu khôi phục tự động.
   - **Người quyết định**: Quản trị viên hệ thống mạng xưởng (IT Admin).
   - **Đầu ra nhỏ nhất dùng được**: Cơ chế khóa tệp (file lease/lock) SQLite fail-closed chống xung đột ghi đồng thời trên ổ mạng chia sẻ.
   - **Lệnh/test đầu tiên của task pack kế tiếp**: `uv run --no-sync --group dev pytest tests/test_nas_sqlite_concurrency.py -k test_safe_file_locking`

Khi điều kiện của bất kỳ nhánh nào đạt, tạo một task pack nhỏ từ đúng đầu ra tối thiểu đó. Không gom gộp làm chậm các nhánh độc lập khác.

## 10. Giai đoạn hội tụ — Sáu US còn lại để chạy bằng một `/goal`

Phần này kích hoạt đợt T030–T057 theo yêu cầu mới của chủ sở hữu. `spec.md` là nguồn chuẩn về tên và phạm vi: US3 học từ phản hồi, US4 điều tra line, US5 tạo báo cáo/SOP, US6 hỗ trợ lập trình, US10 cảnh báo trong ứng dụng và US11 thư viện dùng chung. Drum/DLP, lịch chạy nền và điều khiển máy không thuộc đợt này.

**Cách đi để không bị chặn cả kế hoạch**:

- T030–T032 đóng nợ kiểm toán hiện tại và sửa bản đồ US bị lệch trước khi mở code mới.
- Sáu nhánh kỹ thuật độc lập sau T032. Thiếu dữ liệu/người dùng/mạng thật chỉ giữ nhánh tương ứng ở `OPERATIONAL_PARTIAL`; vẫn phải hoàn tất code, test bằng dữ liệu giả và bàn giao rõ điều còn thiếu.
- US5 có thể hoàn tất kỹ thuật bằng gói bằng chứng giả mà không chờ pilot thật của US4. US10 có thể hoàn tất giao diện bằng bản ghi shadow giả nhưng không được bật cảnh báo vận hành khi gate thật chưa đạt.
- Mọi chữ do chương trình tạo cho người dùng — nút, nhãn, hướng dẫn, trạng thái, tiến độ, cảnh báo, lỗi, nhật ký vận hành và báo cáo — chỉ dùng tiếng Việt dễ hiểu cho người không học công nghệ. Không hiện nguyên traceback, đường dẫn máy, tên engine/model hoặc lỗi tiếng Anh từ thư viện. Mã thiết bị và hằng máy đọc được phép giữ nguyên khi có lời giải thích tiếng Việt đi kèm.
- Mỗi nhiệm vụ phải có test tập trung, `git diff --check` và biên nhận trong `local_runs/`; không đưa biên nhận, dữ liệu thật hay đường dẫn thật vào Git.

### 10.1. Khóa nền trước khi mở sáu nhánh

- [x] T030 Sửa hết phiếu lỗi kỹ thuật còn mở của T029 trước khi thêm chức năng mới (`T029`, `contracts/lsu-acceptance-rubric.md`)
  - Sửa lỗi cú pháp của `scripts/desktop_smoke_test.py`; bổ sung quét các chữ giao diện còn sót như `Unit`, `Units`, `Lot` và các đường hiện nguyên `str(exc)`.
  - Buộc lát cắt đầu chỉ nhận cấu hình BOWSKEW 4 BEAM; dùng hoặc loại khỏi hợp đồng các tham số chưa có hiệu lực như `baseline_window`, `risk_direction`, `maximum_ewma_metrics`, không để cấu hình giả.
  - Thực hiện đúng giới hạn lô 10.000 dòng hoặc sửa hợp đồng theo hành vi có kiểm chứng nhưng không được nạp vượt giới hạn RAM đã khóa; bỏ việc tạo bảng dự đoán lúc chạy nếu migration đã quản lý bảng đó.
  - Chạy lại các test đối kháng LSU, smoke giao diện và bộ quét tiếng Việt; đạt khi các lỗi trên có test hồi quy và không hạ ngưỡng để lấy PASS.

- [x] T031 Cho tác tử kiểm toán độc lập chạy lại và đóng T029 bằng bằng chứng mới (`T029`, `FR-027`)
  - Không tin biên nhận cũ có kết luận sớm; đối chiếu đủ T001–T029 với diff và lệnh thật, sửa `CHECKLIST.md`, `AUDIT_REPORT.md`, receipt nào sai trạng thái.
  - Chạy Python 3.11, `compileall`, toàn bộ `pytest -q`, CLI audit, import Workspace Chat, kiểm tra tài liệu, kiểm tra tiếng Việt, smoke trình duyệt, `git diff --check` và `git diff --cached --check`.
  - Đạt khi T029 được chính tác tử kiểm toán đánh dấu bằng mã thoát/số test hiện tại; thiếu dữ liệu xưởng chỉ ghi đúng cổng vận hành là một phần, không giả thành đạt.

- [x] T032 Đồng bộ lại tên và điều kiện sáu US theo `spec.md`, xóa bản đồ backlog gán sai US4–US6 (`spec.md:98`, `spec.md:108`, `spec.md:117`, `spec.md:126`, `spec.md:163`, `spec.md:171`)
  - Sửa `ROADMAP.md`, `ARCHITECTURE.md`, `PROJECT_HANDOVER.md`, `plan.md` và phần backlog cũ của file này: US4 là điều tra line, US5 là báo cáo/SOP, US6 là hỗ trợ lập trình.
  - Đầu vào kỹ thuật dùng dữ liệu giả đã làm sạch; đầu vào thật chỉ quyết định trạng thái vận hành. Không đặt điều kiện “năm case” khi `spec.md` chỉ yêu cầu ít nhất một case thật đã xác nhận và kết luận.
  - Ghi rõ Drum/DLP là nhánh mở rộng sau US7–US10, không tráo thành US4; đạt khi `scripts/check_docs.py` qua và không còn ánh xạ mâu thuẫn.

### 10.2. US3 — Học từ phản hồi đã xác nhận

- [x] T033 Viết test hợp đồng và migration nhỏ cho bài học trong kho hồ sơ hiện có (`US3`, `FR-007`, `FR-015`)
  - Tái dùng `workspace_cases.sqlite`, `WorkspaceCaseRepository` và migration backup/restore hiện có; không tạo kho vector hoặc file dữ liệu thứ hai.
  - Bản ghi tối thiểu gồm bài học, trạng thái ứng viên/đã duyệt/đã thu hồi, `case_id`, `review_id`, digest bằng chứng, người và thời điểm thay đổi.
  - Test trước các trường hợp: chỉ review `confirmed` tạo được ứng viên; migration lỗi phục hồi được; restart đọc lại đủ; bài học nháp/thu hồi không lọt vào kết quả dùng lại.

- [x] T034 Nối thao tác tạo, sửa, duyệt và thu hồi bài học vào dịch vụ hồ sơ (`US3`, `FR-007`)
  - Dùng quyền/scope hiện có và activity append-only; không coi chức danh là quyền toàn cục và không sửa đè lịch sử review.
  - Có optimistic version để hai lần sửa đồng thời không ghi đè im lặng; lỗi trả mã nội bộ nhưng lớp hiển thị phải giải thích bằng tiếng Việt.
  - Không tự huấn luyện model, không ghi sang `library.sqlite` và không tự biến nội dung chat thô thành sự thật.

- [x] T035 Thêm tra cứu từ khóa và màn hình bài học trong Workspace Chat (`US3`, `SC-004`)
  - Tìm kiếm đơn giản bằng SQLite trên tiêu đề/nội dung đã duyệt; trả tối đa một danh sách ngắn có liên kết về case, review và bằng chứng gốc.
  - Giao diện cho phép tạo ứng viên từ review, sửa, duyệt, thu hồi và mở nguồn; đủ trạng thái trống, thiếu nguồn, thành công, xung đột và lỗi.
  - Tất cả chữ do chương trình tạo phải là tiếng Việt dễ hiểu; không hiển thị từ kỹ thuật tiếng Anh thay cho hướng dẫn người dùng.

- [x] T036 Kiểm toán lát US3 bằng dữ liệu giả và ghi trạng thái vận hành riêng (`US3`, `SC-004`)
  - Chạy test chính, test quyền, restart/readback, fault injection, tìm kiếm và quét tiếng Việt.
  - Nếu chưa có case thật đã xác nhận/kết luận, đánh dấu US3 `TECHNICAL_PASS` và `OPERATIONAL_PARTIAL`; ghi đúng một bước người dùng cần làm để nghiệm thu thật.

### 10.3. US4 — Trợ lý điều tra line chủ động

- [x] T037 Dựng gói điều tra tối thiểu trên parser và kho log đã có (`US4`, `FR-008`)
  - Tái dùng `line_log_parser.py`, `line_events.sqlite`, citation và evidence reference hiện có; CSV thô không đưa vào RAG và không tạo kho log mới.
  - Từ phạm vi máy/mã lỗi/thời gian của case, tạo timeline sự kiện `suspected`, nhóm hiện tượng lặp và danh sách dữ kiện còn thiếu; không match thì trả rỗng, không lấy năm sự kiện mới nhất để lấp chỗ trống.
  - Test bằng fixture Jam và C-call đã làm sạch, gồm sai múi giờ, thiếu mã máy, trùng sự kiện và không có kết quả.

- [x] T038 Cho người dùng xác nhận hoặc bác bỏ độ liên quan của từng manh mối (`US4`, `FR-008`, `FR-015`)
  - Lưu phản hồi append-only trong hồ sơ với provenance và scope công đoạn; giữ nguyên trạng thái `suspected` cho đến khi có xác nhận.
  - Mapping/sơ đồ chỉ hiện khi tham chiếu có phiên bản, digest và trạng thái đã duyệt; ảnh hay đường dẫn nguồn thật không sao chép vào DB hoặc report kiểm thử.
  - Test xung đột phiên bản, bằng chứng mất, hai ý kiến trái chiều và restart/readback.

- [x] T039 Thêm màn hình điều tra gọn trong chi tiết hồ sơ (`US4`, `SC-005`)
  - Chỉ gồm bộ lọc máy/thời gian, timeline, nhóm lặp, bằng chứng liên quan và câu hỏi còn thiếu; không làm dashboard phân tích mới và không tuyên bố chẩn đoán nguyên nhân.
  - Mọi trạng thái bình thường, trống, đang đọc, thiếu dữ liệu, cảnh báo và lỗi dùng tiếng Việt; lỗi parser/hệ điều hành được đổi thành nguyên nhân dễ hiểu cùng bước xử lý.

- [x] T040 Kiểm toán US4 và chạy diễn tập một case từ đầu đến gói điều tra (`US4`, `SC-005`)
  - Dùng fixture để chứng minh kỹ thuật; nếu có dữ liệu thật thì chỉ tiến trình cục bộ đọc và biên nhận chỉ giữ số tổng hợp đã làm sạch.
  - Pilot vận hành chỉ đạt khi một case thật đi qua xác nhận liên quan, báo cáo được duyệt và outcome; nếu thiếu thì US4 vẫn bàn giao `TECHNICAL_PASS`/`OPERATIONAL_PARTIAL` mà không chặn US3, US5, US6 hoặc US11.

### 10.4. US5 — Tạo báo cáo điều tra và SOP có kiểm soát

- [x] T041 Khóa đúng hai mẫu đầu ra và test bộ tạo nháp hiện có (`US5`, `FR-009`)
  - Tái dùng `agent_draft_sop.py`; chỉ hỗ trợ báo cáo điều tra và SOP dạng Markdown trong đợt này, không xây registry/plugin tổng quát.
  - Mỗi mẫu bắt buộc có mã case, kết luận hoặc phần chưa đủ căn cứ, citation/digest nguồn, sự kiện log ghi rõ là nghi ngờ, người tạo, phiên bản và người duyệt cần thiết.
  - Test không đủ bằng chứng, nguồn bị mất, nội dung nguy hiểm và đầu ra vượt vùng cho phép.

- [x] T042 Lưu phiên bản, so sánh thay đổi, duyệt và xuất bản sao mới (`US5`, `FR-009`, `SC-006`)
  - Tái dùng kho hồ sơ/migration hiện có; không xóa hoặc ghi đè tài liệu nguồn, không sửa nội dung của phiên bản đã duyệt.
  - Chỉ xuất dưới output root cục bộ được cấu hình; đường dẫn phải tương đối/an toàn, file trùng tên tạo phiên bản mới và thao tác lỗi không để artifact nửa vời.
  - Approval cũ mất hiệu lực khi nội dung đổi; activity giữ digest của phiên bản, kết quả kiểm tra và quyết định.

- [x] T043 Nối luồng tạo nháp–xem khác biệt–duyệt–xuất vào chi tiết case (`US5`, `SC-006`)
  - UI chỉ có lựa chọn “Báo cáo điều tra” và “Quy trình thao tác chuẩn” trong đợt này; hiển thị nguồn đã dùng, phần thay đổi và trạng thái duyệt.
  - Không hiện prompt nội bộ, traceback, đường dẫn tuyệt đối hoặc tên model/engine; mọi nút, tiến độ, lỗi và tài liệu do chương trình sinh dùng tiếng Việt dễ hiểu.

- [x] T044 Kiểm toán US5 bằng một báo cáo và một SOP giả lập (`US5`, `SC-006`)
  - Kiểm restart/readback, fault injection, chống ghi đè nguồn, thu hồi approval, citation và quét tiếng Việt trên cả UI lẫn file xuất.
  - Thiếu case thật/người duyệt thật chỉ giữ pilot vận hành ở trạng thái một phần; không mở thêm bảng tính, sơ đồ hoặc thiết kế công đoạn trong đợt này.

### 10.5. US6 — Hỗ trợ lập trình trong workspace tách biệt

- [x] T045 Khóa phạm vi task lập trình bằng nền task pack hiện có (`US6`, `FR-010`)
  - Tái dùng `agent_task_pack.py`; task bắt buộc có mục tiêu, file được phép, file cấm, lệnh kiểm thử được phép, commit đầu vào, quyền riêng tư và tiêu chí đạt.
  - Cấm `local_cases/`, `local_runs/` phiên khác, dữ liệu nhà máy, `.env`, lệnh phá hủy, điều khiển line và đường dẫn ngoài workspace; không xây container/orchestrator mới.
  - Test path traversal, symlink thoát scope, lệnh không allowlist, task pack bị sửa digest và dữ liệu nhạy cảm.

- [x] T046 Tạo proposal bất biến gồm diff và lệnh dự kiến, chưa tự áp dụng (`US6`, `FR-010`)
  - Tái dùng bridge/importer hiện có; người dùng xem file thay đổi, diff, lệnh sẽ chạy và rủi ro trước khi cấp phép.
  - Không auto merge, push, đổi nhánh hoặc chạy lệnh ngoài allowlist; thay đổi proposal tạo digest/phiên bản mới.
  - Lời giải thích cho người dùng phải bằng tiếng Việt, còn diff và tên mã giữ nguyên làm bằng chứng kỹ thuật.

- [x] T047 Nhập kết quả chạy và chỉ ghi đạt khi có bằng chứng quan sát được (`US6`, `FR-010`)
  - Tái dùng `agent_result_import.py`; đối chiếu task pack digest, commit, file đổi, lệnh, mã thoát và test thật; báo cáo tự khai không đủ để ghi PASS.
  - Lỗi tiếng Anh từ compiler/test runner chỉ lưu ở bằng chứng kỹ thuật cục bộ; UI hiển thị tóm tắt tiếng Việt cùng file/lệnh cần kiểm tra, không lộ secret hoặc đường dẫn riêng tư.

- [x] T048 Thêm màn hình task lập trình tối thiểu và kiểm toán US6 (`US6`)
  - Một màn hình cho tạo task pack, xem proposal/diff, cấp phép, xem kết quả và từ chối; không thêm hệ thống quản lý dự án hay trình soạn code mới.
  - Test happy path, từ chối, diff ngoài scope, báo đạt giả, restart/readback và quét tiếng Việt. Không có executor tin cậy thì bàn giao đường xuất/nhập thủ công là đầu ra dùng được và ghi phần tự chạy là `OPERATIONAL_PARTIAL`.

### 10.6. US10 — Cảnh báo trong ứng dụng có duyệt

- [x] T049 Tạo cổng bật cảnh báo từ kết quả shadow đã lưu (`US10`, `FR-014`, `FR-015`)
  - Tái dùng kho dự đoán, rubric và case link hiện có; chỉ nhận bản ghi đạt gate, chưa hết hạn, có provenance và chưa bị tắt bằng kill switch.
  - Fixture có thể mở cổng kỹ thuật; không được dùng fixture hoặc một báo cáo cục bộ để bật cảnh báo vận hành thật.
  - Không thêm scheduler, email, tin nhắn điện thoại, dịch vụ nền hay kết nối PLC/JIG.

- [x] T050 Hiển thị cảnh báo ngắn trong Workspace Chat và bốn thao tác người dùng (`US10`)
  - Cảnh báo có lý do dễ hiểu, mức ưu tiên, thời điểm, nút xác nhận, bác bỏ, tạm ẩn và mở hồ sơ; chống hiện lặp bằng khóa đã có.
  - Không lộ tên model/engine, công thức thống kê, traceback hoặc đường dẫn; toàn bộ chữ do chương trình tạo là tiếng Việt cho người không học công nghệ.
  - Khi cổng chưa đạt, UI nói rõ “chưa đủ dữ liệu để bật cảnh báo” và nêu bước cần làm, không để người dùng nhìn trạng thái kỹ thuật mơ hồ.

- [x] T051 Ghi phản hồi cảnh báo, kiểm kill switch và kiểm toán US10 (`US10`, `FR-015`)
  - Xác nhận/bác bỏ/tạm ẩn là activity append-only và có outcome/provenance; kill switch có hiệu lực ngay sau refresh/restart.
  - Test không cảnh báo khi gate thiếu, chống trùng, cooldown, quyền, restart/readback và quét tiếng Việt.
  - Nếu chưa có shadow thật đạt ngưỡng và người nhận thật, ghi `TECHNICAL_PASS`/`OPERATIONAL_PARTIAL`; không chặn năm nhánh còn lại.

### 10.7. US11 — Thư viện công ty dùng chung

- [x] T052 Hoàn thiện cấu hình đường dẫn thư viện dùng chung mà không hard-code máy (`US11`)
  - Tái dùng `storage_root`, `library.sqlite` và thao tác di chuyển có backup/`quick_check` trong `workspace_chat_store.py`; đường dẫn thật chỉ ở cấu hình cục bộ bị Git bỏ qua.
  - UI cho chọn, đổi, kiểm tra quyền và quay về kho cục bộ; khi lỗi không đổi con trỏ đang dùng và giải thích bằng tiếng Việt cách kiểm tra thư mục/quyền mạng.
  - Không đồng bộ chat, hồ sơ case, `line_events.sqlite` hoặc kho dự đoán lên thư viện chung.

- [x] T053 Kiểm chứng một máy ghi–nhiều máy đọc bằng khóa file sẵn có (`US11`)
  - Tái dùng `LibraryWriterLease`; writer thứ hai phải fail-closed, reader chỉ đọc không chiếm quyền ghi và ứng dụng báo rõ ai cần chờ/thử lại.
  - Test đa tiến trình cục bộ cho tranh chấp, mất kết nối giả lập, stale handle và giải phóng khóa sau lỗi; không tự chế giao thức khóa phân tán hoặc máy chủ cơ sở dữ liệu.

- [x] T054 Thêm thao tác sao lưu và khôi phục thư viện có kiểm tra toàn vẹn (`US11`)
  - Dùng SQLite Online Backup và `PRAGMA quick_check`; khôi phục vào vùng staging, chỉ đổi sang bản phục hồi sau khi kiểm tra đạt và giữ bản cũ để quay lại.
  - UI hiển thị thời điểm, nơi lưu đã rút gọn, kết quả và bước xử lý bằng tiếng Việt; không đưa backup vào Git/cloud và không hiện đường dẫn hệ thống đầy đủ trong log thường.
  - Test lỗi giữa chừng, backup hỏng, đích hết quyền, restart/readback và không đổi dữ liệu gốc khi thất bại.

- [x] T055 Chạy diễn tập US11 và ghi checklist nghiệm thu môi trường thật (`US11`)
  - Diễn tập kỹ thuật bằng hai tiến trình và thư mục tạm; nếu có hai máy/NAS thật thì kiểm một writer–nhiều reader, backup, restore và mở lại nguồn sau restart.
  - Không có môi trường thật thì giữ Gate A/US11 `OPERATIONAL_PARTIAL`, ghi đúng ba việc admin cần làm tại công ty; không coi test thư mục tạm là pilot NAS thật và không chặn các US khác.

### 10.8. Kiểm toán cuối và bàn giao

- [x] T056 Kiểm toán tiếng Việt trên toàn bộ sáu lát và tăng độ phủ bộ quét (`FR-025`, `SC-014`)
  - Quét tĩnh và smoke trình duyệt các trạng thái bình thường, trống, chờ, thành công, cảnh báo và lỗi của US3, US4, US5, US6, US10, US11.
  - Cố ý đưa lỗi tiếng Anh từ SQLite, parser, filesystem, test runner và thư viện ngoài; đạt khi UI/log/báo cáo người dùng chỉ hiện lời giải thích tiếng Việt dễ hiểu cùng bước xử lý.
  - Bộ quét phải bắt text literal, chuỗi ghép/f-string và nhánh exception trên các file UI đã kích hoạt; không quét mù tên mã, đường dẫn, citation hoặc nội dung tài liệu nguồn ngoại ngữ.

- [x] T057 Cho tác tử kiểm toán độc lập đóng đợt T030–T057 và viết bàn giao có thể tiếp tục (`US3`, `US4`, `US5`, `US6`, `US10`, `US11`)
  - Đối chiếu từng checkbox với code, test, diff và receipt; tác tử vừa sửa nhóm file không được tự chấm nhóm đó. Lỗi được trả lại sửa tối đa hai vòng cho cùng nguyên nhân rồi kiểm toán lại.
  - Chạy Python 3.11, `compileall`, toàn bộ `pytest -q`, CLI audit, import Workspace Chat, kiểm tra tài liệu, quét tiếng Việt, smoke trình duyệt, `git diff --check` và `git diff --cached --check`.
  - Báo riêng `TECHNICAL_PASS` và trạng thái vận hành của từng US; một nhánh thiếu dữ liệu/quyền/mạng thật không hạ kết quả kỹ thuật hoặc chặn nhánh độc lập khác.
  - Bàn giao ghi file đã sửa, migration/rollback, lệnh và mã thoát, test đạt/trượt, rủi ro còn lại, dữ liệu thật không vào Git/cloud và bước nghiệm thu thật kế tiếp. Không commit/push/merge nếu chủ sở hữu chưa ra lệnh riêng.
