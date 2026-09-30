# Vé GPU-262b — DỪNG GPU-262, nhúng GPU 19 tài liệu phi-CSV (2.883 chunk) + đóng gói delta cho PC0575

## LỆNH DỪNG KHẨN (làm ĐẦU TIÊN, trước mọi bước khác)
User chốt lúc ~00:10 +07 ngày 01/10/2026 (chọn "cách 2"): **DỪNG NGAY** tiến trình
nhúng GPU-262 đang chạy ở `C:\AIOS_staging_262`.
- Stop worker đang nhúng (Ctrl+C / stop process). Ghi lại: dừng ở chunk thứ mấy,
  thời gian dừng.
- KHÔNG xóa `C:\AIOS_staging_262` (giữ nguyên để đối chiếu; dọn sau khi vé này xong).
- Vé GPU-262 cũ bị thay thế hoàn toàn — không làm tiếp bất kỳ bước nào của nó.

## Bối cảnh
- Audit độc lập file `text_export.jsonl` (Muse kiểm trên VM, SHA-256 khớp 100% với
  file máy nhà đã verify tối 30/09: `95aecf07297bfdf2e4f7462fd477fa052a89aa3eaaa462c53cbce40d341bb505`):
  **50.096/52.979 chunk (94,6%) là 87 file CSV số đo thô** (profile/depth/unittest/log
  máy) — giá trị hỏi-đáp ≈ 0 vì câu hỏi tiếng Việt không match được chunk toàn số
  không ngữ cảnh. Quyết định của user: chỉ nhúng 19 tài liệu phi-CSV.
- File `text_export.jsonl` đã có trên máy nhà (tải + verify SHA/size tối 30/09):
  **tái dùng, KHÔNG tải lại từ Drive**.
- 5/19 `document_id` đã có vector trong production PC0575 (nhúng CPU chiều 30/09):
  khi đóng gói delta thì kèm danh sách để vé merge SKIP, không ghi đè.
- Production PC0575
  (`D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`)
  — vé này KHÔNG ĐỤNG tới. Chỉ nhúng vào staging trên máy nhà; merge về PC0575
  là vé khác (Muse ra sau khi review độc lập).

## Việc cần làm
1. Lọc `text_export.jsonl` đã có trên máy: giữ các dòng có `source_name` KHÔNG kết
   thúc bằng `.csv` (không phân biệt hoa/thường). Ghi ra file lọc riêng
   (vd `C:\tmp\gpu-262b\export_19.jsonl`).
   Verify lọc: đúng **19 `document_id`**, **2.883 chunk**, 19 tên file khớp bảng dưới.
   Lệch → DỪNG, mailbox `cho-muse`, ghi rõ số đo thực tế.
2. Tạo staging MỚI `C:\AIOS_staging_262b\library.sqlite`, schema y hệt collection
   `tri_thuc` hiện tại. CẤM ghi production (`C:\AIOS_p1_4\tri_thuc\library.sqlite`),
   CẤM ghi ổ D (ổ D hỏng vật lý, cấm vĩnh viễn).
3. Nhúng GPU 2.883 chunk: tái dùng tooling Vé 0.3; đối chiếu TRƯỚC khi chạy —
   model BGE-M3 đúng rev `5617a9f`, `onnxruntime==1.28.0`, checksum cây onnx máy nhà
   `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`.
   Backend tự chọn CUDA (fail-closed nếu thiếu model).
   Ghi thời gian bắt đầu/kết thúc, tốc độ chunk/giây.
4. Verify sau nhúng (chỉ đọc, không sửa):
   - Đủ 19/19 `document_id`; đếm chunk retrievable.
   - Fingerprint `016c5255…` trên toàn bộ chunk.
   - Spot-check cosine GPU/CPU ≥ 0,999 trên vài chunk mẫu (lấy text từ file lọc,
     embed CPU đối chiếu — như vé GPU-262 cũ).
