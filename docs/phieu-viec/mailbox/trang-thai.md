# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: Vé E2 — Fix synthesis theo E1 + chạy lại B1–B5 (B4 loại).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: b00bd95
- `e2_fix_commit`: 58ec138
- `bao_cao`: `docs/phieu-viec/ket-qua/VE_E2_fix-synthesis.md`
- `ghi_chu`: 2026-09-29 00:33 +07 (h410asrock) — **Phase B xong, chờ Muse duyệt. Kết quả: CHƯA ĐẠT** (rớt đúng 1 trong 2 dòng kiểm then chốt). B3 **đã qua**: câu trả lời nêu nguyên văn `nvarchar(4000)`. B5 **vẫn rớt**: đoạn `[12]` (doc `wsc-ff8304af86028eaa474a1706`, 371 ký tự, vị trí 11/19 trong pack, `score=1.0`) có nguyên văn `19 格納方法 HOUSE_METHOD varchar '0':倉庫へ格納'1':検査` nhưng câu trả lời chỉ trích `[3]`,`[17]`,`[16]`,`[11]`,`[9]` → rớt ở khâu chọn dòng, không phải truy xuất. Cảnh báo chấm máy: chữ `'1'` trong câu trả lời B5 là của trường `RECEIVE_TYPE`, không phải `HOUSE_METHOD`. Điểm mới ngoài tiêu chí vé: **B2 thoái lui** so với P1.4 (mất `YY2-Z151.exe`/`YY2-Z152.exe` dù đoạn `[1]`, `score=29.0`, có). Các tiêu chí còn lại ĐẠT: B1–B5 chạy xong không lỗi/không timeout (52,75/21,55/17,51/46,39/24,92 giây, B4 loại), grounded, `provider_used=false` cả 5 câu; **không ghi D** (SHA kho D sau chạy vẫn `062ec090…`, 2 lượt snapshot 0 thay đổi, SHA bản copy C khớp nguồn); **fail-closed chứng minh được** — env còn 6 khóa (nếu thiếu fix thì dựng được 6 provider cloud), `create_synthesis_provider()` vẫn trả `None`, stderr worker 1 dòng / **0 dòng gọi provider**, 44 mẫu mạng = **0 kết nối**. Phụ: 61 test passed trên máy này (Windows, Python 3.11.14). Đính chính giờ đã ghi sai trước đó: mốc 2–4 thật là 00:14:38 / 00:16:11 / 00:22:01.
- Ticket trước: P1.4 — B1–B5 smoke test kho production ĐẠT, P1.3 đóng (báo cáo `docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`).
