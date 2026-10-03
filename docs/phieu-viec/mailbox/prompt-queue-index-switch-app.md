# Vé: INDEX-SWITCH-APP — chuyển app sang 3 khối lĩnh vực + bật định tuyến

Lane: [NHÀ] OMP chạy trên máy nhà. Không merge `main`. Không đụng PC0575.

## Bối cảnh

Vé R5 đã tách xong và verify ĐẠT: 4 thư mục tại `D:\Sandbox\AIOS_index_split_new\` (`lsu` 92 doc/71.945 chunk, `dieu_tra_loi` 681 doc/74.439 chunk, `mom` 44 doc/1.014 chunk, `tong_hop` 72 doc/2.402 chunk), manifest `overall: DAT`, kho cũ `tri_thuc` nguyên vẹn (SHA `45eb0e07…b7c0`). App hiện vẫn đọc kho `tri_thuc` cũ (định tuyến đang tắt).

Rào cứng: **ổ C chỉ còn ~2,0 GB trống**, 4 file kho mới tổng ~2,86 GB → CẤM copy 4 file này lên ổ C.

## Việc OMP làm

### Bước 0 — Chuẩn bị
1. Pull nhánh `phieu-viec/rag-fix1` mới nhất.
2. Dừng app chat (streamlit + worker BGE) trước khi thao tác collection.

### Bước 1 — Dựng 4 collection cho app (không tốn chỗ ổ C)
3. App đọc collection tại `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\<id>\library.sqlite`. Tạo 4 NTFS junction trong thư mục đó trỏ sang ổ D:
   - `collections\lsu` → `D:\Sandbox\AIOS_index_split_new\lsu`
   - `collections\dieu_tra_loi` → `D:\Sandbox\AIOS_index_split_new\dieu_tra_loi`
   - `collections\mom` → `D:\Sandbox\AIOS_index_split_new\mom`
   - `collections\tong_hop` → `D:\Sandbox\AIOS_index_split_new\tong_hop`
   (lệnh `mklink /J`). KHÔNG copy file, KHÔNG di chuyển file, KHÔNG đụng `collections\tri_thuc`.
4. Kiểm tra app mở được cả 4 collection (đếm document mỗi collection khớp manifest).

### Bước 2 — Bật định tuyến lĩnh vực
5. Đặt biến môi trường `AIOS_DOMAIN_ROUTING_ENABLED=1` cho tiến trình app, restart app.
6. Hỏi đáp thử 4 câu, ghi lại badge "Đang tra cứu khối X" và nhận xét câu trả lời có trích đúng khối không:
   - Câu LSU (VD: "log jig báo bowskew nghĩa là gì, xử lý thế nào?")
   - Câu điều tra lỗi (VD: "mã lỗi C6770 trên Iris2024: nguyên nhân và đối sách?")
   - Câu MOM (VD: "quy trình xuất kho WMS/Opcenter gồm bước nào?")
   - Câu mơ hồ (VD: "hôm nay có gì mới?") → phải ghi rõ đã chọn khối khả dĩ nhất.
7. Kiểm tra phủ định: không câu nào bị định tuyến vào khối `tong_hop` (khối cách ly, router không bao giờ chọn).

### Bước 3 — Thử rollback
8. Tắt `AIOS_DOMAIN_ROUTING_ENABLED` (xóa biến), restart app → hỏi 1 câu, xác nhận app về kho `tri_thuc` cũ và trả lời bình thường. Sau đó BẬT LẠI cờ (trạng thái cuối: cờ BẬT).

### Bước 4 — Đóng vé
9. Ghi SHA-256 + size + mtime của `collections\tri_thuc\library.sqlite` (phải bằng `45eb0e07…b7c0`).
10. Báo cáo `docs/phieu-viec/ket-qua/index-switch-app.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT
- 4 collection đọc được qua junction, đếm document khớp manifest.
- 3 câu thử đầu mỗi câu tra đúng khối (badge hiển thị đúng), câu mơ hồ ghi rõ khối đã chọn.
- Không câu nào vào `tong_hop`.
- Rollback đã thử: tắt cờ → về kho cũ bình thường; trạng thái cuối cờ BẬT.
- Kho `tri_thuc` cũ: SHA/size/mtime trước = sau.

## Kế hoạch rollback (khi có sự cố sau này)
Tắt `AIOS_DOMAIN_ROUTING_ENABLED`, restart app → về kho `tri_thuc` cũ. Xóa 4 junction khi user duyệt (file trên D giữ nguyên).

## Không làm
- Không embed lại, không ingest thêm, không xóa/ghi `tri_thuc`.
- Không merge `main`.
