# VÉ NHỎ: TEST-PORTABLE-AIANSWER-HOME (sửa 2 test ai_answer fail trên môi trường sạch)

- Mã vé: `TEST-PORTABLE-AIANSWER-HOME`
- Role gợi ý: SMOL/TINY (OMP — thợ phụ, máy nhà)
- Báo cáo: `docs/phieu-viec/ket-qua/test-portable-aianswer-home.md`
- Căn cứ: điều phối tự chạy trên VM sạch (không cài gói ngoài `nakazasen_ai_router`) tại head chứa bản sửa cold-start: 2 test trong `tests/test_workspace_chat_ai_answer.py` vẫn fail nguyên trạng —
  - `test_generate_answer_via_router_integration_mocked_outcome`
  - `test_workspace_chat_router_creation_enables_network_and_v051_recovery`
  Lỗi gốc điều phối bắt được: `ModuleNotFoundError: No module named 'nakazasen_ai_router'` và `NameError: name 'Any' is not defined` tại file test (dòng ~1175). Trên máy nhà (có cài gói ngoài) thì pass — tức là test chưa thực sự "di động" như mục tiêu đã đặt từ các vé trước.

## Việc phải làm

1. Sửa để cả file test chạy được trên môi trường KHÔNG cài gói `nakazasen_ai_router`: cô lập/mock đúng ở cấp test (không phụ thuộc gói ngoài có mặt), sửa lỗi `NameError: Any` trong file test.
2. Không nới lỏng ý nghĩa kiểm thử: các test này phải vẫn kiểm đúng hành vi (adapter chạy được khi thiếu gói ngoài; tạo router bật mạng + khôi phục được). Cấm xoá test, cấm skip vô điều kiện để lấy xanh — nếu buộc phải skip khi thiếu gói thì dùng điều kiện rõ ràng và ghi lý do trong báo cáo (điều phối sẽ chạy lại trên VM sạch để đối chiếu).
3. Chạy lại toàn bộ file `tests/test_workspace_chat_ai_answer.py` và ghi kết quả theo môi trường (có gói / không gói nếu tách được).

## Rào cứng

- Chỉ sửa file test và, nếu thật cần, điểm import trong adapter theo hướng fail-closed đã có; không đổi hành vi chạy thật của app. Không ghi chỉ mục; không merge `main`.
- Báo cáo ngắn: nguyên nhân từng lỗi, cách sửa, kết quả chạy lại (số test pass/fail đúng đếm thật).
