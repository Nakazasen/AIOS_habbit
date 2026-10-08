# VÉ: UI-COLDSTART-WORKER-HOME (câu hỏi đầu phiên lạnh phải ra đáp án — xử lý đường nạp worker BGE)

- Mã vé: `UI-COLDSTART-WORKER-HOME`
- Role gợi ý: DEFAULT
- Máy: nhà h410asrock (agy — thợ chính, **CPU-only** theo luật đồng bộ 2 máy)
- Báo cáo: `docs/phieu-viec/ket-qua/ui-coldstart-worker-home.md`
- Căn cứ: nghiệm thu vòng 3 (phiên `CONV-Q3-ED3317`, bằng chứng đã được điều phối đối chiếu khớp) cho kết quả sản phẩm 0/3 câu có đáp án: cả 3 câu kết thúc bằng thông báo `worker_warm_auto_retry` sau 371,75s / 154,62s / 481,14s. Chẩn đoán của vòng 3 đã chỉ rõ cơ chế: tiến trình con BGE qua named-pipe mất 20–40 giây nạp lại mô hình, vượt ngưỡng chờ hoặc sập (`bge_worker_query_timeout` / `bge_subprocess_worker_crashed`) → truy hồi trả `quality_search_unavailable` → app tự làm nóng + thử lại 1 lần → vẫn không xong → hiển thị thông báo "bấm Hỏi lại". Đây là lỗi chặn người dùng thật ở mức 100% trong phiên lạnh và là hạng mục trải nghiệm trung tâm theo chỉ thị đồng bộ 2 máy của user (áp dụng cho cả PC0575 ở cùng commit).

## Việc phải làm

1. **Chẩn đoán đường worker bằng log thật:** vì sao worker được gọi là "persistent" vẫn phải nạp lại mô hình ở lượt hỏi đầu (và có phải mỗi lượt hỏi đều nạp lại không); ngưỡng timeout hiện tại của đường truy hồi là bao nhiêu; worker sập vì nguyên nhân gì (đọc log worker, ghi nguyên văn dòng lỗi). Nộp bảng số đo: thời gian nạp lạnh thật của worker trên CPU (đo 3 lần), thời gian một lượt truy hồi hoàn chỉnh khi worker đã nóng.
2. **Sửa theo 3 hướng bắt buộc:**
   - (a) **Làm nóng trước:** worker được khởi động/nạp mô hình ngay từ lúc app khởi động hoặc lúc mở sổ (song song, không chặn giao diện), có trạng thái hiển thị thật cho người dùng ("đang nạp bộ đọc…") thay vì để câu hỏi đầu tiên gánh toàn bộ thời gian nạp.
   - (b) **Lượt hỏi không kết thúc bằng "bấm Hỏi lại":** khi worker chưa sẵn sàng, lượt hỏi tự chờ trong cùng lượt (hiển thị trạng thái đang chờ nạp) rồi chạy tiếp tới khi có đáp án hoặc chạm trần chờ được công bố rõ; thông báo làm-nóng chỉ là trạng thái tạm trong lúc chờ, không bao giờ là kết quả cuối cùng của một câu hỏi khi worker thực tế nạp xong được.
   - (c) **Ngưỡng chờ khớp thực tế:** timeout của đường truy hồi/worker phải lớn hơn thời gian nạp lạnh đo thật cộng biên an toàn, và/hoặc worker phải sống thật giữa các lượt hỏi (không nạp lại mô hình mỗi lượt). Chọn phương án theo số đo ở mục 1, ghi rõ lý do.
3. **Giải trình 2 test fail trên máy điều phối:** tại commit nộp vòng 3, điều phối tự chạy trên VM thấy 2 test fail lặp lại trong `tests/test_workspace_chat_ai_answer.py` (`test_generate_answer_via_router_integration_mocked_outcome`, `test_workspace_chat_router_creation_enables_network_and_v051_recovery`) — chạy lại trên máy nhà, xác định do khác biệt môi trường hay do thay đổi `truncated=False` của vòng 3 gây ra; nếu do thay đổi thì sửa trong vé này. Đồng thời đính chính số đếm test của file adapter chính (điều phối đếm 85, báo cáo vòng 3 ghi 87) — từ nay số test trong báo cáo phải khớp tuyệt đối với số đếm của file.
4. **Nghiệm thu dùng thật — phiên lạnh tuyệt đối:** tắt hẳn app và worker → khởi động lại app (CPU-only) → mở sổ → hỏi liên tiếp 3 câu Q0699, Q0718, Q0709. Cổng đạt: **cả 3 câu ra đáp án thật** (không câu nào kết thúc bằng thông báo làm-nóng/thử-lại), ghi thời gian từng câu, nộp ảnh (chứa đáp án trong khung) + JSON thô gắn mã phiên mới theo đúng chuẩn bằng chứng của vòng 3, băm chỉ mục trước/sau khớp tuyệt đối, ghi commit HEAD lúc đo.

