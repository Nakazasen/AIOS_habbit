# Báo cáo review chéo spec C-Agent từ góc nhìn dữ liệu (REVIEW-WIRE-CAGENT-SPEC)

- **Người review:** opencode (thợ nắm dữ liệu JSONL) — máy KDTVN-PC0575
- **Ngày:** 2026-10-05
- **Spec được review:** `docs/phieu-viec/ket-qua/wire-cagent-spec.md` (agy lập)
- **Dữ liệu đối chiếu:** `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (3.392 cặp, đã verify ở vé trước)
- **Verdict:** **OK để nối** — không phát hiện vấn đề tương thích chặn việc nối WIRE. Có 4 ghi nhận nhỏ (mức thấp) bên dưới.

## 1. Spec có tính đến shape thực tế của dữ liệu không?

**Có, cơ bản khớp.** JSONL thực tế có đúng 6 trường `id / question / answer / source / category / batch` (kiểm bằng script: 3.392 dòng, id duy nhất, 0 cặp rỗng; phân bố MOM 608 / LSU 1.790 / điều-tra-lỗi 994). Spec §1.2 liệt kê đúng 3.392 cặp theo 3 khối và trích context theo từ khóa / mã lỗi / số hiệu JIG — cách trích này khả thi vì `question` luôn chứa thực thể tra cứu được (mã lỗi, tên tham số, serial).

**Ghi nhận nhỏ #1 (thấp):** template context trong spec §1.2 tách thành 3 mảnh `{bối cảnh gốc} / {hỏi gốc} / {đáp gốc}`, trong khi JSONL chỉ có 2 trường `question / answer` (bối cảnh đã gộp trong câu hỏi/trả lời, không có trường riêng). Thợ vé WIRE cần quy tắc rõ: lấy `{bối cảnh}` từ đâu (bỏ qua hay tách từ `question`). Không chặn, chỉ cần chốt một dòng khi implement.

**Ghi nhận nhỏ #2 (thấp):** spec §căn cứ (dòng 10) ghi "3.393 cặp Q1–Q3406", con số đúng sau khử trùng là **3.392** (Q3214 trùng Q3124). Sửa một chữ số để tài liệu nhất quán.

## 2. Ba câu demo trong spec có khả thi với dữ liệu hiện có không?

**Cả 3 đều khả thi, đã tìm thấy cặp tương ứng trong JSONL:**

| Demo | Nguồn spec ghi | Đối chiếu JSONL | Kết luận |
|---|---|---|---|
| 1. Mã lỗi C0980 (điều-tra-lỗi) | Q3401 (batch-88) + Q3317 (batch-85) | Cả 2 đều có: Q3401 đáp đúng định nghĩa `C0980 là 24V電源断検知` + điều kiện 1 giây; Q3317 đáp đúng `đứt cầu chì F401`, `Q402/Q403 short 3 cực` | Khả thi. Lưu ý: chi tiết `IC401`, `D304/D211` trong kỳ vọng spec không nằm trong 2 cặp này — C-Agent sẽ phải tổng hợp từ cặp khác hoặc trả lời thiếu phần đó, nên kỳ vọng demo nên ghi "tối thiểu F401 + Q402/Q403" thay vì liệt kê cứng cả 4 linh kiện. |
| 2. ctrlMode Matecon (MOM) | raw mom/batch-01 (Q1, Q2) | Q0001 trong JSONL hỏi đúng `ctrlMode = 0 và 1 khác nhau thế nào`, đáp đúng auto/thủ công + SLMP; Q0002 cùng file | Khả thi hoàn toàn. |
| 3. Jig 2ND-1004 Serial 61C999999902 (LSU) | raw lsu/batch-21 (Q825) | Q0825 trong JSONL hỏi đúng serial, đáp đúng `xuất hiện 4 lần`, `Total=NG, Black=NG, Magenta=NG, Cyan=OK, Yellow=NG` | Khả thi hoàn toàn, khớp từng chữ số. |

**Ghi nhận nhỏ #3 (thấp):** demo 2 và 3 trích dẫn đường dẫn **raw** (`chatgpt-enrichment-raw/...`) trong khi dữ liệu staging vé WIRE dùng là file **fixed** và trường `source` trong JSONL ghi dạng ngắn (`mom/batch-01.md`, `lsu/batch-21.md`). Nội dung cùng batch nên không sai, nhưng để truy vết một bước thì spec nên dẫn đường dẫn fixed (hoặc ghi cả hai).

## 3. Năm kịch bản lỗi trong spec có kịch bản nào dữ liệu trigger được không?

Spec §3.1 liệt kê 5 nhóm: quá hạn 60s, mất mạng/DNS, server 5xx, chặn Cloud/Challenge (403), dữ liệu rỗng/sai. Đối chiếu đặc tính dữ liệu thực tế (quét script trên toàn bộ 3.392 cặp):

- **Câu hỏi dài gây quá hạn — dữ liệu KHÔNG trigger được.** Câu hỏi dài nhất chỉ 148 ký tự (Q2048), trả lời dài nhất 505 ký tự (Q0202). Kể cả ghép top-3 cặp vào prompt thì payload vẫn chỉ ~2KB — quá nhẹ so với ngưỡng timeout. Nguy cơ quá hạn nằm ở phía server (baseline đo thực tế ~30s), không phải do dữ liệu.
- **Dữ liệu rỗng/sai (JSON rỗng, thiếu trường `text`) — dữ liệu CÓ THỂ trigger gián tiếp.** 2.545/3.392 cặp chứa ký tự Nhật/Trung và 2.606 cặp chứa backtick (mã, serial, tên file). Nếu client ghép prompt mà encode JSON/UTF-8 sai, server dễ trả về lỗi hoặc HTML thay vì JSON — đúng vào kịch bản này. Đề nghị vé WIRE test một câu chứa tiếng Nhật + backtick (ví dụ Q3401) để khóa encoding ngay từ đầu.
- **Chặn Cloud/403 do rate limit — dữ liệu CÓ THỂ trigger khi chạy demo hàng loạt.** Chính spec đã ghi từng bị chặn ngày 02/10 và trong quá trình sinh dữ liệu. Kho 3.392 cặp mời gọi test quét hàng loạt — nếu vé WIRE chạy vòng lặp demo không giãn cách sẽ tái hiện 403. Đề nghị giữ giãn cách giữa các lần gọi thử (không gọi dồn dập).
- **Mất mạng/DNS, server 5xx, người dùng hủy — hạ tầng / phía client, dữ liệu không trigger.** Không liên quan kho Q&A.

Tóm lại: 2/5 kịch bản liên quan dữ liệu (encoding và rate-limit khi test hàng loạt), đều đã có cách phòng — không cần sửa spec, chỉ cần thợ WIRE đọc kỹ hai điểm này.

## 4. Nhãn "Bản thảo — chưa qua chuyên gia duyệt" có được spec yêu cầu hiển thị ở demo không?

**Có.** Spec §4 quy định nhãn bắt buộc với mọi câu trả lời dùng context 3.392 cặp, kèm mẫu Markdown và vị trí (đầu bong bóng tin nhắn hoặc footer) + ví dụ ghi nguồn khối/ID cặp. Cả 3 câu demo (§5) đều có dòng "Nhãn hiển thị: Có kèm nhãn". Đầy đủ, không thiếu.

## Danh sách ghi nhận (tổng hợp, không có mục chặn)

1. (Thấp) Template context 3 mảnh vs JSONL 2 trường — cần chốt quy tắc lấy `{bối cảnh}` khi implement.
2. (Thấp) Dòng căn cứ ghi 3.393 — sửa thành 3.392 cho nhất quán.
3. (Thấp) Demo 2/3 dẫn đường dẫn raw — nên dẫn thêm đường dẫn fixed / `source` trong JSONL để truy vết một bước.
4. (Lưu ý, không phải lỗi spec) Kỳ vọng demo 1 liệt kê 4 linh kiện trong khi 2 cặp trích dẫn chỉ bao phủ F401 + Q402/Q403 — nên ghi kỳ vọng tối thiểu, tránh nghiệm thu cứng rồi trượt oan.

Không sửa JSONL, không sửa spec theo đúng yêu cầu vé — chỉ ghi nhận.

## Phương pháp kiểm chứng

- Đếm JSONL bằng script: 3.392 dòng, 6 trường đúng tên, id duy nhất, 0 rỗng, phân bố category như trên.
- Tra cứu trực tiếp Q3401/Q3317/Q0001/Q0002/Q0825 trong JSONL, đọc đáp án đối chiếu từng điểm với kỳ vọng spec.
- Quét độ dài toàn kho (max Q 148, max A 505 ký tự) + đếm ký tự CJK/backtick cho phần lỗi.
- Đọc spec toàn văn (§1–§6), kiểm tra nhãn ở §4 và từng demo ở §5.
