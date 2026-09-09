# Goal cho Gemini Flash 3.8: AI phỏng vấn chuyên gia

> **Tài liệu lịch sử**: T000–T080 đã được thực thi theo thiết kế ngày 2026-09-07. Không dùng các chỉ dẫn danh tính/phân quyền, G0–G10 hoặc trạng thái `TECHNICAL_READY` trong file này cho phần sửa hiện tại. Từ ngày 2026-09-09, nguồn thực thi là [plan.md](plan.md), [tasks.md](tasks.md) phần T083–T109 và ADR-0009 bản sửa.

## Prompt khởi chạy để dán vào Gemini

```text
Tiếp tục Goal `010-expert-knowledge-acquisition` trong repo `D:\Sandbox\AIOS_habbit` với vai trò Execution Specialist dùng Gemini Flash 3.8 ở mức suy luận cao.

Đọc và tuân thủ `AGENTS.md`, `CONSTITUTION.md`, `AGENT_RULES.md`, ADR-0007, ADR-0009 và toàn bộ `specs/010-expert-knowledge-acquisition/`, đặc biệt `tasks.md` và `GEMINI_FLASH_3_8_GOAL.md`. Kiểm tra Git trước, bảo toàn mọi thay đổi và file tạm của người dùng. Bắt đầu từ task chưa hoàn thành có ID nhỏ nhất; hiện tại là T000. Tiếp tục tự động trong cổng đang được phép, chạy test và ghi bằng chứng thật sau từng task. Không chỉ báo cáo hoặc lập kế hoạch lại nếu có thể thực hiện an toàn.

Cấm thiết kế thừa: ưu tiên sửa/nâng module hiện có; không tạo framework, app, database, dependency hoặc abstraction để phòng tương lai; không làm trước cổng sau. T000 phải học có chọn lọc từ các repo upstream đã ghi trong `research.md`, pin commit/tag/license và lập ma trận adopt/adapt/reject trước khi code.

Mọi giao diện phải thuần tiếng Việt, dễ hiểu với người không chuyên. Cấm từ kỹ thuật tiếng Anh, traceback, tên engine/provider, tên trạng thái nội bộ và đường dẫn hệ thống trên nhãn, nút, cảnh báo, tiến độ, lỗi hay báo cáo người dùng. Code và token nội bộ vẫn giữ convention hiện có.

Không gửi dữ liệu `local_only`, audio, bản chép lời, secret hoặc dữ liệu nhà máy tới cloud. Không xóa test lỗi và không báo PASS khi chưa chạy. Bộ mặc định G0 đã được khóa trong hồ sơ; không hỏi lại và không dừng `WAITING_OWNER`. Sau mỗi cổng, tự giao audit cho một agent/phiên tách biệt, tự sửa finding rồi tiếp tục cổng sau. Chỉ dùng fixture trong toàn Goal kỹ thuật; thao tác đồng ý ghi âm và duyệt nội dung của người thật thuộc vận hành sau `TECHNICAL_READY`.

Báo tiến độ theo số task/cổng, tách kỹ thuật với pilot vận hành. Trước khi kết thúc mỗi lượt, nêu task đã xong, lệnh và mã thoát, file đã đổi, blocker thật và task kế tiếp.
```

## 1. Mục tiêu duy nhất

Thực hiện trọn feature `010-expert-knowledge-acquisition` theo `tasks.md`, từ T000 đến T080, để AIOS có thể:

1. Tìm khoảng trống tri thức có bằng chứng.
2. Chọn đúng chuyên gia/phạm vi đã xác thực.
3. Chat nhiều vòng và tự hỏi tiếp khi câu trả lời chưa đủ.
4. Ghi âm/chép lời cục bộ khi có đồng ý.
5. Tạo claim, bài học và SOP dạng ứng viên có nguồn.
6. Duyệt, xuất bản có version vào collection và dùng ngay qua retrieval.
7. Đánh giá fine-tune bằng dữ liệu sạch; chỉ mở goal riêng nếu thực sự đủ điều kiện.

Không biến feature thành chatbot chung, nền tảng họp, kho password, hệ quản trị tài liệu mới hoặc pipeline tự fine-tune transcript.

## 1.1. Khóa chống thiết kế thừa

