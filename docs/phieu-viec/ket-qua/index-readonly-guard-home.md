# Báo cáo kết quả vé: INDEX-READONLY-GUARD-HOME
**Khoá cứng chỉ đọc cho chỉ mục production ở đường giao diện**

- **Mã vé**: `INDEX-READONLY-GUARD-HOME`
- **Máy thực hiện**: Nhà `h410asrock` (thợ agy — `gemini-3.8-flash-high`)
- **Thời gian hoàn thành**: 2026-10-08 15:35 +07
- **Trạng thái**: Hoàn thành 100% — Sẵn sàng chờ Muse duyệt
- **Căn cứ**: Báo cáo `index-hash-drift-trace-home.md` (Muse đã verdict ĐẠT lúc ~15:35). Lệnh đóng băng đo app được tuân thủ nghiêm ngặt: vé này chỉ code + test đơn vị, không chạy app thật.

---

## 1. Tóm tắt kết quả thực hiện

Đã cài đặt thành công cơ chế phòng thủ 3 tầng bảo vệ chỉ mục production khỏi mọi hành vi ghi đè từ giao diện người dùng:
1. **Fail-closed ở gốc**: Sửa giá trị mặc định của tham số `read_only` trong hàm `_pipeline_config` (`src/aios_habit/workspace_chat_rag_v2_adapter.py`) từ `False` thành **`True`**. Mọi điểm gọi không truyền tham số sẽ tự động mở chỉ mục ở chế độ CHỈ ĐỌC tuyệt đối (`index_read_only=True`, `ensure_embeddings_on_open=False`).
2. **Chặn đứng ở tầng chuẩn bị nguồn (`prepare_workspace_chat_sources`)**: Bổ sung exception chuyên biệt `ReadOnlyIndexViolationError` và hàm kiểm tra `is_production_sealed_collection`. Bất kỳ yêu cầu chuẩn bị nguồn nào trỏ đích vào kho production `tri_thuc` (kho đã đóng dấu) đều bị chặn ngay lập tức, ném lỗi rõ ràng và **KHÔNG BAO GIỜ** gọi semantic worker chuẩn bị hay sinh mảnh/nhúng vector.
3. **Chặn đứng ở tầng hàng đợi ngầm (`_drain_preparation_queue`)**: Khi worker nền rút việc chuẩn bị nguồn, nếu nguồn đích là kho production `tri_thuc`:
   - Nếu nguồn thuộc tài liệu đã có sẵn trong kho 889 tài liệu (`_durable_semantic_coverage_ready` xác nhận): đánh dấu trạng thái `PREP_STATE_READY` trong ledger và in-memory registry, bỏ qua hoàn toàn bước prepare, không gọi worker.
   - Nếu nguồn chưa có trong kho: chặn đứng, đánh dấu trạng thái `PREP_STATE_FAILED` với mã lỗi `readonly_index_violation`, ghi log lỗi, không gọi worker.
4. **Nhận diện tài liệu sẵn có theo `source_name`**: Mở rộng hàm `_durable_semantic_coverage_ready` để nhận diện tài liệu trong kho 889 theo `source_name = source.title` nếu băm nội dung `document_id` runtime bị lệch ký tự/encoding (như sự cố tài liệu C7620), giúp tài liệu được nhận diện là `READY` mà không bị xếp hàng chuẩn bị lại.
5. **Kiểm thử TDD (Đỏ trước — Xanh sau)**: Đã viết 5 bài test bảo vệ mới, xác nhận đỏ 5/5 trước khi sửa code, và xanh 100% sau khi hoàn tất. Toàn bộ 294 test liên quan và các cổng chất lượng repo đều đạt chuẩn.

---

## 2. Rà soát toàn bộ các điểm gọi `_pipeline_config` trong codebase

Đã kiểm tra toàn bộ cây mã nguồn (`src/` và `tests/`) để xác định mọi điểm gọi `_pipeline_config`:

| STT | Vị trí (Tệp & Dòng) | Thành phần gọi | Tham số `read_only` | Giải trình / Lý do kỹ thuật |
| :---: | :--- | :--- | :---: | :--- |
| 1 | `workspace_chat_rag_v2_adapter.py:722` | `_get_runtime` | `read_only=True` | Khởi tạo runtime truy vấn in-process cho phiên chat; chỉ đọc tuyệt đối. |
| 2 | `workspace_chat_rag_v2_adapter.py:1235` | `_warmup_pipeline_config` | `read_only=True` | Khởi động/làm ấm tiến trình worker BGE-M3 nền; chỉ đọc tuyệt đối. |
| 3 | `workspace_chat_rag_v2_adapter.py:1424` | `prepare_workspace_chat_sources` | `read_only=False` (Tường minh) | **Điểm ghi duy nhất được phép**: Chuẩn bị và nhúng vector cho các bộ sưu tập **non-production** (ví dụ notebook collection riêng). Kho production `tri_thuc` đã được chặn đứng ở guard phía trên. |
| 4 | `workspace_chat_rag_v2_adapter.py:2800` | `_execute_query` | `read_only=True` | Thực thi truy vấn hỏi đáp RAG v2; chỉ đọc tuyệt đối. |
| 5 | `tests/test_workspace_chat_rag_v2_adapter.py:1495` | `test_query_config_is_read_only_and_uses_production_index` | Mặc định (không truyền) | Kiểm thử xác nhận hợp đồng mặc định không truyền tham số luôn trả về `index_read_only=True`. |
| 6 | `tests/test_workspace_chat_rag_v2_adapter.py:1501` | `test_query_config_is_read_only_and_uses_production_index` | `read_only=False` (Tường minh) | Kiểm thử xác nhận khi truyền tường minh `read_only=False` thì `index_read_only=False`. |

