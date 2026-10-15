# BÁO CÁO THỰC THI VÉ: NOTEBOOK-SOURCE-TEXT-FIX-HOME

## 1. THÔNG TIN CHUNG & CẤU HÌNH THỰC THI (BB-CONFIG-PARITY-01)
- **Mã vé:** `NOTEBOOK-SOURCE-TEXT-FIX-HOME` (Làn desktop Antigravity 2.0: `DESKTOP-NOTEBOOK-SOURCE-TEXT-FIX-HOME`)
- **Trạng thái:** `HOAN_THANH`
- **Môi trường thực thi:** `May nha - h410asrock` (CPU-only, tuân thủ biên bản `BB-CONFIG-PARITY-01`: `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `KMP_DUPLICATE_LIB_OK=TRUE`)
- **Kho mã nguồn:** `D:\Sandbox\AIOS_habbit`
- **Nhánh phát triển:** `phieu-viec/rag-fix1`
- **HEAD Commit:** `da7aacc8d8cb0921546feac4d3ffb2e668a07a13`
- **Remote Push:** Đã đẩy thành công lên remote GitHub `https://github.com/Nakazasen/AIOS_habbit.git` tại nhánh `phieu-viec/rag-fix1` (xác thực khớp hash qua `git ls-remote`).

---

## 2. NGUYÊN NHÂN GỐC RỄ & CƠ CHẾ SỬA ĐỔI TẬN GỐC (ROOT CAUSE & REMEDIATION)

### 2.1. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)
- **Điểm phát sinh crash:** Hàm `get_workspace_chat_preparation_summary` trong `src/aios_habit/workspace_chat_rag_v2_adapter.py` duyệt qua `context_sources` bằng biểu thức:
  ```python
  sources = tuple(s for s in context_sources if (s.text or "").strip())
  ```
- **Bất đối xứng mô hình dữ liệu:**
  - Đối tượng `WorkspaceAIContextSource` lưu trong bộ nhớ chat có thuộc tính `.text`.
  - Trong khi đó, đối tượng `NotebookSource` đọc từ SQLite store (`notebooks.sqlite`) chỉ chứa các trường `content_text` và `content_preview`, hoàn toàn **không có thuộc tính `.text`**.
  - Ngoài ra, `NotebookSource` sử dụng `id` (thay vì `source_id`), không mang `source_scope`, và là một mutable dataclass (không thể đưa trực tiếp vào `lru_cache` của `_document_id` hay `_source_fingerprint`).
- **Hậu quả:** Khi một sổ tay có gắn nguồn `NotebookSource` được đưa qua kiểm tra chuẩn bị tài liệu hoặc tóm tắt tiến trình, mã lập tức văng ngoại lệ:
  `AttributeError: 'NotebookSource' object has no attribute 'text'`, làm đứt toàn bộ luồng hỏi đáp trong sổ tay.

### 2.2. Lựa chọn giải pháp sửa ít lan nhất (Least Invasive Decision)
Phiếu việc đưa ra 2 lựa chọn xử lý:
1. Chuẩn hóa truy cập văn bản tại adapter (điểm chạm).
2. Hoặc bổ sung thuộc tính tương đương cho `NotebookSource` ở nơi sinh đối tượng.

**Quyết định:** Chọn **Phương án 1 (Chuẩn hóa tại điểm chạm adapter)** với các lý do:
- **Tuân thủ đúng phân quyền:** Vé quy định rõ `Phân quyền: chỉ sửa điểm truy cập thuộc tính và test liên quan`.
- **Ít lan và an toàn nhất:** Không can thiệp vào schema lưu trữ dataclass `NotebookSource` của SQLite store (`workspace_chat_models.py`), tránh mọi rủi ro thoái lui (regression) ở các tầng serialize/deserialize, migrations hoặc JSON dumping.
- **Tính tự vệ cao (Defensive Programming):** Giúp toàn bộ adapter tiếp nhận an toàn cả `WorkspaceAIContextSource`, `NotebookSource`, `TemporaryConversationSource` lẫn các đối tượng duck-typed mà không bao giờ crash.

### 2.3. Các hàm bổ trợ chuẩn hóa được triển khai
1. `_safe_source_text(source)`: Trích xuất an toàn chuỗi văn bản theo thứ tự ưu tiên: `text` -> `content_text` -> `content_preview` -> `""`.
2. `_safe_source_scope(source)`: Xác định an toàn phạm vi nguồn (`source_scope` -> `SOURCE_SCOPE_NOTEBOOK` nếu có `notebook_id` -> `SOURCE_SCOPE_TEMPORARY`).
3. `_safe_source_id(source)`: Xác định định danh nguồn (`source_id` -> `id` -> `""`).
4. `_coerce_context_source(source)`: Ép kiểu an toàn bất kỳ nguồn nào thành `WorkspaceAIContextSource` đóng băng (frozen, hashable). Nếu đối tượng đã là `WorkspaceAIContextSource` thì trả về ngay lập tức (zero overhead).
5. `_document_id` & `_source_fingerprint`: Ép kiểu nguồn trước khi chuyển vào hàm cached (`_document_id_cached`, `_source_fingerprint_cached`), bảo toàn thuộc tính `.cache_clear`.

### 2.4. Rà soát toàn diện các điểm truy cập thuộc tính nguồn trong adapter
Toàn bộ các điểm giả định nguồn có `.text` hoặc `.source_scope` trong `src/aios_habit/workspace_chat_rag_v2_adapter.py` đã được rà soát và chuẩn hóa:
1. `_document_id`: Đọc văn bản qua `_safe_source_text`, fallback định danh an toàn.
2. `_source_fingerprint`: Đọc văn bản qua `_safe_source_text`, đọc `privacy_label` qua `getattr`.
3. `_select_semantic_candidate_sources`: Ép kiểu nguồn qua `_coerce_context_source`, truy cập `source.text` an toàn.
4. `_maybe_expand_latin_query_for_cjk_corpus`: Đọc văn bản qua `_safe_source_text`.
5. `_retrieval_source_window`: Đọc văn bản qua `_safe_source_text`.
6. `_collection_id_for_sources`: Ép kiểu nguồn qua `_coerce_context_source`.
7. `prepare_workspace_chat_sources`: Ép kiểu `context_sources` qua `_coerce_context_source`.
8. `get_workspace_chat_preparation_summary`: Ép kiểu `context_sources` qua `_coerce_context_source`, khởi tạo map trạng thái và tính toán an toàn.
9. `reconcile_and_enqueue_workspace_chat_sources`: Ép kiểu `context_sources` qua `_coerce_context_source`.
10. `retry_workspace_chat_source_preparation`: Ép kiểu `context_sources` qua `_coerce_context_source`.
11. `resume_workspace_chat_source_preparation`: Ép kiểu `context_sources` qua `_coerce_context_source`.
12. `forget_workspace_chat_sources`: Ép kiểu `context_sources` qua `_coerce_context_source`.
13. `seed_workspace_chat_source_preparation`: Ép kiểu `context_sources` qua `_coerce_context_source`.
14. `_materialize_sources`: Ép kiểu nguồn qua `_coerce_context_source`.
15. `_query_retrieval_v2`: Tra cứu trạng thái nguồn sẵn sàng qua `_safe_source_scope` và `_safe_source_id`.
16. `retrieve_workspace_chat_evidence`: Tra cứu trạng thái nguồn sẵn sàng qua `_safe_source_scope` và `_safe_source_id`.

---

## 3. ĐOẠN TRÍCH NGUYÊN VĂN MÃ NGUỒN SỬA ĐỔI (VERBATIM CODE SNIPPETS)

### 3.1. Điểm bổ trợ chuẩn hóa và đóng gói cache
```python
def _safe_source_text(source: Any) -> str:
    """Extract source text safely across WorkspaceAIContextSource, NotebookSource, or duck-typed objects."""
    text = getattr(source, "text", None)
    if text is not None:
        return str(text)
    content_text = getattr(source, "content_text", None)
    if content_text is not None and str(content_text).strip():
        return str(content_text)
    content_preview = getattr(source, "content_preview", None)
    if content_preview is not None:
        return str(content_preview)
    return ""


def _safe_source_scope(source: Any) -> str:
    """Extract source scope safely across models."""
    scope = getattr(source, "source_scope", None)
    if scope:
        return str(scope)
    if hasattr(source, "notebook_id"):
        return SOURCE_SCOPE_NOTEBOOK
    return SOURCE_SCOPE_TEMPORARY


def _safe_source_id(source: Any) -> str:
    """Extract source id safely across models."""
    sid = getattr(source, "source_id", None)
    if sid:
        return str(sid)
    sid = getattr(source, "id", None)
    if sid:
        return str(sid)
    return ""


def _coerce_context_source(source: Any) -> WorkspaceAIContextSource:
    """Ensure a source is a WorkspaceAIContextSource with all expected attributes."""
    if isinstance(source, WorkspaceAIContextSource):
        return source
    text = _safe_source_text(source)
    source_id = _safe_source_id(source)
    source_scope = _safe_source_scope(source)
    title = str(getattr(source, "title", "") or source_id or "Untitled")
    source_type = str(getattr(source, "source_type", "") or "plain_text")
    privacy_label = str(getattr(source, "privacy_label", "") or "local_only")
    managed_path = str(getattr(source, "managed_path", "") or "")
    truncated = bool(getattr(source, "truncated", False))
    return WorkspaceAIContextSource(
        source_id=source_id,
        source_scope=source_scope,
        source_type=source_type,
        title=title,
        privacy_label=privacy_label,
        text=text,
        included_chars=len(text),
        truncated=truncated,
        managed_path=managed_path,
    )


@functools.lru_cache(maxsize=4096)
def _document_id_cached(source: WorkspaceAIContextSource) -> str:
    if getattr(source, "document_id", ""):
        return str(source.document_id).strip()
    if getattr(source, "source_id", "") and str(source.source_id).startswith("wsc-"):
        return str(source.source_id).strip()
    text_bytes = (getattr(source, "text", "") or "").strip().encode("utf-8")
    if text_bytes:
        return f"wsc-{hashlib.sha256(text_bytes).hexdigest()[:24]}"
    identity = f"{getattr(source, 'source_scope', '')}:{getattr(source, 'source_id', '')}".encode("utf-8")
    return f"wsc-{hashlib.sha256(identity).hexdigest()[:24]}"


def _document_id(source: Any) -> str:
    """Identify a library document by extracted text, not per-machine source id.

    Empty text cannot be matched across machines, so it stays local to
    ``source_scope:source_id``. Filename is never part of the identity.
    """
    coerced = _coerce_context_source(source)
    return _document_id_cached(coerced)


_document_id.cache_clear = _document_id_cached.cache_clear


@functools.lru_cache(maxsize=4096)
def _source_fingerprint_cached(source: WorkspaceAIContextSource) -> str:
    doc_id = _document_id(source)
    text_bytes = (source.text or "").strip().encode("utf-8")
    content_hash = hashlib.sha256(text_bytes).hexdigest()[:16]
    privacy = (source.privacy_label or "").strip().casefold()
    return f"{doc_id}:{content_hash}:{privacy}"


def _source_fingerprint(source: Any) -> str:
    coerced = _coerce_context_source(source)
    return _source_fingerprint_cached(coerced)


_source_fingerprint.cache_clear = _source_fingerprint_cached.cache_clear
```

### 3.2. Điểm sửa chính quy tại `get_workspace_chat_preparation_summary`
```python
<<<<
    sources = tuple(s for s in context_sources if (s.text or "").strip())
    total_count = len(sources)
    if resolved is None or not resolved.enabled:
        statuses = {
            f"{s.source_scope}:{s.source_id}": "unavailable"
            for s in context_sources
        }
====
    coerced_context_sources = tuple(_coerce_context_source(s) for s in context_sources)
    sources = tuple(s for s in coerced_context_sources if (s.text or "").strip())
    total_count = len(sources)
    if resolved is None or not resolved.enabled:
        statuses = {
            f"{s.source_scope}:{s.source_id}": "unavailable"
            for s in coerced_context_sources
        }
>>>>
```

---

## 4. KẾT QUẢ KIỂM THỬ TÁI HIỆN VÀ HỒI QUY (TEST EVIDENCE)

### 4.1. Bằng chứng kiểm thử tái hiện lỗi (Trước khi sửa)
Khi chạy bộ test `tests/test_notebook_source_text_fix_home.py` trước khi áp dụng bản sửa lỗi:
- `7 FAILED, 2 PASSED`:
  - `AttributeError: 'NotebookSource' object has no attribute 'text'` tại `workspace_chat_rag_v2_adapter.py:2925`.
  - `TypeError: unhashable type: 'NotebookSource'` tại `_document_id`.

### 4.2. Bằng chứng kiểm thử sau khi sửa (Sau khi sửa)
```text
============================= test session starts =============================
platform win32 -- Python 3.11.14, pytest-8.4.2, pluggy-1.6.0 -- D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Sandbox\AIOS_habbit
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 9 items

tests/test_notebook_source_text_fix_home.py::test_reproduce_notebook_source_lacks_text_attribute PASSED [ 11%]
tests/test_notebook_source_text_fix_home.py::test_reproduce_and_verify_preparation_summary_with_notebook_source PASSED [ 22%]
tests/test_notebook_source_text_fix_home.py::test_preparation_summary_with_empty_notebook_source PASSED [ 33%]
tests/test_notebook_source_text_fix_home.py::test_preparation_summary_with_content_preview_fallback PASSED [ 44%]
tests/test_notebook_source_text_fix_home.py::test_preparation_summary_preserves_context_source_behavior PASSED [ 55%]
tests/test_notebook_source_text_fix_home.py::test_preparation_summary_mixed_sources PASSED [ 66%]
tests/test_notebook_source_text_fix_home.py::test_get_workspace_chat_source_preparation_status_with_notebook_source PASSED [ 77%]
tests/test_notebook_source_text_fix_home.py::test_source_fingerprint_and_document_id_with_notebook_source PASSED [ 88%]
tests/test_notebook_source_text_fix_home.py::test_duck_typed_source_without_text_attribute PASSED [100%]

============================== 9 passed in 5.68s ==============================
```

### 4.3. Kiểm thử hồi quy toàn diện các bộ test liên quan
Chạy đồng thời:
1. `tests/test_notebook_source_text_fix_home.py` (9 tests)
2. `tests/test_workspace_chat_rag_v2_adapter.py` (91 tests)
3. `tests/test_workspace_chat_backend_fingerprint_gate.py` (18 tests)

**Kết quả:**
```text
============================= 118 passed in 5.69s =============================
```
100% các bài kiểm thử đều vượt qua tuyệt đối (0 lỗi).

---

## 5. KẾT QUẢ ĐẠT 4 CỔNG CHẤT LƯỢNG REPO (QUALITY GATES)

| Cổng | Lệnh thực thi | Kết quả | Ghi chú |
|---|---|---|---|
| **Cổng 1: compileall** | `python -m compileall src tests -q` | **PASS (code 0)** | Toàn bộ mã nguồn và test hợp lệ cú pháp Python |
| **Cổng 2: pytest liên quan** | `pytest tests/test_notebook_source_text_fix_home.py tests/test_workspace_chat_rag_v2_adapter.py tests/test_workspace_chat_backend_fingerprint_gate.py` | **PASS (118/118)** | 100% xanh, không lỗi hồi quy |
| **Cổng 3: cli audit** | `python -m aios_habit.cli audit` | **PASS (code 0)** | `{"errors": [], "status": "PASS", "warnings": []}` |
| **Cổng 4: import app** | `python -c "import aios_habit.workspace_chat_app"` | **PASS (code 0)** | Bootstrap ứng dụng thành công |

---

## 6. KẾT LUẬN
- Ca crash `AttributeError: 'NotebookSource' object has no attribute 'text'` đã được xử lý triệt để tận gốc tại điểm truy cập thuộc tính mà không gây tác động lan.
- Không đụng chạm chỉ mục sản xuất (production index sealed).
- Toàn bộ 4 cổng chất lượng đều đạt chuẩn tuyệt đối.
- Mã nguồn đã được commit và push lên nhánh từ xa `phieu-viec/rag-fix1`.
