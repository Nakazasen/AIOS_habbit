# Báo cáo INDEX-SWITCH-APP — junction + định tuyến trên máy nhà

- Trạng thái: **xong, chờ duyệt.** Không merge `main`. Không đụng PC0575.
- Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
- Ngày: 2026-10-03 đến 2026-10-04.
- Cổng watcher: `LAUNCH 1/4` lúc 2026-10-03 22:39:36 (`launchStallCount=1`). Điều kiện mở đã tới (R5 ĐẠT, đúng máy nhà, 4 thư mục tách còn trên ổ D). Không dùng nhánh 4 lần / `cho-muse`.

## 1. Bước 0

Đã pull `22ae49f`. Dừng Streamlit cổng `8501` và worker BGE trước khi tạo junction. Cầu nối Gemini cổng `8585` giữ nguyên (không giữ khóa collection).

## 2. Junction — không copy

Ổ C lúc làm còn khoảng 7,0 GB trống. Không copy 4 file kho. Bốn junction NTFS:

| Tên | Đích | Document | Chunk | Khớp manifest |
| --- | --- | ---: | ---: | --- |
| `collections\lsu` | `D:\Sandbox\AIOS_index_split_new\lsu` | 92 | 71.945 | đúng |
| `collections\dieu_tra_loi` | `D:\Sandbox\AIOS_index_split_new\dieu_tra_loi` | 681 | 74.439 | đúng |
| `collections\mom` | `D:\Sandbox\AIOS_index_split_new\mom` | 44 | 1.014 | đúng |
| `collections\tong_hop` | `D:\Sandbox\AIOS_index_split_new\tong_hop` | 72 | 2.402 | đúng |

Đếm bằng đường app mở (`collection_runtime_layout` + `SELECT COUNT(DISTINCT document_id) FROM chunks`, chỉ đọc). `tri_thuc` không phải junction, không bị ghi.

App chỉ coi collection là “có” khi sổ collection có `storage_root` khác rỗng. Junction nằm ở `collections\<id>\library.sqlite`, không có `storage_root`. Nếu không sửa, cờ bật vẫn rơi về kho cũ và không hiện badge. Đã sửa `_domain_index_ready`: collection tồn tại khi file `library.sqlite` mở được. Test mới trong `tests/test_index_domain.py` (39 passed).

## 3. Hỏi đáp — cờ bật

App mở lại với cùng biến của `RUN_AIOS_WORKSPACE_CHAT.bat` cộng `AIOS_DOMAIN_ROUTING_ENABLED=1`. Sổ thử `INDEX-SWITCH-APP` (`CONV-56620A6D`) trong sổ `mom_opcenter`, thư viện gốc `tri_thuc`, 75 nguồn đang bật. Không câu nào hiện badge khối `tong_hop`.

Worker trên ổ D nạp chậm (LSU khoảng 28 phút, Điều tra lỗi khoảng 11 phút) vì junction đọc file lớn trên ổ D. Không copy lên C.

| Câu | Badge | Nhận xét trích dẫn |
| --- | --- | --- |
| log jig báo bowskew nghĩa là gì, xử lý thế nào? | `Đang tra cứu khối LSU.` 5 đoạn, 1 nguồn | Đúng khối. Sổ này chỉ chồng 2 tài liệu LSU; câu trả lời nói chưa có định nghĩa bowskew trong nguồn đang bật, trích tài liệu thiết kế thay đổi nằm trong khối LSU. |
| mã lỗi C6770 trên Iris2024: nguyên nhân và đối sách? | Khi app thường (`AIOS_FEATURE_CHAT_ACTION=1`): **không có badge**. Action tra cứu ca lỗi chạy trước RAG. | Action trả đúng mã: từ điển C_CALL “Lỗi nguồn điện thấp Fuser IH”, phiếu 2024/3641 hiện `C6770`. Tắt action rồi hỏi lại thì badge `Đang tra cứu khối Điều tra lỗi.` 20 đoạn, 8 nguồn; gợi ý trích “Lưu trình lỗi phát sinh khi sản xuất AMS”. Câu chữ mô hình còn lẫn ngữ cảnh câu bowskew phía trước. |
| quy trình xuất kho WMS/Opcenter gồm bước nào? | `Đang tra cứu khối MOM.` 11 đoạn, 5 nguồn | Đúng khối. Gợi ý trích sơ đồ nhập xuất kho AMS và hướng dẫn APS. |
| hôm nay có gì mới? | `Đang tra cứu khối Điều tra lỗi. (Câu hỏi chưa rõ lĩnh vực — đã chọn khối khả dĩ nhất.)` 17 đoạn, 5 nguồn | Đúng yêu cầu câu mơ hồ. Router chọn Điều tra lỗi vì confidence 0, không chọn `tong_hop`. |

Vì sao phải sửa thêm đường hỏi: cửa sổ lexical 1 tài liệu không chứa tài liệu của khối vừa chọn, nên worker báo `semantic_index_coverage_incomplete`. Khi cờ bật, app tìm mọi nguồn đã sẵn sàng rồi chỉ giữ tài liệu có trong khối đó và khớp fingerprint. File: `workspace_chat_rag_v2_adapter.py`.

## 4. Rollback rồi bật lại

Tắt cờ (`AIOS_DOMAIN_ROUTING_ENABLED=0`), mở lại app, hỏi “quy trình xuất kho WMS gồm những bước nào?”. Không có dòng `Đang tra cứu khối`. Câu trả lời bình thường, nêu các bước xuất kho WMS/Opcenter từ kho `tri_thuc`.

Trạng thái cuối: cờ **BẬT**. Dòng `set "AIOS_DOMAIN_ROUTING_ENABLED=1"` nằm trong `RUN_AIOS_WORKSPACE_CHAT.bat`. Tiến trình app cuối nghe `8501`, health HTTP 200, cùng các biến launcher cũ cộng cờ định tuyến.

## 5. Kho cũ sau khi xong

| Mục | Trước | Sau |
| --- | --- | --- |
| File | `collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

## 6. Không làm / để lại

- Không embed, không ingest, không ghi `tri_thuc`, không merge `main`.
- Worker ghi thư mục log nhỏ trong khối trên ổ D (`lsu\logs`, `dieu_tra_loi\logs`). Không đụng file `library.sqlite` của khối.
- Câu mẫu C6770 trên app thường không hiện badge vì action tra cứu ca lỗi (cờ chat đã bật từ vé trước) chạy trước định tuyến. Muốn badge khối cho đúng câu đó thì tắt `AIOS_FEATURE_CHAT_ACTION` hoặc để action nhường câu hỏi tài liệu. Đã ghi để Muse chốt, không tự tắt cờ chat ở trạng thái cuối.