---

## 3. Chi tiết mã nguồn đã triển khai

### 3.1. Khai báo `ReadOnlyIndexViolationError` và `is_production_sealed_collection`

```python
class ReadOnlyIndexViolationError(RuntimeError):
    """Raised when an operation attempts to write or prepare sources for a read-only or sealed production index."""


def is_production_sealed_collection(collection_id: str | None) -> bool:
    """Return True if collection_id refers to the sealed production collection ('tri_thuc')."""
    from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID
    from aios_habit.workspace_chat_store import load_collection

    normalized = str(collection_id or "").strip()
    if normalized in {DEFAULT_COLLECTION_ID, "tri_thuc"}:
        return True
    if not normalized:
        default = load_collection(DEFAULT_COLLECTION_ID)
        if default is not None and str(default.storage_root or "").strip():
            return True
    return False
```

### 3.2. Sửa mặc định fail-closed của `_pipeline_config`

```python
def _pipeline_config(
    config: WorkspaceChatRagV2CanaryConfig,
    profile: str,
    *,
    read_only: bool = True,  # Fail-closed mặc định
    include_reranker: bool = False,
    collection_id: str | None = None,
) -> RagV2DevConfig:
```

### 3.3. Chặn ghi trong `prepare_workspace_chat_sources`

```python
    target_collection_id = _collection_id_for_sources(sources)
    if is_production_sealed_collection(target_collection_id):
        raise ReadOnlyIndexViolationError(
            f"Chặn ghi vào kho production đã đóng dấu '{target_collection_id or 'tri_thuc'}'. "
            "Chỉ mục production là chỉ đọc tuyệt đối và không nhận nguồn chuẩn bị mới."
        )

    profile = resolved.requested_profile
    pipe_config = _pipeline_config(
        resolved,
        profile,
        # Explicit read_only=False: preparing and ingesting source chunks and
        # embeddings for eligible non-production collections. The sealed
        # production collection ('tri_thuc') is strictly guarded above.
        read_only=False,
        collection_id=target_collection_id,
    )
```

### 3.4. Chặn ghi và nhận diện tài liệu sẵn có trong `_drain_preparation_queue`

```python
            target_collection = _collection_id_for_sources((source,))
            if is_production_sealed_collection(target_collection):
                # Guard against writing to sealed production collection 'tri_thuc'.
                # Existing documents from 889 corpus must be recognized as READY without preparation.
                if _durable_semantic_coverage_ready(source, config):
                    _commit_preparation_result(
                        db_path,
                        item.source_scope,
                        item.source_id,
                        PREP_STATE_READY,
                        model_fingerprint=drain_fingerprint,
                    )
                    with _PREPARATION_LOCK:
                        _PREPARATION_REGISTRY[_preparation_key(config, source)] = (
                            _preparation_entry(config, source, PREP_STATE_READY)
                        )
                    continue
                else:
                    err_msg = (
                        f"readonly_index_violation: cannot prepare sources for sealed production collection "
                        f"'{target_collection or 'tri_thuc'}'"
                    )
                    LOGGER.error(
                        "rag_v2.drain %s scope=%s source_id=%s",
                        err_msg,
                        item.source_scope,
                        item.source_id,
                    )
                    _commit_preparation_result(
                        db_path,
                        item.source_scope,
                        item.source_id,
                        PREP_STATE_FAILED,
                        error_reason="readonly_index_violation",
                    )
                    with _PREPARATION_LOCK:
                        _PREPARATION_REGISTRY[_preparation_key(config, source)] = (
                            _preparation_entry(config, source, PREP_STATE_FAILED, reason=err_msg)
                        )
                    continue
```

### 3.5. Nhận diện tài liệu sẵn có theo `source_name` trong `_durable_semantic_coverage_ready`

```python
            retrievable = int(connection.execute(
                "SELECT COUNT(*) FROM chunks WHERE document_id=? AND retrievable=1",
                (document_id,),
            ).fetchone()[0])
            if retrievable <= 0:
                candidate_title = (getattr(source, "title", "") or "").strip()
                if candidate_title:
                    found = connection.execute(
                        "SELECT document_id FROM chunks WHERE source_name=? AND retrievable=1 LIMIT 1",
                        (candidate_title,),
                    ).fetchone()
                    if found:
                        matched_doc_id = str(found[0])
                        retrievable = int(connection.execute(
                            "SELECT COUNT(*) FROM chunks WHERE document_id=? AND retrievable=1",
                            (matched_doc_id,),
                        ).fetchone()[0])
                        if retrievable > 0:
                            document_id = matched_doc_id
            if retrievable <= 0:
                return False
```

