# Localization Glossary

Status: `ACTIVE`
Owner role: Project owner / UI reviewer
Last reviewed: 2026-07-25
Review cadence: Before new supported UI terminology or provider-facing copy

## Policy

Supported normal-user UI is Vietnamese-first. Essential technical constants may
remain English when they are immediately explained in Vietnamese. Raw tracebacks
and internal error details must not be shown to the owner.

| Term | Preferred Vietnamese | Usage note |
|---|---|---|
| Workspace Chat | Workspace Chat | Product name; explain as "Không gian hỏi đáp" in supporting copy when needed |
| source | nguồn | Use "nguồn dữ liệu" where clarity matters |
| evidence | bằng chứng | Distinguish from raw source |
| privacy label | nhãn bảo mật | Show meaning before cloud decision |
| local_only | chỉ dùng cục bộ | Never send externally |
| confidential | bảo mật | Never send externally |
| machine_only | cần xác nhận chủ sở hữu | Consent required for external route |
| cloud_safe | cho phép gửi AI cloud | Only after route eligibility |
| consent | xác nhận đồng ý | Bound to source set/destination/purpose |
| insufficient evidence | chưa đủ bằng chứng | Prefer over invented certainty |
| fallback | phương án dự phòng | Explain user effect, not internal mechanics |

## Review rule

New UI copy must retain these terms consistently and include accessible error,
empty/loading and offline states per UX acceptance record.
