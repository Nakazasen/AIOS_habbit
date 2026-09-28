# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé E2 — Fix synthesis theo E1 + chạy lại B1–B5 (B4 loại).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: 0c993eb
- `bao_cao`: chưa có (vé 2 phase — Phase B chưa được phép chạy)
- `ghi_chu`: 2026-09-29 00:26 +07 (h410asrock) — **Mốc 2: pre-flight read-only xong** (chưa chạy B1–B5). SHA-256 kho D `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` khớp P1.4 (2.552.659.968 byte, mtime 28/09 05:55) → D nguyên vẹn, chưa byte nào đổi. Bản copy C `C:\AIOS_p1_4\tri_thuc\library.sqlite` còn nguyên cùng kích thước; C chỉ còn **2,7 GB** nên Phase B sẽ tái dùng bản copy này (không chép mới). **Khóa provider CÒN trong env** (GEMINI/OPENROUTER/GROQ/DEEPSEEK/MISTRAL/CHATANYWHERE/NVIDIA×2) và `provider_configs_from_env()` hiện dựng được 6 provider → điều kiện kiểm chứng fail-closed của vé có thật. Cache xác minh model fp32 tươi (không ghi lại lên D), onnxruntime 1.28.0 / Python 3.11.14, harness `scratch/p1_4_*.py` + bộ câu hỏi B1–B5 đủ. Cổng Phase B vẫn **CHƯA mở** (không có `e2_fix_commit`, thiếu `E1_synthesis-dieu-tra-dot2.md`) → OMP đứng chờ Phase A của Muse, không tự chạy Phase B.
- Ticket trước: P1.4 — B1–B5 smoke test kho production ĐẠT, P1.3 đóng (báo cáo `docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`).
