# Ticket hodap-lsu-loi — Thông luồng hỏi đáp LSU + lỗi trên chat (máy công ty)

## Bối cảnh
- App đang chạy LAN bình thường (P5/P5b ĐẠT, fix banner 0/494 ĐẠT).
- User (thợ máy công ty) báo: **chưa hỏi đáp được trên chat** — muốn hỏi đáp về LSU và về lỗi.
- Hiện trạng dữ liệu (theo vé dieutra-banner-0494): sổ "Điều tra lỗi LSU" có 494 notebook sources
  (262 document_id duy nhất), 0 nguồn đang bật, 0/262 có vector trong index đang chạy; ledger trống.

## Việc cần làm

### Pha 1 — Chẩn đoán (chỉ đọc, làm nhanh)
1. Xác định đúng luồng user dùng: chat trong sổ "Điều tra lỗi LSU" (workspace chat).
2. Kiểm tra: index production hiện chạy chứa tri thức gì (có LSU/lỗi không?);
   494 notebook sources ở trạng thái nào (có nội dung? enabled? vector?);
   thử hỏi 2–3 câu mẫu (1 câu LSU, 1 câu về lỗi) và ghi lại CHÍNH XÁC app trả lời gì /
   báo lỗi gì / có dùng nguồn nào không.
3. Kết luận nguyên nhân gốc: thiếu nguồn bật? thiếu vector? hay lỗi khác.

### Pha 2 — Thông luồng (làm theo kết quả Pha 1, OMP tự quyết kỹ thuật)
- Nếu nguyên nhân là nguồn chưa bật / chưa chuẩn bị: bật các nguồn LSU + lỗi cho cuộc
  trò chuyện rồi chạy chuẩn bị. Lưu ý máy CPU-only: ước tính thời gian trước khi chạy,
  chạy nền, không làm sập app đang phục vụ LAN.
- Nếu nguyên nhân khác: sửa đúng lỗi, không đoán mò, không sửa bừa.

## Tiêu chí ĐẠT
- Bộ câu hỏi mẫu (tối thiểu 3 câu LSU + 3 câu về lỗi) đều được trả lời **có căn cứ từ
  tài liệu** (báo cáo ghi rõ từng câu hỏi + đáp án + nguồn trích dẫn), không bịa đáp án.
- App vẫn phục vụ LAN bình thường sau khi xong.

## Cấm
- Không merge `main`. Không force-push.
- Không xóa nguồn/tài liệu nào khi chưa có lệnh user. (User từng bảo xóa vì tưởng trùng
  LSU máy nhà, nhưng vé này là làm cho hỏi đáp ĐƯỢC — nếu chẩn đoán thấy cần dọn thì ghi
  đề xuất vào báo cáo, không tự xóa.)
- Mọi ghi chép chỉ trong thư mục app `D:\Sandbox\AIOS_habbit` và báo cáo GitHub;
  không đụng ổ D máy nhà.

## Báo cáo
`docs/phieu-viec/ket-qua/hodap-lsu-loi.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.

## BỔ SUNG KHẨN — 2026-09-30 14:40 +07 (theo lệnh user, chiến lược đổi)

1. **DỪNG NGAY worker nhúng CPU Phase 2.** Không nhúng tiếp trên PC0575.
   Lý do: chiến lược đã chốt — mọi vector hóa nặng chỉ chạy 1 lần trên máy nhà
   (có GPU), index dùng chung copy sang các máy công ty. Nhúng lại bằng CPU là
   trái ý muốn của user.
2. **Báo về 1 thông tin duy nhất:** `collection_id` mà sổ "Điều tra lỗi LSU"
   đang dùng (đọc từ notebook record; nếu rỗng thì ghi rõ "dùng mặc định tri_thuc").
   Thông tin này để vé máy nhà index đúng collection.
3. Giữ vé ở `dang-lam`. Sau khi index dùng chung từ máy nhà được copy sang,
   vé sẽ tiếp tục ở bước verify hỏi đáp (3 câu LSU + 3 câu lỗi).

## BỔ SUNG 2 — 2026-09-30 ~15:20 +07 (user xác nhận file Drive = index GPU dùng chung)

1. **Bối cảnh mới.** User (đang ở máy công ty PC0575) xác nhận file Drive
   `https://drive.google.com/file/d/1cbydCaMAvO9eBRJg5YhZ1T2tj66C10hv/view?usp=drive_link`
   (`library.sqlite`) chính là index đã vector hóa 1 lần bằng GPU trên máy nhà,
   chứa dữ liệu LSU + điều tra lỗi, để dùng chung cho các máy công ty.
   Muse (VM) **không tải được file này trực tiếp** (Drive từ chối truy cập ẩn danh).
   Vì vậy toàn bộ bước tải + xác minh + thay index làm **ngay trên PC0575**
   (máy đang đăng nhập Google của user). Không nhờ user relay file.
