# Vé V1 — Verify F1–F4 (schema error_cases + glossary mã lỗi + sổ chống trùng) trên Windows máy nhà

Ngày viết: 2026-09-28 (Muse). Chế độ: Muse code trên VM → OMP verify độc lập trên Windows (luật "không vừa đá vừa thổi còi").
Branch: `phieu-viec/rag-fix1`. Không đụng `main`. Hostname: `h410asrock` (Win 10 Pro).

## Bối cảnh

- Vé 0.3 ĐÃ DUYỆT (2026-09-28): migration GPU hoàn tất 99.003/99.003 khối trên index ổ C, `pending=0`, `integrity_check=ok`.
- Muse code trên VM (luôn nhẹ-CPU, test SQLite `:memory:`, KHÔNG embed):
  - F1 commit `179180a6d75e`: module `src/aios_habit/error_cases/` (schema.sql, column_map.py, store.py; ô xanh 146,208,80 không ghi đè).
  - F1 bổ sung commit `52d3e00`: HISTORY_29_MAP + normalize_history_row + dedup rộng `UNIQUE(no_dvd, machine_type, line)` theo file thật (29 cột).
  - F4 commit `3d1dfbf`: `glossary.py` + `glossary_schema.sql` — 4 họ mã: C_CALL 226 (JP+VN, chuẩn hóa full-width NFKC), F_SYSTEM 129 (JP+EN, giữ wildcard X), JAM 3115 unique (validate ký tự đầu mã = unit; trùng chéo sheet thì bản chính thắng), SCT_ADJ 37 (trùng ErrNo=03 giữ cả 2 qua code_sub). JAM còn tên tiếng Nhật chưa dịch — để batch dịch sau, không chặn vé này.
  - Vé 1 commit `e07ce45`: sổ file chống trùng `ingest_manifest.py` (sha256 + mtime_ns + size; skip khi vất lại file cũ; manifest hỏng → fail open).
- Trên VM (Linux, Python 3.12.3): `test_rag_v2_ingest_manifest.py` 6/6 passed; suite error_cases 26/26 passed (F1 15 + F4 11).

## Cấm kỵ (fail-closed)

- CHỈ đọc + chạy test. Cấm ghi index, cấm chạy batch embed/apply, cấm bất kỳ ingest thật nào.
- Cấm vĩnh viễn ghi ổ D (chỉ đọc cứu dữ liệu cũ khi cần).
- Không `git pull` tạo merge — dùng `git fetch` + `git reset --hard origin/phieu-viec/rag-fix1` (hoặc checkout commit rõ ràng). Không đụng `main`.

## Cách làm

1. `git fetch origin`; checkout đúng HEAD của `phieu-viec/rag-fix1`; GHI RÕ mã commit đã checkout (ít nhất 7 ký tự) vào trang-thai.md.
2. Dùng Python trên Windows (ghi rõ phiên bản, đề xuất 3.12): tạo venv mới, `pip install -e .` (hoặc `PYTHONPATH=src`), cài pytest.
3. Chạy: `pytest tests/test_rag_v2_ingest_manifest.py -q` → kỳ vọng 6/6 passed.
4. Chạy toàn bộ suite `error_cases`: `pytest tests/ -q -k error_cases` (hoặc đường dẫn test cụ thể) → kỳ vọng 26/26 passed; nếu tên test/thư mục khác, ghi rõ lệnh đã chạy.
5. Ghi vào báo cáo: mã commit checkout, OS + Python, số đỗ/trượt độc lập từng suite, bất kỳ fail/error nào (kèm traceback). Không sửa code để "cho qua" — fail thì báo nguyên vẹn.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_V1_verify-F1-F4-windows.md` gồm:
1. Commit checkout + ngày giờ, OS, Python.
2. Kết quả từng suite (6/6 manifest; 26/26 error_cases) với log tóm tắt.
3. Bất kỳ khác biệt nào so với kết quả trên VM (nếu có).

Tiêu chí ĐẠT: cả 3 suite pass 100% trên Windows, không ghi index, mọi thao tác trên branch riêng (không đụng main).

## Sau vé này

Vé V1 đạt → Muse phát hành Vé P1 "đóng dấu kho thử thành kho thật" (integrity → copy sang production → app đọc thử B1–B5). Không tự mở P1 trước verdict.
