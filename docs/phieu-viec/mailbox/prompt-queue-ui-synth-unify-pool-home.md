# VÉ: UI-SYNTH-UNIFY-POOL-HOME (hợp nhất đường tổng hợp của giao diện về pool Command Code + fallback trích cục bộ)

- Mã vé: `UI-SYNTH-UNIFY-POOL-HOME`
- Role gợi ý: PLAN (đọc kỹ 2 điểm nối trước khi code) + DEFAULT khi code
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/ui-synth-unify-pool-home.md`
- Căn cứ: báo cáo truy vết `ui-synth-route-trace-home.md` (đã verdict ĐẠT): giao diện có 4 backend rời rạc; pool Command Code chưa hề được nối vào UI; nhánh `nakazasen_router` trong `antigravity_bridge.py` (~dòng 1208–1230) trả lỗi ngay khi provider hỏng, bỏ qua `local_synthesis` đã tính sẵn — đây là lý do người dùng nhận "Dịch vụ AI chưa phản hồi" thay vì đáp án trích cục bộ.

## Việc phải làm

**Bước 0 — Dọn rò rỉ key trong báo cáo truy vết (BẮT BUỘC, làm trước mọi việc khác):** báo cáo `docs/phieu-viec/ket-qua/ui-synth-route-trace-home.md` §4.1 đang chứa tiền tố rút gọn của `AIOS_LOCAL_AI_API_KEY`. Thay toàn bộ giá trị sau dấu `=` bằng `<đã cấu hình — không ghi giá trị>` và commit riêng. Từ nay mọi báo cáo chỉ ghi "biến có mặt/không có mặt", tuyệt đối không ghi bất kỳ ký tự nào của key.

**Bước 1 — Test trước cho hành vi mới:** viết test đơn vị chứng minh: (a) adapter của giao diện gọi đúng tuyến nội bộ đọc cấu hình pool từ `.env` (mock tầng gọi mạng, không gọi thật trong test); (b) khi tuyến tổng hợp lỗi (mock `ok=False`/timeout), nhánh router trong `antigravity_bridge` trả về đáp án `local_synthesis` kèm badge minh bạch thay vì lỗi chết. Test phải đỏ trước khi sửa, xanh sau khi sửa.

**Bước 2 — Đấu nối adapter về tuyến nội bộ:** sửa `src/aios_habit/workspace_chat_router_adapter.py` để đường mặc định đi qua `aios_habit.ai_router` / `RouterSynthesisProvider` (đọc `AIOS_LOCAL_AI_*` từ `.env` — pool Command Code + failover đã cấu hình). Giữ nguyên chữ ký hàm công khai của adapter; giữ đường gói ngoài `nakazasen_ai_router` làm đường lùi sau một biến môi trường (mặc định không dùng) để rollback 1 dòng khi cần.

**Bước 3 — Bật fallback trích cục bộ cho nhánh router:** trong `route_workspace_chat_submission` (`antigravity_bridge.py`), khi kết quả tuyến tổng hợp không `ok` mà `local_synthesis` khả dụng (dùng lại `_local_fallback_available`), trả đáp án trích cục bộ với `operational_mode` minh bạch kiểu `local_grounded_fallback` + thông điệp người dùng hiểu được (không hiện lỗi "chưa phản hồi" khi vẫn còn đáp án cục bộ). Nhánh huỷ yêu cầu của user giữ nguyên hành vi hiện tại.

**Bước 4 — Sửa runner E2E (file cục bộ `local_runs/run_app_e2e_pool.py`):** lọc trace theo đúng `conversation_id` của phiên đo thay vì `traces[-1]`; đọc đáp án theo message mới sinh trong phiên thay vì phần tử DOM cuối. Ghi rõ trong báo cáo là file này chỉ ở máy nhà, không vào git.

**Bước 5 — Cổng repo:** compileall, pytest các file liên quan (router adapter, antigravity bridge, ai_lane, synthesis) + test mới ở Bước 1, cli audit, import app — tất cả PASS. Tương thích Python 3.11.

**Bước 6 — Nghiệm thu dùng thật (tiêu chí ĐẠT của vé):** chạy lại đúng kịch bản E2E trên app thật với 3 câu của vé APP-E2E-POOL (Q0699/Q0718/Q0709): cả 3 câu phải HIỆN ĐÁP ÁN (qua pool hoặc fallback minh bạch), 0 câu kết thúc bằng lỗi chết; ghi thời gian toàn trình từng câu + ảnh chụp + đáp án nguyên văn; kiểm băm chỉ mục trước/sau khớp.

## Rào cứng

- Không nới bộ kiểm định tổng hợp; đáp án fallback phải qua đúng đường trích cục bộ hiện có, không tự chế đường tắt.
- Không ghi chỉ mục; không merge `main`; không đổi hành vi các backend `gemini_web`/`cagent_api` ngoài việc nhánh router nói trên.
- Key/API secret: chỉ đọc từ `.env` tại máy, không chép giá trị vào bất kỳ file/log/báo cáo nào.
- Vé dài: mốc tiến độ tối thiểu 15 phút/lần vào `trang-thai.md` mailbox-agy + checkpoint để ca sau resume được.
