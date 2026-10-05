# VÉ: OMP-EXIT-PROBE-HOME (điều tra vì sao omp -p xong việc không thoát)

- Mã vé: `OMP-EXIT-PROBE-HOME`
- Role OMP gợi ý: DEFAULT (chẩn đoán process, cần chạy thử)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/omp-exit-probe-home.md`

## Bối cảnh

Đêm 05→06/10, process OMP làm xong vé nhưng không thoát, án ngữ vé mới 5,5 tiếng
(vé FEEDBACK-LOOP-HOME phát 22:35, thợ mới chỉ nhặt được sau khi kill tay lúc
~04:00). Watcher đã được vá diệt zombie (kill khi vé im >20 phút + CPU và I/O
đứng yên 3 nhịp poll) — đó là băng gạc. Vé này chữa gốc: tìm vì sao `omp -p`
không thoát sau khi xong việc.

## Việc cần làm

1. Tái hiện: chạy `omp -p` với một việc nhỏ, quan sát sau khi xong việc process
   có thoát không, thoát mã mấy, mất bao lâu. Chạy probe cô lập — KHÔNG đụng
   process thợ đang chạy vé khác.
2. Nếu tái hiện được kẹt: xác định kẹt ở đâu — đang chờ approval/prompt, exit-code
   không trả về, hay tiến trình con giữ session không buông.
3. Đề xuất cách thoát sạch (đề xuất + bằng chứng là đủ cho vé này; code sửa để
   vé sau). Không sửa code watcher/omp trong vé này.
4. Ghi báo cáo `omp-exit-probe-home.md`: cách tái hiện, điểm kẹt, đề xuất.

## Quy ước heartbeat + checkpoint (chuẩn mới, áp mọi vé dài từ nay)

- **Heartbeat**: mỗi bước ghi 1 dòng tiến độ vào mailbox (`ghi_chu` mốc bước).
  Vé dài heartbeat tối thiểu 15 phút/lần — im quá 20 phút + CPU/I/O đứng yên
  là watcher kill theo luật zombie, không kêu oan.
- **Checkpoint/resume**: mỗi bước xong ghi kết quả vào báo cáo nháp ngay —
  kẹt/giết giữa chừng thì người sau đọc tiếp được, không làm lại từ đầu.

## Tiêu chí nghiệm thu

- ĐẠT = tái hiện được (hoặc chứng minh không tái hiện được, kèm bằng chứng) +
  xác định được điểm kẹt + đề xuất cách thoát sạch có cơ sở.
- Không merge `main`.
