# Báo cáo vé AUDIT-EMBED-GEMMA-HOME — Kiểm lại độc lập đánh giá EmbeddingGemma 2

- **Máy thực hiện:** NHÀ `h410asrock` (thợ `OMP`).
- **Thời điểm:** 2026-10-08 ~23:27 – 23:50 +07.
- **Báo cáo gốc:** `docs/phieu-viec/ket-qua/embed-gemma-eval-home.md` (thợ `agy`, verdict ĐẠT ~10:05 08/10, kết luận KHÔNG thay BGE-M3).
- **Rào cứng giữ nguyên:** chỉ đọc — không chạy lại lượt đo, không cài/gỡ thư viện, không đụng chỉ mục hay cấu hình, không merge `main`. CSDL production chỉ mở `mode=ro`.

## 1. Bảng đối chiếu số đo chính với dữ kiện thô

| Điểm trong báo cáo gốc | Dữ kiện thô dùng để kiểm | Kết quả |
|---|---|---|
| Tập đo 7 câu nhóm A, pool 162 chunks (137 đích + 25 đối chứng) | Đếm lại từ `library.sqlite` (chỉ đọc): Sirius 2 = 22, OKNGUNIT = 26, Bong TAPE = 7, Camera 140 = 5, MOUNT LD BLOCK = 77 → tổng 137; +25 = **162** | **KHỚP 100%** |
| Thứ hạng 768d từng câu (1/1/3/1/3/15/24) + điểm đích | `local_runs/gemma_retrieval_group_a.json`: rank và `target_score` từng câu trùng khít (Q0704 1/0.7727, Q0701 1/0.7046, Q0688 3/0.6609, Q0671 1/0.7113, Q0707 3/0.6918, Q0696 15/0.6768, Q0668 24/0.6092) | **KHỚP 100%** |
| Thứ hạng 256d từng câu (1/1/3/1/5/18/50) + điểm đích | Cùng file trên: Q0704 1/0.7930, Q0701 1/0.7297, Q0688 3/0.6782, Q0671 1/0.7626, Q0707 5/0.7151, Q0696 18/0.6966, Q0668 50/0.6331 | **KHỚP 100%** |
| Tỉ lệ Top-3: 768d 71,4% (5/7), 256d 57,1% (4/7) | Đếm lại `pass_top3` từ file thô: 5/7 và 4/7 | **KHỚP** |
| Nạp mô hình 18,48s; encode câu 515,38ms; encode chunk 2945,63ms; 0,34 chunks/s | `local_runs/gemma_bench_raw.json`: 18.482 / 515.38 / 2945.63 / 0.34 | **KHỚP** |
| Model ID + revision `914f7f89…` | File bench + snapshot trong cache Hugging Face (`snapshots/914f7f89…`) | **KHỚP** |
| Trọng số safetensors 1.488.915.288 bytes (~1,48 GB) | `model.safetensors` trong snapshot đúng từng byte | **KHỚP** |
| Giấy phép Apache 2.0 | Dòng `license: apache-2.0` trong README của snapshot | **KHỚP** |
| Dung lượng vector toàn kho: 613,6 / 460,2 / 153,4 MB | Tính lại (đơn vị thập phân, như báo cáo): 149800×4096/10⁶ = 613,6; ×3072 = 460,2; ×1024 = 153,4 | **KHỚP** (nhất quán cả 3 số) |
| Ước tính nhúng lại 149.800 mảnh ≈ 122,57 giờ CPU | Tính lại từ tốc độ chưa làm tròn (1000/2945,63 = 0,3395 cps): 149800/0,3395/3600 = **122,57** | **KHỚP** (số 0,34 trong bảng là đã làm tròn; dùng số tròn ra 122,39 — lệch trình bày, không ảnh hưởng kết luận) |
| Môi trường cô lập `gemma_eval_venv` Python 3.11.14 | `pyvenv.cfg`: CPython 3.11.14, `include-system-site-packages = false` | **KHỚP** |

## 2. Đối chiếu 3 lý do loại

| Lý do trong kết luận gốc | Bằng chứng kiểm được | Đánh giá |
|---|---|---|
| (a) Dense-only nên trượt câu mã cứng (Q0696 rank 15, Q0668 rank 24; 256d xuống 18/50) | File thô xác nhận đủ rank/score. Soi thêm: ở Q0696 top1 là file CO-BRACKET khác (gap chỉ 0,0156 so với đích); ở Q0668 top1 là Bong TAPE (gap 0,0366) — đúng kiểu dense thiếu phân biệt mã cứng | **CÓ BẰNG CHỨNG, ĐỨNG VỮNG** |
| (b) Đòi `sentence-transformers ≥ 6.1.0` + `transformers ≥ 5.18.0` làm gãy môi trường ghim | Venv cô lập có ST **6.1.0** + transformers **5.19.0** + pillow/torchvision đầy đủ; `pyproject.toml` ghim ST **3.1.1** + transformers **4.44.2** + FlagEmbedding **1.3.5** — chênh major thật | **KIỂM CHỨNG ĐƯỢC PHẦN CHÊNH LỆCH**; riêng khẳng định "sẽ gãy FlagEmbedding/reranker" là suy luận hợp lý từ tương thích phiên bản, không phải quan sát trực tiếp (đúng rào chỉ-đọc nên không được thử nâng cấp) |
| (c) Nhúng lại toàn kho bằng CPU ~122 giờ | Phép tính khớp (mục trên). Soi thêm: tốc độ nhúng pool thật 162/641,49s = **0,25 cps** → ngoại suy 149800 mảnh ≈ **164,8 giờ**, cao hơn 34% so với 122 giờ | **PHÉP TÍNH ĐÚNG, NHƯNG CON SỐ CÒN LẠC QUAN** — thực tế pool cho thấy còn chậm hơn; kết luận "quá tải CPU" vẫn đứng, thậm chí nặng hơn |

## 3. Điểm cần đính chính (không đổi kết luận)

1. **Cột BGE-M3 không có dữ kiện thô đính kèm.** Các số 25,0s / 650–850ms / 0,48 cps / 86,7 giờ và rank Top 1–2 7/7 của BGE-M3 không tái lập được từ `local_runs` của vé này (86,7 giờ tự nhất quán với 0,48 cps nhưng nguồn số 0,48 không rõ). Audit xác nhận được phía Gemma; phía BGE phải tin báo cáo gốc.
2. **Mục tiêu vé nêu "bộ 50 câu LSU" nhưng báo cáo chỉ đo 7 câu nhóm A** — không thấy dữ kiện 50 câu nào trong kho hay máy nhà.
3. **Rank tính theo khớp tên file** (`target_key` nằm trong `source_name`), không phải rank chunk đích cụ thể; pool 162 chunks nhỏ nên rank tuyệt đối phụ thuộc pool — đủ cho so sánh tương đối, chưa đủ làm thước tuyệt đối.

## 4. Kết luận một câu

**Báo cáo gốc đứng vững** — mọi số phía Gemma tái lập được từ dữ kiện thô, cả 3 lý do loại đều có căn cứ (với 3 đính chính nhẹ về mức bằng chứng ở mục 3: cột BGE thiếu dữ kiện thô, thiếu 50 câu LSU như mục tiêu nêu, ước tính 122 giờ còn lạc quan so với tốc độ pool thật); khuyến nghị **KHÔNG thay BGE-M3 bằng EmbeddingGemma 2** giữ nguyên.
