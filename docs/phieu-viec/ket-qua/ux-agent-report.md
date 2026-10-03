# Báo cáo vé UX-AGENT-REPORT — Phase A [VM] (backend items 1–2)

Ngày: 2026-10-03 ~14:35 +07. Người làm: Muse (VM). Lane tiếp: [NHÀ] OMP verify trên app thật.

## Tóm tắt

Đã code xong backend cho items 1–2: chat action tạo/sửa báo cáo `.docx` / `.pptx` / `.md`
bằng lệnh lời, sửa file có sẵn **bắt buộc backup trước khi ghi** (khớp SHA mới cho ghi
tiếp), trả file đính kèm ngay trong câu trả lời qua thẻ artifact sẵn có của UI chat.
**37/37 test mới pass**, test liên quan 49/49 pass, `compileall` OK, `cli audit` PASS,
quét tương thích Python 3.11 sạch, không đụng DB/index production, không commit dữ liệu
`local_only`. **Item 3 (UI trong chat) CHƯA code** — phương án UI ở mục 5, chờ user gật.

## 1. Đã code gì (file, hàm)

Nền đã có từ commit `82698a5` (engine `agent_doc_edit`: backup khớp SHA, chặn path
traversal, ops tạo/sửa md/docx/pptx). Vé này nối tiếp, không viết lại:

### Item 1 — Chat action tạo/sửa báo cáo: `src/aios_habit/chat_action_agent_report.py` (mới)

- `parse_report_command(question)` — hiểu lệnh lời dạng **diễn đạt rõ ràng** thành
  `ReportCommand` (xác định, test được trên VM):
  - tạo mới: "tạo báo cáo tuan.md: …", "tạo slide báo cáo tuần" (thiếu tên file thì
    tự đặt `bao-cao-<chủ đề>-<giờ>.md`, thiếu nội dung thì tạo file có tiêu đề);
    nhắc "slide"/"trình chiếu"/"powerpoint" → `.pptx`, "word" → `.docx`, còn lại `.md`.
  - sửa đúng chỗ user chỉ: "thay X thành Y" → `replace`; "thêm vào slide 3: …" →
    `append_to_slide` (theo số thứ tự hoặc theo tiêu đề slide); "thêm vào mục Kết
    luận: …" → `insert_under_heading` (md); "thêm slide …" → `append_slide` (pptx).
  - "lập báo cáo điều tra …" → `decline`, nhường cho action chuyên biệt
    `lap_bao_cao_dieu_tra` (đăng ký trước, ưu tiên cao hơn).
  - lệnh mơ hồ → `clarify`: hỏi lại đúng 1 ý (tên file / cần sửa gì) kèm ví dụ, không đoán mò.
- `run_report_edit(filename, operations, *, create, command, doc_root)` — thực thi qua
  `agent_doc_edit.edit_document`, kiểm tra nhẹ file vừa ghi có mở được không
  (đếm đoạn/slide), ghi log vận hành, trả dict cho UI chat. Lane LLM lúc chạy thật
  gọi trực tiếp hàm này với operations đã phân tích — không qua parser cứng.
- Handler `_handler` — nối vào framework `chat_action` (đăng ký trong
  `BUILTIN_ACTION_MODULES` của `chat_action.py`, sau `chat_action_bao_cao_dieu_tra`).
  Kết quả trả về là thẻ đính kèm: tóm tắt việc đã làm + tên file + tên bản sao lưu
  + metadata `<!-- aios_chat_artifact: {...} -->` (`work_id` dạng `ARE-XXXXXXXX`,
  `work_type="agent_report_edit"`, `result_path`, `checkpoint_path` = file backup) —
  đúng cơ chế thẻ artifact mà `workspace_chat_ui.py` đã dựng sẵn (Xem / Tải về / Hoàn tác).
- Thư mục làm việc: `AIOS_DOC_ROOT` nếu deploy đặt, mặc định `~/AIOS_bao_cao` (tạo khi
  cần) — không ghi vào thư mục repo/app.

