# FIX 3 follow-up — B1–B5 sai: nội dung có trên máy nhưng thiếu trong index canary

Ngày: 2026-09-26. Hostname: `h410asrock`. Branch: `phieu-viec/rag-fix1`.
Index: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
(lúc đo 9.764.864 byte). Backup đối chiếu:
`library.sqlite.bak-20260926-0842`.

**Phân loại dứt khoát: (a) nội dung đáp án trực tiếp cho B1/B2/B3/B5 không có
trong corpus đã index.** Phần lớn tài liệu có đáp án còn trong
`materialized_sources/wsc-*.txt`, nhưng document_id tương ứng không có trong
index; đây là thiếu ở tầng collection/index (không phải evidence bị ranking bỏ
qua trong một chunk đã index). B4 có các mã cùng dạng trong index, nhưng ví dụ
tham chiếu chính xác và lời giải thích về độ dài/prefix không được tìm thấy.

Chỉ đọc: mọi truy vấn SQLite dùng URI `mode=ro`; grep chỉ đọc file
`materialized_sources`. Không sửa code hay ghi index. Thư mục index chứa 413
chunks, trong đó 340 có vector; index có 25 document_id. Thư mục materialized
có 108 file `wsc-*.txt`; 83 file không có path tương ứng trong index.

## 1. Đáp án tìm trong chunks

| Câu | Chuỗi/biến thể tìm trong `chunks.text` | Kết quả trong index | Document/file type/độ dài/vector |
| --- | --- | --- | --- |
| B1 | `11922`, `12860`, `12626` | Cả ba **0 chunks** | Không có candidate để đối chiếu vector. |
| B2 | `YY2-Z151`, `YY2-Z152` (kể cả không có `.exe`) | Cả hai **0 chunks** | `Z151` riêng lẻ có 3 chunks, `Z152` có 2, nhưng là địa chỉ ô/bảng kiểu `Z151=速度指定`, không phải tên executable. Trong đó Z151: 2 retrievable/có vector, Z152: 1 retrievable/có vector. Document `wsc-b8220b0d1cc36804b19e6dea`, type `txt`, các chunk 989/997 ký tự; một chunk chứa tọa độ không retrievable (5985 ký tự, không vector). |
| B3 | `nvarchar(4000)`, `nvarchar` | Cả hai **0 chunks** | `4000` riêng lẻ có 11 chunks (6 retrievable, 6 vector), nhưng các mẫu là mã lệnh hex như `0x4000`, không phải giới hạn XML. Không có chunk chứa ngữ cảnh đáp án. |
| B4 | `Y302YL93020100` | **0 chunks** | `Y3` riêng lẻ có 60 chunks (37 retrievable/có vector), do nhiễu tìm kiếm. Regex kiểm tra mã đúng 14 ký tự bắt đầu `Y3[0-9A-Z]{12}` thấy 38 chunks, 168 lần xuất hiện; các ví dụ là `Y302XDM0000029`, `Y302XDM0000032`, `Y302V900010101`… Không thấy mã ví dụ tham chiếu `Y302YL93020100` hay lời giải thích chiều dài/prefix. |
| B5 | `HOUSE_METHOD` | 1 chunk | `d5e8716abff78acee8f26cb6017666f36eb4c934d3c889e4e5325bdfd2838fc7`, document `wsc-90b85d5dd5c07833d2dfe481`, `txt`, 522 ký tự, retrievable=1, có vector BGE-M3 (1024d). Nội dung chỉ nói “格納方法_検査へ（HOUSE_METHODに書込み）”; không có giá trị `'0'`/`'1'` hay định nghĩa cất kho/đưa kiểm tra. |

5 mẫu đầu của các hit nhiễu `4000` (chunk_id rút gọn / document / type / chars):

- `06ebef3ac579` / `wsc-b8220b0d1cc36804b19e6dea` / txt / 5988 — mẫu có `O67=0x4000`, mã lệnh 非常停止.
- `1cbcbabfc731` / cùng document / txt / 978 — `O75=0x4000`, mã lệnh 非常停止.
- `2ec656172a39` / cùng document / txt / 982 — `I207=0x4000`, cũng là mã lệnh.
- `3df9963f2112` / cùng document / txt / 2023.
- `4acb7e81fec8` / cùng document / txt / 4386.

Không có `nvarchar` ở các hit này; `4000` là substring của mã hex, không phải đáp án B3.

## 2. Đối chiếu `materialized_sources`

| Câu | Kết quả trên file nguồn | Trạng thái document trong index | Kết luận tầng thiếu |
| --- | --- | --- | --- |
| B1 | Có đủ `...11922`, `...12860`, `...12626` trong hai file trùng nội dung: `wsc-6349bfab87ce7a5eb246e10f.txt`, `wsc-d33a710608155df3811cc1d6.txt`. | Cả hai document_id đều không nằm trong 25 document của index. | Có nguồn materialized, thiếu trong index; không phải chunking cắt mất trong index. |
| B2 | Có `YY2-Z151.exe` và `YY2-Z152.exe` (mỗi tên xuất hiện 2 lần) trong `wsc-5035a3d752d88cc0e20eb4c3.txt`. | Document_id không có trong index. | Có nguồn materialized, thiếu trong index. `Z151/Z152` trong index khác là toạ độ ô, không phải answer. |
| B3 | `nvarchar(4000)` xuất hiện 4 lần trong `wsc-c0cfb5bb4e58b93f4ac06c76.txt`; văn bản nguồn mô tả XML của `T_IF_PROD_RESULT` bị giới hạn 4000 ký tự. | Document_id không có trong index. | Có nguồn materialized, thiếu trong index. |
| B4 | Chuỗi ví dụ chính xác `Y302YL93020100` không có trong 108 file. Có các mã khác đúng 14 ký tự bắt đầu Y3, ví dụ `Y302XDM0000029`, trong nguồn khác. Không tìm được chuỗi/ghi chú `Spec Name`, `Compound Operation`, `14 character(s)` hay `14文字`. | Các mã ví dụ khác cùng dạng có mặt trong index (38 chunks/168 occurrences theo regex), nhưng chuỗi tham chiếu và lời giải thích độ dài/prefix không có. | Evidence cấu trúc chỉ một phần; ví dụ cụ thể không có cả trong source và index. Không đủ cơ sở kết luận B4 hoàn toàn là ranking miss. |
| B5 | Định nghĩa đầy đủ `'0':倉庫へ格納` / `'1':検査` có trong `wsc-ff8304af86028eaa474a1706.txt`; một số file materialized khác có tên trường nhưng không có định nghĩa. | File có định nghĩa không có document_id trong index. Index chỉ có hit `HOUSE_METHOD` nêu trên, thiếu hai giá trị. | Có nguồn materialized, thiếu phần answer trong index. |

