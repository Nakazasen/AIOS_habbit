# VÉ: INDEX-VERIFY-HOME (kiểm chứng chỉ mục máy nhà theo chuẩn vân tay logic mới)

- Mã vé: `INDEX-VERIFY-HOME`
- Role gợi ý: SMOL/TINY (chỉ-đọc, nhanh)
- Máy: nhà h410asrock (máy giữ chỉ mục gốc)
- Báo cáo: `docs/phieu-viec/ket-qua/index-verify-home.md`

## Bối cảnh

Ngày 07/10 phía máy công ty đã kiểm chứng chỉ mục theo chuẩn mới (thay MD5 thô bằng vân tay logic vì byte SQLite đổi khi tiến trình chốt sổ): `quick_check = ok`, 889 tài liệu / 149.800 mảnh, vân tay logic nội dung `87a3626a85bc32c81ec899c0b5c47d59f6208afd73c80cc94c0a4f2f1df6de3c`, vân tay tổng `fce85b60b783d0a59545f87042ac2b1b63212bbd8d9dd9948df647b9dbdcf`. User chỉ đạo triển khai ngang sang máy nhà: chạy đúng phép kiểm này trên chỉ mục gốc ở máy nhà và đối chiếu.

## Việc phải làm (CHỈ-ĐỌC — mở `mode=ro`, `query_only=ON`)

1. `PRAGMA quick_check` trên chỉ mục máy nhà.
2. Đếm: số tài liệu, số mảnh (tách mảnh tóm tắt / mảnh nội dung), số mã có vân tay nguồn / trống vân tay.
3. Tính vân tay logic theo đúng 2 công thức đã dùng ở máy công ty (SHA-256 trên danh sách đã sắp xếp `mã | vân tay nội dung | số mảnh nội dung` cho công thức nội dung; `mã | vân tay nội dung | tổng mảnh` cho công thức tổng) và đối chiếu với mốc máy công ty ở trên: khớp hay lệch, lệch ở đâu (liệt kê nhóm mã lệch nếu có).
4. Ghi mọi kết quả vào báo cáo kèm đường dẫn chỉ mục + kích thước tệp (chỉ để tham khảo, không dùng làm chuẩn).

## Rào cứng

- Chỉ-đọc tuyệt đối: không ghi/sửa/vacuum chỉ mục, không đụng tệp nguồn.
- Không merge `main`. Không chạy việc ghi index nào song song khi đang kiểm.
