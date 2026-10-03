# Báo cáo INDEX-SPLIT-R2 — dừng ở dry-run

- Trạng thái: **DỪNG đúng cổng Bước 1.** Không tách thật, không dựng collection mới, không bật cờ định tuyến, không hỏi đáp thử.
- Máy: `h410asrock` (máy nhà). Không đụng PC0575. Không merge `main`. Không sửa code.
- Ngày: 2026-10-03. Nhánh: `phieu-viec/rag-fix1`. Tip khi nhận vé: `871c2b6` (có Phase A2 từ `323860a`).
- Cổng watcher: `LAUNCH 1/4` lúc 2026-10-03 21:32:32 (`launchStallCount=1`). Điều kiện mở đã tới (đúng máy nhà, Phase A2 đã có trên nhánh). Không dùng nhánh 4 lần watcher. Lý do `cho-muse`: cổng dừng của vé — 72 tài liệu confidence < 0,40.

## 1. Bước 0

`--help` liệt kê `--dry-run` riêng, không gắn với `--allow-production`.

Lệnh module chạy bằng `PYTHONPATH=src uv run --no-sync --group dev python` vì `python` trên PATH là stub Microsoft Store và gói chưa cài editable trong `.venv`. Python thực tế: 3.11.14.

| Mục | Trước | Sau dry-run |
| --- | --- | --- |
| File | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

SHA khớp ghim vé (`45eb0e07…b7c0`) và khớp bản backup `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre`. Không tạo `C:\AIOS_index_split_preview`. Không tạo `collections_new`.

## 2. Dry-run

```
python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "C:\AIOS_index_split_preview" --dry-run
```

Mã thoát 0. Công cụ in: «Chế độ dry-run: không ghi file nào.» Log local (không đưa git): `D:\Sandbox\AIOS_index_split_backup\dry-run-r2-20261003.log`.

Tổng: **889 document / 149.800 chunk** — khớp kiểm kê.

| Khối | Document | Chunk | Độ tin cậy trung bình | Confidence < 0,40 |
| --- | ---: | ---: | ---: | ---: |
| LSU | 123 | 73.150 | 0,562 | 31 |
| Điều tra lỗi | 704 | 75.419 | 0,892 | 23 |
| MOM | 62 | 1.231 | 0,567 | 18 |
| Tổng | 889 | 149.800 |  | 72 |

So với dry-run lần 1 (453 tài liệu confidence < 0,40, trong đó 451 bằng 0): bộ A2 đã kéo phần lớn lên. Còn **72** tài liệu dưới 0,40, gồm **2.402 chunk**. Chỉ **1** tài liệu còn confidence = 0 (`dữ liệu tổng hợp.xlsx` — đúng chủ ý Phase A2: không gán «tổng hợp» theo tên). 71 tài liệu còn lại được centroid gán khối nhưng chênh cosine quá nhỏ nên confidence vẫn dưới 0,40.

Đuôi của 72 tài liệu thấp:

| Nhóm | Số tài liệu |
| --- | ---: |
| `wsc-*.txt` (mất tên gốc) | 47 |
| `.png` | 11 |
| `.xlsx` | 3 |
| `.pdf` | 3 |
| `.msg` | 2 |
| `.bmp` | 2 |
| `.xlsm` | 2 |
| `.csv` | 1 |
| `.html` | 1 |

## 3. Vì sao dừng

Vé nói: nếu số document confidence < 0,40 vẫn lớn bất thường (**vài chục trở lên**) thì dừng, báo danh sách, đặt `cho-muse`. **72 là vài chục trở lên.** Không chạy Bước 2.

Ghi nhận thêm, không phải lý do dừng: ổ C còn khoảng 2,0 GB trống. Tách thật ghi ra `collections_new` trên ổ C sẽ cần cỡ dung lượng kho nguồn (2,94 GB). Dù Muse nới cổng confidence, tách thật trên ổ C hiện không đủ chỗ.

## 4. Danh sách 72 tài liệu confidence < 0,40

Công cụ chỉ in 50 dòng đầu. Bảng dưới là đủ 72 dòng, cùng một lượt phân loại (từ khóa + centroid), sắp theo confidence tăng. JSON đầy đủ nằm ngoài git: `D:\Sandbox\AIOS_index_split_backup\dry-run-r2-low-20261003.json`.

