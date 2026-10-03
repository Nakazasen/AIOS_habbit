# Báo cáo vé `SCAN-O-D` — kiểm kê ổ D (chỉ đọc)

- Máy: `h410asrock`, 2026-10-03 20:09–20:29 +07.
- Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`, không force-push.
- Kết quả: **đã kiểm kê xong, không xóa, không sửa, không di chuyển file nào.**

## 0. Cổng gate

- Watcher (`D:\Sandbox\Vong_lap_giao_viec\watcher_state.json`) tự mở OMP **`LAUNCH 1/4` lúc 2026-10-03 20:08:16**, `launchStallCount=1`.
- Điều kiện mở đã có ngay: đúng máy nhà, ổ D đọc được. **Không** dùng nhánh 4 lần watcher / `cho-muse`, không quay no-op.

## 1. Cách làm và chứng minh chỉ đọc

- Chỉ `scandir` + `stat` để lấy tên, kích thước, mtime. SHA-256 đọc từng khối, không ghi.
- Không mở nội dung tài liệu công ty. Không chạy `integrity_check` (lệnh đó đọc sâu hơn metadata/SHA). Không ingest, không embed.
- 366 đường `*.sqlite` / tên có `.sqlite`: size và mtime **trước = sau**. 184 inode thật; 182 cặp còn lại là cùng một file nhìn qua junction.
- File zip Điều chỉnh: size/mtime trước = sau (858.190.286 byte).
- Kho production trên ổ C (đối chiếu, không nằm trên D): size/mtime trước = sau (2.942.201.856 byte, 2026-10-01 08:27:27).
- Không có lệnh xóa, đổi tên, ghi đè trên ổ D. Artifact quét nằm ở `C:\tmp\scan-o-d\` (ngoài ổ dữ liệu).

## 2. Cây cấp 1 và nhánh lớn

Dung lượng dưới đây là tổng kích thước từng mục thư mục nhìn thấy (cộng `st_size`), không phải số đĩa đã dùng. Ổ D: tổng 250.057.060.352 byte, đã dùng 178.554.191.872 byte, còn trống 71.502.868.480 byte (~66,6 GB).

Tổng cộng mục thư mục = 214.628.867.169 byte, cao hơn số đã dùng khoảng 36,3 GB. Khoảng lệch đó đúng bằng `D:\.pnpm-store`: junction `projects\f211b6f0ba9b2334d1ca33631af131a8` trỏ `\\?\D:\Sandbox\AIOS_habbit` (`os.readlink`). Cùng inode, không phải bản sao thứ hai. Trừ junction thì còn khoảng 178,28 GB, sát số đĩa đã dùng. Phần lệch nhỏ còn lại là `System Volume Information` (không đọc được) và vài thư mục từ chối truy cập.

| Nhánh cấp 1 | Byte | GB | Ghi chú |
| --- | ---: | ---: | --- |
| `1.laptopdata` | 85.407.553.436 | 79,54 GB | dữ liệu cá nhân — chỉ tên/kích thước, không mở file |
| `Sandbox` | 75.887.005.813 | 70,68 GB | gồm repo AIOS và vài dự án khác |
| `.pnpm-store` | 36.348.266.223 | 33,85 GB | junction trùng `AIOS_habbit`, không chiếm thêm đĩa |
| `giao trinh day tieng nhat` | 5.203.938.893 | 4,85 GB | ngoài AIOS |
| `Zalo Data` | 4.535.066.406 | 4,22 GB | ngoài AIOS |
| `Kế hoạch AIOS_habbit` | 2.942.318.841 | 2,74 GB | gần như toàn bộ là file sqlite tạm, xem mục 6 |
| `c` | 1.562.144.291 | 1,45 GB | chỉ có `Users`, mục lạ |
| `Thư viện Calibre` | 1.532.376.453 | 1,43 GB | ngoài AIOS |
| `NVIDIA_Driver` | 722.841.504 | 0,67 GB | dưới 1 GB |
| `tmp` | 213.811.139 | 0,20 GB | gần như toàn bộ là `ux-chat-core` |
| `2.newdata` | 128.478.186 | 0,12 GB | ngoài AIOS |
| `phanmemPython` | 66.952.516 | 0,06 GB | ngoài AIOS |
| `t` | 1.406.300 | 0,00 GB | `ToolJet`, dưới 1 GB |
| `$RECYCLE.BIN` | 129 | 0,00 GB | rỗng thực tế |
| `System Volume Information` | 0 | 0,00 GB | không đọc được, không sửa quyền |

File nằm ngay gốc ổ D (không mở nội dung): `Giấy khai sinh.pdf` 1.593.216 byte, `Nihongo_SouMatome_N1-Goi.pdf` 63.741.962 byte, `Phieu-tap-to-so-1-10.pdf` 11.371.861 byte.

### Nhánh cấp 2 trên 1 GB

| Nhánh | Byte | GB |
| --- | ---: | ---: |
| `1.laptopdata\3. kyocera_document` | 41.102.612.424 | 38,28 GB |
| `1.laptopdata\2. JLPT` | 21.005.244.379 | 19,56 GB |
| `1.laptopdata\1. photo_data` | 18.561.052.479 | 17,29 GB |
| `1.laptopdata\4. electronic book` | 3.866.728.815 | 3,60 GB |
| `Sandbox\AIOS_habbit` | 36.338.609.531 | 33,84 GB |
| `Sandbox\VideoYoutube` | 25.299.628.160 | 23,56 GB |
| `Sandbox\MP2027` | 4.905.076.444 | 4,57 GB |
| `Sandbox\phantichphanmemdc` | 4.251.806.675 | 3,96 GB |
| `Sandbox\.venv` | 1.338.481.273 | 1,25 GB |
| `Sandbox\reference_repos` | 1.328.360.243 | 1,24 GB |
| `Sandbox\leetcode_mastery` | 1.298.775.712 | 1,21 GB |
| `giao trinh day tieng nhat\tailieutiengnhat` | 1.681.235.739 | 1,57 GB |
| `giao trinh day tieng nhat\giaotrinhdaytiengnhatsocap` | 1.317.927.488 | 1,23 GB |
| `Zalo Data\media` | 4.162.525.253 | 3,88 GB |
| `Kế hoạch AIOS_habbit\aios_thu_vien` | 2.942.203.010 | 2,74 GB |
| `c\Users` | 1.562.144.291 | 1,45 GB |
| `Thư viện Calibre\Chua xac dinh` | 1.083.254.048 | 1,01 GB |
| `.pnpm-store\v11` | 36.348.266.223 | 33,85 GB |

`Sandbox\MOM_WMS_QLLSSX` = 332.453.404 byte (nguồn, dưới 1 GB, không đề xuất xóa).

### Trong `AIOS_habbit` (cấp tiếp, trên 100 MB)

| Nhánh | Byte | GB |
| --- | ---: | ---: |
| `local_runs` | 17.629.531.672 | 16,42 GB |
| `models` | 5.761.883.616 | 5,37 GB |
| `.git` | 2.841.233.975 | 2,65 GB |
| `.venv` | 2.263.914.512 | 2,11 GB |
| `Tài liệu của tất cả dòng máy` | 2.069.773.612 | 1,93 GB |
| `vendor` | 1.883.355.261 | 1,75 GB |
| `.venv-rag-compat` | 1.674.487.483 | 1,56 GB |
| `.venv-rag` | 1.326.346.716 | 1,24 GB |
| `.tmp` | 305.411.512 | 0,28 GB |
| `graphify-out` | 207.251.734 | 0,19 GB |
| `scratch` | 123.890.447 | 0,12 GB |

`local_runs` chia tiếp: `workspace_chat_rag_v2_canary` 9.296.349.251 byte, `retrieval_models` 4.588.663.876 byte, `workspace_chat_rag_v2_production` 2.589.809.793 byte. Phần còn lại là cache gate/battle, mỗi nhánh dưới 220 MB.

## 3. Đối chiếu danh mục đã biết

| Mục | Đường dẫn | Byte | SHA-256 | Kết luận |
| --- | --- | ---: | --- | --- |
| Kho production đang chạy (ổ C, không phải D) | `C:\AIOS_workspace_chat_rag_v2_production\...\tri_thuc\library.sqlite` | 2.942.201.856 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | khớp ghim `45eb0e07…b7c0` |
| Bản đông trên D (rollback sau `move-index-c`) | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | 2.552.659.968 | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` | khớp ghim `062ec090…4ef8ca` |
| File tạm cùng kích thước production | `D:\Kế hoạch AIOS_habbit\aios_thu_vien\.library.sqlite.ba9796c9808548f7a844f182c68e7d35.tmp` | 2.942.201.856 | `aae0943e2c568763208fd72095339cfebe84e24b88fe696ead21db4c22ee5425` | cùng số byte với kho C nhưng **SHA khác** — không phải bản sao production |
| Zip Điều chỉnh | `D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Điều chỉnh-20260905T053942Z-1-001.zip` | 858.190.286 | `f18bbae2c0c472fe063cd80543802e8677512012a8aa4606d8c3d09ca8ca18b7` | khớp ghim `f18bbae2…18b7` |
| Staging GPU-262 (lệnh giữ) | `C:\AIOS_staging_262\library.sqlite` | 1.005.621.248 | không hash lại (không nằm trên D) | còn file + bản `.bak-20260930-gpu262-preembed` 834.904.064 byte. **Không có bản nào trên ổ D.** |
| Staging GPU-262b / GPU-DC | `C:\AIOS_staging_262b`, `C:\AIOS_staging_dc` | còn đủ `library.sqlite` + delta | không hash lại | không nằm trên D, không đụng |
| Model ONNX fp32 | `D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32` | 2.289.625.694 | sidecar `9f81075f…b11093` | khớp ghim đã biết, giữ |

