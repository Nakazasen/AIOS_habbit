# Báo cáo Phase A [VM] — công cụ tách index production thành 3 khối lĩnh vực

- Ngày: 2026-10-03. Nhánh: `phieu-viec/rag-fix1`. Không merge `main`, không force-push.
- User chốt: tách toàn bộ thành 3 khối (LSU / Điều-tra-lỗi / MOM), không giữ nguyên 1 index.
- Phase A (VM): code + test trên fixture. Phase B ([NHÀ]): OMP chạy tách thật trên kho production.

## 1. Đã code gì

**`src/aios_habit/index_domain.py` (mới)** — taxonomy 3 lĩnh vực + phân loại:
- Hằng: `DOMAIN_LSU="lsu"`, `DOMAIN_DIEU_TRA_LOI="dieu_tra_loi"`, `DOMAIN_MOM="mom"`; tên hiển thị tiếng Việt; collection id trùng domain id.
- `classify_document(source_name, source_path, text_sample, ledger_hint=None)` → `(domain, confidence 0-1, reason)`. Từ khóa có trọng số cho từng lĩnh vực (LSU: JIG/LSU/FinTest/SelNo/bowskew/laser scan…; Điều-tra-lỗi: KDTPS/mã Fxxx/hiện tượng/nguyên nhân/đối sách/4M/QCC…; MOM: MOM/Opcenter/MES/WMS/仕様書/RevUp/AGV…). Tên file/đường dẫn có trọng số gấp 3 lần nội dung. Độ tin cậy = điểm thắng / (điểm thắng + điểm nhì + 1).
- Mọi tài liệu vào đúng 1 khối, không bỏ sót: tài liệu không có tín hiệu từ khóa được gán minh bạch vào khối Điều-tra-lỗi với confidence 0.0 (lý do: sứ mệnh cốt lõi của AIOS_habbit là hệ thống điều tra lỗi Bước 0–5), manifest ghi rõ để người rà soát.
- `lookup_ledger_hint(db_path, document_id)`: tra bảng `source_preparation_ledger` nếu tồn tại (không bao giờ raise; thiếu bảng/DB chỉ mất một tín hiệu).
- `detect_domain_from_question(question)`: nhận diện lĩnh vực câu hỏi; câu không rõ lĩnh vực vẫn trả về khối khả dĩ nhất kèm reason "câu hỏi không rõ lĩnh vực".
- `select_domain_collection(...)`: quyết định kho cần tra cứu — chỉ dùng kho lĩnh vực khi (1) cờ `AIOS_DOMAIN_ROUTING_ENABLED=1`, (2) câu hỏi vốn tra cứu kho `tri_thuc` cũ, (3) kho lĩnh vực đã tồn tại. Ngược lại giữ nguyên kho cũ và ghi rõ lý do.

**`src/aios_habit/split_index_by_domain.py` (mới)** — CLI tách kho:
- Mở nguồn read-only (`mode=ro` + `PRAGMA query_only=ON`), `integrity_check` trước khi làm.
- Phân loại từng document (mẫu 3 chunk đầu, tối đa 6000 ký tự), copy `chunks` + `chunk_embeddings` + `chunk_sparse_embeddings` + `chunk_multivector_embeddings` (+ `source_preparation_ledger` nếu có) đã lọc theo `document_id` sang `collections/lsu|dieu_tra_loi|mom/library.sqlite`. KHÔNG embed lại — vector copy nguyên (fingerprint `016c5255…` giữ nguyên).
- Bảng FTS5 được dựng lại tự động bởi trigger khi insert chunk (đã kiểm chứng đếm khớp).
- Tự verify: tổng chunk 3 khối = tổng nguồn; không document nào ở 2 khối; mỗi chunk giữ nguyên số dòng vector dense/sparse/multivector như nguồn.
- Xuất `domain_manifest.json` (document_id → domain, confidence, reason + báo cáo verify).
- `--dry-run`: chỉ in phân bố + danh sách confidence thấp, không ghi file.
- Chốt an toàn: từ chối chạy khi `--source` trỏ vào kho production nếu thiếu `--allow-production`; từ chối ghi đè kho đích nếu thiếu `--overwrite`.

**Router trong đường `retrieve_workspace_chat_evidence`** (`workspace_chat_rag_v2_adapter.py`):
- `_select_domain_route()`: nhận diện lĩnh vực từ câu hỏi, chọn collection tương ứng; tắt mặc định (cờ `AIOS_DOMAIN_ROUTING_ENABLED`, mặc định `"0"`).
- `_run_profile()` nhận thêm `domain_collection_id`; chỉ override khi route `applied=True`.
- Mọi kết quả trả về đều kèm `domain_routing` (domain, tên hiển thị, confidence, reason, cờ ambiguous, collection đã dùng, ghi chú).

**Hiển thị trên chat** (`workspace_chat_app.py`): dòng badge "Đang tra cứu khối X."; câu hỏi mơ hồ thêm "(Câu hỏi chưa rõ lĩnh vực — đã chọn khối khả dĩ nhất.)". Không tìm trộm khối khác: khi route không áp dụng thì không hiện dòng này.

**Ingest sau này** (`rag_v2/index.py`): cột mới `chunks.domain` (nullable — dòng cũ vẫn hợp lệ, không vỡ test cũ); `_upsert_rows` gắn nhãn bằng `classify_document` từ `source_name`/`source_path` + mẫu text của chunk; nạp lại thì nhãn được tính lại theo nội dung mới.

## 2. Test

