# Báo cáo vé AUDIT-ENV-FAILOVER-HOME — Kiểm nhất quán cấu hình tuyến tổng hợp sau khi áp 3 tầng

- **Mã vé:** `AUDIT-ENV-FAILOVER-HOME`
- **Máy thực hiện:** NHÀ `h410asrock` (OMP — thợ phụ, chỉ đọc cấu hình).
- **Thời gian:** 2026-10-09 00:04 – 00:06 +07.
- **Căn cứ:** vé `CONFIG-SYNTH-TIERS-HOME` (verdict ĐẠT phần cấu hình) + báo cáo `docs/phieu-viec/ket-qua/config-synth-tiers-home.md` + file sao lưu `docs/phieu-viec/ket-qua/pre-config-synth-tiers.txt`.
- **Cách làm:** chỉ đọc tên biến trong tệp cấu hình môi trường máy nhà (27 tên, không chép khóa), đối chiếu tên model/thứ tự chuỗi với cấu hình chốt, rà biến tạm/sót và định nghĩa trùng, đọc file sao lưu, tra code dùng biến.
- **Rào cứng giữ nguyên:** chỉ đọc, không sửa biến nào, không chạy lại lượt đo, không đụng chỉ mục, không merge `main`. Không in bất kỳ ký tự nào của khóa.

## 1. Biến tuyến tổng hợp đang có mặt (điểm 1 của vé, chỉ tên biến + giá trị không nhạy cảm)

| Tên biến | Giá trị không nhạy cảm tại máy nhà | Vai trò |
|---|---|---|
| `AIOS_LOCAL_AI_ENDPOINT` | đầu `https://api.commandcode.ai/provider/v1/chat/completions` | cổng gọi tuyến tổng hợp |
| `AIOS_LOCAL_AI_MODEL` | tên model chính đã chốt tầng 1 | model chính |
| `AIOS_LOCAL_AI_FAILOVER_MODELS` | chuỗi 2 tên đã chốt tầng 2 + tầng 3 | chuỗi dự phòng |
| `AIOS_LOCAL_AI_API_KEY` | (có mặt — KHÔNG in giá trị) | khóa gọi tuyến (nhạy cảm, chỉ xác nhận tồn tại) |
| `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS` | `1` (BẬT) | công tắc cho phép nhà cung cấp bên ngoài |
| `AIOS_LOCAL_AI_LOCALITY` | `cloud` | vùng chạy tuyến |
| `AIOS_SYNTHESIS_STRICT_CITATION_CONTRACT` | chưa đặt (TẮT theo mặc định code) | cờ hợp đồng trích dẫn nghiêm ngặt |

Code dùng các biến trên: `src/aios_habit/ai_router.py` (đọc model chính + chuỗi dự phòng), `src/aios_habit/rag_v2/synthesis.py` (công tắc cho phép + cờ hợp đồng), `src/aios_habit/rag_v2_synthesis_provider.py` (công tắc cho phép), `src/aios_habit/ai_provider_bridge.py` (vùng chạy). Tệp môi trường máy nhà không nằm trong Git (đúng — khóa không lên kho).

## 2. Đối chiếu cấu hình chốt + rà mâu thuẫn/sót (điểm 2 của vé)

| Hạng mục | Cấu hình chốt | Thực tế máy nhà | Kết luận |
|---|---|---|---|
| Model chính | tầng 1 đã chốt | đúng tên đã chốt | KHỚP |
| Chuỗi dự phòng | tầng 2 → tầng 3 đã chốt, đúng thứ tự | đúng 2 tên, đúng thứ tự | KHỚP |
| Biến tạm/sót (`broken`/`test`/`temp`/`sante`) trong tệp môi trường | không còn | không dòng nào khớp | KHÔNG SÓT |
| Định nghĩa trùng tên biến | không | 0 tên trùng | KHÔNG TRÙNG |
| Tệp môi trường khác (`.env.*`) | không | chỉ 1 tệp duy nhất | KHÔNG PHÂN MẢNH |
| Tên model cũ trong code `src` | không còn tham chiếu | 0 file khớp | KHÔNG SÓT |

## 3. File sao lưu trước đổi (điểm 3 của vé)

| Hạng mục | Kết quả |
|---|---|
| Tồn tại | có — `docs/phieu-viec/ket-qua/pre-config-synth-tiers.txt` (9 dòng) |
| Thời điểm ghi | 2026-10-08 23:17 +07, máy nhà |
| Nội dung | 5 tên biến tuyến (không chứa khóa): cổng gọi, model chính, chuỗi dự phòng 2 tầng cũ, công tắc cho phép, vùng chạy |
| Khớp phần nó ghi | KHỚP — chuỗi dự phòng cũ đúng 2 tầng miễn phí trước khi đổi sang 3 tầng; model chính và cổng gọi trùng hiện tại |

## 4. Ghi chú thời điểm + công tắc cho phép (điểm 4 của vé)

Vé mở cổng tổng hợp cho giao diện (`UI-LOCALONLY-SYNTH-OPEN-HOME`) chưa chạy tại thời điểm kiểm này. Công tắc cho phép nhà cung cấp bên ngoài đang **BẬT** (`1`) — với vé này, trạng thái BẬT là hiệu lực hiện hành của tệp môi trường, không tính là lệch; việc mở cổng cho giao diện là vé riêng tiếp theo, đối chiếu lại phạm vi mở sau khi vé đó chạy.

## 5. Kết luận (điểm 5 của vé)

**Cấu hình nhất quán** — chuỗi 3 tầng đúng chốt, không biến mâu thuẫn/sót/trùng, file sao lưu tồn tại và khớp, cờ hợp đồng trích dẫn nghiêm ngặt đang TẮT đúng quyết định giữ. **Không có tên biến nào cần dọn, không tự sửa gì.**
