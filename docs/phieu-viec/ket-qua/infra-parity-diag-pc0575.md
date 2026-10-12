# Biên bản BB-INFRA-PARITY-01 — thực tế tại máy công ty KDTVN-PC0575

- Vé: `INFRA-PARITY-DIAG-PC0575` (chỉ đọc, không cài đặt, không sửa).
- Máy đo: KDTVN-PC0575, user `tvn183660`, thời điểm `2026-10-12 09:46–10:00 +07`.
- Người đo: thợ opencode. Mọi lệnh đều chỉ đọc.

## Bảng đối chiếu (chuẩn máy nhà | thực tế PC0575 | lệch | đề xuất vé đóng lệch)

| # | Hạng mục | Chuẩn máy nhà | Thực tế PC0575 | Lệch | Đề xuất |
|---|---|---|---|---|---|
| 1a | Kho mã `AIOS_habbit` | remote `Nakazasen/AIOS_habbit`, HEAD lệch sau tip chung `05cacc37` | Có mặt tại `D:\Sandbox\AIOS_habbit`; remote đúng; HEAD thực tế `7e7c3418` | Không lệch (đúng kỳ vọng lệch sau tip chung) | Không cần vé |
| 1b | Kho điều phối `aios-dieu-phoi` | `D:\Sandbox\aios-dieu-phoi`, vault trỏ vào `so-cai` | CHƯA có thư mục local (đã liệt kê `D:\Sandbox`, không thấy) | Đúng kỳ vọng vắng mặt | Vé `OBSIDIAN-SETUP-PC0575` (đã xếp hàng) lo phần clone |
| 1c | Kho khung watcher `agent-mailbox` | Thư mục clone + HEAD/tip mới nhất đã kiểm chứng `b0612345`, có engine `Watch-Project.ps1` đa project | Clone tại `D:\Sandbox\agent-mailbox` (khác tên với `D:\Sandbox\Vong_lap_giao_viec` của máy nhà — đúng kỳ vọng khác tên); local HEAD `0d3d797`; `Watch-Project.ps1` KHÔNG có mặt | LỆCH: local cũ hơn remote (`ls-remote` báo remote HEAD `b0612345`), thiếu engine đa project | Vé nối thông riêng: nâng khung watcher PC0575 lên `b0612345` |
| 2 | Hộp thư và nhà của chúng | Watcher đọc từ kho mã; bản gieo ở kho điều phối (`hop-thu/mailbox-pc0575-*`) | Watcher thực tế trỏ vào `D:\Sandbox\AIOS_habbit` + `docs/phieu-viec/mailbox-pc0575-agy` / `docs/phieu-viec/mailbox-pc0575-opencode`; bản gieo ở kho điều phối chưa ai đọc (kho chưa clone nên chưa kiểm trực tiếp được) | Không lệch | Không cần vé |
| 3 | Watcher/picker từng làn | Task + tiến trình watcher từng làn; config trỏ đúng hộp thư; state/registry NGOÀI cây git; làn desktop chưa tồn tại | Task `MailboxWatcher-opencode` + `MailboxWatcher-agy` đều `Running`, chạy lần cuối `10/12/2026 8:13:11`; task cũ `AIOS_Mailbox_Watcher_pc0575` đã `Disabled`; config dùng `D:\Sandbox\agent-mailbox\config.local.ps1` (có mặt; chỉ ghi tên biến/cờ, không ghi giá trị); log/state chính nằm ở `D:\Sandbox\agent-mailbox` — NGOÀI cây git (đạt); làn desktop: không tiến trình picker nào chạy (đúng kỳ vọng chưa tồn tại) | Lệch nhỏ: còn file `docs/phieu-viec/mailbox/watcher_state_docs_phieu_viec_mailbox_pc0575.json` nằm TRONG cây git và chưa được gitignore (trạng thái cũ `2026-09-29`, không phải của vòng hiện tại) | Vé dọn dẹp nhỏ: thêm watcher_state vào gitignore hoặc chuyển hẳn ra ngoài cây git |
| 4 | Thợ | agy CLI + opencode + Antigravity (có/không, phiên bản; đăng nhập chỉ ghi có/không) | agy `1.3.3` có mặt (watcher gọi `C:\Users\tvn183660\AppData\Local\agy\bin\agy.exe`, model `gemini-3.8-flash-high`); opencode `v2.0.22` có mặt (shim + model `opencode/muse-spark-1.3-contributor-free`, cổng `4096`); Antigravity: thư mục `LOCALAPPDATA\Antigravity` có (`bin` + `staging`) nhưng không tiến trình nào chạy, không thấy dấu hiệu đăng nhập | Không lệch (phần sẵn sàng sâu thuộc vé `ANTIGRAVITY-READY-DIAG-PC0575` riêng) | Không cần vé |
| 5 | Obsidian | Kỳ vọng chưa cài (vé `OBSIDIAN-SETUP-PC0575` xử lý) | Chưa cài (không thấy trong `LOCALAPPDATA`, không có lệnh `obsidian`) | Đúng kỳ vọng | Vé `OBSIDIAN-SETUP-PC0575` (đã xếp hàng) |
| 6 | Quyền GitHub (chỉ đọc, `git ls-remote`) | Thử cả ba kho, ghi OK/lỗi nguyên văn | `AIOS_habbit` OK (`97f14c6`); `aios-dieu-phoi` OK (`213dc8b8` — lần đầu thử kho điều phối riêng từ máy này: THÔNG, kho tồn tại, chỉ chưa clone); `agent-mailbox` OK (`b0612345`) | Không lệch quyền; lệch phiên bản khung như mục 1c | Vé nâng khung như mục 1c |
| 7 | Cấu hình ứng dụng (phần chưa kiểm của BB-CONFIG-PARITY-01) | Liệt kê mục phía PC0575 đang ghi chưa kiểm, kiểm tại máy những mục kiểm được bằng đọc cấu hình (chỉ tên biến/cờ + có/không, không ghi giá trị) | Biên bản `so-cai/Bien-ban-sai-khac-cau-hinh-hai-may.md` nằm ở kho điều phối — máy này chưa clone nên CHƯA đối chiếu được; không ghi giá trị key/bí mật nào (config watcher chỉ xác nhận có biến token, không chép giá trị) | Mở (chờ kho điều phối) | Sau khi `OBSIDIAN-SETUP` clone xong kho điều phối: vé bổ sung đối chiếu BB-CONFIG |

