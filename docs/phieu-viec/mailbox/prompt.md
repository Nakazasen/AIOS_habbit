# Vé BK-82 — Rà soát tay 82 dòng thiếu hiện tượng/nguyên nhân/công đoạn

LANE: [NHÀ] — OMP thực hiện trên máy nhà (cần đối chiếu workbook gốc).

## Bối cảnh
Báo cáo B0-MEASURE (mục 3.3, log `C:/tmp/b0-measure/scan4.out.txt`): 82 dòng thiếu
một trong ba trường — hiện tượng 33 dòng (chủ yếu 2026/2xxx), nguyên nhân 8 dòng,
công đoạn 39 dòng. Không tự động bù được, cần người đối chiếu.

## Việc cần làm
1. Lấy danh sách 82 dòng từ `C:/tmp/b0-measure/scan4.out.txt`.
2. Đối chiếu từng dòng với workbook gốc `Loi KDTPS.xlsx` sheet `History KDTPS`;
   bổ sung được thì bổ sung vào **bản copy** DB (`C:/tmp/b0-dict/error_cases_dict.db` —
   backup + `integrity_check` trước/sau, KHÔNG đụng DB gốc).
3. Dòng nào không bổ sung được: ghi rõ lý do vào báo cáo (không bịa).

## Tiêu chí ĐẠT
- 82/82 dòng được xử lý (đã bổ sung hoặc có lý do rõ ràng).
- Báo cáo `docs/phieu-viec/ket-qua/bk-82.md`, commit riêng trên `phieu-viec/rag-fix1`.
- Không ghi DB gốc, không đụng ổ D, không merge `main`.
