> **PHỤ LỤC PHÁT HÀNH LẠI — 2026-10-05 ~18:50 +07 (điều phối Muse):** Đây là lần phát hành thứ 2 của vé này, sau khi index production `e54c7745…` đã **MẤT không khôi phục được** (vé `RECOVER-RUNTIME-PC0575` verdict KHÔNG KHÔI PHỤC ĐƯỢC) và máy đang chạy **index TẠM `062ec090`** (2.552.659.968 B, md5 `7392ef9a54d82926f59569a9e664458f`, đặt tại `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`; vé `RESTORE-DRIVE-PC0575` verdict Muse **ĐẠT** — audit `Status: PASS`, smoke 1 câu thật ĐẠT).
>
> - Mọi chỗ trong vé gốc ghi "index SHA `e54c7745…`" nay đọc là **"đường dẫn index production, hiện đang chứa bản TẠM `062ec090`"**; tiêu chí "không được đổi index" nay là **"không được đổi/ghi bậy vào bản TẠM đang chạy"** (verify md5 trước/sau, mọi số đo ghi rõ **bản TẠM**).
> - **Rào từ báo cáo `restore-drive-pc0575.md`:** hội thoại sổ LSU (`NB-E35A7BEE` — 0/494 nguồn khớp text-hash với index TẠM) **không dùng được** để đo parity/câu lạnh: mở hội thoại có nguồn chưa khớp khiến app chuẩn bị lại và **GHI vào index**. Chỉ đo trên hội thoại có nguồn khớp index TẠM (vd nhóm `mom_opcenter`, 16 nguồn khớp — như `CONV-4D340116`/`SRC-2441B1A3` đã smoke ĐẠT), hoặc đo riêng phần khởi động worker; muốn đo đúng 6 câu LSU cần index khớp bản nguồn hiện tại (vé rebuild riêng, chưa có — không làm trong vé này).
> - Số đo tham chiếu trên bản TẠM (đĩa máy đang chậm hơn baseline): worker init lượt sạch ~10,5 phút, 1 câu hỏi ~6,5 phút (baseline sạch 02/10 trên bản cũ: init 180,9 s).

---

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
