> **ĐÃ PHÁT HÀNH** — 2026-10-01 ~16:20 +07 (Muse verdict `merge-gpu-dc` **ĐẠT**; 2 delta đã merge vào production PC0575, production chốt SHA `e54c7745…47fe7` (2.842.415.104 B). Theo lệnh user 11:35: chạy lại đúng 6 câu L1–L3/E1–E3 trên toàn collection `tri_thuc`, hội thoại `CONV-9C730D76`.)

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

## TIẾP TỤC — 2026-09-30 ~16:33 +07 (file Drive đã có sẵn, user tải tay)

- User đã tải `library.sqlite` vào đúng
  `D:\Sandbox\AIOS_habbit\scratch\drive_index_check\library.sqlite`
  (xác nhận qua ảnh chụp màn hình 16:31 +07: 2.492.832 KB = 2.552.659.968 byte —
  KHỚP CHÍNH XÁC dung lượng tham chiếu index GPU máy nhà; sửa cuối 9/30/2026 16:17).
- **BỎ QUA Bước 1** (không tải lại, không ghi đè file đã có).
- **Tiếp tục từ Bước 2**: xác minh file (SHA256, `integrity_check`, schema, số
  document/chunk/vector ĐO THỰC TẾ, fingerprint `016c5255…`) → áp gate document
  BỔ SUNG 2.1/2.2 (so số ĐO ĐƯỢC của file Drive với 501 của production;
  < 501 → dừng + `cho-muse` + liệt kê `document_id` thiếu).
- Không đụng production cho tới khi qua hết gate.

## GHI CHÚ MỞ KẸT — 2026-09-30 ~16:05 +07 (trạng thái `cho-muse` lúc 15:58)

### Kẹt 1: OMP không tải được file Drive (Chrome policy)
- OMP đã thử: Chrome/CDP báo `Loading of unpacked extensions is disabled by the
  administrator`; tải ẩn danh và profile junction đều bị chuyển về trang đăng nhập.
  Đã dừng thử, không quay no-op.
- **Cách mở:** USER tự tải bằng Chrome đã đăng nhập Google trên PC0575:
  1. Mở link Drive của file `1cbydCaMAvO9eBRJg5YhZ1T2tj66C10hv`.
  2. Tải `library.sqlite` về, chuyển vào đúng đường dẫn:
     `D:\Sandbox\AIOS_habbit\scratch\drive_index_check\library.sqlite`
     (tạo thư mục nếu chưa có; ổ D còn 9,2 GB — đủ chỗ cho file ~2,5 GB).
- Khi file đã nằm đúng đường dẫn, OMP **tiếp tục từ Bước 2** (xác minh),
  không cần vé mới; đặt `trang-thai.md` lại → `dang-lam` khi tiếp tục.

### Kẹt 2: gate số document — làm rõ
- Con số "496" trong BỔ SUNG 2.1 là **tham chiếu chưa kiểm chứng** (từ máy nhà),
  KHÔNG phải số đo của file Drive (file chưa tải được nên chưa đo).
- Production đo thực tế trên PC0575: **501 `document_id`** riêng biệt.
- Gate đúng: so số document **đo được từ file Drive đã tải** với 501.
  - Nếu ≥ 501 → qua gate, làm tiếp.
  - Nếu < 501 → DỪNG, đặt `cho-muse`, báo cả hai con số + liệt kê `document_id`
    nào của production thiếu trong bản Drive (so theo tập ID, không chỉ đếm số).
    Không tự quyết thay hay không.

## BỔ SUNG 3 — 2026-09-30 17:13 +07 (Muse xử lý cờ `cho-muse` — QUYẾT ĐỊNH KỸ THUẬT)

### 1. Quyết định: KHÔNG thay index production bằng file Drive
- Bằng chứng (báo cáo mục 10): file Drive SHA khớp ghim `062ec090…`, integrity `ok`,
  fingerprint `016c5255…` đúng — NHƯNG chỉ 496 document < production 501, và phủ
  **0/262** `document_id` của sổ "Điều tra lỗi LSU" (production 5/262).
- File Drive là corpus cũ (bản ghim P1.3), không phải index đã nhúng bộ nguồn sổ.
  Thay vào = app mất 5 tài liệu đang ready (676 chunk), tụt về 0 tài liệu ready —
  trái trực tiếp tiêu chí ĐẠT của vé ("user hỏi đáp ĐƯỢC").