## Phát hiện thêm (ngoài 7 mục, ghi để điều phối xử lý)

- Cơ chế đếm watcher vẫn dựng cờ trên chữ ký cũ: log `watcher-mailbox-pc0575-opencode-opencode.log` lúc `09:37–09:38` leo thang `ESCALATE 4/4` + `FALLBACK-LAUNCH` cho chữ ký `SRC-PROBE-PC0575` trong khi `prompt.md` hiện tại đã là vé `OPEN-DIAG-UI-REMEASURE-PC0575`; lúc `09:49` ghi `GATE-MARK-HONG` vì hạn cho-cong `2026-10-13 17:00` nằm ngoài cửa sổ 24 giờ nên vẫn đếm. Đây là cùng lỗi đọc đã được điều phối phân xử lúc `09:20` — thợ không tự đặt cờ theo, chỉ ghi nhận.
- Vé `QA-CONTEXT-DIAG-PC0575` của làn agy vẫn `dang-lam` (xác nhận nhanh đầu file trạng thái) — vé đo giao diện `OPEN-DIAG` tiếp tục chờ cổng có chủ đích, không liên quan vé hạ tầng này.

## Kết luận

- Biên bản BB-INFRA-PARITY-01 (phần PC0575) KHÉP ở đây với 2 lệch cần vé nối thông: (1) nâng khung `agent-mailbox` lên `b0612345` (thiếu engine `Watch-Project.ps1`); (2) dọn file `watcher_state_*.json` trong cây git ra ngoài hoặc gitignore.
- Cổng bắt buộc của biên bản này cho các giai đoạn đồng bộ/chuyển giao tiếp theo: chờ điều phối duyệt + phát vé nối thông.
