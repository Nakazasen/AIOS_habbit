# VÉ: UI-ANSWER-QUALITY-HOME (chẩn đoán + sửa 3 lỗi chất lượng đáp án trên giao diện sau hợp nhất)

- Mã vé: `UI-ANSWER-QUALITY-HOME`
- Role gợi ý: PLAN (truy vết theo trace trước) + DEFAULT khi sửa
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/ui-answer-quality-home.md`
- Căn cứ: vé `UI-SYNTH-UNIFY-POOL-HOME` — phần hợp nhất kỹ thuật đã ĐẠT (adapter về tuyến pool, fallback bật, 0 lỗi chết), nhưng nghiệm thu dùng thật bộc lộ 3 lỗi chất lượng đáp án nghiêm trọng trên phiên `CONV-POOL-B93370`. Điều phối đã tự xem ảnh câu 3 xác nhận lỗi 1.

## 3 hiện tượng phải chẩn đoán tận gốc (theo trace của phiên, không suy luận)

**Lỗi 1 — NẶNG NHẤT: rò rỉ nội dung hệ thống ra giao diện (câu Q0709).** Đáp án hiển thị cho người dùng chứa nguyên văn một phần chỉ dẫn hệ thống (khối "Bạn là trợ lý AI trong Workspace Chat...") và đoạn suy luận tiếng Anh về phân loại an toàn ("User Safety: safe / Response Safety..."). Phải xác định: nội dung này sinh ra ở khâu nào (model của pool trả về cả khối suy luận? một khâu phân loại an toàn bị lấy nhầm kết quả làm đáp án? tầng hiển thị không tách phần suy luận?), vì sao nó qua được mọi lớp kiểm tra để thành tin nhắn trợ lý. Sửa để nội dung hệ thống/suy luận không bao giờ hiển thị thành đáp án; nếu model trả lẫn suy luận thì phải có lớp tách/lọc trước khi lưu message.

**Lỗi 2 — Đáp án bị cắt cụt giữa câu (câu Q0718).** Đáp án chỉ 172 ký tự, dừng giữa câu ("...không phải là nguyên nhân duy nhất gây"). Xác định điểm cắt: giới hạn token của tuyến tổng hợp, tầng lưu/hiển thị cắt chuỗi, hay model dừng sớm. Sửa để đáp án trọn câu hoặc có cơ chế báo rõ khi bị cắt.

**Lỗi 3 — Phạm vi nguồn của phiên làm đáp án sai bản chất (câu Q0699).** Phiên đo dùng cuộc trò chuyện "kế thừa 215 nguồn" và đáp án kết luận "không có tài liệu nào về C7620" — trong khi kho 889 tài liệu có tài liệu đích (các lane đo trên toàn kho lấy được). Chẩn đoán: cơ chế chọn nguồn của cuộc trò chuyện hoạt động thế nào, người dùng phải làm gì trên giao diện để hỏi trên TOÀN KHO, và mặc định hiện tại có phải là cái bẫy khiến hỏi đáp chỉ chạy trên một phần kho không. Phần này CHỈ chẩn đoán + đề xuất (mô hình tài liệu sẽ xử lý ở chuỗi APP-SOURCE-MODEL), không tự ý đổi hành vi chọn nguồn ở vé này — trừ khi nguyên nhân là lỗi hiển thị/ghi nhãn khiến người dùng tưởng đang hỏi toàn kho.

**Việc phụ bắt buộc:** test `tests/test_workspace_chat_router_adapter.py` hiện import trực tiếp gói ngoài `nakazasen_ai_router` nên lỗi thu thập trên máy không cài gói (điều phối kiểm trên VM: ModuleNotFoundError). Sửa test để mock cách ly gói ngoài đúng cách — test phải chạy được trên mọi máy.

## Nghiệm thu lại (tiêu chí ĐẠT)

- Chạy lại đúng 3 câu (Q0699/Q0718/Q0709) trên app thật, phiên mới: đáp án trọn câu, không chứa bất kỳ nội dung hệ thống/suy luận nào, nguồn trích dẫn liên quan câu hỏi. Với Q0699: chạy trong phạm vi toàn kho (theo cách chẩn đoán ở Lỗi 3 chỉ ra) và đáp án phải dựa trên tài liệu C7620 thật.
- Ảnh chụp + đáp án nguyên văn từng câu trong báo cáo; thời gian toàn trình từng câu.
- Cổng repo: compileall, pytest các file liên quan + test mới/sửa, cli audit, import app — PASS, và test adapter chạy được cả khi máy không cài gói ngoài (mô phỏng bằng cách ẩn gói).

## Rào cứng

- Không nới bộ kiểm định tổng hợp; không bịa đáp án cho câu thiếu bằng chứng (đáp án "chưa đủ bằng chứng" đúng chuẩn vẫn chấp nhận — lỗi ở đây là rò rỉ hệ thống, cắt cụt, và phạm vi nguồn gây hiểu nhầm, không phải việc từ chối trả lời).
- Không ghi chỉ mục; kiểm băm chỉ mục trước/sau khi nghiệm thu. Không merge `main`. Tương thích Python 3.11.
- Không ghi bất kỳ ký tự nào của API key vào báo cáo/log.
- Vé dài: mốc tiến độ tối thiểu 15 phút/lần vào `trang-thai.md` mailbox-agy + checkpoint để ca sau resume được.
