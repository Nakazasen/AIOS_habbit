# BÁO CÁO NGHIỆM THU VÉ: DESKTOP-HOME-HUONGDAN-I18N

- **Mã vé:** `DESKTOP-HOME-HUONGDAN-I18N`
- **Tiêu đề:** Lệnh hướng dẫn 3 ngôn ngữ — Gõ lệnh bằng ngôn ngữ nào thì hiện cẩm nang bằng ngôn ngữ đó
- **Trạng thái:** `HOAN_THANH`
- **Thợ thực hiện:** Antigravity Desktop Engine (Model: `Gemini 2.5 Flash`, Thinking Level: `1.00`)
- **Môi trường:** Python 3.11.14 (Virtualenv `D:\Sandbox\AIOS_habbit\.venv`), Windows Desktop
- **Nhánh thực thi repo code:** `phieu-viec/rag-fix1`
- **Thời điểm đóng vé:** `2026-10-23T05:15:00+07:00`

---

## 1. TỔNG QUAN VÀ MỤC TIÊU THỰC HIỆN

Thực hiện yêu cầu người dùng (chốt 2026-10-23 ~03:19): *"hướng dẫn sử dụng phải có 3 thứ tiếng Việt/Trung/Nhật; muốn xem ngôn ngữ nào thì gõ lệnh trên giao diện bằng ngôn ngữ đó."*

Vé này mở rộng tính năng cẩm nang hướng dẫn sử dụng từ vé gốc `DESKTOP-HOME-HUONGDAN-COMMAND` sang hỗ trợ toàn diện 3 ngôn ngữ:
1. **Đưa 2 tệp dịch tiếng Trung (ZH) và tiếng Nhật (JA) vào repo code:**
   - `docs/huong-dan-su-dung/HUONG-DAN-SU-DUNG-AIOS-ZH.md`: `28.276 bytes`, SHA-256 `7873CBA842EB8DF8CE96CDA9FAA2B807A36C4B3A9474CCCC935C05AE25AD642B`.
   - `docs/huong-dan-su-dung/HUONG-DAN-SU-DUNG-AIOS-JA.md`: `37.035 bytes`, SHA-256 `A929E37A2FF94FD3ADBCC9C05C67D7DDF20332D71A32628F2410E1C569FC4EA4`.
   - Giữ nguyên vẹn 100% từng byte và checksum từ kho điều phối. Dùng chung 57 ảnh minh họa đã có trong `docs/huong-dan-su-dung/images/`.
2. **Nhận diện và định tuyến lệnh theo 3 ngôn ngữ:**
   - Lệnh tiếng Việt: `/huongdan` (và các biến thể hiện có) -> cẩm nang tiếng Việt.
   - Lệnh tiếng Nhật: `/使い方` (và `使い方`) -> cẩm nang tiếng Nhật.
   - Lệnh tiếng Trung: `/使用指南` (và `使用指南`) -> cẩm nang tiếng Trung.
   - Gõ lệnh bằng ngôn ngữ nào thì danh mục, từng mục, toàn bộ và huy hiệu chat bubble hiển thị bằng ngôn ngữ đó.
   - Các nút chip gợi ý điều hướng hiển thị đúng ngôn ngữ và gửi lệnh tương ứng (`/使い方 <mục>`, `/使用指南 <mục>`, `/huongdan <mục>`). Mã mục (`A1`..`G18`, `C4`...) và tham số dùng chung cho cả 3 ngôn ngữ.
3. **Mở rộng metric vòng lặp cải thiện liên tục (Continuous Improvement):**
   - Bổ sung trường `"language"` vào từng bản ghi `local_cases/huongdan_events.jsonl`.
   - Mở rộng phân rã `"by_language"` trong `local_cases/huongdan_metrics.json` mà không phá vỡ cấu trúc cũ.
