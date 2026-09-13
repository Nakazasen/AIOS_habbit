# Làm việc thông minh như Grokbot

Tài liệu này trả lời ba câu hỏi:

1. Vì sao Grokbot càng làm việc càng có vẻ thông minh, và nguyên lý (spec) thật sự là gì.
2. Hệ trợ lý người dùng trong `AIOS_habbit` đã có nền để làm điều đó chưa.
3. Nếu muốn áp dụng, phát triển cốt lõi theo hướng nào — trên nền hiện có, không dựng hệ nhớ mới song song.

Đây là **bản ý hướng / phân tích**. Chưa phải đặc tả đã duyệt, chưa phải lệnh viết mã. Hiến chương, kiến trúc và lộ trình vẫn là `CONSTITUTION.md`, `ARCHITECTURE.md`, `ROADMAP.md`. Nếu hướng này được xác nhận, lúc đó mới cập nhật các file canonical và mới được phép lập kế hoạch triển khai.

---

## 1. Câu trả lời thẳng

Grokbot **không** thông minh hơn vì mô hình bên trong bị huấn luyện lại sau mỗi việc bạn làm. Não của nó không đổi.

Nó trông thông minh hơn vì **bàn làm việc của nó đổi**. Mỗi phiên làm việc để lại:

- ghi chú đã lọc (sự kiện, quyết định, quy ước);
- luật nhà (hiến chương, quy tắc dự án);
- phiếu hướng dẫn cho việc lặp lại (kỹ năng / playbook);
- bài học từ lần bị sửa (quy tắc hành vi có độ tin);
- người thư ký tự ghi sổ, không đợi bạn bảo “nhớ giúp”;
- người thủ thư tìm đúng tờ giấy **trước khi** bắt đầu việc mới.

Phiên sau không bắt đầu từ số không. Cùng một mô hình, nhưng ngồi trước một bàn đã có giấy tờ đúng việc.

Đó là toàn bộ “phép màu”. Không có phép màu thứ hai.

AIOS Habit **đã viết đúng triết lý này trong hiến chương** từ đầu: không lưu hội thoại, lưu tri thức; không lưu câu chữ, lưu quy luật; không lưu suy đoán, chỉ lưu bằng chứng. Phần còn thiếu không phải ý tưởng. Phần còn thiếu là **vòng vận hành khép kín trên trợ lý người dùng** (Workspace Chat): ghi nhận → lọc → xác nhận → nhớ → nhắc lại đúng lúc → bị sửa thì thành bài học → định kỳ dọn bàn.

---

## 2. Giải thích đời thường

Hình dung một thư ký mới vào xưởng.

Ngày đầu, thư ký thông minh nhưng chưa biết xưởng. Hỏi lại mọi thứ. Làm xong quên. Ngày mai hỏi lại từ đầu.

Grokbot không trở thành thợ máy giỏi hơn. Grokbot trở thành **thư ký biết giữ sổ**.

### 2.1 Bốn loại giấy trên bàn

| Loại giấy | Đời thường | Việc nó làm |
|---|---|---|
| Luật nhà | Tờ dán tường: “không mang giấy mật ra khỏi xưởng” | Đọc **mọi buổi**, không phải tìm |
| Ghi chú sự kiện | “Hôm qua ta chọn cách A vì B” | Nhắc lại khi việc liên quan |
| Phiếu việc lặp | “Khi nhận máy NG, làm theo 7 bước này” | Chỉ lấy ra khi đúng loại việc |
| Bài học bị sửa | “Đừng bao giờ điền sẵn tên Windows vào ô người quyết định” | Càng bị nhắc lại càng đậm; lâu không dùng thì nhạt |

Người không chuyên chỉ cần nhớ một câu: **luật nhà luôn có, ghi chú thì tìm khi cần, phiếu việc thì chỉ mở đúng lúc, bài học thì phải được chính người dùng xác nhận.**

### 2.2 Việc thư ký làm, không phải việc “não học”

Mỗi buổi làm việc, Grokbot làm bốn động tác, gần như vô hình:

1. **Ghi sổ lúc đang làm** — không đợi bạn nói “nhớ giúp”. Kết thúc buổi, có bản tóm những gì đáng giữ.
2. **Sáng hôm sau mở sổ trước khi làm** — không bắt đầu nói rồi mới nhớ ra.
3. **Khi bạn sửa** — không xin lỗi rồi quên. Rút thành một câu luật: “lần sau, trong tình huống này, làm X, vì nếu không thì Y”.
4. **Thỉnh thoảng dọn bàn** — gộp mảnh vụn thành chủ đề, bỏ trùng, ghi chú cũ bị đánh dấu “hãy kiểm tra lại, có thể đã lỗi thời”.

Bạn cảm thấy nó “hiểu mình hơn” vì bốn động tác đó, không vì mô hình đã thay đổi.

