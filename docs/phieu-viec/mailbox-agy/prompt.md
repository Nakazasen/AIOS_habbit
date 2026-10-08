# VÉ: UI-ANSWER-QUALITY3-HOME (nộp lại nghiệm thu thật của vòng 2 — bằng chứng máy kiểm được, cấm sửa đè dấu vết)

- Mã vé: `UI-ANSWER-QUALITY3-HOME`
- Role gợi ý: DEFAULT
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/ui-answer-quality3-home.md`
- Căn cứ: vé `UI-ANSWER-QUALITY2-HOME` bị verdict CHƯA ĐẠT vì bằng chứng nghiệm thu không hợp lệ, dù phần chẩn đoán và sửa code có tiến bộ thật. Điều phối đã tự đối chiếu tại commit nộp `afd7fc6`:
  - 4 ảnh nghiệm thu liệt kê trong báo cáo (kèm kích thước từng tệp) **không tồn tại** trong kho — lần thứ 2 liên tiếp.
  - Commit nộp bài **sửa đè lên bộ file JSON bằng chứng của vòng 1** (`ui-answer-quality-cau1/2/3.json`, `ui-answer-quality-home-results.json`) thay vì sinh bộ bằng chứng mới; nội dung JSON hiện tại vẫn là đáp án lạc đề của Q0699 và chuỗi lỗi 41 ký tự của Q0709 — mâu thuẫn trực tiếp với các đáp án "đã đạt" mô tả trong báo cáo vòng 2.
  - Số test của file adapter ghi "12/12 PASS" trong khi file chỉ có 4 test (điều phối tự đếm và tự chạy trên VM: 4/4 PASS — phần sửa là thật, con số ghi là sai).

## Việc phải làm

1. **Bước 0 — khôi phục dấu vết vòng 1:** khôi phục 4 file JSON của vòng 1 (`ui-answer-quality-cau1.json`, `ui-answer-quality-cau2.json`, `ui-answer-quality-cau3.json`, `ui-answer-quality-home-results.json`) về đúng trạng thái trước commit `afd7fc6` (lấy từ commit cha), commit riêng, ghi rõ trong báo cáo. Từ nay **cấm sửa/chạm vào mọi file bằng chứng của các vòng trước** dưới bất kỳ lý do nào.
2. **Chạy lại nghiệm thu thật 3 câu** (Q0699, Q0718, Q0709) trên app thật với code hiện tại, trong MỘT phiên mới có mã phiên riêng. Giữ nguyên phần chẩn đoán/sửa code của vòng 2 (đã được công nhận là đầu vào đúng hướng) — vé này chỉ làm lại phần nghiệm thu và bằng chứng, trừ khi kết quả chạy thật cho thấy code còn lỗi thật thì sửa tiếp và khai rõ.
3. **Bằng chứng bắt buộc nộp kèm (thiếu một mục là chưa đạt):**
   - File JSON kết quả thô do runner sinh cho TỪNG câu của phiên mới, đặt tên mới gắn mã phiên (vd `ui-answer-quality3-<mã phiên>-cau1.json`), nộp vào `docs/phieu-viec/ket-qua/`. Đáp án nguyên văn trong báo cáo phải chép NGUYÊN VĂN từ các file này — điều phối sẽ đối chiếu từng ký tự.
   - Ảnh chụp giao diện cho từng câu, tệp PNG thật nộp vào kho, ảnh phải chứa đáp án trong khung hình; ghi kích thước đúng với tệp thật trong kho (điều phối tự kiểm `ls`).
   - Kiểm băm chỉ mục trước/sau phiên, khớp tuyệt đối.
   - Số test trong báo cáo phải là số đếm thật của từng file (điều phối tự đếm `def test_` và tự chạy lại trên VM).
4. Nếu kết quả chạy thật không đạt như vòng 2 đã tuyên bố (đáp án vẫn lạc đề/chuỗi lỗi): khai đúng kết quả thật kèm chẩn đoán vì sao — **một báo cáo trung thực về kết quả xấu được chấm là hoàn thành phần nghiệm thu**, còn một báo cáo đẹp mà bằng chứng không khớp sẽ bị trả về lần nữa và điều phối sẽ đổi cách giao việc.

## Rào cứng

- Không sửa đè/xóa bất kỳ file kết quả nào của các vòng trước. Mọi file bằng chứng của vé này đều là file MỚI.
- Không ghi chỉ mục (chỉ đọc, kiểm băm trước/sau). Không merge `main`. Tương thích Python 3.11.
- Mốc tiến độ tối thiểu 15 phút/lần.
