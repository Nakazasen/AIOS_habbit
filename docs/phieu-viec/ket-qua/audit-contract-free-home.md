# Báo cáo vé AUDIT-CONTRACT-FREE-HOME — Kiểm lại độc lập báo cáo hợp đồng tổng hợp model free

- **Mã vé:** `AUDIT-CONTRACT-FREE-HOME`
- **Máy thực hiện:** NHÀ `h410asrock` (OMP — thợ phụ, chỉ đọc).
- **Thời gian:** 2026-10-08 23:52 – 2026-10-09 00:10 +07.
- **Báo cáo gốc:** `docs/phieu-viec/ket-qua/synth-contract-free-home.md` (agy, verdict ĐẠT-kết-quả-âm).
- **Dữ kiện thô (còn đủ tại máy nhà, ngoài Git):** `C:/tmp/lsu-quality-rag-home/rows-synth-contract-disciplined.jsonl` (50 dòng), `ket-qua-synth-contract-disciplined.json`, `tien-trinh-synth-contract-disciplined.log`, `do_rag_50_synth_contract_free.py`, đối chứng `rows-synth-ab-a/b/c.jsonl`.
- **Cách làm:** đọc trực tiếp từng dòng rows bằng Python, tính lại tổng/GPA/phân rã theo `che_do`/phân rã lỗi theo `validation_errors` từng lượt gọi, so từng ô với báo cáo gốc.
- **Rào cứng giữ nguyên:** chỉ đọc, không chạy lại lượt đo, không đổi cấu hình, không đụng chỉ mục, không merge `main`.

## 1. Số lượt đo (điểm 1 của vé)

| Chỉ số | Báo cáo gốc | Đếm lại từ dữ kiện thô | Kết luận |
|---|---|---|---|
| Số dòng rows | 50 câu | 50/50 dòng trong `rows-synth-contract-disciplined.jsonl` | KHỚP |
| Tổng điểm / GPA | 60,67 / 1,21 | `sum(tong)` = 60,67; GPA = 1,21 | KHỚP |
| Validated | 0/50 | `che_do` chứa `validat` = 0 dòng; trường `validated` = False cả 50 | KHỚP |
| Fallback | 48/50 | `local_extractive_provider_fallback` = 48 | KHỚP |
| Not called | 2/50 (Q0824, Q0668) | `local_extractive_provider_not_called` = 2, đúng Q0824 + Q0668, điểm 0,0 cả hai | KHỚP |
| Đạt 3,0 / đạt ≥2,0 | 4 / 6 | 4 câu 3,0 (Q0689, Q0695, Q1777, Q0680) / 6 câu ≥2,0 (thêm Q0636, Q0674) | KHỚP |
| Trễ TB toàn câu / TB tổng hợp | 16,32s / 7,04s | TB `giay_cau` = 16,32s; TB `giay_tong` = 7,04s | KHỚP |
| Lỗi kỹ thuật | 0/50 | `ok` = True cả 50 | KHỚP |
| Tổng lượt gọi provider | 36 | 36 phần tử `luot_goi_provider` (21 dòng có gọi: 15 dòng × 2 + 6 dòng × 1; 29 dòng 0 lượt) | KHỚP |
| Toàn vẹn index | SHA/MD5/size khớp | `ket-qua-*.json` ghi SHA trước = sau, `index_chi_doc_khop: true`; log tiến trình ghi khớp | KHỚP (theo file, không băm lại vì ngoài phạm vi chỉ-đọc) |

## 2. Phân rã lỗi kiểm định (điểm 2 của vé)

### 2.1. Bảng §1 báo cáo gốc (cơ sở A/B/C)

| Mã lỗi | Lượt A (70 gọi) | Lượt B (29 gọi) | Lượt C (15 gọi) | Đếm lại |
|---|---|---|---|---|
| `uncited_material_claim` | 69 (98,6%) | 27 (93,1%) | 14 (93,3%) | KHỚP cả 3 |
| `missing_required_limitations` | 64 (91,4%) | 25 (86,2%) | 9 (60,0%) | KHỚP cả 3 |
| `claim_budget_exceeded` | 62 (88,6%) | 22 (75,9%) | 12 (80,0%) | KHỚP cả 3 |
| `unsupported_critical_literal` | 46 (65,7%) | 14 (48,3%) | 8 (53,3%) | KHỚP cả 3 |
| `missing_citations` | 0 (0,0%) | 2 (6,9%) | 2 (13,3%) | KHỚP cả 3 |

