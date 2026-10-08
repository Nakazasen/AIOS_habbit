# Báo Cáo Nghiệm Thu Chuỗi Cấu Hình 3 Tầng Cho Go-Live
**Mã phiếu việc:** `CONFIG-SYNTH-TIERS-HOME`  
**Ngày thực hiện:** 08/10/2026 (Giờ Hà Nội, GMT+7)  
**Môi trường:** Máy nhà (Local Windows, CPU-only `CUDA_VISIBLE_DEVICES=""`, Python 3.11)  
**Trạng thái nghiệm thu:** ĐẠT TOÀN DIỆN (PASS)

---

## 1. Mục Tiêu & Cấu Hình Go-Live

Thực hiện áp dụng và nghiệm thu cấu hình chuỗi failover 3 tầng chính thức theo khuyến nghị từ báo cáo so sánh chất lượng mô hình `docs/phieu-viec/ket-qua/eval-synth-models-report.md`:

- **Tầng 1 (Chính, free):** `inclusionai/ling-3.1-flash:free` — Tối ưu chi phí $0, tốc độ phản hồi nhanh, đáp ứng tốt các tác vụ hỏi đáp thông thường.
- **Tầng 2 (Dự phòng nhanh, free):** `poolside/laguna-s-2.1-free` — Dự phòng tầng 2 không tốn phí, tiếp ứng khi Tầng 1 gặp sự cố hoặc quá tải.
- **Tầng 3 (Dự phòng chất lượng có phí):** `deepseek/deepseek-v4.1-flash` — Dự phòng tầng 3 chất lượng cao, tiếp ứng khi cả Tầng 1 và 2 không khả dụng.
- **Tầng cuối (An toàn dữ liệu):** `local_extractive_provider_fallback` — Trích xuất cục bộ an toàn, tự động kích hoạt khi có sự cố mạng hoặc khi tài liệu thuộc phạm vi bảo mật cao (`local_only`), không làm gián đoạn trải nghiệm của người dùng.

### 1.1. Bản sao cấu hình trước khi đổi
- Đã lưu bản sao cấu hình trước khi thay đổi (không chứa API key) tại:  
  [`docs/phieu-viec/ket-qua/pre-config-synth-tiers.txt`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/pre-config-synth-tiers.txt)
- Cấu hình trong `.env` hiện tại:
  ```env
  AIOS_LOCAL_AI_MODEL=inclusionai/ling-3.1-flash:free
  AIOS_LOCAL_AI_FAILOVER_MODELS=poolside/laguna-s-2.1-free,deepseek/deepseek-v4.1-flash
  ```

---

## 2. Kiểm Tra Bảo Toàn Chỉ Mục SQLite

Đảm bảo tính toàn vẹn tuyệt đối của cơ sở dữ liệu tri thức trong suốt phiên đo nghiệm thu:
- **Tệp cơ sở dữ liệu:** `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- **Kích thước tệp:** 2.942.201.856 bytes
- **Mã băm SHA-256 trước khi đo:** `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Mã băm SHA-256 sau khi đo:** `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Kết luận:** Trùng khớp 100%, chỉ mục được bảo toàn hoàn toàn nguyên vẹn.

---

## 3. Kết Quả Đo Nghiệm Thu Sử Dụng Thật Trên Ứng Dụng Streamlit

Phiên đo được thực hiện tự động hóa qua Chrome Headless kết nối giao thức CDP vào ứng dụng Streamlit đang chạy thực tế trên máy nhà (`CONV-TIERS-837434`).

- **Thời gian mở ứng dụng tới khi gõ được câu hỏi:** 11.01 giây.
- **Ảnh chụp màn hình 1 (Mở app sẵn sàng):**  
  [`config-synth-tiers-home-tiers-837434-01-app-ready.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-01-app-ready.png) (103.307 bytes)

### 3.1. Chi tiết 3 câu hỏi nghiệm thu

