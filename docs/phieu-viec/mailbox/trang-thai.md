# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé P1.4 — B1–B5 smoke test kho production (tuyến nội bộ).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: 3cb51f0
- `bao_cao`: chưa có (đang dựng tuyến nội bộ + chống ghi D)
- `ghi_chu`: 2026-09-28 21:50 +07 (h410asrock) — khảo sát xong. Tuyến synthesis nội bộ: deterministic/không gọi AI (pipeline dùng `enable_provider_synthesis=False`, `enable_network=False`; máy không có Ollama/LM Studio/`AIOS_LOCAL_AI_*` nào cấu hình). Kho production: 133.144 chunk, 496 document; đã kiểm tra read-only thấy đáp án B1/B2/B3/B5 có trong index, B4 không có (đúng loại trừ). Bước kế: copy index sang C, dựng runner read-only, chạy B1–B5.
- Ticket trước: P1.3 — sao lưu + chép kho production ĐẠT, B1–B5 chưa chạy (báo cáo `docs/phieu-viec/ket-qua/VE_P1_3_dong-dau-kho-that.md`).