4. **Bảo toàn tuyệt đối các bất biến (Invariants):**
   - Xử lý cục bộ 100% tất định (Zero-LLM Overhead).
   - Không gọi backend AI/C-Agent, không làm phát sinh lượt hỏi - đáp giả trong CSDL (`fake_turns_created = 0`).
   - Tự động ẩn cẩm nang khi gõ câu hỏi nghiệp vụ thông thường.
   - Không khóa nút gửi khi worker đang nạp kho.

---

## 2. CHI TIẾT TÍCH HỢP VÀ THAY ĐỔI MÃ NGUỒN

### 2.1. Bản dịch cẩm nang và hình ảnh minh họa
- Lưu trữ tại: `docs/huong-dan-su-dung/`
  - Tiếng Trung: `HUONG-DAN-SU-DUNG-AIOS-ZH.md` (28.276 bytes, SHA-256: `7873CBA842EB8DF8CE96CDA9FAA2B807A36C4B3A9474CCCC935C05AE25AD642B`).
  - Tiếng Nhật: `HUONG-DAN-SU-DUNG-AIOS-JA.md` (37.035 bytes, SHA-256: `A929E37A2FF94FD3ADBCC9C05C67D7DDF20332D71A32628F2410E1C569FC4EA4`).
  - Tiếng Việt: `HUONG-DAN-SU-DUNG-AIOS.md` (35.103 bytes, SHA-256: `008D2974F8F1E5FF141F9C5228F8331E8012BF6552187FAA87E1147E612B9B82`).
  - Dùng chung 57 ảnh minh họa tại `docs/huong-dan-su-dung/images/`, không nhân bản, không đổi tên.

### 2.2. Module cẩm nang đa ngữ: `src/aios_habit/huongdan_command.py`
- Hàm `detect_huongdan_language(text)`: Tự động phân loại ngôn ngữ dựa trên tiền tố câu lệnh (`ja` cho `/使い方`, `zh` cho `/使用指南`, `vi` cho `/huongdan`).
- Hàm `resolve_manual_path(lang)`: Trỏ tới đúng tệp markdown theo mã ngôn ngữ, hỗ trợ ghi đè biến môi trường.
- Hàm `load_and_parse_manual(lang)`: Bóc tách tự động 9 phần chính và 44 tiểu mục theo thẻ tiêu đề chuẩn của từng ngôn ngữ, tạo bảng danh mục tổng quan bản ngữ, cache riêng biệt theo mã ngôn ngữ.
- Hàm `parse_huongdan_args(text, lang)`: Trích xuất mã phân đoạn dùng chung (`danh_muc`, `tat_ca`, `gioi_thieu`, `phu_luc`, `dong`, `A1`..`G18`, `A`..`G`) hỗ trợ cả từ khóa tiếng Nhật (`全体`, `目次`, `付録`, `閉じる`), tiếng Trung (`全部`, `目录`, `附录`, `关闭`) và tiếng Việt.
- Hàm `get_chips_for_section(section_key, lang)`: Sinh danh sách chip gợi ý bằng đúng ngôn ngữ mục tiêu kèm tiền tố lệnh bản ngữ (`/使い方`, `/使用指南`, `/huongdan`).
- Hàm `record_huongdan_metric` & `get_huongdan_metrics`: Ghi nhận nhật ký sự kiện kèm trường `language` và thống kê lũy kế `by_language` (`vi`, `ja`, `zh`).

### 2.3. Định tuyến ý định: `src/aios_habit/chat_intent_router.py`
- Bổ sung `/使い方`, `/使用指南`, `使い方`, `使用指南` vào danh sách quy tắc `_QUY_TAC` với độ ưu tiên cao nhất.
- Bổ sung giải mã `language` và `muc` trong `classify_all_intents` và `extract_slots`.

