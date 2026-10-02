# Vé SPEED-COLDSTART-PC0575 — Sửa câu hỏi lạnh qua UI (~265 giây, bộ đọc khởi động 180,9 giây)

**Mức ưu tiên:** cao nhất (user chốt tốc độ phản hồi là ưu tiên số 1).
**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Xếp hàng:** đứng ĐẦU hàng chờ `mailbox-pc0575` — trước vé KNOWLEDGE-ENRICH-PILOT.

## Bối cảnh (số liệu đã đo, đã verify)

- Vé OPT-RAGV2-SPEED-APP-PC0575 đã ĐẠT; C-Agent đo 6/6 câu: 16,5–45,8 giây/câu.
- NHƯNG câu hỏi LẠNH qua UI (bộ đọc chưa khởi động): người dùng chờ khoảng **265 giây**.
- Bộ đọc khởi động mất **180,9 giây**, vượt cửa sổ chờ **120 giây** của app.
- Luồng warm-up hiện tại **làm nóng sai collection** (không phải collection đang dùng).
- Trong phần tìm kiếm, `eligibility scan` + `chunks_fts MATCH` vẫn là đoạn chậm.

## Yêu cầu

1. **Đo chi tiết** 180,9 giây khởi động gồm những thành phần nào (nạp model, mở index/SQLite, khởi tạo embedding runtime, …). Ghi bảng thời gian từng bước.
2. **Sửa warm-up làm nóng đúng collection** production (`workspace_chat_rag_v2_production`, index SHA `e54c7745…`). Cấm để cơ chế warm-up trỏ nhầm collection như hiện tại.
3. **Đồng bộ cửa sổ chờ:** hoặc app chờ đủ lâu để bộ đọc sẵn sàng (đồng bộ readiness), hoặc rút khởi động xuống dưới 120 giây, hoặc giữ worker sống giữa các câu hỏi (không khởi động lại mỗi lần). Mục tiêu: **câu hỏi lạnh đầu tiên < 60 giây**.
4. Đo lại đầy đủ 6 câu hỏi L1–E3 từ trạng thái lạnh hoàn toàn (khởi động app sạch → hỏi ngay), ghi thời gian từng câu, so với mốc 265 giây cũ.
5. Không được đổi index (SHA `e54c7745…` phải giữ nguyên), không được giảm chất lượng đáp án (parity 100%, E1 khớp 15/15).

## Điều kiện nghiệm thu

- Câu lạnh đầu tiên ≤ 60 giây, các câu sau giữ trong biên 16,5–45,8 giây/câu đã đạt.
- Parity 100% trước/sau; đáp án 15/15 E1 khớp với đáp án của vé SPEED đã duyệt.
- Bảng thời gian từng bước khởi động trước/sau.

**Verdict:** Muse review trên bằng chứng độc lập. Nếu khởi động vật lý không rút xuống dưới cửa sổ được (giới hạn máy), phải chứng minh cơ chế giữ worker sống + readiness probe hoạt động ổn định qua nhiều lần khởi động app.
