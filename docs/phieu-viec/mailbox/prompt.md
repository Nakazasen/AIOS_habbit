# Vé: UX-AGENT-REPORT — agent sửa/tạo báo cáo bằng lời trong chat

Lane: [VM] Muse code+test trên VM → [NHÀ] OMP verify trên app thật. Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (user yêu cầu 2026-10-02 ~22:00)

User muốn: trong chat, ra lệnh bằng lời để agent tạo mới hoặc sửa báo cáo — ví dụ "thêm biểu đồ X vào slide 3", "sửa bảng này thành..." — thay vì mở file sửa tay.

## Việc Muse làm trên VM

1. **Chat action tạo/sửa báo cáo:** hiểu lệnh bằng lời → tạo mới hoặc mở file báo cáo có sẵn → sửa đúng chỗ user chỉ → trả file đính kèm ngay trong câu trả lời, mở được ngay.
2. **Định dạng hỗ trợ tối thiểu:** Word (.docx), PowerPoint (.pptx), Markdown. Mọi thao tác sửa file có sẵn phải backup/phiên bản trước khi ghi — cấm ghi đè mất nội dung cũ.
3. Theo `AGENTS.md` 4.1: phương án UI trình user duyệt trước khi code (ghi vào báo cáo vé, chờ user gật).

## Việc OMP verify [NHÀ]

- Bằng lời trong chat: tạo 1 báo cáo .docx mới từ dữ liệu thật; sửa 1 file .pptx có sẵn (thêm 1 bảng đúng slide user chỉ). File mở được, nội dung đúng chỗ, bản gốc được backup.
- Báo cáo `docs/phieu-viec/ket-qua/ux-agent-report.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT

- Lệnh bằng lời tạo/sửa đúng vị trí trên cả 3 định dạng (docx/pptx/md).
- Sửa file có sẵn luôn có backup; không mất nội dung cũ.
- `compileall` + `pytest` + `cli audit` PASS.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
