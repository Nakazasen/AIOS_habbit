# BÁO CÁO THỰC THI VÉ DESKTOP-PC0575-CAGENT-FALLBACK-NOTICE-FIX

> **Trạm thực thi**: KDTVN-PC0575  
> **Kho mã nguồn**: `D:\Sandbox\AIOS_habbit`  
> **Nhánh**: `phieu-viec/rag-fix1`  
> **Thời điểm hoàn thành**: 2026-10-16T18:39:00+07:00  
> **Trạng thái**: HOÀN THÀNH (100% yêu cầu chất lượng)  

---

## 1. BỐI CẢNH & NGUYÊN NHÂN VẤN ĐỀ

Theo kết quả điều tra truy vết từ vé chẩn đoán `DESKTOP-PC0575-CAGENT-LOCAL-FALLBACK-DIAG`:
- Lúc 17:53 ngày 2026-10-16, lượt hỏi của người dùng tại sổ `NB-E35A7BEE` (`CONV-9C730D76`) với câu hỏi *"LSU là gì và gồm những bộ phận quang học chính nào?"* đã được chuyển tiếp thành công tới C-Agent qua HTTP POST.
- Tuy nhiên, máy chủ C-Agent phía CMC TS không phản hồi trong ngưỡng 60 giây (`TimeoutError`).
- Hệ thống tự động kích hoạt thác tuyến dự phòng (failover chain) rơi xuống làn tổng hợp cục bộ từ tài liệu (`local_grounded_fallback`) để tránh gây gián đoạn công việc của người dùng.
- **Vấn đề cốt lõi**:
  - Giao diện người dùng trước đây chỉ phản ánh cấu hình ghim tĩnh từ biến môi trường (`AIOS_AI_BACKEND=cagent_api` -> *"Đang dùng: C-Agent (ghim tay)"*) trên thanh công cụ, mà không hiển thị bất kỳ cảnh báo nào về việc C-Agent đã bị timeout và lượt trả lời này đã phải rơi xuống làn trích xuất cục bộ.
  - Người dùng nhìn thấy thẻ đáp án *"Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình"* trong khi thanh công cụ lại ghi *"Đang dùng: C-Agent (ghim tay)"*, gây hiểu lầm rằng hệ thống bỏ qua C-Agent hoặc cấu hình ghim bị phớt lờ.

---

## 2. GIẢI PHÁP THỰC HIỆN

Đã can thiệp đúng phạm vi tầng hiển thị tại `workspace_chat_app.py` và `workspace_chat_ui.py`, giữ nguyên vẹn 100% logic định tuyến, giá trị timeout và nhãn đáp án hiện có:

1. **Hàm quyết định hiển thị cảnh báo dựa trên provenance thực tế**:
   - `should_show_fallback_notice(badge_data)`:
     - Kiểm tra trực tiếp thông tin provenance do `route_workspace_chat_submission` trả về cho lượt hỏi (`badge_data.get("fallback_used") is True`).
     - Yêu cầu `initial_backend` khác rỗng và khác `"local"` (người dùng đã chủ động chọn hoặc ghim dịch vụ AI ngoài như `cagent_api`, `gemini_web`, `nakazasen_router`).
     - Xác nhận đích đến thực tế là trích xuất/tổng hợp cục bộ (`operational_mode in {"local_grounded_fallback", "draft_fallback"}`).
     - **Không phụ thuộc vào biến môi trường hay cấu hình ghim tĩnh**.

2. **Quy tắc kiểm thử âm tính (Negative Guards)**:
   - Khi người dùng tự chọn chạy cục bộ (`backend="local"`): `initial_backend` là None hoặc `"local"` -> **Ẩn cảnh báo**.
   - Khi lượt đi qua C-Agent thành công (`fallback_used=False`): **Ẩn cảnh báo**.
   - Khi hệ thống tự động định tuyến hợp lệ không qua backend ghim: **Ẩn cảnh báo**.
   - Khi `badge_data` rỗng hoặc None: **Ẩn cảnh báo**.