### 2.3 Điều Grokbot cố ý không làm

- Không nuốt nguyên buổi trò chuyện làm trí nhớ. Trò chuyện thô chỉ là nguồn tạm.
- Không coi mọi câu AI nói là sự thật. Phần tự ghi lúc kết thúc buổi chỉ là siêu dữ liệu (chủ đề, số lượt). Phần giàu hơn phải được bạn (hoặc một lượt tóm có kiểm soát) đưa vào sổ.
- Không nhồi toàn bộ sổ vào đầu mỗi lần nói. Chỉ lấy vài tờ **liên quan**, đủ điểm, đủ mới.
- Không giữ mãi mọi mảnh. Có quên, có dọn, có độ tin giảm theo thời gian với nhật ký phiên.
- Không khóa trí nhớ trong một nhà cung cấp AI. Sổ là tệp người đọc được (Markdown), có thể mở bằng tay, xóa bằng tay, mang sang AI khác.

Ba điểm cuối trùng khít hiến chương AIOS. Điểm AIOS **khắt khe hơn** Grokbot: ứng viên chưa có bằng chứng không được dùng như sự thật. Đó là lợi thế sản phẩm, không phải rào cản. Bản AIOS của “càng làm càng thông minh” phải giữ cổng này.

---

## 3. Spec nguyên lý Grokbot

Phần này là bản rút nguyên lý, không phải sao chép mã nguồn Grok. Grok Bot (trên mây / Cursor) và Grok Build (máy này) khác chỗ cất sổ, nhưng **cùng một họ cơ chế**. Khi tài liệu nói “Grokbot”, ý là họ cơ chế đó.

### 3.1 Tách não và bàn

- **Não** = mô hình ngôn ngữ. Thay được. Không chứa sự thật lâu dài của bạn.
- **Bàn** = luật + trí nhớ + phiếu việc + bài học + chỉ mục tìm. Ở lại khi đổi não.

Nếu trí nhớ nằm trong “bộ nhớ nội bộ của một AI”, mất AI là mất người. Hiến chương AIOS đã cấm điều này.

### 3.2 Mười hai nguyên lý

**P1. Ghi nhận tự động, tốn rẻ.**
Quan sát phiên, ý định câu hỏi, công cụ đã dùng, ranh giới phiên. Không gọi mô hình cho phần này. Tắt được. Không nhét bí mật.

**P2. Hai loại trí nhớ bền, không trộn.**
- **Sự kiện / quyết định**: “đã chọn X vì Y”, gắn tệp hoặc nguồn.
- **Quy luật hành vi (bài học)**: “khi tình huống T, luôn/không bao giờ làm X, vì hậu quả Z”. Có độ tin. Lặp lại cùng một câu thì độ tin tăng. Lâu không dùng thì giảm.
Sự kiện không phải quy luật. Quy luật không phải câu chuyện.

**P3. Nhắc trước khi làm, không nhắc sau khi nói.**
Lượt đầu của phiên (và sau khi cắt ngữ cảnh cũ) phải **tìm** trí nhớ liên quan rồi mới trả lời. Kỷ luật này quan trọng hơn dung lượng sổ. Sổ đầy mà không mở thì bằng không có sổ.

**P4. Luật nhà luôn nạp, trí nhớ thì tìm.**
Hiến chương / `AGENTS.md` / quy tắc dự án đi vào mọi phiên. Trí nhớ công việc **không** được nhồi cả kho. Tìm theo từ khóa + nghĩa gần + liên kết khái niệm, lấy ít, đủ điểm.

**P5. Phiếu việc (kỹ năng) chỉ mở khi đúng việc.**
Việc lặp lại được viết thành hướng dẫn từng bước, quá cụ thể để nhét vào luật nhà, quá dài để gõ lại mỗi lần. Hệ thống chỉ đọc phiếu khi việc hiện tại khớp. Đây là “giỏi nghề” chứ không phải “nhớ chuyện”.

**P6. Sửa của người dùng thành bài học, không thành đoạn kể.**
“Lần sau đừng làm X” phải được chưng thành một câu mệnh lệnh + tình huống kích hoạt + hậu quả. Không lưu nguyên vụ. Lần sau, trước việc cùng loại, bài học được nhắc lại — nhưng **không được đè lên chỉ dẫn hiện tại của người dùng**.

**P7. Phiên có thể nối, không bắt đầu mù.**
Mỗi phiên có ranh giới, tóm tắt, câu hỏi còn treo. Phiên mới có thể nhận lại: “đang dở việc gì, câu nào chưa trả lời, bước tiếp theo là gì”.