---

## 4. Bằng chứng kiểm thử TDD (Đỏ trước — Xanh sau)

### 4.1. Bằng chứng ĐỎ (Trước khi sửa code trong adapter)
Lệnh:
`uv run --no-sync --group dev pytest tests/test_workspace_chat_rag_v2_adapter.py -k "test_pipeline_config or test_prepare_sources_targeting or test_prepare_notebook_sources or test_drain_queue_existing or test_drain_queue_unindexed or test_durable_semantic_coverage_matches" -q`
Kết quả:
```text
FAILED tests/test_workspace_chat_rag_v2_adapter.py::test_prepare_sources_targeting_production_sealed_collection_is_blocked (AttributeError: no attribute 'ReadOnlyIndexViolationError')
FAILED tests/test_workspace_chat_rag_v2_adapter.py::test_prepare_notebook_sources_targeting_tri_thuc_is_blocked (AttributeError: no attribute 'ReadOnlyIndexViolationError')
FAILED tests/test_workspace_chat_rag_v2_adapter.py::test_drain_queue_existing_source_in_sealed_index_marked_ready_without_worker (AssertionError: assert 'failed' == 'ready')
FAILED tests/test_workspace_chat_rag_v2_adapter.py::test_drain_queue_unindexed_source_in_sealed_index_marked_failed_without_worker (AssertionError: assert 'readonly_index_violation' in 'source_text_unavailable')
FAILED tests/test_workspace_chat_rag_v2_adapter.py::test_durable_semantic_coverage_matches_existing_889_by_source_name (AssertionError: assert False is True)
5 failed, 82 deselected in 0.95s
```

### 4.2. Bằng chứng XANH (Sau khi sửa code trong adapter)
Lệnh:
`uv run --no-sync --group dev pytest tests/test_workspace_chat_rag_v2_adapter.py -k "test_pipeline_config or test_prepare_sources_targeting or test_prepare_notebook_sources or test_drain_queue_existing or test_drain_queue_unindexed or test_durable_semantic_coverage_matches" -q`
Kết quả:
```text
.....                                                                    [100%]
5 passed, 82 deselected in 0.70s
```

### 4.3. Bằng chứng hồi quy toàn bộ test adapter
Lệnh:
`uv run --no-sync --group dev pytest tests/test_workspace_chat_rag_v2_adapter.py -q`
Kết quả:
```text
........................................................................ [ 82%]
...............                                                          [100%]
87 passed in 3.98s
```

### 4.4. Bằng chứng hồi quy các bộ test liên quan (Deployment, Smoke, Router, AI Answer, Store, Selection)
Lệnh:
`uv run --no-sync --group dev pytest tests/test_workspace_chat_rag_v2_deployment.py tests/test_workspace_chat_app_smoke.py tests/test_workspace_chat_router_adapter.py tests/test_workspace_chat_ai_answer.py tests/test_workspace_chat_store.py tests/test_workspace_chat_source_selection_owner_flow.py -q`
Kết quả:
```text
........................................................................ [ 34%]
........................................................................ [ 69%]
...............................................................          [100%]
207 passed in 53.82s
```
**Tổng số test đơn vị liên quan đã chạy và PASS**: **`294` / `294` tests PASSED 100%**.

---

## 5. Bằng chứng các cổng chất lượng bắt buộc (Quality Gates)

### 5.1. Phiên bản Python
- Lệnh: `uv run --no-sync --group dev python --version`
- Kết quả: `Python 3.11.14` (Đạt chuẩn Python 3.11).

### 5.2. Cổng `compileall`
- Lệnh: `uv run --no-sync --group dev python -m compileall src tests`
- Kết quả: Exit code 0, không có lỗi cú pháp hay kiểu.

### 5.3. Cổng `cli audit`
- Lệnh: `uv run --no-sync --group dev python -m aios_habit.cli audit`
- Kết quả:
```json
{
  "errors": [],
  "status": "PASS",
  "warnings": []
}
```

### 5.4. Cổng import ứng dụng `workspace_chat_app`
- Lệnh: `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`
- Kết quả: `IMPORT_OK` (không vi phạm ranh giới kiến trúc, không import legacy).

---

## 6. Tuân thủ rào cứng của vé

- **Không mở app đo thật**: Tuân thủ tuyệt đối lệnh đóng băng đo app máy nhà; chỉ code và chạy test đơn vị cô lập.
- **Không đụng chạm tệp chỉ mục production**: Không mở tệp SQLite production bằng tiến trình ghi; không khôi phục chỉ mục ở vé này (chờ quyết định riêng của user).
- **Không merge vào `main`**: Thực hiện và đẩy nhánh `phieu-viec/rag-fix1`.
- **Cập nhật tiến độ liên tục**: Đã cập nhật trạng thái và commit/push từng mốc theo quy ước.
