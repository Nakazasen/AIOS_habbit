# VÉ: SYNTH-DEEPSEEK-PROTOCOL-HOME (sửa lỗi giao thức khiến đáp án DeepSeek bị chặn oan — cho tầng dự phòng chất lượng)

- Mã vé: `SYNTH-DEEPSEEK-PROTOCOL-HOME`
- Role gợi ý: DEFAULT (OMP — thợ phụ, máy nhà)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-deepseek-protocol-home.md`
- Căn cứ: vé `SYNTH-CLAIMBUDGET-DIAG-HOME` (đã verdict ĐẠT) phát hiện: trong lượt đo DeepSeek, 34/38 câu tưởng như mô hình không được gọi thực ra ĐÃ gọi thành công, nhưng mô hình dồn toàn bộ nội dung vào trường suy luận nội bộ (`reasoning_content`) khiến trường đáp án chính (`content`) rỗng; lớp lọc an toàn cấm lấy nội dung suy luận làm đáp án nên ném ngoại lệ, hệ thống ghi nhầm thành lỗi mạng và rơi về trích xuất cục bộ. DeepSeek hiện là tầng dự phòng chất lượng trong cấu hình tổng hợp đã chốt — nếu lỗi giao thức này còn, mỗi lần tới lượt DeepSeek phục vụ qua giao diện sẽ lại chết oan.

## Việc phải làm

1. **Chẩn đoán chính xác điểm nghẽn giao thức:** xác định trong mã nguồn đường gọi nhà cung cấp: tham số yêu cầu nào đang được gửi (có bật chế độ suy luận hay không, có giới hạn độ dài suy luận không), và điểm nào quyết định "đáp án rỗng" rồi ghi thành lỗi mạng. Trích dẫn file/dòng cụ thể.
2. **Sửa theo hướng giữ nguyên tắc an toàn:** TUYỆT ĐỐI không lấy nội dung suy luận nội bộ làm đáp án. Các hướng được phép, chọn hướng nào phải có bằng chứng chạy thật:
   - Ưu tiên: khi gọi DeepSeek, yêu cầu trả lời trực tiếp (tắt/giới hạn suy luận qua tham số mà nhà cung cấp hỗ trợ chính thức, hoặc chỉ thị hệ thống ép trả lời thẳng vào trường đáp án).
   - Nếu lần gọi đầu vẫn trả đáp án rỗng vì suy luận: thử lại đúng một lần với yêu cầu mạnh hơn; vẫn rỗng thì phân loại là lỗi định dạng riêng (không ghi là lỗi mạng) và chuyển tầng dự phòng ngay.
3. **Đo kiểm chứng trên tập con:** lấy đúng các câu từng dính lỗi đáp án rỗng ở lượt đo DeepSeek cũ (danh sách trong báo cáo chẩn đoán ngân sách / file kết quả thô của lượt đó) chạy lại bằng runner hiện hành với DeepSeek cố định: báo tỉ lệ câu có đáp án tổng hợp được phục vụ trước/sau, số câu qua kiểm định, điểm theo rubric nếu tính được. Khai chi phí thật của lượt đo (kỳ vọng rất nhỏ, trần cứng 0,5 đô — vượt thì dừng và báo).

## Rào cứng

- Không đổi model chính và thứ tự chuỗi dự phòng trong cấu hình; sửa xong khôi phục mọi cấu hình tạm. Không ghi chỉ mục (băm trước/sau khớp). Không merge `main`. Không in bất kỳ ký tự nào của khóa truy cập.
- Nếu chẩn đoán cho thấy hướng sửa phải đổi hành vi ở lớp lọc an toàn (ví dụ nới cấm dùng nội dung suy luận) thì DỪNG ở chẩn đoán + đề xuất, không tự sửa lớp đó.
- Mốc tiến độ tối thiểu 15 phút/lần. Kích thước tệp trong báo cáo lấy bằng lệnh liệt kê tệp thật.