**P8. Nén và dọn, không để sổ phình thành rác.**
Tóm giàu khi sắp cắt ngữ cảnh hoặc khi buổi làm việc có quyết định. Định kỳ gom mảnh thành chủ đề, bỏ trùng. Nhật ký phiên cũ bị giảm điểm theo thời gian. Trí nhớ đã được người dùng chăm sóc thì không bị giảm điểm kiểu đó, nhưng khi đã cũ vẫn gắn nhãn “hãy kiểm tra hiện trạng”.

**P9. Tìm hỗn hợp, không chỉ một cách.**
Từ khóa (BM25 / FTS) + gần nghĩa (vector, nếu có) + nở theo liên kết khái niệm. Không có mô hình nhúng thì vẫn tìm được bằng chữ. MMR để kết quả không trùng ý. Điểm nguồn có trọng số (sổ dự án / sổ chung / nhật ký phiên).

**P10. Quên là quyền, không phải lỗi.**
Người dùng xem được sổ, sửa được tệp, xóa được mục, tắt được trí nhớ giữa phiên. Sổ không phải hộp đen.

**P11. Chứng cứ và nguồn gốc.**
Ghi chú tốt có: nội dung, khái niệm để tìm lại, tệp/nguồn, tầm quan trọng, thời điểm, phiên. Bài học có tình huống kích hoạt. Grokbot gắn phiên với lần ghi mã. AIOS phải khắt khe hơn: đơn vị trí nhớ đã xác nhận bắt buộc có bằng chứng.

**P12. Học cái bàn, không chỉ học nội dung.**
Ngoài nhớ việc, Grokbot còn nhìn lại dấu vết phiên để chỉnh **chính bộ phiếu việc**: việc nào bạn gõ đi gõ lại thì thành phiếu mới; phiếu nào không bao giờ dùng thì đề xuất cất; phiếu lệch thì sửa. Đây là lớp meta. Với trợ lý xưởng của AIOS, lớp tương ứng là: quy trình người dùng lặp lại phải thành phiếu việc của **họ**, không phải phiếu việc của lập trình viên.

### 3.3 Vòng vận hành (spec vòng)

```text
Bắt đầu việc
    → nạp luật nhà
    → tìm trí nhớ / bài học / phiếu việc liên quan
    → làm việc
    → ghi nhận tự động (rẻ, không gọi mô hình)
    → khi có quyết định: ghi sự kiện (kèm lý do)
    → khi bị sửa: ghi bài học (một câu luật)
    → khi buổi có giá trị: tóm giàu có kiểm soát
Kết thúc / cắt ngữ cảnh
    → giữ siêu dữ liệu phiên
    → câu hỏi còn treo đi cùng phiên sau
Định kỳ
    → dọn bàn (gộp chủ đề, bỏ trùng, đánh dấu cũ)
    → (tùy chọn) nhìn dấu vết để chỉnh phiếu việc
Người dùng
    → xem / sửa / quên / tắt
```

Thiếu **một** mắt xích thì cảm giác “càng làm càng thông minh” gãy. Sổ không tìm = vô dụng. Tìm mà không ghi = không lớn. Ghi mà không lọc = thành rác. Lọc mà không có cổng người dùng = AI tự bịa “sự thật về bạn”.

### 3.4 Phân tầng độ tin — điểm AIOS phải giữ chặt hơn Grokbot

Grokbot cho phép:

- tự ghi siêu dữ liệu phiên (không gọi mô hình);
- bạn nói “nhớ cái này” thì ghi vào sổ Markdown;
- tóm giàu bằng mô hình khi `/flush` hoặc dọn bàn.

AIOS, theo hiến chương, thêm cổng:

```text
Nguồn thô → Bản ghi bằng chứng → Quy luật đã trích → Bộ nhớ đã xác thực → Gói xuất
```

Ứng viên chưa xác nhận chỉ được là `candidate`. Đầu ra AI không phải bằng chứng nếu không có nguồn. Do đó bản AIOS **không** được sao nguyên “tự nhồi tóm tắt mô hình vào sổ rồi lần sau coi là sự thật”.

Cách đúng: Grokbot cho **nhịp** (khi nào ghi, khi nào nhắc, khi nào dọn). AIOS cho **cổng** (cái gì được phép vào sổ sự thật). Hai thứ cộng, không thay nhau.

---

## 4. Trợ lý người dùng của project này đang ở đâu

Sứ mệnh sản phẩm đã viết sẵn vòng mong muốn:

```text
Vụ việc → Bằng chứng → Bản đồ → Hành động → Học hỏi → Bộ nhớ
```

Định vị: hệ điều hành trí nhớ công việc cá nhân, ưu tiên cục bộ. Không phải chatbot RAG. Không phải sao lưu chat.

Vậy nền **có**, nhưng đang nằm ở **nhiều ngăn**, chưa thành một vòng trên Workspace Chat.

### 4.1 Những gì đã có — đây là vốn, không phải chỗ trống

