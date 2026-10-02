# Vé KNOWLEDGE-DIGEST-HOME — báo cáo máy nhà

- Ngày: 2026-10-03, 01:47–02:26 +07.
- Nhánh: `phieu-viec/rag-fix1`. Không merge `main`, không force-push.
- Lane: máy nhà, cầu nối Gemini Web `127.0.0.1:8585`, model `gemini-web`. Không dùng Nakazasen Router.
- Phạm vi ghi: artifact ở `C:/tmp/knowledge-digest-home/` (checkpoint, log, raw). Không commit sổ tay. Không ghi index production. Không đụng ổ D.

## 1. Cổng gate

- Watcher tự mở OMP `LAUNCH 1/4` lúc `2026-10-03T01:45:07` cho vé `KNOWLEDGE-DIGEST-HOME`.
- Điều kiện mở đã tới: `knowledge_digest.py` và `digest_qa.py` có trên nhánh. Không đặt `cho-muse`. Không quay no-op.

## 2. Đếm document (bước 0)

Đếm trực tiếp trên index chỉ đọc, không hardcode:

| Mục | Số |
|---|---|
| Đường index | `C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` |
| Kích thước | 2.942.201.856 byte |
| SHA-256 trước | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` |
| Document phân biệt | 889 |
| Chunk | 149.800 |
| Chunk `retrievable=1` | 121.331 |

Bảng thật là `chunks` (`document_id`, `source_name`, `source_path`, `text`, `chunk_id`). Hàm `run_digest` của mã sản phẩm đọc `chunk_metadata`, bảng này không có trên index nhà. Không sửa mã sản phẩm. Runner ngoài Git `C:/tmp/knowledge-digest-home/run_digest_home.py` đọc bảng `chunks` rồi gọi `summarize_document`, `render_handbook`, `write_manifest`. Prompt tóm tắt vẫn là `SUMMARY_PROMPT_TEMPLATE` trong mã sản phẩm.

## 3. Batch tóm tắt

- Cầu nối lúc đầu: `direct_ready`. Thử 1 tài liệu: JSON đúng schema, 7,2 giây.
- Batch resume từ checkpoint, mỗi tài liệu một lượt, ghi checkpoint sau mỗi tài liệu thành công.
- Kết quả dừng: **92/889** mục, cả 92 đều parse được JSON (`raw` rỗng), 0 chủ đề trống, 26/92 bị rút nguồn ở 12.000 ký tự (đúng `MAX_DOC_CHARS`).
- Thời điểm checkpoint: `2026-10-03 02:21:40` +07.
- Log: 92 dòng `ok`, 34 dòng `fail`. Một lỗi sớm do sidecar bị cắt hạn 300 giây rồi bật lại. Từ `02:03` trở đi Gemini Web trả HTTP 405; sidecar đổi thành 502. Làm mới BL thất bại (HTTP 302 vòng lặp). Vài lượt vẫn lọt (ví dụ vị trí 101, 120), phần lớn fail sau 3 lần thử (~37 giây/lần).
- Đã dừng batch lúc ~02:26 để không quay vòng lỗi. Không bịa số mục còn thiếu.

Sổ tay Markdown và manifest **chưa xuất** vì chưa đủ 889 mục. Tiêu chí phủ 100% chưa đạt.

## 4. Probe hỏi đáp và so sánh RAG

Chưa chạy. Sổ tay chưa đủ để nạp context, và cầu nối đang 405 nên không đo thời gian từng câu. Không có số liệu rubric. Không nói lane sổ tay nhanh hơn hay bao quát hơn.

## 5. Index production chỉ đọc

| File | SHA trước | SHA sau | Khớp |
|---|---|---|---|
| `library.sqlite` | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA, cùng 2.942.201.856 byte | có |

Không nhập sổ tay vào kho. Không gắn nhãn `kiến thức đã được đào tạo bổ sung`. Không có bản thảo trong luồng trả lời chính.

## 6. Kết luận và cách chạy tiếp

Phần đếm và rào chỉ đọc đã xong. Phần tóm tắt **chưa xong** (92/889). Tiêu chí ĐẠT của vé **chưa đạt**. Không tự đánh ĐẠT.

Cách chạy tiếp khi cầu nối Gemini Web hết 405:

1. Kiểm `GET http://127.0.0.1:8585/health` = `direct_ready` và một lượt tóm tắt thử trả JSON.
2. Chạy lại `C:/tmp/knowledge-digest-home/run_digest_home.py`. Checkpoint giữ 92 mục, không làm lại từ đầu.
3. Khi `done=889`, script xuất `so_tay_tri_thuc.md` + manifest SHA-256.
4. Chạy probe 12 câu sổ tay và cùng bộ câu qua lane RAG chỉ đọc, chấm rubric từng câu, đo SHA index lần nữa.

Muse review file này. Cầu nối cần hết HTTP 405 trước khi resume.
