# Trạng thái mailbox

- Trạng thái: `xong`
- Ticket hiện tại: D3 — baseline B1–B5 (+H3) trên corpus đầy đủ, worker ONNX fp32 (chỉ đọc) — ĐÃ DUYỆT ĐẠT
- Ticket trước: D2 — ĐẠT (commit `20bce54`, Muse review 2026-09-26)
- Commit mới nhất: `fc024d2`
- Cập nhật lần cuối: 2026-09-26 ~16:45 +07 (Muse — D3 ĐẠT, hết kế hoạch ticket D-series, chờ user quyết định bước tiếp)
- Ghi chú: ONNX init 27,46s (<300s); 6/6 câu chạy xong, không abstain/timeout, index không đổi (chỉ đọc đúng quy định). B1/B3/B5 sai đáp án DÙ bằng chứng đúng đã có trong đoạn truy xuất (lỗi ở tầng tổng hợp câu trả lời, không phải retrieval); B2 có đủ 2 tên file nhưng không gán rõ ACR/CTU; B4 loại khỏi chấm điểm (ground truth lệch với tài liệu hiện có). Câu hỏi mở cho user: dọn XML ở extractor? sửa ground truth B4? đổi default backend sang ONNX fp32?
- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_baseline-D3-onnx.md`