### 2.4. Trình bày giao diện: `src/aios_habit/workspace_chat_app.py`
- Lưu trữ trường `language` vào `st.session_state[f"wsc_huongdan_display_{conv_id}"]`.
- Cập nhật `_render_huongdan_chat_bubble`:
  - Tiếng Nhật: Huy hiệu `📖 AIOS台帳 総合利用マニュアル`, chú thích `下の項目を素早く選択：`.
  - Tiếng Trung: Huy hiệu `📖 AIOS 台账综合使用指南`, chú thích `在下方快速选择项目：`.
  - Tiếng Việt: Huy hiệu `📖 Cẩm nang Hướng dẫn sử dụng AIOS`, chú thích `Chọn nhanh hạng mục bên dưới:`.

### 2.5. Mở rộng kiểm thử đơn vị: `tests/test_huongdan_command.py`
- Toàn bộ 9/9 ca kiểm thử đơn vị bao phủ toàn diện 3 ngôn ngữ chạy trên Python 3.11 đều đạt PASS 100%.

---

## 3. KẾT QUẢ NGHIỆM THU 5 CỔNG TRÊN MÀN HÌNH DESKTOP THỰC TẾ

Kịch bản nghiệm thu tự động hóa có kiểm soát: `scripts/verify_desktop_huongdan_i18n.py` chạy trên Python 3.11 với Playwright mở trình duyệt Chromium thực tế hiển thị trên desktop (`headless=False`, viewport 1440x960), thao tác theo nhịp gõ phím của con người trên cuộc trò chuyện sạch `CONV-I18N-175C1B94` (sổ `NB-LAZY-LSU`).

### Bảng tổng hợp 5 Cổng Nghiệm thu:

| Cổng | Tên cổng nghiệm thu | Tiêu chí đánh giá | Kết quả thực tế | Trạng thái | Tệp ảnh minh chứng |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **1** | **Cẩm nang tiếng Nhật & Mở C4** | Gõ `/使い方` -> danh mục tiếng Nhật; gõ `/使い方 C4` -> nội dung C4 tiếng Nhật, giữ nguyên số liệu 136 lần / FY27H2/263 / 30.075 ca, ảnh minh họa Base64 hiển thị thật | Danh mục `AIOS台帳 総合利用マニュアル` hiển thị chuẩn; mở C4 có đầy đủ số liệu `136回`, `FY27H2/263件`, `30.075件`. Ảnh minh họa render thật kích thước **646.9px × 431.2px**. | **ĐẠT** | `anh-hd-i18n-01-japanese-c4.png` |
| **2** | **Cẩm nang tiếng Trung** | Gõ `/使用指南` -> danh mục tiếng Trung; mở mục C4 -> chữ tiếng Trung, số liệu 136 lần / FY27H2/263 | Danh mục `AIOS 台账综合使用指南` hiển thị chuẩn; mở C4 hiển thị `自动分类与第5步复发预警卡片`, đủ số liệu `136 次`, `FY27H2/263`. Ảnh hiển thị thật. | **ĐẠT** | `anh-hd-i18n-02-chinese-menu-and-section.png` |
| **3** | **Hồi quy tiếng Việt** | Gõ `/huongdan` -> danh mục tiếng Việt; mở C4 khớp bản tiếng Việt gốc | Danh mục `CẨM NANG HƯỚNG DẪN SỬ DỤNG SỔ CÁI AIOS` hiển thị chuẩn; mở C4 khớp 100% bản gốc tiếng Việt với số liệu 136 lần và ảnh thẻ cảnh báo tái phát. | **ĐẠT** | `anh-hd-i18n-03-vietnamese-regression.png` |
| **4** | **Đứng yên đường gửi chat $\ge$ 60s** | Gửi `/使い方` đúng 1 lần rồi để yên $\ge$ 60 giây không thao tác: hiện đúng 1 lần, không nhân đôi, không khóa giao diện | Gửi lúc `05:06:39`, danh mục hiện lúc `05:06:49`. Chờ tĩnh **61.2 giây**. Số tin nhắn assistant = 1, user = 0. Không nhân đôi, UI tương tác hoàn toàn mượt mà. | **ĐẠT** | `anh-hd-i18n-04-submission-stillness-60s.png` |
| **5** | **Chứng minh tạo 0 lượt giả** | Đếm tin nhắn CSDL hội thoại trước/sau cả 3 luồng ngôn ngữ: số lượt giả tạo ra = 0; hỏi câu thường trả lời tốt | Trước câu hỏi thường: **0 tin nhắn** trong CSDL. Sau câu hỏi RAG: đúng **2 tin nhắn** (1 user, 1 assistant). Số lượt giả tạo ra = **0**. | **ĐẠT** | `anh-hd-i18n-05-zero-fake-turns.png` |

