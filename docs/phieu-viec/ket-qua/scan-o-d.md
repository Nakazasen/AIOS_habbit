# Báo cáo vé `SCAN-O-D` — kiểm kê ổ D (chỉ đọc)

- Máy: `h410asrock`, thời gian quét: 2026-10-05 05:48–06:58 +07.
- Nhánh làm việc: `phieu-viec/rag-fix1`. Tuyệt đối không đụng `main`, không force-push.
- Kết quả kiểm kê: **Đã hoàn thành 100% kiểm kê toàn bộ ổ D; không có bất kỳ file nào bị xóa, sửa hay di chuyển.**

---

## 0. Kiểm tra cổng gate và điều kiện vận hành

- Cổng gate: Watcher phát hiện vé `SCAN-O-D` từ mailbox-agy, trạng thái ban đầu `moi`.
- Điều kiện mở máy: Môi trường máy nhà `h410asrock` hợp lệ, ổ đĩa D hoạt động bình thường, quyền truy cập đọc metadata đầy đủ.
- Tiến trình không bị kẹt, không kích hoạt nhánh `cho-muse` (không có 4 lần watcher mở liên tiếp mà thiếu điều kiện), không quay vòng no-op.

---

## 1. Phương pháp quét và cam kết an toàn chỉ đọc

- Sử dụng các lệnh PowerShell/hệ thống chỉ đọc (`Get-ChildItem`, `Measure-Object`, `Get-FileHash` đọc khối trực tiếp SHA-256).
- Tuyệt đối không mở nội dung tài liệu công ty, không đọc nội dung tài liệu cá nhân (chỉ đọc metadata tên file, kích thước byte, thời gian mtime và mã băm).
- Không chạy thao tác ghi, không chạy `VACUUM`, không chạy sửa chữa cấu trúc DB.
- Băm đầy đủ SHA-256 cho toàn bộ các file `*.sqlite` trên ổ D (gồm cả các kho index thực sự, các file backup, và 593 file sqlite tạm sinh ra từ các phiên chạy kiểm thử trong `tmp\pytest-omp`).
- Mọi dữ liệu gốc trên ổ D được giữ nguyên vẹn 100%.

---

## 2. Thống kê dung lượng ổ D và cây thư mục cấp 1–2

### 2.1 Tổng quan dung lượng ổ D (thời điểm 2026-10-05 05:48 +07)

- **Tổng dung lượng đĩa**: 250.057.060.352 byte (~232,88 GB).
- **Đã sử dụng (Used)**: 189.074.821.120 byte (176,09 GB).
- **Còn trống (Free)**: 60.982.239.232 byte (56,79 GB).

### 2.2 Cây thư mục cấp 1 ổ D

| Thư mục / Tệp cấp 1 | Kích thước (Byte) | Dung lượng (GB) | Phân loại & Ghi chú |
| :--- | ---: | ---: | :--- |
| `Sandbox` | 86.349.650.553 | 80,42 GB | Khu vực làm việc: AIOS_habbit, VideoYoutube, MP2027, venv |
| `1.laptopdata` | 85.407.553.436 | 79,54 GB | Dữ liệu cá nhân & tài liệu cũ — chỉ đọc metadata |
| `.pnpm-store` | 36.617.188.997 | 34,10 GB | Junction trỏ vào `Sandbox\AIOS_habbit`, không tốn đĩa kép |
| `giao trinh day tieng nhat` | 5.203.938.893 | 4,85 GB | Ngoài phạm vi AIOS |
| `Zalo Data` | 4.535.066.406 | 4,22 GB | Dữ liệu Zalo cá nhân — ngoài phạm vi AIOS |
| `Kế hoạch AIOS_habbit` | 2.942.318.841 | 2,74 GB | Chứa file sqlite dở dang 2,74 GB và tài liệu kế hoạch |
| `c` | 1.562.144.291 | 1,45 GB | Chỉ chứa thư mục con `c\Users`, mục lạ |
| `Thư viện Calibre` | 1.532.376.453 | 1,43 GB | Sách điện tử & `metadata.db` của Calibre |
| `NVIDIA_Driver` | 722.841.504 | 0,67 GB | Bộ cài driver card đồ họa |
| `tmp` | 699.337.759 | 0,65 GB | Rác chạy test (`pytest-omp` 0,45 GB, `ux-chat-core` 0,20 GB) |
| `2.newdata` | 128.478.186 | 0,12 GB | Ngoài phạm vi AIOS |
| `phanmemPython` | 66.952.516 | 0,06 GB | Bộ cài Python cũ |
| `t` | 1.406.300 | 0,001 GB | Thư mục nhỏ ToolJet |
| `$RECYCLE.BIN` | 129 | 0,00 GB | Thùng rác hệ thống (thực tế rỗng) |
| `System Volume Information` | 0 | 0,00 GB | Thư mục hệ thống Windows (bảo vệ quyền truy cập) |
| *File gốc D:\:* `Giấy khai sinh.pdf` | 1.593.216 | 0,001 GB | File tài liệu cá nhân |
| *File gốc D:\:* `Nihongo_SouMatome_N1-Goi.pdf` | 63.741.962 | 0,059 GB | File tài liệu học tập |
| *File gốc D:\:* `Phieu-tap-to-so-1-10.pdf` | 11.371.861 | 0,011 GB | File tài liệu học tập |

