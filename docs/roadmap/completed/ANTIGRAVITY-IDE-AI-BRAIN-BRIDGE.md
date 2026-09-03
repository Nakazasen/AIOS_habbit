# Thẻ Cổng: Cầu Nối Não Bộ AI Antigravity IDE (Gate Card: Antigravity IDE AI Brain Bridge)

Status: `DONE — 2026-09-04`

Owner role: Architecture / AI Systems Engineer

Last reviewed: 2026-09-04

Review cadence: Post-implementation verification

## 1. Mục Đích & Kết Quả (Purpose & Outcome)

Thiết lập một cầu nối AI cục bộ trực tiếp, đồng thời cao giữa **AIOS WorkLens (Workspace Chat)** và **Não bộ AI của Antigravity IDE**, cho phép hệ thống tận dụng các mô hình suy luận đỉnh cao (Gemini 2.5 Pro, Claude 3.7 Sonnet, NVIDIA NIM) với cửa sổ ngữ cảnh khổng lồ (1M+ tokens), thời gian phản hồi cục bộ nhanh chóng và khả năng tự động bàn giao (auto-handoff) bền bỉ mà không bị ngắt quãng do giới hạn tốc độ (rate-limit).

---

## 2. Các Artifact & Kiến Trúc Đã Chuyển Giao

1. **Client & Watcher Sidecar Cục Bộ (`src/aios_habit/antigravity_bridge.py`)**:
   - `is_antigravity_bridge_available(health_url)`: Phát hiện trạng thái sức khỏe cục bộ siêu nhanh.
   - `call_antigravity_bridge(question, system_prompt, context_text)`: Gọi chat completion có cấu trúc.
   - `process_pending_ide_handoffs()`: Tự động phát hiện và xử lý các tác vụ outbox chuyên sâu, trả về `response.json` đã kiểm chứng vào inbox.
2. **Dịch Vụ Tiến Trình Nền Sidecar Daemon (`scripts/antigravity_sidecar_daemon.py`)**:
   - Máy chủ HTTP gọn nhẹ lắng nghe trên `127.0.0.1:8585` mở các endpoint `/health` và `/v1/chat/completions`.
   - Luồng chạy nền liên tục theo dõi và tự động giải quyết các gói bàn giao IDE handoff bundle.
3. **Tích Hợp Router & Provider Bridge (`src/aios_habit/workspace_chat_router_adapter.py`, `src/aios_habit/ai_provider_bridge.py`)**:
   - Đăng ký provider `antigravity_ide_brain` với mức ưu tiên định tuyến cấp 1 (tier-1) và tự động chuyển đổi dự phòng trong suốt.
4. **Trạng Thái & Chỉ Báo Giao Diện Workspace Chat (`src/aios_habit/workspace_chat_app.py`)**:
   - Chỉ báo trực tiếp trên header: `🟢 Não bộ Antigravity IDE: Đang kết nối (Frontier AI)` với dự phòng `🔵 Smart Router (Tự động)`.

---

## 3. Bằng Chứng Kiểm Chứng (Verification Evidence)

- **Kiểm thử đơn vị và luồng giao diện**: `89 passed in 21.64s` trên `tests/test_antigravity_bridge.py` và `tests/test_antigravity_handoff_ui_flow.py` vào ngày 2026-09-04.
- **Smoke test thực thi an toàn**: `scripts/smoke_test_real_sidecar_direct.py` đạt kết quả `HOÀN TẤT THÀNH CÔNG VÀ AN TOÀN` (DRY-RUN & verification).
- **Kiểm tra tích hợp runtime**: Import `aios_habit.workspace_chat_app` thành công, FSM trạng thái Sidecar đạt `direct_ready`.
- **Vệ sinh phát hành**: Khởi chạy dễ dàng 1-click qua `start_antigravity_bridge.bat`.
