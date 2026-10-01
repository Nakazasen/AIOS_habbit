# Vé OPT-RAGV2-PYLOOPS — Tối ưu 3 vòng lặp Python trong RAG v2 (lexical / dense / sparse)

LANE: [VM] — Muse code+test trên VM; OMP verify số đo trên PC0575 CPU-only khi Muse báo code xong + commit rõ ràng. Trong lúc code trên VM, app LAN PC0575 vẫn chạy bình thường (không đụng production PC0575).

## Bối cảnh

Vé `hodap-lsu-loi` kẹt ở cổng "tra cứu < 1 phút". Số đo thật của OMP trên PC0575
(CPU-only, index production `tri_thuc`, ~108k chunk retrievable), probe chỉ-đọc
`scratch/hodap_stage_timing.py`, ghi chú 2026-10-01 10:06 +07 trong
`docs/phieu-viec/mailbox-pc0575/trang-thai.md`:

- `pipeline.query` (query lạnh, worker vừa restart): **266,8s**
  - lexical `search_with_summary`: **81,2s**
  - `dense_candidates` (numpy đã bật): **69,2s** — trong đó nạp ma trận
    float32 108.007×1024 (~442MB) lần đầu hết **92,3s**, riêng xếp hạng chỉ **0,28s**
  - `sparse_candidates`: **115,4s** (đắt nhất)
- Fix CROSS JOIN trước đây chỉ sửa cổng coverage (readiness), không đụng 3 vòng này.
  Bật `AIOS_RAG_V2_NUMPY_DENSE=1` chỉ đưa dense từ "vài phút" về "0,28s khi cache ấm"
  — query lạnh đầu tiên vẫn gánh 92,3s nạp ma trận.

Ba vòng lặp nằm trong `src/aios_habit/rag_v2/index.py` (branch
`phieu-viec/rag-fix1`), `hybrid_search_with_summary` luôn chạy cả 3 kênh mỗi câu hỏi:

**Vòng 1 — lexical, `search_with_summary` (dòng 3040), đo 81,2s:**
- Dòng 3060–3062: `fetchall("SELECT * FROM chunks WHERE retrievable = 1")` — kéo
  ~108k dòng kèm text về Python, rồi vòng lặp lọc `eligible_rows`.
- Mỗi query variant (tối đa 8, `query_planning.py:86`): `_candidate_rows` (dòng 3464).
  Query chứa CJK (câu hỏi tiếng Nhật L1–L3) rơi vào dòng 3482–3483:
  `return list(eligible_rows), "deterministic_scan"` — bypass FTS5 vì tokenizer
  `unicode61` của `chunks_fts` không tách được CJK (comment dòng 3478–3481).
- Sau đó `_score_candidate` (dòng 3652) chạy trên TỪNG dòng × TỪNG variant:
  tokenize toàn văn + `Counter` + `json.loads` + kiểm tra substring CJK.

**Vòng 2 — dense, `dense_candidates` (dòng 2178) → `_dense_candidates_numpy` (dòng 2020), đo 69,2s:**
- `_load_dense_matrix_cache` (dòng 1884): SQL fetchall 108k vector blob, rồi vòng lặp
  Python `for index, row in enumerate(kept)` copy từng blob vào ma trận numpy.
- Cache ấm qua `_dense_matrix_cache_for` (dòng 1944), token =
  (`PRAGMA data_version`, `total_changes`) (dòng 1879–1881). Worker BGE là tiến trình
  thường trực (vòng lặp stdin, `bge_subprocess_worker.py:219`) nên query 2+ dùng
  cache — nhưng query lạnh đầu tiên sau mỗi restart vẫn trả 92,3s trong timeout.

**Vòng 3 — sparse, `sparse_candidates` (dòng 2697), đo 115,4s:**
- Dòng 2718–2726: fetchall `SELECT c.*, s.sparse_json ...` 108k dòng.
- Vòng lặp sau đó: `json.loads(sparse_json)` + `normalize_sparse_vector` cho từng dòng,
  rồi mỗi variant chấm `sparse_dot_similarity` (`semantic.py:324`) Python thuần × 108k.

## Việc cần làm (theo thứ tự — làm xong từng bước, đo rồi mới sang bước tiếp)

1. **[V2-A] Preload ma trận dense lúc worker init — chắc ăn nhất, ngữ nghĩa 0 đổi.**
   Trong nhánh `init` của `bge_subprocess_worker.py` (sau khi pipeline mở index),
   gọi `_dense_matrix_cache_for(fingerprint, dimension)` một lần, log thời gian nạp.
   Query lạnh đầu tiên không còn gánh 92,3s trong timeout truy vấn. Không đổi đường
   xếp hạng (`_numpy_rank_variant` + tie-band exact-rescore giữ nguyên).

