# Báo cáo INDEX-SPLIT-HOME — dừng ở dry-run

- Trạng thái: **DỪNG đúng Bước 1 của vé.** Không tách thật, không đổi app, không bật cờ định tuyến.
- Máy: `h410asrock` (máy nhà). Không đụng PC0575. Không merge `main`. Không sửa code.
- Ngày: 2026-10-03. Nhánh: `phieu-viec/rag-fix1`.
- Cổng gate: watcher LAUNCH 1/4 lúc 21:01:05. Điều kiện mở đã tới (Phase A có sẵn, đúng máy nhà, kho production còn). Không dùng nhánh 4 lần / `cho-muse` lúc nhận vé.
- Lý do `cho-muse` lúc đóng mốc này: vé bắt dừng khi danh sách confidence thấp lớn bất thường. 453/889 tài liệu dưới 0,40 — chờ user rà trước khi tách thật.

## 1. Bước 0 — backup và dấu kho cũ

Đã dừng app chat (streamlit + worker BGE) trước khi đo, để không có tiến trình ghi kho.

| Mục | Trước |
| --- | --- |
| File | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` |
| Byte | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` |

SHA khớp ghim các vé trước (`merge-home`, `hodap-home`, `scan-o-d`).

Backup: `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre` — robocopy 84 file, 2,747 GB, 0 failed (mã thoát robocopy 1 = đã copy). SHA file `library.sqlite` trong backup **khớp từng byte** với bản trên ổ C.

Ổ C còn khoảng 4 GB trống. Chưa ghi kho mới.

## 2. Dry-run

Lệnh (thêm `--allow-production` vì code chặn đường production **trước** nhánh dry-run; dry-run vẫn không ghi file — thư mục `C:\AIOS_index_split_preview` không được tạo):

```
python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "C:\AIOS_index_split_preview" --dry-run --allow-production
```

Tổng: **889 document / 149.800 chunk** — khớp kiểm kê.

| Khối | Document | Chunk | Độ tin cậy trung bình | Confidence < 0,40 |
| --- | ---: | ---: | ---: | ---: |
| LSU | 101 | 76.501 | 0,799 | 0 |
| Điều tra lỗi | 732 | 71.597 | 0,288 | 453 |
| MOM | 56 | 1.702 | 0,762 | 0 |

## 3. Vì sao dừng

- Ngưỡng thấp của công cụ: 0,40.
- **453 tài liệu** dưới ngưỡng (51% kho). Trong đó **451 confidence = 0** (không có tín hiệu từ khóa, gán mặc định vào Điều tra lỗi) và **2** tài liệu chỉ khớp yếu từ "lỗi".
- Phase A đã cảnh báo khoảng 496 document canary mất dấu thư mục sẽ rơi confidence 0 và **cần người rà trước khi coi là xong**. Số đo này nằm trong vùng đó, nhưng lớn đến mức gắn nhầm nửa kho vào khối Điều tra lỗi nếu tách ngay.
- Vé nói: dừng để user rà danh sách confidence thấp nếu số lượng lớn bất thường. OMP không chạy Bước 2 (tách thật).

Đuôi file của 453 tài liệu thấp:

| Đuôi | Số tài liệu |
| --- | ---: |
| `.xlsx` | 200 |
| `.pdf` | 140 |
| `.txt` | 62 |
| `.png` | 22 |
| `.msg` | 15 |
| `.xls` | 4 |
| `.xlsm` | 3 |
| `.bmp` | 2 |
| `.html` | 2 |
| `.csv` | 2 |
| `.pptx` | 1 |

Lý do:

- 451 — tài liệu: không có tín hiệu từ khóa; gán mặc định minh bạch
- 2 — tài liệu: khớp từ khóa Điều tra lỗi(lỗi×1)

Danh sách đủ 453 dòng (cùng nội dung file `D:\Sandbox\AIOS_index_split_backup\dry-run-low-20261003.json`, không đưa JSON vào git):

