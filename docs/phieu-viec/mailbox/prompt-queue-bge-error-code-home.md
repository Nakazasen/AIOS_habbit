# VÉ: BGE-ERROR-CODE-HOME (giữ mã lỗi hết-giờ riêng thay vì bị đè thành "bộ đọc sập" + test trực tiếp cho đường tắt sổ)

- Mã vé: `BGE-ERROR-CODE-HOME`
- Role gợi ý: DEFAULT (OMP — thợ phụ, máy nhà)
- Báo cáo: `docs/phieu-viec/ket-qua/bge-error-code-home.md`
- Căn cứ: phát hiện phụ §6 của vé `WORKER-TESTS-DIAG-HOME` (đã verdict ĐẠT): tại nhánh bọc lỗi chung trong `src/aios_habit/rag_v2/bge_subprocess_client.py` (khoảng dòng 663–667), lỗi hết-giờ truy vấn (`bge_worker_query_timeout`) bị đổi mã thành `bge_subprocess_worker_crashed`. Hành vi đóng bộ đọc (fail-closed) là chủ đích và phải giữ nguyên — nhưng nhãn lỗi sai làm mất thông tin chẩn đoán: "hết giờ" khác hẳn "sập tiến trình", và chính sự nhập nhằng nhãn lỗi từng khiến chẩn đoán vụ cold-start đi đường vòng. Vé này chỉ sửa NHÃN lỗi, không đổi hành vi.

## Việc phải làm

1. **Mục chính — giữ mã lỗi hết-giờ:** tại nhánh bọc lỗi của client, nếu nguyên nhân gốc là lỗi hết-giờ (mã dạng `bge_worker_*_timeout`) thì giữ nguyên mã đó khi ném lại; các lỗi khác giữ nguyên hành vi hiện tại (đè thành mã sập + đóng bộ đọc). Hành vi đóng bộ đọc khi có lỗi nghiêm trọng GIỮ NGUYÊN ở cả hai đường.
2. Test cho mục chính: (a) ca hết-giờ → mã lỗi giữ là mã hết-giờ, bộ đọc vẫn đóng đúng fail-closed; (b) ca lỗi không phải hết-giờ → vẫn mã sập như hiện tại. Chạy lại 3 tệp test hạ tầng bộ đọc + các test client liên quan, ghi kết quả thật.
3. **Mục phụ — test trực tiếp cho đường tắt sổ:** bổ sung 1 test khẳng định trực tiếp hành vi của commit `ce6212c`: nguồn có phạm vi `notebook` KHÔNG vào hàng đợi chuẩn bị (được đánh dấu sẵn sàng tức thì), trong khi nguồn `temporary` vẫn vào hàng đợi như thường. Đặt test ở tệp phù hợp nhất theo cấu trúc hiện có.

## Rào cứng

- Chỉ sửa đúng điểm bọc lỗi nêu trên + test; không thay đổi ngưỡng thời gian, không thay đổi hành vi đóng/mở bộ đọc, không nới bất kỳ cổng nào. Không ghi chỉ mục. Không merge `main`.
- Nếu phát hiện mã lỗi hết-giờ đang được nơi khác trong code phân nhánh theo mã `worker_crashed` (phụ thuộc vào việc bị đè), phải khai rõ trong báo cáo TRƯỚC khi sửa và giữ tương thích (ví dụ giữ cả hai thông tin: mã chính là hết-giờ, kèm trường nguyên nhân) — không phá thầm lặng các điểm đọc mã lỗi khác.
- Mốc tiến độ tối thiểu 15 phút/lần. Báo cáo: diff tóm tắt, kết quả test trước/sau.