Các source file B1/B2/B3/B5 có câu trả lời không được giữ nguyên index-retrievable dưới document_id của file đó. Trên máy có 108 materialized files nhưng chỉ 25 document paths trong index; số này là dữ liệu quan sát trên `h410asrock`, không áp sang máy công ty. Điều tra này xác định rõ **nội dung có ở thư mục materialized nhưng chưa được đưa vào collection**, không khẳng định nguyên nhân vận hành khiến 83 file chưa được index.

## 3. Nhiễu XML

- Chunks có `xmlns`: **33** (32 `txt`, 1 `document_summary`).
- Chunks có `<p:sld`: **23**.
- Ba mẫu nguyên văn (172, 367, 374 ký tự):

```
ns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"> 3 Embedded media/images: 36
```

```
ng thường biểu thứ tự sản xuất Mở file excel “ 生産順位表 ( 本番サーバ )Ver_06.xlsm” ở trong link: \\fstvn01\Data\10_Production Control( 生産管理部 )\10. 生産管理課ー QLSX\05.DOCCUMENT\1.Nghiệp vụ phòng QLSX & đào tạo cơ bản\APS File này do bên IT cung cấp và tạo Macro, nếu có vấn đề gì thì liên Speaker notes: <p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xml
```

```
＝ 製品やサービスが開発されて市場に登場してから 衰退するまでの一連の流れ 製品ライフサイクルとは、ある製品やサービスが開発され市場に導入されてから、成長・成熟・衰退という段階を経て、最終的には市場から撤退するまでの一連の過程を表す言葉 <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"> マスターデータとは マスターデータ とは、 会社の業務にとって基盤となる
```

Count/query mẫu này đọc text trong index ở `mode=ro`; không ghi gì.

## 4. Kết luận

Theo tiêu chí phân loại của phiếu: **(a) current index corpus thiếu các chunk đáp án trực tiếp**, không phải chỉ retrieval bỏ sót trong các chunk đó.

- B1/B2/B3/B5: answer có trong materialized source nhưng document tương ứng không được index; chunk trả lời không tồn tại trong collection hiện tại. Do đó rerank/retrieval trên index hiện tại không thể đưa đúng chunk lên.
- B4: mã mẫu tham chiếu không có ở source/index; mã khác 14 ký tự bắt đầu `Y3` hiện diện trong index nhưng không kèm giải thích nghiệp vụ. B4 có một phần dữ liệu cùng dạng, vì vậy không kết luận ranking là nguyên nhân chính cho các mã tham chiếu cụ thể.
- Lần chạy FIX3 trước không abstain nhưng trả kết quả chung chung; B1–B5 đều không có đáp án tham chiếu trong output. Thiếu source chunks tại index đã đủ giải thích sai B1/B2/B3/B5. Nhiễu XML là vấn đề bổ sung, rõ rệt ở B3 output, nhưng không phải lý do duy nhất khiến đáp án sai.

## 5. Tùy chọn ONNX fp32 — đã thử, không có kết quả câu hỏi

- `models/bge-m3-onnx-fp32/` có trên máy, gồm `model.onnx` (553 KiB) và
  `model.onnx_data` (~2,2 GiB), nên không phải trường hợp thiếu thư mục.
- Đã thử B1–B5 với `BGE_BACKEND=onnx`, hai flag summary giữ `1`, index config
  `index_read_only=True`/`ensure_embeddings_on_open=False`, 25 specs đã index.
- Worker không khởi tạo: `bge_worker_init_timeout` sau 300 giây; không có event
  init hay câu trả lời. Dừng bước ONNX theo điều kiện phiếu, không tự sửa hoặc
  retry model. Vì vậy không có latency ONNX/so sánh answer.
- PyTorch lần 3 đối chiếu: B1 101,61 s / B2 2,25 s / B3 3,64 s /
  B4 2,19 s / B5 1,81 s.

## 6. Phạm vi và tiếp theo

- Không sửa code; không chạy backfill/apply; không ghi vào index. Các lần chạy
  ONNX/PyTorch query đã dùng config read-only. Scratch runners và raw logs nằm
  trong ignored `scratch/` hoặc `C:/Users/Admin/AppData/Local/Temp/`, không
  thuộc commit.
- Vòng này không ingest 83 materialized files, không sửa extractor/XML, không
  điều tra ranking sâu hơn; ghi nhận phân loại từ dữ liệu hiện có.
- Commit riêng file báo cáo và push lên `phieu-viec/rag-fix1`; không merge
  `main`. Sau đó dừng chờ duyệt.