### Item 2 — Engine mở rộng: `src/aios_habit/agent_doc_edit.py` (thêm 2 ops)

- `{"op": "append_to_slide", "slide": 3, "text": "..."}` hoặc
  `{"op": "append_to_slide", "slide_title": "...", "text": "..."}` (pptx): thêm đúng
  vào slide user chỉ (số thứ tự 1-based hoặc slide có tiêu đề chứa cụm từ).
- `{"op": "insert_under_heading", "heading": "...", "text": "..."}` (md/txt): chèn
  đúng dưới đề mục, trước đề mục cùng/bậc cao hơn tiếp theo.
- Quy tắc an toàn giữ nguyên: mọi ghi đè file đã tồn tại đều backup trước, backup
  phải khớp SHA-256 với bản gốc mới cho ghi tiếp; sai thì dừng, file gốc giữ nguyên.

### Vòng lặp cải thiện liên tục: `src/aios_habit/agent_report_feedback.py` (mới)

Theo quyết định user 2026-10-03 (mọi tính năng có đủ 3 điểm), ghi `local_cases`,
không ghi kho tri thức:

1. Điểm hứng feedback tại chỗ dùng: `log_report_action(...)` ghi mỗi lần agent
   tạo/sửa vào `local_cases/agent_report_actions.jsonl`.
2. Feedback của user ngay trên kết quả: `record_report_feedback(work_id, user, verdict,
   ...)` — verdict `dung`/`mot_phan`/`sai`; chấm `mot_phan`/`sai` mà thiếu 1 trong 3
   trường (lý do, nguyên nhân thật, nội dung nắn lại) thì **raise `ReportFeedbackError`
   (ValueError)** với thông báo tiếng Việt, không ghi log. Nhận cả tên trường Việt/Anh.
3. Metric đo được + vòng xem lại: `action_metrics()` (tổng số, tỉ lệ thành công, theo
   định dạng/loại), `feedback_metrics()` (tỉ lệ phải sửa lại = redo rate),
   `improvement_overview()` (chia lịch sử làm 2 kỳ, trả `giam_dan` / `khong_giam` /
   `khong_du_du_lieu`).

### Test

- `tests/test_chat_action_agent_report.py` (mới, 23 test): parser (tạo/sửa/decline/
  clarify/đuôi không hỗ trợ), chạy đầu-cuối qua `ChatActionRequest` (tạo md/docx/pptx,
  sửa có backup đúng nội dung gốc, file thiếu → hướng dẫn, `dieu tra` → handler trả
  `None`), thẻ đính kèm có metadata đầy đủ, ưu tiên action điều tra, log + feedback
  nghiêm + metric + xu hướng vòng lặp.
- `tests/test_agent_doc_edit.py` (thêm 4 test): 2 ops mới + giữ nguyên file gốc khi lỗi.

## 2. Cách dùng API (cho OMP verify ở nhà)

```python
import os
os.environ["AIOS_DOC_ROOT"] = r"C:\tmp\ux-agent-report\bao_cao"  # thư mục thử, tránh ghi lung tung
os.environ["AIOS_LOCAL_CASES_DIR"] = r"C:\tmp\ux-agent-report\local_cases"

from aios_habit.chat_action_agent_report import (
    parse_report_command, run_report_edit,
)
from aios_habit.chat_action import ChatActionRequest, dispatch_multi

# Cách 1: qua chat action như app gọi (khuyên dùng khi verify)
outcome = dispatch_multi(ChatActionRequest(
    question="tạo báo cáo tuan.md: line 1 chạy ổn định, tỉ lệ đạt 98%",
    context={"doc_root": r"C:\tmp\ux-agent-report\bao_cao"},
))

# Cách 2: gọi trực tiếp (lane LLM / OMP tự phân tích lệnh)
cmd = parse_report_command("sửa tuan.md: thay 98% thành 99%")
result = run_report_edit(cmd.filename, cmd.operations,
                         create=(cmd.kind == "create"), command="...",
                         doc_root=r"C:\tmp\ux-agent-report\bao_cao")
# result: {"ok", "work_id" ("ARE-..."), "path", "backup", "applied",
#          "sha256", "verify_vi", "error_vi"}

# Cách 3: sửa đúng slide trong pptx có sẵn
result = run_report_edit("sl.pptx",
    [{"op": "append_to_slide", "slide": 3, "text": "Bổ sung số liệu tháng 10."}],
    command="sửa sl.pptx: thêm vào slide 3: ...")
```

