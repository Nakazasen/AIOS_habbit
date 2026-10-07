# Báo cáo vé SYNTH-COMPOSER-NOISE-FIX-HOME — chặn mảnh nhiễu lọt vào khâu soạn đáp án

- Mã vé: `SYNTH-COMPOSER-NOISE-FIX-HOME`. Máy làm: nhà h410asrock. Thời gian: 2026-10-08 01:49 → 01:58 +07.
- Căn cứ: `prompt.md` vé này + báo cáo `test-red22-fix-home.md` mục 2 (test đỏ `test_architecture_composer_rejects_noise_and_unscoped_multi_facet_fillers` trong `tests/test_rag_v2_synthesis.py`).
- Kết quả: **test đích xanh**, hồi quy liên quan **85/86** (1 đỏ cũ đã xác nhận trước khi sửa, không phải do vé này), cổng repo đủ (Python 3.11, `compileall` sạch, `cli audit` PASS, `import workspace_chat_app` thành công). Không đụng tầng truy xuất/chỉ mục, không ghi chỉ mục, không hợp nhất vào `main`.

## 1. Truy vết vì sao mảnh nhiễu lọt qua

- Mảnh nguồn của vé: `Grounded local evidence for the production workflow. | ABV（Step1対象外 | 5 ©2025 Example Document Solutions Inc.` (gán đa-facet `components`, `data_flow`, `interfaces`).
- Đường tách mảnh (`_candidate_fragments`, tách theo `|` và dấu câu) cho ra 3 mảnh con:
  - `Grounded local evidence for the production workflow.` → bị loại đúng (khớp quy tắc boilerplate mở đầu).
  - `5 ©2025 Example Document Solutions Inc.` → bị loại đúng (khớp quy tắc chân trang `©`, dài dưới 90 ký tự).
  - `ABV（Step1対象外` → **lọt**: dài đúng 12 ký tự (vừa qua ngưỡng tối thiểu 12), không chứa `©`, không lặp từ; hàm trích thuật ngữ tách thêm n-gram chữ Hán (`対象`, `象外`...) nên đếm ra 6 thuật ngữ, qua được ngưỡng `terms < 3`.
- Khâu chọn theo facet (`_best_facet_candidate`) chấm điểm chồng lắp với câu hỏi: cả mảnh nhiễu và mảnh tốt đều 0 điểm chồng lắp (câu hỏi dùng `components` số nhiều, mảnh tốt dùng `component` số ít), nên tiêu chí phụ `-len(fragment)` (ngắn thắng) đẩy mảnh nhiễu 12 ký tự lên trên mảnh tốt dài. Metadata đa-facet khiến mảnh nhiễu thành ứng viên cho cả 3 facet.
- Hàm `_fragment_supports_facet` hiện tại chỉ kiểm đếm thuật ngữ (không xét facet hay câu hỏi), nên không chặn được trường hợp này — nhưng siết hàm này theo hướng đòi chồng lắp câu hỏi sẽ giết cả mảnh tốt (mảnh tốt cũng 0 chồng lắp như trên), nên không chọn hướng đó.

## 2. Đề xuất hướng sửa (viết trước khi code) và chống quá khớp test

- Phương án (a) — chỉ sửa bộ lọc nhiễu: thêm quy tắc cấu trúc cho mảnh cửa sổ cắt dở (ngoặc lệch). Ưu: gọn, giữ nguyên recall. Nhược: mảnh nhiễu cân ngoặc vẫn có thể lọt.
- Phương án (b) — chỉ sửa khâu chọn theo facet: ưu tiên mảnh đơn-facet khi hòa điểm từ vựng. Ưu: chặn cả mảnh nhiễu cân ngoặc. Nhược: một mình không loại mảnh nhiễu khỏi đáp án nếu nó là ứng viên duy nhất của facet.
- Phương án (c) — làm cả hai (đã chọn): lọc cấu trúc loại mảnh cắt dở + ưu tiên phạm vi hẹp khi hòa điểm. Chống quá khớp bằng cách: không ghi cứng chuỗi `ABV`/`Step1`/`対象外` nào vào code; quy tắc ngoặc lệch áp cho mọi cặp ngoặc (kể cả toàn角); ưu tiên đơn-facet chỉ chen vào giữa điểm từ vựng và độ dài (chồng lắp cao vẫn thắng, ứng viên đa-facet duy nhất vẫn được dùng). Kiểm recall bằng mảnh tốt tiếng Anh + tiếng Việt + mảnh cân ngoặc chứa `ABV`.

