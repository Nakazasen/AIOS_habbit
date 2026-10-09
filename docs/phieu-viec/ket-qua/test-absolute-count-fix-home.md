# Báo cáo vé TEST-ABSOLUTE-COUNT-FIX-HOME (đổi hai ca ghim số tuyệt đối sang khẳng định quan hệ)

- Mã vé: `TEST-ABSOLUTE-COUNT-FIX-HOME`
- Ngày làm: 2026-10-09 (máy thực hiện, Python 3.11.14)
- Phạm vi: chỉ sửa đúng hai ca kiểm thử theo vé, không sửa mã chạy thật, không sửa ca nào khác, không ghi chỉ mục, không merge `main`.

## 1. Việc đã làm

### Ca 1 — đếm trên chỉ mục production thật (`tests/test_index_status.py`)

- Lưu ý tên hàm: trong vé ghi `test_production_index_counts`, nhưng trong tệp hiện tại ca đích tên là `test_index_status_matches_real_db_if_present` (ca duy nhất trong tệp ghim `149800`/`889`). Đã sửa đúng ca này, giữ nguyên tên hàm.
- Bỏ phần ghim `== 149800` và `== 889`: đổi thành `info.chunk_count == direct_chunks` và `info.doc_count == direct_docs` (kèm `> 0` để vẫn có giá trị khi kho lớn lên).
- Vân tay đổi sang quan hệ: `info.fingerprint_12 == direct_fp[:12]` cộng kiểm độ dài (`len(direct_fp) == 64`, `len(info.fingerprint_12) == 12`); bỏ chuỗi ghim `87a3626a85bc`.
- Dòng trạng thái cũng dựng lại từ số đọc trực tiếp (`format_thousands_vi(direct_docs)`, `format_thousands_vi(direct_chunks)`, `direct_fp[:12]`) nên không còn số tuyệt đối nào trong ca.
- Điều kiện bỏ qua khi vắng chỉ mục production giữ nguyên.

### Ca 2 — bản đồ miền (`tests/test_workspace_chat_production_index_filtering.py`, `test_domain_document_map_counts`)

- Bỏ toàn bộ số ghim 889 / 92 / 681 / 44 / 72.
- Đổi sang khẳng định quan hệ:
  - tổng số bản đồ `> 0`, mỗi miền (`lsu`, `dieu_tra_loi`, `mom`, `tong_hop`) có ít nhất một tài liệu;
  - số đọc qua hàm lấy theo miền khớp số đọc trực tiếp từ bản đồ đã nạp (so từng miền với `doc_map`);
  - bốn miền rời nhau hoàn toàn (đủ 6 cặp), hợp lại bằng đúng tập khóa bản đồ, tổng bốn miền bằng tổng bản đồ.
- Không giữ lại con số tuyệt đối nào của kho hiện tại trong ca này.

## 2. Kiểm chứng sau sửa (nguyên văn)

Lệnh chạy (chỉ hai tệp chứa hai ca, theo đúng vé):

```text
uv run --no-sync --group dev pytest tests/test_index_status.py tests/test_workspace_chat_production_index_filtering.py -q
```

Kết quả:

```text
...............                                                          [100%]
15 passed in 86.96s (0:01:26)
```

- Không có ca đỏ trong hai tệp nên không rơi nhánh "dừng và báo nguyên văn".
- Kiểm tra bằng script: trong thân hai ca đã sửa không còn chuỗi `149800`, `889` (ca 1), `== 889/92/681/44/72` (ca 2), hay chuỗi vân tay cũ.
- Kiểm tra hồi quy phụ trợ: `compileall src tests` sạch; `python -m aios_habit.cli audit` cho `"status": "PASS"`; `import aios_habit.workspace_chat_app` thành công.
- Bộ toàn kho (`pytest -q` đầy đủ) không chạy trong vé này (ngoài phạm vi vé, tốn ~80 phút theo lịch sử); hai tệp đích đã xanh toàn bộ.

## 3. Rào cứng và ghi chú trung thực

- Diff của vé chỉ gồm 2 tệp kiểm thử trên (42 thêm / 12 bớt) cộng báo cáo và `trang-thai.md`; không đụng `src/`, không ghi chỉ mục, không merge `main`.
- Tiêu đề mô tả ở đầu tệp bản đồ miền vẫn còn dòng chữ ví dụ số cũ (không phải khẳng định trong ca, ngoài phạm vi "chỉ sửa hai ca" nên để nguyên, ghi rõ tại đây để điều phối quyết).
- Không phát hiện thêm ca đỏ nào trong hai tệp.