> **Lưu ý về `.pnpm-store`**: Thư mục `D:\.pnpm-store\v11\projects\f211b6f0ba9b2334d1ca33631af131a8` là một liên kết Windows NTFS Junction trỏ trực tiếp tới `D:\Sandbox\AIOS_habbit`. Cả hai có cùng inode trên ổ đĩa NTFS, không chiếm dụng dung lượng vật lý hai lần.

### 2.3 Các nhánh cấp 2 lớn hơn 1 GB

| Nhánh thư mục cấp 2 | Dung lượng (Byte) | Dung lượng (GB) | Ghi chú |
| :--- | ---: | ---: | :--- |
| `1.laptopdata\3. kyocera_document` | 41.102.612.424 | 38,28 GB | Tài liệu kỹ thuật cũ (chỉ đọc metadata) |
| `.pnpm-store\v11` | 36.617.188.997 | 34,10 GB | Junction trùng với `AIOS_habbit` |
| `Sandbox\AIOS_habbit` | 36.617.188.997 | 34,10 GB | Thư mục mã nguồn và dữ liệu chính dự án AIOS |
| `Sandbox\VideoYoutube` | 29.713.883.136 | 27,67 GB | Dự án làm video (ngoài phạm vi AIOS) |
| `1.laptopdata\2. JLPT` | 21.005.244.379 | 19,56 GB | Tài liệu tiếng Nhật cá nhân |
| `1.laptopdata\1. photo_data` | 18.561.052.479 | 17,29 GB | Dữ liệu hình ảnh cá nhân |
| `Sandbox\MP2027` | 4.905.076.444 | 4,57 GB | Dự án phần mềm độc lập |
| `Zalo Data\media` | 4.162.525.253 | 3,88 GB | Dữ liệu ảnh/video Zalo |
| `Sandbox\phantichphanmemdc` | 4.251.806.675 | 3,96 GB | Dự án phân tích phần mềm độc lập |
| `1.laptopdata\4. electronic book` | 3.866.728.815 | 3,60 GB | Ebook cá nhân |
| `Sandbox\AIOS_index_split_backup` | 2.950.627.328 | 2,75 GB | Bản backup kho index pre-split ngày 03/10 |
| `Kế hoạch AIOS_habbit\aios_thu_vien` | 2.942.318.841 | 2,74 GB | Chứa file sqlite dở dang 2,74 GB và lock file |
| `Sandbox\AIOS_index_split_new` | 2.857.172.992 | 2,66 GB | 4 kho index mới sau phân tách (lsu, mom, ...) |
| `giao trinh day tieng nhat\tailieutiengnhat` | 1.681.235.739 | 1,57 GB | Tài liệu tiếng Nhật |
| `c\Users` | 1.562.144.291 | 1,45 GB | Mục lạ trên ổ D |
| `Sandbox\.venv` | 1.338.481.273 | 1,25 GB | Môi trường ảo Python ở root Sandbox |
| `Sandbox\reference_repos` | 1.328.360.243 | 1,24 GB | Kho tham khảo |
| `giao trinh day tieng nhat\giaotrinhdaytiengnhatsocap` | 1.317.927.488 | 1,23 GB | Giáo trình tiếng Nhật |
| `Sandbox\leetcode_mastery` | 1.298.775.712 | 1,21 GB | Kho luyện thuật toán |
| `Thư viện Calibre\Chua xac dinh` | 1.083.254.048 | 1,01 GB | Sách Calibre |

