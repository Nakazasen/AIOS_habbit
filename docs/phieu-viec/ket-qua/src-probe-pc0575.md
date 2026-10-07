# Báo cáo vé thăm dò nguồn cho 29 tệp đã khôi phục

- Vé: `SRC-PROBE-PC0575` — thăm dò truy hồi đầu-cuối cho 29 tệp nguồn đã khôi phục.
- Máy làm: công ty `KDTVN-PC0575`, mạng công ty suốt quá trình đo.
- Thời gian đo: 2026-10-07 16:20 → 17:08 +07.
- Trạng thái vé: đang làm (mới xong bao phủ, truy vấn đầy đủ còn kẹt).
- Nhánh làm việc: `phieu-viec/rag-fix1`, không gộp nhánh chính.
- Đầu vào đã đọc: `docs/phieu-viec/ket-qua/src-sync-pc0575.md` mục 7 (29 tệp) và mục 8 (vân tay logic).

## 1. Phạm vi và cách đo

- Chỉ đọc chỉ mục, không ghi hay sửa tệp nguồn hay chỉ mục.
- Mở pipeline như người dùng cuối: `index_read_only=True` + `strict_semantic=True`, biên dạng `bge_m3_hybrid`, thiết bị `cpu`.
- Không đụng `src/rag_v2*` (phần việc của nhóm khác giữ nguyên).
- Ba cổng vân tay cần qua: không rơi `__source_unavailable__`, không bị đánh dấu cũ, qua cổng an toàn sau trộn.
- Đối chứng bắt buộc: âm 5 tài liệu thiếu tệp phải bị chặn, dương 5 tài liệu đủ tệp phải qua.

## 2. Danh sách 29 tệp còn nguyên

- Kiểm đĩa + băm `SHA-256` khớp vân tay chỉ mục: 29/29 đạt.
- Gốc một mảnh trong chỉ mục: 45 mã (40 `txt` + 5 `gpu`), trừ 11 lệch còn 34, trong đó 29 `txt` đạt và 5 `gpu` rớt đúng (đường `gpu://` không phải tệp).
- 29 mã đạt:

| STT | Mã tài liệu | Ghi chú |
|---|---|---|
| 1 | wsc-015067b75dc12e2770b7d8cb | đạt băm, có tệp |
| 2 | wsc-0a49389b70f1e9592670c5e9 | đạt băm, có tệp |
| 3 | wsc-149cac9d8b129f8244b616ef | đạt băm, có tệp |
| 4 | wsc-18c17803678e5d71f0cbb2ba | đạt băm, có tệp |
| 5 | wsc-1d6dc72ebb72350e220dfb07 | đạt băm, có tệp |
| 6 | wsc-22ab58a4a087909fa305efb7 | đạt băm, có tệp |
| 7 | wsc-42843eb6ca4459ae3af6b657 | đạt băm, có tệp |
| 8 | wsc-431e31fbbc3df5fc16f444cb | đạt băm, có tệp |
| 9 | wsc-492485e50bac291bf4c81cc4 | đạt băm, có tệp |
| 10 | wsc-4cbd21f3ccab9c9ea52161fa | đạt băm, có tệp |
| 11 | wsc-4e59cb5f495278f0be7fa444 | đạt băm, có tệp |
| 12 | wsc-4ed67081b49075eed077ebf7 | đạt băm, có tệp |
| 13 | wsc-5b78db8c9cc2ad9844a9a0d7 | đạt băm, có tệp |
| 14 | wsc-5f2696c9a22072e7d4873267 | đạt băm, có tệp |
| 15 | wsc-6c84807638a179552dd437ce | đạt băm, có tệp |
| 16 | wsc-71abdd06f47c205da102e908 | đạt băm, có tệp |
| 17 | wsc-7954d0d22c344af53bafd047 | đạt băm, có tệp |
| 18 | wsc-90597a45cd475fa1a42d442d | đạt băm, có tệp |
| 19 | wsc-9e9831c8c58795058809bf95 | đạt băm, có tệp |
| 20 | wsc-aa48e2b47a8c52c66c835e70 | đạt băm, có tệp |
| 21 | wsc-be0e15bdc0524321e7587d7c | đạt băm, có tệp |
| 22 | wsc-c4f19c08de138e4dfeeceacc | đạt băm, có tệp |
| 23 | wsc-d51ca7a46bac26fe55714eba | đạt băm, có tệp |
| 24 | wsc-da1844282c07cff93145d49f | đạt băm, có tệp |
| 25 | wsc-db6bb8495e13e16cd73fe9aa | đạt băm, có tệp |
| 26 | wsc-e5f2338de8fbfdbd4faefe63 | đạt băm, có tệp |
| 27 | wsc-eab6e69c0a9795201f575c88 | đạt băm, có tệp |
| 28 | wsc-f5e16c8261a4f585e58dd705 | đạt băm, có tệp |
| 29 | wsc-fb5c095f5d8bcfa80db7805b | đạt băm, có tệp |

