# Báo cáo INDEX-SPLIT-R5 — tách thật đạt

- Trạng thái: **xong, chờ duyệt.** Manifest `overall: DAT`. Không dựng collection cho app, không bật cờ định tuyến, không hỏi đáp thử.
- Máy: `h410asrock` (máy nhà). Không đụng PC0575. Không merge `main`. Không sửa code.
- Ngày: 2026-10-03. Nhánh: `phieu-viec/rag-fix1`. Tip khi nhận vé: `db3e189` (có vá `5043a42`).
- Cổng watcher: `LAUNCH 1/4` lúc 2026-10-03 22:25:10 (`launchStallCount=1`). Điều kiện mở đã tới (đúng máy nhà, vá `5043a42` đã có trên nhánh). **Không** dùng nhánh 4 lần watcher.

## 1. Bước 0

`python` trên PATH là stub Microsoft Store. Lệnh module chạy bằng `PYTHONPATH=src uv run --no-sync --group dev python` (Python 3.11.14).

`pytest tests/test_split_index_by_domain.py -q`: **13 passed** trong 2,45 giây, gồm `test_verify_domain_batches_over_sqlite_variable_limit`.

| Mục | Trước | Sau tách thật |
| --- | --- | --- |
| File | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

SHA khớp ghim vé (`45eb0e07…b7c0`). Kho cũ chỉ bị đọc.

Dung lượng trống trước khi tách: ổ D còn 67.392.720.896 byte (~62,8 GB). Ổ C không nhận file tách.

File dở của R4 trước khi chạy lại: `D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite` 1.155.637.248 byte. `--overwrite` đã xóa và tạo lại.

## 2. Lệnh đã chạy

```
python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "D:\Sandbox\AIOS_index_split_new" --allow-production --overwrite
```

Lệnh thoát thành công. Thời gian khoảng 170 giây. Dòng cuối: `Kết quả tổng: ĐẠT`. Manifest ghi lúc `2026-10-03T22:30:49+07:00`.

Không còn lỗi `too many SQL variables`. Bốn khối đều tự kiểm `ĐẠT` (`documents_match` và `vectors_intact`, `vector_loss` rỗng).

## 3. Manifest

File: `D:\Sandbox\AIOS_index_split_new\domain_manifest.json`.

- `overall`: `DAT`
- `verification.cross_domain.ok`: true
- `source_chunks` = `split_chunks_sum` = **149.800**
- `source_documents` = **889**
- `overlapping_documents`: `[]`
- Không có `document_id` lặp trong manifest (889 mục, 889 id khác nhau).
- Tập `domain=tong_hop` **trùng đúng** tập `low_confidence=true` (72 tài liệu, không thừa, không thiếu).

| Khối | Thư mục | Document | Chunk | Dense | Sparse | Multivector | Tự kiểm |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| LSU | `lsu` | 92 | 71.945 | 52.842 | 52.842 | 0 | ĐẠT |
| Điều tra lỗi | `dieu_tra_loi` | 681 | 74.439 | 66.055 | 66.055 | 0 | ĐẠT |
| MOM | `mom` | 44 | 1.014 | 933 | 933 | 0 | ĐẠT |
| Tổng hợp | `tong_hop` | 72 | 2.402 | 1.841 | 1.841 | 0 | ĐẠT |
| Tổng |  | 889 | 149.800 | 121.671 | 121.671 | 0 | DAT |

Số vector dense/sparse cộng 4 khối = 121.671, khớp kiểm kê kho cũ đã biết. Multivector = 0, cũng khớp.

Khối Tổng hợp là 72 tài liệu confidence < 0,40 đã chuyển khỏi khối gán gốc (LSU 31, Điều tra lỗi 23, MOM 18). Cùng 72 tài liệu của dry-run R2, cùng 2.402 chunk.

| File đích | Byte | mtime |
| --- | ---: | --- |
| `lsu\library.sqlite` | 1.155.637.248 | 2026-10-03 22:29:10 |
| `dieu_tra_loi\library.sqlite` | 1.643.761.664 | 2026-10-03 22:30:35 |
| `mom\library.sqlite` | 21.598.208 | 2026-10-03 22:30:44 |
| `tong_hop\library.sqlite` | 36.081.664 | 2026-10-03 22:30:49 |
| `domain_manifest.json` | 491.253 | 2026-10-03 22:30:49 |

