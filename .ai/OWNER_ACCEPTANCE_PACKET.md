# Gói chấp nhận Owner AIOS P1

## Trạng thái hiện tại

- Repo: `[LOCAL_WORKSPACE]\AIOS_habbit`
- Branch: `main`
- Commit đã push: `e89c848`
- P1.0: **CHƯA MỞ**
- NotebookLM parity: **CHƯA CLAIM**
- Owner acceptance: **CHƯA HOÀN TẤT**

## Đã hoàn tất

- Checklist sẵn sàng P1 đã được ghi nhận.
- Owner workflow guide đã có lệnh CLI đọc-only.
- Local answer composer MVP đã có: tạo bản nháp local, deterministic, có citation, không gọi LLM/provider.
- Local reranker MVP đã có: heuristic local, deterministic, opt-in benchmark, không Vector DB/Graph DB.
- P1 opening plan chỉ là bản nháp, không mở P1.0.
- Full test suite đã PASS trước khi push.
- Push main lên GitHub đã hoàn tất tại `e89c848`.

## Chưa claim / chưa làm

- Chưa claim NotebookLM parity.
- Chưa mở P1.0.
- Chưa hoàn tất acceptance run bởi owner.
- Chưa thêm Vector DB.
- Chưa thêm Graph DB.
- Chưa tự động gọi provider/cloud/NotebookLM.

## Lệnh owner cần chạy

Chạy trong PowerShell tại thư mục repo:

```powershell
$env:PYTHONPATH='src'; py -3 -m aios_habit.cli owner-workflow --fake-data
```

Nếu dùng dữ liệu thật, chỉ dùng local-only và không paste dữ liệu công ty ra cloud:

```powershell
$env:PYTHONPATH='src'; py -3 -m aios_habit.cli owner-workflow
```

## Checklist acceptance

Owner tự kiểm tra các điểm sau:

- [ ] Tôi hiểu bước tiếp theo cần làm mà không cần đọc test Python.
- [ ] Tôi hiểu khi nào dữ liệu `local_only` không được xuất ra ngoài.
- [ ] Tôi nhìn được evidence/citation hỗ trợ câu trả lời.
- [ ] Tôi hiểu cảnh báo insufficient evidence và biết phải dừng khi thiếu bằng chứng.
- [ ] Tôi hiểu local answer composer chỉ tạo draft local, không gọi provider.
- [ ] Tôi thấy flow đủ rõ để dùng hằng ngày hoặc biết điểm nào còn quá thủ công.
- [ ] Tôi không paste dữ liệu công ty thật vào NotebookLM/cloud/provider.

## Mẫu báo cáo PASS/FAIL

```text
AIOS Owner Acceptance Run
Mode: fake-data / real-data-local-only
Date:
Commit tested: e89c848
Result: PASS / FAIL
Too manual: YES / NO
Most confusing step:
Privacy confidence: HIGH / MEDIUM / LOW
Evidence/citation confidence: HIGH / MEDIUM / LOW
Local answer composer useful: YES / NO
Notes:
```

## Cảnh báo quan trọng

Owner acceptance **không thể được hoàn tất bởi agent**. Chỉ human owner mới có thể đánh giá flow có đủ dùng hằng ngày hay chưa.

Không paste dữ liệu công ty thật, MOM docs, API key, file `.env`, `local_cases`, generated prompt pack, hoặc paste-back có dữ liệu nhạy cảm vào NotebookLM, cloud chat, provider, hoặc IDE bên ngoài.

## Next step

- Nếu owner acceptance **PASS**: chuẩn bị P1 opening review.
- Nếu owner acceptance **FAIL**: quay lại polish owner workflow, ưu tiên giảm thao tác thủ công và làm rõ privacy/evidence flow.