- Giữ nguyên production: SHA `5260c043…`, 501 document / 108.007 retrievable,
  fingerprint `016c5255…`.

### 2. Bước tiếp theo: BỎ QUA Bước 3–5, làm thẳng Bước 6
- **BỎ QUA Bước 3 (backup), Bước 4 (thay index), Bước 5 (reconcile)** — không còn
  áp dụng vì không thay index.
- **Bước 6 — verify hỏi đáp (chỉ đọc) trên production hiện tại:**
  - Chạy bộ 6 câu hỏi mẫu (L1–L3, E1–E3 trong báo cáo mục 6) trên UI LAN,
    đúng hội thoại `CONV-9C730D76`.
  - Phạm vi căn cứ: 5 tài liệu đang ready (LSU pptx, 3 xlsx dữ liệu, biên bản lỗi kỳ 2).
  - Ghi lại từng câu hỏi + đáp án + nguồn trích dẫn.
  - Câu nào không trả lời được có căn cứ trong phạm vi hiện tại → ghi rõ
    "không có căn cứ trong 5 tài liệu hiện có", KHÔNG bịa.
- **Bước 7** như cũ: cập nhật báo cáo (bỏ chữ "TẠM", ghi đầy đủ bằng chứng),
  `trang-thai.md` → `xong-cho-duyet`.

### 3. Những việc KHÔNG đụng
- Không nhúng CPU thêm (BỔ SUNG KHẨN vẫn hiệu lực).
- 25 nguồn đang park (`paused_shared_index_from_home_machine`) GIỮ NGUYÊN —
  chờ index dùng chung thật từ máy nhà.
- File Drive trong `scratch/` giữ nguyên làm bằng chứng, không xóa.
- Không bấm "Thử chuẩn bị lại".

### 4. Follow-up (không làm trong vé này)
- Vé máy nhà sau khi LSU-1 + hàng chờ xong: nhúng GPU đúng bộ nguồn sổ
  (262 `document_id`) từ chính dữ liệu đã nhập; verify danh sách nguồn + text
  trích xuất khớp PC0575 TRƯỚC khi tốn công nhúng; rồi copy index sang PC0575
  và chạy verify hỏi đáp full scope.
- Muse sẽ phát hành vé này khi máy nhà xong LSU-1 (poll tự ghi vào hàng chờ).

## BỔ SUNG 4 — 2026-09-30 ~17:46 +07 (xuất text 262 nguồn sổ LSU cho vé GPU máy nhà)

Mục đích: chuẩn bị đầu vào cho vé GPU — xuất (document_id, chunk_text) đúng
262 `document_id` của sổ "Điều tra lỗi LSU" (`NB-E35A7BEE`). Máy nhà sẽ nhúng
ĐÚNG text này (cùng text → cùng document_id), không trích xuất lại, không đánh
cược khớp ID. User không biết file nguồn ở đâu — OMP tự tra từ registry/notebook
của app, không hỏi user.

### Thứ tự mới: Bước 6 → Bước 8 → Bước 9 → Bước 7 (đóng vé)
- Bước 6 giữ nguyên (verify 6 câu hỏi + chẩn đoán worker timeout ở Mốc 2).
- Bước 8 và 9 dưới đây làm SAU Bước 6, TRƯỚC Bước 7.
- Bước 7 (báo cáo + `xong-cho-duyet`) chỉ làm sau khi Bước 9 xong.

### Bước 8 — Tra cứu nguồn và đối chiếu (chỉ đọc, không ghi)
1. Từ registry/notebook của app, lấy danh sách 262 `document_id` + tên nguồn +
   đường dẫn file gốc của sổ.
2. Đối chiếu với production `library.sqlite` (chỉ đọc), chia 3 nhóm:
   - Nhóm A (đã có vector trong index): xuất thẳng chunk text từ index.
   - Nhóm B (chưa có vector, còn file gốc): trích xuất text bằng đúng
     extractor/chunker của app (code hiện tại trên máy này).
   - Nhóm C (không tra được text / mất file gốc): liệt kê, KHÔNG bịa.
3. Báo cáo 3 nhóm (số lượng + danh sách nhóm C nếu có). Nhóm C > 0 → dừng,
   đặt `cho-muse` kèm danh sách thiếu.

