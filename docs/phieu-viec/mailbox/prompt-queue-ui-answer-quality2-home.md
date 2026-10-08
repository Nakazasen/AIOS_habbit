# VÉ: UI-ANSWER-QUALITY2-HOME (sửa chất lượng đáp án vòng 2 — chỉ phát hành sau khi có kết luận INDEX-HASH-DRIFT-TRACE)

- Mã vé: `UI-ANSWER-QUALITY2-HOME`
- Role gợi ý: PLAN + DEFAULT
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/ui-answer-quality2-home.md`
- Căn cứ: vé `UI-ANSWER-QUALITY-HOME` vòng 1 — chẩn đoán 3 lỗi đã tốt (bridge lấy reasoning_content làm đáp án; max_tokens 700 bị reasoning ăn hết; phạm vi nguồn theo sổ), code sửa đúng hướng, NHƯNG nghiệm thu vòng 1 không đạt: cả 3 câu đều rơi về fallback (0 câu qua pool), Q0699 ra khung rỗng không dựa trên tài liệu C7620 thật, Q0718 còn XML thô `<p:sld...>` và chữ vỡ trong đáp án, Q0709 chỉ là thông báo lỗi 41 ký tự, và 2 test adapter FAIL trên máy không cài gói ngoài (điều phối tự chạy xác nhận tại commit nộp).

## Việc phải làm

1. **Vì sao pool không qua nổi sau khi siết:** đo bằng log lượt gọi thô (không qua sanitizer): với ling-3.1-flash, trường `content` thực tế rỗng bao nhiêu % lượt gọi, sanitizer loại bỏ những gì. Phân biệt dứt khoát: model trả content rỗng thật (→ cần đổi cách gọi/đổi model chính trong pool theo bằng chứng) hay lớp sửa vòng 1 quá tay (→ sửa lớp sửa). Nêu số liệu trước khi sửa.
2. **Q0699 phải ra đáp án thật:** với nguồn C7620 đã bật, truy hồi phải đưa mảnh đích của `Sirius 2 _ C7620_報告書 4.pptx` vào ngữ cảnh; chẩn đoán vì sao vòng 1 mảnh đích không vào (điểm truy hồi? giới hạn mảnh? fallback cắt đoạn?). Đáp án đạt chuẩn: có nội dung C7620 thật kèm trích dẫn, hoặc abstention đúng cấu trúc có lý do cụ thể — khung rỗng các mục trống là không đạt.
3. **Làm sạch trích đoạn fallback:** đáp án trích cục bộ không được chứa XML thô (`<p:sld`, `xmlns:...`) hay rác định dạng — xác định khâu trích xuất mảnh đang để lọt và làm sạch ở đúng khâu đó (không lọc che ở tầng hiển thị bằng vài mẫu chuỗi).
4. **Q0709 phải có đáp án thật** từ bảng quy đổi Skew (hoặc abstention đúng cấu trúc nếu thật sự không có bằng chứng) — thông báo lỗi trần 41 ký tự không tính là đáp án.
5. **Test adapter phải xanh ở cả hai môi trường:** 2 ca đang FAIL trên VM (`test_adapter_runs_when_external_router_package_missing`, `test_adapter_legacy_rollback_via_env_flag`) phải PASS trên máy không cài gói ngoài VÀ trên máy nhà. Điều phối sẽ tự chạy lại trên VM khi chấm.
6. **Nghiệm thu lại trên app thật** (chỉ chạy khi điều phối đã gỡ đóng băng chỉ mục sau vé truy nguyên): 3 câu cũ, nộp ĐỦ ẢNH vào repo (các vé trước đều nộp ảnh vào `docs/phieu-viec/ket-qua/` — vòng 1 thiếu ảnh là một lỗi nộp bài), đáp án nguyên văn, thời gian từng câu, kiểm băm chỉ mục trước/sau phải khớp tuyệt đối.

## Rào cứng

- Kỷ luật báo cáo: mọi con số trong báo cáo (số test pass, "sạch", "trọn câu") phải khớp đúng bằng chứng đính kèm — điều phối đối chiếu độc lập từng con số; khai lệch bằng chứng là lỗi nặng nhất của vé này.
- Không nới bộ kiểm định; không bịa đáp án khi thiếu bằng chứng.
- Chỉ mục production: chỉ đọc; nếu nghiệm thu cần bật nguồn thì chỉ dùng cách đã được vé truy nguyên băm xác nhận an toàn. Không merge `main`. Tương thích Python 3.11.
- Vé dài: mốc tối thiểu 15 phút/lần + checkpoint.
