# BÁO CÁO: APP-SOURCE-MODEL-PC0575 (CHẶNG 1 — RÀ SOÁT VÒNG ĐỜI NGUỒN & ĐỀ XUẤT HỢP NHẤT)

- **Mã vé:** `APP-SOURCE-MODEL-PC0575`
- **Chặng:** Chặng 1 — Rà soát mô hình + Đề xuất giải pháp (chỉ-đọc, chưa can thiệp code)
- **Máy thực hiện:** KDTVN-PC0575
- **Thợ:** agy (Antigravity CLI)
- **Thời gian:** 2026-10-08 17:35 +07
- **Tình trạng:** Hoàn thành Chặng 1, chờ điều phối (Muse) duyệt phương án trước khi sang Chặng 2.

---

## 1. Bối cảnh & Hiện tượng người dùng chỉ ra

Trên giao diện ứng dụng Workspace Chat (`workspace_chat_app.py`), khi người dùng mở Sổ "Điều tra lỗi LSU", trên cùng một màn hình xuất hiện đồng thời một loạt con số và thông báo mâu thuẫn:
1. Sidebar thông báo: **"Sổ Điều tra lỗi LSU — sẵn sàng, 494 tài liệu"**.
2. Phía dưới thanh quản lý nguồn hiển thị: **"Nguồn đang bật: 35"**.
3. Phía trên khung chat xuất hiện banner thông báo: **"ℹ️ AIOS đang chuẩn bị 2 tài liệu ở chế độ nền. Bạn có thể hỏi đáp bình thường với 33 tài liệu đã sẵn sàng."**
4. Thanh tiến độ tiến trình nhấp nháy: **"Đã chuẩn bị xong 33/35 (94%)"**.
5. Trong khi đó, dòng trạng thái chỉ mục thực tế (đã gắn ở vé `INDEX-STATUS-LINE`) ghi rõ: **"Kho đang dùng: library.sqlite · 889 tài liệu · 149.800 mảnh · mã 87a3626a85bc · ONNX fp32"**.

Người dùng đặt câu hỏi hoàn toàn chính xác: *Tài liệu đã được index xong xuôi rồi, người dùng chỉ cần chọn khối tri thức để hỏi đáp — tại sao lại tồn tại cả một đống con số tài liệu mâu thuẫn và cơ chế "chuẩn bị" rườm rà này?*

---

## 2. Kết quả rà soát kiến trúc & Bản đồ vòng đời tài liệu

Qua rà soát chuyên sâu trong mã nguồn (`workspace_chat_app.py`, `workspace_chat_ui.py`, `workspace_chat_rag_v2_adapter.py`, `workspace_chat_store.py`) và kiểm tra dữ liệu thực tế tại `local_cases/workspace_chat/` cùng các tệp SQLite, chúng tôi xác định nguyên nhân gốc rễ: **Hệ thống đang chạy song song 2 lớp quản lý tài liệu chồng lấn lên nhau.**

```
+-------------------------------------------------------------------------------------------------+
|                                 GIAO DIỆN NGƯỜI DÙNG (Streamlit UI)                              |
|  [Sổ: 494 tài liệu]  |  [Nguồn bật: 35]  |  [Sẵn sàng: 33/35 (94%)]  |  [Kho thực tế: 889 tài liệu]|
+-------------------------------------------------------------------------------------------------+
                                      |                                          |
                      (Rò rỉ trạng thái nội bộ)                        (Truy hồi thực tế)
                                      v                                          v
+---------------------------------------------------------+   +-----------------------------------+
| LỚP QUẢN LÝ NGUỒN CŨ (Legacy Workspace Store)           |   | LỚP CHỈ MỤC TRI THỨC HỢP NHẤT     |
| - local_cases/workspace_chat/notebook_sources.jsonl     |   |   (RAG v2 Production Index)       |
|   -> Chứa 494 bản ghi metadata/text thô của Sổ LSU.     |   |                                   |
| - conversation_source_selections.jsonl                  |   | - library.sqlite (2.85 GB)        |
|   -> Quản lý công tắc bật/tắt (enabled) cho từng chat  |   |   -> 889 tài liệu đã cắt mảnh     |
|   -> Đang bật 35 tài liệu (chọn thủ công/kế thừa).      |   |   -> 149.800 mảnh véc-tơ BGE-M3   |
| - rag_v2_preparation_ledger.sqlite                      |   |   -> Đã nhúng Dense + Sparse FTS5 |
|   -> Bảng sổ cái theo dõi chuẩn bị véc-tơ               |   |   -> CHỈ ĐỌC TUYỆT ĐỐI (Sealed)   |
|   -> 33 bản ghi "ready", 2 bản ghi "pending"            |   |                                   |
|   -> Gây nghẽn CPU khi nạp app vì quét & đối soát lại.  |   | => SẴN SÀNG TỨC THÌ 100% KHI HỎI  |
+---------------------------------------------------------+   +-----------------------------------+
```