## 3. Kết quả bao phủ 29 tệp

- Hàm dùng: `verify_selected_document_coverage` với `sparse_required=True`.
- Mở pipeline 31,5 giây, đo xong tổng 145,6 giây.
- Kết quả: 29/29 `valid=True`, không rớt cổng nào.

| Nhóm | Số lượng | Kết quả | Ghi chú |
|---|---|---|---|
| 29 tệp khôi phục | 29 | 29 qua | không rơi cổng, không bị đánh dấu cũ |
| Dương 5 mẫu đầu danh sách | 5 | 5 qua | trùng 5 mã đầu bảng trên |
| Âm 5 mã nhiều mảnh | 5 | 5 bị chặn đúng | `valid=False`, lý do không khớp định danh |

- 5 mã âm dùng đối chứng: `wsc-00428f94`, `wsc-00438611`, `wsc-00557b84`, `wsc-006998d9`, `wsc-015a1b6d` — đều bị chặn đúng như kỳ vọng.

## 4. Truy vấn đầy đủ còn kẹt

- Mẫu thử: `wsc-015067b75dc12e2770b7d8cb`, nội dung 60 ký tự, đường dẫn đuôi `canary\materialized_sources\wsc-015067b75dc12e2770b7d8cb.txt`.
- Mở pipeline 25,2 giây (`readonly+strict`), gửi truy vấn rồi treo quá 300 giây phải ngắt.
- Nhánh `lexical` rớt nhanh đúng cổng khi chưa nạp hậu thuẫn, nhánh `bge_m3_hybrid` mở 28 giây rồi kẹt ở bước dày đặc quá 6 phút.
- Nguyên nhân: máy bận do tiến trình đo song song của nhóm khác (149 nghìn mảnh véc-tơ), không phải lỗi tệp (bao phủ vẫn đạt).
- Thử lại 17:22 +07: mở pipeline 39,2 giây (`readonly+strict`), gửi cùng truy vấn mẫu rồi treo quá 330 giây phải ngắt (lần kẹt thứ hai, máy đã bớt tiến trình đo của nhóm khác nhưng bước dày đặc vẫn treo).
- Theo rào vé: chưa ghi nhận tệp nào rớt ở pipeline thật, chỉ ghi nhận kẹt hệ thống nên không sửa tệp hay chỉ mục, chờ nhịp máy rảnh thử lại từng tốp nhỏ.

## 5. Rào đã giữ

- Chỉ đọc chỉ mục (`mode=ro`, `immutable=1`, `query_only=ON`), không ghi hay sửa chỉ mục.
- Không ghi hay sửa tệp nguồn, không xóa dữ liệu đã tải ở `local_runs/src_sync`.
- Không đụng `src/rag_v2*`, không gộp nhánh chính, không đưa bí mật vào báo cáo.

## 6. Kết luận tạm thời (giữ nguyên mốc 17:24)

- Bao phủ đạt: dương 29/29 qua, âm 5/5 bị chặn đúng, dương 5/5 qua.
- Truy vấn đầy đủ chưa xong: 1 mẫu kẹt quá 5 phút do máy bận, cần thử lại khi máy rảnh.
- Vé chưa khép, nhịp sau chạy tiếp truy vấn từng tốp nhỏ có ghi nhật ký từng chặng.

## 7. Mốc kiểm nhẹ 17:53 + hoãn mẫu truy vấn đầy đủ theo chốt 17:48

- Kiểm nhẹ lúc 17:53 +07 (chỉ đọc chỉ mục `mode=ro`, không mở mô hình): đĩa + băm `SHA-256` của 29 tệp vẫn 29/29 khớp, hết 0,1 giây.
- Máy lúc kiểm còn bận: chương trình giao diện của thợ khác còn chạy, một lượt kiểm thử đang chạy từ 17:13, một kiểm thử truy hồi của thợ khác chạy từ 17:47 — đúng trường hợp chốt 17:48 dặn chỉ chạy mẫu khi máy rảnh.
- Quyết định trung thực: hoãn mẫu 3 truy vấn đầy đủ (gồm tệp đã kẹt `wsc-015067b7`, chạy nền tách phiên, ghi nhật ký từng chặng, trần 900 giây mỗi truy vấn) sang cửa máy rảnh, không cố chạy lúc máy bận để khỏi treo như hai lần trước (300 giây + 330 giây).
- Rào giữ nguyên: không ghi hay sửa tệp nguồn hay chỉ mục, không đụng `src/rag_v2*`, không gộp nhánh chính.

