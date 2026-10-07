# VÉ: INDEX-PROD-HOME (kiểm chứng đúng tệp chỉ mục app máy nhà đang đọc thật)

- Mã vé: `INDEX-PROD-HOME`
- Role gợi ý: SMOL/TINY (chỉ-đọc, nhanh)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/index-prod-home.md`

## Bối cảnh

Vé `INDEX-VERIFY-HOME` (ĐẠT 07/10) đã kiểm chứng tệp backup pre-split `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite`: nguyên vẹn, khớp logic 100% với máy công ty. Nhưng báo cáo đó cũng ghi nhận còn một ứng viên khác cùng kích thước ở đường dẫn production (`C:\AIOS_workspace_chat_rag_v2_production\...`). Trước khi coi máy nhà sẵn sàng dùng chính thức, phải xác định dứt khoát: **app trên máy nhà đang mở đúng tệp nào** (theo cấu hình app thật), và tệp đó có nguyên vẹn + khớp logic với bản đã kiểm chứng hay không.

## Việc phải làm (CHỈ-ĐỌC)

1. Xác định từ cấu hình/khởi động app thật trên máy nhà: đường dẫn chỉ mục app đang nạp khi mở sổ (ghi rõ bằng chứng: biến cấu hình/dòng log/đường dẫn app công bố).
2. Trên đúng tệp đó (mở `mode=ro`, `query_only=ON`): `quick_check`, đếm tài liệu/mảnh (tách tóm tắt/nội dung), tính vân tay logic nội dung — đối chiếu mốc đã kiểm chứng: 889 / 149.800 (385 + 149.415), vân tay nội dung `87a3626a85bc32c81ec899c0b5c47d59f6208afd73c80cc94c0a4f2f1df6de3c`.
3. Nếu app đang đọc tệp KHÁC tệp đã kiểm chứng: nói rõ khác ở đâu (đường dẫn, kích thước, số đếm, vân tay) và mức rủi ro khi dùng chính thức; không tự ý đổi cấu hình — chỉ báo cáo, điều phối quyết.

## Rào cứng

- Chỉ-đọc tuyệt đối với mọi tệp chỉ mục; không đổi cấu hình app; không ghi/vacuum; không merge `main`.