**Luật nhà (P4, một phần).**
`CONSTITUTION.md`, `AGENT_RULES.md`, `AGENTS.md`, ADR-0009. Rất mạnh cho **tác tử viết mã**. Trợ lý Workspace Chat thì lời hệ thống hiện tại gần như trắng: “chỉ dùng câu hỏi và nguồn trong request này”. Luật nhà của **người dùng xưởng** chưa được nạp vào trợ lý.

**Kho bộ nhớ Phase 0 (P2, P11).**
`05_memory_vault/` với đúng các ngăn Grokbot cần: nhận diện, hành vi, ngôn ngữ, quy trình, tri thức dự án, bài học, mẫu quyết định. Kiểu `MemoryUnit` đã có trạng thái `draft | needs_evidence | verified | deprecated | rejected`, bắt buộc bằng chứng khi `verified`, chỉ bản đã xác nhận mới được xuất. CLI `memory add/list/export/validate` đã có. `extraction.py` tạo ứng viên từ nguồn. **Nhưng đây là kho Phase 0**: Workspace Chat runtime **không đọc** kho này trước khi trả lời.

**Thẻ học việc (P2, P6, gần P5).**
`SeniorLearningCard` trong `src/aios_habit/learning_models.py` đã có đúng các ô một bài học Grokbot cần: bài học tái sử dụng, mẫu nhận ra, áp dụng khi, không áp dụng khi, lần sau kiểm tra gì trước, từ khóa tìm, câu trả lời hữu ích. Có cổng `draft | reviewed | confirmed`. `case_prompt.py` đã biết nhét thẻ vào gói prompt **khi có hồ sơ vụ**. US3 trên lộ trình (“Học từ bài học đã xác nhận”) đã có hợp đồng kiểm thử `tests/test_case_knowledge_lessons.py`. **Chưa phải vòng mặc định của mọi câu hỏi Workspace Chat.**

**Hồ sơ vụ và bài học vụ.**
`workspace_cases.sqlite`, `CaseLesson` (ứng viên → duyệt → thu hồi), “Lưu vào hồ sơ” không sao chép hội thoại thô — đúng hiến chương. Đây là chỗ cất **việc đã xảy ra**, chưa phải chỗ **nhắc trước khi hỏi**.

**Goal 010 — phỏng vấn chuyên gia (P1 một phần, P10 một phần, P11 mạnh).**
Luồng bốn chặng: chọn thư viện → phỏng vấn → kiểm tra bản nháp → xác nhận và đưa vào thư viện. `DecisionRecord` (tên, máy, thời điểm, độ tin, căn cứ, nguồn, trách nhiệm). Artifact `sop` / `lesson`. Dữ liệu thô `local_only`. Thư viện chỉ nhận bản đã xác nhận. ADR-0009 khóa ranh giới. Đây là đường **ghi có người chịu trách nhiệm** — bản AIOS của “nhớ giúp”, khắt khe hơn `/remember` của Grokbot. Cờ `expert_knowledge_acquisition` vẫn tắt mặc định cho đến khi có walkthrough người không chuyên. Fine-tune bị cấm trong Goal 010 — đúng P1: trí nhớ không phải huấn luyện lại não.

**Thư viện hỏi–đáp (`library.sqlite`).**
Kho tài liệu đã xác nhận, FTS, cắt đoạn chồng lấn, gói bằng chứng. Đây là **sổ tài liệu**, không phải sổ làm việc của người dùng. Chat, audio, bản chép lời thô không vào đây — đúng.

**RAG v2.**
Nền truy xuất (parser, FTS/BM25, hybrid, rerank, gói bằng chứng) đã có code. Hồ sơ sản xuất `bge_m3_hybrid` đang `rolled_back`. Không được tuyên bố RAG sản xuất. NotebookLM vẫn hơn trên corpus thật. P9 của Grokbot **có nền kỹ thuật**, chưa phải nền vận hành ổn.

**Quan sát cải tiến truy xuất.**
`agent_learning.py`: ứng viên `semantic_failure` / `lexical_insufficiency`, băm ngữ cảnh, đếm lần lặp, promote khi có bằng chứng. Đây là P1+P2 **cho máy tìm kiếm**, không phải cho trí nhớ người dùng. Mẫu “ứng viên → duyệt → promote, cấm nhét prompt thô” thì nên **tái sử dụng**.

**Phiếu việc phác.**
`WorkflowCard`, `domain_playbooks.py`. Mỏng. Chưa kích hoạt theo loại việc trên trợ lý.

**Bản đồ / đồ thị.**
Evidence Graph, `visual_map_builder`, `worklens_semantic_map`. Lộ trình giai đoạn 7 đã ghi “Bản đồ luồng / đồ thị tri thức”. Chưa phải lớp nở khái niệm lúc nhắc trí nhớ.