2. **Đường dẫn trên PC0575.**
   - File tạm tải về: `D:\Sandbox\AIOS_habbit\scratch\drive_index_check\library.sqlite`
     (tạo thư mục nếu chưa có; không tải ra ngoài thư mục app).
   - Production hiện tại:
     `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
   - Bản canary 8,5 MB (`..._canary\...`) là đồ thử FIX 5 cũ — **để yên, không đụng**.

### Bước 1 — Tải file Drive (trên PC0575)
- Tải bằng trình duyệt đang đăng nhập Google của user (hoặc Drive Desktop nếu có)
  về đúng đường dẫn file tạm ở trên. Kiểm tra tải xong: dung lượng kỳ vọng ~2,5 GB.

### Bước 2 — Xác minh file tải về (chỉ đọc, CHƯA đụng production)
1. Ghi lại dung lượng byte + SHA256 thực tế.
2. Giá trị **tham chiếu** của index GPU máy nhà:
   SHA `062EC090644FB4EC09D2FB6388F3175E988E48D63061B04E6C27BBED334EF8CA`,
   2.552.659.968 byte. Nếu SHA khớp → chắc chắn là bản GPU.
   **Nếu SHA khác: không được kết luận file sai.** Làm tiếp các mục 3–6;
   nếu integrity/schema/số liệu/fingerprint đều ổn thì vẫn dùng được,
   ghi rõ SHA thực tế vào báo cáo.
3. `PRAGMA integrity_check` trên file tải về → phải `ok` (mở `mode=ro`).
4. Đếm: số document, số chunk, số vector dense/sparse.
   Tham chiếu: 496 document, 133.144 chunk, 107.331 retrievable,
   dense/sparse `107.331/107.331`.
5. Fingerprint vector phải là
   `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`.
   Lệch fingerprint → **dừng**, đặt `cho-muse` (app sẽ coi vector hết hạn).
6. Kiểm tra nội dung có LSU + điều tra lỗi (đếm document/chunk theo tên nguồn
   đã biết: `Tài_liệu_đào_tạo_LSU`, biên bản lỗi các kỳ, bảng mã lỗi...).
   Không đọc sâu nội dung tài liệu vào báo cáo.
7. So số document với production hiện tại (496 document — OMP đo lại con số
   thực tế trên máy rồi so): file Drive phải có số document **≥** production.
   Nếu ít hơn → **DỪNG**, đặt `cho-muse` (nguy cơ thay nhầm bản thiếu dữ liệu,
   làm mất tri thức khác của collection `tri_thuc`).

### Bước 3 — Backup production hiện tại
- Copy production sang
  `.../collections/tri_thuc/library.sqlite.bak-20260930-1530` (cùng thư mục).
- `PRAGMA integrity_check` trên bản backup → `ok` mới được sang Bước 4.

### Bước 4 — Thay index
- Dừng app Streamlit (PID 21016, port 8501).
- Copy file Drive **đã xác minh** đè lên đường dẫn production
  (copy sang tên tạm cùng thư mục rồi rename đè để atomic).
- Khởi động lại app. Kiểm tra: `localhost:8501` và IP LAN → HTTP 200,
  `/_stcore/health` → `ok`.

### Bước 5 — Để app reconcile, KHÔNG nhúng lại
- Để `reconcile_and_enqueue_workspace_chat_sources` tự chạy: nguồn nào đã có
  vector đúng fingerprint sẽ tự thành `ready` qua `_durable_semantic_coverage_ready`
  (đè lên dòng đang park `paused_shared_index_from_home_machine`).
- **Tuyệt đối không bấm "Thử chuẩn bị lại" / "Tiếp tục chuẩn bị".**
  Không sinh tiến trình `bge_subprocess_worker` mới — kiểm tra và ghi vào báo cáo.
- Kiểm tra ledger (`mode=ro`): ghi số `ready` / `failed` / `processing`.

### Bước 6 — Verify hỏi đáp (chỉ đọc)
- Chạy bộ 6 câu hỏi mẫu (L1–L3, E1–E3 trong báo cáo mục 6) trên UI LAN,
  đúng hội thoại `CONV-9C730D76`.
- Ghi lại từng câu hỏi + đáp án + nguồn trích dẫn. Đáp án phải có căn cứ
  từ tài liệu, không bịa.

### Bước 7 — Đóng vé
- Cập nhật `docs/phieu-viec/ket-qua/hodap-lsu-loi.md`: bỏ chữ "TẠM",
  ghi đầy đủ bằng chứng (SHA thực tế, integrity, số document/chunk/vector,
  fingerprint, kết quả 6 câu hỏi + citation, trạng thái app).
- `trang-thai.md` → `xong-cho-duyet`.

## Cấm (bổ sung)
- Không nhúng CPU thêm bất kỳ nguồn nào trong vé này.
- Không merge `main`. Không force-push.
- Không xóa nguồn/tài liệu nào.
- Nếu file Drive có dấu hiệu không đúng (integrity fail, thiếu hẳn LSU/lỗi,
  fingerprint lệch) → dừng, đặt `cho-muse`, không tự xử lý tiếp.
