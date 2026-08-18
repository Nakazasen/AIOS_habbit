# Hướng dẫn Vận hành & Kích hoạt / Rollback 1-Bước: Adaptive Reranking UX (003)

Tài liệu này hướng dẫn chi tiết quy trình kích hoạt (Activation), kiểm tra tiền kiểm (Pre-flight Audit) và hoàn nguyên khẩn cấp 1-bước (Rollback) cho tính năng Adaptive Reranking.

---

## 1. Nguyên tắc An toàn Tuyệt đối

- **Mặc định OFF**: `adaptive_enabled=false` và `canary_enabled=false` ở mọi môi trường trừ khi có kích hoạt tường minh.
- **Fail-Closed**: Mọi sự cố checksum, thiếu model hoặc timeout đều hạ cấp an toàn hoặc từ chối thực thi thay vì lộ lỗi kỹ thuật ra người dùng.
- **Quyền của Người dùng**: Người dùng chọn "Tìm kỹ hơn" luôn được ưu tiên, nhưng không bao giờ hiển thị "Đã tìm kỹ" nếu reranker không thực sự chạy thành công.

---

## 2. Kiểm tra Tiền kiểm (Pre-flight Audit)

Trước khi kích hoạt, chạy lệnh audit chuẩn:

```bash
# Kiểm tra manifest và artifact reranker
py -3 -m aios_habit.workspace_chat_rag_v2_deployment --manifest config/workspace_chat_rag_v2.local.json --check-adaptive --json
```

**Tiêu chí PASS:**
- `status`: `"PASS"`
- `checks.model_path_exists`: `true`
- `checks.profile_match`: `true`
- `checks.reranker_configured`: `true`
- `checks.reranker_revision_match`: `true`

---

## 3. Quy trình Kích hoạt 1-Bước (One-Step Activation)

### Cách A: Qua Manifest Deployment (Khuyến nghị)
Chỉnh sửa file manifest `config/workspace_chat_rag_v2.local.json`:
```json
{
  "schema_version": 3,
  "activation_state": "activated",
  "requested_profile": "bge_m3_hybrid",
  "runtime": {
    "root": "D:/Sandbox/AIOS_habbit/data/runtime"
  },
  "model": {
    "path": "D:/Sandbox/AIOS_habbit/models/bge-m3",
    "revision": "5617a9f61b028005a4858fdac845db406aefb181",
    "checksum": "sha256:f8faedab99c4c901e5c2f311ea3f32786b3395b5cbb0c10a60c2b83970d64405",
    "device": "cpu"
  },
  "reranker": {
    "path": "D:/Sandbox/AIOS_habbit/models/bge-reranker-v2-m3",
    "revision": "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e",
    "checksum": "sha256:66ee82666f78ee4c16efa73de43586a00b1338bf9d96cb5cf891b7b705c873c7",
    "device": "cpu"
  },
  "adaptive": {
    "enabled": true,
    "policy_version": "adaptive-reranking-v1",
    "deep_timeout_ms": 5000
  },
  "policy": {
    "fail_closed": true,
    "lexical_fallback_enabled": false,
    "semantic_progressive": false
  }
}
```

### Cách B: Qua Biến Môi Trường (Cho CI / Sandbox Testing)
```bash
$env:AIOS_WORKSPACE_RAG_V2_MANIFEST = "D:\Sandbox\AIOS_habbit\config\workspace_chat_rag_v2.local.json"
```

---

## 4. Quy trình Hoàn nguyên Khẩn cấp 1-Bước (1-Step Instant Rollback)

Khi phát hiện bất kỳ sự cố nào (RAM vượt ngưỡng, độ trễ p95 tăng cao, hoặc sự cố subprocess):

### Cách 1: Tắt Adaptive Reranking ngay lập tức (Giữ Hybrid BGE-M3)
Trong `config/workspace_chat_rag_v2.local.json`, đổi:
```json
"adaptive": {
  "enabled": false
}
```
*Tác dụng*: Toàn bộ truy vấn lập tức quay về luồng Hybrid nhanh, không gọi subprocess reranker.

### Cách 2: Tắt toàn bộ RAG v2 Canary (Quay về Lexical / Base RAG v1)
Trong `config/workspace_chat_rag_v2.local.json`, đổi:
```json
"activation_state": "rolled_back"
```
*Tác dụng*: Workspace Chat lập tức bypass toàn bộ Canary RAG v2, quay về pipeline nguyên bản ban đầu an toàn 100%.

---

## 5. Xử lý Sự cố Tự phục hồi & Circuit Breaker

- **Circuit Breaker**: Tự động ngắt kết nối reranker sau 3 lần lỗi liên tiếp (`circuit_breaker_open`), hạ cấp trong suốt về Hybrid để bảo vệ RAM.
- **Tự làm mát (Cooldown)**: Sau 30 giây cooldown, hệ thống tự động thử nghiệm lại reranker.
- **Telemetry**: Toàn bộ lỗi được gắn nhãn mã an toàn (`reranker_backend_timeout`, `reranker_backend_failed`, `reranker_backend_unavailable`, `circuit_breaker_open`) mà không làm lộ câu hỏi hay dữ liệu nhạy cảm của người dùng.