## 4. Danh sách 72 tài liệu khối Tổng hợp

Sắp theo confidence tăng. Cột «khối gán gốc» là `assigned_domain` trước khi chuyển sang `tong_hop`. Cả 72 dòng có `low_confidence=true`.

| # | document_id | khối gán gốc | confidence | chunk | tên nguồn |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | `wsc-2340acdb03f71fc0a04fd77f` | Điều tra lỗi | 0.000 | 500 | dữ liệu tổng hợp.xlsx |
| 2 | `wsc-ef469ab3d32e4c1060e9f947` | Điều tra lỗi | 0.021 | 4 | wsc-ef469ab3d32e4c1060e9f947.txt |
| 3 | `wsc-c6c395c5962dbd9a7cd35661` | LSU | 0.029 | 6 | dvu_prt_vdbg_docpg.csv |
| 4 | `wsc-492485e50bac291bf4c81cc4` | LSU | 0.030 | 1 | wsc-492485e50bac291bf4c81cc4.txt |
| 5 | `wsc-5f2696c9a22072e7d4873267` | LSU | 0.030 | 1 | wsc-5f2696c9a22072e7d4873267.txt |
| 6 | `wsc-1526cbd0e45f7c07240030b8` | LSU | 0.034 | 44 | wsc-1526cbd0e45f7c07240030b8.txt |
| 7 | `wsc-5f357714c9ab95fe58b8fff6` | LSU | 0.041 | 17 | wsc-5f357714c9ab95fe58b8fff6.txt |
| 8 | `wsc-8782bf3e41a80998543bc9dd` | MOM | 0.043 | 1 | wsc-8782bf3e41a80998543bc9dd.txt |
| 9 | `wsc-da1844282c07cff93145d49f` | Điều tra lỗi | 0.044 | 1 | wsc-da1844282c07cff93145d49f.txt |
| 10 | `wsc-2d62e0b3a3ca889c7679ed93` | LSU | 0.053 | 8 | wsc-2d62e0b3a3ca889c7679ed93.txt |
| 11 | `wsc-06019d8f449eb205c7bcae02` | Điều tra lỗi | 0.056 | 61 | RE    IRIS2020(Low model) -C22 A1- Upsoft OK initial setting - LCD displayed C3501.msg |
| 12 | `wsc-baf337f476d781df19a8b7e8` | Điều tra lỗi | 0.060 | 245 | FW  2021 11 20週報.msg |
| 13 | `wsc-037c28842e209b28625d6157` | Điều tra lỗi | 0.065 | 4 | wsc-037c28842e209b28625d6157.txt |
| 14 | `wsc-1696cf072a16a43c802ff100` | LSU | 0.080 | 1 | TEK00001.BMP |
| 15 | `wsc-4cbd21f3ccab9c9ea52161fa` | Điều tra lỗi | 0.085 | 1 | wsc-4cbd21f3ccab9c9ea52161fa.txt |
| 16 | `wsc-71abdd06f47c205da102e908` | Điều tra lỗi | 0.085 | 1 | wsc-71abdd06f47c205da102e908.txt |
| 17 | `wsc-b645bfc9b278ac6d11ffa21c` | Điều tra lỗi | 0.089 | 81 | Tab led cam ung.pdf |
| 18 | `wsc-fa75c3428af75175f9f4d5aa` | Điều tra lỗi | 0.089 | 1 | N00137687_実行.pdf |
| 19 | `wsc-0a49389b70f1e9592670c5e9` | MOM | 0.093 | 1 | wsc-0a49389b70f1e9592670c5e9.txt |
| 20 | `wsc-9e9831c8c58795058809bf95` | MOM | 0.093 | 1 | wsc-9e9831c8c58795058809bf95.txt |
| 21 | `wsc-18c17803678e5d71f0cbb2ba` | MOM | 0.108 | 1 | wsc-18c17803678e5d71f0cbb2ba.txt |
| 22 | `wsc-4e59cb5f495278f0be7fa444` | MOM | 0.108 | 1 | wsc-4e59cb5f495278f0be7fa444.txt |
| 23 | `wsc-fb3c0c9d41407d55a8dbb2fe` | Điều tra lỗi | 0.109 | 64 | Tab led cam ung.pdf |
| 24 | `wsc-c7377cc9661005aa4d35d54e` | Điều tra lỗi | 0.115 | 3 | wsc-c7377cc9661005aa4d35d54e.txt |
| 25 | `wsc-149cac9d8b129f8244b616ef` | MOM | 0.118 | 1 | wsc-149cac9d8b129f8244b616ef.txt |
| 26 | `wsc-eab6e69c0a9795201f575c88` | MOM | 0.118 | 1 | wsc-eab6e69c0a9795201f575c88.txt |
| 27 | `wsc-be0e15bdc0524321e7587d7c` | MOM | 0.123 | 1 | wsc-be0e15bdc0524321e7587d7c.txt |
| 28 | `wsc-c4f19c08de138e4dfeeceacc` | MOM | 0.123 | 1 | wsc-c4f19c08de138e4dfeeceacc.txt |
| 29 | `wsc-5b78db8c9cc2ad9844a9a0d7` | MOM | 0.127 | 1 | wsc-5b78db8c9cc2ad9844a9a0d7.txt |
| 30 | `wsc-42843eb6ca4459ae3af6b657` | Điều tra lỗi | 0.131 | 1 | wsc-42843eb6ca4459ae3af6b657.txt |
| 31 | `wsc-db6bb8495e13e16cd73fe9aa` | Điều tra lỗi | 0.131 | 1 | wsc-db6bb8495e13e16cd73fe9aa.txt |
| 32 | `wsc-118d0600a2a94d418f2880ac` | LSU | 0.132 | 28 | wsc-118d0600a2a94d418f2880ac.txt |
| 33 | `wsc-65074328893666b1fbd9b4aa` | Điều tra lỗi | 0.137 | 3 | wsc-65074328893666b1fbd9b4aa.txt |
| 34 | `wsc-d51ca7a46bac26fe55714eba` | Điều tra lỗi | 0.138 | 1 | wsc-d51ca7a46bac26fe55714eba.txt |
| 35 | `wsc-fb5c095f5d8bcfa80db7805b` | Điều tra lỗi | 0.138 | 1 | wsc-fb5c095f5d8bcfa80db7805b.txt |
| 36 | `wsc-4ed67081b49075eed077ebf7` | MOM | 0.152 | 1 | wsc-4ed67081b49075eed077ebf7.txt |
| 37 | `wsc-6c84807638a179552dd437ce` | MOM | 0.152 | 1 | wsc-6c84807638a179552dd437ce.txt |
| 38 | `wsc-6d14cd1be7bda0d92499e2ae` | LSU | 0.156 | 1 | TEK00002.BMP |
| 39 | `wsc-579b74f1c047f8145d879382` | LSU | 0.161 | 13 | 238.png |
| 40 | `wsc-527f8bd013650df67796b8bc` | LSU | 0.163 | 14 | 238 l2.png |
| 41 | `wsc-9abdeef3c1bfc6c3a09df1e7` | LSU | 0.169 | 13 | 234.png |
| 42 | `wsc-4cc1bf837aa6c9844d67eb4c` | LSU | 0.170 | 38 | wsc-4cc1bf837aa6c9844d67eb4c.txt |
| 43 | `wsc-57a940899f40e39ec67b9661` | LSU | 0.170 | 14 | 235 l2.png |
| 44 | `wsc-230baee36cd917aefc37d5e9` | MOM | 0.171 | 116 | AllItems.html |
| 45 | `wsc-8ce71e2a14d81de80d196655` | Điều tra lỗi | 0.174 | 2 | wsc-8ce71e2a14d81de80d196655.txt |
| 46 | `wsc-ef2a484ca7dce3af9666b643` | LSU | 0.179 | 13 | 239.png |
| 47 | `wsc-5953d3fff1a73f1068d08192` | LSU | 0.180 | 14 | 234 master.png |
| 48 | `wsc-aa48e2b47a8c52c66c835e70` | Điều tra lỗi | 0.181 | 1 | wsc-aa48e2b47a8c52c66c835e70.txt |
| 49 | `wsc-e5f2338de8fbfdbd4faefe63` | Điều tra lỗi | 0.181 | 1 | wsc-e5f2338de8fbfdbd4faefe63.txt |
| 50 | `wsc-7f5d66631ea984eb8dfb4614` | LSU | 0.183 | 14 | 235 master.png |
| 51 | `wsc-c86111fa5390875aaa5fefb4` | LSU | 0.187 | 14 | 238 l1.png |
| 52 | `wsc-08d8d7616f71e6b9ae67940f` | LSU | 0.192 | 41 | wsc-08d8d7616f71e6b9ae67940f.txt |
| 53 | `wsc-4ab9350286ad8e78809e7dc3` | LSU | 0.193 | 14 | 234 l2.png |
| 54 | `wsc-a010f8f4fc78f6eabbaf4dff` | LSU | 0.193 | 14 | 238 master.png |
| 55 | `wsc-8fa4fe038d9a05d81b9eb528` | LSU | 0.201 | 14 | 234 l1.1.png |
| 56 | `wsc-38c83e012535c1c00a21b3a5` | LSU | 0.203 | 36 | wsc-38c83e012535c1c00a21b3a5.txt |
| 57 | `wsc-d489e437c9abecd020ee12ba` | LSU | 0.203 | 36 | wsc-d489e437c9abecd020ee12ba.txt |
| 58 | `wsc-5d2f610a69cf193a6d06c754` | LSU | 0.204 | 36 | wsc-5d2f610a69cf193a6d06c754.txt |
| 59 | `wsc-989a0376f54d1fc7ebc90698` | LSU | 0.206 | 36 | wsc-989a0376f54d1fc7ebc90698.txt |
| 60 | `wsc-f5e16c8261a4f585e58dd705` | Điều tra lỗi | 0.222 | 1 | wsc-f5e16c8261a4f585e58dd705.txt |
| 61 | `wsc-ed68732921223c2e64eb1304` | LSU | 0.249 | 10 | matome.xlsx |
| 62 | `wsc-9b0f3c85c73cf74b5dbd8bef` | LSU | 0.251 | 98 | Dữ liệu tổng hợp.xlsx |
| 63 | `wsc-ab3ed0277c9e671ac3587bd0` | LSU | 0.272 | 591 | 6778_CyCav_F_2025.11.13.xlsm |
| 64 | `wsc-a36e39c1d9713f21dc65bcaf` | LSU | 0.302 | 1 | wsc-a36e39c1d9713f21dc65bcaf.txt |
| 65 | `wsc-750990be3801b81970805644` | MOM | 0.311 | 4 | wsc-750990be3801b81970805644.txt |
| 66 | `wsc-51548ca220d6ccc9ec419c8c` | MOM | 0.324 | 59 | wsc-51548ca220d6ccc9ec419c8c.txt |
| 67 | `wsc-9a89ee076ef452c7837435d1` | LSU | 0.327 | 24 | 6778_CyCav_G_2025.11.13.xlsm |
| 68 | `wsc-015067b75dc12e2770b7d8cb` | Điều tra lỗi | 0.343 | 1 | wsc-015067b75dc12e2770b7d8cb.txt |
| 69 | `wsc-90597a45cd475fa1a42d442d` | Điều tra lỗi | 0.343 | 1 | wsc-90597a45cd475fa1a42d442d.txt |
| 70 | `wsc-097fe6a008b410dc299a0948` | MOM | 0.348 | 11 | wsc-097fe6a008b410dc299a0948.txt |
| 71 | `wsc-9abe0b8f8e644d009d771d5a` | MOM | 0.348 | 11 | wsc-9abe0b8f8e644d009d771d5a.txt |
| 72 | `wsc-d320e16fa80ee7e311b42fb7` | MOM | 0.354 | 4 | wsc-d320e16fa80ee7e311b42fb7.txt |

## 5. Không làm

- Không embed lại, không ingest, không sửa `tri_thuc\library.sqlite`.
- Không bật `AIOS_DOMAIN_ROUTING_ENABLED` (biến môi trường không đặt).
- Không dựng collection cho app, không restart app, không hỏi đáp thử.
