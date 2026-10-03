# Báo cáo INDEX-SPLIT-R3 — dừng vì công cụ tách lỗi trên Windows

- Trạng thái: **DỪNG, đặt `cho-muse`.** Không có manifest. Không dựng collection cho app, không bật cờ định tuyến, không hỏi đáp thử.
- Máy: `h410asrock` (máy nhà). Không đụng PC0575. Không merge `main`. Không sửa code.
- Ngày: 2026-10-03. Nhánh: `phieu-viec/rag-fix1`. Tip khi nhận vé: `591ae97` (có Phase A3 `a7a005c`).
- Cổng watcher: `LAUNCH 1/4` lúc 2026-10-03 21:52:35 (`launchStallCount=1`). Điều kiện mở đã tới (đúng máy nhà, Phase A3 đã có trên nhánh). **Không** dùng nhánh 4 lần watcher. Lý do `cho-muse`: lệnh tách thật thoát mã 1 trước khi ghi manifest.

## 1. Bước 0

`--help` liệt kê `--fallback-threshold` và `--no-fallback-domain`.

Lệnh module chạy bằng `PYTHONPATH=src uv run --no-sync --group dev python` vì `python` trên PATH là stub Microsoft Store. Python thực tế: 3.11.

| Mục | Trước | Sau lần chạy lỗi |
| --- | --- | --- |
| File | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

SHA khớp ghim vé (`45eb0e07…b7c0`). Kho cũ chỉ bị đọc.

Dung lượng trống trước khi tách:

| Ổ | Byte trống | Cổng |
| --- | ---: | --- |
| C | 2.129.387.520 (~2,0 GB) | không ghi file tách lên C |
| D | 68.548.808.704 (~63,8 GB) | đạt (≥ 3,5 GB) |

Đích `D:\Sandbox\AIOS_index_split_new` lúc bắt đầu chưa tồn tại.

## 2. Lệnh đã chạy

```
python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "D:\Sandbox\AIOS_index_split_new" --allow-production
```

Mã thoát **1**. Log ngoài git: `D:\Sandbox\AIOS_index_split_backup\split-r3-20261003.log`.

Dòng cuối trước lỗi: `Đang tách kho LSU: 92 tài liệu...`

```
sqlite3.OperationalError: unable to open database: file:C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite?mode=ro
```

Vị trí: `src/aios_habit/split_index_by_domain.py` dòng 615, `ATTACH DATABASE 'file:%s?mode=ro'`. Kết nối đích mở bằng `sqlite3.connect(đường Windows)` **không** bật `uri=True`, nên SQLite coi chuỗi `file:C:/...?mode=ro` là tên file thường. Dấu `:` sau ổ `C` làm mở thất bại. Bước mở nguồn bằng `sqlite3.connect(..., uri=True)` thì chạy được (integrity + phân loại đã xong). Lỗi này không lộ trên VM vì đường dẫn không có ký tự ổ đĩa.

Không có `domain_manifest.json`. Không kiểm được `overall`, 4 khối, 889 document, 149.800 chunk, `overlapping_documents`, hay `low_confidence`.

## 3. Hiện trạng để lại (không xóa, không chạy lại)

| Đường dẫn | Byte | mtime |
| --- | ---: | --- |
| `D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite` | 86.016 | 2026-10-03 21:57:28 |

File này chỉ có lược đồ (tạo trước khi `ATTACH` lỗi), chưa copy chunk. Không có thư mục `dieu_tra_loi`, `mom`, `tong_hop`. Không có manifest. Không đụng app. Ổ C không nhận file tách.

Theo vé: không xóa, không chạy lại `--overwrite` mù. Thư mục đích đúng là của vé này, nhưng lần chạy lại chỉ an toàn sau khi Muse vá lỗi `ATTACH` trên Windows.

## 4. Việc Muse cần làm

Vá chỗ gắn kho nguồn ở chế độ chỉ đọc trên Windows (bật URI cho kết nối đích, dùng dạng `file:///C:/...?...`, hoặc cách tương đương đã có ở `Path.as_uri()`), test có đường dẫn ổ đĩa, rồi phát hành lại. OMP chưa sửa code.

## 5. Không làm

- Không embed lại, không ingest, không sửa `tri_thuc\library.sqlite`.
- Không dựng collection, không bật `AIOS_DOMAIN_ROUTING_ENABLED`, không restart app, không hỏi đáp thử.
