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

## 6. Verify [NHÀ] — CHƯA ĐẠT, dừng `cho-muse`

Ngày: 2026-10-03 18:21–18:32 +07. Người làm: OMP (máy nhà). Không sửa code. Không merge `main`. Không force-push.

### 6.1 Cổng gate

- Watcher tự mở OMP lần 1/4 lúc 18:19:14 (`launchStallCount=1`). Không phải chuỗi 4 lần. Không dừng vì kẹt cổng.
- SHA vé ghi `98a2a65` **không có** trên nhánh. Mã Phase A thật `d5d3250` là tổ tiên của HEAD lúc nhận (`7183fef`). File `src/aios_habit/agent_report_artifact.py` có trên HEAD. Điều kiện mở đã tới.

### 6.2 Cách chạy

- Python `3.11.14` (`.venv`).
- App thử `http://127.0.0.1:8515`, đúng biến môi trường của `RUN_AIOS_WORKSPACE_CHAT.bat`, kể cả `AIOS_FEATURE_CHAT_ACTION=1`. File `.bat` **không** đặt `AIOS_DOC_ROOT`.
- Không đụng app người dùng cổng `8501` (PID `5828` giữ nguyên). Cầu nối `8585` (PID `17204`) không tắt.
- Sổ `E2EUxApp`. Hội thoại mới `Cuộc trò chuyện 03/10 18:28`.
- Gõ đúng câu: `tạo báo cáo tuan.docx: Nội dung verify UX-AGENT-UI. Dòng một để mở bằng Word.` rồi bấm `Hỏi`.

### 6.3 Kết quả

| Mục | Kết quả | Bằng chứng |
|---|---|---|
| 1. Tạo `tuan.docx`, thẻ 3 nút, Tải về mở được bằng Word | **FAIL** | App trả: "Tạo / sửa báo cáo — Chưa làm được: Đường dẫn nằm ngoài thư mục làm việc, từ chối." Không có thẻ đính kèm. Không có file `tuan.docx`. |
| 2. Sửa rồi Hoàn tác | **chưa chạy** | Không có file để sửa. |
| 3. Nút Xem toàn văn của `.md` / nút mờ của `.docx` | **chưa chạy** | Không có thẻ. |
| 4. SHA index production | **không đổi** | Trước và sau cùng `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`, size `2552659968`. |

Thư mục `C:\\Users\\Admin\\AIOS_bao_cao` được tạo lúc 18:29 và **trống** (không có `tuan.docx`).

### 6.4 Nguyên nhân (để Muse vá, OMP không sửa)

Hai chỗ tính thư mục báo cáo khác nhau khi không có `AIOS_DOC_ROOT`:

- `chat_action_agent_report._default_doc_root()` ghi vào `~/AIOS_bao_cao` (`C:\\Users\\Admin\\AIOS_bao_cao`).
- `agent_doc_edit._safe_path()` chỉ cho phép đường dẫn nằm trong `cwd` (`D:\\Sandbox\\AIOS_habbit`).

File đích nằm ngoài `cwd` nên `edit_document` ném đúng câu "Đường dẫn nằm ngoài thư mục làm việc, từ chối." App thật mở bằng `.bat` không đặt `AIOS_DOC_ROOT`, nên mục 1 gãy trước khi có thẻ nút.

### 6.5 Cổng lệnh (không cứu mục 1)

- `compileall src tests`: OK.
- `pytest` `tests/test_agent_report_artifact.py` + `tests/test_chat_action_agent_report.py` + `tests/test_workspace_chat_ui_copy.py`: **52 passed**.
- `cli audit`: `"status": "PASS"`, `warnings` rỗng.
- `import aios_habit.workspace_chat_app`: được.

Test đỗ vì test tự đặt `AIOS_DOC_ROOT` vào thư mục tạm. App người dùng không có biến đó.

### 6.6 Kết luận

Vé **CHƯA ĐẠT**. Dừng `cho-muse`. Không đặt `xong-cho-duyet`. Không sửa code.

Đề xuất Muse: hai hàm phải dùng cùng một gốc thư mục (gốc `~/AIOS_bao_cao` khi không đặt `AIOS_DOC_ROOT`, đúng như báo cáo Phase A). Sau khi vá, OMP verify lại 4 mục trên app 8515.