## 4. Kho sqlite trên ổ D

Đủ **366** đường, **184** inode, không thiếu SHA, không có `sha_error`. Bảng dưới là 184 file thật trong repo và thư mục Kế hoạch. Mỗi file trong repo còn một đường gương:

`D:\.pnpm-store\v11\projects\f211b6f0ba9b2334d1ca33631af131a8\` + phần đường dẫn sau `AIOS_habbit\`

Đã kiểm từng cặp: cùng inode, cùng SHA. Hai file trong `Kế hoạch AIOS_habbit` không có gương.

| Byte | mtime | SHA-256 | Đường dẫn |
| ---: | --- | --- | --- |
| 2.942.201.856 | 2026-10-02 07:04:38 | `aae0943e2c568763208fd72095339cfebe84e24b88fe696ead21db4c22ee5425` | `D:\Kế hoạch AIOS_habbit\aios_thu_vien\.library.sqlite.ba9796c9808548f7a844f182c68e7d35.tmp` |
| 2.552.659.968 | 2026-09-28 05:55:03 | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` |
| 1.750.740.992 | 2026-09-27 16:48:22 | `31e80a9497b3c64f8bfd7ede0233f6eaf0526f55c78d5d694bfccdaf69452fda` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite` |
| 1.698.164.736 | 2026-09-27 15:36:51 | `47e15665ea7d5949a8c1b47fe138e5dc25b72c3b82bbdd277d6b36b72ed28843` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260927-153511-g1gpu` |
| 1.635.676.160 | 2026-09-27 08:36:19 | `caf8e69ee6826ebf056daedab42397f4b60871900d23bad11eafb38b24bba509` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260927-083508-938555` |
| 1.574.125.568 | 2026-09-27 08:09:35 | `6ad678ab3b0fa55186661da3937a14554e84721f265432b3a92abf40221a8d07` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260927-080904-192041` |
| 872.464.384 | 2026-09-27 07:59:48 | `e722c50002e6c7934f6716bb4e1ba4e711c2169c0c449e1fa0e6f88e7ca288bb` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260927-075907-450330` |
| 864.022.528 | 2026-09-27 07:49:03 | `b933d06c7feae962327d21805bf66a23c1a0eb3fc0504bed04bc6e2891c15fca` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260927-074835-812794` |
| 755.052.544 | 2026-09-27 07:37:32 | `cc5b07dd64b21b50d8eb324c93e65deafe5242b953e930a2cfbd49b9c4f8c81d` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260927-073716-457599` |
| 152.707.072 | 2026-09-25 06:21:25 | `e02ed7caf1037c191251b8d92103be48f9719b52fa24fd54c37ecd3dbd323396` | `D:\Sandbox\AIOS_habbit\.tmp\fix1_bench\real_10081.sqlite` |
| 151.552.000 | 2026-08-15 12:22:51 | `e2479f72821c5cd5d2dc330da97c68ae9a5487f80cab4035b9da8016a78cd068` | `D:\Sandbox\AIOS_habbit\.tmp\fix1_bench\real_9919.sqlite` |
| 151.552.000 | 2026-08-15 12:22:51 | `e2479f72821c5cd5d2dc330da97c68ae9a5487f80cab4035b9da8016a78cd068` | `D:\Sandbox\AIOS_habbit\local_runs\battle_rag_v2_index_cache\bffc6fac625657acdad91b172079034cb8ec0b6ac403ee48e6ae4f56ef8bd20d\rag_v2_dev.sqlite` |
| 87.343.104 | 2026-08-16 18:52:23 | `310fcf7c7f7d739aa2c1bfde558ff31942e7c61385392ebd828bad138d47a1d0` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_current\SELECTED-bge_m3_hybrid-1786880512-e33e5670\lexical_baseline_runtime\rag_v2_dev.sqlite` |
| 87.339.008 | 2026-08-16 19:04:26 | `a026c681532f1a8b0f27fbdd0a96deacec40a10ce69aeb142657396bf3b3abc2` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_current_rerun\SELECTED-bge_m3_hybrid-1786881247-e33e5670\lexical_baseline_runtime\rag_v2_dev.sqlite` |
| 70.201.344 | 2026-08-16 23:13:20 | `08ab185db73ed044b673f9caa3535ab8022633cb44e94ca7b69c58b7b8040157` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_compacted_batch4_corrected\SELECTED-bge_m3_hybrid-1786885621-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite` |
| 68.988.928 | 2026-08-22 14:20:48 | `f67a07f691a5448c55ed0d050d3fa5a82b6b1fc54d139012d8ed320ed825198d` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_restore\SELECTED-bge_m3_hybrid-1787382520-e33e5670\lexical_baseline_runtime\rag_v2_dev.sqlite` |
| 68.972.544 | 2026-08-22 14:41:09 | `44e840f883ec44f5ee739558a2675ee8e1215622d66e012b26b32a2ef80c4942` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_restore\SELECTED-bge_m3_hybrid-1787383502-e33e5670\lexical_baseline_runtime\rag_v2_dev.sqlite` |
| 68.968.448 | 2026-08-22 14:23:28 | `7788a59f73b2efb46c514379c40b5e11c8df6f65b671e473564bf4793ff2b9e0` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_restore\SELECTED-bge_m3_hybrid-1787382661-e33e5670\lexical_baseline_runtime\rag_v2_dev.sqlite` |
| 60.452.864 | 2026-08-16 20:18:03 | `dd97d32db3507b4b0e40c7309b57f6ca64b456856a8510eb4e1d62679fc00d6d` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_compacted_batch4_corrected\SELECTED-bge_m3_hybrid-1786885621-e33e5670\lexical_baseline_runtime\rag_v2_dev.sqlite` |
| 60.444.672 | 2026-08-16 19:54:31 | `d1b6922175bda56dd0e625dec38f822f8c6acbcebb066d5fc321335dde776918` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_compacted_batch4\SELECTED-bge_m3_hybrid-1786884194-e33e5670\lexical_baseline_runtime\rag_v2_dev.sqlite` |
| 60.436.480 | 2026-08-16 19:33:57 | `08b5ee0ee5f9087ed3c8059ca1389ee2a6aacbd8fe056aa66f205adaa5c7deca` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_compacted\SELECTED-bge_m3_hybrid-1786882465-e33e5670\lexical_baseline_runtime\rag_v2_dev.sqlite` |
| 48.623.616 | 2026-09-12 22:49:20 | `4b874fb0f38729f9d7464de0bcd05426bf4fcb38fe5f8f42b02113c54e4a7845` | `D:\Sandbox\AIOS_habbit\local_runs\battle_workspace_stage_cache\00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074\bge_m3_hybrid\workspace_chat.sqlite` |
| 40.140.800 | 2026-08-16 23:22:41 | `ac859ead2a010a27cc947c1bb17bfc6d33d6eae69e752d5013b1ded74bdc1abe` | `D:\Sandbox\AIOS_habbit\local_runs\battle_workspace_stage_cache\00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074\bge_m3_hybrid\workspace_chat.before_actual_matecon_ui_repair.sqlite` |
| 39.440.384 | 2026-08-15 17:25:53 | `38fc425355499bb209f08ce2afecb6acff28195891c62dcaa27d4ba2d7a358ab` | `D:\Sandbox\AIOS_habbit\local_runs\battle_workspace_stage_cache\00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074\bge_m3_hybrid\workspace_chat.before_matecon_vector_repair.sqlite` |
| 30.375.936 | 2026-08-22 22:03:14 | `2cf2dcd3bad643c226f0355b7342523237a3d2392adf61f2a2d9dc9d58ea10b6` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\workspace_chat.sqlite` |
| 29.851.648 | 2026-09-27 07:34:11 | `c86a610d809a53165832dcafae80d8d911cb64d1e86af8f27b3511dc339cc71e` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260927-073411-497891` |
| 28.753.920 | 2026-09-19 22:32:03 | `08c2b5c854b70471c7036f14456f3eedc65eee4352ba5acd7a2b269cb0095dec` | `D:\Sandbox\AIOS_habbit\local_cases\library_backups\backup_tri_thuc_20260919_223202_BAK-7762385F59\library.sqlite` |
| 28.753.920 | 2026-09-13 21:16:22 | `844cf18e51a62d82a7a323525975a48a44d77e5a29c86b00e54d2ba06142a1ec` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260927-023546` |
| 18.636.800 | 2026-08-13 23:46:12 | `3d062148304795f073cd5605aa3e1f0165567988a2eb39c59b95d1c6a482890b` | `D:\Sandbox\AIOS_habbit\local_runs\bq01_bq02_adapter_diagnostic\workspace_runtime\bge_m3_hybrid\workspace_chat.sqlite` |
| 14.868.480 | 2026-08-15 00:27:44 | `1abea261993b2bd8f3ed650cde6ebc468ea548219445f53a61c1c0e8621b193a` | `D:\Sandbox\AIOS_habbit\local_runs\battle_workspace_stage_cache\e94ab2ee6914375f1b5be7d7229e7b446ea7fa706433d4a0c444be3ded970dce\bge_m3_hybrid\workspace_chat.sqlite` |
| 12.652.544 | 2026-09-26 14:45:35 | `1b13be430b56702123ebc75efce031bb7a7bf93ba1c7d47cdd9e514608d43a66` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260926-1445` |
| 9.764.864 | 2026-09-26 11:42:06 | `84503c690974ca8b9f5eb64658d5592695a4c580bbed11ad8d42fdc82e13555d` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260926-1142` |
| 9.588.736 | 2026-09-26 08:42:42 | `d4f461ca24de7d83325027f4118b89e4f61f450cca1ada75956c9229f2839366` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20260926-0842` |
| 7.176.192 | 2026-09-27 11:28:17 | `55afd1a9fbb216510a22abaaffce18bb849923e138851cb9a10a08fb02dc9002` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\workspace_chat.sqlite` |
| 6.447.104 | 2026-08-22 15:04:51 | `7c6945e39b960be74d2e9040250d0e7c83ce0cc7a4c0632149231a4297c40d55` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_restore\SELECTED-bge_m3_hybrid-1787383502-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite` |
| 5.148.672 | 2026-08-16 20:05:40 | `06f604d71b6251d08de590c2b73601ea83d60d4ffb7b0050e6820b20aaa6806e` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_compacted_batch4\SELECTED-bge_m3_hybrid-1786884194-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite` |
| 3.698.688 | 2026-09-20 09:31:17 | `9817cc17363bda9db2e7d6b64f1981febbb26d869449706c257382e648649250` | `D:\Sandbox\AIOS_habbit\local_runs\thread_answer_probe\runtime\rag_v2_dev.sqlite` |
| 2.252.800 | 2026-08-29 21:01:29 | `c0e9947cb3030a86767da5a55d4c8ad6caec41a882bb8bf56ac3157acf530107` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e1_v2_run1\indexes\chunk-eval-1788011745\chunk_eval.sqlite` |
| 2.252.800 | 2026-08-29 21:20:46 | `0915ca207bb6339dedf87940a5ac75bdafb5f77b618b5100dae7de4e887327c4` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e1_v3_run1\indexes\chunk-eval-1788012928\chunk_eval.sqlite` |
| 2.248.704 | 2026-08-29 21:06:33 | `33449fe23d6c67966ad62f99e0ed8f3349e2378a2047a6634c96d59148ec34f0` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e2_v2_run1\indexes\chunk-eval-1788012122\chunk_eval.sqlite` |
| 2.248.704 | 2026-08-29 21:25:48 | `db55c44a7e5d73fbf8e5eb88269af30c6a117e675b55a7efb022010160c278e1` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e2_v3_run1\indexes\chunk-eval-1788013280\chunk_eval.sqlite` |
| 2.179.072 | 2026-09-19 09:30:45 | `3b6d192152a457afedc063962bb9db648c8e7a28e1c14cba576c6cb571bf5b11` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e5_lite_final\indexes\chunk-eval-1789784499\chunk_eval.sqlite` |
| 2.011.136 | 2026-08-16 22:58:34 | `e35a4c406301b85bcbd7ade7d8dd022ca748535541451ae0939f5f6a7bbfc681` | `D:\Sandbox\AIOS_habbit\local_runs\matecon_semantic_diagnostic_run\runtime\bge_m3_hybrid\workspace_chat.sqlite` |
| 1.859.584 | 2026-08-29 19:36:09 | `130ff5fa872f8a9923ee012b0eb2cd801b48d0f774badf89c105b2ab7538e0ec` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e1_run1\indexes\chunk-eval-1788006856\chunk_eval.sqlite` |
| 1.859.584 | 2026-08-29 19:39:26 | `c143186748d8e6f4ff65fb132b5b2714886a80e1021ad4d84cee11deedce03fb` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e1_run2\indexes\chunk-eval-1788007041\chunk_eval.sqlite` |
| 1.859.584 | 2026-08-29 20:23:15 | `8587c943a147a21f29d42e69f571141c4e1e2811d0a8356c02e43ee64a812af1` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e2_run1\indexes\chunk-eval-1788009609\chunk_eval.sqlite` |
| 1.859.584 | 2026-08-29 20:27:46 | `a01ed4a3aa10b7641ddee25f818eb4d97948bba1da2c0f4a35cbbab9a2cf114e` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e2_run2\indexes\chunk-eval-1788009940\chunk_eval.sqlite` |
| 1.458.088 | 2026-08-16 23:13:18 | `4f39d7a6aaa486d91d1291669a61a8939ff882110f6bdef1a757d24071ffcf83` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_compacted_batch4_corrected\SELECTED-bge_m3_hybrid-1786885621-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite-journal` |
| 1.306.624 | 2026-08-16 19:38:30 | `3a915094d748bfac218f2f8173284652c0e7f26d0cb91e7aacb614d5e1da2cb2` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_compacted\SELECTED-bge_m3_hybrid-1786882465-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite` |
| 1.011.712 | 2026-08-16 19:06:46 | `02c0c106a40acc4d7af216c30df2e43777fee97035bc4bf25496ac245b29a264` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_current_rerun\SELECTED-bge_m3_hybrid-1786881247-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite` |
| 909.312 | 2026-09-19 22:31:32 | `bb3cc3749335199e03c3bfb1cecfa723274a9e69e775fa1ba572644b5bb0c817` | `D:\Sandbox\AIOS_habbit\local_runs\speed_smoke_lsu_verify\runtime\rag_v2_dev.sqlite` |
| 905.216 | 2026-09-19 21:26:18 | `b1cda04c994ca8fdc9c52b1a4dab183d9f4ae7f6bdf1e08f2f916edbcc8f6b3b` | `D:\Sandbox\AIOS_habbit\local_runs\speed_smoke_6tha3\runtime\rag_v2_dev.sqlite` |
| 638.976 | 2026-09-19 22:28:42 | `58e7baeccad55027d1a3893d93acd0191cabe52a0c9ec45809d5ed0cc8fcb85c` | `D:\Sandbox\AIOS_habbit\local_runs\speed_smoke_lsu_training\runtime\rag_v2_dev.sqlite` |
| 540.672 | 2026-08-16 18:41:06 | `0c6e2214678ec32c529f2ffe137004fba9a4f896570984a8bd3961dd4e3f5adf` | `D:\Sandbox\AIOS_habbit\local_runs\rag_manual_matecon_repair\reference_rebuild\notebooklm_acquisition.sqlite3` |
| 466.944 | 2026-09-13 20:47:53 | `f90dcb566152a4f3186a5e2638a9c0b5c8a26e58dcf2bb28b305df923aaa4720` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.sqlite` |
| 442.368 | 2026-09-13 18:45:53 | `daa0f23f031648ab7ab0e66de83703cf1e127e366c94a0db1244687c243c052d` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v8-to-v9.sqlite` |
| 405.504 | 2026-08-16 18:41:06 | `2b9e0e73e798131296275f00aa4e4e627b8ec236ef3bda484aa6fd14703d0eda` | `D:\Sandbox\AIOS_habbit\local_runs\rag_manual_matecon_repair\reference_rebuild\notebooklm_reference_registry.sqlite3` |
| 315.392 | 2026-09-19 09:07:27 | `b2ff0e15fc8f6b43c4fe196baff76cad8d2c3ac6c9851d005f1454b973737671` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e5_lite_check\indexes\chunk-eval-1789783541\chunk_eval.sqlite` |
| 282.624 | 2026-09-09 21:59:40 | `12106cbc0085536ab5e17a943501f86183efc1b1446953b7ad6bdda7f425040d` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v7-to-v8.sqlite` |
| 274.432 | 2026-09-26 16:36:46 | `8f790aa81801dc27b8a3f627f050ce42527c70d45ec13a385070bf59fa4a92ae` | `D:\Sandbox\AIOS_habbit\local_runs\test_verify_runtime\local_cases\workspace_cases.sqlite` |
| 274.432 | 2026-09-26 20:39:49 | `b442208c636efaaee96ce1abefa528de3daf8fa1f2a1932fda80a4cd51eac543` | `D:\Sandbox\AIOS_habbit\src\local_cases\workspace_cases.sqlite` |
| 253.952 | 2026-09-12 13:56:05 | `04963d3414d2f9ebc8cda1af150e044caade9686604df91329c0098bc859bc90` | `D:\Sandbox\AIOS_habbit\local_runs\goal011_memory_toggle_import\local_cases\workspace_cases.sqlite` |
| 192.512 | 2026-09-08 05:59:01 | `60d4a7c42e99c840e288966baa2f33a883ae8e5f9d68a6b0b66111a5821c2f9f` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v6-to-v7.sqlite` |
| 156.464 | 2026-08-16 19:39:07 | `afa3240c3be5167833b68a149260722f03d995315c2217a3bba7c809bc83a1cb` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_compacted\SELECTED-bge_m3_hybrid-1786882465-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite-journal` |
| 151.552 | 2026-09-08 00:15:12 | `09adabc3ab281dca8073ed7e2181a8cb76a89e90dc7d3b925c84cf733e1bf4fd` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v5-to-v6.sqlite` |
| 147.456 | 2026-08-02 13:56:14 | `3ce771f1b788490a4708085563b133e19d0070b069ee2fec7ecfa5c5d944a660` | `D:\Sandbox\AIOS_habbit\local_runs\nakazasen_model_catalog.sqlite3` |
| 131.840 | 2026-08-22 15:04:51 | `2f28548dbdbc4b73c7659c6d3224ee3ad7e668f3d77b6e170e5e5d329189cfff` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_restore\SELECTED-bge_m3_hybrid-1787383502-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite-journal` |
| 126.976 | 2026-09-06 14:22:15 | `ec80a68e6625d78677016e344c079967484d195e116ac79608c1af66b11934b0` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v4-to-v5.sqlite` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20260913_140926_382272` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20260913_140940_097355` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20260913_140940_342177` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20260913_140943_141066` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20260913_140943_269129` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20260920_062040_627597` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20261003_040510_625217` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20261003_090940_033587` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20261003_091238_675005` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20261003_091255_886804` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20261003_091353_877459` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20261003_091407_960107` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20261003_091430_723835` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20261003_091433_722375` |
| 118.784 | 2026-09-08 00:16:36 | `301a723428f42b326486da4d24bb846b62615413bdc68e20890184f95978a11b` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20261003_091527_930031` |
| 106.496 | 2026-09-06 13:35:04 | `0da56107358f0ea8ea04d8065b99f987042ec0627abd091c0a35d1ddc925aa18` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v3-to-v4.sqlite` |
| 106.496 | 2026-09-05 14:05:51 | `7b1c263f5c8d29d5d4fd73a7555670a9c3843be8da81d85d9fe6bdba732fce0a` | `D:\Sandbox\AIOS_habbit\local_runs\evidence_case_loop_goal\run_20260905_062200\runtime\lsu_m1_verify.sqlite` |
| 99.008 | 2026-09-19 09:30:45 | `68f96e282aceaba815f780d6b813a4a56f250a18f15202f1f400aa1474313033` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e5_lite_final\indexes\chunk-eval-1789784499\chunk_eval.sqlite-journal` |
| 98.304 | 2026-10-03 18:08:41 | `4ecc3d7a2561b6bea73f42c0ada2f648249ff79bd26c4225bdc0363fc9d68f00` | `D:\Sandbox\AIOS_habbit\local_cases\staging_enrichment.sqlite` |
| 94.904 | 2026-08-16 20:05:41 | `8eca1b01b2bf2f37b24684dbfd8c27ee9b73be40a5d077dd0fcc3e2087d6fdb3` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_compacted_batch4\SELECTED-bge_m3_hybrid-1786884194-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite-journal` |
| 90.112 | 2026-08-30 16:36:54 | `74be4bea2cd5e11e2a76b45f497c10f00505e9d43e7d2822f43a6ae16c5d1a3d` | `D:\Sandbox\AIOS_habbit\local_runs\test_verify_runtime\rag_v2_dev.sqlite` |
| 86.016 | 2026-09-12 07:51:28 | `edfb7a1349727bc05163a51b7fee6c93e4384d29168539994592f395cd6c81c9` | `D:\Sandbox\AIOS_habbit\local_runs\rag_v2_dev\rag_v2_dev.sqlite` |
| 86.016 | 2026-09-27 07:59:30 | `160a1bb80fa7311f82909a60e532cd1e8ff16f8939bc45b6123eb82b5d7ff76e` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\rag_v2_dev.sqlite` |
| 81.920 | 2026-09-30 04:19:38 | `f28fb95f51ba1b572ff0ad6343a1feca38d099ea4c1c97dfe633d248918bb638` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\workspace_chat.sqlite` |
| 74.384 | 2026-09-19 09:07:27 | `97391ff4d295ef9ffc0134f326e7ca4f0711644de01dfd91ef25c91ca4ac147b` | `D:\Sandbox\AIOS_habbit\local_runs\chunk_evaluation\e5_lite_check\indexes\chunk-eval-1789783541\chunk_eval.sqlite-journal` |
| 69.632 | 2026-09-05 14:37:31 | `196dacea5765740949f1d1b70f174ebca232f52e76a0cea2989e12759b1f898d` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v2-to-v3.sqlite` |
| 53.864 | 2026-08-16 19:07:22 | `52c96c9596d2bb41c8a229129040618dd66c19e404e525262736c423b8a8884c` | `D:\Sandbox\AIOS_habbit\local_runs\gate_h_selected_profile_current_rerun\SELECTED-bge_m3_hybrid-1786881247-e33e5670\bge_m3_hybrid_runtime\rag_v2_dev.sqlite-journal` |
| 53.248 | 2026-09-05 14:17:15 | `615af4668f37e188d13e2f22969e318a480b6992878caa5e549661e7c61a03d6` | `D:\Sandbox\AIOS_habbit\local_runs\evidence_case_loop_goal\run_20260905_062200\runtime\test_m2_rehearsal.sqlite` |
| 53.248 | 2026-09-05 14:17:15 | `615af4668f37e188d13e2f22969e318a480b6992878caa5e549661e7c61a03d6` | `D:\Sandbox\AIOS_habbit\local_runs\evidence_case_loop_goal\run_20260905_062200\runtime\test_m2_rehearsal.sqlite.bak_20260905_071715_215118` |
| 49.152 | 2026-09-07 06:15:33 | `6398662f66133367b6584c66c2e3643f44aaec45c6de7c56e08ff15d6308b9de` | `D:\Sandbox\AIOS_habbit\local_cases\production_prediction.sqlite.bak_20260907_171635_328448` |
| 45.056 | 2026-10-03 14:53:14 | `920653aeeff14ec7c0e97ecd76cfa013aaf9178ff7fbb0ce3b210ac484392158` | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\workspace_chat.sqlite` |
| 36.864 | 2026-09-12 13:56:05 | `4c6f95453e71bd1da9d3db36799c7068e0a5fafcc55b2504268080b7a566b60f` | `D:\Sandbox\AIOS_habbit\local_runs\goal011_memory_toggle_import\local_cases\production_prediction.sqlite` |
| 36.864 | 2026-09-26 16:36:50 | `4c6f95453e71bd1da9d3db36799c7068e0a5fafcc55b2504268080b7a566b60f` | `D:\Sandbox\AIOS_habbit\local_runs\test_verify_runtime\local_cases\production_prediction.sqlite` |
| 36.864 | 2026-09-26 20:39:50 | `4c6f95453e71bd1da9d3db36799c7068e0a5fafcc55b2504268080b7a566b60f` | `D:\Sandbox\AIOS_habbit\src\local_cases\production_prediction.sqlite` |
| 32.768 | 2026-10-03 18:08:58 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_cases\staging_enrichment.sqlite-shm` |
| 32.768 | 2026-10-03 17:56:33 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v2-to-v3.sqlite-shm` |
| 32.768 | 2026-10-03 17:56:37 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v3-to-v4.sqlite-shm` |
| 32.768 | 2026-10-03 17:56:42 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v4-to-v5.sqlite-shm` |
| 32.768 | 2026-10-03 17:56:49 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v5-to-v6.sqlite-shm` |
| 32.768 | 2026-10-03 17:56:54 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v6-to-v7.sqlite-shm` |
| 32.768 | 2026-10-03 17:56:57 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v7-to-v8.sqlite-shm` |
| 32.768 | 2026-10-03 17:56:57 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v8-to-v9.sqlite-shm` |
| 32.768 | 2026-10-03 17:56:59 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_runs\evidence_case_loop_goal\run_20260905_062200\runtime\lsu_m1_verify.sqlite-shm` |
| 32.768 | 2026-10-03 17:56:59 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_runs\goal011_memory_toggle_import\local_cases\workspace_cases.sqlite-shm` |
| 32.768 | 2026-10-03 17:57:00 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\local_runs\test_verify_runtime\local_cases\workspace_cases.sqlite-shm` |
| 32.768 | 2026-10-03 17:57:01 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` | `D:\Sandbox\AIOS_habbit\src\local_cases\workspace_cases.sqlite-shm` |
| 20.480 | 2026-08-30 17:11:01 | `5dcff30b0c404a2a8fd4a9cae5691ec2b2bf589d4a8af4a8112a573a6bd8ba4c` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_chat\collections\tri_thuc\line_events.sqlite` |
| 16.384 | 2026-08-23 07:40:16 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_activated_runtime_failure0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:20 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_adapter_degraded_reranker0\rag\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:28 | `a7bf9d2d2629f7476fd8161e38c20ca069b4d89dd30a558ff323cd17df957992` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_background_drain_queue_th0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:30 | `e7d6019d7bb4eb34d01af36231c82418d91cb852e67a2bc9ab9ef86151f3a4f8` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_background_drain_queue_up0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:36 | `aecf5fb74d31e5df70fad9f3b0b6deda5b597151778b2893037ef0e6ffd788e0` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_background_drain_true_con0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:37 | `5abe8be630f55544292f7489e791866311615a70b0d916ffa27e06269dd1acff` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_drain_worker_double_check0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:57 | `a1676e5eab45fdd1b6fd20777092d1a24bd9a64e5a350194f4410a13ff38da6a` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_e2e_sandbox_upload_new_so0\canary_runtime\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:14 | `0870b41607cfa1a6fa62b9b4a29bf3bda79fbd4fc230e03d7d6c5fd7d33473eb` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_existing_complete_semanti0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:15 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_failure_telemetry_does_no0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:26 | `42ddb705f9917f2452e3eba0a00a8eaebfb202cd7adf75853b3f5d27b8c1c43b` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_forget_sources_deletes_le0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:25 | `a46ce5681a6380ef242369077690ed48139ce955c0be07b0eefff05d20a7858d` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_get_workspace_chat_prepar0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:15 | `a85c261e34b9a73105dfaee929ad19c666f6387640e28bd6176e8f0be492e1e4` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_missing_bge_pins_fail_clo0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:16 | `ce256f406cabcfde868cb4f0cf150609180405bb448c02ec4f12c1b1744d7202` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_preparation_schedule_dedu0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:17 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_preparation_status_identi0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:17 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_prepare_then_query_uses_p0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:24 | `1838971cadc675cb76f72f747ef1e17857229d5178bfd51f677acb546c34ecdf` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_promote_priority_to_inter0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:17 | `349c087501cf11ef3665f88e7e312ee749dbdbc30f2aadbb05463380820b23cd` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_query_returns_no_evidence0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:23 | `3d3f5ced7274b0fcd86bc3fef5822074154eb632c6a06088625062ef3d2c65b2` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_reconcile_and_enqueue_pre0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:20 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_search_preference_deep_ov0\rag\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:19 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_seeded_preparation_enable0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:18 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_semantic_preparation_batc0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:19 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_semantic_preparation_init0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:18 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_semantic_preparation_uses0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:21 | `b3579c16f7d3f74cae87de980ff8f7e5d2dfecbc6e0be9f36e3358cb134dde2b` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_sqlite_preparation_ledger0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:23 | `80f688ec78f5ccc94780ea25e7c4a94d1ee9178e1c70f9dc119bc56a384e4ec5` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_sqlite_preparation_priori0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:21 | `264d94f057d2cb070860ff50b64bbcda4f9c6cc1c9211c3f882e45d2e4d85bde` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_sqlite_stale_processing_r0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:40:15 | `b6e616d50fe467922248a07667b6561daf26bc71f6b1b5087496f1a35cf4a626` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-0\test_unprepared_query_remains_0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:31 | `bbd1d1c70a7ba2442c34f6429d90ee4934440689441092295273a22a46225da1` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-1\test_e2e_sandbox_upload_new_so0\canary_runtime\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:43 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_activated_runtime_failure0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:49 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_adapter_degraded_reranker0\rag\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:57 | `61eea9d02979b86dcb5be16fe5dfe025fe7a4c9acef33eb6ec55f7cfd849abe5` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_background_drain_queue_th0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:58 | `1f1e0d1ca053b9defd5e20741a3fe18c66089f776003a7f5c130d9f589918e30` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_background_drain_queue_up0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:42:04 | `427af34a6962fd503e40bb5cc865532b20be003cf4d536896454aadc5043af98` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_background_drain_true_con0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:42:05 | `69ff69f0a3700beb93a329c5cf6e60f3086aeab7337ba93004b3cf4a7026c428` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_drain_worker_double_check0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:42:26 | `91a3b12d64ec9fde225e2276af64c51791a22d74d82c518da97bd7eec8fcad4f` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_e2e_sandbox_upload_new_so0\canary_runtime\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:42 | `da57c6f0b0f598ef76dc7d3252107f8e6a69f1b73eb78350fa9f2f313a8feb17` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_existing_complete_semanti0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:43 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_failure_telemetry_does_no0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:54 | `42ddb705f9917f2452e3eba0a00a8eaebfb202cd7adf75853b3f5d27b8c1c43b` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_forget_sources_deletes_le0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:54 | `a46ce5681a6380ef242369077690ed48139ce955c0be07b0eefff05d20a7858d` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_get_workspace_chat_prepar0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:42 | `4d3d311aa49fd0e2c0162c8c455e2159009308b943f3beecc8dec3d1d7a7d751` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_missing_bge_pins_fail_clo0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:44 | `3884a70757284d0ca719ef4ae9ea5e3f0f5f5a922f03228ce023974c85e43d6f` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_preparation_schedule_dedu0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:45 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_preparation_status_identi0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:46 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_prepare_then_query_uses_p0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:53 | `a52c990ecb96f5ca691fcf7ed50566c2955e7ae93c8534f17c7b2931bb85c3f4` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_promote_priority_to_inter0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:45 | `cb2906e43bb1c644d7396274e85f54ce13944f947f85f881fb21a8651fba2857` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_query_returns_no_evidence0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:52 | `d6b50638a5c054b508f5e25969af79d90c78ead3f7c3d9e6ae43b7ea8abd73d4` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_reconcile_and_enqueue_pre0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:48 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_search_preference_deep_ov0\rag\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:48 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_seeded_preparation_enable0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:47 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_semantic_preparation_batc0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:47 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_semantic_preparation_init0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:46 | `7740555b9901170666734f818aaea40a19352df539a3389906ee07d9688df48c` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_semantic_preparation_uses0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:49 | `b3579c16f7d3f74cae87de980ff8f7e5d2dfecbc6e0be9f36e3358cb134dde2b` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_sqlite_preparation_ledger0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:51 | `df7075593e1084c1e0db6f225842d7cd812005f6a00c762bac28be8a4025ef73` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_sqlite_preparation_priori0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:50 | `27b6cb9c10ca25d878936f8c8d3374941dd47f0f62a328c065136458957e5b03` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_sqlite_stale_processing_r0\workspace_chat.sqlite` |
| 16.384 | 2026-08-23 07:41:43 | `eb46838f90877f75677d84727a63faef6a175f43daa4a351486537a6704095b2` | `D:\Sandbox\AIOS_habbit\.tmp\pytest-of-Vinh\pytest-2\test_unprepared_query_remains_0\workspace_chat.sqlite` |
| 1.024 | 2026-10-02 07:04:38 | `bf3546d6abcfacac6989a4311383ede1e2380310e397dc65cf0402e7bb8740a9` | `D:\Kế hoạch AIOS_habbit\aios_thu_vien\.library.sqlite.ba9796c9808548f7a844f182c68e7d35.tmp-journal` |
| 0 | 2026-10-03 18:08:58 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_cases\staging_enrichment.sqlite-wal` |
| 0 | 2026-10-03 17:56:33 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v2-to-v3.sqlite-wal` |
| 0 | 2026-10-03 17:56:36 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v3-to-v4.sqlite-wal` |
| 0 | 2026-10-03 17:56:42 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v4-to-v5.sqlite-wal` |
| 0 | 2026-10-03 17:56:48 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v5-to-v6.sqlite-wal` |
| 0 | 2026-10-03 17:56:54 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v6-to-v7.sqlite-wal` |
| 0 | 2026-10-03 17:56:57 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v7-to-v8.sqlite-wal` |
| 0 | 2026-10-03 17:56:57 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_cases\workspace_cases.backup-v8-to-v9.sqlite-wal` |
| 0 | 2026-10-03 17:56:59 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_runs\evidence_case_loop_goal\run_20260905_062200\runtime\lsu_m1_verify.sqlite-wal` |
| 0 | 2026-10-03 17:56:59 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_runs\goal011_memory_toggle_import\local_cases\workspace_cases.sqlite-wal` |
| 0 | 2026-10-03 17:57:00 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\local_runs\test_verify_runtime\local_cases\workspace_cases.sqlite-wal` |
| 0 | 2026-10-03 17:57:01 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `D:\Sandbox\AIOS_habbit\src\local_cases\workspace_cases.sqlite-wal` |

Không có file sqlite nào ở `1.laptopdata`, `Zalo Data`, `MOM_WMS_QLLSSX` hay các nhánh cá nhân khác.

## 5. Backup, zip, model, log

### Model (`models\`, 5.761.883.616 byte)

| Thư mục | Byte | Ghi chú |
| --- | ---: | --- |
| `bge-m3-onnx-fp32` | 2.289.625.694 | ghim đang dùng, giữ |
| `.bge-m3-onnx-work-r2` | 2.289.606.933 | bản làm việc gần bằng fp32, chưa thấy trong danh mục giữ |
| `bge-m3-onnx-int8` | 591.786.329 | biến thể đã từng đo, sidecar `2205c800…` |
| `bge-m3-onnx-optimum` | 590.861.845 | biến thể đã từng đo, sidecar `fab539b8…` |

`local_runs\retrieval_models` thêm 4.588.663.876 byte (cây `bge-m3-5617a9f` và `bge-reranker-v2-m3`). Không mở trọng số. Đây là bản model cũ cạnh cây `models\`, chưa gộp.

### Zip / tar liên quan AIOS

- `D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Điều chỉnh-20260905T053942Z-1-001.zip` — 858.190.286 byte, SHA khớp ghim. Giữ. Bản nhìn qua junction pnpm là cùng file.
- Các zip/rar lớn khác (giáo trình, ComfyUI, sách, Halcon) không thuộc kho AIOS. Không liệt kê nội dung, không đề xuất xóa.

### Log lớn

Không có file `.log` nào ≥ 50 MB trên ổ D. Không mở log.

### Backup nhìn thấy (chỉ tên/kích thước)

- File sqlite có chữ backup/bak trong repo: 50 file, 7.522.357.248 byte (7,01 GB).
- Trong đó chuỗi `.bak` của canary `tri_thuc`: 10 file, 7.461.363.712 byte (6,95 GB).
- Bản đông production `062ec090…` **không** nằm trong nhóm đề xuất xóa.

## 6. Mục lạ hoặc chưa từng ghi nhận

1. `Kế hoạch AIOS_habbit\aios_thu_vien\.library.sqlite.….tmp` — 2.942.201.856 byte, mtime 2026-10-02 07:04, SHA `aae0943e2c568763208fd72095339cfebe84e24b88fe696ead21db4c22ee5425`. Cùng số byte với kho C đang chạy nhưng SHA khác `45eb0e07…` và khác bản đông D `062ec090…`. Kèm file journal 1.024 byte và khóa cũ `.aios-library-writer.info` (pid 15652, `acquired_at` 2026-10-02T06:59:18). Pid đó không còn chạy. Có vẻ là lần ghi thư viện dở, không phải kho đang dùng.
2. `D:\c\Users` — 1.562.144.291 byte. Cấp 2 chỉ thấy `Public`. Không mở. Không có trong danh mục AIOS.
3. `.bge-m3-onnx-work-r2` — gần trùng kích thước fp32, chưa có lệnh giữ.
4. Junction pnpm ở trên — không phải bản sao, nhưng dễ bị tưởng là 36 GB rác.
5. `git worktree list` còn `D:/Sandbox/AIOS_habbit_gate_f_live_baseline` (detached, `prunable`) nhưng thư mục **không còn**. Không xóa gì thêm.
6. 27 thư mục `pytest_*` trong `AIOS_habbit` và `local_runs` trả Access denied. Không nâng quyền, không coi là rỗng. `System Volume Information` cũng không đọc được.

## 7. Đề xuất dọn — chỉ đề xuất, không làm

Thứ tự vé yêu cầu. Số GB để user gật sau, không phải lệnh xóa.

### 7.1 Rác tmp (an toàn hơn cả, vẫn cần gật)

| Mục | Byte | GB |
| --- | ---: | ---: |
| `AIOS_habbit\.tmp\fix1_bench` | 304.259.072 | 0,28 |
| `AIOS_habbit\.tmp\pytest-of-Vinh` | 1.119.234 | 0,00 |
| `D:\tmp\ux-chat-core` | 213.648.303 | 0,20 |
| **Cộng nhóm này** | **518.026.609** | **0,48** |

Không xếp file tmp 2,94 GB ở mục 6.1 vào nhóm rác. SHA lạ, cần user xem trước.

### 7.2 Venv trùng

App đang chạy dùng `D:\Sandbox\AIOS_habbit\.venv` (2.263.914.512 byte, thấy trong dòng lệnh process). **Giữ.**

| Ứng viên | Byte | GB |
| --- | ---: | ---: |
| `AIOS_habbit\.venv-rag-compat` | 1.674.487.483 | 1,56 |
| `Sandbox\.venv` | 1.338.481.273 | 1,25 |
| `AIOS_habbit\.venv-rag` | 1.326.346.716 | 1,24 |
| **Cộng** | **4.339.315.472** | **4,04** |

Chỉ xóa sau khi user xác nhận không còn script nào trỏ vào ba thư mục này.

### 7.3 Worktree cũ

- Thư mục `AIOS_habbit_gate_f_live_baseline` không còn. Việc còn lại chỉ là `git worktree prune` (sửa metadata git, không xóa dữ liệu). Không làm trong vé này.
- Worktree `deep-dev` nằm trên ổ C, ngoài phạm vi.

### 7.4 Backup cũ — chỉ sau kiểm toàn vẹn, và chỉ khi user gật từng mục

- Chuỗi bak canary: 7.461.363.712 byte (6,95 GB). Vé này **chưa** chạy `integrity_check`.
- Không đụng bản đông production `062ec090…` (2.552.659.968 byte) — đây là điểm rollback.
- Không đụng `C:\AIOS_staging_262` (lệnh giữ GPU-262), dù thư mục đó ở ổ C.
- Không đụng zip Điều chỉnh, cây `models\bge-m3-onnx-fp32`, `MOM_WMS_QLLSSX`, `Tài liệu của tất cả dòng máy`.

### 7.5 Ngoài thứ tự, chỉ để user biết

- `.bge-m3-onnx-work-r2` 2,29 GB: có thể trùng fp32. Muốn xóa thì so SHA model trước, không xóa mù.
- `graphify-out` 207.251.734 byte và `scratch` 123.890.447 byte: cache/nháp, chưa xếp vào rác tmp.
- `vendor` 1.883.355.261 byte: wheel, có thể tạo lại, không đề xuất xóa ở vé này.
- `VideoYoutube`, `MP2027`, `phantichphanmemdc`, dữ liệu cá nhân, Zalo, Calibre, giáo trình: **ngoài AIOS, không đề xuất xóa.**

## 8. Không làm

- Không xóa, không đổi tên, không ghi file dữ liệu trên ổ D.
- Không sửa quyền thư mục bị từ chối truy cập.
- Không merge `main`.

Báo cáo ghi lúc 2026-10-03 20:29:27 +07.