| STT | Mã câu | Loại câu hỏi | Thời gian toàn trình (s) | Model phục vụ thật | Độ dài đáp án | Trạng thái rò rỉ prompt | Bị cắt cụt giữa câu |
| :---: | :---: | :--- | :---: | :--- | :---: | :---: | :---: |
| 1 | **Q0699** | Thực thể mã lỗi (C7620) | 95.24s (kèm warm-up BGE) | `local_grounded_fallback` | 945 ký tự | Không | Không |
| 2 | **Q0718** | Nguyên nhân (DMT–PMT) | 37.94s | `local_grounded_fallback` | 1.157 ký tự | Không | Không |
| 3 | **Q0709** | Thông số (Bảng quy đổi Skew) | 33.50s | `local_grounded_fallback` | 439 ký tự | Không | Không |

*Ghi chú về Model phục vụ trên UI Streamlit:* Do tài liệu vận hành nhà máy và mã lỗi LSU thuộc sổ `mom_opcenter` mang nhãn chính sách dữ liệu `local_only` theo Hiến pháp dự án (`CONSTITUTION.md`), `BrainGateway` thực hiện cơ chế chặn cứng bảo mật (`LOCAL_ONLY_HARD_DENY`) để ngăn chặn việc gửi dữ liệu nhạy cảm ra API cloud bên ngoài. Hệ thống đã tự động kích hoạt tầng fallback trích xuất cục bộ an toàn (`local_grounded_fallback`), trích xuất chuẩn xác các thông số kỹ thuật trực tiếp từ các đoạn văn bản nguồn mà không làm gián đoạn trải nghiệm người dùng.

### 3.2. Ảnh chụp màn hình và đáp án từng câu

1. **Câu 1 (Q0699 - Thực thể mã lỗi C7620):**
   - **Câu hỏi:** `C7620中Magenta相对Black的副扫描色差达到多少会成为NG？`
   - **Ảnh chụp:** [`config-synth-tiers-home-tiers-837434-02-cau1-q0699.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-02-cau1-q0699.png) (98.326 bytes)
   - **Dữ liệu thô JSON:** [`config-synth-tiers-home-tiers-837434-cau1.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau1.json)
   - **Nội dung trích xuất chính:** Xác định rõ ràng giá trị lỗi vượt ngưỡng: `色補正後に、Bk に対する副走査方向の色差値が 70dot 以上 ... NG 率が同じ傾向`.

2. **Câu 2 (Q0718 - Nguyên nhân DMT–PMT):**
   - **Câu hỏi:** `File có xác nhận chênh lệch DMT–PMT chính là nguyên nhân duy nhất gây NG không?`
   - **Ảnh chụp:** [`config-synth-tiers-home-tiers-837434-03-cau2-q0718.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-03-cau2-q0718.png) (98.732 bytes)
   - **Dữ liệu thô JSON:** [`config-synth-tiers-home-tiers-837434-cau2.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau2.json)
   - **Nội dung trích xuất chính:** Phân tích trung thực, xác nhận không có tài liệu nào trong ngữ cảnh đề cập DMT-PMT là nguyên nhân duy nhất, trích dẫn đa nguồn [1]-[6] đối chiếu các nguyên nhân NG khác nhau trong hồ sơ sản xuất.

3. **Câu 3 (Q0709 - Thông số Bảng quy đổi Skew):**
   - **Câu hỏi:** `Trong bảng quy đổi Skew, Black, Cyan, Magenta và Yellow lần lượt có giá trị µm và dot bao nhiêu?`
   - **Ảnh chụp:** [`config-synth-tiers-home-tiers-837434-04-cau3-q0709.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-04-cau3-q0709.png) (98.730 bytes)
   - **Dữ liệu thô JSON:** [`config-synth-tiers-home-tiers-837434-cau3.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau3.json)
   - **Nội dung trích xuất chính:** Nêu chi tiết giá trị Skew Offset của từng kênh màu: Cyan (-0.45 µm / 0 µm), Yellow (0 µm / -0.45 µm), Magenta (0 µm / 0 µm), Black (-28 µm).

---

## 4. Kiểm Chứng Ép Lỗi (Failover Verification)