5. Đóng gói delta cho PC0575 (zip ra ổ C): vector của 19 `document_id` + manifest
   ghi rõ 5 ID đã tồn tại trong production (vé merge sẽ SKIP, không ghi đè).
6. Mailbox → `xong-cho-duyet` + báo cáo `docs/phieu-viec/ket-qua/gpu-262b.md`
   (ghi rõ: đã dừng GPU-262 ở chunk thứ mấy, số đo lọc, tốc độ nhúng, kết quả verify).

## Bảng 19 document_id (tổng 2.883 chunk)
| `document_id` | chunk | `source_name` |
| --- | ---: | --- |
| `wsc-e0c617eb98b847bd3b20be64` | 568 | `RE__Iris_LSU_Beam径NG多発_異常品質会議3回目.msg` |
| `wsc-9e3e7cbc01ed57332c1384eb` | 345 | `RE__Iris_LSU_Beam径NG多発_異常品質会議2回目.msg` |
| `wsc-fb4f4f8ff43f9f96c9c6ade4` | 308 | `DATA_Matome.xlsx` |
| `wsc-a1a89391eee709a956a46130` | 274 | `tổng_hợp_dữ_liệu_dán_tape.xlsx` |
| `wsc-c21a49defc899499fff0797a` | 217 | `Dữ_liệu_tổng_hợp_CaV2__1241_.xlsx` |
| `wsc-a683f1cdbccec94c8c2e4746` | 213 | `tổng_hợp_dữ_liệu_XY_Target_2021.04.12.xlsx` |
| `wsc-ef913f966d66f012654d9581` | 210 | `dữ_liệu_tổng_hợp.xlsx` |
| `wsc-61d4aa19758ed232210b4508` | 196 | `RE__Iris_LSU_Beam径NG多発_異常品質会議5回目.msg` |
| `wsc-c292106969b26cfd6269485b` | 155 | `sirius2_beam径確認_240202.xlsx` |
| `wsc-cd81e7da2748a7e06c215ea5` | 137 | `Sirius2_7620.xlsx` |
| `wsc-d1e06540cd149c697de19519` | 108 | `Dữ_liệu_tổng_hợp_CaV3__1242_.xlsx` |
| `wsc-582a992dc46566ab198dabe2` | 69 | `3V2ND19040-MOUNT_LD_BLOCK__LOT_18.8.2026.xlsx` |
| `wsc-cc7d383bb6f7b9127bcaef00` | 31 | `dữ_liệu_tổng_hợp_CaV2__1240_.xlsx` |
| `wsc-154101d384acc2d01009025d` | 15 | `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx` |
| `wsc-58589483c646877fdb341f46` | 11 | `Dữ_liệu_tổng_hợp.xlsx` |
| `wsc-1e233aa1ef54e266c51e4d7d` | 11 | `Bong_TAPE_COVER_GLASS_Rev.00_VN.pptx` |
| `wsc-ee5a4f6d3c263185fe6ff10b` | 7 | `OKNGUNITのCO_BRACKETの倒れ_傾き確認結果.xlsx` |
| `wsc-0d60443d350ced325b4775f0` | 4 | `siriud2調整治具_2号機_240411.pptx` |
| `wsc-de63ca1244089877827b62aa` | 4 | `Y_BeamH_Camera_140_to_bất_thường.pptx` |

## 5 document_id đã có trong production PC0575 (vé merge SKIP, không ghi đè)
- `wsc-154101d384acc2d01009025d` (`Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx`)
- `wsc-9e3e7cbc01ed57332c1384eb` (`RE__Iris_LSU_Beam径NG多発_異常品質会議2回目.msg`)
- `wsc-a1a89391eee709a956a46130` (`tổng_hợp_dữ_liệu_dán_tape.xlsx`)
- `wsc-58589483c646877fdb341f46` (`Dữ_liệu_tổng_hợp.xlsx`)
- `wsc-cc7d383bb6f7b9127bcaef00` (`dữ_liệu_tổng_hợp_CaV2__1240_.xlsx`)
