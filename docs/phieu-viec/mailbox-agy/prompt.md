# VÉ: BGE-WORKER-FIX-HOME (sửa timeout khởi động worker + tự phục hồi sau lỗi khởi động)

- Mã vé: `BGE-WORKER-FIX-HOME`
- Role gợi ý: DEFAULT (code + test + nghiệm thu dùng thật)
- Máy: nhà h410asrock (code chung nhánh — máy công ty hưởng cùng bản sửa khi cập nhật)
- Báo cáo: `docs/phieu-viec/ket-qua/bge-worker-fix-home.md`
- Căn cứ: báo cáo chẩn đoán `docs/phieu-viec/ket-qua/bge-worker-diag-home.md` (ĐẠT 07/10).

## Gốc lỗi đã chẩn đoán (không chẩn lại)

1. Worker BGE (ONNX fp32) khởi động mất 246–302 giây trên CPU (nạp model 188–214s + preload dense/sparse), trong khi code đặt 2 trần thấp hơn thực tế: `_INIT_TIMEOUT_SECONDS = 300` (lần baseline tràn đúng 2,2s) và `_PERSIST_SPAWN_WAIT_SECONDS = 120` (client bỏ cuộc trước khi worker kịp mở named pipe — model_load một mình đã ≥188s).
2. Độc phiên: một lần timeout là `_last_failure_reason` giữ nguyên, mọi câu sau fail-fast 0,01s không thử lại — mất tìm kiếm ngữ nghĩa cả phiên.

## Việc phải làm

1. **Nới trần theo số đo** trong `src/aios_habit/rag_v2/bge_subprocess_client.py`: `_INIT_TIMEOUT_SECONDS` 300 → **420**; `_PERSIST_SPAWN_WAIT_SECONDS` 120 → **360**. Ghi comment cạnh hằng: căn cứ số đo init 246–302s (báo cáo diag) để người sau không hạ bừa.
2. **Tự phục hồi:** trong `workspace_chat_rag_v2_adapter.py` (và/hoặc registry chuẩn bị nguồn liên quan): khi khởi động worker timeout, KHÔNG giữ cờ lỗi vĩnh viễn cho phiên — lượt hỏi tiếp theo phải được thử khởi động lại worker (xoá `_last_failure_reason`/đánh dấu nguồn ở trạng thái cho phép thử lại). Giữ nguyên hành vi báo lỗi rõ ràng cho lượt đang chạy (không treo im lặng, không bịa đáp án).
3. **Test:** unit test cho (a) các hằng timeout mới; (b) hành vi thử lại: lần 1 timeout → lần 2 được phép kích hoạt lại worker (mock worker thành công ở lần 2 → trả kết quả bình thường); (c) không hồi quy các suite liên quan (rag_v2, adapter).
4. **Nghiệm thu DÙNG THẬT trên app máy nhà (bắt buộc):** phiên mới → hỏi câu C7620 (ngữ nghĩa): ghi thời gian chờ thực tế (kỳ vọng: chờ khởi động một lần rồi CÓ đáp án đúng ngưỡng 70 dot); hỏi tiếp câu ngữ nghĩa thứ hai: kỳ vọng nhanh (worker đã sống). Ghi cả hai vào báo cáo kèm ảnh chụp.

## Rào cứng

- Không đổi backend, không đổi model, không ghi index, không đụng `src/aios_habit/rag_v2/index.py`/`pipeline.py`.
- Cổng kiểm chứng repo: Python 3.11, compileall + pytest liên quan + `cli audit` + import app.
- Không merge `main`.