## 3. Cách sửa

- Vị trí: `src/aios_habit/rag_v2/synthesis.py`, 2 hàm.
- `_is_fragment_noise`: thêm kiểm tra ngoặc lệch cho 12 cặp ngoặc (tròn/vuông/nhọn toàn角 và bán角: `()`, `[]`, `{}`, `〈〉`, `《》`, `「」`, `『』`, `【】`, `〖〗`, `（）`, `［］`, `｛｝`). Mảnh `ABV（Step1対象外` mở `（` mà thiếu `）` nên bị loại.
- `_best_facet_candidate`: khóa xếp hạng thành `(ưu tiên thân bài, điểm từ vựng..., đơn-facet, độ ngắn, thứ tự)`. Chồng lắp từ vựng vẫn quyết định trước; chỉ khi hòa điểm thì mảnh gán đúng 1 facet thắng mảnh gán nhiều facet. Không loại bỏ ứng viên, chỉ xếp lại thứ tự nên không giết recall.
- Không đụng tầng truy xuất/chỉ mục; không thêm cờ tính năng (sửa đúng chỗ lọc, không phải tính năng mới).

## 4. Kiểm chứng bằng kiểm thử

- Test đích `test_architecture_composer_rejects_noise_and_unscoped_multi_facet_fillers`: **1 passed** (0,19 giây). Trước sửa: rớt ở `assert "ABV" not in result.answer` (đáp án chứa `ABV（Step1...` ở `COMPONENTS`).
- Hồi quy liên quan: `test_rag_v2_synthesis.py` + `test_rag_v2_synthesis_provider.py` + `test_rag_v2_eval_harness.py` — **85 passed, 1 failed** (`test_provider_limitations_contain_accurate_reasons`, thiếu `cloud_privacy_blocked`). Đã đối chiếu bằng cách giấu sửa tạm (`stash`): test này đỏ y hệt khi chưa sửa, nên là đỏ cũ ngoài phạm vi vé, không phải hồi quy.
- Kiểm recall mảnh tốt (kịch bản `recall_check.py`, dùng đúng đường `_candidate_fragments`): giữ đủ 5/5 mảnh tốt (3 câu tiếng Anh của vé, 1 câu tiếng Việt, 1 câu cân ngoặc có `ABV (Step1)` đủ nghĩa); loại đúng 3/3 mảnh nhiễu (mảnh ngoặc lệch, mảnh `Copyright`, mảnh boilerplate).

## 5. Kiểm chứng bằng dùng thật

- Chạy đúng đường soạn thật `synthesize_evidence(pack, answer_shape="architecture")` với đủ 5 mảnh của vé (đo trong tiến trình, không ghi chỉ mục):
  - Thời gian soạn: khoảng **1,6 mili giây**.
  - Kết quả: `grounded=True`, 3 tuyên bố đúng 3 facet (`components`, `data_flow`, `interfaces`), mỗi tuyên bố gán đúng 1 facet, không trùng chứng cứ.
  - Đáp án thật: `COMPONENTS` giữ câu đăng ký trung tâm, `DATA_FLOW` giữ câu thiết bị đầu cuối gửi bản ghi, `INTERFACES_AND_VERIFICATION` giữ câu cổng `MOM`; không còn `ABV`, `Copyright`, `©2025`, `Grounded local evidence`.
- Không ghi chỉ mục thật, không đụng dữ liệu sản phẩm, không hợp nhất vào `main`.

## 6. Cổng repo

- Python `3.11.14` qua `uv`.
- `python -m compileall src tests`: sạch.
- `python -m aios_habit.cli audit`: `{"status": "PASS"}`.
- `import aios_habit.workspace_chat_app`: thành công.
- Bộ toàn kho `pytest -q` chưa chạy (nặng khoảng 57 phút như vé trước; vé này phạm vi là bộ synthesis + cổng repo, không báo đạt cho toàn kho).

## 7. Đề nghị

- Vé đã khép ca đỏ cuối nhóm đã xác nhận ở `test-red22-fix-home.md` mục 2. Đề nghị điều phối cho chạy lại cụm synthesis trên máy ảo để chốt.
