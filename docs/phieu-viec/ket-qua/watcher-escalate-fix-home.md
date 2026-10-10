# Báo cáo kết quả: Sửa lỗi leo thang của watcher hộp thư (Vé WATCHER-ESCALATE-FIX-HOME)

- **Mã vé**: `WATCHER-ESCALATE-FIX-HOME`
- **Thợ thực hiện**: agy máy nhà (`gemini-3.8-flash-high`)
- **Thời gian hoàn thành**: 2026-10-11 00:55 +07
- **Trạng thái**: Hoàn thành 100% các yêu cầu của ticket, sẵn sàng chờ duyệt.

---

## 1. Phân tích nguyên nhân gốc của 3 lỗi

Sau khi đối soát mã nguồn và vết log thực tế lúc 22:51 ngày 10/10/2026 (opencode) và lúc 17:37 ngày 10/10/2026 (agy):

1. **Lỗi 1 (Ghi đè toàn bộ file trạng thái thay vì chèn dòng)**:
   - Trong hàm `Invoke-StallEscalation` cũ, lệnh thay thế chuỗi dùng toán tử PowerShell:
     ```powershell
     $c = $c -replace 'Trạng thái:\s*`[^`]+`', 'Trạng thái: `cho-muse`'
     $c = $c -replace '(?m)^\s*-\s*`?ghi_chu`?\s*:.*$', ("- ``ghi_chu``: " + $reason)
     ```
   - Toán tử `-replace` trong PowerShell mặc định thay thế **toàn cục (global)** mọi vị trí khớp regex trong toàn bộ văn bản. Do đó, tất cả các dòng `Trạng thái: ...` và `ghi_chu: ...` của MỌI khối vé lịch sử từ trước đến nay đều bị ghi đè thành `cho-muse` và chuỗi `$reason`.
   - Thứ tự thực thi cũ sai lầm: script ghi file sửa bẩn trên đĩa TRƯỚC, sau đó mới gọi `git pull --rebase origin $branch`. Khi remote có commit mới, working tree bị dirty khiến rebase bị abort, để lại file sửa dở dang trên đĩa (dẫn đến việc phải tạo stash sự cố 22:51).

2. **Lỗi 2 (Bám tên vé cũ `INDEX-PROD-HOME` thay vì đọc tên vé hiện hành)**:
   - Trong vòng lặp chính của watcher:
     ```powershell
     $ticket = Parse-Field $text 'Ticket hiện tại:\s*([^\r\n]+)'
     ```
   - Khối vé hiện hành của file trạng thái (ví dụ `hop-thu/mailbox-opencode/trang-thai.md`) dùng định dạng `- Vé: `AUDIT-RT-WIRE-HOME-OPENCODE`` (không có chữ `Ticket hiện tại:`).
   - Hàm `Parse-Field` quét toàn bộ file văn bản `$text`. Ở dòng 254 của file trạng thái, có một vé cũ trong quá khứ từng dùng chuỗi `- Ticket hiện tại: `INDEX-PROD-HOME`...`. Do đó regex nhảy cóc xuống dòng 254 để bắt lấy tên vé cũ này và lưu vào state JSON. Khi leo thang, watcher lấy biến lưu cũ `$ticket` mang tên `INDEX-PROD-HOME` để ghi vào reason.

3. **Lỗi 3 (Chèn ký tự BOM vào đầu file khi ghi)**:
   - Script cũ ghi file bằng lệnh:
     ```powershell
     $c | Out-File -LiteralPath $mailboxFile -Encoding utf8
     ```
   - Trong Windows PowerShell 5.1, `Out-File -Encoding utf8` luôn tự động chèn 3 byte UTF-8 BOM (`0xEF 0xBB 0xBF`) vào đầu file markdown.

---

## 2. Kết luận về tính dùng chung mã và các tệp đã sửa

- **Kết luận**: Cả hai watcher `Watch-Mailbox-opencode-dieu-phoi.ps1` và `Watch-Mailbox.ps1` **dùng chung 100% cùng một họ mã nguồn v5** và dùng chung chính xác cùng một hàm `Invoke-StallEscalation` bị lỗi. Do đó cả hai watcher đều cần và đã được sửa đồng bộ trong cùng vé này.
- **Các tệp đã sửa**:
  1. `D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox-opencode-dieu-phoi.ps1` (đã commit vào repo `agent-mailbox` tại commit `8c54e92`).
  2. `D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox.ps1` (đã commit vào repo `agent-mailbox` tại commit `8c54e92`).
- **Nội dung sửa đổi trong mã nguồn watcher**:
  - **Tách khối hiện hành độc lập (`Split-MailboxContent`)**: Tách chính xác khối vé hiện hành (ở đầu file) ra khỏi toàn bộ các khối vé lịch sử (`$restOfFile`). Mọi thao tác đổi trạng thái và chèn ghi chú chỉ được phép thực hiện trên `$currentBlock`.
  - **Đọc tên vé hiện hành tin cậy (`Get-ActiveTicketName`)**: Đọc trực tiếp từ `prompt.md` trong cùng hộp thư (nguồn chính xác nhất về việc đang giao), hoặc đọc từ dòng `- Vé:`, `## Vé hiện tại:`, `- Ticket:` trong khối hiện hành. Tuyệt đối không dùng tên vé cũ lưu từ state hay từ lịch sử.
  - **Quy trình leo thang an toàn và có rollback toàn diện (`Invoke-StallEscalation`)**:
    1. Chạy `git pull --rebase` TRƯỚC khi chạm vào file (khi working tree còn sạch). Nếu pull fail, abort ngay và trả về `$false`, không để lại dirty file.
    2. Đọc file, chuyển dòng `Trạng thái: ...` của khối hiện hành thành `Trạng thái: `cho-muse``, và CHÈN THÊM một dòng `- `ghi_chu`: $reason` ngay dưới dòng trạng thái. Giữ nguyên 100% các dòng ghi chú khác.
    3. Ghép khối hiện hành với các khối lịch sử gốc và ghi ra file bằng UTF-8 không BOM:
       ```powershell
       $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
       [System.IO.File]::WriteAllText($mailboxFile, $newFullContent, $utf8NoBom)
       ```
    4. Git add và git commit. Nếu add/commit fail, tự động checkout hoàn tác.
    5. Git push. Nếu push fail, tự động `git reset --hard HEAD~1` để huỷ commit cục bộ mồ côi, tránh làm tắc nghẽn các lần poll tiếp theo.
  - **Sửa đoạn parse trong vòng lặp chính của watcher**: Chỉ parse `$status`, `$ticket`, `$note`, `$commit` từ `$currentText` (khối hiện hành), không quét toàn file.
  - **Bảo toàn BOM của chính script `.ps1`**: Bản thân file script PowerShell được lưu với UTF-8 BOM (`utf-8-sig`) để thỏa mãn kiểm tra `$__bomOK` tự bảo vệ của script, đồng thời các biểu thức regex được thiết kế trung lập để không bao giờ bị ảnh hưởng bởi lỗi mojibake.

---

## 3. Bằng chứng kiểm chứng leo thang trên bản sao

Kiểm chứng được thực hiện độc lập trên bản sao của cả hai file trạng thái (`docs/phieu-viec/mailbox-agy/trang-thai-test-copy.md` và `D:\Sandbox\aios-dieu-phoi\hop-thu\mailbox-opencode\trang-thai-test-copy.md`).

### 3.1. Diff kiểm chứng trên bản sao hộp thư AGY

```diff
diff --git a/docs/phieu-viec/mailbox-agy/trang-thai.md b/docs/phieu-viec/mailbox-agy/trang-thai-test-copy.md
--- a/docs/phieu-viec/mailbox-agy/trang-thai.md
+++ b/docs/phieu-viec/mailbox-agy/trang-thai-test-copy.md
@@ -2,7 +2,8 @@
 
 ## Vé hiện tại: WATCHER-ESCALATE-FIX-HOME (sửa watcher hộp thư leo thang ghi đè trạng thái)
 
-- Trạng thái: `dang-lam`
+- Trạng thái: `cho-muse`
+- `ghi_chu`: 2026-10-11 00:50 watcher auto-escalate: 4 lan tu mo agy (moi lan cach ~10 phut) ma mailbox khong tien trien. Chuyen sang cho-muse de Muse xu ly. Ticket: WATCHER-ESCALATE-FIX-HOME
 - `ghi_chu`: 2026-10-11 00:44 +07 — **ĐÃ NHẬN VÉ** `WATCHER-ESCALATE-FIX-HOME`: Bắt đầu xử lý 3 lỗi leo thang của watcher (chỉ chèn khối hiện hành, không ghi đè lịch sử, đọc đúng tên vé hiện hành, UTF-8 không BOM, dọn dấu vết giả).
 - `ghi_chu`: 2026-10-11 00:41 +07 — **PHÁT HÀNH CHÍNH THỨC** vé `WATCHER-ESCALATE-FIX-HOME` (prompt.md đã thay bằng nội dung vé đã xếp hàng). Hàng chờ sau vé này đã xếp sẵn theo thứ tự phụ thuộc: (1) `MISSING5-PARSER-FIX-HOME`, (2) `MISSING5-EMBED-COMPLETE-HOME`, (3) `Q0668-BLOCK-FIX-HOME`, (4) `CSV-STRUCTURED-LANE-HOME` — điều phối phát hành lần lượt khi từng vé khép.
```

### 3.2. Diff kiểm chứng trên bản sao hộp thư OPENCODE

```diff
diff --git a/D:\Sandbox\aios-dieu-phoi\hop-thu\mailbox-opencode\trang-thai.md b/D:\Sandbox\aios-dieu-phoi\hop-thu\mailbox-opencode\trang-thai-test-copy.md
--- a/D:\Sandbox\aios-dieu-phoi\hop-thu\mailbox-opencode\trang-thai.md
+++ b/D:\Sandbox\aios-dieu-phoi\hop-thu\mailbox-opencode\trang-thai-test-copy.md
@@ -1,6 +1,7 @@
 # Trạng thái mailbox-opencode (thợ opencode — model free muse-spark-1.3 / space-bunny)
 - Vé: `AUDIT-RT-WIRE-HOME-OPENCODE`
-- Trạng thái: `moi`
+- Trạng thái: `cho-muse`
+- `ghi_chu`: 2026-10-11 00:50 watcher auto-escalate: 4 lan tu mo opencode (moi lan cach ~10 phut) ma mailbox khong tien trien. Chuyen sang cho-muse de Muse xu ly. Ticket: AUDIT-RT-WIRE-HOME-OPENCODE
 - `ghi_chu` (điều phối Muse — PHÁT HÀNH): 2026-10-10 ~22:15 +07 — Phát hành vé kiểm toán mã đường nối cảnh báo realtime (chỉ đọc, không chạy app) theo vai audit của opencode trong luật phân vai 21:01 10/10. Vé đo thời gian mở app `UI-OPEN-TIMING-REMEASURE-HOME-OPENCODE` tạm lùi vào hàng chờ (tệp `prompt-queue-ui-open-timing-remeasure-home-opencode.md` trong cùng hộp thư) vì cổng của nó chưa mở (chờ DATA-INGEST khép) — điều phối phát hành lại ngay khi cổng mở, không mất vé.
 - `bao_cao`: `hop-thu/mailbox-opencode/ket-qua/audit-rt-wire-home-opencode.md`
 - `hang-cho`: 1) `UI-OPEN-TIMING-REMEASURE-HOME-OPENCODE` (chờ cổng DATA-INGEST khép).
```

### 3.3. Kiểm chứng định dạng mã hoá (không chèn BOM)

Kết quả kiểm tra thực tế 3 byte đầu của hai file sau leo thang:
- `docs/phieu-viec/mailbox-agy/trang-thai-test-copy.md`: `has BOM: False`, `first3: 35, 32, 84` (`# T`)
- `D:/Sandbox/aios-dieu-phoi/hop-thu/mailbox-opencode/trang-thai-test-copy.md`: `has BOM: False`, `first3: 35, 32, 84` (`# T`)
- **Kết luận**: File trạng thái được ghi hoàn toàn là UTF-8 thuần túy, không có ký tự BOM.

---

## 4. Dọn dấu vết giả trong `docs/phieu-viec/mailbox-agy/trang-thai.md`

- **Số lượng vết giả trước khi dọn**: Đúng 252 dòng lặp lại của sự cố 17:37 ngày 10/10.
- **Xử lý dọn dẹp**:
  1. Tại khối `SYNTH-RETRIEVAL-GAP-DIAG-HOME` (nơi sự cố bắt đầu): giữ lại đúng 1 dòng đại diện có ghi chú rõ ràng:
     ```markdown
     - `ghi_chu`: 2026-10-10 17:37 watcher auto-escalate: 4 lan tu mo agy (moi lan cach ~10 phut) ma mailbox khong tien trien. Chuyen sang cho-muse de Muse xu ly. Ticket: `SYNTH-CLAIMBUDGET-APPLY-HOME` — áp chính thức nới ngân sách luận điểm cho câu hỏi chẩn đoán/tra cứu + đo xác nhận. Prompt: `docs/phieu-viec/mailbox-agy/prompt.md`. Role: DEFAULT. (dòng đại diện sự cố leo thang 17:37; 251 bản sao ghi đè vào các khối lịch sử đã được dọn theo vé WATCHER-ESCALATE-FIX-HOME)
     ```
  2. Tại các khối lịch sử từ `SYNTH-REMEASURE-STABLE-HOME` trở về cuối file: phục hồi 100% nội dung gốc từ commit `137938b` (trước thời điểm watcher ghi đè lúc commit `f72fe69`).
  3. Toàn bộ 251 dòng dấu vết giả trong các khối lịch sử đã được xoá sạch; các mốc thời gian, số đo, commit SHA và verdict lịch sử của các vé cũ đã được khôi phục nguyên vẹn.
- **Kiểm chứng sau khi dọn**:
  - `Select-String -Pattern "watcher auto-escalate"` trả về đúng **1 dòng duy nhất**.
  - File được bảo toàn mã hoá UTF-8 không BOM (`BOM: False`).
- **Ràng buộc**: Tuyệt đối không đụng vào stash ở clone kho điều phối (giữ nguyên làm bằng chứng sự cố theo lệnh user).

---

## 5. Khuyến nghị thời điểm nạp lại Watcher an toàn

Theo ràng buộc của vé: "Không khởi động lại watcher đang chạy giữa chừng nếu việc đó làm gián đoạn vé đang chạy".
- Hiện tại các watcher trên máy vẫn đang giám sát bình thường các vé đang chạy.
- **Thời điểm an toàn để nạp lại**: Sau khi điều phối duyệt vé `WATCHER-ESCALATE-FIX-HOME` và vé `AUDIT-RT-WIRE-HOME-OPENCODE` chuyển sang trạng thái `xong-cho-duyet`/`moi` tiếp theo, hoặc khi khởi động phiên làm việc mới, tiến hành khởi động lại watcher qua `Install-MailboxTasks.ps1` hoặc chạy lại tiến trình watcher.