### 2.1. Trả lời dứt khoát: 494 / 35 / 33 đếm cái gì? Ở lớp nào?

| Con số | Nhãn hiển thị trên UI | Thực chất đếm cái gì? | Nguồn dữ liệu & Lớp mã nguồn |
|:---:|:---|:---|:---|
| **494** | `Sổ Điều tra lỗi LSU — sẵn sàng, 494 tài liệu` <br> `⚙️ Quản lý tài liệu · 494 tài liệu` | Tổng số lượng tài liệu thô được gán vào Sổ "Điều tra lỗi LSU" (`NB-E35A7BEE`). | **Lớp Sổ tay (Legacy Notebook Store)**: Đếm số dòng có `notebook_id == 'NB-E35A7BEE'` trong `local_cases/workspace_chat/notebook_sources.jsonl` thông qua hàm `load_notebook_sources()`. |
| **35** | `Nguồn đang bật: 35` <br> `35 đang bật` | Số lượng tài liệu trong Sổ LSU đang có cờ kích hoạt (`is_enabled == True`) trong phiên chat hiện tại. | **Lớp Hội thoại (Conversation Selections)**: Đếm từ `conversation_source_selections.jsonl` kết hợp danh sách nguồn qua `load_enabled_sources_for_conversation()`. |
| **33** | `Đã chuẩn bị xong 33/35 (94%)` <br> `hỏi đáp bình thường với 33 tài liệu đã sẵn sàng` | Trong 35 tài liệu đang bật, có 33 tài liệu đã có trạng thái `ready` trong sổ cái chuẩn bị, còn 2 tài liệu đang ở trạng thái `pending`/`processing`. | **Lớp Sổ cái chuẩn bị (Preparation Ledger)**: Đếm trạng thái `ready` từ bảng `source_preparation_ledger` trong `local_runs/.../workspace_chat.sqlite` và dict `_PREPARATION_REGISTRY`. |

*Đối chiếu với con số **889**:*
- **889**: Là tổng số tài liệu thực sự có trong chỉ mục tri thức production `library.sqlite`. 494 tài liệu của Sổ LSU thực chất chỉ là một tập con trong 889 tài liệu này.

### 2.2. Việc "chuẩn bị" ghi vector vào đâu? Có trùng lặp với chỉ mục 889 không?

1. **Ghi vào đâu?**
   - Trong `workspace_chat_rag_v2_adapter.py`: Khi worker chạy chuẩn bị (`prepare_workspace_chat_sources`), nếu collection mục tiêu là kho production sealed `tri_thuc`, hàm kiểm tra tại dòng 1424 sẽ lập tức chặn lại và ném lỗi:
     ```python
     if is_production_sealed_collection(target_collection_id):
         raise ReadOnlyIndexViolationError("Chỉ mục production là chỉ đọc tuyệt đối và không nhận nguồn chuẩn bị mới.")
     ```
   - Điều này có nghĩa là: **Kho 889 tài liệu không bao giờ nhận thêm vector từ tiến trình chuẩn bị này.**
   - Cơ chế chuẩn bị chỉ ghi trạng thái `ready`/`pending`/`failed` vào tệp ledger SQLite `workspace_chat.sqlite` sau khi kiểm tra hàm `_durable_semantic_coverage_ready()`.
   - Hàm `_durable_semantic_coverage_ready()` mở `library.sqlite` ở chế độ chỉ đọc (`mode=ro`), đếm số lượng chunks của tài liệu xem đã đủ dense + sparse chưa. Nếu có một sai lệch nhỏ về tên tệp hoặc fingerprint, nó không đánh dấu `ready` mà để ở trạng thái `pending`.
