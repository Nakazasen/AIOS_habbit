# Nghiên cứu: Dự phòng tổng hợp cục bộ có trích dẫn khi cầu nối không tới được

**Nguồn**: `specs/antigravity-truthful-bridge/spec.md`, `specs/002-cross-source-synthesis-upgrade/spec.md`
**Ngày**: 2026-09-23
**Trạng thái**: Đã chốt phương án, chờ thực thi

## Vấn đề cần giải

Đường trả lời của Workspace Chat có ba nhánh và **cả ba đều cần một nhà cung cấp câu trả lời**:

| Nhánh | Điều kiện | Hệ quả khi không tới được |
| --- | --- | --- |
| `cagent_api` | có mạng ra endpoint AgentFlow | không trả lời được |
| `nakazasen_router` | có mạng + nguồn xếp `cloud_safe` | mặc định nguồn là `machine_only` nên bị chặn |
| `gemini_web` (cầu nối Antigravity `127.0.0.1:8585`) | tiến trình sidecar chạy | cầu nối chết thì fail-closed |

Nhánh cuối của `route_workspace_chat_submission` (`src/aios_habit/antigravity_bridge.py:1316-1323`) trả về:

```
"Cầu nối Antigravity IDE hiện không khả dụng. Hãy bấm Kết nối lại Gemini Web, rồi gửi lại câu hỏi."
```

Trong khi đó động cơ tổng hợp cục bộ **đã chạy xong và đã bị vứt đi**:

- `src/aios_habit/rag_v2/pipeline.py:941-943` luôn gọi `synthesize_evidence(...)` vì adapter ghim `enable_provider_synthesis: False` (`src/aios_habit/workspace_chat_rag_v2_adapter.py:547`).
- `src/aios_habit/rag_v2/bge_subprocess_worker.py:129-137` tuần tự hoá kết quả thành `synthesis`.
- `src/aios_habit/workspace_chat_rag_v2_adapter.py:2279-2293` đóng gói thành `result["local_synthesis"]`.
- `src/aios_habit/workspace_chat_app.py:1141-1165` (trong `_run_chat_turn_async`) **chỉ đọc** `status`, `summary_count`, `retrieved_context_sources`, `evidence_items`, `safe_owner_message` — rồi chuyển thẳng sang `route_workspace_chat_submission`.

Grep toàn kho xác nhận: `local_synthesis` chỉ được đọc bởi công cụ chạy ngoài giao diện (`scripts/battle_notebooklm_rag_v2.py:3153`, `scripts/audit_rag_quality_plateau.py:76`). **Không** nơi nào trong Workspace Chat đọc.

## Phát hiện quyết định tính khả thi

Nhãn trích dẫn của đáp án cục bộ **khớp chính xác** với `citation_id` của `evidence_items`, nên không cần cơ chế trích dẫn mới:

| Bước | Vị trí | Giá trị |
| --- | --- | --- |
| Đặt nhãn | `src/aios_habit/rag_v2/evidence.py:653` | `citation_id = f"[{rank}]"` |
| Truyền qua worker | `src/aios_habit/rag_v2/bge_subprocess_worker.py:71` | `"citation_id": item.citation_id` |
| Vào giao diện | `src/aios_habit/workspace_chat_rag_v2_adapter.py:2184` | `"citation_id": citation_id` |
| Đối chiếu dấu vết | `src/aios_habit/evidence_trace.py:195-228` | khoá `[{idx}]` khớp chữ trong `answer_text` |

Kết luận: nếu đáp án cục bộ được đưa lên giao diện cùng `evidence_items`, `build_evidence_trace_from_citations` sẽ cho `status="valid"` và canvas đồ thị bằng chứng dựng được — tính năng đồ thị vốn đã có, không phải viết mới.

### Đã chứng minh bằng thực nghiệm (2026-09-23)

Probe `local_runs/smoke_007_t037/probe_fallback_feasibility.py` (không commit) dựng pack hai tài liệu, chạy `synthesize_evidence`, rồi đi đúng đường mà kế hoạch sẽ đi:

| Bước kiểm | Kết quả |
| --- | --- |
| `grounded` / `abstained` / `provider_used` | `True` / `False` / `False` |
| Nhãn trích dẫn của đáp án là tập con của nhãn trong pack | `True` |
| `build_evidence_trace_from_citations` → `status` | `valid`, `cited_count=1` |
| Nút và liên kết dấu vết | 4 nút (`question`, `answer`, `citation`, `source`), 3 liên kết |
| `build_evidence_graph_view_model` → `is_insufficient` | `False`; thống kê `4 nút · 3 liên kết` |

**Phát hiện quan trọng làm đổi chi tiết hợp đồng**: bộ tổng hợp **không** trích dẫn mọi đoạn đã truy xuất — nó chỉ trích dẫn đoạn thật sự dùng làm căn cứ. Trong probe, 2 đoạn được truy xuất nhưng đáp án chỉ mang `[2]`. Đây là hành vi đúng (trung thực về căn cứ), nhưng có hai hệ quả phải ghi vào hợp đồng và kiểm thử:

1. `badge["source_count"]` trong hợp lệnh ghi **phải** tính theo số trích dẫn thật (`len(citation_ids)`), không phải theo số `evidence_items` đã truy xuất.
2. `FR-029` không được từ chối chỉ vì tập trích dẫn nhỏ hơn tập đã truy xuất. Điều kiện từ chối duy nhất là đáp án rỗng hoặc không có trích dẫn nào.
3. Smoke S9 hiện kiểm 6 thực thể (2 trích dẫn + 2 nguồn); với đường dự phòng số đó có thể là 1 trích dẫn + 1 nguồn. Kịch bản dự phòng phải kiểm **có ít nhất một** nhóm trích dẫn và nguồn, không ghim số cứng.

## Quyết định

### Q1 — Chèn ở đâu

**Chọn**: thêm tham số tuỳ chọn `local_synthesis: Optional[Mapping[str, Any]] = None` vào `route_workspace_chat_submission`, và truyền từ `_run_chat_turn_async`.

**Vì sao**: `route_workspace_chat_submission` bị gọi ở **hơn ba mươi chỗ trong test** (`tests/test_antigravity_bridge.py`, `tests/test_antigravity_handoff_ui_flow.py`) và luôn dùng chữ ký 4 tham số trả về. Tham số có mặc định `None` giữ nguyên hành vi cũ khi không truyền, nên không test nào phải sửa.

**Loại bỏ**: đổi chữ ký trả về thành 5 phần tử — phá hơn ba mươi lời gọi và không đem lại lợi ích gì.

### Q2 — Tự động hiện hay mời người dùng

**Chọn**: **mời người dùng trước** (người dùng đã chốt).

Cầu nối chết vẫn báo lỗi đúng như hiện nay; kèm theo một nút `Xem tổng hợp cục bộ từ trích đoạn`. Chỉ khi người dùng bấm mới ghi đáp án vào hội thoại.

**Vì sao**: đáp án trích xuất đọc khô hơn đáp án mô hình. Người dùng đang trong xưởng cần biết rõ mình đang xem loại đáp án nào, không bị đưa một đáp án trông giống hệt nhưng thực chất khác.

**Loại bỏ**: tự động hiện — không phải lựa chọn của người dùng. Thêm cờ cấu hình bật/tắt — thêm thành phần không phục vụ tiêu chí nghiệm thu nào (trái luật chống thiết kế quá mức, `AGENT_RULES.md` mục 5).

### Q3 — Ghi đáp án bằng đường nào

**Chọn**: hàm mới `commit_local_grounded_answer(...)` trong `src/aios_habit/antigravity_bridge.py`, dùng lại `save_message` + `build_evidence_trace_from_citations` + `save_evidence_trace` — đúng bộ ba mà nhánh `cagent_api` và nhánh `direct` đang dùng.

**Vì sao**: ba nhánh hiện có đã có một mẫu ghi vết thống nhất. Thêm một mẫu thứ tư là dựng quy ước thứ hai.

### Q4 — Nhãn hiển thị

**Chọn**: đáp án cục bộ mang nhãn tiếng Việt cố định `Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình`, kèm số đoạn trích và `answer_mode` khi là `answer_with_limits`.

**Vì sao**: `FR-021` của spec này buộc chỉ gắn nhãn nguồn AI khi câu trả lời thật sự đến từ AI. Đáp án cục bộ không đến từ mô hình, nên không được mang nhãn `Antigravity IDE` hay bất kỳ tên mô hình nào.

### Q5 — Có gọi nhà cung cấp nào không

**Không**. Đường dự phòng chỉ đọc dữ liệu đã truy xuất trong máy. `SC-006` của spec này (0 lời gọi dự phòng ra Smart Router) giữ nguyên hiệu lực.

## Phương án đã cân nhắc và loại bỏ

| Phương án | Lý do loại |
| --- | --- |
| Bật `enable_provider_synthesis` để pipeline tự gọi mô hình | Trái ràng buộc cục bộ của pipeline; `pipeline.py:199-200` chặn thẳng. Còn phải mở đường mạng. |
| Trả đáp án cục bộ ngay trong `route_workspace_chat_submission` như thể thành công | Nói dối về nguồn gốc — trái nguyên tắc trung thực của chính spec này. |
| Sinh văn bản mới bằng mô hình nhỏ cục bộ | Cần thêm model pack; chưa có tiêu chí nghiệm thu nào đòi. Thừa thành phần. |
| Dùng kênh handoff để người dùng tự dán vào IDE | Chậm, cần thao tác ngoài; đã có sẵn nhưng không giải quyết ca mất mạng. |

## Rủi ro tồn dư

- Đáp án trích xuất không tổng hợp được như mô hình. Nhãn phải nói rõ để người dùng không nhầm mức độ tin cậy.
- `answer_mode` có thể là `answer_with_limits`; khi đó phải hiện `limitation_reasons` thay vì bỏ qua.
- Nếu `abstained=True` thì không có gì để mời — phải giữ nguyên lỗi cầu nối đơn thuần, không hiện nút rỗng.