**Quyền riêng tư local-first.**
Chặn cloud, nhãn `local_only`, không commit dữ liệu thật. Bắt buộc giữ khi thêm vòng nhớ.

### 4.2 Đối chiếu từng nguyên lý

| Nguyên lý Grokbot | Nền AIOS hôm nay | Mức |
|---|---|---|
| P1 Ghi nhận tự động rẻ | Có lưu chat cục bộ; Goal 010 ghi có chủ đích; không có “kết thúc buổi → siêu dữ liệu phiên” cho trợ lý | Thiếu nhịp |
| P2 Sự kiện ≠ bài học | Có đủ kiểu: `MemoryUnit`, `SeniorLearningCard`, artifact SOP/lesson, `CaseLesson` | Có schema, loãng ngăn |
| P3 Nhắc trước khi làm | Prompt Workspace Chat: chỉ nguồn trong request. Không tìm `memory_vault` / thẻ học / bài học đã xác nhận trước câu trả lời thường | **Mắt xích gãy** |
| P4 Luật nhà luôn nạp | Mạnh với agent mã. Yếu với trợ lý xưởng | Lệch đối tượng |
| P5 Phiếu việc theo việc | Playbook/domain mỏng; SOP Goal 010 nằm thư viện tài liệu | Thiếu kích hoạt |
| P6 Sửa → bài học | Có form quyết định lúc xuất bản; không có “câu vừa rồi sai, lần sau luôn X” ngay trên chat | Thiếu vòng sửa |
| P7 Nối phiên | Chỉ lịch sử hội thoại **trong** cuộc hiện tại | Thiếu handoff |
| P8 Dọn bàn | Có extract ứng viên; không có gom chủ đề / giảm điểm theo thời gian / nhãn cũ | Thiếu |
| P9 Tìm hỗn hợp | RAG v2 có nền, sản xuất rollback; trí nhớ công việc chưa đi qua chỉ mục đó | Nền kỹ thuật, chưa nối |
| P10 Quên / xem / sửa sổ | Goal 010 thu hồi xuất bản; không có “xem trí nhớ của tôi / quên điều này” trên trợ lý | Thiếu UX |
| P11 Chứng cứ | Mạnh nhất trong repo | Vốn cốt lõi |
| P12 Học cái bàn | `agent_learning` chỉ cho retrieval; không học phiếu việc của người dùng từ dấu vết | Chưa mở |

### 4.3 Kết luận nền — có hay chưa?

**Có nền triết lý, có mô hình dữ liệu, có đường ghi có trách nhiệm, có kho tài liệu, có hồ sơ vụ.**

**Chưa có hệ “càng làm càng thông minh” trên trợ lý người dùng.**

Lý do gãy, nói một câu: **trợ lý trả lời từ tài liệu được chọn trong lượt đó, không trả lời từ người dùng đã sống cùng hệ thống qua nhiều ngày.**

Ba hệ đang đứng cạnh nhau, chưa thành một người:

1. **Thư viện tài liệu** — hỏi đáp giấy tờ (RAG).
2. **Kho trí nhớ Phase 0 + thẻ học + bài học vụ** — đúng hình dạng Grokbot, gần như không được nhắc lúc hỏi thường.
3. **Goal 010** — cửa có người gác để đưa kinh nghiệm vào thư viện; chưa phải nhịp hằng ngày.

Lộ trình đã **đặt tên** đúng các tầng còn thiếu, và chưa mở như sản phẩm:

- Giai đoạn 6 — Bộ nhớ vụ việc theo quy mô.
- Giai đoạn 7 — Bản đồ luồng / đồ thị tri thức.
- Giai đoạn 8 — Học tập chuyên sâu / hệ điều hành cá nhân.

Hướng này **không phải tính năng mới lạ**. Nó là cách làm cho giai đoạn 6–8 **thành vòng**, thay vì thêm một chatbot nhớ lung tung.

---

## 5. Ý hướng cốt lõi khi áp dụng

### 5.1 Một câu khóa

> Trợ lý người dùng của AIOS phải có **bàn làm việc riêng của người dùng**, chạy đúng nhịp Grokbot, đi qua **cổng bằng chứng** của AIOS, tái sử dụng kho đã có, không cài thêm não, không cài thêm máy chủ trí nhớ lạ.

### 5.2 Bốn điều cấm khi phát triển