### Bước 9 — Trích xuất và đóng gói (chỉ khi nhóm C = 0)
1. Nhóm A: đọc (`document_id`, `source_name`, `chunk_index`, `chunk_text`) từ production.
2. Nhóm B: chạy extractor/chunker → chunk text; kiểm tra `sha256(text)[:24]`
   khớp `document_id` của sổ — lệch thì chuyển sang nhóm C, không xuất bừa.
3. Đóng gói 1 file JSONL, mỗi dòng 1 chunk:
   `{"document_id": "...", "source_name": "...", "chunk_index": n, "text": "..."}`
   Đặt tại `D:\Sandbox\AIOS_habbit\scratch\export_262\text_export.jsonl`
4. Báo cáo: số `document_id` xuất được / 262, tổng số chunk, dung lượng file,
   SHA-256 của file. Thử upload lên Drive AIOS_Data; không được thì để nguyên
   tại `scratch` và báo đường dẫn (user sẽ copy về máy nhà bằng USB).

### Ràng buộc
- Chỉ đọc production và file nguồn; không ghi index, không nhúng vector
  (export không đụng tới BGE worker), không bấm "Thử chuẩn bị lại".
- Không bịa text, không đoán `document_id`.

## BỔ SUNG 5 — 2026-09-30 ~18:20 +07 (LỆNH DỪNG thí nghiệm 600s + vé fix BGE worker)

### 1. DỪNG NGAY
- Kill/dừng tiến trình đang đo worker với timeout 600s. Không chờ hết 10 phút,
  không chạy thêm câu hỏi nào.
- Lý do: chẩn đoán "chậm hay hỏng" làm nhanh bằng đọc log (vài phút), không cần
  chờ 10 phút/câu.

### 2. Chẩn đoán nhanh (chỉ đọc log, không chờ)
- Đọc log của `bge_subprocess_worker` ở lần crash gần nhất (lúc query câu L1):
  worker có khởi động được không, chết ở bước nào?
- Ghi lại NGUYÊN VĂN dòng lỗi vào báo cáo.

### 3. Fix theo đúng bệnh (OMP tự quyết nhánh theo bằng chứng, không hỏi user)
- **Nhánh A — worker HỎNG** (log báo lỗi khởi động: thiếu env, sai đường dẫn model,
  checksum lệch...): sửa đúng nguyên nhân đó → verify worker sống ổn định
  (restart app nếu cần, kiểm tra `/_stcore/health`) → chạy lại 6 câu L1–L3/E1–E3.
- **Nhánh B — worker SỐNG nhưng chậm** (embed được nhưng quá 30s trên CPU):
  đo thời gian query thật 1–2 câu → đặt timeout = số đo thực + margin an toàn
  (OMP tự chọn theo số đo; CẤM để 600s thành mặc định).
  - Nếu timeout chỉnh được bằng env/config → OMP tự chỉnh, restart app, verify.
  - Nếu timeout nằm trong code (`_QUERY_TIMEOUT_SECONDS`) → DỪNG, đặt `cho-muse`,
    báo đúng file/dòng cần sửa. **Không tự sửa code** (luật user chốt từ P2) —
    Muse gửi bản sửa qua commit, OMP `git pull` rồi restart app.
  - Sau đó chạy lại 6 câu L1–L3/E1–E3 trên UI LAN, hội thoại `CONV-9C730D76`.

### 4. Báo cáo + cảnh báo mục tiêu
- Ghi: kết luận chậm/hỏng + nguyên văn lỗi (nếu có) + thời gian thực tế từng câu
  trong 6 câu + timeout cuối cùng đã đặt.
- Nếu thời gian trung bình > 60s/câu → ghi rõ trong báo cáo: mục tiêu
  "tra cứu dưới 1 phút" (Bước 1 lộ trình, `docs/dich-den-du-an.md`) bị đe dọa
  trên máy CPU-only → Muse ra vé tối ưu tiếp.

### 5. Sau fix → tiếp tục đúng thứ tự BỔ SUNG 4
Bước 6 (xong) → Bước 8 → Bước 9 (export 262) → Bước 7 (báo cáo + `xong-cho-duyet`).

