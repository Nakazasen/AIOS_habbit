# Báo cáo vé SPEED-COLDSTART-HOME — nghiệm thu khởi động lạnh trên máy nhà

Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`, không force-push, **không ghi index**.

## 1. Kết luận

**Chưa đủ để ghi ĐẠT toàn vé.** Hai tiêu chí đạt, một tiêu chí chưa đủ.

- Khởi động lại tiến trình app 3/3 lần gắn lại đúng worker cũ, cùng PID, không nạp lại mô hình. Cấu hình lệch bị chặn đúng thiết kế.
- Init lạnh nạp mô hình: **112,1 giây** (ONNX), nhanh hơn dải PC0575 180,9–408,5 giây.
- 6 câu lạnh: **5/6** qua lane 1 (`gemini-web`, `provider_validated`). Câu E3 gọi Gemini 3 lần nhưng thiếu nhãn trích dẫn, cổng kiểm từ chối, rơi về tổng hợp cục bộ. Không tính là trả lời lane 1. Không nới cổng kiểm.
- Lane 3 (Nakazasen Router) không dùng. Vé trước đã chứng minh router không gọi được. Vé này không đo chay bằng router.
- SHA index production trước/sau không đổi (mục 4).

## 2. Cổng gate

- Watcher tự mở lại OMP **`RELAUNCH 1/4`** lúc `2026-10-02 23:44:25` (`launchStallCount=1`, log `D:\Sandbox\Vong_lap_giao_viec\watcher.log`).
- **Điều kiện mở đã tới:** `LLM-ENABLE-DO-NHA-R1` đã ĐẠT (báo cáo commit `2325065`, verdict `daf177b`). Cầu nối Gemini `127.0.0.1:8585` trả `direct_ready`. Không đặt `cho-muse`, không quay no-op.

## 3. Cách đo

- Không bật UI `localhost:8501`. Hội thoại theo sổ có thể chuẩn bị nguồn và ghi index. Cùng lý do vé `hodap-home` và `llm-enable-do-nha`.
- “Khởi động lại app” được đo bằng tiến trình client mới gọi `initialize_worker` trên named pipe. Đó là đường app dùng khi mở lại (`AIOS_RAGV2_WORKER_PERSIST=1`).
- Không gọi `query_ready` của app cho 6 câu: đường đó lọc theo file nguồn, 348/889 file nguồn không còn trên đĩa, worker sẽ báo index cũ và dừng. Truy xuất dùng đúng cách chỉ đọc của hai vé trước: `search_with_summary`, `allowed_document_ids=None`, `limit=15`, `per_document_limit=3`.
- Viết đáp án: `synthesize_with_provider` + router chỉ cầu nối `openai_compatible_local` / `gemini-web`. Công tắc `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` đặt trong tiến trình đo. Nhắc định dạng tiếng Việt nằm trong probe, không sửa mã sản phẩm.
- Probe ngoài Git: `C:\tmp\speed-coldstart-home\`.

## 4. Index chỉ đọc

| Mục | Trước (23:48) | Sau 6 câu |
| --- | --- | --- |
| Đường dẫn | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng đường |
| Dung lượng | 2.942.201.856 B | 2.942.201.856 B |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | **khớp** (đối lúc 00:09 ngày 2026-10-03) |

## 5. Init lạnh và 3 lần gắn lại

Worker persist PID **11896**, pipe đuôi `dde1fb0e7c4a`, backend `onnx`. Log: `collections\tri_thuc\logs\bge_worker_daemon.stderr.log`.

| Pha | mili giây |
| --- | ---: |
| Kiểm mô hình | 1,2 |
| Nạp mô hình | 39.254,1 |
| Mở index | 88,1 |
| Nạp đặc | 33.909,7 (121.331 khối) |
| Nạp thưa | 38.857,6 (121.331 khối, 22.890 từ) |
| **Tổng init** | **112.111,4** |

So PC0575 (180,9–408,5 giây): máy nhà nhanh hơn, chủ yếu vì ONNX + đĩa nhà. Không kết luận GPU thắng tuyệt đối vì hai máy khác đĩa và tải.

Ba tiến trình client mới, worker không bị tắt giữa các lần:

| Lần | Gắn lại | PID | Nạp mô hình lần này | Tường (giây) |
| --- | --- | ---: | --- | ---: |
| 1 | đúng | 11896 | không | 0,060 |
| 2 | đúng | 11896 | không | 0,010 |
| 3 | đúng | 11896 | không | 0,011 |

Cấu hình lệch (`retrieval_limit` khác): lỗi `persistent_worker_configuration_mismatch`. PID trước/sau vẫn 11896, worker vẫn sẵn sàng. Đúng thiết kế P3+P4.

Tiến trình hỏi 6 câu cũng gắn lại trước khi hỏi: 0,012 giây, cùng PID, không nạp lại mô hình.

## 6. Sáu câu lạnh

Thời gian là lượt ngay sau tiến trình mới (23:57–00:00). Cột viết là thời gian gọi lane 1, kể cả lần cổng kiểm từ chối. Đáp án nhận là lần `provider_validated`. L1 và E1 nhận từ lượt hỏi lại vì lượt đầu rơi cục bộ. E3 không có lần nào qua cổng.

| Câu | Tìm (s) | Viết (s) | Tổng (s) | Lane | Mode nhận | Trace |
| --- | ---: | ---: | ---: | --- | --- | --- |
| L1 | 35,06 | 6,13 | 70,16 (gồm mở pipeline 28,98) | 1 | `provider_validated` (hỏi lại) | `trc_b3b24787ebce` valid |
| L2 | 20,20 | 3,35 | 23,55 | 1 | `provider_validated` | `trc_d47179bd3391` |
| L3 | 16,25 | 3,71 | 19,97 | 1 | `provider_validated` | `trc_2c399c782cc3` |
| E1 | 15,92 | 6,08 | 22,00 | 1 | `provider_validated` (hỏi lại) | `trc_4f5a4e77fcd4` valid |
| E2 | 15,09 | 2,96 | 18,05 | 1 | `provider_validated` | `trc_a3a3efdc08d0` |
| E3 | 5,91 | 8,22 | 14,12 | 1 bị từ chối | rơi cục bộ, 3 lần | không nhận |

Provider/model mọi lần gọi thành công hoặc bị từ chối: `AI trong máy tương thích OpenAI` / `gemini-web`.

### Đáp án nhận

L1 — chưa đủ bằng chứng để nói LSU là gì và các bộ phận quang học chính [1]. Không bịa tên bộ phận.

L2 — đường kính BEAM lớn (100 µm) làm khoảng cách hẹp, ảnh bị chèn, đai đen [1]. Đường kính nghiêng hoặc trục quang bất thường cũng có thể gây đai đen [2].

L3 — đường kính đạt lý tưởng 60 µm khi các BEAM cách đều [2]. Đường kính lớn (100 µm) làm đai đen [2]. Có dòng `LIMITATIONS: incomplete_query_term_coverage`.

E1 — chưa đủ bằng chứng để chốt định nghĩa, nguyên nhân và hướng xử lý Beam径 NG trên Iris LSU [1]. Có dòng giới hạn phủ từ khóa. Không bịa nguyên nhân.

E2 — kẹp LD mirror bằng SIM để xem xu hướng đường kính Beam có đổi không [4].

E3 — không có đáp án lane 1 được nhận. Lần Gemini thứ hai nói lệch trục quang thì không chỉnh được đường kính BEAM, nhưng không có nhãn `[n]` nên bị hủy. Lần thứ ba nói phủ UV và dịch độ sâu JIG 1 mm, cũng không nhãn, không nhận. Bản cục bộ còn mảnh MOUNT LD BLOCK / vết sửa MIRROR LD / lệch µm, giống nhiễu lane cục bộ cũ, không tính là lane 1.

## 7. Đối chứng

| Câu | So với `llm-enable-do-nha` (lane 1) | So với `hodap-home` (cục bộ) |
| --- | --- | --- |
| L1 | Cùng hướng: chưa đủ bằng chứng, không bịa tên bộ phận | Kém hơn về độ đủ. Cục bộ nêu Lens, POLYGON, Lens F, LD mirror |
| L2 | Cùng quan hệ đai đen / đường kính / trục. Lượt này có thêm 100 µm | Khớp hướng, sạch hơn, hết XML |
| L3 | Đủ hơn lượt trước: có cả 60 µm và ngưỡng 100 µm | Khớp hướng, sạch hơn |
| E1 | Cùng mỏng: chưa đủ bằng chứng, không bịa | Cục bộ còn mảnh motor polygon / PWB APC và nhiễu |
| E2 | Khớp: kẹp SIM để xem xu hướng đường kính | Khớp câu hỏi, không kể unit test |
| E3 | Không đối được đáp án lane 1. Ý thô lần hai gần lượt trước (lệch trục quang) nhưng không qua cổng | Không nhận bản cục bộ làm parity lane 1 |

Parity 5 câu nhận được: cùng hướng với lane 1 trước, không bịa số mới ngoài mảnh. E3 chưa có đáp án lane 1 để đối.

## 8. Điều kiện không đạt

1. E3 không qua cổng nhãn sau 3 lần gọi Gemini (`provider_answer_missing_citations` + `provider_answer_uncited_material_claim`). Không nới cổng, không nhận bản cục bộ.
2. Lane 3 không sẵn sàng từ vé trước. Vé này không đo lại router.
3. UI app không được bật, để khỏi ghi index.

## 9. Trạng thái

`trang-thai.md` → `xong-cho-duyet`. Chờ Muse đối chứng. Không merge `main`.