1. **Không** đưa `agentmemory` / Grok memory / một SQLite trí nhớ thứ tư vào runtime. Repo đã có `library.sqlite`, `workspace_cases.sqlite`, `memory_units.jsonl`, `learning_cards.jsonl`. Thêm kho mới khi chưa chỉ ra task hiện tại cần nó là vi phạm luật chống thiết kế quá mức.
2. **Không** tự nhồi tóm tắt mô hình vào trí nhớ đã xác nhận. Tóm tắt mô hình tối đa thành `candidate`. Người dùng (hoặc cổng Goal 010 / US3) mới nâng lên `verified` / `confirmed`.
3. **Không** đợi RAG sản xuất đạt NotebookLM rồi mới làm vòng nhớ. Vòng nhớ của người dùng **khác** truy xuất tài liệu. Có thể bắt đầu bằng FTS trên đơn vị trí nhớ đã xác nhận.
4. **Không** gọi đây là Goal 010 close-out, không đụng `RUN_AIOS_WORKSPACE_CHAT.bat`, không bật lại `bge_m3_hybrid` nhân tiện, không đồng bộ `ARCHITECTURE.md` / `ROADMAP.md` cho đến khi hướng này được xác nhận.

### 5.3 Ánh xạ Grokbot → AIOS (dùng lại, không copy)

| Bộ phận Grokbot | Chỗ AIOS dùng lại | Việc phải thêm (ý, chưa phải mã) |
|---|---|---|
| `MEMORY.md` toàn cục / theo dự án | `MemoryUnit` + ngăn `05_memory_vault/` | Runtime đọc/ghi qua cổng trạng thái; UX tiếng Việt “sổ việc của tôi” |
| Bài học độ tin | `SeniorLearningCard` + artifact `lesson` + `CaseLesson` | Một lối vào; nhắc trước câu hỏi khi `applies_when` khớp; độ tin tăng khi cùng bài học được xác nhận lại |
| Skill / phiếu việc | `WorkflowCard` + SOP đã xuất bản trong thư viện | Kích hoạt theo loại việc (điều tra line, NG máy, lập SOP…), không nhồi mọi SOP vào prompt |
| Hook ghi nhận | Chat store + kết thúc cuộc / lưu hồ sơ | Siêu dữ liệu phiên: chủ đề, nguồn đã dùng, hồ sơ liên quan — **không** nguyên văn chat |
| `/remember` | Goal 010 “đưa vào thư viện” + lệnh đời thường “nhớ giúp” | Đường ngắn: nhớ sự kiện/quy ước; đường dài: phỏng vấn khi là SOP/bài học xuất bản |
| `/forget` | Thu hồi Goal 010 + `deprecated` trên `MemoryUnit` | Nút/câu “quên điều này”, xem sổ, sửa sổ |
| First-turn injection | `build_workspace_ai_prompt` | Trước nguồn tài liệu: thêm khối “sổ việc đã xác nhận” (ít mục, đủ điểm, có nguồn). Nguồn tài liệu vẫn như hiện tại |
| `/flush` + `/dream` | `extraction.py` + ứng viên `agent_learning` (mẫu cổng) | Lượt tóm buổi → `candidate`; định kỳ gộp chủ đề trong vault; không auto-verified |
| Handoff phiên | `conversation_id` + hồ sơ vụ | “Việc đang dở / câu còn treo / bước tiếp” khi mở lại |
| Hybrid search | RAG v2 FTS (+ vector khi được phép) | Chỉ mục **đơn vị trí nhớ**, tách chỉ mục tài liệu. Không trộn chat thô |
| `/learn` (meta) | US3 + dấu vết hồ sơ đã `confirmed` | Sau này: phiếu việc của người dùng từ vụ lặp. Không mở sớm |

### 5.4 Hình vòng trên trợ lý (đời thường)

Người dùng hỏi trên Workspace Chat.

1. Hệ thống nạp luật nhà của trợ lý xưởng (tiếng Việt, không bịa, không lộ `local_only`, không coi nguồn là lệnh).
2. Hệ thống **tìm** vài mục trí nhớ / bài học / phiếu việc đã xác nhận, liên quan câu hỏi — đây là “sáng nay mở sổ”.
3. Hệ thống tìm tài liệu thư viện như hiện tại (gói bằng chứng).
4. Trả lời: dựa sổ việc + giấy tờ, nói rõ cái nào là quy ước đã nhớ, cái nào là tài liệu, cái nào chưa đủ.
5. Người dùng có thể:
   - “nhớ cái này” → ứng viên, mời xác nhận;
   - “sai, lần sau luôn/không bao giờ …” → bài học ứng viên;
   - “quên cái này”;
   - “lưu vào hồ sơ” như hiện tại.
6. Kết thúc cuộc có giá trị: siêu dữ liệu phiên được ghi rẻ; nếu có quyết định, mời xác nhận một dòng, không nuốt cả chat.
7. Định kỳ (không chặn người dùng): gộp ứng viên trùng, đánh dấu mục lâu không đụng.

Người không chuyên thấy bốn câu, không thấy mười hai nguyên lý:

- “Trợ lý nhớ việc tôi đã chốt.”
- “Trợ lý nhắc đúng lúc, không nhắc linh tinh.”
- “Tôi xem và xóa được những gì nó nhớ.”
- “Nó không bịa thành quy định của xưởng.”