3. **Văn bản cảnh báo chuẩn tiếng Việt & Gọi đúng tên C-Agent**:
   - `format_fallback_notice(badge_data, locale="vi")`:
     - Tự động lấy tên dịch vụ từ `backend_label_vi(initial_backend)` (đối với `cagent_api` trả về đúng `"C-Agent"`).
     - Định dạng qua từ điển đa ngôn ngữ `t("local_fallback_warning", locale=locale, service=service_name)`:
       > **"Dịch vụ C-Agent không phản hồi trong thời gian chờ, đáp án hiện tại là bản tổng hợp cục bộ từ tài liệu."**

4. **Hiển thị trực quan tại tầng giao diện (Streamlit Display Layer)**:
   - `render_fallback_notice(badge_data, locale)`: Phát thông báo cảnh báo màu vàng (`st.warning`) ngay phía trên thẻ kết quả đáp án (`# AI Answer Badge`) của chính lượt hỏi đó.
   - Giữ nguyên nhãn thành công hiện có: `st.success(f"📄 **{t('local_fallback_note', locale=current_ui_locale)}**")` ("Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình").
   - Hỗ trợ thêm tham số `badge_data` trong `render_chat_bubble()` cho phép hiển thị cảnh báo ngay trong bubble trả lời khi được kiểm thử độc lập.

---

## 3. BẰNG CHỨNG HIỂN THỊ CẢNH BÁO TRÊN LƯỢT RƠI LÀN MÔ PHỎNG

Đoạn trích xuất từ kịch bản chạy mô phỏng chính xác lượt hỏi 17:53 (`scripts/verify_cagent_fallback_notice.py`):

```text
================================================================================
XÁC MINH HIỂN THỊ CẢNH BÁO RƠI LÀN TỪ C-AGENT XUỐNG TỔNG HỢP CỤC BỘ
Mã vé: DESKTOP-PC0575-CAGENT-FALLBACK-NOTICE-FIX
================================================================================

[KỊCH BẢN 1: TÍCH CỰC] Người dùng ghim C-Agent, C-Agent bị timeout 60s -> Rơi làn cục bộ
-> should_show_fallback_notice: True
-> format_fallback_notice: "Dịch vụ C-Agent không phản hồi trong thời gian chờ, đáp án hiện tại là bản tổng hợp cục bộ từ tài liệu."
[UI RENDER - ST.WARNING] ⚠️  Dịch vụ C-Agent không phản hồi trong thời gian chờ, đáp án hiện tại là bản tổng hợp cục bộ từ tài liệu.
=> KẾT QUẢ KỊCH BẢN 1: ĐẠT (Cảnh báo hiển thị chính xác tên C-Agent và thông điệp tiếng Việt).

[KỊCH BẢN 2: ÂM TÍNH 1] Người dùng tự chọn Chạy cục bộ ngay từ đầu
-> should_show_fallback_notice: False
=> KẾT QUẢ KỊCH BẢN 2: ĐẠT (Không hiển thị cảnh báo khi người dùng chủ động chọn cục bộ).

[KỊCH BẢN 3: ÂM TÍNH 2] C-Agent phản hồi thành công (không có lỗi/timeout)
-> should_show_fallback_notice: False
=> KẾT QUẢ KỊCH BẢN 3: ĐẠT (Không hiển thị cảnh báo khi C-Agent chạy bình thường).

================================================================================
TẤT CẢ CÁC BÀI KIỂM TRA ĐÃ HOÀN TẤT THÀNH CÔNG VỚI ĐỘ CHÍNH XÁC 100%.
================================================================================
```