---

## 4. CHI TIẾT DANH SÁCH ẢNH NGHIỆM THU & BẰNG CHỨNG HASH SHA-256

Toàn bộ các tệp ảnh và dữ liệu nghiệm thu JSON được lưu trữ đồng bộ tại hai vị trí:
1. Repo code `AIOS_habbit`: `docs/phieu-viec/ket-qua/`
2. Repo điều phối: `D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\`

| Tên tệp ảnh | Kích thước (bytes) | SHA-256 Checksum | Chú thích nội dung trong khung hình |
| :--- | :---: | :--- | :--- |
| `anh-hd-i18n-01-japanese-c4.png` | 213.667 | `FFC81939F767DEF9356308B676D05BF9DB61E717406E33CFD7ADA1B53F437610` | Cẩm nang tiếng Nhật: tiểu mục C4 (自動分類とステップ5再発警告カード) kèm ảnh minh họa và chip điều hướng tiếng Nhật |
| `anh-hd-i18n-02-chinese-menu-and-section.png` | 210.544 | `00E379C7B334AE244994931C960AF11E6BA14A30151E1C2742C08553EA3F0108` | Cẩm nang tiếng Trung: tiểu mục C4 (自动分类与第5步复发预警卡片) kèm ảnh minh họa và chip điều hướng tiếng Trung |
| `anh-hd-i18n-03-vietnamese-regression.png` | 204.770 | `27FB437C8B53AA95C383E467F8E411484CB183F2EEDF26843523A819C6630744` | Hồi quy cẩm nang tiếng Việt: tiểu mục C4 (Thẻ Cảnh báo Tái phát Bước 5) hiển thị chuẩn mực như vé gốc |
| `anh-hd-i18n-04-submission-stillness-60s.png` | 158.959 | `B5744AD1EB59B481D44A76104CEDA500E60D52BAA62F854ABC0FEFB6D8FCDBC3` | Danh mục tiếng Nhật xuất hiện sau khi gửi /使い方 và chờ tĩnh 61.2s, chứng minh không nhân đôi, không đơ UI |
| `anh-hd-i18n-05-zero-fake-turns.png` | 140.098 | `8BADB1159C73C3DF7CD4B03AE2600BBB084BA23C984D25F04D8184486C2E496F` | Khung chat sau câu hỏi RAG bình thường, minh chứng CSDL chỉ lưu đúng 2 tin nhắn thực, số lượt giả = 0 |

---

## 5. THỐNG KÊ METRICS VÒNG LẶP CẢI THIỆN LIÊN TỤC

Dữ liệu ghi nhận từ `local_cases/huongdan_metrics.json`:
```json
{
  "total_calls": 101,
  "by_section": {
    "C4": 37,
    "tat_ca": 27,
    "danh_muc": 32,
    "C": 5
  },
  "by_language": {
    "vi": 10,
    "ja": 10,
    "zh": 10
  },
  "last_called_at": "2026-10-23T05:08:09.827967+07:00"
}
```

---

```json
{
  "ma_ve": "DESKTOP-HOME-HUONGDAN-I18N",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-23T05:15:00+07:00",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