Vòng lặp feedback + metric:

```python
from aios_habit.agent_report_feedback import (
    record_report_feedback, action_metrics, feedback_metrics,
    improvement_overview,
)

# User chê kết quả "một phần": thiếu 1 trong 3 trường -> raise ValueError
record_report_feedback("ARE-XXXX", "omp", "mot_phan",
    ly_do="thiếu bảng số liệu",
    nguyen_nhan_that="lệnh không nói rõ cần bảng",
    noi_dung_nan_lai="thêm bảng vào slide 3")

print(action_metrics())       # {"total", "ok", "failed", "success_rate", ...}
print(feedback_metrics())     # {"total", "dung", "mot_phan", "sai", "redo_rate"}
print(improvement_overview()) # {"xu_huong": "giam_dan"|"khong_giam"|"khong_du_du_lieu", ...}
```

## 3. Kết quả kiểm chứng trên VM

- `tests/test_agent_doc_edit.py` + `tests/test_chat_action_agent_report.py`: **37/37 pass**
  (14 engine gồm 4 test ops mới, 23 chat action + feedback/metric).
- Test liên quan cũ (`test_chat_action`, `test_chat_action_multi_intent`,
  `test_chat_action_bao_cao_dieu_tra`, `test_chat_action_phan_hoi`): **49/49 pass** —
  không vỡ action hiện có, không cướp lệnh báo cáo điều tra.
- `compileall` OK; quét syntax Python 3.11 sạch (không f-string nhiều dòng PEP 701,
  không `type` statement; annotation `X | Y` chỉ dùng kèm `from __future__ import
  annotations` như convention repo).
- `cli audit`: **PASS** (`{"status": "PASS", "errors": [], "warnings": []}`).
- `import aios_habit.workspace_chat_app`: được.
- Không file nào ghi vào DB/index production trong test (`AIOS_DOC_ROOT` +
  `AIOS_LOCAL_CASES_DIR` trỏ vào tmp).
- Commit backend: `54e2ba7` trên nhánh `phieu-viec/rag-fix1` (không đụng `main`,
  không force-push).

## 4. Việc OMP verify [NHÀ] (dữ liệu thật, trong app)

1. Trong chat (bật `AIOS_FEATURE_CHAT_ACTION=1`): "tạo báo cáo tuan.docx: …" → file
   `.docx` được tạo trong thư mục báo cáo, mở được bằng Word, nội dung đúng.
2. Chuẩn bị 1 file `.pptx` có sẵn ≥ 3 slide → "sửa <file>: thêm vào slide 2: …" →
   nội dung mới nằm đúng slide 2 (mở PowerPoint kiểm tra), các slide khác nguyên vẹn.
3. Sửa 1 file có sẵn → kiểm tra file `.bak-<giờ>` cùng thư mục: mở được, nội dung
   đúng bản gốc trước khi sửa.
4. "sửa <file>: thay X thành Y" với X không tồn tại → chat báo rõ "Không tìm thấy
   đoạn cần thay", file gốc không đổi.
5. Chấm 1 kết quả "sai" thiếu trường → phải raise `ValueError` tiếng Việt, không ghi
   log; chấm đủ 3 trường → `feedback_metrics()` có `redo_rate` hợp lý.
