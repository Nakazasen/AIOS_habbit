# Khả năng Phục hồi Định tuyến AI (AI Routing Resilience)

Status: `ACTIVE`
Owner role: Project owner / architecture reviewer
Last reviewed: 2026-08-15
Review cadence: Before a routing contract or resilience policy changes

## Ranh giới (Boundary)

AIOS sở hữu quyền riêng tư, sự đồng ý (consent), ranh giới nguồn/bằng chứng, kiểm thực câu trả lời và nâng cấp benchmark. Router được ủy quyền chỉ là một phụ thuộc định tuyến nhà cung cấp (provider-routing). Nó có thể chọn một tuyến truyền tải hợp lệ nhưng không thể tự cấp quyền gửi dữ liệu ra ngoài hoặc làm cho câu trả lời đủ điều kiện thăng cấp.

## Ba phạm vi lỗi (Three Failure Scopes)

| Phạm vi | Ví dụ kích hoạt | Hành vi cô lập |
|---|---|---|
| Ngắt mạch Provider (Provider circuit) | Hết thời gian (timeout), lỗi mạng, chuỗi lỗi 5xx | Đánh dấu provider bị suy giảm/mở mạch (degraded/open); các provider khỏe mạnh khác vẫn đủ điều kiện; một lần thăm dò bán mở (half-open) được phép sau khi hết hạn. |
| Thời gian hồi Key (Key cooldown) | Lỗi 429/hết hạn mức (quota) và header `Retry-After` | Chỉ đưa key bị ảnh hưởng (đã che giấu/masked) vào thời gian hồi; các key khác vẫn đủ điều kiện. Lỗi xác thực chỉ vô hiệu hóa riêng key đó. |
| Khóa mô hình (Model lockout) | Mô hình đã dừng/không hỗ trợ hoặc đầu ra của provider liên tục không hợp lệ | Chỉ khóa bộ `(provider, masked key, model)`; việc thay thế mô hình đã phê duyệt hoặc dùng mô hình/key/provider khác vẫn tiếp tục hoạt động. |

Trạng thái lưu trữ tuyệt đối không chứa API key thô, prompt, nội dung bằng chứng/nguồn, exception thô từ bên ngoài hoặc ID nguồn. JSON lưu trữ chỉ sử dụng ID đã che giấu (masked IDs), các lớp lỗi an toàn, dấu thời gian (timestamps) và số liệu độ tin cậy tổng hợp.

## Lựa chọn Tuyến (Route Selection)

Sau khi thỏa mãn tính hợp lệ của chính sách AIOS, môi trường production sắp xếp thứ tự các tuyến một cách tất định theo:

1. Tính khả dụng của Mạch ngắt / Key / Mô hình.
2. Mức độ gắn kết phiên tốt gần nhất hợp lệ (opaque, giới hạn theo task/ngôn ngữ/nhãn bảo mật và tồn tại ngắn hạn).
3. Độ phù hợp ngôn ngữ VI/JA/EN.
4. Độ tin cậy thành công quan sát được và độ trễ EWMA.
5. Thứ tự ưu tiên cấu hình rõ ràng và tiêu chí phân xử ID nhà cung cấp.

Bộ benchmark đánh giá mù có thẩm quyền giữ nguyên một nhóm provider được cấu hình theo thứ tự nhằm đảm bảo tính tái lập. Nó vẫn nhận khả năng phục hồi provider/key/model, telemetry thử nghiệm đã làm sạch và trạng thái router bền vững.

## Tính Toàn vẹn của Kết quả (Outcome Integrity)

`success`, `retry_later`, `infrastructure_invalid`, `policy_blocked`, và `local_renderer` là các trạng thái nội bộ phân biệt rõ ràng.

- Tổng hợp không hợp lệ về trích dẫn (citation) có thể chuyển sang tuyến render cục bộ đã kiểm chứng hiện có; nó được gắn nhãn `provider_validation_fallback`, không phải là sự cố toàn hệ thống của provider.
- Bất kỳ nhóm tổng hợp benchmark nào không khả dụng hoặc cạn kiệt đều là `INFRASTRUCTURE_INVALID`. Lượt chạy đó không thể thăng cấp và không được tính điểm như một lỗi giảm chất lượng RAG.
- Việc đóng giai đoạn trực tiếp (live phase) vẫn cần bộ benchmark 12/12 hoàn thành hợp lệ, không có dòng lỗi hạ tầng, kiểm tra tuyến ngôn ngữ đạt và vượt qua các gate so sánh độc lập với NotebookLM hiện có.

## Ma trận Kiểm chứng (Verification Matrix)

Sử dụng client giả lập (fake clients) và đồng hồ kiểm thử trước khi dùng thông tin xác thực thật:

- Provider 5xx → mạch mở (circuit opens), provider thay thế thành công.
- Mạch hết hạn → đúng một lần thăm dò bán mở (half-open probe); thành công sẽ đóng mạch lại.
- Key 429 kèm `Retry-After` → chỉ key đó tạm dừng trong khoảng thời gian upstream yêu cầu.
- Lỗi xác thực → chỉ key đó bị vô hiệu hóa.
- Mô hình không khả dụng → mô hình thay thế đã cấu hình hoặc một phương án khác vẫn đủ điều kiện.
- Đầu ra của provider không vượt qua kiểm thực → tín hiệu lỗi chỉ gán cho mô hình / chuyển sang render cục bộ đã xác thực.
- Phân loại truy vấn VI, JA, EN và hỗn hợp chỉ diễn ra ở mức truy vấn và plan mang trường ngôn ngữ canonical.
- Tất cả các tuyến không khả dụng → benchmark rơi vào trạng thái hạ tầng không hợp lệ (infra-invalid/non-promotable).