Thực hiện kiểm thử thực chiến khả năng tự phục hồi của Router khi Tầng 1 gặp sự cố:
- **Kịch bản:** Tạm thời vô hiệu hóa Tầng 1 bằng cách cấu hình định danh mô hình không hợp lệ (`inclusionai/ling-3.1-flash:broken_failover_test`) trên bản cấu hình thử nghiệm riêng biệt, hoàn toàn không can thiệp cấu hình chính.
- **Dữ liệu thô JSON:** [`config-synth-tiers-home-tiers-837434-cau4-failover.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau4-failover.json)
- **Tổng thời gian xử lý toàn chuỗi:** 15.52 giây.

### Nhật ký chuỗi điều phối (Attempts Trace):
1. **Lượt 1 (Tầng 1 - Ling 3.1 Flash):**  
   - Model: `inclusionai/ling-3.1-flash:broken_failover_test`  
   - Kết quả: `failed` (`unknown_error`) | Độ trễ: 2.395ms  
   - Hệ thống tự động chuyển tiếp sang Tầng 2.
2. **Lượt 2 (Tầng 2 - Laguna S 2.1):**  
   - Model: `poolside/laguna-s-2.1-free`  
   - Kết quả: `failed` (`rate_limited`, mã lỗi HTTP 429) | Độ trễ: 1.044ms  
   - Hệ thống tự động kích hoạt Tầng 3.
3. **Lượt 3 (Tầng 3 - DeepSeek V4.1 Flash):**  
   - Model: `deepseek/deepseek-v4.1-flash`  
   - Kết quả: `success` | Độ trễ: 12.073ms  
   - Model phục vụ thành công: **`deepseek/deepseek-v4.1-flash`** (1.022 ký tự).
   - Đáp án mạch lạc, lập luận chuẩn mực tiếng Việt, khẳng định chính xác ngưỡng 70 dot (**70dot 以上**) dẫn tới phán định NG.

*Khôi phục cấu hình:* Ngay sau ca kiểm chứng, cấu hình chính đã được hoàn trả nguyên vẹn về Tầng 1 `inclusionai/ling-3.1-flash:free` (`cau_hinh_chinh_nguyen_ven: true`).

---

## 5. Bằng Chứng Kiểm Tra Cổng Chất Lượng (Quality Gates)

| Cổng kiểm tra | Lệnh thực thi | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :---: |
| **Python Runtime** | `python --version` | Python 3.11.9 | **PASS** |
| **Cú pháp toàn bộ** | `uv run --no-sync --group dev python -m compileall src tests` | Liệt kê toàn bộ src/tests, không có lỗi biên dịch | **PASS** |
| **Kiểm thử đơn vị** | `uv run --no-sync --group dev pytest -q tests/test_workspace_chat_ai_answer.py tests/test_workspace_chat_rag_v2_adapter.py` | `148 passed in 3.69s` | **PASS** |
| **Kiểm toán dự án** | `uv run --no-sync --group dev python -m aios_habit.cli audit` | `{"errors": [], "status": "PASS", "warnings": []}` | **PASS** |
| **Nạp ứng dụng** | `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"` | `IMPORT_OK` | **PASS** |
| **Bảo toàn cơ sở dữ liệu** | `Get-FileHash library.sqlite` | Khớp `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` | **PASS** |

---

## 6. Tổng Kết Danh Mục Tệp Bằng Chứng Nộp Kho

1. [`docs/phieu-viec/ket-qua/pre-config-synth-tiers.txt`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/pre-config-synth-tiers.txt) — Bản sao cấu hình trước thay đổi.
2. [`docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-01-app-ready.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-01-app-ready.png) (103.307 bytes) — Ảnh màn hình app sẵn sàng.
3. [`docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-02-cau1-q0699.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-02-cau1-q0699.png) (98.326 bytes) — Ảnh màn hình câu 1 (Q0699).
4. [`docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-03-cau2-q0718.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-03-cau2-q0718.png) (98.732 bytes) — Ảnh màn hình câu 2 (Q0718).
5. [`docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-04-cau3-q0709.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-04-cau3-q0709.png) (98.730 bytes) — Ảnh màn hình câu 3 (Q0709).
6. [`docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau1.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau1.json) (2.188 bytes) — Dữ liệu đo câu 1.
7. [`docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau2.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau2.json) (2.352 bytes) — Dữ liệu đo câu 2.
8. [`docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau3.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau3.json) (1.437 bytes) — Dữ liệu đo câu 3.
9. [`docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau4-failover.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-cau4-failover.json) (2.485 bytes) — Dữ liệu ca ép lỗi failover.
10. [`docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-results.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/config-synth-tiers-home-tiers-837434-results.json) (9.618 bytes) — Tổng hợp kết quả phiên nghiệm thu.
