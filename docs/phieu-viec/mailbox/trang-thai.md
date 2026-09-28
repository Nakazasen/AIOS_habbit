# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé E2 — Fix synthesis theo E1 + chạy lại B1–B5 (B4 loại).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: 5dad312
- `bao_cao`: chưa có (vé 2 phase — Phase B chưa được phép chạy)
- `ghi_chu`: 2026-09-29 00:35 +07 (h410asrock) — **Mốc 3: đã chốt bằng chứng "trước fix", sẵn sàng Phase B** (vẫn CHƯA chạy B1–B5). Probe `scratch/e2_precheck.py` gọi đúng hàm `create_synthesis_provider()` mà worker BGE dùng, **để nguyên khóa provider trong env**: trả về `RouterSynthesisProvider` dựng từ **6 provider cloud** (gemini/openrouter/groq/deepseek/mistral/chatanywhere; model `gemini-2.5-pro`, `deepseek-v4-flash`, …) ⇒ hành vi không an toàn vẫn đang sống trong mã hiện tại; sau Phase A, chạy lại đúng probe này phải ra `is_none=true` mới tính là fail-closed. Phép thử không gọi mạng, không mở index, không ghi D (cây làm việc sạch), chỉ in `provider_id`/`model_name` — không in khóa. Cổng Phase B **vẫn chưa mở**: tip nhánh chỉ có commit phát hành vé + 2 commit tiến độ của OMP, không có commit fix nào của Phase A. (Ghi chú nhỏ: dòng `ghi_chu` bản trước có nhắc nguyên văn tên dấu hiệu mở cổng — đã bỏ để tránh nhầm với dấu hiệu thật.)
- Ticket trước: P1.4 — B1–B5 smoke test kho production ĐẠT, P1.3 đóng (báo cáo `docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`).
