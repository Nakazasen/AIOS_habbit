# Hợp đồng vòng phỏng vấn và xuất bản tri thức

## 1. Mục đích

Hợp đồng này khóa hành vi giữa coverage, chat, claim, artifact và publication. Tên Python/HTTP cụ thể có thể thay đổi; invariant không được thay đổi nếu chưa cập nhật ADR/spec.

## 2. Lệnh nghiệp vụ

### `propose_coverage_run`

**Đầu vào**: `collection_id`, `scope`, `source_inventory_digest`, `question_set`, actor.  
**Đầu ra**: `coverage_id`, metrics, gap candidates và receipt.  
**Từ chối**: collection/scope không hợp lệ, inventory đổi giữa lượt, câu hỏi không có expected evidence.

### `review_gap_candidate`

**Đầu vào**: `gap_id`, exact digest, quyết định `accept|merge|defer|reject`, lý do, actor.  
**Đầu ra**: trạng thái mới append-only.  
**Từ chối**: actor thiếu scope, digest stale hoặc gap không còn ở trạng thái reviewable.

### `create_interview_plan`

**Đầu vào**: gap đã accepted, required scope, expert candidates, budget, completion rubric.  
**Đầu ra**: plan draft; AI có thể đề xuất câu hỏi nhưng không tự phê duyệt plan.  
**Từ chối**: gap thiếu evidence, expert không có verified profile hoặc budget không hữu hạn.

### `start_or_resume_interview`

**Đầu vào**: `plan_id`, principal context, session ID tùy chọn, idempotency key.  
**Đầu ra**: session/checkpoint và câu hỏi kế tiếp.  
**Từ chối**: principal không ánh xạ, scope hết hạn, plan chưa duyệt, session bind người khác.

### `submit_interview_answer`

**Đầu vào**: session/checkpoint, turn ID, answer hoặc `unknown|uncertain|skip|pause|stop`, confidence, idempotency key.  
**Đầu ra**: turn receipt và một trong `ask_followup|request_confirmation|complete|pause|escalate`.  
**Từ chối**: checkpoint cũ, answer lặp khác payload, session không active hoặc principal đổi.

### `propose_next_question`

Model chỉ được trả schema:

```json
{
  "action": "ask_followup",
  "reason": "missing_threshold",
  "question": "Ngưỡng nào khiến anh/chị chuyển từ theo dõi sang dừng máy?",
  "trigger_refs": ["TURN-003"],
  "expected_evidence": ["threshold", "unit", "exception"],
  "confidence": 0.73
}
```

`action`: `ask_followup|request_confirmation|complete|escalate`.  
`reason`: `missing_condition|missing_threshold|missing_exception|missing_example|missing_counterexample|uncertain|missing_source|contradiction|rubric_complete`.  

Service phải từ chối schema sai, câu hỏi ngoài scope, trigger không tồn tại, budget hết hoặc lặp semantic vượt ngưỡng. Model không trực tiếp ghi turn.

### `extract_claim_candidates`

**Đầu vào**: các turn/transcript segment đã khóa digest.  
**Đầu ra**: claim candidate nguyên tử với exact source refs, scope, condition, uncertainty và conflict links.  
**Từ chối**: source chưa tồn tại, transcript critical token chưa xác nhận hoặc model tạo statement không có support.

### `build_artifact_candidate`

**Đầu vào**: confirmed/candidate claims được chọn, template version, artifact type.  
**Đầu ra**: versioned Markdown/JSON + claim map + diff.  
**Từ chối**: dùng claim rejected/revoked; claim conflicted chỉ được xuất hiện trong phần “cần quyết định”, không phải hướng dẫn chính thức.

### `decide_artifact`

**Đầu vào**: exact artifact digest, `approve|reject|request_change|revoke`, rationale, authenticated actor.  
**Đầu ra**: ApprovalDecision append-only.  
**Từ chối**: actor/scope không đúng, self-approval bị policy cấm, digest/version stale hoặc thiếu approval bắt buộc.

### `publish_artifact`

**Đầu vào**: sealed PublicationPackage và actor có `publication.publish` trên collection.  
**Thứ tự bắt buộc**:

1. Xác minh approval + digest + artifact status.
2. Tạo/kiểm tra backup collection.
3. Lấy writer lease.
4. Nạp artifact qua pipeline nguồn chuẩn.
5. Chạy SQLite `quick_check` và retrieval acceptance.
6. Ghi receipt rồi mới chuyển `published`.

Lỗi ở bước 3–5 không được ghi `published`; giữ hoặc khôi phục bản usable trước đó.

### `revoke_or_supersede_publication`

**Đầu vào**: publication ID, exact digest, lý do, replacement tùy chọn, actor có quyền.  
**Đầu ra**: receipt loại khỏi retrieval hiện hành và liên kết lịch sử.  
**Từ chối**: quyền không hợp lệ, replacement chưa duyệt hoặc digest stale.

## 3. Invariant bắt buộc

- Không model output nào tự trở thành quyết định quyền hoặc phê duyệt.
- Không turn nào được ghi hai lần với cùng idempotency key.
- Không question nào thiếu gap/turn/claim trigger hợp lệ.
- Không claim xuất bản nào thiếu source refs.
- Không critical token từ audio nào được xuất bản khi chưa human-confirmed.
- Không candidate/conflicted/revoked nào đi vào retrieval thường.
- Không ghi trực tiếp SQL từ model vào `library.sqlite`.
- Không sửa/xóa event audit cũ; correction tạo version/event mới.

## 4. Hành vi khi lỗi model

- Timeout: lưu checkpoint, hiển thị lỗi tiếng Việt và cho thử lại; không nhân đôi turn.
- Schema sai: một lần repair có giới hạn; sau đó `blocked_model_output`.
- Nội dung ngoài scope/không có nguồn: từ chối proposal và không hiển thị như kết luận.
- Provider không được phép nhận dữ liệu: dùng local route hoặc chặn, không âm thầm đổi route.