### Cấm (nhắc lại)
- Không nhúng CPU, không ghi index, không bấm "Thử chuẩn bị lại".
- Không tự sửa code — cần sửa code thì `cho-muse`.
- Không merge `main`. Không force-push.

### BỔ SUNG 5.1 — 2026-09-30 ~18:25 +07 (đo tách 3 chặng — user chỉ đúng điểm kiến trúc)

User nói đúng: đã có index thì lúc hỏi máy user không cần mạnh. Mỗi câu hỏi chỉ gồm
3 chặng nhẹ: (1) nhúng 1 câu ngắn, (2) search trong index có sẵn, (3) LLM sinh đáp án.
Vì vậy OMP đo TÁCH RIÊNG 3 chặng cho mỗi câu hỏi mẫu, ghi thời gian từng chặng:

- **Chặng 1 — nhúng câu hỏi (BGE worker):** bao nhiêu giây? Kiểm tra worker có bị
  khởi động lạnh mỗi lần hỏi không (nạp lại model ~2,2 GB từ đĩa rồi mới nhúng).
  Nếu có → đây là thủ phạm chính (không phải máy yếu mà là kiến trúc sai):
  fix = giữ worker sống thường trực (warm), nạp model 1 lần duy nhất.
- **Chặng 2 — search trong index:** phải ở mức mili giây đến vài giây (vector đã có
  sẵn, chỉ so sánh). Nếu chặng này chậm → DỪNG, đặt `cho-muse` (index có vấn đề,
  không phải chuyện timeout).
- **Chặng 3 — LLM sinh đáp án:** đang dùng provider/model gì, mất bao nhiêu giây?
  Nếu chặng này ngốn hàng phút vì chạy local trên CPU laptop → ghi rõ vào báo cáo,
  KHÔNG tự đổi provider. Muse ra vé riêng (hướng: gọi API ngoài — DATA_POLICY đã
  được user mở từ 2026-09-28 — hoặc model local nhẹ hơn; user quyết).

Báo cáo cuối ghi đủ: thời gian từng chặng của từng câu + kết luận chặng nào là
nút thắt + đã fix gì.

## BỔ SUNG 6 — 2026-09-30 ~19:20 +07 (LỆNH CƯỠNG CHẾ EXPORT — user sắp về, máy tắt qua đêm)

### 1. DỪNG mọi việc khác NGAY
- Dừng probe 6 câu hỏi đang chạy. Dừng mọi đo đạc, thử timeout.
- Việc set env `AIOS_BGE_QUERY_TIMEOUT` + restart app + chạy lại 6 câu hỏi:
  DỜI SANG MAI khi user đến công ty. Không làm tối nay.

### 2. ƯU TIÊN CAO NHẤT: chạy Bước 8 → Bước 9, xuất `text_export.jsonl` NGAY
- Chạy `step8_groups.py`: tra 262 `document_id`, chia nhóm A/B/C.
- Chạy `step9_export.py`: xuất JSONL ra
  `D:\Sandbox\AIOS_habbit\scratch\export_262\text_export.jsonl`
  (mỗi dòng: `document_id`, `source_name`, `chunk_index`, `text`).
- Nếu nhóm C > 0 (thiếu nguồn): KHÔNG dừng — xuất nhóm A+B có được, ghi rõ
  coverage x/262 + danh sách nhóm C vào báo cáo. (Ngoại lệ cưỡng chế tối nay;
  mai xử lý nhóm C.)
- Nếu script lỗi: sửa nhanh cho chạy được, không refactor, không làm việc khác.

### 3. Báo ngay khi file xong (user đang đợi để về)
- Ghi vào `trang-thai.md` (ghi chú mới nhất) + báo cáo: đường dẫn file, số
  `document_id` xuất được/262, tổng chunk, dung lượng, SHA-256.
- KHÔNG thử upload Drive tối nay — user copy bằng USB trực tiếp cho nhanh.
- Giữ vé ở `dang-lam`, ghi rõ: "tạm dừng qua đêm — mai tiếp Bước 6
  (set env timeout + restart + 6 câu hỏi) rồi Bước 7 đóng vé".

### 4. User tắt máy sau khi copy USB xong
- Sau khi OMP báo file xong và user copy xong: user tắt máy. OMP không cần
  làm gì thêm. Sáng mai máy bật lại, watcher tự tiếp tục vé từ trạng thái này.
