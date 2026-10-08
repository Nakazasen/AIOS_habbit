# Báo cáo audit độc lập — kết quả đo vé `ROUTER-POOL-COMMANDCODE-HOME`

- **Người thực hiện:** OMP (thợ phụ) — máy nhà `h410asrock`, phiên 2026-10-08 ~07:50–08:05 +07.
- **Phạm vi:** việc phụ #1 do điều phối Muse giao sau vé `RAG-CLAIM-BUDGET-HOME`.
  **Chỉ đọc + tính lại** — không sửa code, không ghi index, không merge `main`.
- **Nguồn đối chiếu:** báo cáo `docs/phieu-viec/ket-qua/router-pool-commandcode-home.md` (thợ agy)
  với dữ liệu thô tại máy nhà (ngoài Git): `C:/tmp/lsu-quality-rag-home/rows-commandcode-pool.jsonl`,
  `ket-qua-commandcode-pool.json`, `tien-trinh-commandcode-pool.log`, runner `do_rag_50_commandcode_pool.py`.
- **Cách làm:** đọc trực tiếp 50 hàng rows bằng Python, đếm theo trường `che_do` (nguồn chuẩn vận hành),
  rà `luot_goi_provider/attempts` từng lượt gọi, đối chiếu từng tuyên bố số trong bảng §4.2 của báo cáo.

## 1. Số tự tính lại từ dữ liệu thô (nguồn chuẩn = rows)

- Tổng điểm **62,67/150, GPA 1,25**; câu ≥2: **7**; câu =3: **5** (`Q0689, Q0695, Q0693, Q1777, Q0680`);
  hai câu 2,33: `Q0636, Q0674`.
- Phân bố chế độ: **47** `local_extractive_provider_fallback` + **2** `local_extractive_provider_not_called`
  (`Q0824, Q0668`) + **1** `provider_validated` (`Q0693`, 3,0 điểm, 8 khối bằng chứng, 1 lượt gọi).
- Lượt gọi provider: **94** (46 lượt sửa). Model phục vụ ở mức lượt gọi: `ling-3.0-flash-sante:free` **90**,
  `ling-3.1-flash:free` **2**, `poolside/laguna-s-2.1-free` **2** → **cả 3 model trong pool đều đã phục vụ thật**
  trong lane (cột `model_tra_loi` cấp câu ghi 48 câu do `ling-3.0-flash-sante:free`).
- `ok=True` cả **50/50** hàng; `attempts` **94/94** trạng thái `success`; không có dấu vết 429/5xx/lỗi mạng
  trong `limitation_reasons` (chỉ có lỗi nội dung kiểm định) và `nhat_ky_provider` rỗng toàn bộ.
- Thời gian thật: **trung bình 47,4s/câu** (nhanh nhất 9,6s — chậm nhất 184,5s ở câu đầu `Q0699`, gồm khởi động nguội).
- Lỗi kiểm định theo lượt gọi (thông tin thêm): `uncited` 93, `budget` 76, `missing_required_limitations` 82,
  `literal` 49, `missing_citations` 7, `facet` 1.

## 2. Đối chiếu tuyên bố của báo cáo (từng dòng bảng §4.2)