6. Nếu cả 5 đạt → báo `xong-cho-duyet` cho vé này.

Lưu ý: câu lệnh diễn đạt tự do kiểu "thêm biểu đồ X vào slide 3" (X cần *vẽ mới* biểu
đồ) thuộc lane LLM lúc chạy thật — bản này trả lời hướng dẫn diễn đạt lại, không đoán
mò. Ghi rõ vào báo cáo verify nếu OMP thử trường hợp này.

## 5. Phương án UI đề xuất (CHỜ USER GẬT — chưa code)

Nói ngắn gọn, không kỹ thuật. Hiện trạng: UI chat đã có sẵn thẻ đính kèm cho mỗi file
agent tạo/sửa (3 nút: Xem toàn văn / Tải về / Hoàn tác) — backend vé này cắm đúng vào
thẻ đó nên không cần thêm màn hình mới. Nhưng có 1 lệch: nút "Tải về" hiện tại đọc file
dạng văn bản — với `.docx`/`.pptx` (file nhị phân) thì nút bị vô hiệu hóa, nghĩa là
"mở được ngay" chưa đạt với đúng 2 định dạng user hay dùng nhất.

Phương án A (đề xuất): sửa nút "Tải về" cho nhận biết định dạng — file `.docx`/`.pptx`
thì tải đúng dạng nhị phân để máy tự mở bằng Word/PowerPoint ngay; file `.md` giữ
nguyên xem trước trong thẻ. Nút "Hoàn tác" dùng luôn file sao lưu backend đã tạo
(`checkpoint_path`) để lấy lại bản gốc một chạm.

- Ưu: đúng yêu cầu "trả file đính kèm, mở được ngay"; không thêm nút mới nào vào
  giao diện (đúng định hướng chat-first, 1 ô nhập + 1 vùng trả lời); tận dụng thẻ có sẵn.
- Nhược: vẫn phải tải về máy mới xem/sửa tiếp — chưa sửa trực tiếp trong chat.

Phương án B: xem trước nội dung ngay trong thẻ (docx → trích đoạn văn bản, pptx →
liệt kê tiêu đề từng slide) rồi mới tải.

- Ưu: biết ngay file có đúng ý không mà không cần mở app khác.
- Nhược: chỉ là xem, muốn sửa vẫn phải tải về; tốn thêm code chuyển đổi.

Đề xuất: làm **A trước** (đủ tiêu chí "mở được ngay"), B để dành nếu user thấy cần.
Không code cho đến khi user gật phương án.

## 6. Ghi chú kỹ thuật cho review

- Tái dùng, không viết lại: `agent_doc_edit` (backup/SHA/traversal), framework
  `chat_action` (đăng ký/điều phối/render), thẻ artifact của `workspace_chat_ui`
  (không sửa UI). Parser là lớp xác định cho lệnh diễn đạt rõ; NL tự do do lane LLM
  đảm nhận lúc chạy (`run_report_edit` là điểm cắm).
- Thứ tự đăng ký: `tao_sua_bao_cao` sau `lap_bao_cao_dieu_tra`; cộng thêm guard
  "dieu tra" → handler trả `None` nên `dispatch_multi` bỏ qua, không cướp lệnh.
- Ghi chú trung thực: `tra_cuu_loi_tuong_tu` đăng ký *trước* `lap_bao_cao_dieu_tra`
  trong registry (do `chat_action_bao_cao_dieu_tra` import nó) — có sẵn từ trước vé
  này (kiểm chứng bằng `git stash` trên cây sạch), không đụng vì ngoài scope.
- Dữ liệu vận hành (log action, feedback, metric) nằm ở `local_cases/*.jsonl` —
  theo bài học 2026-10-03, không ghi vào kho tri thức; nhãn nội bộ, không commit.
- Commit: `54e2ba7` (backend) trên nhánh `phieu-viec/rag-fix1`; báo cáo này commit riêng.

## 7. Verify máy nhà (OMP điền)
