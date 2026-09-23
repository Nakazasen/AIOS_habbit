# Mô hình Dữ liệu: Dự phòng Tổng hợp Cục bộ có Trích dẫn

**Spec**: [spec.md](spec.md) mục R6 | **Kế hoạch**: [plan.md](plan.md) mục 9
**Ngày**: 2026-09-23

## Thực thể: LocalGroundedFallback

Lời mời dự phòng gắn với một lượt hỏi, sống trong bộ nhớ phiên, không ghi xuống đĩa cho tới khi người dùng bấm nút.

| Trường | Kiểu | Nguồn | Ràng buộc |
| --- | --- | --- | --- |
| `answer` | `str` | `ret_res["local_synthesis"]["answer"]` | Rỗng thì không mời |
| `citation_ids` | `tuple[str, ...]` | `ret_res["local_synthesis"]["citation_ids"]` | Nhãn dạng `[N]`, khớp `evidence_items[].citation_id` |
| `grounded` | `bool` | `ret_res["local_synthesis"]["grounded"]` | Phải `True` mới mời |
| `abstained` | `bool` | `ret_res["local_synthesis"]["abstained"]` | Phải `False` mới mời |
| `answer_mode` | `str` | `ret_res["local_synthesis"]["answer_mode"]` | `answer` hoặc `answer_with_limits` |
| `limitation_reasons` | `tuple[str, ...]` | `ret_res["local_synthesis"]["limitation_reasons"]` | Hiện cho người dùng khi có |
| `provider_used` | `bool` | luôn `False` | Không được đổi |

**Quy tắc hợp lệ để mời**: `answer` khác rỗng **và** `grounded is True` **và** `abstained is False`.

**Quy tắc hợp lệ để ghi**: như trên, kiểm lại tại thời điểm bấm nút vì dữ liệu có thể đã đổi.

## Thực thể: Cặp tin nhắn dự phòng (ghi vào kho cục bộ)

Khi người dùng bấm nút, hệ thống ghi đúng hai bản ghi `ChatMessage` và một `EvidenceTrace`.

| Bản ghi | Trường quan trọng | Giá trị |
| --- | --- | --- |
| Tin nhắn người dùng | `role` | `user` |
| | `content` | câu hỏi gốc |
| Tin nhắn trả lời | `role` | `assistant` |
| | `content` | đáp án trích xuất, kèm dòng `LIMITATIONS` nếu có |
| | `trace_id` | mã của dấu vết vừa dựng |
| Dấu vết bằng chứng | `status` (trong `metadata`) | `valid` khi có ít nhất một trích dẫn khớp |
| | `cited_count` | số trích dẫn đối chiếu được |
| | `nodes` | câu hỏi, câu trả lời, mỗi trích dẫn một nút, mỗi nguồn một nút |
| | `edges` | trả lời dẫn từ câu hỏi; trả lời trích dẫn; trích dẫn trích từ nguồn |

## Chuyển trạng thái

```text
[Lượt hỏi: truy xuất xong]
        |
        v
[local_synthesis] --(rỗng / abstained / không grounded)--> [chỉ lỗi cầu nối]
        |
        (dùng được)
        v
[Mời dự phòng]  --(người dùng không bấm)--> [không thay đổi gì]
        |
        (người dùng bấm)
        v
[Kiểm lại tính hợp lệ]
        |
        +--(không hợp lệ)--> [Từ chối, báo tiếng Việt, ghi 0 tin nhắn]
        |
        (hợp lệ)
        v
[Ghi 2 tin nhắn + 1 dấu vết] --> [Huy hiệu cập nhật, nút đồ thị hoạt động]
```

## Ràng buộc kiểm thử

- Dấu vết phải qua `build_evidence_trace_from_citations` — không tự dựng nút bằng tay.
- Chỉ ghi khi `answer` khác rỗng; nếu không thì `commit_local_grounded_answer` trả về lỗi tiếng Việt.
- Không trường nào của thực thể này được chảy ra nhật ký vận hành hoặc thông báo lỗi.
