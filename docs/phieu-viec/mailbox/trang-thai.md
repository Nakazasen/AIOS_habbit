# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé P1.4 — B1–B5 smoke test kho production (tuyến nội bộ).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: 3af665b
- `bao_cao`: chưa có (đang chạy B1–B5 trên bản copy C)
- `ghi_chu`: 2026-09-28 23:21 +07 (h410asrock) — copy index production D→C xong (2.552.659.968 byte, SHA `062ec090…` khớp bản P1.3, 42,5s). Runner read-only đã dựng (`scratch/p1_4_smoke.py`, worker BGE subprocess như app, `enable_network=False`/`enable_provider_synthesis=False`). Chốt backend đúng: ONNX fp32 (`BGE_BACKEND=onnx`) — vector trong index mang fingerprint `016c5255…` do class ONNX với cây model fp32 sinh ra (nhãn runtime bị gán cứng `onnxruntime-int8`). Chỉ 74/496 document có file khớp fingerprint; các document đáp án B1/B2/B3/B5 đều nằm trong nhóm khớp. Đang chạy B1–B5.
- Ticket trước: P1.3 — sao lưu + chép kho production ĐẠT, B1–B5 chưa chạy (báo cáo `docs/phieu-viec/ket-qua/VE_P1_3_dong-dau-kho-that.md`).
