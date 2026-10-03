# Báo cáo vé `INDEX-NGUON-KIEM-KE` — kiểm kê document theo thư mục nguồn (chỉ đọc)

- Máy: `h410asrock`, 2026-10-03 19:58–20:04 +07.
- Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`, không force-push.
- Kết quả: **ĐẠT phần kiểm kê kho đang chạy**, với một lệch đường dẫn phải nói rõ ở mục 1.

## 1. Đường vé ghi không còn — không phải cổng chờ

Vé yêu cầu mở `C:\AIOS_habit_index_ve03\library.sqlite`. Thư mục này **không còn**. Báo cáo `don-canary` đã xóa cả thư mục canary đó ngày 2026-10-01. Đây là sự thật cố định, không phải điều kiện mở để chờ watcher bật lại.

Kho app đang resolve (đọc `config/workspace_chat_rag_v2.local.json`, key `runtime.root`, không chép secret):

`C:\AIOS_workspace_chat_rag_v2_production`

Chuỗi resolve đã chốt ở vé `MOVE-INDEX-C`: `runtime.root / bge_m3_hybrid / collections / tri_thuc / library.sqlite`. File đó tồn tại. Mọi số bên dưới lấy từ file này, mở `mode=ro` + `PRAGMA query_only=ON`. Không ingest, không embed, không ghi vào `C:\AIOS_habit_index_ve03\` (thư mục không tồn tại, không tạo lại) và không ghi vào thư mục index đang chạy.

Bản đông trên D (`D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`, 2.552.659.968 byte, mtime 2026-09-28 05:55) là bản ghim cũ, **không** phải kho app đang chạy. Vé này không mở file đó để truy vấn.

## 2. Chứng minh chỉ đọc

| Phép kiểm | Trước | Sau |
| --- | --- | --- |
| Kích thước | 2.942.201.856 byte | 2.942.201.856 byte |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng chuỗi |
| `-wal` / `-shm` / `-journal` | không có | không có |

`COUNT(*)` trên bảng `chunks` = **149.800**. `COUNT(DISTINCT document_id)` = **889**. Không có `document_id` nào gắn hơn một `source_path`. Hai số nhóm bên dưới cộng lại đúng hai tổng này.

Vé ước ~107k chunk / 889 document. Số document khớp 889. Số chunk cao hơn vì kho C đã được app và các vé merge bổ sung sau mốc ghim `062ec090…` (2.552.659.968 byte). Không có cột `domain`.

Chunk `retrievable=1`: 121.331 (ghi thêm để đối chiếu, không thay bảng chính).

## 3. Bảng thư mục nguồn

Gom theo tiền tố thư mục thật sự còn trong `source_path`. Không trích nội dung chunk, không liệt kê tên file.

| Thư mục nguồn | Document | Chunk |
| --- | ---: | ---: |
| `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\materialized_sources` | 496 | 133.144 |
| `gpu-dc:\` (tiền tố tổng hợp khi merge, không phải ổ đĩa) | 329 | 12.720 |
| `gpu-262b:\` (tiền tố tổng hợp khi merge, không phải ổ đĩa) | 19 | 2.883 |
| `C:\AIOS_workspace_chat_rag_v2_production\materialized_sources` | 45 | 1.053 |
| **Tổng** | **889** | **149.800** |

Đối chiếu số đã biết: 12.720 chunk / 329 document khớp báo cáo `gpu-dc`; 2.883 chunk khớp vé `gpu-262b`. 496 document / 133.144 chunk là khối canary cũ đã thành lõi production. 45 document / 1.053 chunk là phần app tự chuẩn bị trên ổ C sau khi chuyển kho.

## 4. Ba nguồn user hỏi có bị trộn không

Có: **một file, một collection `tri_thuc`**, không lọc theo lĩnh vực. Bốn nhóm đường dẫn ở bảng trên đang nằm chung.

Giới hạn: `source_path` của khối 496 **không còn** thư mục gốc MOM, thư mục LSU trên Drive, hay thư mục Điều-tra-lỗi. Cả 496 đều trỏ vào `materialized_sources` của canary. Quét từ khóa trên `source_path` (không đọc nội dung):

| Từ khóa | Document | Nằm ở nhóm nào |
| --- | ---: | --- |
| `MOM` | 0 | không thấy |
| `Dieu-tra` / `điều-tra` | 0 | không thấy |
| `LSU` | 4 | cả 4 thuộc `gpu-262b:\` |
| `Điều chỉnh` / `dieu chinh` | 1 | thuộc `gpu-dc:\` |

Vì vậy không tách được 496 document kia về đúng 3 thư mục gốc chỉ bằng cột `source_path`. `metadata_json` lồng bên trong cũng không có trường đường dẫn gốc (chỉ có `bbox`, `page`, `sheet`, `extractor`…). Muốn biết 496 document thuộc MOM / LSU / Điều-tra thì cần sổ nguồn khác, không có trong index này.

## 5. Collection khác

Dưới runtime production `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\` chỉ có `tri_thuc`. Không có `collections/<id>/` thứ hai.

Các file `library.sqlite` khác trên ổ C (`C:\AIOS_staging_262`, `C:\AIOS_staging_262b`, `C:\AIOS_staging_dc`) là staging, không nằm trong `collections/<id>/` của runtime đang chạy. Vé này không mở chúng.

## 6. Không làm

- Không ingest, không embed, không sửa index, không tạo lại `C:\AIOS_habit_index_ve03\`.
- Không merge `main`.