| # | document_id | khối gán | confidence | chunk | tên nguồn | lý do |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 1 | `wsc-2340acdb03f71fc0a04fd77f` | Điều tra lỗi | 0.000 | 500 | dữ liệu tổng hợp.xlsx | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch |
| 2 | `wsc-ef469ab3d32e4c1060e9f947` | Điều tra lỗi | 0.021 | 4 | wsc-ef469ab3d32e4c1060e9f947.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.839, chênh 0.005) |
| 3 | `wsc-c6c395c5962dbd9a7cd35661` | LSU | 0.029 | 6 | dvu_prt_vdbg_docpg.csv | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.798, chênh 0.007) |
| 4 | `wsc-492485e50bac291bf4c81cc4` | LSU | 0.030 | 1 | wsc-492485e50bac291bf4c81cc4.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.551, chênh 0.007) |
| 5 | `wsc-5f2696c9a22072e7d4873267` | LSU | 0.030 | 1 | wsc-5f2696c9a22072e7d4873267.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.551, chênh 0.007) |
| 6 | `wsc-1526cbd0e45f7c07240030b8` | LSU | 0.034 | 44 | wsc-1526cbd0e45f7c07240030b8.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.837, chênh 0.009) |
| 7 | `wsc-5f357714c9ab95fe58b8fff6` | LSU | 0.041 | 17 | wsc-5f357714c9ab95fe58b8fff6.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.814, chênh 0.010) |
| 8 | `wsc-8782bf3e41a80998543bc9dd` | MOM | 0.043 | 1 | wsc-8782bf3e41a80998543bc9dd.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.683, chênh 0.011) |
| 9 | `wsc-da1844282c07cff93145d49f` | Điều tra lỗi | 0.044 | 1 | wsc-da1844282c07cff93145d49f.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.568, chênh 0.011) |
| 10 | `wsc-2d62e0b3a3ca889c7679ed93` | LSU | 0.053 | 8 | wsc-2d62e0b3a3ca889c7679ed93.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.745, chênh 0.013) |
| 11 | `wsc-06019d8f449eb205c7bcae02` | Điều tra lỗi | 0.056 | 61 | RE    IRIS2020(Low model) -C22 A1- Upsoft OK initial setting - LCD displayed C3501.msg | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.865, chênh 0.014) |
| 12 | `wsc-baf337f476d781df19a8b7e8` | Điều tra lỗi | 0.060 | 245 | FW  2021 11 20週報.msg | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.862, chênh 0.015) |
| 13 | `wsc-037c28842e209b28625d6157` | Điều tra lỗi | 0.065 | 4 | wsc-037c28842e209b28625d6157.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.848, chênh 0.016) |
| 14 | `wsc-1696cf072a16a43c802ff100` | LSU | 0.080 | 1 | TEK00001.BMP | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.651, chênh 0.020) |
| 15 | `wsc-4cbd21f3ccab9c9ea52161fa` | Điều tra lỗi | 0.085 | 1 | wsc-4cbd21f3ccab9c9ea52161fa.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.659, chênh 0.021) |
| 16 | `wsc-71abdd06f47c205da102e908` | Điều tra lỗi | 0.085 | 1 | wsc-71abdd06f47c205da102e908.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.659, chênh 0.021) |
| 17 | `wsc-fa75c3428af75175f9f4d5aa` | Điều tra lỗi | 0.089 | 1 | N00137687_実行.pdf | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.723, chênh 0.022) |
| 18 | `wsc-b645bfc9b278ac6d11ffa21c` | Điều tra lỗi | 0.089 | 81 | Tab led cam ung.pdf | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.759, chênh 0.022) |
| 19 | `wsc-0a49389b70f1e9592670c5e9` | MOM | 0.093 | 1 | wsc-0a49389b70f1e9592670c5e9.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.685, chênh 0.023) |
| 20 | `wsc-9e9831c8c58795058809bf95` | MOM | 0.093 | 1 | wsc-9e9831c8c58795058809bf95.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.685, chênh 0.023) |
| 21 | `wsc-18c17803678e5d71f0cbb2ba` | MOM | 0.108 | 1 | wsc-18c17803678e5d71f0cbb2ba.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.611, chênh 0.027) |
| 22 | `wsc-4e59cb5f495278f0be7fa444` | MOM | 0.108 | 1 | wsc-4e59cb5f495278f0be7fa444.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.611, chênh 0.027) |
| 23 | `wsc-fb3c0c9d41407d55a8dbb2fe` | Điều tra lỗi | 0.109 | 64 | Tab led cam ung.pdf | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.772, chênh 0.027) |
| 24 | `wsc-c7377cc9661005aa4d35d54e` | Điều tra lỗi | 0.115 | 3 | wsc-c7377cc9661005aa4d35d54e.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.780, chênh 0.029) |
| 25 | `wsc-149cac9d8b129f8244b616ef` | MOM | 0.118 | 1 | wsc-149cac9d8b129f8244b616ef.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.689, chênh 0.029) |
| 26 | `wsc-eab6e69c0a9795201f575c88` | MOM | 0.118 | 1 | wsc-eab6e69c0a9795201f575c88.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.689, chênh 0.029) |
| 27 | `wsc-be0e15bdc0524321e7587d7c` | MOM | 0.123 | 1 | wsc-be0e15bdc0524321e7587d7c.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.715, chênh 0.031) |
| 28 | `wsc-c4f19c08de138e4dfeeceacc` | MOM | 0.123 | 1 | wsc-c4f19c08de138e4dfeeceacc.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.715, chênh 0.031) |
| 29 | `wsc-5b78db8c9cc2ad9844a9a0d7` | MOM | 0.127 | 1 | wsc-5b78db8c9cc2ad9844a9a0d7.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.526, chênh 0.032) |
| 30 | `wsc-42843eb6ca4459ae3af6b657` | Điều tra lỗi | 0.131 | 1 | wsc-42843eb6ca4459ae3af6b657.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.676, chênh 0.033) |
| 31 | `wsc-db6bb8495e13e16cd73fe9aa` | Điều tra lỗi | 0.131 | 1 | wsc-db6bb8495e13e16cd73fe9aa.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.676, chênh 0.033) |
| 32 | `wsc-118d0600a2a94d418f2880ac` | LSU | 0.132 | 28 | wsc-118d0600a2a94d418f2880ac.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.794, chênh 0.033) |
| 33 | `wsc-65074328893666b1fbd9b4aa` | Điều tra lỗi | 0.137 | 3 | wsc-65074328893666b1fbd9b4aa.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.813, chênh 0.034) |
| 34 | `wsc-d51ca7a46bac26fe55714eba` | Điều tra lỗi | 0.138 | 1 | wsc-d51ca7a46bac26fe55714eba.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.738, chênh 0.035) |
| 35 | `wsc-fb5c095f5d8bcfa80db7805b` | Điều tra lỗi | 0.138 | 1 | wsc-fb5c095f5d8bcfa80db7805b.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.738, chênh 0.035) |
| 36 | `wsc-4ed67081b49075eed077ebf7` | MOM | 0.152 | 1 | wsc-4ed67081b49075eed077ebf7.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.717, chênh 0.038) |
| 37 | `wsc-6c84807638a179552dd437ce` | MOM | 0.152 | 1 | wsc-6c84807638a179552dd437ce.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.717, chênh 0.038) |
| 38 | `wsc-6d14cd1be7bda0d92499e2ae` | LSU | 0.156 | 1 | TEK00002.BMP | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.642, chênh 0.039) |
| 39 | `wsc-579b74f1c047f8145d879382` | LSU | 0.161 | 13 | 238.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.874, chênh 0.040) |
| 40 | `wsc-527f8bd013650df67796b8bc` | LSU | 0.163 | 14 | 238 l2.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.876, chênh 0.041) |
| 41 | `wsc-9abdeef3c1bfc6c3a09df1e7` | LSU | 0.169 | 13 | 234.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.878, chênh 0.042) |
| 42 | `wsc-57a940899f40e39ec67b9661` | LSU | 0.170 | 14 | 235 l2.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.874, chênh 0.043) |
| 43 | `wsc-4cc1bf837aa6c9844d67eb4c` | LSU | 0.170 | 38 | wsc-4cc1bf837aa6c9844d67eb4c.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.834, chênh 0.043) |
| 44 | `wsc-230baee36cd917aefc37d5e9` | MOM | 0.171 | 116 | AllItems.html | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.795, chênh 0.043) |
| 45 | `wsc-8ce71e2a14d81de80d196655` | Điều tra lỗi | 0.174 | 2 | wsc-8ce71e2a14d81de80d196655.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.774, chênh 0.043) |
| 46 | `wsc-ef2a484ca7dce3af9666b643` | LSU | 0.179 | 13 | 239.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.878, chênh 0.045) |
| 47 | `wsc-5953d3fff1a73f1068d08192` | LSU | 0.180 | 14 | 234 master.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.883, chênh 0.045) |
| 48 | `wsc-aa48e2b47a8c52c66c835e70` | Điều tra lỗi | 0.181 | 1 | wsc-aa48e2b47a8c52c66c835e70.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.721, chênh 0.045) |
| 49 | `wsc-e5f2338de8fbfdbd4faefe63` | Điều tra lỗi | 0.181 | 1 | wsc-e5f2338de8fbfdbd4faefe63.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.721, chênh 0.045) |
| 50 | `wsc-7f5d66631ea984eb8dfb4614` | LSU | 0.183 | 14 | 235 master.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.881, chênh 0.046) |
| 51 | `wsc-c86111fa5390875aaa5fefb4` | LSU | 0.187 | 14 | 238 l1.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.883, chênh 0.047) |
| 52 | `wsc-08d8d7616f71e6b9ae67940f` | LSU | 0.192 | 41 | wsc-08d8d7616f71e6b9ae67940f.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.835, chênh 0.048) |
| 53 | `wsc-4ab9350286ad8e78809e7dc3` | LSU | 0.193 | 14 | 234 l2.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.882, chênh 0.048) |
| 54 | `wsc-a010f8f4fc78f6eabbaf4dff` | LSU | 0.193 | 14 | 238 master.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.882, chênh 0.048) |
| 55 | `wsc-8fa4fe038d9a05d81b9eb528` | LSU | 0.201 | 14 | 234 l1.1.png | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.890, chênh 0.050) |
| 56 | `wsc-38c83e012535c1c00a21b3a5` | LSU | 0.203 | 36 | wsc-38c83e012535c1c00a21b3a5.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.816, chênh 0.051) |
| 57 | `wsc-d489e437c9abecd020ee12ba` | LSU | 0.203 | 36 | wsc-d489e437c9abecd020ee12ba.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.817, chênh 0.051) |
| 58 | `wsc-5d2f610a69cf193a6d06c754` | LSU | 0.204 | 36 | wsc-5d2f610a69cf193a6d06c754.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.816, chênh 0.051) |
| 59 | `wsc-989a0376f54d1fc7ebc90698` | LSU | 0.206 | 36 | wsc-989a0376f54d1fc7ebc90698.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.819, chênh 0.052) |
| 60 | `wsc-f5e16c8261a4f585e58dd705` | Điều tra lỗi | 0.222 | 1 | wsc-f5e16c8261a4f585e58dd705.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.591, chênh 0.055) |
| 61 | `wsc-ed68732921223c2e64eb1304` | LSU | 0.249 | 10 | matome.xlsx | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.766, chênh 0.062) |
| 62 | `wsc-9b0f3c85c73cf74b5dbd8bef` | LSU | 0.251 | 98 | Dữ liệu tổng hợp.xlsx | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.922, chênh 0.063) |
| 63 | `wsc-ab3ed0277c9e671ac3587bd0` | LSU | 0.272 | 591 | 6778_CyCav_F_2025.11.13.xlsm | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.835, chênh 0.068) |
| 64 | `wsc-a36e39c1d9713f21dc65bcaf` | LSU | 0.302 | 1 | wsc-a36e39c1d9713f21dc65bcaf.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.702, chênh 0.075) |
| 65 | `wsc-750990be3801b81970805644` | MOM | 0.311 | 4 | wsc-750990be3801b81970805644.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.772, chênh 0.078) |
| 66 | `wsc-51548ca220d6ccc9ec419c8c` | MOM | 0.324 | 59 | wsc-51548ca220d6ccc9ec419c8c.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.891, chênh 0.081) |
| 67 | `wsc-9a89ee076ef452c7837435d1` | LSU | 0.327 | 24 | 6778_CyCav_G_2025.11.13.xlsm | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất LSU (cos 0.803, chênh 0.082) |
| 68 | `wsc-015067b75dc12e2770b7d8cb` | Điều tra lỗi | 0.343 | 1 | wsc-015067b75dc12e2770b7d8cb.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.648, chênh 0.086) |
| 69 | `wsc-90597a45cd475fa1a42d442d` | Điều tra lỗi | 0.343 | 1 | wsc-90597a45cd475fa1a42d442d.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất Điều tra lỗi (cos 0.648, chênh 0.086) |
| 70 | `wsc-097fe6a008b410dc299a0948` | MOM | 0.348 | 11 | wsc-097fe6a008b410dc299a0948.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.816, chênh 0.087) |
| 71 | `wsc-9abe0b8f8e644d009d771d5a` | MOM | 0.348 | 11 | wsc-9abe0b8f8e644d009d771d5a.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.816, chênh 0.087) |
| 72 | `wsc-d320e16fa80ee7e311b42fb7` | MOM | 0.354 | 4 | wsc-d320e16fa80ee7e311b42fb7.txt | tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch / centroid vector: gần nhất MOM (cos 0.763, chênh 0.089) |

## 5. Không làm

- Không tách thật, không `--allow-production`.
- Không dựng collection `lsu` / `dieu_tra_loi` / `mom`.
- Không bật `AIOS_DOMAIN_ROUTING_ENABLED`.
- Không hỏi đáp thử, không thử rollback (chưa đổi app).
- Không embed lại, không ingest, không sửa `tri_thuc\library.sqlite`.