| # | document_id | khối gán | confidence | chunk | tên nguồn |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | `wsc-174cb6d090816f2fbb93dd00` | Điều tra lỗi | 0.000 | 244 | 02XC_機能定義書_JAM一覧 (1).xls |
| 2 | `wsc-7773b3b4c507e6fb58acfee8` | Điều tra lỗi | 0.000 | 192 | 02XC_自己診断表示一覧表-Iris2020 VN.xls |
| 3 | `wsc-256ae84f2d121c011f1bb063` | Điều tra lỗi | 0.000 | 200 | 02XC_自己診断表示一覧表.xls |
| 4 | `wsc-109b90a7c0a14f5b227ea16a` | Điều tra lỗi | 0.000 | 6 | 20260310 KDTVN IRIS2024 文字顯示異常03.30 (1).pdf |
| 5 | `wsc-921a2daef8ecf13210a5c3ff` | Điều tra lỗi | 0.000 | 6 | 20260310 KDTVN IRIS2024 文字顯示異常03.30 (1).pdf |
| 6 | `wsc-d2f571952e88b9b3305826e0` | Điều tra lỗi | 0.000 | 13 | 234 5simtape.png |
| 7 | `wsc-8fa4fe038d9a05d81b9eb528` | Điều tra lỗi | 0.000 | 14 | 234 l1.1.png |
| 8 | `wsc-4ab9350286ad8e78809e7dc3` | Điều tra lỗi | 0.000 | 14 | 234 l2.png |
| 9 | `wsc-5953d3fff1a73f1068d08192` | Điều tra lỗi | 0.000 | 14 | 234 master.png |
| 10 | `wsc-9abdeef3c1bfc6c3a09df1e7` | Điều tra lỗi | 0.000 | 13 | 234.png |
| 11 | `wsc-8e77034be821a0defc399696` | Điều tra lỗi | 0.000 | 14 | 235 l1.png |
| 12 | `wsc-57a940899f40e39ec67b9661` | Điều tra lỗi | 0.000 | 14 | 235 l2.png |
| 13 | `wsc-7f5d66631ea984eb8dfb4614` | Điều tra lỗi | 0.000 | 14 | 235 master.png |
| 14 | `wsc-d90f8acf1edfbd5f21ef80a4` | Điều tra lỗi | 0.000 | 11 | 235.png |
| 15 | `wsc-4c2f33de97e314843c99e69b` | Điều tra lỗi | 0.000 | 13 | 235l2.png |
| 16 | `wsc-c86111fa5390875aaa5fefb4` | Điều tra lỗi | 0.000 | 14 | 238 l1.png |
| 17 | `wsc-527f8bd013650df67796b8bc` | Điều tra lỗi | 0.000 | 14 | 238 l2.png |
| 18 | `wsc-a010f8f4fc78f6eabbaf4dff` | Điều tra lỗi | 0.000 | 14 | 238 master.png |
| 19 | `wsc-579b74f1c047f8145d879382` | Điều tra lỗi | 0.000 | 13 | 238.png |
| 20 | `wsc-ef2a484ca7dce3af9666b643` | Điều tra lỗi | 0.000 | 13 | 239.png |
| 21 | `wsc-527ade7fb230338f3df478d9` | Điều tra lỗi | 0.000 | 13 | 2ND-7002_Iris OPTION検査_ブロック図Ver.2.2_201223.pdf |
| 22 | `wsc-babbcc717aab08dcbb2feeb6` | Điều tra lỗi | 0.000 | 17 | 2ND-7002_Iris OPTION検査_ブロック図Ver.2.2_201223.pdf |
| 23 | `wsc-71a1146df86dd76eaec6d8da` | Điều tra lỗi | 0.000 | 55 | 2XC_PA1166B_FRONT DRIVE_HIGH_回路図_190717.pdf |
| 24 | `wsc-8458ecd9bd71aa7161285f5e` | Điều tra lỗi | 0.000 | 48 | 2XC_PA1166B_FRONT DRIVE_HIGH_回路図_190717.pdf |
| 25 | `wsc-18003f087932b2e7e326c931` | Điều tra lỗi | 0.000 | 396 | 302L745040.pdf |
| 26 | `wsc-26df7c4233241be5cc7c83d6` | Điều tra lỗi | 0.000 | 555 | 302L745040.pdf |
| 27 | `wsc-34567e4bd564d0b1d856f2ef` | Điều tra lỗi | 0.000 | 195 | 302XC45030 full.pdf |
| 28 | `wsc-6d56f89f94f2e1ea664ebbb0` | Điều tra lỗi | 0.000 | 174 | 302XC45030 full.pdf |
| 29 | `wsc-8012535065df01cd95422632` | Điều tra lỗi | 0.000 | 18 | 302XC47060-03.pdf |
| 30 | `wsc-c2719d3da28bcf84b92af45c` | Điều tra lỗi | 0.000 | 17 | 302XC47060-03.pdf |
| 31 | `wsc-a92af1dd4c6ecf14b51a94d5` | Điều tra lỗi | 0.000 | 4 | 302XC47090-02.pdf |
| 32 | `wsc-cfa5c7450e44172eb98c0089` | Điều tra lỗi | 0.000 | 4 | 302XC47090-02.pdf |
| 33 | `wsc-6cf9ca1a19e5eeffa16e18af` | Điều tra lỗi | 0.000 | 6 | 302XC47100_03.pdf |
| 34 | `wsc-ed3c3e9dadcef7c82c259e0d` | Điều tra lỗi | 0.000 | 7 | 302XC47100_03.pdf |
| 35 | `wsc-100d365213cfa22b7592d056` | Điều tra lỗi | 0.000 | 26 | 302XC47120-06.pdf |
| 36 | `wsc-f3f710aba8cf2bba652dcdd2` | Điều tra lỗi | 0.000 | 23 | 302XC47120-06.pdf |
| 37 | `wsc-5b469982b6dea2328aa2def4` | Điều tra lỗi | 0.000 | 6 | 302XC47150_03.pdf |
| 38 | `wsc-9d4730c1e88feb3aa3294e8c` | Điều tra lỗi | 0.000 | 6 | 302XC47150_03.pdf |
| 39 | `wsc-69155f3b8385a4e8fb94a3f9` | Điều tra lỗi | 0.000 | 4 | 302XC47210-01.pdf |
| 40 | `wsc-6d6398a3ab79894c5425393f` | Điều tra lỗi | 0.000 | 4 | 302XC47210-01.pdf |
| 41 | `wsc-419a613474ecac902ecfeac6` | Điều tra lỗi | 0.000 | 22 | 302XC47220-04.pdf |
| 42 | `wsc-8b90ef2327f3335eab9893f6` | Điều tra lỗi | 0.000 | 24 | 302XC47220-04.pdf |
| 43 | `wsc-13e7af8eda332bcf0a69d92e` | Điều tra lỗi | 0.000 | 49 | 302XC47250-01.pdf |
| 44 | `wsc-a1b7ec2841bc80862f0f785b` | Điều tra lỗi | 0.000 | 57 | 302XC47250-01.pdf |
| 45 | `wsc-7aadc03f0430574d2dd9f4b4` | Điều tra lỗi | 0.000 | 20 | 302XC47260-03.pdf |
| 46 | `wsc-ac4e891ca1aeee34156767c8` | Điều tra lỗi | 0.000 | 23 | 302XC47260-03.pdf |
| 47 | `wsc-899180f7d2efddff1577fac6` | Điều tra lỗi | 0.000 | 206 | 302XD45010-full.pdf |
| 48 | `wsc-fe4b3598210150f6b3c2316b` | Điều tra lỗi | 0.000 | 164 | 302XD45010-full.pdf |
| 49 | `wsc-684b23ed428197535ab6823a` | Điều tra lỗi | 0.000 | 18 | 302XD47060-04.pdf |
| 50 | `wsc-a9448dfc107ebbc20dd951ed` | Điều tra lỗi | 0.000 | 16 | 302XD47060-04.pdf |
| 51 | `wsc-af66518377381816dd1f1941` | Điều tra lỗi | 0.000 | 20 | 302XD47070-04.pdf |
| 52 | `wsc-e1992e61a7fb5057fca73a09` | Điều tra lỗi | 0.000 | 23 | 302XD47070-04.pdf |
| 53 | `wsc-5782d41b7dde1cbdb668c31c` | Điều tra lỗi | 0.000 | 28 | 302XD47250-01.pdf |
| 54 | `wsc-bd1066a5ccf93d36bc34cd79` | Điều tra lỗi | 0.000 | 30 | 302XD47250-01.pdf |
| 55 | `wsc-e5fe0eb9570af0dabd30002c` | Điều tra lỗi | 0.000 | 17 | 302XD47260-03.pdf |
| 56 | `wsc-ef468f2d557a12cfa1bc387e` | Điều tra lỗi | 0.000 | 19 | 302XD47260-03.pdf |
| 57 | `wsc-6dfabb03ef6bb4e15b9ebf5a` | Điều tra lỗi | 0.000 | 10 | 302XF47060-04.pdf |
| 58 | `wsc-f610bd8daad0c8cda9ef8f74` | Điều tra lỗi | 0.000 | 9 | 302XF47060-04.pdf |
| 59 | `wsc-94ee483fbfe75e097fe2007b` | Điều tra lỗi | 0.000 | 57 | 302XF47250-01.pdf |
| 60 | `wsc-f0301a7b95e757da242e62cc` | Điều tra lỗi | 0.000 | 46 | 302XF47250-01.pdf |
| 61 | `wsc-2777b69bb78a5861fed22523` | Điều tra lỗi | 0.000 | 38 | 303V401010_main PF.pdf |
| 62 | `wsc-92b0281626781ec129e28804` | Điều tra lỗi | 0.000 | 29 | 303V401010_main PF.pdf |
| 63 | `wsc-0ac3ea307df810908f4446a5` | Điều tra lỗi | 0.000 | 82 | 3V2ND19040-MOUNT LD BLOCK  LOT 18.8.2026.xlsx |
| 64 | `wsc-582a992dc46566ab198dabe2` | Điều tra lỗi | 0.000 | 69 | 3V2ND19040-MOUNT_LD_BLOCK__LOT_18.8.2026.xlsx |
| 65 | `wsc-907f7112286b9826029a57ce` | Điều tra lỗi | 0.000 | 46 | 3V2XC01141.pdf |
| 66 | `wsc-fac9c625efe24ea6261f13ac` | Điều tra lỗi | 0.000 | 47 | 3V2XC01141.pdf |
| 67 | `wsc-297dea46dc11bddb9241f659` | Điều tra lỗi | 0.000 | 8 | 3V2XC47080-01.pdf |
| 68 | `wsc-9948c7d3e84794a5eb0b21a2` | Điều tra lỗi | 0.000 | 4 | 3V2XC47080-01.pdf |
| 69 | `wsc-4a04fdb87f93736eae5af513` | Điều tra lỗi | 0.000 | 57 | 3V2XD47050-02.pdf |
| 70 | `wsc-fc43a654334a07af70edeed7` | Điều tra lỗi | 0.000 | 45 | 3V2XD47050-02.pdf |
| 71 | `wsc-c3b3f8a1b533df3cd353801d` | Điều tra lỗi | 0.000 | 51 | 3V2XD47090_01.pdf |
| 72 | `wsc-edf9817dd705508ae5986f4e` | Điều tra lỗi | 0.000 | 44 | 3V2XD47090_01.pdf |
| 73 | `wsc-5719cc700a115abeb9933116` | Điều tra lỗi | 0.000 | 46 | 3V2XF47050-06.pdf |
| 74 | `wsc-e33ffbbaef18063f6f600ce9` | Điều tra lỗi | 0.000 | 58 | 3V2XF47050-06.pdf |
| 75 | `wsc-8cf2ddcf89f5446ef9462d6d` | Điều tra lỗi | 0.000 | 65 | 3V3TC01010_Drive Assy.pdf |
| 76 | `wsc-e0138cd831766c178190b731` | Điều tra lỗi | 0.000 | 49 | 3V3TC01010_Drive Assy.pdf |
| 77 | `wsc-ab3ed0277c9e671ac3587bd0` | Điều tra lỗi | 0.000 | 591 | 6778_CyCav_F_2025.11.13.xlsm |
| 78 | `wsc-9a89ee076ef452c7837435d1` | Điều tra lỗi | 0.000 | 24 | 6778_CyCav_G_2025.11.13.xlsm |
| 79 | `wsc-006998d9fbb692500808f741` | Điều tra lỗi | 0.000 | 8 | 7PA0547CJF_回路図20181113_KUIO.pdf |
| 80 | `wsc-e802f04300d4c26648375d6e` | Điều tra lỗi | 0.000 | 7 | 7PA0547CJF_回路図20181113_KUIO.pdf |
| 81 | `wsc-654ff83db5c2c37a1289ec7b` | Điều tra lỗi | 0.000 | 9 | 7PA1111B_回路図_180423.pdf |
| 82 | `wsc-dd364fb3d90ed49714841f9e` | Điều tra lỗi | 0.000 | 10 | 7PA1111B_回路図_180423.pdf |
| 83 | `wsc-4fa5190e1a384777e8706a38` | Điều tra lỗi | 0.000 | 56 | 7PA1187DCZ 回路図.pdf |
| 84 | `wsc-9cfd3a3d1b9c3cf75af0fe8e` | Điều tra lỗi | 0.000 | 67 | 7PA1187DCZ 回路図.pdf |
| 85 | `wsc-facdca00057b4d5f43dcf980` | Điều tra lỗi | 0.000 | 45 | 7PA1204BDS.pdf |
| 86 | `wsc-fb69867468c0def75120661d` | Điều tra lỗi | 0.000 | 44 | 7PA1204BDS.pdf |
| 87 | `wsc-e49f4e80655a7fcecf48ea70` | Điều tra lỗi | 0.000 | 24 | 7PA1216A_回路図_190729.pdf |
| 88 | `wsc-ec42cf548c5b74e535a8048a` | Điều tra lỗi | 0.000 | 28 | 7PA1216A_回路図_190729.pdf |
| 89 | `wsc-230baee36cd917aefc37d5e9` | Điều tra lỗi | 0.000 | 116 | AllItems.html |
| 90 | `wsc-aad17f536dcb37525a8599ea` | Điều tra lỗi | 0.000 | 14 | AllItems.html |
| 91 | `wsc-2f4f337f46c13cb099d8a2eb` | Điều tra lỗi | 0.000 | 10 | ALPHARD2_2N4_CURRENTAVE_PP_01_最新回路図_302N401190.pdf |
| 92 | `wsc-c84d8083f0c13c67cd462ee9` | Điều tra lỗi | 0.000 | 11 | ALPHARD2_2N4_CURRENTAVE_PP_01_最新回路図_302N401190.pdf |
| 93 | `wsc-1e233aa1ef54e266c51e4d7d` | Điều tra lỗi | 0.000 | 11 | Bong_TAPE_COVER_GLASS_Rev.00_VN.pptx |
| 94 | `wsc-0dfeef5924e6ac4bce171ccf` | Điều tra lỗi | 0.000 | 9 | Copy of 【DRBFM】Iris2020_C6610_coupling_new.xlsx |
| 95 | `wsc-5cbd8cb62a75bcfba3ed7a3f` | Điều tra lỗi | 0.000 | 2 | Copy of 【DRBFM】Iris2020_C6610_coupling_new.xlsx |
| 96 | `wsc-7a505c0cbff07a91486d0604` | Điều tra lỗi | 0.000 | 24 | Cy用治具の修理_6778_CyCav_F.xlsm |
| 97 | `wsc-1d4ffd410136f2997f24b84e` | Điều tra lỗi | 0.000 | 114 | DP IF ASSY_7PA1153CJF.pdf |
| 98 | `wsc-671647b1c8d9a58a095d1a5c` | Điều tra lỗi | 0.000 | 97 | DP IF ASSY_7PA1153CJF.pdf |
| 99 | `wsc-d819b58680e78b57fa1462ba` | Điều tra lỗi | 0.000 | 1 | dvu_prt_engpage_info_log.csv |
| 100 | `wsc-c6c395c5962dbd9a7cd35661` | Điều tra lỗi | 0.000 | 6 | dvu_prt_vdbg_docpg.csv |
| 101 | `wsc-2340acdb03f71fc0a04fd77f` | Điều tra lỗi | 0.000 | 500 | dữ liệu tổng hợp.xlsx |
| 102 | `wsc-9b0f3c85c73cf74b5dbd8bef` | Điều tra lỗi | 0.000 | 98 | Dữ liệu tổng hợp.xlsx |
| 103 | `wsc-8a1d6cc88fb222f53250c8ec` | Điều tra lỗi | 0.000 | 143 | ENGINE_3V2XC47020_03.pdf |
| 104 | `wsc-f165c842e6ea20b0ebdb4ab5` | Điều tra lỗi | 0.000 | 109 | ENGINE_3V2XC47020_03.pdf |
| 105 | `wsc-5c325bc2f80435062df95d50` | Điều tra lỗi | 0.000 | 87 | ENGINE_3V2XD47020_03.pdf |
| 106 | `wsc-a032baf0a275d56b9d143c6e` | Điều tra lỗi | 0.000 | 143 | ENGINE_3V2XD47020_03.pdf |
| 107 | `wsc-3587e2f5bfbd6e496ba35b6c` | Điều tra lỗi | 0.000 | 143 | ENGINE_3V2XF47020_03.pdf |
| 108 | `wsc-db175ac176b1f61b1d7366bc` | Điều tra lỗi | 0.000 | 70 | ENGINE_3V2XF47020_03.pdf |
| 109 | `wsc-0f1d8764dd417ca17696556e` | Điều tra lỗi | 0.000 | 50 | FEED_3V2XC47030-02.pdf |
| 110 | `wsc-a63546361dd85a8d7590e066` | Điều tra lỗi | 0.000 | 56 | FEED_3V2XC47030-02.pdf |
| 111 | `wsc-06dd073629bf411f998d8358` | Điều tra lỗi | 0.000 | 46 | FW    IRIS2020 (High Model) QA_C0650_08_Dec.msg |
| 112 | `wsc-8108791a3914d7a95a6d92b2` | Điều tra lỗi | 0.000 | 184 | FW    IRIS2020 (High Model) QA_C0650_08_Dec.msg |
| 113 | `wsc-a6056603cd9e2cfbda3b9ca6` | Điều tra lỗi | 0.000 | 17 | FW  2021 11 20週報.msg |
| 114 | `wsc-baf337f476d781df19a8b7e8` | Điều tra lỗi | 0.000 | 245 | FW  2021 11 20週報.msg |
| 115 | `wsc-2c09cb995ab62639bcff042f` | Điều tra lỗi | 0.000 | 101 | IMAGE DRIVE_HIGH_20211105.pdf |
| 116 | `wsc-c796749fb56c6558d4a3006f` | Điều tra lỗi | 0.000 | 79 | IMAGE DRIVE_HIGH_20211105.pdf |
| 117 | `wsc-a0ac30ec0d69447c282517d0` | Điều tra lỗi | 0.000 | 92 | IMAGE_3V2XD47040-02.pdf |
| 118 | `wsc-eee84fc769be032b59c91f88` | Điều tra lỗi | 0.000 | 73 | IMAGE_3V2XD47040-02.pdf |
| 119 | `wsc-1e00d058fb53d977664395cf` | Điều tra lỗi | 0.000 | 74 | IMAGE_V2XC47040-02.pdf |
| 120 | `wsc-dcbf68ac7f6f50e228744682` | Điều tra lỗi | 0.000 | 96 | IMAGE_V2XC47040-02.pdf |
| 121 | `wsc-a3c22ba67b8c8d0dbce595d3` | Điều tra lỗi | 0.000 | 25 | Iris 2ND IH PP 01 302ND47250 20160205.pdf |
| 122 | `wsc-f78359f9fd1d8169981942d4` | Điều tra lỗi | 0.000 | 22 | Iris 2ND IH PP 01 302ND47250 20160205.pdf |
| 123 | `wsc-76c8e2359e579b0448972a17` | Điều tra lỗi | 0.000 | 22 | Iris 2ND IH PP 01 302ND47260 20160205.pdf |
| 124 | `wsc-d345f24ffd6331c12d85541d` | Điều tra lỗi | 0.000 | 24 | Iris 2ND IH PP 01 302ND47260 20160205.pdf |
| 125 | `wsc-b9a7cdf1be485464c426c840` | Điều tra lỗi | 0.000 | 15 | Iris2020_302XC45020(転写)_Ver1.1.pdf |
| 126 | `wsc-f7d8e468ade5537fe2107426` | Điều tra lỗi | 0.000 | 26 | Iris2020_302XC45020(転写)_Ver1.1.pdf |
| 127 | `wsc-25d14f843dbbf5b39a681f09` | Điều tra lỗi | 0.000 | 26 | Iris2020_302XC45020(転写)_Ver1.2.pdf |
| 128 | `wsc-333ca7a39d0c430f85b28423` | Điều tra lỗi | 0.000 | 16 | Iris2020_302XC45020(転写)_Ver1.2.pdf |
| 129 | `wsc-6756e9d4da74ab45297f0096` | Điều tra lỗi | 0.000 | 6 | Iris2020_LED DRIVE基板回路図_190624.pdf |
| 130 | `wsc-a760bd10e5adc9d60f0546c7` | Điều tra lỗi | 0.000 | 6 | Iris2020_LED DRIVE基板回路図_190624.pdf |
| 131 | `wsc-6d5f9eb67e081bff7e4ef652` | Điều tra lỗi | 0.000 | 1 | Iris2020High_302XC45010_D級アンプモジュール.pdf |
| 132 | `wsc-d17535366b5acd16c41ce29e` | Điều tra lỗi | 0.000 | 3 | Iris2020High_302XC45010_D級アンプモジュール.pdf |
| 133 | `wsc-1175ba55f50d8593070f0789` | Điều tra lỗi | 0.000 | 38 | Iris2020High_302XC45010_Ver2.0.pdf |
| 134 | `wsc-e1d1ab72abb8bf9fe98e233b` | Điều tra lỗi | 0.000 | 44 | Iris2020High_302XC45010_Ver2.1.pdf |
| 135 | `wsc-a7a6e6af7f273726ed7887db` | Điều tra lỗi | 0.000 | 8 | Iris2020High_302XC45010_縦基板_Ver2.0.pdf |
| 136 | `wsc-d3d42ae454d5dd661cdff4ea` | Điều tra lỗi | 0.000 | 5 | Iris2020High_302XC45010_縦基板_Ver2.0.pdf |
| 137 | `wsc-0ccea4725e16aa19798d6b3d` | Điều tra lỗi | 0.000 | 8 | Iris2020High_302XC45010立て基板_Ver2.1.pdf |
| 138 | `wsc-9b72e97690e09625f2f4367b` | Điều tra lỗi | 0.000 | 5 | Iris2020High_302XC45010立て基板_Ver2.1.pdf |
| 139 | `wsc-52c0bf23393702089f5df5ac` | Điều tra lỗi | 0.000 | 24 | Iris2020Low_302L745040.pdf |
| 140 | `wsc-a8de942eabd16132b2d7e858` | Điều tra lỗi | 0.000 | 31 | Iris2020Low_302L745040.pdf |
| 141 | `wsc-02b0e29e4af0c34436b864f3` | Điều tra lỗi | 0.000 | 21 | Iris2020Mono_302XF45010Ver2.1.pdf |
| 142 | `wsc-58542ce6a2bd931954bcfe0f` | Điều tra lỗi | 0.000 | 15 | Iris2024 PMT 上位机C2103调查报告20240927.xlsx |
| 143 | `wsc-d9e35041318fcc6ae5050630` | Điều tra lỗi | 0.000 | 101 | Iris2024 PMT 上位机C2103调查报告20240927.xlsx |
| 144 | `wsc-5ffc1cf0d0244daff95a3f88` | Điều tra lỗi | 0.000 | 9 | IRIS2_2V8_HUMAN DETECT_PP_01基板回路図.pdf |
| 145 | `wsc-fc090c33876d29708aa9744a` | Điều tra lỗi | 0.000 | 10 | IRIS2_2V8_HUMAN DETECT_PP_01基板回路図.pdf |
| 146 | `wsc-703148c1b14c3d271f69773f` | Điều tra lỗi | 0.000 | 23 | Iris_2ND_IH_MP_01基板回路図_302ND47250_20170116.pdf |
| 147 | `wsc-f22a9158488fd77a604fcaef` | Điều tra lỗi | 0.000 | 25 | Iris_2ND_IH_MP_01基板回路図_302ND47250_20170116.pdf |
| 148 | `wsc-c9dca0889867430a81dd73f4` | Điều tra lỗi | 0.000 | 22 | Iris_2ND_IH_MP_01基板回路図_302ND47260_20170116.pdf |
| 149 | `wsc-dd84358aa3c71512eb1de019` | Điều tra lỗi | 0.000 | 25 | Iris_2ND_IH_MP_01基板回路図_302ND47260_20170116.pdf |
| 150 | `wsc-756dd40c8928c1f7a9f07e6f` | Điều tra lỗi | 0.000 | 7 | Iris_2ND_IH_MP_01基板回路図_302ND47341_20170116.pdf |
| 151 | `wsc-8542dc0b45fd92bfeac1d400` | Điều tra lỗi | 0.000 | 8 | Iris_2ND_IH_MP_01基板回路図_302ND47341_20170116.pdf |
| 152 | `wsc-00428f9482636841c4638269` | Điều tra lỗi | 0.000 | 6 | Iris_FUSER_PP_01基板回路図.pdf |
| 153 | `wsc-745957d44a9de3531a704db8` | Điều tra lỗi | 0.000 | 7 | Iris_FUSER_PP_01基板回路図.pdf |
| 154 | `wsc-da9dd616e97a5ad5eb253315` | Điều tra lỗi | 0.000 | 10 | KTD-2024-10-1275-Iris2020-C34-A1-Maintance front is close.xlsx |
| 155 | `wsc-130f6507201b63a1958a8601` | Điều tra lỗi | 0.000 | 7 | KTD-2024-11-1610-Iris2020-C35-A1-C3200.xlsx |
| 156 | `wsc-0cddcf9be6a24416a3265bc0` | Điều tra lỗi | 0.000 | 9 | KTD-2024-12-1698-Iris2020-C34-Operation-Màn hình hiển thị bất thường.xlsx |
| 157 | `wsc-ba1a2263c71d445eddea1776` | Điều tra lỗi | 0.000 | 9 | KTD-2024-12-1752-Iris2020-C35-Operation-Vỡ linh kiện.xlsx |
| 158 | `wsc-db399570b90a8f853af0877e` | Điều tra lỗi | 0.000 | 12 | KTD-2024-8-Iris2020-C33 T101 UHV FUSER SHORT .xlsx |
| 159 | `wsc-e70a9d9d9cd0f3ec6b13de4c` | Điều tra lỗi | 0.000 | 11 | KTD-2024-9-1227-Iris 2020-C34-C6950.xlsx |
| 160 | `wsc-b2a1ab94a524417179cd144e` | Điều tra lỗi | 0.000 | 8 | KTD-2025-01-0019-IRIS2024-C34-operation màn hình xanh bất thường.xlsx |
| 161 | `wsc-27cf749e5aa7038c98c57853` | Điều tra lỗi | 0.000 | 11 | KTD-2025-01-0100-Iris2020-kaizo-C35-A1-Màn hình không sáng.xlsx |
| 162 | `wsc-263b82782ff9d692d840559b` | Điều tra lỗi | 0.000 | 12 | KTD-2025-01-0109-Iris2024-C34-HONTAI-Connector NG.xlsx |
| 163 | `wsc-9291fbad2042853cb55ceeba` | Điều tra lỗi | 0.000 | 12 | KTD-2025-02-0140-Iris2024-C35-Hontai1-Kênh chân connector.xlsx |
| 164 | `wsc-c7f5f0737a41a7f8d1e8f734` | Điều tra lỗi | 0.000 | 22 | KTD-2025-02-0148-Iris2024-C34-A1-C0980.xlsx |
| 165 | `wsc-b7952d78731793540a69dcc2` | Điều tra lỗi | 0.000 | 16 | KTD-2025-02-0169-Iris2024-C35-A1-C6930.xlsx |
| 166 | `wsc-d1a2c5999f4354c2d267aa08` | Điều tra lỗi | 0.000 | 2143 | KTD-2025-02-1000-Iris2024-WASE TONNER BOX IS NOT INSTALL.xlsx |
| 167 | `wsc-865ce9d83a09db055a608707` | Điều tra lỗi | 0.000 | 9 | KTD-2025-03-0215-Iris2024-C35-C4709-.xlsx |
| 168 | `wsc-794a6014e1db7ca12a463750` | Điều tra lỗi | 0.000 | 9 | KTD-2025-03-0230-Iris2024-C34-Operation-Cảm ứng bất thường.xlsx |
| 169 | `wsc-e55ea3b2d44563c8ace198d5` | Điều tra lỗi | 0.000 | 21 | KTD-2025-03-0239-Iris2024-C35-A7-C0980.xlsx |
| 170 | `wsc-b08efb14d63a9f17c55118fa` | Điều tra lỗi | 0.000 | 16 | KTD-2025-03-0262-Iris2024-C33-A1-Không lên nguồn.xlsx |
| 171 | `wsc-f4560f43f2f522ffe7ca9aea` | Điều tra lỗi | 0.000 | 9 | KTD-2025-03-0275-Iris2024-C35-Hontai-Thiếc hàn dính trên cuộn cảm L3..xlsx |
| 172 | `wsc-bb2f50ae6ea94abda3ff5b89` | Điều tra lỗi | 0.000 | 7 | KTD-2025-03-0280-Iris2024-C35-Màn hình không sáng.xlsx |
| 173 | `wsc-63ee830e8f40274c7cbbdfc4` | Điều tra lỗi | 0.000 | 21 | KTD-2025-03-0315-Iris2024-C34-A6-C0980.xlsx |
| 174 | `wsc-e297dfbd7aacd9a2a0655bb3` | Điều tra lỗi | 0.000 | 21 | KTD-2025-03-0316-Iris2024-C35-DLP- toner sensor lắp khó.xlsx |
| 175 | `wsc-f50f5a0150d8d0e79143ad48` | Điều tra lỗi | 0.000 | 21 | KTD-2025-03-0332-Iris2024-C33-A5-Máy sập nguồn.xlsx |
| 176 | `wsc-52bcbeb1d86b336f017ba6fa` | Điều tra lỗi | 0.000 | 10 | KTD-2025-03-0341-Iris2024-C35-A6-Không nhận biết size giấy.xlsx |
| 177 | `wsc-13dc5d0d8ae16e8c31bdf1f1` | Điều tra lỗi | 0.000 | 7 | KTD-2025-04-0363-Iris2024-C34-ASSY-Bong linh kiện.xlsx |
| 178 | `wsc-abcbc33f243bd0eef6e3fd55` | Điều tra lỗi | 0.000 | 17 | KTD-2025-04-0364-Iris2024-C34-A1-C6950.xlsx |
| 179 | `wsc-98f1a2dba280d680dfa49eea` | Điều tra lỗi | 0.000 | 10 | KTD-2025-04-0399-Iris2024-C33-A1-C7904.xlsx |
| 180 | `wsc-d1735009c665ba4d305ae6ed` | Điều tra lỗi | 0.000 | 9 | KTD-2025-04-0402-Iris2024-C35-A3-C6950.xlsx |
| 181 | `wsc-097ffc38b07f11cf53843ead` | Điều tra lỗi | 0.000 | 19 | KTD-2025-04-0435-Iris2024-C33-A1-C0980.xlsx |
| 182 | `wsc-fee0e656f0679fe3e4772ec3` | Điều tra lỗi | 0.000 | 24 | KTD-2025-05-0447-Iris2024-C33-A2-C6770.xlsx |
| 183 | `wsc-1bf77cfe359bae2fbc68c729` | Điều tra lỗi | 0.000 | 7 | KTD-2025-05-0456-Iris2024-C34-A2-C6770.xlsx |
| 184 | `wsc-ac6edc7427a6faa961aa30fb` | Điều tra lỗi | 0.000 | 30 | KTD-2025-05-0469-Iris2024-C34-A2-Không lên nguồn.xlsx |
| 185 | `wsc-0c15280f4188b2c31c1c0b58` | Điều tra lỗi | 0.000 | 23 | KTD-2025-05-0482-Iris2024-C33-A1.2-C0980.xlsx |
| 186 | `wsc-f8fafb2ac813c0c8dad2aae3` | Điều tra lỗi | 0.000 | 26 | KTD-2025-05-0525-Iris2024-C33-A1-C6760.xlsx |
| 187 | `wsc-be3445add4596246bda91ef8` | Điều tra lỗi | 0.000 | 23 | KTD-2025-05-0536-Iris2024-C33-A2-C6770.xlsx |
| 188 | `wsc-c634eaf0e81bafad4a4b7f51` | Điều tra lỗi | 0.000 | 21 | KTD-2025-05-0538-Iris2024-C35-A1- C6950.xlsx |
| 189 | `wsc-5284e5eb6541997ae1861dd4` | Điều tra lỗi | 0.000 | 18 | KTD-2025-05-0539-Iris2024-C35-A6- C6770.xlsx |
| 190 | `wsc-bcda9f863324d162d1ef4917` | Điều tra lỗi | 0.000 | 18 | KTD-2025-05-0540-Iris2024-C34-A1- C6770.xlsx |
| 191 | `wsc-1b5939b5c43b5a48f6af8ff5` | Điều tra lỗi | 0.000 | 11 | KTD-2025-05-0541-Iris2024-C35-A6-Error56.xlsx |
| 192 | `wsc-b0217ce0f1e8c76b33cf16e1` | Điều tra lỗi | 0.000 | 9 | KTD-2025-06-0570-Iris2024-C34-A1-C6950.xlsx |
| 193 | `wsc-856776d9f52abcb01c770de8` | Điều tra lỗi | 0.000 | 13 | KTD-2025-06-0572-Iris2024-C35-A2-C6000.xlsx |
| 194 | `wsc-c043520b00c14db807ffc0a1` | Điều tra lỗi | 0.000 | 25 | KTD-2025-06-0578-Iris2024-C33-A2-C6770.xlsx |
| 195 | `wsc-b67a8ee411273ba936aa6e3c` | Điều tra lỗi | 0.000 | 7 | KTD-2025-06-0582-Iris2024-C35-A8-C6770.xlsx |
| 196 | `wsc-0e101cefe1d7c8af523c9e3e` | Điều tra lỗi | 0.000 | 9 | KTD-2025-06-0599-Iris2024-C35-A2-Màn hình hiển thị bất thường.xlsx |
| 197 | `wsc-e69f79d12e423dc6c63fe5e3` | Điều tra lỗi | 0.000 | 18 | KTD-2025-06-0606-Iris2024-C33-Operation-Màn hình hiển thị bất thường.xlsx |
| 198 | `wsc-da631a8393f534bcdbe55677` | Điều tra lỗi | 0.000 | 30 | KTD-2025-06-0639-Iris2024-C35-A1-Không lên nguồn.xlsx |
| 199 | `wsc-ec0ae55d30cd38c6a4863bd7` | Điều tra lỗi | 0.000 | 9 | KTD-2025-06-0650-Iris2024-C35-A6-Error80.xlsx |
| 200 | `wsc-3be416fb975b60f419ade492` | Điều tra lỗi | 0.000 | 12 | KTD-2025-07-0664-Iris2024-C35-A2-C6770.xlsx |
| 201 | `wsc-85767d5af538c492b57229d5` | Điều tra lỗi | 0.000 | 12 | KTD-2025-07-0671-Iris2024-C35-A2-C6770.xlsx |
| 202 | `wsc-7030e0419bdb4c0b0d4370b8` | Điều tra lỗi | 0.000 | 14 | KTD-2025-07-0673-Iris2024-C33-A11-C6770.xlsx |
| 203 | `wsc-942e16fb891bdf307915ecc9` | Điều tra lỗi | 0.000 | 7 | KTD-2025-07-0677-Iris2024-C33-A1-không vào trạng thái Upsoft.xlsx |
| 204 | `wsc-3aa8ca33e183741d43b4ec60` | Điều tra lỗi | 0.000 | 31 | KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx |
| 205 | `wsc-843d4c78354106aa63f64768` | Điều tra lỗi | 0.000 | 9 | KTD-2025-07-0680-Iris2024-C34-Operation-Màn hình hiển thị bất thường.xlsx |
| 206 | `wsc-288bd4faf48b948b1f387e31` | Điều tra lỗi | 0.000 | 10 | KTD-2025-07-0683-Iris2024-C34-A6-Scan SITC NG.xlsx |
| 207 | `wsc-659942f48e2057945b2fddd7` | Điều tra lỗi | 0.000 | 8 | KTD-2025-07-0710-Iris2024-C33-A5-C4101.xlsx |
| 208 | `wsc-43617ac15a7145d46660243d` | Điều tra lỗi | 0.000 | 7 | KTD-2025-07-0733-Iris2024-C33-A11-C6950.xlsx |
| 209 | `wsc-da34025c9863368d6d45baed` | Điều tra lỗi | 0.000 | 19 | KTD-2025-07-0743-DP Iris2020-C2E-Connector NG.xlsx |
| 210 | `wsc-dfc14e4889788f9139db7454` | Điều tra lỗi | 0.000 | 7 | KTD-2025-07-0745-Iris2024-C35-A8.5-Hình ảnh bất thường.xlsx |
| 211 | `wsc-d50142fd6818b4cdf2a1385a` | Điều tra lỗi | 0.000 | 16 | KTD-2025-07-0764-Iris2024-C33-A1-C6770.xlsx |
| 212 | `wsc-6e51a0f2bb7b2d5e85afcf62` | Điều tra lỗi | 0.000 | 15 | KTD-2025-07-0784-Iris2024-C33-A1-Không lên nguồn.xlsx |
| 213 | `wsc-6ee7bee35dc72905076f42d2` | Điều tra lỗi | 0.000 | 9 | KTD-2025-07-0785-Iris2024-C33-ISU-.xlsx |
| 214 | `wsc-5582ee77957a9aab925f3312` | Điều tra lỗi | 0.000 | 12 | KTD-2025-07-0786-PF Iris2020-A2D-Kênh chân connector.xlsx |
| 215 | `wsc-c903cdc836408d749261e9a1` | Điều tra lỗi | 0.000 | 16 | KTD-2025-07-0787-Iris2024-C34-A6-Error56.xlsx |
| 216 | `wsc-2335294212d0f129b375d3db` | Điều tra lỗi | 0.000 | 17 | KTD-2025-07-0788-Iris2024-C33-A9-C6770.xlsx |
| 217 | `wsc-efaad6f86415572c03c67b9a` | Điều tra lỗi | 0.000 | 20 | KTD-2025-07-0789-Iris2024-C35-A6-C6950.xlsx |
| 218 | `wsc-88b9a732e3007c8110dc64bd` | Điều tra lỗi | 0.000 | 9 | KTD-2025-07-0802-Iris2024-C34-A6-Không nhận biết size giấy.xlsx |
| 219 | `wsc-998b92e8af5c086557e8797a` | Điều tra lỗi | 0.000 | 10 | KTD-2025-07-0805-DP Iris2020-C2D-C9080.xlsx |
| 220 | `wsc-c601aaa050ebde0946ac6e41` | Điều tra lỗi | 0.000 | 12 | KTD-2025-08-0831-Iris2024-C35-A8.6-Scan tự động NG.xlsx |
| 221 | `wsc-70c916ba961ab584ec28ba23` | Điều tra lỗi | 0.000 | 21 | KTD-2025-08-0841-Iris2024-C35-A8-C0980.xlsx |
| 222 | `wsc-b204340ee659900704027697` | Điều tra lỗi | 0.000 | 7 | KTD-2025-08-0853-Iris2024-C34-A8.5- Jam4709.xlsx |
| 223 | `wsc-a9dafab21d3287a9cea74290` | Điều tra lỗi | 0.000 | 6 | KTD-2025-08-0854-Iris2024-C34-A1-The cover is open.xlsx |
| 224 | `wsc-3417cc72cb93591e9b55602f` | Điều tra lỗi | 0.000 | 9 | KTD-2025-08-0860-Iris2024-C34-A8-Hình ảnh bất thường.xlsx |
| 225 | `wsc-5f4753572bafb19738cc4e22` | Điều tra lỗi | 0.000 | 31 | KTD-2025-08-0866-DP Iris2020-C2B- Write DP Serial NG.xlsx |
| 226 | `wsc-f1500d9f841de301382fef0a` | Điều tra lỗi | 0.000 | 11 | KTD-2025-08-0869-Iris2024-C33-A1-TLBĐ NG.xlsx |
| 227 | `wsc-758dbc494c6c79e1c24399bb` | Điều tra lỗi | 0.000 | 14 | KTD-2025-08-0871-Iris2024-C35-A1-C6770.xlsx |
| 228 | `wsc-468aede06b922b9f1a06bbbb` | Điều tra lỗi | 0.000 | 9 | KTD-2025-08-0902-Iris2024-C35-A6-Error56.xlsx |
| 229 | `wsc-43628c11d54ddeeb6ff17d77` | Điều tra lỗi | 0.000 | 9 | KTD-2025-08-0905-Iris2024-C35-A8-Hình ảnh bất thường.xlsx |
| 230 | `wsc-32d335de53deecb7234400bb` | Điều tra lỗi | 0.000 | 20 | KTD-2025-08-0907-Iris2024-C33-A8-Không lên  nguồn..xlsx |
| 231 | `wsc-52d6c2ec0a4bc8e13d2d7e7b` | Điều tra lỗi | 0.000 | 7 | KTD-2025-08-0912-Iris2024-C34-A1-Màn hình không sáng.xlsx |
| 232 | `wsc-a656cc0d5bcc128c2eabc3b3` | Điều tra lỗi | 0.000 | 6 | KTD-2025-08-0914-Iris2024-C35-A7-Error80.xlsx |
| 233 | `wsc-ce0597d94b5fa4ef43b550e2` | Điều tra lỗi | 0.000 | 23 | KTD-2025-08-0924-Iris2024-C33-A3-C6770.xlsx |
| 234 | `wsc-6ce168797974d612eba1d141` | Điều tra lỗi | 0.000 | 10 | KTD-2025-08-0931-DP Iris2020-C2B-Jam9002.xlsx |
| 235 | `wsc-29abb276a2ec3d199058e392` | Điều tra lỗi | 0.000 | 13 | KTD-2025-09-0932-DP Iris2020-C2E-NG Fax.xlsx |
| 236 | `wsc-37cde0df4a074bd346648c4e` | Điều tra lỗi | 0.000 | 9 | KTD-2025-09-0937-Iris2020-C35-ASSY2-Bong linh kiện.xlsx |
| 237 | `wsc-f42456150599cfd058554c3e` | Điều tra lỗi | 0.000 | 20 | KTD-2025-09-0941-Iris2024-C33-A3-C6770.xlsx |
| 238 | `wsc-d182d6a6892d8de0f50133b4` | Điều tra lỗi | 0.000 | 10 | KTD-2025-09-0952-Iris2024-C35-A6-Hình ảnh bất thường.xlsx |
| 239 | `wsc-2f3e5b720c50316fd816a04d` | Điều tra lỗi | 0.000 | 22 | KTD-2025-09-0953-Iris2024-C2B-NG Fax.xlsx |
| 240 | `wsc-0b2c3cfc2f8115b362e9224e` | Điều tra lỗi | 0.000 | 10 | KTD-2025-09-0965-Iris2024-C35-A1-C9540.xlsx |
| 241 | `wsc-e94e601e208e77de3727b087` | Điều tra lỗi | 0.000 | 7 | KTD-2025-09-0986-Iris2024-C34-A1-C0350.xlsx |
| 242 | `wsc-4a884ed893315f6536f3e437` | Điều tra lỗi | 0.000 | 16 | KTD-2025-09-1009-DP Iris2020-C2D-A1-C9080.xlsx |
| 243 | `wsc-6b2aa94ef8e53292a9ec0c1d` | Điều tra lỗi | 0.000 | 25 | KTD-2025-09-1015-Iris2024-C33-A8.2-C6770.xlsx |
| 244 | `wsc-5214515c9419a919f5fd9b01` | Điều tra lỗi | 0.000 | 13 | KTD-2025-10-1024-Iris2024-C33-A8.4-JAM4012.xlsx |
| 245 | `wsc-93a152e658d9e9c7d7577611` | Điều tra lỗi | 0.000 | 9 | KTD-2025-10-1050-Iris2024-C35-A7-Hình ảnh bất thường.xlsx |
| 246 | `wsc-6aa9d3fc0950434765835f35` | Điều tra lỗi | 0.000 | 25 | KTD-2025-10-1074-Iris2024-C33-ISU-Dính hàn.xlsx |
| 247 | `wsc-f5d26558502f914517c0be8c` | Điều tra lỗi | 0.000 | 7 | KTD-2025-10-1075-DP Iris2020-C2D-Scan tự động NG.xlsx |
| 248 | `wsc-3caf4b6aacbde11a595a308e` | Điều tra lỗi | 0.000 | 13 | KTD-2025-10-1089-DP Iris2020-C2D-A16-C9080.xlsx |
| 249 | `wsc-c8cd3fc7721deb12af92b5bd` | Điều tra lỗi | 0.000 | 13 | KTD-2025-10-1091-Iris2024-C33-Hontai-Chịu áp cách điện NG.xlsx |
| 250 | `wsc-16b07714040fa97f80b82d59` | Điều tra lỗi | 0.000 | 11 | KTD-2025-10-1095-DP Iris2020-C2D-A9-Vạch tờ Gray.xlsx |
| 251 | `wsc-ec39b96aabbce0fb40ffa4bc` | Điều tra lỗi | 0.000 | 10 | KTD-2025-10-1119-Iris2024-C34-A8.5-Màn hình hiển thị bất thường.xlsx |
| 252 | `wsc-cc8f350176281fb128c76910` | Điều tra lỗi | 0.000 | 11 | KTD-2025-10-1122-Iris2024-C3A-K2-.xlsx |
| 253 | `wsc-70e43b4fd7941d590c853961` | Điều tra lỗi | 0.000 | 10 | KTD-2025-10-1148-DP Iris2020-C2D-Assy-.xlsx |
| 254 | `wsc-10885646e1efad265d1b7245` | Điều tra lỗi | 0.000 | 7 | KTD-2025-11-1150-Iris2024-C35-A8-C6770.xlsx |
| 255 | `wsc-b4cc75ecac2b2dcd7e2471c7` | Điều tra lỗi | 0.000 | 10 | KTD-2025-11-1163-DP Iris2020-C2D-C9080.xlsx |
| 256 | `wsc-a629562965ea15b806bd8ff6` | Điều tra lỗi | 0.000 | 16 | KTD-2025-11-1165-Iris2024-C33-Assy2-Vỡ linh kiện.xlsx |
| 257 | `wsc-09d5dcaf3f94ddb5f9d6f8ac` | Điều tra lỗi | 0.000 | 13 | KTD-2025-11-1170-Iris2024-C35-8.2-Hình ảnh bất thường.xlsx |
| 258 | `wsc-c3e7ff49251ad8ff24cf613e` | Điều tra lỗi | 0.000 | 6 | KTD-2025-11-1181-Iris2024-C35-A5-Màn hình không sáng.xlsx |
| 259 | `wsc-76beb46f6973ff5135836034` | Điều tra lỗi | 0.000 | 8 | KTD-2025-11-1196-Iris2024-C33-A2-C6030.xlsx |
| 260 | `wsc-eefe38a9278f1a43fbe04e07` | Điều tra lỗi | 0.000 | 8 | KTD-2025-11-1198-DP Iris2020-C2D-A10-C9080.xlsx |
| 261 | `wsc-dd3714ace41938b744ebc0cd` | Điều tra lỗi | 0.000 | 11 | KTD-2025-11-1232-DP Iris2020-C2D-C9080.xlsx |
| 262 | `wsc-841c550e596405b02acca0fc` | Điều tra lỗi | 0.000 | 9 | KTD-2025-12-1288-DP Iris2020-C2D-A2-Scan SITC NG.xlsx |
| 263 | `wsc-7f0a77dcd5d243e5f8ff4884` | Điều tra lỗi | 0.000 | 28 | KTD-2025-12-1310-Iris2024-C35-A1-C0980.xlsx |
| 264 | `wsc-4abade7d2456adf01bb1fd26` | Điều tra lỗi | 0.000 | 26 | KTD-2025-12-1314-Iris2024-C33-A1-C6760.xlsx |
| 265 | `wsc-b2e22ec6dba6c50078d14b2a` | Điều tra lỗi | 0.000 | 10 | KTD-2025-12-1325-DP Iris2020-C2D-A6-C9080.xlsx |
| 266 | `wsc-c5654c099fc04e2360e630e7` | Điều tra lỗi | 0.000 | 12 | KTD-2025-12-1326-Iris2024-C33-A11-JAM4212.xlsx |
| 267 | `wsc-5e1396801eb098b19421a59e` | Điều tra lỗi | 0.000 | 9 | KTD-2025-12-1332-Iris2024-C33-A2-C0350.xlsx |
| 268 | `wsc-be7eeb5b5d407ea971154543` | Điều tra lỗi | 0.000 | 12 | KTD-2025-12-1353-Iris2024-C35-assy2-Bong linh kiện.xlsx |
| 269 | `wsc-d4e602e22bf25b3afea16ae8` | Điều tra lỗi | 0.000 | 9 | KTD-2025-12-1384-Iris2024-C35-A6-Không nhận biết size giấy.xlsx |
| 270 | `wsc-a422421f0162693ca6d6c829` | Điều tra lỗi | 0.000 | 12 | KTD-2025-12-1389-Iris2024-C33-A7-Error56.xlsx |
| 271 | `wsc-5ea69e17220dfbfb09ad59d1` | Điều tra lỗi | 0.000 | 10 | KTD-2025-12-1390-Iris2024-C34-A7-Error56.xlsx |
| 272 | `wsc-49753efc0247446f4754564c` | Điều tra lỗi | 0.000 | 7 | KTD-2025-12-1398-Iris2024-C35-A6-Hình ảnh bất thường.xlsx |
| 273 | `wsc-c7af7d1a39f4e37f2174a4bf` | Điều tra lỗi | 0.000 | 6 | KTD-2026-01-0005-Iris2024-C34-A1-C2840.xlsx |
| 274 | `wsc-19210ff0c52dbcba6f156813` | Điều tra lỗi | 0.000 | 9 | KTD-2026-01-0011-Iris2024-Eva-.xlsx |
| 275 | `wsc-509d925a147d8feae7bb72e6` | Điều tra lỗi | 0.000 | 7 | KTD-2026-01-0030-Iris2024-C34-A4-C6000.xlsx |
| 276 | `wsc-3d9aa320fd815c22934dd257` | Điều tra lỗi | 0.000 | 6 | KTD-2026-01-0067-Iris2020-C34-A1-C4701.xlsx |
| 277 | `wsc-4a661df9d0318f5164a9d649` | Điều tra lỗi | 0.000 | 6 | KTD-2026-01-0087-Iris2024-C34-A1-C0350.xlsx |
| 278 | `wsc-d1582dbca5c82c737612268e` | Điều tra lỗi | 0.000 | 6 | KTD-2026-01-0096-Iris2024-C34-A1-C6770.xlsx |
| 279 | `wsc-d3cde7ece9ec0806ecaa792f` | Điều tra lỗi | 0.000 | 6 | KTD-2026-01-0104-Iris2024-C35-A7-J4002.xlsx |
| 280 | `wsc-565fad6cef70e70bccf4a360` | Điều tra lỗi | 0.000 | 10 | KTD-2026-01-0114-Iris2024-C33-A6-Error80.xlsx |
| 281 | `wsc-61c93ce16af0fbeb80b7aeed` | Điều tra lỗi | 0.000 | 10 | KTD-2026-02-0115-Iris2024-C34-Assy-Lắp khó.xlsx |
| 282 | `wsc-04c3db879b730cb0c53063f6` | Điều tra lỗi | 0.000 | 6 | KTD-2026-02-0117-Iris2024-C35-A1-C9540.xlsx |
| 283 | `wsc-d1bbc4c4d0bf7ca8127a6634` | Điều tra lỗi | 0.000 | 11 | KTD-2026-02-0137-Iris2024-C33-K4 Operation-âm bàn phím không kêu.xlsx |
| 284 | `wsc-bd169223852e951cbdb30f5f` | Điều tra lỗi | 0.000 | 6 | KTD-2026-02-0150-Iris2024-C34-A1-C0840.xlsx |
| 285 | `wsc-3a6cd2f22301364893742ddb` | Điều tra lỗi | 0.000 | 9 | KTD-2026-02-0152-Iris2024-C33-A2-TLBĐ NG RFID.xlsx |
| 286 | `wsc-2c5b5ab6d3275d37196b4910` | Điều tra lỗi | 0.000 | 6 | KTD-2026-02-0154-Iris2024-C34-A7-C2950.xlsx |
| 287 | `wsc-93b4d09cfb820bdc9a04f258` | Điều tra lỗi | 0.000 | 6 | KTD-2026-02-0167-Iris2024-C35-A8-Jam0501.xlsx |
| 288 | `wsc-e640f1cc1e6255147c30d453` | Điều tra lỗi | 0.000 | 6 | KTD-2026-03-0199-Iris2024-C34-A1-Scan SITC NG.xlsx |
| 289 | `wsc-ce948fa79f1da30cb6dbba00` | Điều tra lỗi | 0.000 | 10 | KTD-2026-03-0232-Iris2024-C35-Drum-Bản mạch bị nứt.xlsx |
| 290 | `wsc-91ce4d7b6af13d7cecec04d7` | Điều tra lỗi | 0.000 | 6 | KTD-2026-03-0245-Iris2024-C35-A1-TLBĐ NG RFID.xlsx |
| 291 | `wsc-480e4c1a6c92337ab598f53c` | Điều tra lỗi | 0.000 | 6 | KTD-2026-03-0252-Iris2024-C34-A3-Led Job Separator không sáng.xlsx |
| 292 | `wsc-1fcb1ee9191657a7a56c478d` | Điều tra lỗi | 0.000 | 10 | KTD-2026-03-0262-Iris2024-C35-A1-The Toner Container Is not Properly Installed.xlsx |
| 293 | `wsc-1f82d84d72992f70bf7897f4` | Điều tra lỗi | 0.000 | 7 | KTD-2026-04-0313-Iris2024-C35-A1-C4801.xlsx |
| 294 | `wsc-5a63dbce80246536b744fd12` | Điều tra lỗi | 0.000 | 7 | KTD-2026-04-0331-Iris2024-C35-A6-Hình ảnh bất thường.xlsx |
| 295 | `wsc-8d6b06ce2266f3fee2004eef` | Điều tra lỗi | 0.000 | 6 | KTD-2026-04-0334-Iris2024-C34-Operation-Màn hình hiển thị bất thường.xlsx |
| 296 | `wsc-5527b89949fcbd89449224c8` | Điều tra lỗi | 0.000 | 9 | KTD-2026-04-0359-DP Iris2020-C2C-A4-Không nhận biết size giấy.xlsx |
| 297 | `wsc-c648d96d66a2ff7a796ed10b` | Điều tra lỗi | 0.000 | 9 | KTD-2026-04-0383-Iris2024-C34-A11-Màn hình hiển thị bất thường.xlsx |
| 298 | `wsc-ffa5990a715ba460983eb681` | Điều tra lỗi | 0.000 | 2 | KTD-2026-04-0397-Iris2024-C35-A1-C0980.xlsx |
| 299 | `wsc-d590c4effcf23f50b86e25ee` | Điều tra lỗi | 0.000 | 10 | KTD-2026-04-0400-Iris2024-C35-A5-Hình ảnh bất thường.xlsx |
| 300 | `wsc-6f2381659edca571f63aaa13` | Điều tra lỗi | 0.000 | 9 | KTD-2026-04-0401-Iris2024-C36-A6-JAM4202.xlsx |
| 301 | `wsc-c4470e2a1b0f67333f6075c4` | Điều tra lỗi | 0.000 | 10 | KTD-2026-04-Iris2024-C33-Operation- Góc trên bên trái bị sáng bất thường.xlsx |
| 302 | `wsc-1c8461634ff2e1af4c617ee0` | Điều tra lỗi | 0.000 | 10 | KTD-2026-05-0410-Iris2024-C35-A7-error80.xlsx |
| 303 | `wsc-6355c4f658a300f6fdd9d203` | Điều tra lỗi | 0.000 | 7 | KTD-2026-05-0419-Iris2024-C34-A8.4-Hình ảnh bất thường.xlsx |
| 304 | `wsc-662a97440783e685358d6e0f` | Điều tra lỗi | 0.000 | 17 | KTD-2026-05-0428-Iris2024-C35-A1-C6950.xlsx |
| 305 | `wsc-6376bc54c4e43de2427d1343` | Điều tra lỗi | 0.000 | 10 | KTD-2026-05-0459-Iris2024-C34-A8.4-Hình ảnh bất thường.xlsx |
| 306 | `wsc-756ec8bfa45adbec0fffba9f` | Điều tra lỗi | 0.000 | 12 | KTD-2026-05-0460-Iris2024-C33-A11-TLXH NG.xlsx |
| 307 | `wsc-eed4d7d849c2fa03813a4c78` | Điều tra lỗi | 0.000 | 5 | KTD-2026-05-0460-Iris2024-C34-A1-TLBĐ NG.xlsx |
| 308 | `wsc-a9e56b8f8a6fd79a38d2eab9` | Điều tra lỗi | 0.000 | 10 | KTD-2026-05-0469-Iris2024-C33-A5-Màn hình trắng.xlsx |
| 309 | `wsc-67bb63e1fa2e59f1fbc7320d` | Điều tra lỗi | 0.000 | 26 | KTD-2026-05-0477-Iris2024-C33-A1-C6950.xlsx |
| 310 | `wsc-7fda9af6d612cc97e9d47dab` | Điều tra lỗi | 0.000 | 7 | KTD-2026-05-0523-Iris2024-C33-A6-Scan tự động NG.xlsx |
| 311 | `wsc-3c7e472ad026f0847800684d` | Điều tra lỗi | 0.000 | 10 | KTD-2026-06-0525-Iris2024-C35-A6-Không nhận biết size giấy.xlsx |
| 312 | `wsc-c2cb0f8f952f4777a2d305d7` | Điều tra lỗi | 0.000 | 8 | KTD-2026-06-0526-Iris2024-C35-A8.4-Hình ảnh bất thường.xlsx |
| 313 | `wsc-04ae32689118099604c3dee8` | Điều tra lỗi | 0.000 | 14 | KTD-2026-06-0527-Iris2024-C33-A1.2-C3100.xlsx |
| 314 | `wsc-3bca9339ea369420675341e0` | Điều tra lỗi | 0.000 | 13 | KTD-2026-06-0532-Iris2024-C35-A6-Không nhận biết size giấy.xlsx |
| 315 | `wsc-5c456e05b4216ec1bb640530` | Điều tra lỗi | 0.000 | 7 | KTD-2026-06-0540-Iris2024-C35-A2-NG Fax.xlsx |
| 316 | `wsc-4328f237e9ac71f762c4d3d0` | Điều tra lỗi | 0.000 | 11 | KTD-2026-06-0547-Iris2024-C35-A1-Không lên nguồn.xlsx |
| 317 | `wsc-499ff5f1075e6fdada286813` | Điều tra lỗi | 0.000 | 31 | KTD-2026-06-0555-Iris2024-C33-A1-Không lên nguồn.xlsx |
| 318 | `wsc-7968ee2d1b2ebb56a5055dc6` | Điều tra lỗi | 0.000 | 9 | KTD-2026-06-0575-Iris2024-C34-A1-C7902.xlsx |
| 319 | `wsc-91eca8a4697ceb4cd61721c6` | Điều tra lỗi | 0.000 | 13 | KTD-2026-06-0606-Iris2024-C33-A2-C6770.xlsx |
| 320 | `wsc-4938538dbb7dd4f340ddac85` | Điều tra lỗi | 0.000 | 18 | KTD-2026-06-0613-Iris2024-C34-operation-Tablet xước.xlsx |
| 321 | `wsc-c961124d57a87b233f3391f7` | Điều tra lỗi | 0.000 | 7 | KTD-2026-06-0639-Iris2024-C34-C35-Error56.xlsx |
| 322 | `wsc-00438611f8e3f3d244934723` | Điều tra lỗi | 0.000 | 10 | KTD-2026-06-0647-Iris2024-C33-A-JAM4212.xlsx |
| 323 | `wsc-e3d09874a88fa3343bf97a34` | Điều tra lỗi | 0.000 | 6 | KTD-2026-06-0649-Iris2024-C34-A7-C2203.xlsx |
| 324 | `wsc-26c5000f2fe11a6c8c8dd3db` | Điều tra lỗi | 0.000 | 9 | KTD-2026-07-0680-Iris2024-C33-ISU-Điều chỉnh độ quang trục NG.xlsx |
| 325 | `wsc-1c32eff929cdd48b35b92a21` | Điều tra lỗi | 0.000 | 13 | KTD-2026-07-0726-Iris2024-C33-A1.1-ERROR 0801.xlsx |
| 326 | `wsc-263e3d627626ceeabf093628` | Điều tra lỗi | 0.000 | 9 | KTD-2026-07-0783-Iris2024-C33-A1-C6960.xlsx |
| 327 | `wsc-eea9d787f58cff7b019cf4ac` | Điều tra lỗi | 0.000 | 11 | KTD-2026-08-0790-Iris2024-C35-A1-C6770.xlsx |
| 328 | `wsc-8cc0793364bf7baaf4096f17` | Điều tra lỗi | 0.000 | 10 | KTD-2026-08-0803-Iris2024-C33-A1.1-C9540.xlsx |
| 329 | `wsc-75ac58a60b2852018a5224ff` | Điều tra lỗi | 0.000 | 10 | KTD-2026-08-0816-Iris2024-C35-A1-C1950.xlsx |
| 330 | `wsc-a0846d72893f8d178f0d50c9` | Điều tra lỗi | 0.000 | 10 | KTD-2026-08-0857-Iris2024-C33-Hontai1-Kiểm tra thông mạch NG.xlsx |
| 331 | `wsc-2a6baf287b751fcc5b7fa904` | Điều tra lỗi | 0.000 | 11 | KTD-2026-08-0858-Iris2024-C34-A8.1-Hình ảnh bất thường.xlsx |
| 332 | `wsc-85c52c3a94a508811c1e6e81` | Điều tra lỗi | 0.000 | 7 | KTD-2026-08-0861-Iris2024-C34-FUSER-đứt vỏ.xlsx |
| 333 | `wsc-2c54e5a4b9fc88562a95bc3c` | Điều tra lỗi | 0.000 | 9 | KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx |
| 334 | `wsc-4f2b74e844ce3bdd51ab1f63` | Điều tra lỗi | 0.000 | 7 | KTD-2026-08-0876-Iris2024-C33-Drum-xước dây.xlsx |
| 335 | `wsc-a1b8eb7507269dd4f862f709` | Điều tra lỗi | 0.000 | 6 | KTD-2026-08-0877-Iris2024-C34-A1-C0363.xlsx |
| 336 | `wsc-7a4cdc2ca7d0f5e66b619cc1` | Điều tra lỗi | 0.000 | 52 | LCD 302V845023.pdf |
| 337 | `wsc-ad59d7227ae8d8ae5949fe08` | Điều tra lỗi | 0.000 | 46 | LCD 302V845023.pdf |
| 338 | `wsc-6a25f0b37dc4c45c4ad1874f` | Điều tra lỗi | 0.000 | 216 | MAIN_3V2XC47010_04.pdf |
| 339 | `wsc-be102d2a42ad5588247dabc6` | Điều tra lỗi | 0.000 | 283 | MAIN_3V2XC47010_04.pdf |
| 340 | `wsc-4bb9a926160fc7b2687cb7ac` | Điều tra lỗi | 0.000 | 161 | MAIN_3V2XD47010_04.pdf |
| 341 | `wsc-dd752fb64136606c10e80430` | Điều tra lỗi | 0.000 | 283 | MAIN_3V2XD47010_04.pdf |
| 342 | `wsc-28d8058750c5ed4dfe17a4cb` | Điều tra lỗi | 0.000 | 283 | MAIN_3V2XF47010_04.pdf |
| 343 | `wsc-f796eee58f407ed5332b6d2d` | Điều tra lỗi | 0.000 | 178 | MAIN_3V2XF47010_04.pdf |
| 344 | `wsc-c18dcc9ac98cfd1c61aeb358` | Điều tra lỗi | 0.000 | 296 | Maintenance mode 3.xlsx |
| 345 | `wsc-c7aee12699dcc44affb708de` | Điều tra lỗi | 0.000 | 105 | Maintenance mode 3.xlsx |
| 346 | `wsc-ed68732921223c2e64eb1304` | Điều tra lỗi | 0.000 | 10 | matome.xlsx |
| 347 | `wsc-9bd46ef70a6555cd11bb15c4` | Điều tra lỗi | 0.000 | 14 | MIRROR cũ.png |
| 348 | `wsc-8708909fc8c5140efa7389fc` | Điều tra lỗi | 0.000 | 13 | MIRROR mới.png |
| 349 | `wsc-fa75c3428af75175f9f4d5aa` | Điều tra lỗi | 0.000 | 1 | N00137687_実行.pdf |
| 350 | `wsc-0a4be7cf281bc7c2fdb02a13` | Điều tra lỗi | 0.000 | 3 | PA0893D_circuit.pdf |
| 351 | `wsc-b124bf7cf16c2ffe0bd1518a` | Điều tra lỗi | 0.000 | 3 | PA0893D_circuit.pdf |
| 352 | `wsc-239fe1602c23dc5e981d2453` | Điều tra lỗi | 0.000 | 6 | PA1203A_Inner Shift Tray_回路図_20190622.pdf |
| 353 | `wsc-6bd9e3daf4eff90fb12873e3` | Điều tra lỗi | 0.000 | 6 | PA1203A_Inner Shift Tray_回路図_20190622.pdf |
| 354 | `wsc-468d8552f20bef64ca827c16` | Điều tra lỗi | 0.000 | 43 | PWB DRIVE DP.pdf |
| 355 | `wsc-6873e12bb462171a62f81d15` | Điều tra lỗi | 0.000 | 44 | PWB DRIVE DP.pdf |
| 356 | `wsc-06019d8f449eb205c7bcae02` | Điều tra lỗi | 0.000 | 61 | RE    IRIS2020(Low model) -C22 A1- Upsoft OK initial setting - LCD displayed C3501.msg |
| 357 | `wsc-a027dc74a6fb4b600fff5430` | Điều tra lỗi | 0.000 | 10 | RE    IRIS2020(Low model) -C22 A1- Upsoft OK initial setting - LCD displayed C3501.msg |
| 358 | `wsc-90c0903167e4e2bc194e328d` | Điều tra lỗi | 0.000 | 46 | RE  C7303エラー  IRIS2020 .msg |
| 359 | `wsc-e30dd5059219c220a19c6f19` | Điều tra lỗi | 0.000 | 269 | RE  C7303エラー  IRIS2020 .msg |
| 360 | `wsc-6941cdac7ea87d001251b851` | Điều tra lỗi | 0.000 | 14 | RE  PP生産不具合_C6620IHコアモータ回転異常.msg |
| 361 | `wsc-91aab1a0a88120f2204dfa99` | Điều tra lỗi | 0.000 | 104 | RE  PP生産不具合_C6620IHコアモータ回転異常.msg |
| 362 | `wsc-00557b84e95c9fb3504e582e` | Điều tra lỗi | 0.000 | 42 | RE  「Iris2020下位」　C6900 エラー発生RE  Log C6900_QA.msg |
| 363 | `wsc-c882dc2eaf6199953566578f` | Điều tra lỗi | 0.000 | 135 | RE  「Iris2020下位」　C6900 エラー発生RE  Log C6900_QA.msg |
| 364 | `wsc-0c3d3d096d5b7b9a8552a166` | Điều tra lỗi | 0.000 | 111 | RE_ 【出荷検査】Iris2024  _HOLD_.msg |
| 365 | `wsc-6545fbd02cf63f9124d579cb` | Điều tra lỗi | 0.000 | 24 | RE_ 【出荷検査】Iris2024  _HOLD_.msg |
| 366 | `wsc-325427cfcc26cf128db2284c` | Điều tra lỗi | 0.000 | 11 | RX ASSY_303TD01010.pdf |
| 367 | `wsc-900d495916697dad42a0e8dd` | Điều tra lỗi | 0.000 | 11 | RX ASSY_303TD01010.pdf |
| 368 | `wsc-8266003e7836cb48dd8eb71c` | Điều tra lỗi | 0.000 | 26 | SCT自動調整エラーコード一覧_140221.xls |
| 369 | `wsc-7dc11a30e67f3b914854c443` | Điều tra lỗi | 0.000 | 59 | SHD_7PA1334A.pdf |
| 370 | `wsc-9430e724e29edd1200a60420` | Điều tra lỗi | 0.000 | 79 | SHD_7PA1334A.pdf |
| 371 | `wsc-80ec36f258a2e8c9cf0f63f6` | Điều tra lỗi | 0.000 | 82 | T02XC47110_PWB VIDEO ASSY_DMT回路図.pdf |
| 372 | `wsc-ac4003964ded9ce76832613b` | Điều tra lỗi | 0.000 | 61 | T02XC47110_PWB VIDEO ASSY_DMT回路図.pdf |
| 373 | `wsc-b645bfc9b278ac6d11ffa21c` | Điều tra lỗi | 0.000 | 81 | Tab led cam ung.pdf |
| 374 | `wsc-fb3c0c9d41407d55a8dbb2fe` | Điều tra lỗi | 0.000 | 64 | Tab led cam ung.pdf |
| 375 | `wsc-09824ff6e09ca255c727537b` | Điều tra lỗi | 0.000 | 14 | tape 2 (27) master.png |
| 376 | `wsc-497b85eb59ff95be7162016f` | Điều tra lỗi | 0.000 | 14 | tape 2 (27).png |
| 377 | `wsc-fb277aa9484017b30147f7bd` | Điều tra lỗi | 0.000 | 14 | tape 2 (40).png |
| 378 | `wsc-e1833b154abdca909a95f861` | Điều tra lỗi | 0.000 | 14 | tape 3 (27).png |
| 379 | `wsc-8f9b210b6aa7127695267b2a` | Điều tra lỗi | 0.000 | 13 | tape 40 (go duoi).png |
| 380 | `wsc-1696cf072a16a43c802ff100` | Điều tra lỗi | 0.000 | 1 | TEK00001.BMP |
| 381 | `wsc-6d14cd1be7bda0d92499e2ae` | Điều tra lỗi | 0.000 | 1 | TEK00002.BMP |
| 382 | `wsc-921d7a6025bee08cedda051d` | Điều tra lỗi | 0.000 | 3272 | tổng hợp dữ liệu dán tape.xlsx |
| 383 | `wsc-0537fd89ce0396da6ebbdec6` | Điều tra lỗi | 0.000 | 15 | USB HUB_3V2XC47160.pdf |
| 384 | `wsc-85ac8b249e20debfa290afcd` | Điều tra lỗi | 0.000 | 16 | USB HUB_3V2XC47160.pdf |
| 385 | `wsc-015067b75dc12e2770b7d8cb` | Điều tra lỗi | 0.000 | 1 | wsc-015067b75dc12e2770b7d8cb.txt |
| 386 | `wsc-037c28842e209b28625d6157` | Điều tra lỗi | 0.000 | 4 | wsc-037c28842e209b28625d6157.txt |
| 387 | `wsc-08d8d7616f71e6b9ae67940f` | Điều tra lỗi | 0.000 | 41 | wsc-08d8d7616f71e6b9ae67940f.txt |
| 388 | `wsc-097fe6a008b410dc299a0948` | Điều tra lỗi | 0.000 | 11 | wsc-097fe6a008b410dc299a0948.txt |
| 389 | `wsc-0a49389b70f1e9592670c5e9` | Điều tra lỗi | 0.000 | 1 | wsc-0a49389b70f1e9592670c5e9.txt |
| 390 | `wsc-118d0600a2a94d418f2880ac` | Điều tra lỗi | 0.000 | 28 | wsc-118d0600a2a94d418f2880ac.txt |
| 391 | `wsc-11f5fbf5720d445b40967b4f` | Điều tra lỗi | 0.000 | 4 | wsc-11f5fbf5720d445b40967b4f.txt |
| 392 | `wsc-149cac9d8b129f8244b616ef` | Điều tra lỗi | 0.000 | 1 | wsc-149cac9d8b129f8244b616ef.txt |
| 393 | `wsc-1526cbd0e45f7c07240030b8` | Điều tra lỗi | 0.000 | 44 | wsc-1526cbd0e45f7c07240030b8.txt |
| 394 | `wsc-18c17803678e5d71f0cbb2ba` | Điều tra lỗi | 0.000 | 1 | wsc-18c17803678e5d71f0cbb2ba.txt |
| 395 | `wsc-1b661fb170798e66bb7de3a1` | Điều tra lỗi | 0.000 | 26 | wsc-1b661fb170798e66bb7de3a1.txt |
| 396 | `wsc-1b737eb997502d0f546982dc` | Điều tra lỗi | 0.000 | 20 | wsc-1b737eb997502d0f546982dc.txt |
| 397 | `wsc-1d6a06690fd87180c59240d0` | Điều tra lỗi | 0.000 | 4 | wsc-1d6a06690fd87180c59240d0.txt |
| 398 | `wsc-1d6dc72ebb72350e220dfb07` | Điều tra lỗi | 0.000 | 1 | wsc-1d6dc72ebb72350e220dfb07.txt |
| 399 | `wsc-2d62e0b3a3ca889c7679ed93` | Điều tra lỗi | 0.000 | 8 | wsc-2d62e0b3a3ca889c7679ed93.txt |
| 400 | `wsc-38c83e012535c1c00a21b3a5` | Điều tra lỗi | 0.000 | 36 | wsc-38c83e012535c1c00a21b3a5.txt |
| 401 | `wsc-42843eb6ca4459ae3af6b657` | Điều tra lỗi | 0.000 | 1 | wsc-42843eb6ca4459ae3af6b657.txt |
| 402 | `wsc-431e31fbbc3df5fc16f444cb` | Điều tra lỗi | 0.000 | 1 | wsc-431e31fbbc3df5fc16f444cb.txt |
| 403 | `wsc-4600afa0ca80041712e8c65f` | Điều tra lỗi | 0.000 | 4 | wsc-4600afa0ca80041712e8c65f.txt |
| 404 | `wsc-492485e50bac291bf4c81cc4` | Điều tra lỗi | 0.000 | 1 | wsc-492485e50bac291bf4c81cc4.txt |
| 405 | `wsc-4cbd21f3ccab9c9ea52161fa` | Điều tra lỗi | 0.000 | 1 | wsc-4cbd21f3ccab9c9ea52161fa.txt |
| 406 | `wsc-4cc1bf837aa6c9844d67eb4c` | Điều tra lỗi | 0.000 | 38 | wsc-4cc1bf837aa6c9844d67eb4c.txt |
| 407 | `wsc-4e59cb5f495278f0be7fa444` | Điều tra lỗi | 0.000 | 1 | wsc-4e59cb5f495278f0be7fa444.txt |
| 408 | `wsc-4ed67081b49075eed077ebf7` | Điều tra lỗi | 0.000 | 1 | wsc-4ed67081b49075eed077ebf7.txt |
| 409 | `wsc-51548ca220d6ccc9ec419c8c` | Điều tra lỗi | 0.000 | 59 | wsc-51548ca220d6ccc9ec419c8c.txt |
| 410 | `wsc-5b78db8c9cc2ad9844a9a0d7` | Điều tra lỗi | 0.000 | 1 | wsc-5b78db8c9cc2ad9844a9a0d7.txt |
| 411 | `wsc-5d2f610a69cf193a6d06c754` | Điều tra lỗi | 0.000 | 36 | wsc-5d2f610a69cf193a6d06c754.txt |
| 412 | `wsc-5f2696c9a22072e7d4873267` | Điều tra lỗi | 0.000 | 1 | wsc-5f2696c9a22072e7d4873267.txt |
| 413 | `wsc-5f357714c9ab95fe58b8fff6` | Điều tra lỗi | 0.000 | 17 | wsc-5f357714c9ab95fe58b8fff6.txt |
| 414 | `wsc-624b7034af500a849305d8bf` | Điều tra lỗi | 0.000 | 22 | wsc-624b7034af500a849305d8bf.txt |
| 415 | `wsc-65074328893666b1fbd9b4aa` | Điều tra lỗi | 0.000 | 3 | wsc-65074328893666b1fbd9b4aa.txt |
| 416 | `wsc-6c84807638a179552dd437ce` | Điều tra lỗi | 0.000 | 1 | wsc-6c84807638a179552dd437ce.txt |
| 417 | `wsc-71abdd06f47c205da102e908` | Điều tra lỗi | 0.000 | 1 | wsc-71abdd06f47c205da102e908.txt |
| 418 | `wsc-750990be3801b81970805644` | Điều tra lỗi | 0.000 | 4 | wsc-750990be3801b81970805644.txt |
| 419 | `wsc-762cd98f79d4ad1a0c235393` | Điều tra lỗi | 0.000 | 22 | wsc-762cd98f79d4ad1a0c235393.txt |
| 420 | `wsc-8782bf3e41a80998543bc9dd` | Điều tra lỗi | 0.000 | 1 | wsc-8782bf3e41a80998543bc9dd.txt |
| 421 | `wsc-8ce71e2a14d81de80d196655` | Điều tra lỗi | 0.000 | 2 | wsc-8ce71e2a14d81de80d196655.txt |
| 422 | `wsc-8f9caa49cee9d05bb1f76bd2` | Điều tra lỗi | 0.000 | 26 | wsc-8f9caa49cee9d05bb1f76bd2.txt |
| 423 | `wsc-90597a45cd475fa1a42d442d` | Điều tra lỗi | 0.000 | 1 | wsc-90597a45cd475fa1a42d442d.txt |
| 424 | `wsc-989a0376f54d1fc7ebc90698` | Điều tra lỗi | 0.000 | 36 | wsc-989a0376f54d1fc7ebc90698.txt |
| 425 | `wsc-9abe0b8f8e644d009d771d5a` | Điều tra lỗi | 0.000 | 11 | wsc-9abe0b8f8e644d009d771d5a.txt |
| 426 | `wsc-9e9831c8c58795058809bf95` | Điều tra lỗi | 0.000 | 1 | wsc-9e9831c8c58795058809bf95.txt |
| 427 | `wsc-a36e39c1d9713f21dc65bcaf` | Điều tra lỗi | 0.000 | 1 | wsc-a36e39c1d9713f21dc65bcaf.txt |
| 428 | `wsc-aa48e2b47a8c52c66c835e70` | Điều tra lỗi | 0.000 | 1 | wsc-aa48e2b47a8c52c66c835e70.txt |
| 429 | `wsc-b2fb28663b5d62bab155737c` | Điều tra lỗi | 0.000 | 4 | wsc-b2fb28663b5d62bab155737c.txt |
| 430 | `wsc-be0e15bdc0524321e7587d7c` | Điều tra lỗi | 0.000 | 1 | wsc-be0e15bdc0524321e7587d7c.txt |
| 431 | `wsc-bfbdd33cacd73c3e69d1ca2b` | Điều tra lỗi | 0.000 | 4 | wsc-bfbdd33cacd73c3e69d1ca2b.txt |
| 432 | `wsc-c4f19c08de138e4dfeeceacc` | Điều tra lỗi | 0.000 | 1 | wsc-c4f19c08de138e4dfeeceacc.txt |
| 433 | `wsc-c7377cc9661005aa4d35d54e` | Điều tra lỗi | 0.000 | 3 | wsc-c7377cc9661005aa4d35d54e.txt |
| 434 | `wsc-d320e16fa80ee7e311b42fb7` | Điều tra lỗi | 0.000 | 4 | wsc-d320e16fa80ee7e311b42fb7.txt |
| 435 | `wsc-d489e437c9abecd020ee12ba` | Điều tra lỗi | 0.000 | 36 | wsc-d489e437c9abecd020ee12ba.txt |
| 436 | `wsc-d51ca7a46bac26fe55714eba` | Điều tra lỗi | 0.000 | 1 | wsc-d51ca7a46bac26fe55714eba.txt |
| 437 | `wsc-da1844282c07cff93145d49f` | Điều tra lỗi | 0.000 | 1 | wsc-da1844282c07cff93145d49f.txt |
| 438 | `wsc-db6bb8495e13e16cd73fe9aa` | Điều tra lỗi | 0.000 | 1 | wsc-db6bb8495e13e16cd73fe9aa.txt |
| 439 | `wsc-ddff4330d33132af9cde8bcf` | Điều tra lỗi | 0.000 | 4 | wsc-ddff4330d33132af9cde8bcf.txt |
| 440 | `wsc-e5f2338de8fbfdbd4faefe63` | Điều tra lỗi | 0.000 | 1 | wsc-e5f2338de8fbfdbd4faefe63.txt |
| 441 | `wsc-e9d27b6c728c286f2cf0ef93` | Điều tra lỗi | 0.000 | 14 | wsc-e9d27b6c728c286f2cf0ef93.txt |
| 442 | `wsc-eab6e69c0a9795201f575c88` | Điều tra lỗi | 0.000 | 1 | wsc-eab6e69c0a9795201f575c88.txt |
| 443 | `wsc-edb70d31441621a7baaa28c2` | Điều tra lỗi | 0.000 | 4 | wsc-edb70d31441621a7baaa28c2.txt |
| 444 | `wsc-ef469ab3d32e4c1060e9f947` | Điều tra lỗi | 0.000 | 4 | wsc-ef469ab3d32e4c1060e9f947.txt |
| 445 | `wsc-f5e16c8261a4f585e58dd705` | Điều tra lỗi | 0.000 | 1 | wsc-f5e16c8261a4f585e58dd705.txt |
| 446 | `wsc-fb5c095f5d8bcfa80db7805b` | Điều tra lỗi | 0.000 | 1 | wsc-fb5c095f5d8bcfa80db7805b.txt |
| 447 | `wsc-2979c545c0c2ee3e8a5f972f` | Điều tra lỗi | 0.000 | 6 | 【DRBFM】Iris2020_C6610対応_hook_fuser_release_r.xlsx |
| 448 | `wsc-6d58d6c9477720fb1229436c` | Điều tra lỗi | 0.000 | 27 | 【DRBFM】Iris2020_C6610対応_hook_fuser_release_r.xlsx |
| 449 | `wsc-641135cb9ce4d911661d664b` | Điều tra lỗi | 0.000 | 62 | 【Iris2020】PF全体配線図.xlsx |
| 450 | `wsc-c30c3e4f14dea65ed0d89754` | Điều tra lỗi | 0.000 | 641 | 【Iris2020】PF全体配線図.xlsx |
| 451 | `wsc-4db8ddc1e8392dcf3f73a468` | Điều tra lỗi | 0.000 | 8 | 信号　7303.xlsx |
| 452 | `wsc-9721b4691a00af18092b3b38` | Điều tra lỗi | 0.333 | 122 | FW  IRIS2020 A-6工程打印RCG画像时发生C2103  2台.msg |
| 453 | `wsc-591aa0bdb18b4341676e518a` | Điều tra lỗi | 0.333 | 17 | KTD-2026-07-0669-Iris2024-C33-A1-C6960.xlsx |

## 4. Chưa làm

- Chưa tách thật ra `collections_new`.
- Chưa tạo collection `lsu` / `dieu_tra_loi` / `mom`.
- Chưa bật `AIOS_DOMAIN_ROUTING_ENABLED`.
- Chưa hỏi đáp thử, chưa thử rollback.
- File kho `tri_thuc` cũ không bị ghi. App được mở lại **không** bật cờ, để hỏi đáp vẫn dùng kho cũ.

## 5. Cần user / Muse quyết

1. Rà 451 tài liệu confidence 0: giữ fallback Điều tra lỗi, hay khoanh lại trước khi tách.
2. Nếu chấp nhận phân bố này, trả lời rõ để OMP chạy Bước 2 (tách thật, chỉ ghi kho mới, không đụng file cũ).

