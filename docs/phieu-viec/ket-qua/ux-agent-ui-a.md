# Báo cáo vé UX-AGENT-UI — Phase A [VM] (phương án A đã được user gật)

Ngày: 2026-10-03 ~17:00 +07. Người làm: Muse (VM). Lane tiếp: [NHÀ] OMP verify trên app thật.
User chọn **phương án A** 2026-10-03 ~16:10 (mục 5 của `ux-agent-report.md`):
sửa nút "Tải về" nhận biết định dạng; không thêm nút mới.

## 1. Đã code gì (file, hàm)

**Mới: `src/aios_habit/agent_report_artifact.py`** — logic thuần (không import streamlit):

- `artifact_download_payload(path)` — gói tải cho nút "Tải về":
  `.docx` → bytes + `application/vnd.openxmlformats-officedocument.wordprocessingml.document`;
  `.pptx` → bytes + `.../presentationml.presentation`;
  `.md`/`.txt` → chuỗi văn bản như cũ. File không tồn tại → `ok=False`
  kèm thông báo tiếng Việt (không lộ traceback).
- `restore_report_backup(result_path, checkpoint_path)` — hoàn tác một chạm:
  có file sao lưu → chép đè bản gốc từ sao lưu; tạo mới không có sao lưu →
  xóa file vừa tạo. Từ chối: đường dẫn chứa `..`, sao lưu khác thư mục báo cáo,
  sao lưu không tồn tại, đuôi file ngoài `.docx/.pptx/.md/.txt`. Không raise,
  thông báo tiếng Việt.

**Sửa: `src/aios_habit/workspace_chat_ui.py`** (thẻ đính kèm trong bong bóng chat):

- Nút "Tải về" dùng payload trên: file `.docx`/`.pptx` tải đúng dạng nhị phân
  để máy tự mở bằng Word/PowerPoint ngay; `.md` giữ nguyên xem trước.
- Nút "Xem toàn văn" bị vô hiệu hóa với file nhị phân (trước đây bấm vào là
  vỡ vì đọc nhị phân như chữ); khi mở vẫn hiện dòng hướng dẫn "bấm nút Tải về
  để mở bằng Word/PowerPoint".
- Nút "Hoàn tác" với thẻ loại `agent_report_edit`: dùng luôn file sao lưu
  backend đã tạo (`checkpoint_path`) để lấy lại bản gốc một chạm, không đi
  qua hàng đợi orchestrator (trước đây nút này báo "không tìm thấy checkpoint"
  với thẻ báo cáo). Các loại thẻ khác giữ nguyên luồng cũ.

## 2. Test

`tests/test_agent_report_artifact.py` — **11/11 pass**:

- Tải về: `.md` → text + `text/markdown`; `.docx` → bytes + MIME Word;
  `.pptx` → bytes + MIME PowerPoint; file không có → lỗi tiếng Việt.
- Hoàn tác: sửa có backup → khôi phục đúng từng byte bản gốc; tạo mới không
  backup → xóa file vừa tạo; thiếu sao lưu / sao lưu khác thư mục / `..` /
  đuôi lạ → từ chối, file nguyên vẹn.
- End-to-end với backend thật: tạo `.docx` bằng `run_report_edit` → sửa
  (backend tự backup, SHA đổi) → payload tải về nhận đúng nhị phân → hoàn tác
  → SHA file khớp SHA bản gốc.

## 3. Xác minh tối thiểu (VM)

- `compileall src tests`: OK.
- `pytest` các test liên quan: **đỗ hết** (11 artifact + 39 agent_report +
  39 workspace_chat_ui_copy).
- `cli audit`: `"status": "PASS"`.
- `import aios_habit.workspace_chat_app`: được.
- Không ghi index production; test dùng thư mục tạm.

## 4. OMP cần verify [NHÀ] trên app thật

1. Trong chat, gõ "tạo báo cáo tuan.docx: ..." (nội dung tùy ý): thẻ đính kèm
   hiện 3 nút; bấm **Tải về** → file `.docx` tải về mở được ngay bằng Word,
   nội dung đúng.
2. Gõ "sửa báo cáo tuan.docx: thêm ..." (file đã có): sau khi sửa, bấm
   **Hoàn tác** → file trở về đúng nội dung trước khi sửa (so bằng mắt hoặc SHA).
3. Tạo báo cáo `.md`: nút **Xem toàn văn** vẫn mở/thu gọn được trong thẻ;
   với `.docx`, nút Xem toàn văn **bị mờ** (không bấm được).
4. Ghi SHA index production trước/sau (phải không đổi), rồi `xong-cho-duyet`.

## 5. Giới hạn đã biết (không chặn verify)

- Muốn xem/sửa tiếp vẫn phải tải về máy — chưa sửa trực tiếp trong chat
  (phương án B để dành theo quyết định của user).
