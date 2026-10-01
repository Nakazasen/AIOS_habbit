# Vé: OPT-RAGV2-LEXICAL — khâu lexical 75–177s + sửa token cache bị vô hiệu giữa query

Lane: [VM] Muse code+test trên VM → [CTY] OMP verify trên KDTVN-PC0575 (CPU-only, index production).
Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (số đo verify OPT-RAGV2-PYLOOPS, vòng 2 cache ấm, 2026-10-01 +07)
- L1 266s, L2 ~426s, L3 297s, E1 455s, E2 405s, E3 303s.
- Kết quả vòng 2 (`opt_ragv2_verify_new.json` trên PC0575) = **baseline** của vé này.
- Dense/sparse khi ấm: ~0,3–1,5s (E1: dense 0,5s / sparse 0,3s) — numpy + preload đã phát huy tối đa.
- Lexical: 75–177s/câu — **nút thắt duy nhất còn lại**.
- Phát hiện chặn (micro-probe OMP đã chứng minh): câu non-CJK đi nhánh FTS, ghi ~120k dòng vào bảng tạm
  `rag_v2_eligible_chunks` trên cùng connection → `total_changes` nhảy → token cache
  `(data_version, total_changes)` đổi → dense/sparse tưởng DB đổi → nạp lại ma trận 100+s
  (`load_ms` 106–162s ở L1–L3) ngay trong chính query đó. E1 (câu CJK duy nhất, nhánh
  `deterministic_scan` không ghi temp) giữ nguyên cache.

## Phase A — sửa token cache (spec chính xác, làm trước)
1. `src/aios_habit/rag_v2/index.py::_index_cache_token()` (~dòng 1932): **bỏ `total_changes` khỏi token,
   chỉ giữ `PRAGMA data_version`** — token chỉ invalidate khi file DB đổi thật.
2. Điều kiện an toàn (probe 30s trên PC0575 trước khi chấp nhận): ghi bảng TEMP không làm
   `data_version` của main nhảy. Ghi rõ giả định vào comment: worker không bao giờ ghi bảng
   embedding giữa query (mọi merge đều restart app).
3. Test hồi quy: seed cache → ghi bảng TEMP trên cùng connection → assert
   `_dense_matrix_cache_for` / `_sparse_vector_cache_for` trả về đúng object cũ, không gọi loader.
4. Hiệu quả kỳ vọng: câu ấm bỏ 100–260s nạp lại ma trận (số đo preload: dense 114–248s, sparse 102–141s).

## Phase B — tối ưu lexical (đo trước, đoán sau)
1. Profile: tách thời gian lexical thành 3 phần — (a) build bảng tạm (DELETE + INSERT ~120k dòng),
   (b) `chunks_fts MATCH` + bm25 + JOIN, (c) vòng Python `_score_candidate`/tokenize.
2. Tối ưu theo số đo, không đoán:
   - (a) nặng → thay temp table bằng subquery/CTE eligibility ngay trong MATCH, hoặc gom INSERT 1 transaction;
   - (b) nặng → xem lại thứ tự JOIN / cách dùng bm25;
   - (c) nặng → vectorize/batch scoring, cắt top-k sớm.
   - Nhánh CJK (`_cjk_like_prefilter_rows`, LIKE quét ~120k chunk): đánh giá `chunks_fts MATCH`
     hoặc cấu trúc index phù hợp — **giữ nguyên top-15**, đặc biệt câu E1.
3. Kill-switch `AIOS_RAGV2_LEXICAL_V2` (giữ đường cũ khi =0); default theo kết quả verify.

## Tiêu chí nghiệm thu (OMP verify trên PC0575)
1. Phase A: test mới đỗ; câu ấm không còn `load_ms` hàng trăm giây ở dense/sparse.
2. Phase B: chạy lại 6 câu — **top-15 khớp baseline 100%** (đặc biệt E1), citation/trace không thoái lui,
   lexical giảm có số đo (mục tiêu stretch: tổng <60s/câu).
3. Full suite không regression mới so với nền.
4. E1 (chữ Nhật/Hàn): nếu top-15 lệch → đặt kill-switch về 0, không đóng vé.