- `tests/test_index_domain.py` (20 test): phân loại đúng mỗi lĩnh vực, ca mơ hồ → fallback minh bạch confidence 0, biên độ tin cậy khi tín hiệu lẫn, detect câu hỏi 3 lĩnh vực + câu mơ hồ, cờ bật/tắt, 4 nhánh `select_domain_collection`, tra ledger (có/không bảng/không DB), gắn nhãn lúc ingest qua `LocalChunkIndex` + nạp lại cập nhật nhãn.
- `tests/test_split_index_by_domain.py` (6 test): `--dry-run` không ghi file; tách thật trên fixture (đếm khớp, không trùng document, vector đủ, FTS dựng lại, manifest `DAT`); chốt production; chốt ghi đè; manifest liệt kê tài liệu confidence thấp.
- Tổng: **26 test mới pass**; `tests/test_rag_v2_index.py` (38 test cũ) vẫn pass — cột `domain` không vỡ ingest cũ.
- `python -m compileall src tests`: OK. `python -m aios_habit.cli audit`: `{"status": "PASS"}`. `import aios_habit.workspace_chat_app`: OK.
- Hồi quy có chọn lọc (những test chạy được trên VM): `test_workspace_chat_rag_v2_adapter` + `test_workspace_chat_store` + `test_line_log_parser` (135 test) pass; `test_workspace_chat_source_ingest` pass.
- Full suite `pytest -q` trên VM: **không chạy sạch được do thiếu dependency nhóm dev** (`nakazasen_ai_router`…) — VM không có `uv`/nhóm dev theo quy ước repo. So sánh base (7824379, chưa có code mới) với nhánh có code mới: cùng **46 failed** (tập fail trùng hệt nhau, đều do thiếu dependency/môi trường), không có fail mới nào do thay đổi này gây ra. Toàn bộ 26 test mới pass trong full run.

## 3. OMP cần làm ở Phase B (vé `prompt-queue-index-split-home.md`)

1. Backup kho production + `integrity_check` (ghi SHA/size/mtime trước–sau).
2. Chạy `--dry-run` trên kho thật, báo phân bố 3 khối + danh sách confidence thấp để user rà.
3. Chạy tách thật ra 3 collection mới (không ghi vào file `tri_thuc` cũ).
4. Verify: đọc `domain_manifest.json` (`overall: DAT`), đối chiếu tổng chunk/document với kiểm kê (149.800 chunk / 889 document).
5. Đăng ký 3 collection mới vào app (storage_root), bật `AIOS_DOMAIN_ROUTING_ENABLED=1`, hỏi đáp thử mỗi khối (LSU / Điều-tra-lỗi / MOM) + 1 câu mơ hồ, kiểm tra badge "Đang tra cứu khối X".
6. Rollback: tắt cờ → app tự về kho `tri_thuc` cũ (file cũ không bị động đến trong cả quá trình).

## 4. Rủi ro đã biết

- 496 document lõi canary mất dấu thư mục gốc: phân loại 100% bằng từ khóa nội dung; tài liệu ít chữ/không tín hiệu sẽ rơi vào fallback (confidence 0) — cần người rà danh sách này ở Phase B trước khi coi là xong.
- Từ khóa "lỗi"/"jig" có thể gây lẫn giữa khối LSU và Điều-tra-lỗi ở tài liệu biên (VD: điều tra lỗi của jig). Cơ chế margin + confidence thấp đã ghi nhận trường hợp này trong manifest để rà tay.

## 5. Phase A2 — sửa classifier sau dry-run (2026-10-03 ~21:30 +07)

Dry-run trên máy nhà: 453/889 document confidence < 0,40 (451 bằng 0) bị gán mặc định vào Điều-tra-lỗi. Nguyên nhân: taxonomy từ khóa bỏ sót từ vựng thật trong kho (tiền tố `KTD-`, thuật ngữ Nhật về lỗi, số part Kyocera...). File `index-split-lowconf-453-names.txt` (372 tên duy nhất) được dùng làm fixture hồi quy.

Thay đổi:
- `index_domain.py`: thêm ~30 rule — `KTD-` (0.9), mã lỗi `Cxxxx`/`JAM`/`Error\d*`/`エラー`, `DRBFM`, `自己診断`/`不具合`/`異常`, `エラーコード`, `調査報告`/`调查报告`, `maintenance mode`, `NG`, `回路図`/`配線図`/`ブロック図`/`ASSY`/số part (`30x…`, `3V2…`, `7PA…`), `治具`/`tape`/`mirror`/`log` → LSU. `tổng hợp`/`matome` cố tình KHÔNG gán theo tên — đi đường nội dung/centroid.
- `split_index_by_domain.py`: fallback centroid bằng vector dense sẵn có (không embed lại) — centroid mỗi lĩnh vực từ document confidence ≥ 0,7; document < 0,4 được gán centroid gần nhất khi margin > 0, confidence = min(0,85, margin×4). Không có bảng vector → giữ nguyên manifest.
- Sửa bug: `--dry-run` không còn đòi `--allow-production` (dry-run chỉ đọc).
- Kết quả trên fixture 372 tên: 75,8% đạt confidence ≥ 0,4 bằng tên; 212/212 tên có nhãn kỳ vọng phân loại đúng; ~90 tên còn lại (wsc-*.txt, tổng hợp...) đi đường nội dung/centroid trên máy nhà.
- Test mới: 15 test rule trong `test_index_domain.py`, `test_index_domain_fixture_names.py` (3 test), 4 test centroid/guard trong `test_split_index_by_domain.py`. Tổng 47 test pass; `test_rag_v2_index.py` 36 pass; `compileall` OK; `cli audit` PASS; tương thích Python 3.11 (AST feature_version).
