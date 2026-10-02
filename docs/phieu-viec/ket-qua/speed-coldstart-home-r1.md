# Báo cáo vé SPEED-COLDSTART-HOME-R1 — chạy lại câu E3 qua lane 1

Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`, không force-push, **không ghi index**, không sửa mã sản phẩm, không nới cổng kiểm.

Báo cáo vé gốc: `docs/phieu-viec/ket-qua/speed-coldstart-home.md` (SHA `b88938e274`).

## 1. Kết luận

**Đủ tiêu chí vé R1.**

- E3 nhận `provider_validated` qua lane 1 (`gemini-web`) ngay lần gọi 1/3. Trace `trc_dc0fba32d727` trạng thái `valid`. Không có lỗi cổng.
- Cộng với 5/6 câu lane 1 của vé gốc: **6/6** câu lạnh qua lane 1. Lane 3 không dùng (vé gốc đã chứng minh router không gọi được; vé này không đo lại).
- SHA index production trước/sau không đổi.
- Worker persist PID **11896** còn sống, gắn lại, không nạp lại mô hình.

## 2. Cổng gate

- Watcher tự mở OMP **`LAUNCH 1/4`** lúc `2026-10-03 00:17:22` (`launchStallCount=1`, log `D:\Sandbox\Vong_lap_giao_viec\watcher.log`).
- **Điều kiện mở đã tới:** vé [NHÀ] đo lại E3, không chờ mã VM. Cầu nối Gemini `127.0.0.1:8585` trả `direct_ready`. Worker PID 11896 còn sống.
- Không đặt `cho-muse`, không quay no-op.

## 3. Cách đo

- Probe ngoài Git: `C:\tmp\speed-coldstart-home-r1\e3_r1.py`. Python 3.11 qua `uv`.
- Gắn lại worker trước khi hỏi: `initialize_worker` trên named pipe, `AIOS_RAGV2_WORKER_PERSIST=1`.
- Truy xuất chỉ đọc, đúng đường vé gốc: `search_with_summary`, `allowed_document_ids=None`, `limit=15`, `per_document_limit=3`.
- Viết đáp án: `synthesize_with_provider` + cầu nối `gemini-web`. Công tắc `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` chỉ trong tiến trình đo.
- Điểm khác duy nhất so với lượt trước: probe nhắc rõ mọi khẳng định vật liệu phải kết thúc bằng nhãn `[n]`. `max_attempts=1` để mỗi lần là một lời gọi Gemini, trần 3 lần. Lần này dừng ở lần 1 vì đã qua cổng.
- Không bật UI `localhost:8501`.

## 4. Gắn lại worker

| Mục | Giá trị |
| --- | --- |
| PID | 11896 |
| Pipe đuôi | `dde1fb0e7c4a` |
| `reused` | đúng |
| Nạp mô hình lần này | không |
| Tường gắn lại | 0,057 giây (lúc hỏi); lần kiểm riêng 0,1 giây |
| Lúc gắn | 2026-10-03 00:22:00 |

## 5. Index chỉ đọc

| Mục | Trước (00:21:48) | Sau (00:24:50) |
| --- | --- | --- |
| Đường dẫn | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng đường |
| Dung lượng | 2.942.201.856 B | 2.942.201.856 B |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | **khớp** |

## 6. Câu E3

Câu: Khi beam diameter NG thì cần kiểm tra những hạng mục nào (LD mirror, trục quang, độ sâu chỉnh)?

| Lần | Tìm (s) | Viết (s) | Tổng (s) | Lane | Mode | Trace |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 1/3 | 91,783 | 3,491 | 95,274 | 1 | `provider_validated` | `trc_dc0fba32d727` valid |

Provider/model: `AI trong máy tương thích OpenAI` / `gemini-web`. `provider_used=true`. Lỗi cổng: không có. Số nhãn trong đáp án nhận: 2. Số mảnh evidence: 15. Hỏi lúc 2026-10-03 00:24:15.

Đáp án nhận:

- Nếu trục quang lệch thì xảy ra hiện tượng không thể điều chỉnh đường kính beam [4]
- Khi trục quang nghiêng thì tia sẽ bị chiếu nghiêng lên Lens F [4]
- `LIMITATIONS: incomplete_query_term_coverage`

Không gọi lần 2 và lần 3.

## 7. Đối chứng

So với E3 lane 1 của `llm-enable-do-nha` (cùng câu, mode `provider_validated`, nhãn [4], cùng dòng `LIMITATIONS`):

- Cùng hướng: lệch trục quang thì không chỉnh được đường kính beam.
- Lượt này bỏ cụm “và timing” và bỏ câu chỉnh hướng X/Y. Thêm ý tia chiếu nghiêng lên Lens F. Không bịa số µm/mm.
- Vẫn thiếu hạng mục độ sâu chỉnh và LD mirror trong đáp án nhận. Dòng giới hạn phủ từ khóa vẫn còn, đúng cổng, không nới.

So với bản cục bộ bị từ chối ở vé gốc: không nhận bản cục bộ. Đáp án lần này là lane 1.

## 8. Sáu câu lạnh sau R1

Năm câu L1–E2 giữ nguyên số đo vé gốc (không hỏi lại). E3 lấy lượt R1.

| Câu | Lane 1 |
| --- | --- |
| L1–E2 | đã `provider_validated` ở vé gốc |
| E3 | `provider_validated` lượt này, trace valid |

Đủ 6/6 qua lane 1.

## 9. Trạng thái

`trang-thai.md` → `xong-cho-duyet`. Chờ Muse đối chứng. Không merge `main`.
