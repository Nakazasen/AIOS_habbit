# Báo cáo vé FEEDBACK-DOGFOOD-HOME — chạy thử vòng lặp feedback trên dữ liệu thật máy nhà

- Ngày: 2026-10-06 (giờ máy khi chốt).
- Vé: `FEEDBACK-DOGFOOD-HOME` — "ăn thử món mình nấu" sau 2 vé ĐẠT (LOOP-HOME + REVIEW-HOME).
- Prompt: `docs/phieu-viec/mailbox/prompt.md` (copy `prompt-queue-feedback-dogfood-home.md`).
- Nhánh: `phieu-viec/rag-fix1`. Không merge `main`.
- Trạng thái: đã làm + verify xong, chờ duyệt.
- Cổng gate: MỞ suốt vé (không có file watcher tự mở nào trong `mailbox/`; các commit chen giữa của lane opencode/agy chỉ chạm `ket-qua/` + `mailbox-agy/` + `mailbox-opencode/`, không chạm `src`/`tests` của vé này).

## 1. Bật cờ theo phiên (không sửa default trong code)

- Code mặc định vẫn TẮT (`feedback_loop_enabled()` trả `False` khi không đặt env).
- Vé này chỉ đặt `AIOS_FEATURE_FEEDBACK_LOOP_HOME=1` trong lệnh chạy, xong việc là hết (môi trường shell đóng là cờ tắt).
- Kiểm lại sau xong: cờ tắt → module review in "Cờ … đang tắt nên không chạy.", exit 0, không ghi file.

## 2. Tạo 32 lượt feedback thật qua đúng handler UI gọi

- Handler thật: `feedback_loop_home.record_device_feedback()` — đúng hàm nút like/dislike trong `workspace_chat_ui.py` gọi (nhánh `_loop_on`).
- Backup trước: `local_cases/answer_feedback.jsonl.bak_truoc_dogfood_20261006` (giữ 1 dòng cũ từ 04/10).
- 32 lượt mới (lane `dogfood-home`), 3 câu hỏi khác nhau:
  - Q1 LSU (`Loi JAM4709 ket giay tren may LSU JIG la gi?`, chủ đề `lsu`): 16 lượt = 12 chê kèm lý do + 4 khen. Câu chê thật nhiều lần theo đúng vé (≥10 chê).
  - Q2 MOM (`Mo file MOM tren Opcenter MES bi loi thi lam gi?`, chủ đề `mom`): 10 lượt = 8 khen + 2 chê.
  - Q3 KDTPS (`KDTPS buoc 2 dieu tra loi the nao?`, chủ đề `dieu_tra_loi`): 6 lượt = 5 khen + 1 chê tự ghi tay.
- Mã máy thật: `may-716ef0e2119e` (file `local_cases/device_id`, tạo lần đầu trên máy này) — đủ 32/32 lượt mới.
- Lý do chê tự ghi tay: 2 lượt (1 ở Q1 kèm nhãn chọn sẵn, 1 ở Q3 ghi tay hoàn toàn). 0 lượt chê thiếu lý do (store từ chối chê không lý do — đúng luật "chê phải nói rõ").

## 3. Bảng xếp hạng metric thật (`compute_loop_metrics` trên dữ liệu thật)

- Tổng store: 33 lượt (18 khen / 15 chê, tỉ lệ chê 0,455) — gồm 32 lượt dogfood + 1 dòng cũ.
- Theo câu: JAM4709 đầu bảng (16 lượt, 12 chê, tỉ lệ 0,750, 1 máy) → MOM (10 lượt, 2 chê, 0,200) → KDTPS (6 lượt, 1 chê, 0,167) → câu cũ (1 lượt, 0 chê).
- Theo chủ đề: `lsu` 16 lượt 12 chê (0,750) → `mom` 10 lượt 2 chê (0,200) → `dieu_tra_loi` 6 lượt 1 chê (0,167) → `chua_phan_loai` 1 lượt 0 chê.
- `flag_answers_for_fix`: rỗng — trung thực (ngưỡng cần chê từ ≥2 máy, dogfood này chỉ 1 máy nhà nên chưa lọt; không hạ ngưỡng để lấy số đẹp).
- Gợi ý: tỉ lệ chê >30% + xem lại chủ đề `lsu` (12/16).

## 4. Báo cáo review thật trên `local_cases/` thật

- Lệnh vé bắt: `python -m aios_habit.feedback_review_home --dau-ra local_cases/feedback_review_dogfood.md` — đã chạy thật, exit 0.
- Kết quả: tổng 33 lượt, tỉ lệ chê 0,455, **0 cảnh báo câu / 0 cảnh báo chủ đề** — ĐÚNG, không phải thiếu sót: chuỗi dài nhất mới 1 ngày trong 2 ngày có dữ liệu (04/10 + 06/10), chưa đủ cửa sổ để kết luận xu hướng.
- Báo cáo ghi rõ: "Chuỗi dữ liệu: chuỗi dài nhất 1 ngày trong 2 ngày có dữ liệu (chưa đủ 20 điểm, sơ bộ; không cảnh báo giả từ dữ liệu ít)." — đúng quy ước vé.
- Đề xuất trong báo cáo: xem lại chủ đề `lsu` (bị chê 12/16).

