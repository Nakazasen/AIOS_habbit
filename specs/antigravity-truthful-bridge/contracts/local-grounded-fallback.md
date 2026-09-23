# Hợp đồng: Dự phòng Tổng hợp Cục bộ có Trích dẫn

**Spec**: [../spec.md](../spec.md) mục R6 | **Ngày**: 2026-09-23
**Trạng thái**: Chờ thực thi

## 1. Hàm định tuyến — tham số mở rộng

```python
def route_workspace_chat_submission(
    question: str,
    evidence_items: list[dict[str, Any]],
    packed_sources: tuple[Any, ...],
    conversation_id: str,
    notebook_id: str = "",
    # ... các tham số hiện có giữ nguyên ...
    local_synthesis: Optional[Mapping[str, Any]] = None,   # MỚI
) -> tuple[bool, str, Optional[dict[str, Any]], Optional[str]]:
```

**Bất biến**:

1. Chữ ký trả về **không đổi**: vẫn bốn phần tử `(ok, message, badge, error)`.
2. `local_synthesis=None` (mặc định) giữ **nguyên** hành vi cũ ở mọi nhánh.
3. Không nhánh nào gọi mạng vì tham số này.

**Đầu vào `local_synthesis`** (khớp đúng khoá đang có ở `workspace_chat_rag_v2_adapter.py:2279-2293`):

```json
{
  "answer": "chuỗi đáp án trích xuất, có thể chứa [1] [2]",
  "citation_ids": ["[1]", "[2]"],
  "grounded": true,
  "abstained": false,
  "answer_mode": "answer | answer_with_limits",
  "limitation_reasons": ["..."]
}
```

## 2. Nhánh `unavailable` — hành vi mới

**Khi chưa có đáp án cục bộ dùng được** — giữ nguyên hiện trạng:

```
(False, "", None, "Cầu nối Antigravity IDE hiện không khả dụng. Hãy bấm Kết nối lại Gemini Web, rồi gửi lại câu hỏi.")
```

**Khi có đáp án cục bộ dùng được** — cùng chuỗi lỗi, cộng thêm cờ mời trong `badge`:

```json
{
  "conversation_id": "...",
  "type": "local_fallback_offered",
  "local_answer": "chuỗi đáp án trích xuất",
  "local_citation_ids": ["[1]", "[2]"],
  "local_answer_mode": "answer_with_limits",
  "local_limitation_reasons": ["..."],
  "provider_used": false
}
```

**Ràng buộc**:

- `ok` vẫn là `False` — lần gửi này **không** hoàn tất.
- Không tin nhắn nào được ghi ở nhánh này.
- Nhãn không chứa tên mô hình hay tên nhà cung cấp.

## 3. `commit_local_grounded_answer`

```python
def commit_local_grounded_answer(
    *,
    question: str,
    local_answer: str,
    local_citation_ids: Sequence[str],
    evidence_items: list[dict[str, Any]],
    allowed_source_ids: Optional[Sequence[str]] = None,
    notebook_id: str = "",
    conversation_id: str = "",
    answer_language: str = "vi",
) -> tuple[bool, str, Optional[dict[str, Any]]]:
```

Trả về `(ok, message_tiếng_việt, badge)`.

**Khi từ chối** (`ok=False`):

| Điều kiện | Thông báo tiếng Việt | Tin nhắn ghi |
| --- | --- | --- |
| `local_answer` rỗng sau khi cắt khoảng trắng | `Không có bản tổng hợp cục bộ để lưu lúc này.` | 0 |
| Không có `local_citation_ids` | như trên | 0 |
| Thiếu `conversation_id` | `Thiếu định danh cuộc trò chuyện để lưu câu trả lời.` | 0 |
| Dựng hoặc lưu dấu vết lỗi | `Không lưu được câu trả lời cục bộ. Vui lòng thử lại.` | 0 (ghi có hoàn tác theo thứ tự) |

**Khi nhận** (`ok=True`):

- Ghi tin nhắn người dùng, dựng và lưu dấu vết, ghi tin nhắn trả lời, cập nhật huy hiệu.
- Thứ tự ghi: người dùng → dấu vết → trả lời. Nếu bước dấu vết lỗi thì không ghi tin nhắn trả lời.
- `badge["provider_used"]` luôn `False`; `badge["ai_source"]` là chuỗi rỗng.
- **`source_count` và `source_titles` tính theo số trích dẫn THẬT trong đáp án**, không theo số `evidence_items` đã truy xuất. Bộ tổng hợp chỉ trích dẫn đoạn nó thực sự dùng làm căn cứ; đã đo được ca 2 đoạn truy xuất nhưng đáp án chỉ mang `[2]`.

**`badge` khi thành công** (ví dụ với 1 trích dẫn thật):

```json
{
  "conversation_id": "...",
  "type": "ai_answered",
  "source_count": 1,
  "source_titles": ["tên tài liệu của đoạn [2]"],
  "ai_source": "",
  "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
  "operational_mode": "local_grounded_fallback",
  "provider_used": false,
  "trace_id": "..."
}
```

## 4. Nhãn giao diện

| Chuỗi i18n | `vi` | `ja` | `zh-CN` |
| --- | --- | --- | --- |
| `local_fallback_offer_button` | `Xem tổng hợp cục bộ từ trích đoạn` | `ローカル抜粋の要約を表示` | `查看本地摘录汇总` |
| `local_fallback_note` | `Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình` | `ローカル抜粋からの要約 — モデル未使用` | `本地摘录汇总 — 未经模型` |
| `local_fallback_empty_error` | `Không có bản tổng hợp cục bộ để lưu lúc này.` | `保存できるローカル要約がありません。` | `当前没有可保存的本地汇总。` |
| `local_fallback_saved` | `Đã lưu bản tổng hợp cục bộ từ trích đoạn.` | `ローカル抜粋の要約を保存しました。` | `已保存本地摘录汇总。` |

**Ràng buộc**: không nhãn nào chứa tên mô hình, tên nhà cung cấp, hay câu tiếng Anh.

## 5. Điều kiện mời dự phòng (hợp đồng quyết định)

```
mời  ⟺  local_synthesis không rỗng
        VÀ answer.strip() khác rỗng
        VÀ grounded == True
        VÀ abstained == False
        VÀ nhánh định tuyến là "unavailable"
```

Bất kỳ điều kiện nào sai → giữ nguyên hành vi cũ, không hiện gì thêm.
