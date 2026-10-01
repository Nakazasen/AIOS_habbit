# Báo cáo vé `OPT-LEXICAL-BENCH-NHA` — bench Phase B lexical trên index thật máy nhà

Máy: `h410asrock` (máy nhà). Nhánh: `phieu-viec/rag-fix1`. Thời điểm: phiên 2026-10-02 04:48 +07 → ~05:20 +07 (bench + toggle + hybrid + kiểm SHA sau). Vé: `docs/phieu-viec/mailbox/prompt.md` (bản phát hành `OPT-LEXICAL-BENCH-NHA`, commit `c96287e`; mã Phase B `be4845c` + `1f30092`). Không đụng `main`, không force-push, **không ghi index**, không ghi ổ D, không restart app, không đụng gói dùng thử J3.

## 1. Kết luận

**Đủ 4 việc của vé** trên index thật 149.800 chunk, chỉ đọc, kênh lexical đúng chuỗi truy xuất đã dùng ở vé `hodap-home`:

1. **Parity top-15 A≡B 100%** — cả 6 câu khớp hoàn toàn (id + thứ tự + điểm) trên kênh lexical (chuỗi `hodap-home`) **và** trên smoke stack đầy đủ (L1 + E1, có dense/sparse/fuse); tính toàn bộ lượt đảo thứ tự + mọi toggle + hybrid: **50/50 record, 0 lệch**.
2. **Tốc độ**: B (`AIOS_RAGV2_LEXICAL_V2=1`, default) nhanh hơn A **−1,15…−1,34 s/câu (−24%…−33%)** trên 5 câu thường — nhờ `NARROW_ELIGIBILITY` (bước eligibility 2,24 → 1,10 s; temp-build/FTS/python-score không đổi).
3. **Câu chữ Nhật/CJK (E1): B CHẬM hơn A +1,0…+1,4 s (+9%)** — thủ phạm là **`SCORE_CACHE`**: +1,5 s ở vòng Python scoring trên ~23,8k ứng viên LIKE (kế hoạch 1 biến thể → cache không có gì để tái dùng, chỉ còn chi phí lưu/GC). Tắt `SCORE_CACHE`: E1 wall 16,4 → **14,7 s / 14,6 s** (nhanh hơn cả A ~0,6 s, vì vẫn giữ `NARROW_ELIGIBILITY`). Đo lại trên stack đầy đủ xác nhận cùng chiều: L1 hybrid B −1,28 s (−21%), E1 hybrid B +1,0…+1,2 s.
4. `SKIP_FULL_ELIGIBLE` **không kích hoạt** trên kho này (`eligible_complete=false`: 373 mảnh nhãn rỗng bị lọc) → chưa đo được; `CJK_TRIGRAM` **bỏ qua** vì `chunks_fts_trigram` chưa tồn tại (vé cấm tự build) — ghi nhận đúng yêu cầu.

**Khuyến nghị cho bước verify PC0575:** giữ `AIOS_RAGV2_LEXICAL_V2=1` với `NARROW_ELIGIBILITY` (và các toggle trung tính); **cân nhắc đặt `AIOS_RAGV2_LEX_V2_SCORE_CACHE=0`** — ít nhất cho bộ câu có CJK — cho tới khi Muse xem lại chi phí cache trên đường CJK một-biến-thể; `SKIP_FULL_ELIGIBLE`/`CJK_TRIGRAM` để mặc định (vô hại, chưa có số trên kho thật).

## 2. Cổng gate

- Watcher tự mở OMP **`LAUNCH 1/4`** lúc `2026-10-02 04:48:21` (`launchStallCount=1`, `D:\Sandbox\Vong_lap_giao_viec\watcher.log`).
- **Điều kiện mở ĐÃ TỚI**: vé [NHÀ] phát hành sau khi Phase B code+test xong trên VM — sau `git pull` thấy đủ `be4845c` (B1 instrumentation) + `1f30092` (B2 tối ưu sau kill-switch) → nhận vé bình thường, **không** dùng nhánh "4 lần watcher"/`cho-muse`, không quay no-op.

## 3. Định danh kho

