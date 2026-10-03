# Vé: INDEX-SPLIT-HOME — tách index production thành 3 khối lĩnh vực (LSU / Điều-tra-lỗi / MOM)

Lane: [NHÀ] OMP chạy trên máy nhà (có quyền ghi index; VM không được ghi production index theo luật vòng tròn). Không merge `main`.

Code Phase A đã xong trên nhánh `phieu-viec/rag-fix1` (xem báo cáo `docs/phieu-viec/ket-qua/index-split-phaseA.md`). Vé này chỉ chạy công cụ, không sửa code.

## Bối cảnh

User chốt tách toàn bộ index production (`C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`, 149.800 chunk / 889 document, 1 collection duy nhất) thành 3 khối riêng theo lĩnh vực. Vector dense+sparse đã có sẵn — KHÔNG embed lại, chỉ copy.

## Việc OMP làm

### Bước 0 — Chuẩn bị
1. Pull nhánh `phieu-viec/rag-fix1` mới nhất. KHÔNG dùng máy công ty (lệnh user: cuối tuần 2026-10-03–04 không đụng PC0575).
2. Backup toàn bộ `C:\AIOS_workspace_chat_rag_v2_production\` ra ổ D (hoặc thư mục backup đã chốt). Ghi SHA-256 + kích thước + mtime của `collections\tri_thuc\library.sqlite` TRƯỚC khi làm.

### Bước 1 — Dry-run, báo phân bố
3. Chạy (trong repo, Python 3.11):
   `python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "C:\AIOS_index_split_preview" --dry-run`
   (lưu ý: script tự chặn production nếu thiếu `--allow-production` — dry-run không ghi file nên không cần cờ này).
4. Copy kết quả phân bố (3 khối: số document/chunk/độ tin cậy TB + danh sách confidence thấp) vào báo cáo. **DỪNG ở đây để user rà danh sách confidence thấp** nếu số lượng lớn bất thường.

### Bước 2 — Tách thật
5. Chạy tách thật với `--allow-production` (đọc nguồn read-only; chỉ ghi vào `--out`):
   `python -m aios_habit.split_index_by_domain --source "...\tri_thuc\library.sqlite" --out "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections_new" --allow-production`
6. Đọc `collections_new\domain_manifest.json`: `overall` phải là `DAT`; tổng chunk 3 khối = 149.800 (hoặc tổng thực tế, ghi rõ); tổng document = 889; `overlapping_documents` rỗng.

### Bước 3 — Chuyển app sang 3 kho mới
7. Đổi tên `collections_new` → ghi đè cấu trúc collection: tạo 3 collection `lsu`, `dieu_tra_loi`, `mom` trỏ storage_root tới 3 thư mục đã tách (giữ nguyên file `tri_thuc` cũ — KHÔNG xóa, KHÔNG ghi vào đó).
8. Bật định tuyến lĩnh vực: `AIOS_DOMAIN_ROUTING_ENABLED=1`, restart app.
9. Hỏi đáp thử: 1 câu LSU (VD: log jig báo bowskew), 1 câu điều tra lỗi (VD: mã lỗi Fxxx và đối sách), 1 câu MOM (VD: quy trình xuất kho), 1 câu mơ hồ (VD: "hôm nay có gì mới"). Kiểm tra badge hiện "Đang tra cứu khối X" và câu trả lời trích đúng khối.

### Bước 4 — Đóng vé
10. Ghi SHA/size/mtime của file `tri_thuc\library.sqlite` cũ SAU khi làm (phải bằng TRƯỚC — chứng minh không động vào kho cũ).
11. Báo cáo `docs/phieu-viec/ket-qua/index-split-home.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT

- `domain_manifest.json`: `overall: DAT`, tổng chunk/document khớp kiểm kê, không document trùng khối.
- File kho `tri_thuc` cũ: SHA/size/mtime trước = sau.
- App với cờ bật: 3 câu thử mỗi câu tra đúng khối (badge hiển thị), câu mơ hồ ghi rõ đã chọn khối khả dĩ nhất.
- Rollback đã thử: tắt cờ → app về kho `tri_thuc` cũ, hỏi đáp bình thường.

## Kế hoạch rollback (khi có sự cố)

Tắt `AIOS_DOMAIN_ROUTING_ENABLED` (hoặc xóa biến) và restart app → retrieval tự dùng lại kho `tri_thuc` cũ. Ba file kho mới nằm riêng, xóa khi user duyệt.

## Không làm

- Không embed lại, không ingest thêm trong vé này.
- Không xóa/sửa file `tri_thuc\library.sqlite` cũ.
- Không merge `main`.
