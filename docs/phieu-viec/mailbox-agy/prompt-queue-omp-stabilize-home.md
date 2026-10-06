# VÉ: OMP-STABILIZE-HOME (điều tra zombie thợ chính OMP + fix cho ổn định)

- Mã vé: `OMP-STABILIZE-HOME`
- Role OMP gợi ý: DEFAULT (chẩn đoán process + sửa script launcher/watcher, cần chạy thử trên máy thật)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/omp-stabilize-home.md`
- Vé này THAY THẾ `OMP-EXIT-PROBE-HOME` (chưa chạy) — gộp điều tra + fix trong một vé theo lệnh trực tiếp của user.

## Bối cảnh

Đêm 05→06/10, process OMP (`omp -p`, thợ chính) làm xong vé nhưng không thoát,
án ngữ vé mới 5,5 tiếng (vé FEEDBACK-LOOP-HOME phát 22:35, thợ mới chỉ nhặt được
sau khi user kill tay lúc ~04:00, mở worker mới PID 3276). Watcher đã được vá diệt
zombie (kill khi vé im >20 phút + CPU và I/O đứng yên 3 nhịp poll) — đó là băng gạc
chữa cháy. Vé này chữa gốc + gia cố: tìm vì sao `omp -p` không thoát sau khi xong
việc, rồi implement cơ chế đảm bảo thợ luôn thoát sạch.

## Việc cần làm

### Pha 1 — Điều tra nguyên nhân gốc
1. Tái hiện: chạy `omp -p` với một việc nhỏ TRONG PHIÊN PROBE CÔ LẬP — TUYỆT ĐỐI
   KHÔNG đụng process thợ đang chạy vé khác (OMP đang làm SMA-IMPROVE-HOME ở
   mailbox chính, opencode đang làm RT-ALERT-E2E-HOME). Quan sát sau khi xong việc
   process có thoát không, exit code mấy, mất bao lâu.
2. Nếu tái hiện được kẹt: xác định kẹt ở đâu — đang chờ approval/prompt, exit-code
   không trả về, tiến trình con giữ session không buông, hay stdin/stdout còn mở.
3. Ghi đầy đủ cách tái hiện + điểm kẹt vào báo cáo nháp ngay (checkpoint).

### Pha 2 — Fix cho ổn định (chỉ làm sau khi Pha 1 có kết luận chắc chắn)
1. Implement cơ chế đảm bảo thoát sạch ở TẦNG CỦA MÌNH (launcher/watcher) —
   KHÔNG sửa binary OMP (đó là tool ngoài, không thuộc repo).
   Hướng gợi ý (thợ tự chọn phương án tốt nhất, có bằng chứng): phát hiện tín hiệu
   "xong việc" (trạng thái mailbox chuyển xong-cho-duyet/xong) + ép thoát sạch cây
   process nếu quá N phút không tự thoát; hoặc sửa cách gọi `omp -p` (flag/stdin)
   để nó thoát sạch ngay từ đầu.
2. Rào cứng:
   - Mọi thay đổi vào `Watch-Mailbox.ps1` (script chung 3 thợ) phải có cờ/feature-flag,
     test cô lập trước, KHÔNG làm gián đoạn watcher đang chạy của OMP/opencode.
   - KHÔNG đụng file OMP đang làm (`trend_alerts.py` + test của vé SMA-IMPROVE-HOME)
     — luật 1 file 1 đứa.
   - KHÔNG đụng process thợ đang chạy. Không merge `main`. Không secret trong
     báo cáo/log.
3. Test chứng minh: sau fix, chạy probe `omp -p` xong việc thì thoát sạch trong hạn.

### Pha 3 — Báo cáo + bàn giao
- Báo cáo `docs/phieu-viec/ket-qua/omp-stabilize-home.md`: nguyên nhân gốc, cách fix,
  bằng chứng test trước/sau, cách rollback nếu fix gây tác dụng phụ.
- Nếu Pha 1 chứng minh KHÔNG tái hiện được (môi trường đã khác): ghi rõ bằng chứng,
  đề xuất cơ chế giám sát thay vì fix mù — CẤM fix bừa không có căn cứ.

## Quy ước heartbeat + checkpoint (chuẩn mới, áp mọi vé dài từ nay)

- **Heartbeat**: mỗi bước ghi 1 dòng `ghi_chu` mốc bước vào mailbox (`trang-thai.md`),
  tối thiểu 15 phút/lần. Im quá 20 phút + CPU/I/O đứng yên là watcher kill theo luật
  zombie — đã biết luật thì không kêu oan.
- **Checkpoint/resume**: mỗi bước xong ghi kết quả vào báo cáo nháp ngay — kẹt/giết
  giữa chừng thì người sau đọc tiếp được, không làm lại từ đầu.

## Tiêu chí nghiệm thu

- ĐẠT = xác định được nguyên nhân gốc (có bằng chứng tái hiện, hoặc chứng minh không
  tái hiện được kèm bằng chứng) + fix đã implement (hoặc lý do chính đáng không fix)
  + test chứng minh thợ thoát sạch sau khi xong việc.
- Không merge `main`.