- Dùng lại module và luồng hiện có trước; không tạo framework, app hoặc database mới để “phòng tương lai”.
- Chỉ tạo file/lớp/dependency khi task hiện tại và test chấp nhận chứng minh cần thiết.
- Không triển khai sớm module của cổng sau, không thêm cấu hình/adapter chưa có người dùng thật.
- Nếu hai phương án cùng đạt yêu cầu, chọn phương án ít code, ít dependency và dễ hoàn tác hơn.
- Audit phải đánh dấu `NEEDS_FIX` nếu diff có abstraction, generalization hoặc hạ tầng không phục vụ trực tiếp tiêu chí của feature 010.

## 1.2. Khóa giao diện thuần Việt

Code, schema và log kỹ thuật nội bộ được giữ token theo convention. Riêng mọi nội dung người dùng nhìn thấy phải dùng tiếng Việt đời thường; không bắt người dùng hiểu thuật ngữ kỹ thuật.

| Khái niệm nội bộ | Chữ dùng trên giao diện |
| --- | --- |
| `knowledge gap` | Nội dung còn thiếu hoặc cần làm rõ |
| `scope` | Phạm vi chuyên môn |
| `consent` | Đồng ý ghi âm |
| `transcript` | Bản chép lời |
| `claim` | Nội dung rút ra cần xác nhận |
| `candidate` | Bản nháp chưa được duyệt |
| `conflict` | Nội dung đang mâu thuẫn |
| `publication` | Đưa vào thư viện |
| `retrieval` | Tìm căn cứ trong thư viện |
| `checkpoint` | Điểm có thể tiếp tục |
| `fine-tune` | Huấn luyện bổ sung; chỉ hiện trong màn hình quản trị khi thật sự cần |
| `digest` | Mã kiểm tra nội dung; chỉ hiện khi người dùng mở chi tiết kiểm toán |

Không hiện tên model, engine, provider, cơ sở dữ liệu, trạng thái viết hoa nội bộ, traceback hoặc đường dẫn hệ thống. Lỗi bên ngoài phải được đổi thành: việc gì chưa làm được, dữ liệu có được bảo toàn không và người dùng nên làm gì tiếp theo.

## 2. Phân vai hệ thống và vai trò của Gemini

Hệ thống phân định ranh giới trách nhiệm rõ ràng giữa các tác tử và thành phần:

1. **Gemini Flash 3.8**: Là **Execution Specialist** viết code, test và tài liệu trong repo `AIOS_habbit`. Không tự đưa ra các quyết định kiến trúc nằm ngoài hợp đồng hay tự ý bypass audit.
2. **BGE-M3**: Là mô hình nhúng cục bộ phục vụ tìm kiếm RAG v2, chỉ tạo biểu diễn vector, tìm và xếp hạng các đoạn tài liệu (snippets) liên quan theo độ tương đồng ngữ nghĩa.
3. **AIOS Runtime**: Lớp kiểm soát tất định. AIOS phân tích kết quả retrieval cùng metadata/version/digest và câu hỏi bao phủ để phát hiện các tín hiệu: thiếu nguồn, thiếu thuộc tính bắt buộc, mâu thuẫn hoặc tài liệu lỗi thời (stale). AIOS tự kiểm tra danh tính, scope và grant; mô hình AI không được tự chọn chuyên gia ngoài danh sách thẩm quyền hợp lệ.
4. **C-AGENT qua Brain Gateway**: Tiếp nhận gói tín hiệu và bằng chứng có giới hạn để giải thích lý do khoảng trống tri thức, xếp hạng candidate và đề xuất câu hỏi thích nghi tiếp theo. Cấu hình C-AGENT được quản lý qua Brain Gateway (không hardcode "Sonnet 4" trong source) và lưu model/provider receipt nếu endpoint trả về. Mọi kết quả không có citation hợp lệ đều bị AIOS loại bỏ. Nếu C-AGENT không sẵn sàng, AIOS giữ tín hiệu ở trạng thái candidate, không tự fallback sang cloud và không chặn Goal fixture.
5. **An toàn dữ liệu**: Dữ liệu `local_only` chỉ đi qua đường C-AGENT nội bộ được phép; không tự ý gửi hoặc fallback sang cloud.

Gemini Flash 3.8 (Execution Specialist) được phép:

- Search/đọc code và tài liệu theo lớp của `AGENTS.md`.
- Viết code/test/docs trong allowlist của cổng theo yêu cầu.
- Dùng fixture giả lập, chạy test và ghi receipt trung thực.
- Tự tiếp tục task kế tiếp khi task hiện tại đạt và không vượt cổng.

Gemini Flash 3.8 không được:

- Bỏ qua bộ mặc định, privacy, identity, consent hoặc tự ghi PASS thay auditor tách biệt.
- Dùng dữ liệu/chuyên gia thật trong Goal kỹ thuật; toàn bộ G0–G10 chỉ dùng fixture.
- Tự commit/push, xóa test fail, bỏ cổng hoặc báo PASS từ lời model.
- Gửi `local_only`, audio/transcript thô, secret hoặc dữ liệu nhà máy tới cloud.
- Tự train/fine-tune trong feature 010.

## 3. Tài liệu bắt buộc đọc theo thứ tự

1. `AGENTS.md`
2. `CONSTITUTION.md`
3. `AGENT_RULES.md`
4. `docs/adr/0007-evidence-case-loop-boundaries.md`
5. `docs/adr/0009-expert-interview-and-knowledge-publication-boundary.md`
6. `specs/010-expert-knowledge-acquisition/spec.md`
7. `specs/010-expert-knowledge-acquisition/plan.md`
8. `specs/010-expert-knowledge-acquisition/research.md`
9. `specs/010-expert-knowledge-acquisition/data-model.md`
10. Hai file trong `specs/010-expert-knowledge-acquisition/contracts/`
11. `specs/010-expert-knowledge-acquisition/tasks.md`
12. `specs/010-expert-knowledge-acquisition/quickstart.md`

T000 bắt buộc đọc các repo upstream được liệt kê trong `research.md`, pin commit/tag và ghi rõ `adopt|adapt|reject`. Không đọc rồi copy đại: so capability với code AIOS, license, dependency, test và chi phí cập nhật.

Sau đó chỉ đọc code/test đúng task và file canonical liên quan; không nuốt cả repo.

## 4. Câu lệnh bắt đầu

```powershell
Set-Location D:\Sandbox\AIOS_habbit
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
git status --short --branch
Get-Content .\.specify\feature.json -Encoding UTF8
Get-Content .\specs\010-expert-knowledge-acquisition\tasks.md -Encoding UTF8
```

Nếu `.specify/feature.json` không trỏ tới `specs\\010-expert-knowledge-acquisition`, sửa pointer bằng workflow SpecKit trước khi code. Không xóa hoặc stage thay đổi không thuộc Goal.

## 5. Thuật toán chạy liên tục

Lặp cho tới T080:

1. Chọn task chưa xong có ID nhỏ nhất mà dependency đã đạt.
2. Xác nhận task thuộc cổng đang `ACTIVE`; nếu chưa, dừng ở checkpoint cổng.
3. Search code trước khi thiết kế; ưu tiên nâng module sẵn có.
4. Viết/chỉnh test hợp đồng trước hoặc cùng logic quan trọng.
5. Implement thay đổi nhỏ nhất đủ tiêu chí; không mở abstraction chưa cần.
6. Chạy test trọng điểm, negative test và `git diff --check`.
7. Đọc lại diff, kiểm tra UTF-8/tiếng Việt/privacy và trạng thái Git.
8. Chỉ đánh dấu task `[x]` khi có command + exit code + evidence.
9. Cập nhật Gate Card bằng một dòng receipt; không dán raw data.
10. Tiếp tục task kế tiếp trong cùng cổng mà không hỏi lại.

Kết thúc cổng:

1. Chạy toàn bộ test của cổng.
2. Ghi trạng thái `READY_FOR_INDEPENDENT_AUDIT`, không tự ghi `PASS`.
3. Tự bàn giao cho Audit Specialist ở agent/phiên tách biệt.
4. Nếu audit `PASS`, cập nhật cổng và tự tiếp tục task kế tiếp.
5. Nếu `NEEDS_FIX`, sửa đúng finding rồi audit lại cho tới khi đạt.
6. Nếu môi trường thiếu tài khoản, microphone hoặc runtime tùy chọn, giữ capability đó tắt, hoàn tất contract/fixture và tiếp tục; không hạ chuẩn an toàn.

“Chạy hết một lèo” nghĩa là tự tiếp tục trong phạm vi đã duyệt và qua từng checkpoint; không có nghĩa là tự cấp quyền hoặc bỏ audit.