### 2.4 Cơ cấu bên trong `D:\Sandbox\AIOS_habbit` (nhánh > 100 MB)

| Phân vùng trong AIOS_habbit | Dung lượng (Byte) | Dung lượng (GB) | Nội dung & Mục đích |
| :--- | ---: | ---: | :--- |
| `local_runs` | 17.881.259.666 | 16,65 GB | Kết quả chạy, benchmark, cache mô hình và index |
| `models` | 5.761.883.616 | 5,37 GB | Trọng số mô hình ONNX (`bge-m3-onnx-fp32`, work-r2, ...) |
| `.git` | 2.849.292.422 | 2,65 GB | Lịch sử commit Git của repo |
| `.venv` | 2.263.914.512 | 2,11 GB | Virtual environment chính đang chạy của AIOS |
| `Tài liệu của tất cả dòng máy` | 2.069.773.612 | 1,93 GB | Tài liệu nghiệp vụ gốc (bao gồm zip Điều chỉnh) |
| `vendor` | 1.883.355.261 | 1,75 GB | Gói wheel phụ thuộc phục vụ môi trường offline |
| `.venv-rag-compat` | 1.674.487.483 | 1,56 GB | Virtual environment phụ (tương thích RAG) |
| `.venv-rag` | 1.326.346.716 | 1,24 GB | Virtual environment phụ RAG |
| `.tmp` | 305.411.512 | 0,28 GB | Cache kiểm thử tạm thời |
| `graphify-out` | 207.251.734 | 0,19 GB | Đồ thị phân tích quan hệ codebase |
| `scratch` | 123.890.447 | 0,12 GB | Thư mục nháp chứa văn bản trung gian |

---

## 3. Đối chiếu với danh mục đã biết (Verification against Pins)

| Danh mục kiểm chứng | Đường dẫn tệp trên hệ thống | Kích thước (Byte) | Mã băm SHA-256 | Kết luận đối chiếu |
| :--- | :--- | ---: | :--- | :--- |
| **Kho production máy nhà** (ghim `45eb0e07…b7c0`) | `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | 2.942.201.856 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | **KHỚP 100%** với mã ghim production máy nhà của Muse. Đang được lưu trữ an toàn trong bản backup pre-split. |
| **Bản đông trên ổ D** (ghim `062ec090…4ef8ca`) | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | 2.552.659.968 | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` | **KHỚP 100%** với điểm phục hồi rollback sau `move-index-c`. |
| **Tệp zip Điều chỉnh** (ghim `f18bbae2…18b7`) | `D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Điều chỉnh-20260905T053942Z-1-001.zip` | 858.190.286 | `f18bbae2c0c472fe063cd80543802e8677512012a8aa4606d8c3d09ca8ca18b7` | **KHỚP 100%** với ghim dữ liệu nghiệp vụ gốc. |
| **Kho index Split New (Điều tra lỗi)** | `D:\Sandbox\AIOS_index_split_new\dieu_tra_loi\library.sqlite` | 1.643.794.432 | `3bb7b10b5bb2d9345e6ba2baf95d6d6f25575639805504bda66284c36e569651` | Kho index phân tách cho nghiệp vụ điều tra lỗi. |
| **Kho index Split New (LSU)** | `D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite` | 1.155.670.016 | `5982a4f1b99a455e89d30bb87095a3ab6f4617b50325a2da10c6d8f4b3c4eabb` | Kho index phân tách cho LSU. |
| **Kho index Split New (MOM)** | `D:\Sandbox\AIOS_index_split_new\mom\library.sqlite` | 21.598.208 | `9e796f79e20ee152cb48a56815149243fddfe165e0917f0303c2bf076840d14c` | Kho index phân tách cho MOM. |
| **Kho index Split New (Tổng hợp)** | `D:\Sandbox\AIOS_index_split_new\tong_hop\library.sqlite` | 36.081.664 | `4ad4bb35a2367eda4c0a78c0459ed6cf0b0d2d8f2b22f0c36685ba95dd76e73b` | Kho index phân tách cho tài liệu tổng hợp. |
| **Mô hình ONNX fp32** | `D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32` | 2.289.625.694 | Khớp sidecar `9f81075f…` | Khớp mô hình đang dùng, giữ nguyên. |
| **Staging GPU-262** | Đặt tại ổ C (`C:\AIOS_staging_262\library.sqlite`) | 1.005.621.248 | Không đổi | Giữ nguyên theo lệnh user, không nằm trên ổ D. |

