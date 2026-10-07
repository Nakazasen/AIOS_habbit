# VÉ: APP-SOURCE-MODEL-PC0575 (một nguồn sự thật cho tài liệu — gỡ các con số mâu thuẫn)

- Mã vé: `APP-SOURCE-MODEL-PC0575`
- Role gợi ý: PLAN trước (rà soát mô hình + đề xuất), điều phối duyệt hướng mới code.
- Máy: công ty KDTVN-PC0575
- Báo cáo: `docs/phieu-viec/ket-qua/app-source-model-pc0575.md`
- Điều kiện bốc vé: xếp hàng #1 mailbox opencode PC0575 (trước `APP-OPEN-PERF-PC0575` — vé đó phải chờ kết luận của vé này cho phần liên quan "chuẩn bị tài liệu").
- File chính: `src/aios_habit/workspace_chat_app.py` + tầng nguồn của workspace chat. KHÔNG đụng `src/rag_v2*` (WIP agy).

## Bối cảnh (user chỉ ra trực tiếp 07/10 kèm ảnh, và user ĐÚNG)

Trên cùng một màn hình app hiện đồng thời: sổ có **494 tài liệu** / "Nguồn đang bật: **35**" / "hỏi đáp bình thường với **33 tài liệu** đã sẵn sàng" / "Đã chuẩn bị xong **33/35 (94%)**". User hỏi: *tài liệu đã index xong rồi, người dùng chỉ cần chọn khối tri thức để hỏi đáp — tại sao còn tồn tại đống con số tài liệu mâu thuẫn này?*

Rà soát sơ bộ của điều phối trong code đã thấy hai lớp chồng nhau:
1. **Chỉ mục tri thức** (rag_v2): 889 tài liệu đã cắt mảnh + nhúng sẵn — hỏi là tra được ngay.
2. **Tầng "nguồn" theo cuộc trò chuyện/sổ**: nguồn phải "bật/tắt" (`set_source_enabled`, `load_enabled_sources_for_conversation`) và phải "chuẩn bị" lại (`reconcile_and_enqueue_workspace_chat_sources`, trạng thái chuẩn bị 33/35) — sổ sách nội bộ của lớp này rò rỉ hết lên giao diện thành các con số mâu thuẫn, và chính việc "chuẩn bị" này ăn CPU trên đường mở sổ (liên quan vé APP-OPEN-PERF).

## Việc phải làm

### Chặng 1 — Rà soát + đề xuất (chỉ đọc, nộp báo cáo chặng trước khi code)
1. Vẽ bản đồ vòng đời tài liệu: một tài liệu đi từ đâu (thư viện sổ / tệp tải lên / chỉ mục) → qua những trạng thái nào (bật/tắt, chuẩn bị, sẵn sàng) → khi hỏi thì đường trả lời đọc từ đâu (chỉ mục rag_v2 hay kho riêng của workspace). Trả lời dứt khoát: 494 / 35 / 33 mỗi con số đếm cái gì, ở lớp nào; việc "chuẩn bị" ghi vector vào đâu — có trùng lặp với chỉ mục 889 không.
2. Đề xuất mô hình hợp nhất theo hướng user chốt: **tài liệu đã có trong chỉ mục = sẵn sàng tức thì** (không chuẩn bị lại, không đếm chuẩn bị); "chuẩn bị" chỉ còn cho tệp mới thật sự chưa index, chạy nền im lặng như đường ống nội bộ; giao diện chỉ còn tối đa **một con số có nghĩa duy nhất** (số tài liệu của khối tri thức đã chọn) hoặc không con số nào.
3. Báo cáo chặng 1 vào file báo cáo + đặt mốc trong mailbox chờ điều phối duyệt hướng. Chưa duyệt thì không code chặng 2.

### Chặng 2 — Code theo hướng đã duyệt (chỉ khi điều phối ghi duyệt vào mailbox)
1. Hỏi đáp trên sổ mặc định chạy trên chỉ mục cho tài liệu đã index; gỡ các banner/đếm mâu thuẫn ("đang chuẩn bị N tài liệu", "33/35", các con số trùng lặp giữa sidebar và khối quản lý) — một chỗ hiển thị, một ý nghĩa.
2. Giữ nguyên chất lượng trả lời và các rào an toàn dữ liệu hiện có; tệp tải lên ad-hoc vẫn dùng được (đi đường chuẩn bị nền im lặng).

## Kiểm chứng (theo luật nghiệm thu SỬ DỤNG THẬT)

- Mở sổ LSU trên app thật: tài liệu đã index sẵn sàng ngay, không bão chuẩn bị; hỏi 3 câu thật, đáp án + thời gian ghi vào báo cáo; ảnh trước/sau của đúng màn hình user đã chụp.
- Cổng repo phụ trợ: compileall + pytest liên quan + `cli audit`; Python 3.11.