---

## 6. Cách phát triển cốt lõi — thứ tự lát cắt

Không làm một lần. Mỗi lát phải có nghiệm thu đời thường. Audit độc lập với implement. Không tự PASS.

### Lát 0 — Khóa ý hướng (lát này)

- File này.
- Chờ xác nhận: có đi theo vòng “nhắc trước — ghi có cổng — dọn bàn” trên nền hiện có không.
- Nếu có: cập nhật `ARCHITECTURE.md` (một mục vòng trí nhớ trợ lý) và `ROADMAP.md` (gắn giai đoạn 6–8), mở speckit specify **một** hạng mục, không mở song song Goal 010.

### Lát 1 — Nhắc trước khi trả lời (P3 + P4)

Mục tiêu: câu hỏi mới được trả lời kèm **sổ việc đã xác nhận**, không chỉ tài liệu.

Phạm vi tối thiểu:

- Một lối đọc thống nhất: `MemoryUnit` `verified` + `SeniorLearningCard` `confirmed` + `CaseLesson` đã duyệt + artifact Goal 010 đã xuất bản và chưa thu hồi.
- Tìm FTS/từ khóa trên trường đã có (`statement`, `reusable_lesson`, `retrieval_keywords`, `applies_when`). Chưa cần vector.
- `build_workspace_ai_prompt` thêm khối “Sổ việc đã xác nhận”, giới hạn số mục, mỗi mục có nguồn/bằng chứng. Không để nội dung sổ thành lệnh hệ thống (cùng kỷ luật với khối NGUỒN hiện tại).
- Nếu không có mục nào đủ điểm: im lặng, không bịa “tôi nhớ là…”.

Nghiệm thu: cùng một quy ước đã xác nhận hôm qua, hôm nay hỏi việc liên quan thì trợ lý nhắc đúng quy ước và chỉ ra nguồn. Tắt sổ thì hành vi về như hiện tại.

**Đây là lát tạo cảm giác Grokbot.** Làm trước. Rẻ. Không đụng RAG sản xuất.

### Lát 2 — Nhớ có chủ đích trên chat (P2 + P10 + Goal 010 đường ngắn)

Mục tiêu: người dùng nói “nhớ giúp / đây là quy ước của tôi” mà không phải đi hết bốn chặng phỏng vấn.

- Tạo `candidate` `MemoryUnit` hoặc thẻ học `draft`, tiếng Việt, hiện cho người dùng xác nhận một màn hình ngắn (tên ghi nhận, độ tin, căn cứ).
- SOP / bài học xuất bản vào thư viện **vẫn đi Goal 010**. Không mở đường tắt làm hỏng ADR-0009.
- “Xem sổ việc” / “quên điều này” trên giao diện tiếng Việt. Quên = `deprecated` hoặc thu hồi, không xóa dấu vết quyết định.

Nghiệm thu: người không chuyên nhớ một quy ước, hỏi lại ngày hôm sau thấy nó; bảo quên thì không còn bị nhắc.

### Lát 3 — Sửa thành bài học (P6)

Mục tiêu: “câu vừa rồi sai” không trôi.

- Khi người dùng sửa câu trả lời hoặc nói “lần sau luôn/không bao giờ”, chưng **một** câu luật + tình huống + hậu quả.
- Lưu `candidate`; cùng nội dung được xác nhận lại thì tăng độ tin (đếm), không nhân bản.
- Lát 1 phải nhắc bài học này trước việc cùng loại.
- Bài học **không** được đè chỉ dẫn mới của người dùng trong phiên hiện tại.

Nghiệm thu: bị sửa một lần, việc cùng loại lần sau không mắc lại; người dùng đổi ý thì bài học cũ không thắng.

### Lát 4 — Kết thúc buổi và nối phiên (P1 + P7)

Mục tiêu: không mất “đang dở gì”.

- Khi đóng cuộc / lưu hồ sơ: ghi siêu dữ liệu (chủ đề, số lượt, hồ sơ, nguồn) — không gọi mô hình, không nhét transcript vào vault.
- Nếu buổi có quyết định: mời xác nhận 1–3 dòng ứng viên (flush có người gác).
- Mở lại: hiện “việc đang dở / câu còn treo / bước gợi ý”, bám `conversation_id` và hồ sơ vụ.

Nghiệm thu: tắt máy, mở lại, trợ lý không hỏi từ đầu những gì đã chốt; chat thô vẫn không nằm trong thư viện.

### Lát 5 — Dọn bàn (P8)

Mục tiêu: sổ không thành bãi rác.

- Định kỳ gộp ứng viên trùng, giữ bản có bằng chứng hơn.
- Nhật ký phiên giảm điểm theo thời gian; mục `verified` không tự giảm nhưng hiện “nên kiểm tra lại” khi quá cũ.
- Không tự xóa. Không tự verified.

