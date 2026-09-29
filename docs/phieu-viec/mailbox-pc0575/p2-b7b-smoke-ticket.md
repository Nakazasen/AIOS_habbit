# Vé P2-B7b — Hoàn tất smoke test (sparse head)

## Bối cảnh
- Vector check ĐẠT tuyệt đối: 5/5 chunk cosine = 1.0 (`VECTOR_EQUIVALENT`).
  Model PC0575 cho vector giống hệt vector đã seal trong index.
- Smoke B7b kẹt ở `onnx_int8_sparse_head_missing`: profile `bge_m3_hybrid`
  đòi sparse head, nhưng thư mục onnx thiếu `sparse_linear.npy`.

## Việc cần làm (trên PC0575, repo `D:\Sandbox\AIOS_habbit`)

### 1. Lấy file sparse head
```powershell
cd D:\Sandbox\agent-mailbox
git pull origin main
```
Verify SHA-256 sau pull:
- `pc0575\sparse_head\sparse_linear.npy` →
  `ecf456ee92e5f4ce04fdcaa56b44f1ef89d21a4ec5a32d21e17534f61819aa4c`
- `pc0575\sparse_head\sparse_linear_bias.npy` →
  `ac9c745621f4013d231ecfeb94e271a1a4f9487b4d60249ba3c1992ecd99e442`

SHA lệch → DỪNG, báo lại. Không tự convert `.pt` (máy không có torch).

### 2. Đặt file vào thư mục model
```powershell
Copy-Item "D:\Sandbox\agent-mailbox\pc0575\sparse_head\sparse_linear.npy" `
  "D:\Sandbox\AIOS_habbit\local_runs\retrieval_models\bge-m3-5617a9f\onnx\"
Copy-Item "D:\Sandbox\agent-mailbox\pc0575\sparse_head\sparse_linear_bias.npy" `
  "D:\Sandbox\AIOS_habbit\local_runs\retrieval_models\bge-m3-5617a9f\onnx\"
```

### 3. Set env + TÍNH LẠI checksum (bắt buộc — cây model đã đổi vì thêm file)
```powershell
cd D:\Sandbox\AIOS_habbit
$env:AIOS_BGE_ONNX_MODEL_PATH = "D:\Sandbox\AIOS_habbit\local_runs\retrieval_models\bge-m3-5617a9f\onnx"
$env:AIOS_RAG_INDEX_PATH = "D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite"
$env:AIOS_BGE_ONNX_MODEL_CHECKSUM = (.\.venv\Scripts\python.exe -B -c "import sys; sys.path.insert(0,'src'); from aios_habit.rag_v2.retrieval_backends import sha256_model_tree; print(sha256_model_tree(r'D:\Sandbox\AIOS_habbit\local_runs\retrieval_models\bge-m3-5617a9f\onnx'))")
```

### 4. Chạy smoke
```powershell
.\.venv\Scripts\python.exe -B scratch\p2_b7_smoke.py
```
ĐẠT khi exit 0 và có `scratch\p2_b7_report.json`.

## Quy tắc
- KHÔNG sửa code để "cho qua" cổng kiểm tra.
- KHÔNG ghi vào index production (smoke chỉ đọc).
- Lỗi → dừng, ghi JSON/báo cáo nguyên văn vào
  `docs/phieu-viec/ket-qua/`, cập nhật `trang-thai.md` trong mailbox này,
  đặt trạng thái `cho-muse`.

## Báo cáo
- File báo cáo: `docs/phieu-viec/ket-qua/p2_b7b_smoke_2026-09-29.md`
  (gồm: exit code, JSON report nguyên văn, checksum mới, SHA index).
- Cập nhật `trang-thai.md`: B7b `dang-lam` → `xong` (hoặc `cho-muse` nếu lỗi).
