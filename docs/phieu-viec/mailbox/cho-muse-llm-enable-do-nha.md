# Cho-muse: LLM-ENABLE-DO-NHA — chẩn đoán kẹt probe + cách gỡ

- Thời gian: 2026-10-02 ~23:10 +07. Watcher escalate lúc 23:04 sau 4 lần mở OMP không tiến triển (process OMP dừng lúc 23:01).
- Tiến độ đã có (không mất): gate ĐẠT lúc 21:55 — bridge Gemini Web `127.0.0.1:8585` = `direct_ready`, thử 1 câu ra đáp án thật, chọn bridge vì env key lỗi `unknown_error`.

## Chẩn đoán của Muse (kiểm code trên VM)

Probe khả năng crash khi đọc `EvidenceTrace` của đáp án — đúng chỗ OMP đang soi lúc 22:50 (`trace_id`, `metadata["status"]`, `cited_count`):

- `trace.metadata["cited_count"]` → **KeyError khi đáp án có 0 citation hợp lệ.** Builder chỉ gắn `cited_count` khi số citation > 0; khi bằng 0 thì metadata chỉ có `status="insufficient_evidence"` (xem `src/aios_habit/evidence_trace.py`, đoạn builder quanh dòng 276–290).
- `trace.metadata["status"]` → nếu trace đi qua đường dựng khác có thể không có key này.

Cách đọc an toàn cho probe:

```python
status = trace.metadata.get("status", "unknown")
cited = trace.metadata.get("cited_count", 0)
trace_id = trace.trace_id or ""
```

## Việc cần làm (OMP, máy nhà)

1. Pull nhánh mới nhất (có note này).
2. Sửa probe theo mẫu đọc an toàn ở trên, chạy lại đo 6 câu L1–E3.
3. Nếu probe vẫn lỗi: paste **traceback đầy đủ** vào báo cáo, không đoán mò, không viết lại probe từ đầu khi chưa rõ lỗi.
4. Gate đã qua — chỉ còn phần đo 6 câu + báo cáo `docs/phieu-viec/ket-qua/llm-enable-do-nha.md`, rồi `xong-cho-duyet`.

## Ghi chú vận hành

- OMP đang dừng (watcher không tự mở lại sau escalate). User mở lại OMP ở máy nhà để nó pull và đọc note này.