| Thuộc tính | Trước bench | Sau bench |
| --- | --- | --- |
| Đường dẫn (app resolve, chỉ đọc) | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | (cùng file) |
| Dung lượng | **2.942.201.856 B** | **2.942.201.856 B** (khớp) |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` (khớp ghim `merge-home`) | **`45eb0e07…65b7c0` — khớp từng byte** |
| mtime | 2026-10-01 08:27:27 (ổn định trong lúc băm) | **2026-10-01 08:27:27** (không đổi) |
| Toàn vẹn | `PRAGMA quick_check` = `ok` | SHA/mtime/size không đổi ⇒ nguyên trạng (mọi truy cập `mode=ro`) |
| Nội dung | 149.800 chunk / **121.331 retrievable** / 889 tài liệu; dense = sparse 121.671 · FTS 121.331 · multivector 0 | — |
| `chunks_fts_trigram` | **không tồn tại** → bỏ qua toggle `CJK_TRIGRAM`, không build (đúng ràng buộc vé) | — |

App LAN trong suốt phiên: `/_stcore/health` = `ok`, `localhost:8501` → HTTP 200 — **không restart** (đúng ràng buộc vé). Khi chạy search mỗi lượt (cả A lẫn B): 121.331 hàng retrievable, **120.958 hợp lệ** (373 mảnh bị lọc nhãn riêng tư — nhãn rỗng nằm ngoài allowlist app) → `eligible_complete=false` nên nhánh `SKIP_FULL_ELIGIBLE` không mở.

## 4. Phương pháp (chỉ đọc, đúng chuỗi đã dùng ở vé `hodap-home`)

1. `WorkspaceChatRagV2CanaryConfig.from_env()` → manifest → `_pipeline_config("bge_m3_hybrid", read_only=True, include_reranker=False, collection_id="tri_thuc")` → `RagV2DevPipeline` (BGE-M3 ONNX fp32, `device=cpu` như app đang chạy).
2. `LocalChunkIndex.search_with_summary(coerce_query_plan(câu), limit=15, options)` — `candidate_limit=pc.candidate_limit` (100), `per_document_limit=3`, phạm vi toàn kho `tri_thuc`, không lọc `document_id`.
3. Env như launcher app máy nhà: `AIOS_RAG_V2_NUMPY_DENSE=1`, `AIOS_BGE_QUERY_TIMEOUT=1200`.
4. Cấu hình: **A** = `AIOS_RAGV2_LEXICAL_V2=0` (đường cũ); **B** = `AIOS_RAGV2_LEXICAL_V2=1` (default các toggle con); toggle-off = `AIOS_RAGV2_LEX_V2_<TÊN>=0`. Kill-switch đọc lại mỗi lần search nên A/B/toggle chạy trong cùng tiến trình, cùng kết nối SQLite, cùng cache — khác biệt chỉ ở nhánh mã.
5. Đo: wall time kênh lexical + `SearchSummary.lexical_breakdown_ms` (instrumentation B1): `eligibility_ms` (a: lọc + dựng bảng tạm), `temp_build_ms`/`fts_match_ms` (b: MATCH + bm25 + JOIN), `python_score_ms` (c: vòng scoring); `like_prefilter_ms` cho đường CJK. Parity = danh sách `(chunk_id, điểm)` top-15.
6. Mỗi tiến trình có **1 lượt warmup** (không ghi nhận) + **luân phiên thứ tự A/B** (ab/ba) + lặp; script `C:/tmp/opt-lexical-bench-nha/bench.py`, kết quả thô `C:/tmp/opt-lexical-bench-nha/{identity,sha-after}.json + bench.jsonl` (ngoài git, không chứa nội dung tài liệu).

## 5. Kết quả A/B 6 câu (kênh lexical)

### 5.1. Bảng tổng hợp (giây; SQLite ấm + warmup)

| Câu | A wall | B wall | Δ | Δ% | elig A→B | temp A→B | fts A→B | py A→B | ret |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 3,94 | **2,64** | −1,30 | −33,0% | 2236→1105 | 1028→1006 | 412→422 | 40→45 | 15/15 |
| L2 | 4,54 | **3,26** | −1,28 | −28,2% | 2229→1116 | 1026→1002 | 1022→1037 | 48→52 | 15/15 |
| L3 | 4,68 | **3,34** | −1,34 | −28,6% | 2265→1096 | 1081→1018 | 1071→1123 | 49→51 | 15/15 |
| E1 | **15,24** | 16,62 | **+1,38** | **+9,1%** | 2279→1100 | — | — | **10535→12171** | 6/6 |
| E2 | 4,76 | **3,61** | −1,15 | −24,2% | 2243→1178 | 1095→1061 | 1158→1224 | 45→45 | 13/13 |
| E3 | 4,80 | **3,49** | −1,31 | −27,3% | 2267→1188 | 1115→1057 | 1153→1143 | 45→45 | 15/15 |

Ghi chú: E1 đi nhánh CJK (`deterministic_scan` + `like_prefilter_ms` ≈ 1,9–2,1 s mỗi cấu hình, 23.836 ứng viên được scoring); 5 câu còn lại đi `fts5_bm25` (100 ứng viên). E1 trả 6 kết quả (cổng phủ từ khóa cắt, như baseline `hodap-home`).

### 5.2. Lặp xác nhận

| Phép đo | A | B | Kết luận |
| --- | ---: | ---: | --- |
| E1 lần 1 (ab) | 15,24 (py 10.535) | 16,62 (py 12.171) | B chậm |
| E1 lần 2 (ba — B chạy trước) | 15,35 (py 10.566) | 16,30 (py 12.026) | B chậm (không phải artifact thứ tự) |
| E1 lần 3 (ab) | 15,13 (py 10.566) | 16,49 (py 12.210) | B chậm |
| L2 đảo thứ tự (ba) | 4,57 | **3,21** | B nhanh hơn 1,36 s |

### 5.3. Parity

- A≡B: **6/6 câu** khớp hoàn toàn id + thứ tự + điểm (E1: 6/6 mục; E2: 13/13).
- Toàn bộ **50/50 record** trong `bench.jsonl` (mọi cấu hình + mọi toggle-off + các lượt hybrid) khớp mốc A từng câu theo từng đường — `bench.py parity` → `PARITY: ALL OK`.

## 6. Matrix toggle (E1 — câu CJK, nơi có chênh lệch)

| Cấu hình | wall (s) | Δ so B-default | py scoring (ms) | Ghi chú |
| --- | ---: | ---: | ---: | --- |
| B-default | 16,37 | — | 11.974 | |
| B-TEMP_TXN=0 | 16,16 | −0,21 | 11.667 | nhiễu |
| B-SKIP_FULL_ELIGIBLE=0 | 16,49 | +0,12 | 11.965 | vốn không kích hoạt |
| **B-NARROW_ELIGIBILITY=0** | 17,76 | **+1,39** | 11.876 | xác nhận toggle ăn tiền |
| B-PRIVACY_LAZY=0 | 16,49 | +0,12 | 11.891 | không kích hoạt (có lọc nhãn) |
| B-SCORE_HOIST=0 | 16,45 | +0,08 | 11.957 | nhiễu |
| **B-SCORE_CACHE=0** | **14,73** | **−1,64** | **10.522** | lần lặp: 16,06→**14,57** (py 11.664→10.330) |
| B-repeat (kiểm trôi) | 16,32 | −0,05 | 11.964 | nhiễu ±0,2 s |

**Kết luận toggle:** `NARROW_ELIGIBILITY` = khoản lời chính (≈1,1–1,4 s/câu). `SCORE_CACHE` = **âm trên đường CJK** khi kế hoạch chỉ có 1 biến thể: bundle từng hàng bị lưu cho toàn bộ 23.836 ứng viên nhưng không có lượt dùng lại nào → chỉ còn chi phí. Ở chế độ mở rộng nhiều biến thể (app có expansion), cache có thể hoàn vốn — cần đo lại nếu verify PC0575 chạy nhiều biến thể.

## 7. Smoke stack đầy đủ (`hybrid_search_with_summary` — lexical + dense + sparse + fuse)

Chạy thêm 2 câu (L1 — đường FTS; E1 — đường CJK): warmup + lặp lấy số ổn định (lượt đo đầu ở lần smoke trước từng bị lệch do trang cache bị đẩy sau khi nạp ma trận dense ~500 MB; các lượt lặp trong bảng đã ổn định).

| Câu | Cấu hình | wall (s) | kênh lexical (ms) | dense (ms) | sparse (ms) | ret | parity |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| L1 | A (`V2=0`) | 6,02 / 6,10 / 6,14 | 3.858 / 3.944 / 4.008 | ~430 | ~225 | 17 | khớp |
| L1 | B (`V2=1`) | **4,78 / 4,83 / 4,85** | **2.694 / 2.698 / 2.734** | ~420 | ~225 | 17 | khớp |
| E1 | A (`V2=0`) | **17,24 / 17,62** | 15.069 / 15.464 | ~440 | ~285 | 15 | khớp |
| E1 | B (`V2=1`) | 18,42 / 18,46 | 16.253 / 16.213 | ~435 | ~285 | 15 | khớp |

- L1: **B nhanh hơn ~1,28 s (−21%)** — cùng xu hướng kênh lexical; dense/sparse không đổi giữa A/B (đúng thiết kế — Phase B chỉ chạm kênh lexical).
- E1: **B chậm hơn ~1,0–1,2 s (+6–7%)** — tái hiện đúng hành vi `SCORE_CACHE` đo trên kênh lexical; các kênh khác không đổi.
- Parity top-15 **fused** A≡B cả 2 câu (khớp id + thứ tự + điểm) → parity tầng lexical lan truyền đúng lên kết quả cuối; lưu ý hybrid trả **15 kết quả** ở E1 (dense/sparse phủ thêm) còn kênh lexical đơn thuần chỉ 6 — parity vẫn tuyệt đối trong từng đường.

## 8. Ràng buộc giữ

- Kho **không đổi một byte**: SHA-256 `45eb0e07…65b7c0`, dung lượng 2.942.201.856 B, mtime `2026-10-01 08:27:27` **khớp trước↔sau** toàn bộ phiên; mọi truy cập mở `mode=ro`.
- Không restart app; không đổi hành vi app đang chạy (kill-switch mặc định vẫn 0 trong môi trường app — chỉ set trong tiến trình bench).
- Không tự build `chunks_fts_trigram`; không đụng `main`/ổ D/gói J3/JIG.
- Mọi lệnh trong vé đều chạy trên máy nhà; báo cáo không chứa nguyên văn nội dung tài liệu (`local_only`).

## 9. Hạn chế

- Số tuyệt đối nhỏ hơn lượt chạy app thật vì SQLite/OS cache đã ấm (warmup); mục tiêu là **so sánh tương đối A/B** — cả hai cấu hình chịu cùng điều kiện.
- Bench đo **kênh lexical** (đúng chuỗi `hodap-home`); kế hoạch 1 biến thể. Đường app mở rộng nhiều biến thể có thể khác — đặc biệt với `SCORE_CACHE` (có tái dùng giữa biến thể).
- Máy vẫn phục vụ app LAN song song; nhiễu đo ±0,2 s (xem dòng B-repeat). E1 chỉ so trên 6 kết quả cuối (cổng phủ từ khóa).
- E1 là câu duy nhất có ký tự CJK trong bộ 6 câu — phát hiện `SCORE_CACHE` mới có 1 mẫu; đề nghị Muse xác nhận trên PC0575 trước khi chốt.

## 10. Tái lập

```powershell
cd D:\Sandbox\AIOS_habbit
uv run --no-sync --group dev python C:/tmp/opt-lexical-bench-nha/bench.py identity
uv run --no-sync --group dev python C:/tmp/opt-lexical-bench-nha/bench.py pair --start 1 --end 6 --order ab --warmup
uv run --no-sync --group dev python C:/tmp/opt-lexical-bench-nha/bench.py matrix --start 4 --end 4 --warmup
uv run --no-sync --group dev python C:/tmp/opt-lexical-bench-nha/bench.py parity
uv run --no-sync --group dev python C:/tmp/opt-lexical-bench-nha/bench.py sha
```

Trạng thái cuối: **chờ Muse review** — mailbox `docs/phieu-viec/mailbox/trang-thai.md` chuyển `xong-cho-duyet`; Muse review xong sẽ phát hành lại vé `J3` (giữ nguyên chờ lane [NGƯỜI DÙNG]).