## Rào cứng

- CPU-only cho mọi lần đo (GPU chỉ dành cho embedding/index). Không ghi chỉ mục. Không merge `main`. Tương thích Python 3.11.
- Không sửa đè/chạm vào bất kỳ file bằng chứng nào của các vòng trước; mọi file của vé này đều mới, gắn mã phiên riêng.
- Mốc tiến độ tối thiểu 15 phút/lần + checkpoint/resume. Kỷ luật số liệu tuyệt đối: mọi con số phải đối chiếu được với file đính kèm.

## MỤC 0 BẮT BUỘC (điều phối bổ sung 20:55 08/10 sau khi user yêu cầu tra lịch sử): ĐỐI CHIẾU 3 ĐỢT XỬ LÝ TRƯỚC — CẤM LÀM LẠI TỪ ĐẦU

Vấn đề nạp worker đã qua 3 đợt xử lý có verdict, thợ PHẢI đọc trước khi chẩn đoán/sửa (điều phối đã tự kiểm: các hằng số của đợt 3 vẫn còn nguyên trong code hiện tại):
1. **02/10 tại PC0575 (vé SPEED-COLDSTART-PC0575):** chẩn đoán gốc — thời gian nạp worker thật ~181 giây vượt cửa sổ chờ 120 giây của app (hết giờ thì sinh worker mới, bỏ mặc worker đang nạp); làm nóng nền trỏ SAI collection (chỉ mục legacy thay vì `tri_thuc`). Đã sửa: làm nóng trỏ đúng collection production chỉ-đọc; đồng bộ cửa sổ chờ 300 giây; giữ worker đang nạp cho lần gọi sau; worker sống lâu qua named pipe. Báo cáo: `docs/phieu-viec/ket-qua/speed-coldstart-pc0575.md`.
2. **06/10:** verdict ĐẠT trong phạm vi khởi động lại app khi worker còn sống (18,6–34 giây); ghi rõ kịch bản worker lạnh hoàn toàn vẫn 130–209 giây, CHƯA đạt và bị để treo từ đó.
3. **07/10 tại máy nhà (vé BGE-WORKER-DIAG-HOME → BGE-WORKER-FIX-HOME, verdict ĐẠT 23:27):** đo phân rã nạp 246–302 giây trên CPU máy nhà; commit `c338a87` nới trần nạp 300→420 giây và trần chờ sinh worker 120→360 giây, thêm cơ chế tự phục hồi (xoá cờ lỗi để thử lại). Nghiệm thu dùng thật ĐẠT: lượt 1 câu C7620 khởi động worker thành công và trả lời đúng 70dot, lượt 2 worker đã sống nên chỉ 15,25 giây. Báo cáo: `docs/phieu-viec/ket-qua/bge-worker-diag-home.md` và `bge-worker-fix-home.md`.

**Câu hỏi vé này phải trả lời TRƯỚC khi sửa (bằng log worker của phiên vòng 3 và đối chiếu commit):** đường hỏi đã ĐẠT ngày 07/10 vì sao hỏng ngày 08/10? Hai nghi vấn chính phải phân biệt rõ: (i) worker SẬP tiến trình (`bge_subprocess_worker_crashed`) — loại lỗi khác hẳn "nạp chậm", trần chờ dài bao nhiêu cũng không cứu được; (ii) các thay đổi sau 07/10 (bộ lọc khối tri thức của chặng 2 tại PC0575 commit `ce6212c`, các sửa tương thích ở chuỗi vé chất lượng vòng 1–3) đã đổi đường đi của lượt hỏi. Kết luận chẩn đoán phải chỉ rõ: chết vì sập hay vì hết giờ, ở commit/điều kiện nào, và phần nào của 3 đợt trước vẫn còn hiệu lực (không được sửa lại những gì đang đúng).
