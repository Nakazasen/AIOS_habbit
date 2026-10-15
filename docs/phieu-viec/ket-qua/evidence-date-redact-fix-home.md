# BÁO CÁO THỰC THI VÉ: EVIDENCE-DATE-REDACT-FIX-HOME
(Mã điều phối làn desktop: DESKTOP-EVIDENCE-DATE-REDACT-FIX-HOME)

## 1. THÔNG TIN CHUNG & CẤU HÌNH THỰC THI (BB-CONFIG-PARITY-01)
- **Mã vé điều phối:** `DESKTOP-EVIDENCE-DATE-REDACT-FIX-HOME` (Vé gốc repo: `EVIDENCE-DATE-REDACT-FIX-HOME`)
- **Trạng thái:** `HOAN_THANH`
- **Môi trường thực thi:** `May nha - h410asrock` (Intel Core i3-10100, 16GB RAM, chế độ CPU-only tuân thủ biên bản chuẩn `BB-CONFIG-PARITY-01`: `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `KMP_DUPLICATE_LIB_OK=TRUE`)
- **Kho mã nguồn:** `D:\Sandbox\AIOS_habbit`
- **Nhánh Git:** `phieu-viec/rag-fix1`
- **Mã Commit mã nguồn, kiểm thử & ảnh bằng chứng:** `6af79768dc4c49fdac02843b8cbb976df31d8b70`
- **Tình trạng đẩy kho từ xa (Remote Push):** Đã đẩy thành công lên nhánh `phieu-viec/rag-fix1` tại kho `https://github.com/Nakazasen/AIOS_habbit.git`. Kiểm chứng bằng `git ls-remote` xác nhận khớp 100% hash commit trên remote.
- **Ràng buộc an toàn chỉ mục:** KHÔNG đụng chạm hoặc làm thay đổi chỉ mục production (production index sealed).

---

## 2. NGUYÊN NHÂN GỐC RỄ & CƠ CHẾ SỬA ĐỔI TẬN GỐC (ROOT CAUSE & REMEDIATION)

### 2.1. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)
- **Tệp phát sinh:** `src/aios_habit/brain_gateway.py`
- **Vị trí phát sinh:** dòng 185 (trước khi sửa):
  ```python
  text = re.sub(r'/(?:[a-zA-Z0-9_\.\-]+/)+[^\s\)\(\"\']+', '[REDACTED_LOCAL_PATH]', text)
  ```
- **Cơ chế lỗi:**
  - Biểu thức chính quy trên nhằm mục đích che các đường dẫn Unix (`/home/...`, `/var/log/...`), nhưng **thiếu hoàn toàn điều kiện ranh giới bắt đầu** (`(?<![\w/\\])`).
  - Khi văn bản bằng chứng RAG hoặc dữ liệu bảng chứa chuỗi ngày dạng `yyyy/mm/dd` (ví dụ `2026/08/20`):
    - Phần `2026` đứng đầu chuỗi.
    - Ký tự `/` tiếp theo bắt đầu làm khớp mẫu `/(?:[a-zA-Z0-9_\.\-]+/)+[^\s\)\(\"\']+`.
    - Đoạn `08/` khớp `[a-zA-Z0-9_\.\-]+/`, và đoạn `20` khớp `[^\s\)\(\"\']+`.
    - Hậu quả: Đoạn `/08/20` bị thay thế bằng `[REDACTED_LOCAL_PATH]`, làm chuỗi biến thành `2026[REDACTED_LOCAL_PATH]`.
    - Tương tự với định dạng `dd/mm/yyyy` (ví dụ `20/08/2026` biến thành `20[REDACTED_LOCAL_PATH]`).
  - **Hệ quả đo lường tại phiên A5:** Khi câu hỏi về serial `61C999999902` trong tệp `2026_08_UnitTest.csv` được đưa vào tổng hợp qua làn RAG retrieval, cả 2 mốc ngày `2026/08/20` và `2026/08/21` đều bị che thành `2026[REDACTED_LOCAL_PATH]`. Mô hình LLM không thể đọc được ngày cụ thể và buộc phải phát sinh câu trả lời "ngày cụ thể không đọc được", gây rớt điểm chất lượng một cách oan uổng.

### 2.2. Thiết kế giải pháp sửa đổi (Remediation Design)
Tuân thủ đúng phân quyền của vé: **Chỉ sửa bộ che và test liên quan; không nới bất kỳ mẫu che nào khác**.

1. **Cơ chế bảo vệ ngày trước khâu che đường dẫn (Pre-redaction Date Guard):**
   - Định nghĩa biểu thức chính quy bảo vệ ngày chặt chẽ:
     ```python
     _DATE_REDACT_GUARD_PATTERN = re.compile(
         r'(?<![\w/\\])'
         r'(?:'
         r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'
         r'|'
         r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
         r')'
         r'(?![\w/\\])'
     )
     ```
   - Nhận diện toàn diện các định dạng: `yyyy/mm/dd`, `yyyy-mm-dd`, `dd/mm/yyyy`, `dd-mm-yyyy`, `yyyy/m/d`, `d/m/yyyy`.
   - Thay thế tạm thời bằng token an toàn `__AIOS_PRESERVED_DATE_{idx}__` (không chứa dấu gạch chéo `/`, dấu hai chấm `:` hoặc gạch chéo ngược `\`) nên không bao giờ bị các regex đường dẫn ăn nhầm.

2. **Bảo tồn và siết chặt các lớp che đường dẫn cục bộ thật:**
   - **Đường dẫn ổ đĩa Windows:** Giữ nguyên các mẫu quét ổ đĩa Windows với cả gạch chéo xuôi và ngược (`D:\...`, `C:/...`).
   - **Đường dẫn UNC:** Bổ sung mẫu che cho đường dẫn chia sẻ mạng UNC `\\server\share\...` và `//server/share/...`.
   - **Đường dẫn thư mục người dùng:** Bổ sung mẫu che cho `~/...`.
   - **Đường dẫn Unix tuyệt đối:** Bổ sung điều kiện ranh giới `(?<![\w/\\])` để chỉ che các đường dẫn Unix thật, không ăn lẹm vào giữa từ hay số.
   - **Đường dẫn Unix chứa thư mục ngày:** Nếu một đường dẫn cục bộ thật có chứa thư mục ngày (ví dụ `/var/log/2026/08/20/app.log`), do `2026` đi liền sau `/` (`[\w/\\]`), `_DATE_REDACT_GUARD_PATTERN` sẽ từ chối không coi đó là ngày cô lập, và toàn bộ đường dẫn vẫn được che thành `[REDACTED_LOCAL_PATH]` như quy chuẩn an toàn.

3. **Khôi phục mốc ngày an toàn:**
   - Sau khi các lớp che đường dẫn hoàn tất, các token `__AIOS_PRESERVED_DATE_{idx}__` được khôi phục nguyên vẹn 100% về chuỗi ngày gốc.

4. **Bảo toàn tuyệt đối các lớp che nhạy cảm khác:**
   - Lớp che OpenAI API key (`sk-...`) và Google AI key (`AIza...`) giữ nguyên 100%.
   - Lớp che secret/password/token/apikey giữ nguyên 100%.

---

## 3. ĐOẠN TRÍCH NGUYÊN VĂN MÃ NGUỒN SỬA ĐỔI (VERBATIM CODE SNIPPETS)

Trong `src/aios_habit/brain_gateway.py`:
```python
_DATE_REDACT_GUARD_PATTERN = re.compile(
    r'(?<![\w/\\])'
    r'(?:'
    r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'
    r'|'
    r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    r')'
    r'(?![\w/\\])'
)


def sanitize_text(text: str) -> str:
    if not text:
        return ""

    # DESKTOP-EVIDENCE-DATE-REDACT-FIX-HOME:
    # Bảo vệ các chuỗi ngày (yyyy/mm/dd, yyyy-mm-dd, dd/mm/yyyy) không bị nhận nhầm
    # thành đường dẫn nội bộ (trước đây regex Unix path ăn nhầm phần đuôi /mm/dd).
    preserved_dates: list[str] = []

    def _preserve_date(match: re.Match[str]) -> str:
        preserved_dates.append(match.group(0))
        return f"__AIOS_PRESERVED_DATE_{len(preserved_dates) - 1}__"

    text = _DATE_REDACT_GUARD_PATTERN.sub(_preserve_date, text)

    # Redact Windows paths (bao gồm cả dấu gạch chéo xuôi/ngược và khoảng trắng)
    # Ví dụ: D:\Sandbox Folder\secret.txt, C:\Users\Admin\My Documents\a.txt
    text = re.sub(r'(?i)[a-z]:\\(?:[^\\:\"\'<>\|\?\*]+(?:\\|/))*[^\\:\"\'<>\|\?\*\s]+(?:\.[a-zA-Z0-9]{2,4})?', '[REDACTED_LOCAL_PATH]', text)
    text = re.sub(r'(?i)[a-z]:/(?:[^\\:\"\'<>\|\?\*]+(?:\\|/))*[^\\:\"\'<>\|\?\*\s]+(?:\.[a-zA-Z0-9]{2,4})?', '[REDACTED_LOCAL_PATH]', text)
    # Tiếp tục quét các Windows path dạng C:\path\to\file nếu còn sót
    text = re.sub(r'[a-zA-Z]:\\[^\s\)\(\"\']+', '[REDACTED_LOCAL_PATH]', text)
    text = re.sub(r'[a-zA-Z]:/[^\s\)\(\"\']+', '[REDACTED_LOCAL_PATH]', text)

    # Redact UNC paths (\\\\server\\share hoặc //server/share)
    text = re.sub(r'(?<![\w/\\])(?:\\\\|//)[a-zA-Z0-9_\.\-]+(?:[\\/][^\s\)\(\"\'<>\|\?\*]+)+', '[REDACTED_LOCAL_PATH]', text)

    # Redact User home paths (~/...)
    text = re.sub(r'(?<![\w/\\])~[\\/][^\s\)\(\"\'<>\|\?\*]+', '[REDACTED_LOCAL_PATH]', text)

    # Redact Unix paths (chặn ăn nhầm chuỗi không bắt đầu ở đầu đường dẫn)
    text = re.sub(r'(?<![\w/\\])/(?:[a-zA-Z0-9_\.\-]+/)+[^\s\)\(\"\'<>\|\?\*]+', '[REDACTED_LOCAL_PATH]', text)

    # Khôi phục các chuỗi ngày đã được bảo vệ
    for idx, original_date in enumerate(preserved_dates):
        text = text.replace(f"__AIOS_PRESERVED_DATE_{idx}__", original_date)

    # Redact API Keys / secrets (e.g. sk-..., AIza...)
    text = re.sub(r'(sk-[a-zA-Z0-9]{8,})', '[REDACTED_API_KEY]', text)
    text = re.sub(r'(AIza[a-zA-Z0-9_\-]{8,})', '[REDACTED_API_KEY]', text)

    # Redact secret-like patterns (case-insensitive)
    text = re.sub(r'(?i)(secret|token|api_key|password|private_key|api-key|apikey)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.\+@]{8,}["\']?', r'\1=[REDACTED_SECRET]', text)
    return text
```

---

## 4. KẾT QUẢ KIỂM THỬ HỒI QUY HAI CHIỀU (TEST EVIDENCE)

Đã bổ sung bộ kiểm thử chuyên dụng tại `tests/test_evidence_date_redact_fix_home.py` bao phủ đầy đủ hai chiều và tích hợp cổng BrainGateway:
```text
============================= test session starts =============================
platform win32 -- Python 3.11.14, pytest-8.4.2, pluggy-1.6.0
rootdir: D:\Sandbox\AIOS_habbit
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 57 items

tests\test_evidence_date_redact_fix_home.py ..............               [ 24%]
tests\test_brain_gateway_privacy_policy.py .......................       [ 64%]
tests\test_brain_gateway_router_mock.py ....................             [100%]

============================= 57 passed in 1.16s ==============================
```

Chi tiết 14 ca kiểm thử chuyên sâu mới trong `tests/test_evidence_date_redact_fix_home.py`:
1. `test_date_yyyy_mm_dd_slash_not_redacted`: Chuỗi `2026/08/20` và `2026/08/21` không bị che.
2. `test_date_yyyy_mm_dd_dash_not_redacted`: Chuỗi `2026-08-20` không bị che.
3. `test_date_dd_mm_yyyy_slash_and_dash_not_redacted`: Chuỗi `20/08/2026` và `21-08-2026` không bị che.
4. `test_date_single_digit_month_day_not_redacted`: Chuỗi `2026/8/20` và `1/8/2026` không bị che.
5. `test_date_in_csv_evidence_line_not_redacted`: Bản ghi dòng CSV `2026/08/20,09:40:32,61C999999902...` giữ nguyên ngày và giờ.
6. `test_serial_61c999999902_four_rows_evidence_dates_preserved`: Dữ kiện đối chiếu chuẩn xác của serial `61C999999902` (4 dòng: 1 dòng ngày 20/08, 3 dòng ngày 21/08) giữ nguyên 100%.
7. `test_dates_in_punctuation_and_brackets_not_redacted`: Ngày trong dấu ngoặc `(2026/08/20)`, `[2026/08/21]`, `'2026/08/22'`, `\"2026/08/23\"` không bị che.
8. `test_windows_drive_paths_redacted`: Đường dẫn Windows `D:\...` và `C:/...` vẫn bị che `[REDACTED_LOCAL_PATH]`.
9. `test_unc_paths_redacted`: Đường dẫn UNC `\\filestore.local\...` và `//smbserver\...` vẫn bị che `[REDACTED_LOCAL_PATH]`.
10. `test_user_home_paths_redacted`: Đường dẫn `~/.aios/...` vẫn bị che `[REDACTED_LOCAL_PATH]`.
11. `test_unix_absolute_paths_redacted`: Đường dẫn Unix `/var/log/...` và `/home/...` vẫn bị che `[REDACTED_LOCAL_PATH]`.
12. `test_unix_path_containing_date_folders_is_still_redacted`: Đường dẫn thật chứa thư mục ngày `/var/log/production/2026/08/20/error.log` vẫn bị che trọn vẹn `[REDACTED_LOCAL_PATH]`.
13. `test_api_keys_and_tokens_remain_redacted`: Lớp che `sk-...`, `AIza...`, `password`, `api_key` giữ nguyên 100%.
14. `test_brain_gateway_preflight_preserves_dates_in_question_and_sources`: Tích hợp end-to-end qua `BrainGateway.preflight_check`.

---

## 5. XÁC THỰC 4 CỔNG CHẤT LƯỢNG REPO (QUALITY GATES)

| Cổng | Lệnh thực thi | Kết quả | Ghi chú chi tiết |
|---|---|---|---|
| **Cổng 1: compileall** | `python -m compileall src tests scripts -q` | **PASS (exit code 0)** | Toàn bộ mã nguồn `src`, kiểm thử `tests` và kịch bản `scripts` sạch cú pháp Python |
| **Cổng 2: pytest liên quan** | `pytest tests/test_evidence_date_redact_fix_home.py tests/test_brain_gateway_privacy_policy.py tests/test_brain_gateway_router_mock.py` | **PASS (57/57 tests)** | 100% test xanh tuyệt đối, thời gian chạy 1.16s |
| **Cổng 3: cli audit** | `python -m aios_habit.cli audit` | **PASS (exit code 0)** | Trả về `{"errors": [], "status": "PASS", "warnings": []}` sạch sẽ |
| **Cổng 4: import app** | `python -c "import aios_habit.workspace_chat_app"` | **PASS (exit code 0)** | Ứng dụng bootstrap thành công hoàn toàn |

---

## 6. NGHIỆM THU TRÊN GIAO DIỆN THẬT PLAYWRIGHT (CHUẨN SẢN PHẨM)

Đã thực thi kiểm thử giao diện tự động bằng Playwright trên máy nhà (`h410asrock`, CPU-only) theo kịch bản [`scripts/run_evidence_date_redact_fix_home_ui.py`](file:///D:/Sandbox/AIOS_habbit/scripts/run_evidence_date_redact_fix_home_ui.py):
- **Sổ tay:** `mom_opcenter`
- **Khối ghim (Pinned Block):** `lsu`
- **Mã hội thoại:** `CONV-DATE-REDACT-0B8EDE`
- **Câu hỏi biến thể:** *"Trong tệp 2026_08_UnitTest.csv, serial 61C999999902 có kết quả kiểm tra như thế nào qua các ngày?"*
- **Thời gian phản hồi:** **55.53s**
- **Trạng thái:** `HOAN_THANH` (completed=True)

### 6.1. Đáp án thực tế hiển thị trên giao diện (Đọc đầy đủ mốc ngày cụ thể)
```markdown
Dựa trên tệp **2026_08_UnitTest.csv** [1], kết quả kiểm tra phán định chi tiết của Serial **61C999999902** qua các ngày như sau:

* **Ngày 2026/08/20:**
  * `TotalJudge` = NG
  * `Black`: NG
  * `Magenta`: NG
  * `Cyan`: OK
  * `Yellow`: NG

* **Ngày 2026/08/21:**
  * `TotalJudge` = NG
  * `Black`: NG
  * `Magenta`: NG
  * `Cyan`: OK
  * `Yellow`: NG

* **Kết luận:** Hạng mục NG giữa các ngày là như nhau, không đổi (変わっていません) [1].

Nguồn tệp dữ liệu: **2026_08_UnitTest.csv** [1].
```

### 6.2. Đối soát dữ kiện chất lượng theo yêu cầu của vé
- Serial `61C999999902` có đúng 4 dòng trong tệp nguồn `2026_08_UnitTest.csv`:
  - **Ngày 2026/08/20:** 1 dòng (lúc 09:40:32).
  - **Ngày 2026/08/21:** 3 dòng (lúc 19:53:10, 19:54:01, 19:56:14).
- Đáp án đọc rõ ràng cả hai mốc ngày **2026/08/20** và **2026/08/21**, không hề bị che nhầm thành `[REDACTED_LOCAL_PATH]`.
- Phán định đúng 100%: Cả 2 ngày TotalJudge đều là NG (Black: NG, Magenta: NG, Cyan: OK, Yellow: NG).

### 6.3. Hồ sơ bằng chứng ảnh (Áp cổng bằng chứng bản siết 11/10)
Cả 2 ảnh đều đã được lưu trữ và kiểm định tính toàn vẹn:
1. **Ảnh App Ready:**
   - Tệp: [`docs/phieu-viec/ket-qua/evidence-date-redact-01-app-ready.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/evidence-date-redact-01-app-ready.png)
   - Kích thước: **132.775 bytes**
   - Mã băm SHA-256: `3CA7E5AC3650DCEAB4C31A36825D3454AA35D1D0A5CA3850C93169E3961E1764`
2. **Ảnh trọn thân đáp án câu biến thể:**
   - Tệp: [`docs/phieu-viec/ket-qua/evidence-date-redact-02-cau-bien-the-dates.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/evidence-date-redact-02-cau-bien-the-dates.png)
   - Kích thước: **146.800 bytes**
   - Mã băm SHA-256: `81B66C95F6C4C7318E169604C96CDE22C703281D398D1F0ADF6144E2075F3D22`
- **Kiểm định trùng byte:** `sha_ready != sha_answer` (Hoàn toàn khác biệt, không trùng byte, thân đáp án nằm trọn vẹn trong viewport).

---

## 7. KẾT LUẬN & BÀN GIAO
- Lỗi bộ che dữ kiện ăn nhầm chuỗi ngày thành đường dẫn cục bộ đã được xử lý triệt để tận gốc.
- Đã bổ sung 14 bài kiểm tra hồi quy hai chiều bảo vệ an toàn dài hạn.
- Đã nghiệm thu giao diện thật trên máy nhà và đẩy đầy đủ mã nguồn, test, ảnh bằng chứng lên kho từ xa.

```json
{
  "ma_ve": "DESKTOP-EVIDENCE-DATE-REDACT-FIX-HOME",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-15T19:20:00.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
