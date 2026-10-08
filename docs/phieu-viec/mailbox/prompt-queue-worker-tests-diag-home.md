# VÉ: WORKER-TESTS-DIAG-HOME (điều tra 3 ca test hạ tầng bộ đọc đỏ ở cả hai môi trường)

- Mã vé: `WORKER-TESTS-DIAG-HOME`
- Role gợi ý: PLAN/DEFAULT (OMP — thợ phụ, máy nhà là môi trường đích Windows cho các test này)
- Báo cáo: `docs/phieu-viec/ket-qua/worker-tests-diag-home.md`
- Căn cứ: báo cáo full suite của vé `TEST-PORTABLE-AIANSWER-HOME` ghi 3 ca đỏ hạ tầng bộ đọc trên máy nhà; điều phối cũng tự bắt được 1 ca trong số đó fail y hệt trên VM sạch:
  1. `tests/test_bge_worker_self_healing.py::test_adapter_self_healing_reconciles_timeout_errors` — fail trên CẢ máy nhà (`assert 0 == 1`) lẫn VM của điều phối. Đây là test của đợt sửa tự-phục-hồi (verdict ĐẠT 23:27 07/10) — nếu nó đỏ thật thì tính năng tự phục hồi có thể đã bị hồi quy bởi các thay đổi sau đó.
  2. `tests/test_bge_subprocess_client.py::test_client_enforces_bounded_deep_timeout` — `bge_subprocess_worker_crashed` trên máy nhà.
  3. `tests/test_bge_subprocess_worker.py::test_bge_subprocess_worker_crash_handling` — `PermissionError [WinError 5]` thư mục tạm trên máy nhà (có thể là lỗi môi trường Windows).

## Việc phải làm

1. Chạy lại từng ca riêng lẻ trên máy nhà, lấy traceback đầy đủ; phân loại từng ca: lỗi code thật / lỗi ở chính test (giả định đã lỗi thời sau các thay đổi gần đây) / lỗi môi trường (quyền thư mục tạm, tiến trình còn sót).
2. Với ca (1): đối chiếu hành vi hiện tại của adapter tự phục hồi với kỳ vọng của test — chỉ rõ thay đổi nào (commit nào, nếu truy được) làm lệch, và lệch ở code hay ở test.
3. Nếu lỗi nằm ở test (giả định lỗi thời, dọn dẹp thiếu): sửa test cho đúng hành vi hiện tại đã được nghiệm thu dùng thật ở các vé gần đây, chạy lại xanh. Nếu lỗi nằm ở code thật: KHÔNG tự đổi hành vi — báo cáo chẩn đoán + đề xuất hướng sửa để điều phối quyết bằng vé riêng.
4. Dọn điều kiện môi trường cho ca (3) nếu là quyền thư mục tạm/tiến trình sót: nêu cách tái lập sạch và kết quả sau khi dọn.

## Rào cứng

- Không ghi chỉ mục; không đổi hành vi chạy thật của app trong vé này. Không merge `main`.
- Báo cáo: bảng phân loại từng ca + bằng chứng traceback + việc đã sửa (nếu sửa test) kèm kết quả chạy lại.
- Mốc tiến độ tối thiểu 15 phút/lần.
