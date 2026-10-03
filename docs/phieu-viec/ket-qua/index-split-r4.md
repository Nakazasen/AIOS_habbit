# Báo cáo INDEX-SPLIT-R4 — dừng vì tự kiểm vượt giới hạn biến SQL

- Trạng thái: **DỪNG, đặt `cho-muse`.** Không có manifest. Không dựng collection cho app, không bật cờ định tuyến, không hỏi đáp thử.
- Máy: `h410asrock` (máy nhà). Không đụng PC0575. Không merge `main`. Không sửa code.
- Ngày: 2026-10-03. Nhánh: `phieu-viec/rag-fix1`. Tip khi nhận vé: `8d1c026` (có vá URI `98ba03b`).
- Cổng watcher: `LAUNCH 1/4` lúc 2026-10-03 22:12:40 (`launchStallCount=1`). Điều kiện mở đã tới (đúng máy nhà, vá `98ba03b` đã có trên nhánh). **Không** dùng nhánh 4 lần watcher. Lý do `cho-muse`: lệnh tách thật thoát mã 1 sau khi copy khối LSU, trước khi ghi manifest.

## 1. Bước 0

`python` trên PATH là stub Microsoft Store. Lệnh module chạy bằng `PYTHONPATH=src uv run --no-sync --group dev python` (Python 3.11.14). Import `_open_read_only` in `ok`. File nạp: `src/aios_habit/split_index_by_domain.py`.

| Mục | Trước | Sau lần chạy lỗi |
| --- | --- | --- |
| File | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

SHA khớp ghim vé (`45eb0e07…b7c0`). Kho cũ chỉ bị đọc.

Dung lượng trống trước khi tách: ổ D còn 68.548.538.368 byte (~63,8 GB). Ổ C không nhận file tách.

File dở của R3 trước khi chạy lại: `D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite` 86.016 byte. Vé cho phép `--overwrite` ghi đè đúng file này.

## 2. Lệnh đã chạy

```
python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "D:\Sandbox\AIOS_index_split_new" --allow-production --overwrite
```

Mã thoát **1**. Thời gian khoảng 86 giây. Dòng in trước lỗi: `Đang tách kho LSU: 92 tài liệu...`

Vá URI của R3 đã qua được: không còn `unable to open database`. Lỗi mới ở tự kiểm, sau khi copy khối LSU và `commit`:

```
sqlite3.OperationalError: too many SQL variables
```

Vị trí: `src/aios_habit/split_index_by_domain.py` dòng 451, trong `_verify_domain`. Câu lệnh gắn một placeholder `?` cho mỗi `chunk_id`:

```
SELECT chunk_id, COUNT(*) FROM <bảng nhúng> WHERE chunk_id IN (?,?,...) GROUP BY chunk_id
```

SQLite đi kèm Python này là 3.50.4, `MAX_VARIABLE_NUMBER=32766`. Khối LSU có 92 tài liệu nhưng số chunk lớn hơn giới hạn biến, nên `IN (...)` fail-closed. Không có `domain_manifest.json`. Không kiểm được `overall`, 4 khối, 889 document, 149.800 chunk, `overlapping_documents`, hay `low_confidence`.

## 3. Hiện trạng để lại (không xóa, không chạy lại)

| Đường dẫn | Byte | mtime |
| --- | ---: | --- |
| `D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite` | 1.155.637.248 | 2026-10-03 22:16:51 |

Chỉ có thư mục `lsu`. Không có `dieu_tra_loi`, `mom`, `tong_hop`. Không có manifest. File LSU là bản copy dở của lần chạy này (lớn hơn 86.016 byte của R3), đã `commit` trước khi tự kiểm nổ. Không đụng app. Ổ C không nhận file tách.

Theo cổng dừng của vé tách: không xóa, không chạy lại `--overwrite` mù. Chạy lại chỉ an toàn sau khi Muse vá chỗ tự kiểm (chia mẻ dưới 32766 biến, hoặc so bằng `JOIN` thay vì `IN` một phát).

## 4. Việc Muse cần làm

Vá `_verify_domain` (và mọi `IN` cùng kiểu nếu có) để không gắn quá `MAX_VARIABLE_NUMBER` biến trên một câu, rồi test với số chunk > 32766. OMP chưa sửa code.

## 5. Không làm

- Không embed lại, không ingest, không sửa `tri_thuc\library.sqlite`.
- Không dựng collection, không bật `AIOS_DOMAIN_ROUTING_ENABLED`, không restart app, không hỏi đáp thử.