### Trực quan hóa cấu trúc hiển thị trên màn hình Workspace Chat:
```
┌────────────────────────────────────────────────────────────────────────┐
│ 👤 User: LSU là gì và gồm những bộ phận quang học chính nào?           │
├────────────────────────────────────────────────────────────────────────┤
│ 🤖 Assistant:                                                          │
│   - Tổng quan về quá trình in ảnh điện tử và chức năng của LSU... [13]  │
│   - LID SCANNER: Tác dụng nắp đậy... [1]                               │
│   LIMITATIONS: incomplete_query_term_coverage...                       │
├────────────────────────────────────────────────────────────────────────┤
│ [AI Answer Badge]                                                      │
│ ⚠️ Dịch vụ C-Agent không phản hồi trong thời gian chờ, đáp án hiện     │
│    tại là bản tổng hợp cục bộ từ tài liệu.                             │
│ 📄 Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình                     │
│ ℹ️ Tra cứu 20 đoạn liên quan từ khối LSU.                             │
│ 📚 Nguồn gửi cùng câu hỏi: 20                                          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (PYTEST)

### 4.1. Bộ test chuyên biệt cho vé (`tests/test_desktop_pc0575_cagent_fallback_notice.py`)
Đạt **15/15 test cases PASSED** (thời gian: 3.27s):
1. `test_should_show_fallback_notice_cagent_fallback`: PASSED
2. `test_should_show_fallback_notice_gemini_fallback`: PASSED
3. `test_should_show_fallback_notice_router_fallback`: PASSED
4. `test_should_not_show_when_pinned_cagent_succeeds`: PASSED (Test âm tính 1)
5. `test_should_not_show_when_user_explicitly_chose_local_lane`: PASSED (Test âm tính 2)
6. `test_should_not_show_when_fallback_target_is_remote_ai`: PASSED (Test âm tính 3)
7. `test_should_not_show_when_badge_empty_or_none`: PASSED (Test âm tính 4)
8. `test_format_fallback_notice_cagent_vietnamese`: PASSED (Đúng văn bản tiếng Việt gọi "C-Agent")
9. `test_format_fallback_notice_gemini_vietnamese`: PASSED
10. `test_format_fallback_notice_returns_empty_when_not_applicable`: PASSED
11. `test_render_fallback_notice_displays_warning`: PASSED (`st.warning` được gọi chính xác)
12. `test_render_fallback_notice_suppressed_for_negative_cases`: PASSED
13. `test_render_chat_bubble_with_fallback_badge`: PASSED
14. `test_render_chat_bubble_without_fallback_badge`: PASSED
15. `test_integration_routing_simulation_cagent_timeout_triggers_notice`: PASSED (Tái hiện toàn trình mô phỏng sự cố 17:53 với `route_workspace_chat_submission`)

### 4.2. Bộ test hồi quy liên quan
- `tests/test_synth_lane_failover.py`: 7/7 PASSED
- `tests/test_desktop_pc0575_answer_header_strip.py`: 16/16 PASSED
- `tests/test_ui_render_optimization.py`: 9/9 PASSED
- `tests/test_workspace_chat_ui_i18n.py` (kiểm tra tính toàn vẹn từ điển bản dịch): PASSED

---

## 5. DANH SÁCH TỆP TIN THAY ĐỔI TRONG COMMIT

1. `src/aios_habit/i18n.py`: Bổ sung khóa `local_fallback_warning` đồng bộ 3 ngôn ngữ (`vi`, `ja`, `zh-CN`).
2. `src/aios_habit/workspace_chat_ui.py`: Thêm `should_show_fallback_notice()`, `format_fallback_notice()`, `render_fallback_notice()`; mở rộng `render_chat_bubble()` nhận `badge_data`.
3. `src/aios_habit/workspace_chat_app.py`: Tích hợp hiển thị cảnh báo `render_fallback_notice(badge_data)` trong khối `# AI Answer Badge` trước nhãn tổng hợp cục bộ.
4. `tests/test_desktop_pc0575_cagent_fallback_notice.py`: 15 bài kiểm tra tích cực và âm tính cho điều kiện hiển thị cảnh báo.
5. `scripts/verify_cagent_fallback_notice.py`: Kịch bản kiểm chứng độc lập đầu cuối.

---

```json
{
  "ma_ve": "DESKTOP-PC0575-CAGENT-FALLBACK-NOTICE-FIX",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-16T11:39:00.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