2. **Có trùng lặp không?**
   - **TRÙNG LẶP 100% VỀ MẶT BẢN CHẤT**: 494 tài liệu trong Sổ LSU thực chất **ĐÃ ĐƯỢC INDEX HOÀN TOÀN** trong `library.sqlite` (149.800 chunks).
   - Việc hệ thống lại đi quản lý riêng 494 bản ghi trong file JSONL, rồi quản lý bật/tắt 35 bản ghi, rồi lại chạy worker đối soát kiểm tra ledger 33/35 là **hoàn toàn thừa thãi**, là tàn dư (legacy) từ thời ứng dụng hoạt động theo cơ chế upload tệp cục bộ đơn lẻ từng cuộc trò chuyện trước khi có chỉ mục hợp nhất RAG v2.

### 2.3. Khi hỏi đáp thì đường trả lời đọc từ đâu?

Khi người dùng nhập câu hỏi và gửi đi:
1. Giao diện gọi `_run_chat_turn_async` trong `workspace_chat_app.py`.
2. Hàm này gọi `retrieve_local_evidence` (`retrieve_workspace_chat_evidence` trong `workspace_chat_rag_v2_adapter.py`).
3. `retrieve_workspace_chat_evidence` chuyển tiếp tới `_run_profile`.
4. Trong `_run_profile`, pipeline mở trực tiếp `pipe_config.index_path` — chính là **`library.sqlite`** (kho 889 tài liệu, 149.800 mảnh) ở chế độ chỉ-đọc (`mode=ro`).
5. Toàn bộ chặng tìm kiếm lai (Dense Numpy BLAS 121k/149k + Sparse Lexical FTS5 BM25 + Diversity Capping + Evidence Assembly) chạy **100% trên `library.sqlite`**.
6. **KẾT LUẬN:** Đường trả lời **chỉ đọc từ chỉ mục RAG v2 (`library.sqlite`)**, hoàn toàn không đọc từ `workspace_chat.sqlite` hay `notebook_sources.jsonl`.
   - Việc lọc "35 nguồn đang bật" ở tầng ngoài thực chất chỉ làm nhiệm vụ filter thô các `specs`, thậm chí nếu lọc sai còn có nguy cơ bỏ sót tài liệu liên quan đã có sẵn trong chỉ mục 889 tài liệu.

---

## 3. Đề xuất mô hình hợp nhất (Một nguồn sự thật — Single Source of Truth)

Bám sát định hướng của người dùng và điều phối:
> *"Tài liệu đã có trong chỉ mục = sẵn sàng tức thì (không chuẩn bị lại, không đếm chuẩn bị); 'chuẩn bị' chỉ còn cho tệp mới thật sự chưa index, chạy nền im lặng như đường ống nội bộ; giao diện chỉ còn tối đa một con số có nghĩa duy nhất hoặc không con số nào."*

### 3.1. Nguyên tắc kiến trúc mới

1. **Chỉ mục tri thức là nguồn sự thật duy nhất (Single Source of Truth):**
   - Mọi tài liệu thuộc các khối tri thức đã có trong `library.sqlite` (LSU, Điều tra lỗi, MOM...) đều được coi là **SẴN SÀNG TỨC THÌ (Instant Ready)**.
   - Không chạy đối soát ledger, không chạy vòng lặp chuẩn bị `reconcile_and_enqueue_workspace_chat_sources` đối với các tài liệu đã có trong chỉ mục.
   - Khi người dùng chọn một khối tri thức (hoặc để Tự động), phạm vi tìm kiếm của RAG v2 mặc định bao trùm toàn bộ khối tri thức đó mà không bắt người dùng phải tích chọn từng checkbox.

2. **Dọn sạch giao diện — Triệt tiêu các con số mâu thuẫn:**
   - **Gỡ bỏ hoàn toàn:**
     * Thanh tiến độ chuẩn bị `render_preparation_progress_bar`: `"Đã chuẩn bị xong 33/35 (94%)"`.
     * Thông báo `"ℹ️ AIOS đang chuẩn bị N tài liệu ở chế độ nền. Bạn có thể hỏi đáp bình thường với M tài liệu đã sẵn sàng."` (`non_blocking_preparation_partial_info`).
     * Toast `"AIOS đang tìm kiếm trên M tài liệu đã sẵn sàng (N tài liệu đang chuẩn bị trong nền)"` (`non_blocking_search_ready_toast`).
     * Dòng đếm `"Nguồn đang bật: 35"` ở sidebar và trong thân khung chat.
     * Tiêu đề rườm rà: `"⚙️ Quản lý tài liệu · 494 tài liệu · 35 đang bật"` -> tinh giản thành `"⚙️ Quản lý tài liệu bổ sung"` (hoặc chỉ hiển thị khi có tệp người dùng tự tải lên).
   - **Chỉ giữ lại duy nhất 1 thông tin có nghĩa:**
     * Dòng trạng thái chỉ mục sẵn có: `Kho đang dùng: library.sqlite · 889 tài liệu · 149.800 mảnh · mã 87a3626a85bc · ONNX fp32`.
     * Khi chọn khối tri thức: `Khối tri thức: Điều tra lỗi LSU (494 tài liệu đã sẵn sàng)` hoặc `Khối tri thức: Tự động (889 tài liệu)`.