## 5. Sửa nhỏ module trong vé này (2 điểm vé bắt mà code cũ thiếu)

Vì vé dogfood bắt 2 hành vi mà module REVIEW-HOME cũ chưa có, đã sửa nhỏ (không đổi logic SMA/trend):

1. `feedback_review_home.py` — báo cáo thêm dòng chuỗi dữ liệu (số ngày chuỗi dài nhất + tổng ngày có dữ liệu + "chưa đủ 20 điểm, sơ bộ" khi <20 điểm). Trước đó báo cáo không ghi số ngày nào.
2. `feedback_review_home.py` — cờ tắt thì CLI exit **0** (trước là exit 2). Vé bắt "cờ tắt → module không làm gì (exit 0, không ghi file)". Test cũ không khóa exit code nên lọt.
3. `tests/test_feedback_review_home.py` — thêm 2 test: báo cáo chuỗi ngắn ghi "sơ bộ" + không cảnh báo giả; CLI cờ tắt exit 0 + không ghi file.

Diff vé này: `src/aios_habit/feedback_review_home.py` +21/-1, `tests/test_feedback_review_home.py` +16/-0. Không sửa file khác, không đổi default cờ, không chạm index/kho tri thức.

## 6. Đối chiếu tiêu chí nghiệm thu trong prompt

- ≥30 lượt feedback thật, store có device_id máy thật, ≥1 lý do tự ghi: đạt — 32 lượt qua handler UI thật, 32/32 mang `may-716ef0e2119e`, 2 lý do tự ghi.
- Bảng xếp hạng metric thật có số đo thật: đạt — mục 3.
- Báo cáo review thật từ `local_cases/` thật; không cảnh báo giả khi chuỗi ngắn; ghi "sơ bộ": đạt — mục 4.
- Cờ tắt → không làm gì (exit 0, không ghi file): đạt — đã kiểm thật 2 lần + test khóa.
- `compileall` sạch, `cli audit` PASS, import app OK: đạt — compile exit 0; audit `{"status": "PASS", "errors": []}`; `import workspace_chat_app` OK (chạy bằng `PYTHONPATH=src`, Python 3.11.14).
- Không ghi index/kho tri thức (chỉ `local_cases/`), không merge `main`, không secret, không đổi default cờ: đạt — grep không thấy secret; diff chỉ 2 file vé; toàn single-parent.
- Test: 52/52 xanh (`review_home` 12 = 10 cũ + 2 mới, `loop_home` 12, `feedback_loop` + `answer_feedback` cũ 28).

## 7. Ghi chú trung thực

- Dữ liệu dogfood là OMP tự chấm tay qua handler thật (không phải người dùng thật bấm trên Streamlit) — đã ghi rõ trong báo cáo này; giá trị thật nằm ở chỗ handler + store + metric + review đều chạy thật trên máy thật.
- `flag_answers_for_fix` rỗng vì 1 máy — không hạ ngưỡng, chờ nhiều máy thật mới có ý nghĩa.
- Bộ toàn kho nặng không chạy (như vé trước, prompt không bắt buộc).
- Dữ liệu feedback thật giữ trong `local_cases/` (đã gitignore, không commit). File backup + `device_id` + báo cáo review đều nằm đó, không lên git.

## 8. Cách dùng và hoàn tác

- Xem báo cáo review: `local_cases/feedback_review_dogfood.md` (gitignore, chỉ máy nhà có).
- Chạy lại review khi có thêm feedback: đặt `AIOS_FEATURE_FEEDBACK_LOOP_HOME=1` rồi chạy lệnh mục 4.
- Hoàn tác code: revert 2 file ở mục 5 là về đúng cây REVIEW-HOME (logic SMA/trend không đổi).
- Dữ liệu: muốn về trước dogfood thì copy file `.bak_truoc_dogfood_20261006` đè lại `answer_feedback.jsonl` + xóa `device_id` (sẽ tạo mã mới).

## 9. Đề nghị duyệt vé

- Vé đạt ở mức chờ duyệt: đủ 32/32 feedback thật có mã máy thật + 2 lý do tự ghi, metric + review thật có số đo thật, báo cáo ghi "sơ bộ" đúng quy ước, cờ tắt exit 0, 52/52 test xanh, audit PASS, đúng rào an toàn.
- Nhờ Muse review độc lập rồi phát hành vé tiếp theo.
