# Ticket hiện tại — Verify worker ONNX fp32 hết timeout + chạy lại B1–B5 (Bước C)

> OMP đọc kỹ `QUY-UOC.md` trước. Ticket này CHỈ LÀM Bước C. Xong thì commit +
> push + cập nhật `trang-thai.md` thành `xong-cho-duyet`, rồi DỪNG.
> Bước A ĐẠT (commit `ea195c1`). Bước B ĐẠT (commit `23ca36e`: 340/340 vector
> đã migrate sang fingerprint ONNX `016c5255…`, pending 0, backup mới
> `library.sqlite.bak-20260926-1142` integrity ok).
> Bước C KHÔNG ghi index — chỉ đọc + chạy query. Không chạy script migrate.

## Bối cảnh

- Branch: `phieu-viec/rag-fix1`. Không đụng `main`.
- Diagnostic `1488e77`: worker với `BGE_BACKEND=onnx` từng timeout sau 300 s ở
  init vì `_ensure_embeddings` coi 340 chunk fingerprint PyTorch là pending và
  re-embed toàn index (1,6–22,8 s/chunk).
- Sau Bước B, 340 chunk đã có vector ONNX đúng fingerprint → kỳ vọng init
  không còn re-embed, hết timeout.
- Baseline PyTorch để đối chiếu: báo cáo `docs/phieu-viec/ket-qua/` của commit
  `484ac76` (13 câu A/B/H chạy worker PyTorch, init 97,18 s).

## Bước C — Bật worker ONNX, đo init, chạy lại B1–B5, rồi DỪNG chờ duyệt

### C1. Khởi động worker với backend ONNX, đo thời gian init

- Lệnh: `BGE_BACKEND=onnx` + lệnh khởi động worker như các lần nghiệm thu trước
  (cùng index canary máy nhà
  `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`).
- Ghi lại thời gian init (cold). Tiêu chí: **< 300 s** (không timeout).
- Nếu init vẫn vượt 300 s: DỪNG NGAY, không retry mù, báo cáo log init
  (fingerprint backend, pending count nếu có) rồi chờ chỉ đạo.
- Tuyệt đối không xóa/sửa vector PyTorch cũ trong index.

### C2. Chạy lại 5 câu B1–B5 (và H3 nếu nhanh), đối chiếu với baseline PyTorch

- Chạy B1–B5 trên worker ONNX (cả hai flag summary-first + provenance bật như
  lần `484ac76` để so sánh công bằng).
- Ghi cho mỗi câu: mode (overview/hybrid/full), latency, đáp án tóm tắt,
  so với đáp án baseline PyTorch ở `484ac76` (giống/khác gì).
- Không cần so on/off flag — chỉ so backend onnx vs pytorch.

### C3. Báo cáo + bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX2_onnx-worker-verify.md`, gồm:
  hostname, đường dẫn index, thời gian init ONNX (so với timeout 300 s và
  init PyTorch 97,18 s), bảng B1–B5 (latency + đáp án onnx vs pytorch),
  kết luận timeout còn hay hết.
- Commit RIÊNG cho Bước C, push branch `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md`: `xong-cho-duyet` + ghi commit SHA + đường dẫn báo cáo.
- DỪNG. Chờ review xong mới có ticket tiếp theo (quyết định có bật ONNX
  mặc định hay không — ngoài phạm vi Bước C).

## Ngoài phạm vi Bước C

- Mọi ghi/sửa/xóa trên index (migration đã xong ở Bước B).
- Đổi default backend, bật flag cho production, dọn model PyTorch/ONNX.
- Sửa code runtime vì timeout (nếu còn timeout thì báo, không tự sửa).