Đối chứng A kiểm thêm: 50 dòng, fallback 46 + not_called 2 + `provider_validated` 2 (đúng Q0689 3,0 và Q0677 2,0), tổng 61,67 — khớp báo cáo gốc.

### 2.2. Bảng §3 báo cáo gốc (lượt thử hợp đồng kỷ luật, 36 gọi)

| Mã lỗi | Báo cáo gốc | Đếm lại | Kết luận |
|---|---|---|---|
| `uncited_material_claim` | 36/36 (100%) | 36/36 | KHỚP |
| `claim_budget_exceeded` | 35/36 (97,2%) | 35/36 | KHỚP |
| `missing_required_limitations` | 32/36 (88,9%) | 32/36 | KHỚP |
| `unsupported_critical_literal` | (không nêu) | 24/36 (66,7%) | GHI NHẬN — báo cáo không sai, chỉ thiếu 1 mã |
| `missing_citations` | (không nêu) | 0/36 | KHỚP ngầm (không có) |

Ví dụ hành vi §4.1: Q0708 có đủ 2 lượt gọi trong dữ kiện thô, attempt đầu và attempt repair đều mở đầu bằng câu `"The user asks..."` không trích dẫn — khớp trích dẫn trong báo cáo. Q0662 được nêu tên cùng Q0708 nhưng trong dữ kiện thô Q0662 là dòng 0 lượt gọi (rơi về fallback, có dấu hiệu lỗi mạng nhà cung cấp) nên không có đáp án provider nào để giải phẫu — mọi bằng chứng chữ đều từ Q0708.

**Đính chính về con số "14 câu dính 429":** dữ kiện thô không ghi mã trạng thái số nào; chỉ có 29 dòng 0 lượt gọi (27 fallback + 2 not-called), trong đó 27 dòng fallback mang cảnh báo `failed(rate_limited)` và thêm 6 dòng có gọi vẫn mang cảnh báo này (tổng 33 dòng chạm cảnh báo). Con số 14 không tái lập được từ file thô còn lại (ghi chú giữa chừng của agy lúc 10:15 ghi "18 câu", cũng không phải 14). Đề nghị diễn đạt lại thành số đếm được từ rows.

## 3. Cờ hợp đồng sau lượt đo (điểm 3 của vé, chỉ mức tên biến/cờ)

| Hạng mục | Kết quả kiểm |
|---|---|
| Tên cờ trong code (`src/aios_habit/rag_v2/synthesis.py`) | `AIOS_SYNTHESIS_STRICT_CITATION_CONTRACT`, tài liệu trong code ghi mặc định TẮT |
| Giá trị môi trường tại máy nhà lúc audit | Chưa đặt (tắt) |
| Test hồi quy biến thể (`tests/test_rag_v2_synthesis.py`) | Tồn tại `test_disciplined_citation_contract_format` (không chạy lại, ngoài phạm vi chỉ-đọc của vé) |
| Thay đổi code/cấu hình trong lúc audit | Không có (`git status` vùng `src`/`tests` sạch) |

Không sao chép bất kỳ giá trị khóa hay bí mật nào.

## 4. Kết luận (điểm 4 của vé)

**Báo cáo gốc đứng vững** — mọi số cốt lõi (50 câu, 60,67/1,21, validated 0/50, fallback 48, not-called Q0824/Q0668, 36 lượt gọi với 3 tỉ lệ lỗi nêu, toàn bộ bảng §1 ba lượt A/B/C, ví dụ Q0708) tái lập 100% từ dữ kiện thô; quyết định giữ cờ TẮT có đủ căn cứ; cần 3 đính chính nhẹ ghi hồ sơ không đổi kết luận: (1) con số "14 câu dính 429" không tái lập được từ rows (đếm được 27 dòng fallback 0 lượt gọi mang cảnh báo giới hạn tốc độ); (2) bảng lượt thử thiếu mã `unsupported_critical_literal` 24/36; (3) ví dụ Q0662 không có đáp án provider nào trong dữ kiện thô, mọi trích dẫn hành vi đều từ Q0708.