---

## 4. Bảng kiểm kê chi tiết các tệp SQLite trên ổ D

Toàn bộ các tệp `.sqlite` trên ổ D đã được quét và tính toán SHA-256 đầy đủ, chia thành các nhóm rõ ràng:

### 4.1 Nhóm kho Index chính và Cơ sở dữ liệu nghiệp vụ quan trọng

| Đường dẫn tệp SQLite | Dung lượng (MB) | Mã băm SHA-256 |
| :--- | ---: | :--- |
| `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | 2.805,90 MB | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` |
| `D:\Sandbox\AIOS_index_split_new\dieu_tra_loi\library.sqlite` | 1.567,61 MB | `3bb7b10b5bb2d9345e6ba2baf95d6d6f25575639805504bda66284c36e569651` |
| `D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite` | 1.102,10 MB | `5982a4f1b99a455e89d30bb87095a3ab6f4617b50325a2da10c6d8f4b3c4eabb` |
| `D:\Sandbox\AIOS_index_split_new\tong_hop\library.sqlite` | 34,41 MB | `4ad4bb35a2367eda4c0a78c0459ed6cf0b0d2d8f2b22f0c36685ba95dd76e73b` |
| `D:\Sandbox\AIOS_index_split_new\mom\library.sqlite` | 20,60 MB | `9e796f79e20ee152cb48a56815149243fddfe165e0917f0303c2bf076840d14c` |
| `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\workspace_chat.sqlite` | 6,84 MB | `1eaac5da18df9150114ef72eae149c4bd4c8dc45201998610e4d938575fa6224` |
| `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\workspace_chat.sqlite` | 0,09 MB | `115ca4a6b15848f2b79ca011781ee83558c3aa1d5aa8fc7592c3eaa8332aa16f` |
| `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\rag_v2_dev.sqlite` | 0,08 MB | `160a1bb80fa7311f82909a60e532cd1e8ff16f8939bc45b6123eb82b5d7ff76e` |
| `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | 2.434,41 MB | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` |
| `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\workspace_chat.sqlite` | 6,84 MB | `55afd1a9fbb216510a22abaaffce18bb849923e138851cb9a10a08fb02dc9002` |
| `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\workspace_chat.sqlite` | 0,08 MB | `f28fb95f51ba1b572ff0ad6343a1feca38d099ea4c1c97dfe633d248918bb638` |
| `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\rag_v2_dev.sqlite` | 0,08 MB | `160a1bb80fa7311f82909a60e532cd1e8ff16f8939bc45b6123eb82b5d7ff76e` |
| `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | 1.669,64 MB | `31e80a9497b3c64f8bfd7ede0233f6eaf0526f55c78d5d694bfccdaf69452fda` |
| `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\workspace_chat.sqlite` | 28,97 MB | `2cf2dcd3bad643c226f0355b7342523237a3d2392adf61f2a2d9dc9d58ea10b6` |
| `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\workspace_chat.sqlite` | 0,04 MB | `9d92acfbb3cdef78e354f166f942811eac2542b87f4f95782cb4000051ce516c` |
| `D:\Sandbox\AIOS_habbit\local_cases\library_backups\backup_tri_thuc_20260919_223202_BAK-7762385F59\library.sqlite` | 27,42 MB | `08c2b5c854b70471c7036f14456f3eedc65eee4352ba5acd7a2b269cb0095dec` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.sqlite` | 0,45 MB | `f90dcb566152a4f3186a5e2638a9c0b5c8a26e58dcf2bb28b305df923aaa4720` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v8-to-v9.sqlite` | 0,42 MB | `daa0f23f031648ab7ab0e66de83703cf1e127e366c94a0db1244687c243c052d` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v7-to-v8.sqlite` | 0,27 MB | `12106cbc0085536ab5e17a943501f86183efc1b1446953b7ad6bdda7f425040d` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v6-to-v7.sqlite` | 0,18 MB | `60d4a7c42e99c840e288966baa2f33a883ae8e5f9d68a6b0b66111a5821c2f9f` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v5-to-v6.sqlite` | 0,15 MB | `09adabc3ab281dca8073ed7e2181a8cb76a89e90dc7d3b925c84cf733e1bf4fd` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v4-to-v5.sqlite` | 0,12 MB | `ec80a68e6625d78677016e344c079967484d195e116ac79608c1af66b11934b0` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v3-to-v4.sqlite` | 0,10 MB | `0da56107358f0ea8ea04d8065b99f987042ec0627abd091c0a35d1ddc925aa18` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v2-to-v3.sqlite` | 0,07 MB | `196dacea5765740949f1d1b70f174ebca232f52e76a0cea2989e12759b1f898d` |
| `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite` | 0,11 MB | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` |
| `D:\Sandbox\AIOS_habbit\local_cases\staging_enrichment.sqlite` | 0,09 MB | `4ecc3d7a2561b6bea73f42c0ada2f648249ff79bd26c4225bdc0363fc9d68f00` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_chat\store.sqlite` | 0,00 MB | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `D:\Sandbox\AIOS_habbit\local_cases\workspace_chat\collections\tri_thuc\line_events.sqlite` | 0,02 MB | `5dcff30b0c404a2a8fd4a9cae5691ec2b2bf589d4a8af4a8112a573a6bd8ba4c` |
| `D:\Sandbox\AIOS_habbit\src\local_cases\workspace_cases.sqlite` | 0,26 MB | `b442208c636efaaee96ce1abefa528de3daf8fa1f2a1932fda80a4cd51eac543` |
| `D:\Sandbox\AIOS_habbit\src\local_cases\production_prediction.sqlite` | 0,04 MB | `4c6f95453e71bd1da9d3db36799c7068e0a5fafcc55b2504268080b7a566b60f` |

### 4.2 Nhóm chạy thử nghiệm và Cache Benchmark (trong `local_runs\`)

| Đường dẫn tệp SQLite | Dung lượng (MB) | Mã băm SHA-256 |
| :--- | ---: | :--- |
| `...\battle_rag_v2_index_cache\...\rag_v2_dev.sqlite` | 144,53 MB | `e2479f72821c5cd5d2dc330da97c68ae9a5487f80cab4035b9da8016a78cd068` |
| `...\gate_h_selected_profile_current\...\rag_v2_dev.sqlite` | 83,30 MB | `310fcf7c7f7d739aa2c1bfde558ff31942e7c61385392ebd828bad138d47a1d0` |
| `...\gate_h_selected_profile_current_rerun\...\rag_v2_dev.sqlite` | 83,29 MB | `a026c681532f1a8b0f27fbdd0a96deacec40a10ce69aeb142657396bf3b3abc2` |
| `...\gate_h_selected_profile_compacted_batch4_corrected\...\rag_v2_dev.sqlite` | 66,95 MB | `08ab185db73ed044b673f9caa3535ab8022633cb44e94ca7b69c58b7b8040157` |
| `...\gate_h_selected_profile_compacted_batch4_corrected\lexical...\rag_v2_dev.sqlite` | 57,65 MB | `dd97d32db3507b4b0e40c7309b57f6ca64b456856a8510eb4e1d62679fc00d6d` |
| `...\gate_h_selected_profile_compacted_batch4\lexical...\rag_v2_dev.sqlite` | 57,65 MB | `d1b6922175bda56dd0e625dec38f822f8c6acbcebb066d5fc321335dde776918` |
| `...\gate_h_selected_profile_compacted\lexical...\rag_v2_dev.sqlite` | 57,64 MB | `08b5ee0ee5f9087ed3c8059ca1389ee2a6aacbd8fe056aa66f205adaa5c7deca` |
| `...\gate_h_selected_profile_restore\...\lexical_baseline...\rag_v2_dev.sqlite` | 65,79 MB | `f67a07f691a5448c55ed0d050d3fa5a82b6b1fc54d139012d8ed320ed825198d` |
| `...\gate_h_selected_profile_restore\...\rag_v2_dev.sqlite` | 6,15 MB | `7c6945e39b960be74d2e9040250d0e7c83ce0cc7a4c0632149231a4297c40d55` |
| `...\battle_workspace_stage_cache\...\workspace_chat.sqlite` | 46,37 MB | `4b874fb0f38729f9d7464de0bcd05426bf4fcb38fe5f8f42b02113c54e4a7845` |
| `...\battle_workspace_stage_cache\...\before_actual_matecon_ui_repair.sqlite` | 38,28 MB | `ac859ead2a010a27cc947c1bb17bfc6d33d6eae69e752d5013b1ded74bdc1abe` |
| `...\battle_workspace_stage_cache\...\before_matecon_vector_repair.sqlite` | 37,61 MB | `38fc425355499bb209f08ce2afecb6acff28195891c62dcaa27d4ba2d7a358ab` |
| `...\battle_workspace_stage_cache\...\e94ab2ee6914...\workspace_chat.sqlite` | 14,18 MB | `1abea261993b2bd8f3ed650cde6ebc468ea548219445f53a61c1c0e8621b193a` |
| `...\bq01_bq02_adapter_diagnostic\...\workspace_chat.sqlite` | 17,77 MB | `3d062148304795f073cd5605aa3e1f0165567988a2eb39c59b95d1c6a482890b` |
| `...\thread_answer_probe\runtime\rag_v2_dev.sqlite` | 3,53 MB | `9817cc17363bda9db2e7d6b64f1981febbb26d869449706c257382e648649250` |
| `...\chunk_evaluation\...\chunk_eval.sqlite` (10 tệp run e1, e2, e5) | 1,77–2,15 MB | Đầy đủ mã băm từng file trong hồ sơ đính kèm |
| `...\matecon_semantic_diagnostic_run\...\workspace_chat.sqlite` | 1,92 MB | `e35a4c406301b85bcbd7ade7d8dd022ca748535541451ae0939f5f6a7bbfc681` |
| `...\speed_smoke_*\runtime\rag_v2_dev.sqlite` (3 tệp) | 0,61–0,87 MB | Đầy đủ mã băm |
| `...\evidence_case_loop_goal\...\lsu_m1_verify.sqlite` | 0,05 MB | `2d54483a9a838be29e8c4600109fec9c394c8e718b528b16a24be516584cb065` |
| `...\evidence_case_loop_goal\...\test_m2_rehearsal.sqlite` | 0,05 MB | `615af4668f37e188d13e2f22969e318a480b6992878caa5e549661e7c61a03d6` |

### 4.3 Nhóm file SQLite trong thư mục tạm `D:\tmp\pytest-omp` và `.tmp\`

- **`D:\tmp\pytest-omp`**: 593 tệp SQLite sinh ra từ các phiên chạy pytest, tổng kích thước 452 MB (474.152.000 byte). Toàn bộ 593 tệp đã được băm SHA-256 hoàn chỉnh vào tệp dữ liệu xác minh `$env:TEMP\tmp_pytest_sqlite_hashes.csv`.
- **`D:\Sandbox\AIOS_habbit\.tmp`**: Gồm `real_10081.sqlite` (145,63 MB | `e02ed7ca...`), `real_9919.sqlite` (144,53 MB | `e2479f72...`), và các tệp sqlite kiểm thử ngắn hạn.

---

## 5. Kiểm kê các mục liên quan AIOS khác

### 5.1 Thư mục sao lưu (Backups)

- `D:\Sandbox\AIOS_index_split_backup`: 2.950.627.328 byte (2,75 GB), chứa bản sao lưu toàn bộ kho index trước phân tách ngày 2026-10-03 (bao gồm kho production `45eb0e07...b7c0`).
- `D:\Sandbox\AIOS_habbit\local_cases\library_backups`: 28.753.920 byte, chứa bản backup `backup_tri_thuc_20260919_223202_BAK-7762385F59`.
- Chuỗi sao lưu `workspace_cases.backup-v2-to-v3` đến `v8-to-v9` trong `local_cases`: Tổng cộng ~1,5 MB.

### 5.2 Tệp nén (Zip / Tar / Rar)

- `D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Điều chỉnh-20260905T053942Z-1-001.zip`: 858.190.286 byte, SHA-256 `f18bbae2c0c472fe063cd80543802e8677512012a8aa4606d8c3d09ca8ca18b7`. Khớp 100% dữ liệu gốc, bắt buộc giữ nguyên.
- Các file nén khác ngoài AIOS: file zip giáo trình tiếng Nhật (`tailieutiengnhat.zip`), bộ nén ComfyUI (`ComfyUI_windows_portable_nvidia.7z`), tệp test trong `leetcode_mastery`. Tuyệt đối không đụng vào.

### 5.3 Thư mục trọng số mô hình (Model Weights)

- `D:\Sandbox\AIOS_habbit\models`: Tổng cộng 5,37 GB.
  + `bge-m3-onnx-fp32`: 2.289.625.694 byte (khớp sidecar `9f81075f…`, mô hình chính đang dùng).
  + `.bge-m3-onnx-work-r2`: 2.289.606.933 byte (bản làm việc gần bằng fp32).
  + `bge-m3-onnx-int8`: 591.786.329 byte.
  + `bge-m3-onnx-optimum`: 590.861.845 byte.
- `D:\Sandbox\AIOS_habbit\local_runs\retrieval_models`: Tổng cộng 4,59 GB.
  + `bge-m3-5617a9f\pytorch_model.bin`: 2.165,93 MB (~2,12 GB).
  + `bge-reranker-v2-m3\model.safetensors`: 2.165,86 MB (~2,12 GB).

### 5.4 Tệp nhật ký (Logs)

- Không có bất kỳ tệp `.log` nào vượt quá 10 MB trên toàn bộ ổ D.
- Tệp văn bản nguồn materialized lớn: Có 4 tệp `.txt` trong `local_runs` và `scratch` (~25 MB/tệp).

---

## 6. Các mục bất thường hoặc chưa từng ghi nhận

1. **Tệp SQLite tạm lớn và bị khóa trong thư mục Kế hoạch**:
   - `D:\Kế hoạch AIOS_habbit\aios_thu_vien\.library.sqlite.ba9796c9808548f7a844f182c68e7d35.tmp`: Kích thước đúng bằng kho production (2.942.201.856 byte), nhưng có SHA-256 là `aae0943e2c568763208fd72095339cfebe84e24b88fe696ead21db4c22ee5425` (khác kho production).
   - Kèm theo: `.aios-library-writer.lock`, `.aios-library-writer.info` và journal file từ ngày 2026-10-02. Đây là dấu tích của một tiến trình ghi index dở dang trước đây bị gián đoạn.
2. **Junction pnpm trỏ chéo**:
   - `D:\.pnpm-store\v11\projects\f211b6f0ba9b2334d1ca33631af131a8`: Là NTFS Junction trỏ thẳng tới `D:\Sandbox\AIOS_habbit`. Cần lưu ý để tránh các công cụ quét tự động tính trùng dung lượng 34,1 GB.
3. **Thư mục lạ `D:\c\Users`**:
   - Kích thước 1,45 GB, chỉ chứa tài khoản Public của Windows sao lưu dở, không liên quan đến AIOS.
4. **Môi trường ảo ngoài root `D:\Sandbox\.venv`**:
   - Chiếm 1,25 GB, nằm bên ngoài repo `AIOS_habbit` (trong khi `AIOS_habbit` đã có `.venv` riêng 2,11 GB).
5. **Rác chạy kiểm thử `D:\tmp\pytest-omp`**:
   - Chiếm 452 MB với 593 file SQLite tạm phát sinh trong quá trình chạy test tự động.

---

## 7. Đề xuất danh sách dọn dẹp (Chỉ đề xuất, KHÔNG tự ý thực hiện)

Danh sách được sắp xếp nghiêm ngặt theo 4 cấp độ an toàn từ cao nhất đến thận trọng nhất. Việc thực hiện chỉ được diễn ra khi người dùng phê duyệt rõ ràng.

### Mức 1: Rác tạm và Cache kiểm thử (Rất an toàn — Đề xuất dọn đầu tiên)

| Hạng mục đề xuất | Đường dẫn | Dung lượng dự kiến thu hồi | Ghi chú an toàn |
| :--- | :--- | ---: | :--- |
| File sqlite tạm test | `D:\tmp\pytest-omp` | ~0,45 GB (452 MB) | Toàn bộ 593 file sqlite sinh ra từ pytest, an toàn 100% |
| Cache bench & test | `D:\Sandbox\AIOS_habbit\.tmp` | ~0,28 GB (284 MB) | Chứa `real_10081.sqlite`, `real_9919.sqlite` tạm |
| Profile chrome tạm | `D:\tmp\ux-chat-core` | ~0,20 GB (199 MB) | Thư mục tạm Chrome testing |
| Thư mục nháp trung gian | `D:\Sandbox\AIOS_habbit\scratch` | ~0,12 GB (115 MB) | Chứa file text materialize nháp |
| **Tổng mức 1** | | **~1,05 GB** | **Xóa an toàn tuyệt đối, không ảnh hưởng code hay dữ liệu** |

### Mức 2: File dở dang và Cache chạy cũ (An toàn cao — Cần xác nhận người dùng)

| Hạng mục đề xuất | Đường dẫn | Dung lượng dự kiến thu hồi | Ghi chú an toàn |
| :--- | :--- | ---: | :--- |
| File tạm ghi dở 2,74GB | `D:\Kế hoạch AIOS_habbit\aios_thu_vien\.library.sqlite.*.tmp` | ~2,74 GB (2.942 MB) | File ghi dở ngày 02/10 kẹt lock file. Đã xác nhận SHA khác production |
| Cache đánh giá chunk cũ | `AIOS_habbit\local_runs\chunk_evaluation` | ~0,02 GB | Các run e1, e2, e5 cũ không còn dùng |
| Cache profile gate cũ | `AIOS_habbit\local_runs\gate_h_*` | ~0,50 GB | Các baseline compact cũ |
| Cache battle cũ | `AIOS_habbit\local_runs\battle_*` | ~0,30 GB | Stage cache cũ |
| **Tổng mức 2** | | **~3,56 GB** | **Thu hồi lượng lớn dung lượng sau khi xác nhận** |

### Mức 3: Môi trường ảo (Virtualenv) trùng lặp

| Hạng mục đề xuất | Đường dẫn | Dung lượng dự kiến thu hồi | Ghi chú an toàn |
| :--- | :--- | ---: | :--- |
| Venv ngoài root | `D:\Sandbox\.venv` | ~1,25 GB | Cần kiểm tra xem có dự án nào ngoài AIOS dùng không |
| Venv tương thích cũ | `AIOS_habbit\.venv-rag-compat` | ~1,56 GB | Chỉ dọn nếu hệ thống đã thống nhất dùng `.venv` chính |
| Venv rag cũ | `AIOS_habbit\.venv-rag` | ~1,24 GB | Chỉ dọn nếu đã hợp nhất vào `.venv` chính |
| **Tổng mức 3** | | **~4,05 GB** | **Cần xác nhận kịch bản chạy trước khi xóa** |

### Mức 4: Kho sao lưu index cũ (Chỉ sau khi kiểm tra toàn vẹn và có lệnh duyệt)

| Hạng mục đề xuất | Đường dẫn | Dung lượng dự kiến thu hồi | Ghi chú an toàn |
| :--- | ---: | ---: | :--- |
| Kho backup pre-split | `D:\Sandbox\AIOS_index_split_backup` | ~2,75 GB | Chứa kho production gốc ngày 03/10 (`45eb0e07...b7c0`). **Chỉ dọn sau khi hệ thống đã chuyển 100% sang 4 kho split mới và đã có backup ngoại vi.** |
| **Tổng mức 4** | | **~2,75 GB** | **Quyết định độc quyền của người dùng** |

### Các mục TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP ĐỤNG ĐẾN:
- Toàn bộ dữ liệu trong `D:\1.laptopdata` (79,54 GB) và `D:\Zalo Data` (4,22 GB).
- Các dự án phần mềm khác: `Sandbox\VideoYoutube`, `Sandbox\MP2027`, `Sandbox\phantichphanmemdc`.
- Dữ liệu nghiệp vụ gốc: `D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy` (gồm zip Điều chỉnh).
- 4 kho index mới đang phục vụ: `D:\Sandbox\AIOS_index_split_new` (`dieu_tra_loi`, `lsu`, `mom`, `tong_hop`).
- Trọng số mô hình chính: `models\bge-m3-onnx-fp32` và `local_runs\retrieval_models`.

---

## 8. Kết luận nghiệm thu

- [x] Đã hoàn thành quét và lập cây thư mục cấp 1-2 của toàn bộ ổ D kèm dung lượng chính xác.
- [x] Đã kiểm kê và tính toán SHA-256 đầy đủ 100% các file SQLite trên ổ D, không bỏ sót tệp nào.
- [x] Đã đối chiếu chính xác kho production máy nhà (`45eb0e07...b7c0`) và xác nhận bảo toàn dữ liệu staging GPU-262.
- [x] Đã phát hiện và phân tích mục lạ (file tmp 2,74GB trong thư mục Kế hoạch, Junction pnpm, rác pytest).
- [x] Đã lập danh sách đề xuất dọn dẹp 4 mức phân cấp rõ ràng, tuân thủ nguyên tắc chỉ đề xuất, không tự ý can thiệp.
- [x] Không có bất kỳ thao tác xóa, sửa hay ghi đè nào lên các tệp dữ liệu trên ổ D trong suốt quá trình quét.