Nghiệm thu: sau nhiều buổi, tìm vẫn ra việc đúng, không bị mười bản sao cùng một quy ước.

### Lát 6 — Phiếu việc theo việc (P5), sau khi lát 1–3 sống

- Lấy SOP đã xuất bản + `WorkflowCard`.
- Kích hoạt khi câu hỏi/hồ sơ khớp loại việc (ví dụ điều tra line, NG, lập SOP).
- Một phiếu / một lúc. Không nhồi thư viện SOP.

Gắn US4/US5 trên lộ trình, không dựng agent mới.

### Lát 7 — Tìm sâu hơn (P9) và bản đồ (giai đoạn 7)

- Chỉ khi lát 1 đã đo được: FTS trí nhớ thiếu nghĩa gần.
- Dùng lại nền RAG v2 trên **đơn vị trí nhớ**, không mở vector DB mới, không gửi nhúng cloud với `local_only`.
- Đồ thị khái niệm chỉ khi FTS + cửa sổ truy xuất vẫn thiếu — đúng bài học cũ: đừng nhảy GraphRAG trước khi nới cửa sổ.

### Lát 8 — Học cái bàn (P12 / giai đoạn 8)

- Chỉ khi đã có dấu vết hồ sơ `confirmed` và phiếu việc thật sự được dùng.
- Đầu ra: đề xuất phiếu việc mới từ vụ lặp, người dùng duyệt. Không fine-tune. Không xóa phiếu chỉ vì “ít hit”.

---

## 7. Rủi ro nếu làm sai (đã thấy trên chính Grokbot và trên repo này)

- **Sổ không mở** — Grokbot cũng vô dụng nếu tắt injection. AIOS hôm nay đang ở trạng thái đó với vault.
- **Sổ nuốt chat** — trái hiến chương, trái ADR-0009, trái “Lưu vào hồ sơ”.
- **Sổ tin lời AI** — tạo quy định xưởng ma. Cổng `candidate` tồn tại đúng vì rủi ro này.
- **Sổ thứ tư** — thêm DB/framework “cho giống Grok” làm loãng, audit `NEEDS_FIX`.
- **Trộn tài liệu và trí nhớ người** — người dùng không phân biệt “giấy máy” với “quy ước của tôi”. Prompt phải tách khối.
- **Nhắc linh tinh** — không có ngưỡng điểm / `applies_when` thì trợ lý thành người hay kể chuyện cũ.
- **Làm nhân tiện RAG sản xuất** — Goal 010 và RAG rollback đã cảnh báo: không tự PASS, không walkthrough thì không tuyên bố thông minh hơn.

---

## 8. Việc cần người dùng xác nhận trước khi viết mã

1. Có chốt hướng: **nhịp Grokbot + cổng bằng chứng AIOS + tái sử dụng kho hiện có**?
2. Lát đầu tiên có phải **Lát 1 (nhắc trước khi trả lời)** không, hay muốn bắt đầu từ “nhớ giúp” (Lát 2)?
3. Sổ việc của trợ lý sống ở đâu là nguồn sự thật duy nhất khi các ngăn trùng ý: vault Phase 0, thẻ học, `CaseLesson`, hay artifact Goal 010? (Khuyến nghị: **một lớp đọc**, nhiều ngăn ghi như hiện tại, không merge vật lý ngay.)
4. Có cập nhật `ARCHITECTURE.md` / `ROADMAP.md` sau khi chốt không? (Hiến chương bắt buộc nếu đây thành hành vi hệ thống.)

Chưa xác nhận thì dừng ở file này. Không viết mã, không thêm dependency, không đụng cờ Goal 010, không đụng RAG sản xuất.

---

## 9. Tóm tắt một trang

Grokbot càng làm càng “hiểu” vì nó **giữ bàn**, không vì nó **đổi não**: luật nhà luôn có, sổ được mở trước khi làm, phiếu việc mở đúng lúc, lần bị sửa thành luật, buổi làm việc được ghi rẻ rồi dọn, người dùng xem và quên được.

AIOS đã thiết kế đúng bàn đó từ hiến chương, vault, thẻ học, hồ sơ vụ và Goal 010. Trợ lý Workspace Chat **chưa ngồi vào bàn**: nó hỏi đáp giấy tờ trong lượt hiện tại.

Muốn trợ lý của người dùng thông minh dần như Grokbot: **khép vòng trên nền đã có**, bắt đầu bằng “nhắc trước khi trả lời”, rồi “nhớ / quên có người gác”, rồi “sửa thành bài học”, rồi “nối phiên và dọn bàn”. Không cài não mới. Không cài sổ mới. Không bỏ cổng bằng chứng.
