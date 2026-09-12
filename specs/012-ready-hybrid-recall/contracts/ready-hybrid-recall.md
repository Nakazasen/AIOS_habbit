# Hợp đồng: ready hybrid recall

## Truy xuất nguồn ready

`_retrieval_source_window(question, ready_sources) -> sources`

- Không được trả về tập cắt 3 khi `query_corpus_script_mismatch(question, titles+text)` là true và `|ready_sources| > 3`.
- Phải trả về tập hẹp khi kho 2 nguồn, không đa số CJK, câu trùng từ khóa một nguồn (Matecon/manual).

## Ranking

`hybrid_ranking_for_texts(query, corpus_names) -> HybridRankingConfig`

- Lệch chữ: dense_weight > lexical_weight > 0
- Cùng họ: mặc định 1.0 / 1.0 / 1.0

## Cấm

Chuỗi `BQ0`, tên file `.xlsx` nhà máy, token nghiệp vụ cố định trong module `script_family` và nhánh ranking mới.