| Tuyên bố | Kết quả audit |
|---|---|
| Tổng 62,67/150, GPA 1,25 | **KHỚP** |
| Validated 1 câu (`Q0693`) / fallback 47 / không gọi 2 (`Q0824, Q0668`) | **KHỚP rows** (đúng theo `che_do`) |
| 5 câu =3,0 đúng danh sách; thêm `Q0636/Q0674` 2,33 | **KHỚP** |
| “0% (0/50 câu lỗi kỹ thuật / rate-limit)” | **KHỚP cục bộ** (ok 50/50, attempts success 100%, không rate-limit) |
| Index chỉ-đọc | **KHỚP**: SHA-256 trước = sau = `45eb0e07…b7c0`, md5 `23900967…`, size 2.942.201.856 byte |
| Preload 121.331 chunk (dense 62,7s / sparse 66,7s) | **KHỚP** `ket-qua-commandcode-pool.json` |
| 3 model pool nạp với priority 10/12/14 + failover | **KHỚP**: log nạp đủ 3 provider; cả 3 model phục vụ thật (90/2/2 lượt gọi) |
| “$0 credits (100% Free trên GOAT)” | **khớp chứng cứ cục bộ**: mọi model xuất hiện (log + rows + attempts) đều hậu tố `:free`; không có dấu vết model trả phí. Hoá đơn thật phải xem dashboard Command Code — ngoài dữ liệu máy |
| Mô hình phục vụ chính `ling-3.0-flash-sante:free` (48 câu) | **KHỚP** cột `model_tra_loi` |

## 3. Phát hiện lệch số (cần ghi nhớ khi trích dẫn)

- `ket-qua-commandcode-pool.json` và dòng chốt log ghi **`validated=0, fallback=50`** — **SAI** so với rows (**1/47/2**).
- Nguyên nhân (đã lần theo runner ngoài Git `do_rag_50_commandcode_pool.py`, dòng 283/321/322):
  1. Runner đọc `getattr(tong_hop, "validated", False)` — nhưng `LocalSynthesisResult`
     (`src/aios_habit/rag_v2/synthesis.py` dòng 44–56) **không có trường `validated`** → cờ luôn `False`;
  2. Công thức `fallback` so `che_do != "EvidenceAnswerMode.ANSWER"` — chuỗi `che_do` thực tế dạng
     `local_extractive_provider_fallback` / `provider_validated` / `..._not_called` nên **không bao giờ khớp** → dồn hết 50 vào fallback.
- Hệ quả: **bảng §4.2 của báo cáo là số ĐÚNG** (1/47/2 — cùng rows); hai chỗ sai là file tổng + dòng log chốt.
- Khuyến nghị (không thuộc code repo): khi trích dẫn kết quả lane, đếm theo `che_do` từ `rows-*.jsonl`;
  runner họ này nên sửa bộ đếm theo `che_do` ở lần đo sau (lỗi đếm thuần vận hành, không ảnh hưởng pipeline).

## 4. Lưu ý vận hành (trung thực)

- GPA 1,25 **nằm giữa** SYNTH (1,22) và FIX1 (1,29) — không phải “tương đương/vượt” mức cũ; đúng hơn là *ổn định, nhích nhẹ*.
- Tuyến pool ổn định về kỹ thuật (0 lỗi, không rate-limit) nhưng **chỉ 1/50 câu qua kiểm định nội dung**:
  94 lượt gọi dính `budget` 76, `uncited` 93, `literal` 49 → model free viết vượt ngân sách/thiếu trích dẫn nhiều;
  khớp việc điều phối đã xếp vé `SYNTH-MODEL-AB` tiếp theo.
- Tốc độ lane pool chậm hơn tuyến cũ: **TB 47,4s/câu** vs ~15,9s/câu (cầu Gemini 8585, lane BUDGET) — cần lưu ý khi so thời gian các lane sau.

## 5. Kết luận audit

- Các số cốt lõi của báo cáo **khớp dữ liệu thô**: tổng/GPA, phân bố chế độ, danh sách câu điểm cao,
  index chỉ-đọc không ghi, 0 lỗi kỹ thuật, 3 model pool hoạt động.
- Một lệch số duy nhất nằm ở **file tổng + log của runner** (`validated=0/fallback=50`) — bảng báo cáo không bị ảnh hưởng;
  nguyên nhân đã truy tới dòng code runner (ngoài Git).
- Tuyên bố “$0 credits” khớp chứng cứ cục bộ (toàn model `:free`); xác nhận cuối cùng cần dashboard nhà cung cấp.
- Audit chỉ-đọc: **không sửa code, không ghi index, không merge `main`**.
