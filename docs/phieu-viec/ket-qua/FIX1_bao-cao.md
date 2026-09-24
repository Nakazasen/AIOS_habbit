# FIX 1 — Báo cáo numpy-hoá dense search

## 1. Tóm tắt thay đổi

Sửa `src/aios_habit/rag_v2/index.py`. `dense_candidates` giữ nguyên chữ ký. Khi `AIOS_RAG_V2_NUMPY_DENSE` bật, index nạp một lần ma trận `float32` (N×d) của các vector đã chuẩn hoá, cache trong tiến trình, và chấm bằng `matrix @ qvec` rồi `argpartition`. Vòng cosine Python cũ không bị xoá và vẫn là đường mặc định.

Điểm trả ra được chấm lại bằng `cosine_similarity` của đường cũ cho các hàng sát ngưỡng và cho top-k cuối, để thứ tự và điểm khớp bit với đường Python. `pipeline.py` và `adaptive_retrieval.py` không sửa. Test so sánh hai đường: `tests/test_rag_v2_numpy_dense.py`.

## 2. Bảng benchmark trước/sau

Máy này. Vector thật BGE-M3, 1024 chiều, `float32-le`, `normalized=1`, từ `local_runs/battle_rag_v2_index_cache/bffc6fac625657acdad91b172079034cb8ec0b6ac403ee48e6ae4f56ef8bd20d/rag_v2_dev.sqlite`.

Mỗi lần đo: 8 biến thể, `candidate_limit=100`, `limit=10`. `embed_query` trả về một vector đã lưu, nên số liệu là thời gian quét, không gồm thời gian nhúng BGE. 1 lần lạnh, 1 lần làm nóng, rồi 5 lần tính giờ. Đơn vị giây.

| Tập | Chunks | Đường | Lạnh | 5 lần ấm | Trung bình ấm | Trung vị ấm |
| --- | ---: | --- | ---: | --- | ---: | ---: |
| Index thật | 9919 | Python | 16.206701600 | 28.006536300, 45.915047300, 50.189585100, 50.481634700, 47.572170600 | 44.432994800 | 47.572170600 |
| Index thật | 9919 | Numpy | 1.161773500 | 0.459060900, 0.359290200, 0.420900900, 0.443045500, 0.477125300 | 0.431884560 | 0.443045500 |
| Thật + 81 bản sao vector thật | 10000 | Python | 24.248609300 | 15.734785100, 34.709961300, 27.051103100, 19.023376400, 15.792076200 | 22.462260420 | 19.023376400 |
| Thật + 81 bản sao vector thật | 10000 | Numpy | 0.781189800 | 0.240956500, 0.228166400, 0.263170600, 0.242766800, 0.263864700 | 0.247785000 | 0.242766800 |

Tốc độ trên tập 10000 chunk: trung bình 90.652×, trung vị 78.361×. Cặp thận trọng nhất trên cùng tập (Python nhanh nhất / numpy chậm nhất) là 15.734785100 / 0.263864700 = 59.632×. Thời gian Python dao động vì máy đang bận; numpy ổn định hơn.

## 3. So sánh chất lượng

Top-10, điểm cosine và `ranking_signals` của hai đường giống nhau trên cả 9919 chunk thật và 10000 chunk. Test `test_numpy_dense_topk_matches_python_path` so `SearchResult` bằng nhau 100%, gồm thứ tự, điểm, biến thể khớp, và bộ lọc privacy/staleness.

## 4. Kết quả `pytest tests/`

`3117 passed, 2 skipped, 1 failed` trong 865.99s.

Đỏ, không do FIX 1: `tests/test_commit_d_wheel_and_packaging.py::TestDependencyManifestLockIntegrity::test_uv_lock_check_succeeds`. `uv lock --check` báo lockfile cần cập nhật. `pyproject.toml` và `uv.lock` không nằm trong diff của fix này.

## 5. Flag rollback

- `AIOS_RAG_V2_NUMPY_DENSE`: mặc định tắt (`unset` / khác `1|true|yes|on`). Tắt là về vòng Python.
- `AIOS_RAG_V2_NUMPY_DENSE_MAX_BYTES`: mặc định `2147483648`. Vượt ngân sách thì không cache và dùng đường Python.

## 6. Điểm khác với phiếu việc

- Index thật còn đọc được lớn nhất là 9919 chunk, không đủ 10000. Lần đo ≥10k dùng bản sao tạm của index đó cộng 81 vector thật nhân đôi, không ghi vào DB sản xuất.
- Không dùng một phép `matrix @ qvec` làm điểm công bố. Float32/float64 lệch khoảng 1 ULP so với tổng Python, nên shortlist dùng matmul, hàng sát nhau và top-k trả ra được chấm lại bằng `cosine_similarity`. Nhờ đó kết quả giống đường cũ.
- Log stage thêm ở `dense_candidates`: embed, load, score, fuse. Không bọc `synthesize_evidence` vì hàm đó có nhiều lối thoát; thời gian synthesis đã có trong `eval_harness.py`.

## 7. Đánh giá

Đạt khi bật flag: top-k giống đường cũ, và lần quét ấm trên ≥10k chunk nhanh hơn 50 lần kể cả cặp thận trọng nhất (59.632×). Mặc định vẫn tắt, đúng ràng buộc rollback.
