# VÉ XẾP HÀNG: SYNTH-COMPOSER-NOISE-FIX-HOME (chặn mảnh nhiễu lọt vào khâu soạn đáp án)

- Mã vé: `SYNTH-COMPOSER-NOISE-FIX-HOME`
- Role gợi ý: PLAN → DEFAULT (việc cần suy nghĩ trước khi code)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/synth-composer-noise-fix-home.md`
- Căn cứ: báo cáo `test-red22-fix-home.md` mục 2 — test đỏ `test_architecture_composer_rejects_noise_and_unscoped_multi_facet_fillers` (tests/test_rag_v2_synthesis.py): mảnh nhiễu dạng `ABV...©2025...` lọt vào COMPONENTS dù `_is_fragment_noise` có chặn boilerplate `^grounded local evidence` — cửa sổ mảnh cắt qua câu nên thoát bộ lọc. Gốc nằm ở khâu chọn mảnh theo facet trong `synthesis.py`.

## Việc phải làm

1. Đọc và truy vết đường chọn mảnh của composer: vì sao mảnh nhiễu qua được cả bộ lọc nhiễu lẫn điều kiện facet. Đề xuất hướng sửa trong báo cáo TRƯỚC khi code (mục riêng): sửa ở bộ lọc nhiễu, ở khâu chọn theo facet, hay cả hai — kèm rủi ro quá khớp test (overfit) và cách tránh.
2. Code theo hướng đã chọn; test đích xanh; chạy thêm bộ đề chất lượng nhỏ (fixtures eval có sẵn) để chứng minh không làm rớt mảnh tốt ở câu thật — sửa lọc nhiễu mà giết recall là thất bại.
3. Không hồi quy: suites synthesis + synthesis_provider + eval_harness + cổng repo (Python 3.11, compileall, cli audit, import app).

## Rào cứng

- Không đụng tầng retrieval/index; không ghi index; không merge `main`.
