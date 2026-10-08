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