3. **Cơ chế nạp tệp mới (Ad-hoc Upload) chuyển sang đường ống nền im lặng:**
   - Khi người dùng kéo-thả hoặc tải lên tệp tài liệu mới tinh (chưa có trong chỉ mục):
     * Hệ thống nạp tệp và chuyển vào hàng đợi xử lý nền trong im lặng (silent background ingestion).
     * Không hiện popup lỗi, không hiện banner 0/N làm phiền người dùng.
     * Người dùng vẫn tiếp tục hỏi đáp bình thường trên kho tri thức đã có; khi tệp mới index xong, nó tự động hòa vào kết quả tìm kiếm của các câu hỏi tiếp theo.

4. **Lợi ích kép cho hiệu năng mở sổ (mở đường cho vé `APP-OPEN-PERF`):**
   - Loại bỏ hoàn toàn việc gọi `reconcile_and_enqueue_workspace_chat_sources` và `schedule_workspace_chat_source_preparation` trên 494 tài liệu khi mở sổ.
   - Cắt bỏ hàng loạt câu truy vấn SQLite lặp và khóa `_PREPARATION_LOCK` trên đường khởi động.
   - Sổ sẽ mở tức thì trong chớp mắt (< 0.5 giây) thay vì phải chờ quét chuẩn bị như hiện tại.

---

## 4. Kế hoạch triển khai Chặng 2 (sau khi được duyệt)

Khi điều phối phê duyệt phương án trên, Chặng 2 sẽ được thực hiện với các bước cụ thể:

1. **Bước 1 (Gỡ bỏ UI mâu thuẫn):**
   - Trong `src/aios_habit/workspace_chat_app.py`:
     * Bỏ lệnh gọi `render_preparation_progress_bar` (dòng 5195) và hàm `_live_preparation_progress_panel`.
     * Bỏ khối hiển thị `non_blocking_preparation_partial_info` và `render_ai_source_context_summary` (dòng 4153-4182).
     * Bỏ toast `non_blocking_search_ready_toast` (dòng 4945, 4979, 5010).
     * Sửa tiêu đề expander quản lý tài liệu thành tiêu đề gọn gàng, không hiển thị các con số đối chọi (dòng 5207).
   - Trong `src/aios_habit/workspace_chat_ui.py`:
     * Bỏ dòng `st.caption(t("enabled_sources_count", ...))` và `st.write(t("enabled_sources_count", ...))`.
2. **Bước 2 (Chuyển chuẩn bị nguồn thành đường ống im lặng):**
   - Bỏ lệnh tự động `schedule_workspace_chat_source_preparation` và `reconcile_and_enqueue_workspace_chat_sources` trên tập tài liệu đã thuộc chỉ mục production.
   - Chỉ kích hoạt nạp nền khi có tệp tải lên mới trong `temporary_sources`.
3. **Bước 3 (Kiểm chứng sử dụng thật & cổng repo):**
   - Mở app thật trên máy công ty: mở Sổ LSU -> giao diện sạch bóng các con số mâu thuẫn, không có banner chuẩn bị 33/35.
   - Hỏi thử 3 câu thực tế về lỗi LSU: ghi nhận thời gian trả lời và độ chuẩn xác của câu trả lời.
   - Chạy đủ 4 cổng chất lượng repo: `compileall`, `pytest`, `cli audit`, `import workspace_chat_app`.

---

## 5. Kết luận Chặng 1

- Báo cáo đã làm rõ nguồn gốc từng con số (494 từ notebook store, 35 từ selections, 33 từ ledger, 889 từ chỉ mục production RAG v2).
- Khẳng định đường hỏi đáp chỉ đọc từ `library.sqlite`, việc đếm chuẩn bị 33/35 là thừa và gây hiểu nhầm.
- Phương án hợp nhất đã sẵn sàng.
- **Kính trình điều phối (Muse) xem xét và phê duyệt để chuyển sang Chặng 2.**