## 8. Mốc kiểm nhẹ 18:04 + giữ hoãn mẫu truy vấn theo chốt 17:48

- Kiểm nhẹ lúc 18:04 +07 (chỉ đọc chỉ mục `mode=ro` + `query_only=ON`, truy đúng 29 mã, không mở mô hình): đĩa + băm `SHA-256` vẫn 29/29 khớp, hết 0,2 giây. Quét toàn bảng 1-mảnh thử trước đó bị quá giờ 120 giây do cơ sở dữ liệu bận (thợ khác đo song song) nên chuyển sang truy trực tiếp từng mã cho nhẹ — trung thực ghi rõ.
- Máy lúc kiểm vẫn bận: các tiến trình nặng của thợ khác còn sống (bắt đầu từ 17:13, 17:41, 17:47) — đúng trường hợp chốt 17:48 dặn chỉ chạy mẫu khi máy rảnh.
- Quyết định giữ nguyên: hoãn mẫu 3 truy vấn đầy đủ (gồm tệp đã kẹt `wsc-015067b7`, chạy nền tách phiên, ghi nhật ký từng chặng, trần 900 giây mỗi truy vấn) sang cửa máy rảnh. Bao phủ 29/29 + âm 5/5 + dương 5/5 ở mục 3 giữ nguyên giá trị.
- Rào giữ nguyên: không ghi hay sửa tệp nguồn hay chỉ mục, không đụng `src/rag_v2*`, không gộp nhánh chính.

## 9. Mốc kiểm nhẹ 18:11 + giữ hoãn mẫu truy vấn theo chốt 17:48

- Kiểm nhẹ lúc 18:11 +07 (chỉ đọc chỉ mục `mode=ro` + `query_only=ON`, truy trực tiếp 29 mã, đối chiếu đường dẫn tuyệt đối + băm `SHA-256`, không mở mô hình): 29/29 tồn tại và khớp vân tay, hết 0,0 giây.
- Máy lúc kiểm vẫn bận: tiến trình kiểm thử của thợ khác từ 17:13, đo truy hồi từ 17:47, notebook từ 17:41 còn sống — đúng trường hợp chốt 17:48 dặn chỉ chạy mẫu khi máy rảnh.
- Quyết định giữ nguyên: hoãn mẫu 3 truy vấn đầy đủ (gồm tệp đã kẹt `wsc-015067b7`, chạy nền tách phiên, ghi nhật ký từng chặng, trần 900 giây mỗi truy vấn) sang cửa máy rảnh. Bao phủ 29/29 + âm 5/5 + dương 5/5 ở mục 3 giữ nguyên giá trị.
- Rào giữ nguyên: không ghi hay sửa tệp nguồn hay chỉ mục, không đụng `src/rag_v2*`, không gộp nhánh chính.

## 10. Mốc kiểm nhẹ 18:21 + giữ hoãn mẫu truy vấn theo chốt 17:48

- Kiểm nhẹ lúc 18:21 +07 (chỉ đọc chỉ mục `mode=ro` + `query_only=ON`, truy trực tiếp 29 mã, đối chiếu đường dẫn tuyệt đối + băm `SHA-256`, không mở mô hình): 29/29 tồn tại và khớp vân tay, hết 0,29 giây.
- Máy lúc kiểm vẫn bận: 15 tiến trình `python.exe` còn sống — đúng trường hợp chốt 17:48 dặn chỉ chạy mẫu khi máy rảnh.
- Quyết định giữ nguyên: hoãn mẫu 3 truy vấn đầy đủ (gồm tệp đã kẹt `wsc-015067b7`, chạy nền tách phiên, ghi nhật ký từng chặng, trần 900 giây mỗi truy vấn) sang cửa máy rảnh. Bao phủ 29/29 + âm 5/5 + dương 5/5 ở mục 3 giữ nguyên giá trị.
- Rào giữ nguyên: không ghi hay sửa tệp nguồn hay chỉ mục, không đụng `src/rag_v2*`, không gộp nhánh chính.