2. **[V1-A2] Prefilter bằng SQL LIKE cho query CJK trong `_candidate_rows` — recall không đổi.**
   Trước nhánh `deterministic_scan` (dòng 3482): chạy
   `SELECT chunk_id FROM chunks WHERE retrievable = 1 AND normalized_text LIKE '%term%'`
   (escape `%`/`_`/`\`, dùng 1–2 term dài nhất của variant) để lấy tập ứng viên, chỉ
   gọi `_score_candidate` trên tập này thay vì 108k dòng. Cơ sở giữ ngữ nghĩa:
   `LIKE '%term%'` là superset của điều kiện match hiện tại (`term in normalized_text`
   với CJK), và `_score_candidate` vẫn là người chấm điểm cuối cùng nên thứ tự cuối
   không đổi. Đường FTS5 cho non-CJK giữ nguyên.

3. **[V3-A] Cache sparse đã parse + inverted index trong worker — toán học y hệt.**
   Parse `sparse_json` 1 lần lúc worker init (hoặc lazy lần đầu rồi cache theo token
   như dense cache, dòng 1944); dựng inverted index `term → posting list`.
   Mỗi variant chỉ chấm dot trên docs chứa ≥1 query term — dot với term vắng mặt
   bằng 0 nên kết quả y hệt full scan. **Đo memory trên VM trước khi chốt**
   (108k dict Python có thể nặng); nếu vượt ngân sách thì báo số thật và dừng ở
   cache-parse (bỏ inverted index), không cố.

4. **[V3-B] (TÙY CHỌN, RỦI RO ĐỔI KẾT QUẢ — chỉ làm khi 3 bước trên chưa đạt <60s)**
   Cắt pool sparse bằng union top-(candidate_limit×20) của dense+lexical trước khi
   chấm sparse. BẮT BUỘC: sau feature-flag mặc định TẮT + đo độ lệch top-100 sparse
   trên 6 câu mẫu L1–L3/E1–E3; lệch thì bỏ, không ép.

5. **Đo và báo cáo 2 rủi ro (không cần sửa ngay):**
   - App PC0575 có ghi vào `library.sqlite` trong lúc query không? Nếu có,
     `PRAGMA data_version` đổi → dense cache invalidate giữa chừng → query đột nhiên
     chậm lại ~92s. Ghi nhận bằng chứng, đề xuất sau.
   - Throughput đọc blob SQLite (~4,8MB/s theo số đo 92,3s/442MB) — kiểm tra
     `PRAGMA cache_size`/`page_size` của connection worker có bất thường không.

## KHÔNG làm

- Không rebuild / không đổi tokenizer `chunks_fts` trên production (hướng FTS5-trigram
  cho CJK chỉ là dự phòng, cần vé riêng).
- Không đổi công thức RRF/fusion, trọng số kênh, `candidate_limit`, ngưỡng cắt top-K.
- Không nhúng lại vector, không ghi index production, không đụng ổ D máy nhà.
- Không bật V3-B (prefilter đổi kết quả) nếu chưa có flag mặc định tắt + số đo lệch
  được duyệt.
- Không merge `main`, không force-push. Commit riêng trên `phieu-viec/rag-fix1`.

## Tiêu chí ĐẠT

- Bảng số đo trước/sau **từng kênh** (lexical / dense-lạnh / sparse, đơn vị giây,
  1 chữ số thập phân) trên PC0575 CPU-only, cùng index production `tri_thuc`,
  bằng cùng phương pháp probe chỉ-đọc của OMP. Ghi rõ số query lạnh (worker vừa
  restart) và query ấm.
- Mục tiêu: query lạnh **<60s**. Nếu không đạt → báo số thật từng kênh, nêu rõ nút
  thắt còn lại, KHÔNG ép số, không "làm tròn cho qua".
- Kết quả retrieval không đổi ngữ nghĩa: so `top-15 chunk_id` của 6 câu L1–L3/E1–E3
  trước/sau trên cùng index — V2-A/V1-A2/V3-A yêu cầu trùng 100% (lệch do tie-break
  đã ghi nhận thì liệt kê rõ từng câu); V3-B (nếu làm) báo tỷ lệ lệch.
- Test mới cho từng tối ưu pass trên VM Linux Python 3.12; full suite không thoái lui
  so với nền (`pytest -q`).
- Mọi tối ưu đổi hành vi xếp hạng (chỉ V3-B) nằm sau feature-flag mặc định tắt.
- Báo cáo `docs/phieu-viec/ket-qua/opt-ragv2-pyloops.md` kèm bảng số đo + commit.
- OMP verify trên PC0575: chạy lại 6 câu L1–L3/E1–E3, đối chiếu thời gian + top-15
  với baseline, rồi mới đóng vé.