## 6. Cổng và điều kiện không được vượt

| Cổng | Task | Khóa bắt buộc |
| --- | ---: | --- |
| G0 | T000–T007 | Upstream matrix + bộ mặc định khóa sẵn + ADR accepted + fixture sạch |
| G1 | T008–T015 | verified identity và negative impersonation |
| G2 | T016–T024 | gap có evidence |
| G3 | T025–T029 | plan đúng expert/scope/budget |
| G4 | T030–T038 | chat thích nghi, pause/resume, no loop |
| G5 | T039–T047 | consent + local-only transcription |
| G6 | T048–T053 | claim có source, conflict không tự hòa giải |
| G7 | T054–T059 | SOP/lesson candidate và exact-digest approval |
| G8 | T060–T068 | backup + writer lease + ingest + retrieval receipt |
| G9 | T069–T072 | eligibility report, không training job |
| G10 | T073–T080 | diễn tập fixture + audit agent độc lập + full gates |

## 7. Quy tắc chat thích nghi

C-AGENT qua Brain Gateway trong sản phẩm phải chat tự nhiên, nhưng mỗi câu hỏi tiếp theo cần một `reason` hợp lệ và `trigger_refs`. Ưu tiên hỏi:

- Điều kiện bắt đầu/kết thúc.
- Ngưỡng, đơn vị và cách đo.
- Ngoại lệ và trường hợp không áp dụng.
- Ví dụ thật và phản ví dụ.
- Dấu hiệu phân biệt hai nguyên nhân gần nhau.
- Mức chắc chắn và nguồn có thể kiểm tra.
- Điểm mâu thuẫn với tài liệu/chuyên gia trước.

Không ép trả lời. `Không biết`, `không chắc`, `bỏ qua`, `tạm dừng`, `kết thúc` là đáp án hợp lệ. Không tự bịa phần thiếu để kết thúc rubric.

## 8. Quy tắc học và fine-tune

### Học dùng ngay

Sau G8, artifact đã duyệt được ingest vào collection và truy xuất từ câu hỏi tiếp theo. Đây là vòng học chính của AIOS: có citation, version, revoke và supersede.

### Fine-tune

G9 đo baseline để lưu bằng chứng nhưng luôn kết luận `NOT_APPLICABLE` trong feature 010. Nếu tương lai muốn huấn luyện bổ sung, tạo Goal riêng gồm dataset manifest, quyền sử dụng, train/dev/holdout, metric, canary và rollback.

Không fine-tune để “ghi nhớ” SOP/sự thật. Không dùng raw audio/transcript. Không xem số lượng ít mẫu là lý do train sớm.

## 9. Báo cáo tiến độ

Mỗi checkpoint báo ngắn:

```text
Cổng: Gx
Task: Txxx–Tyyy
Đã đạt: ...
Evidence: lệnh, exit code, số test, digest fixture
Chưa đạt/blocker: ...
File đã đổi: ...
Working tree: ...
Finding audit hoặc giới hạn môi trường: ...
```

Không dùng phần trăm nếu chưa định nghĩa mẫu số. Có thể báo `n/81 task`, `x/11 cổng` và tách `kỹ thuật` khỏi `pilot vận hành`.

## 10. Định nghĩa hoàn tất Goal

Goal chỉ hoàn tất khi:

- T000–T080 đều `[x]` với evidence.
- SC-001–SC-010 trong `spec.md` đạt.
- 2 danh tính chuyên gia fixture/2 scope/3 phiên/5 gap và 5 đơn vị tri thức + 1 quy trình đã được diễn tập tự động.
- Candidate/conflicted/revoked không lọt vào retrieval thường.
- Audio/transcript thô không rò và critical tokens được người có quyền xác nhận.
- Full quality gate, E2E Windows và audit độc lập đạt.
- ADR, Architecture, Roadmap, Handover và sổ LSU phản ánh đúng trạng thái.
- Fine-tune có kết luận trung thực `NOT_APPLICABLE` hoặc được tách thành Goal mới; không còn training side effect trong feature 010.

Kết thúc Goal là `TECHNICAL_READY`: code, fixture, contract, E2E và audit đã đạt. Việc người thật đồng ý ghi âm, trả lời và duyệt nội dung là vận hành sản phẩm, không phải phase phát triển hoặc lý do dừng Goal.
