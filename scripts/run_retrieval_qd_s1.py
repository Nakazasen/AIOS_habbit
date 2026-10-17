import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.workspace_chat_rag_v2_adapter import retrieve_workspace_chat_evidence

QUERIES = [
    ("Q0662", "Các mục tham khảo số 13–16 có nominal và dung sai thế nào?", "lsu"),
    ("Q0680", "Phương pháp tính độ lệch trái–phải của LENS CO trong file là gì?", "lsu"),
    ("Q0685", "Bracketの測定値を見るだけで斜め光NG原因を確定できますか。", "lsu"),
    ("Q0693", "NanoScan比较后，需要重新Correlation的是哪台Jig？", "lsu"),
    ("Q0703", "B距離が長くなる想定状態は何ですか。", "lsu"),
    ("Q0707", "SIM tape được dán ở đâu, dày bao nhiêu và trình tự thao tác thế nào?", "lsu"),
    ("ALIAS_OKNG_XLSX", "Theo tài liệu OKNGUNITのCO_BRACKETの倒れ_傾き確認結果.xlsx kết quả kiểm tra thế nào?", "lsu"),
    ("ALIAS_OKNG_NOEXT", "Theo tài liệu OKNGUNITのCO_BRACKETの倒れ_傾き確認結果 kết quả kiểm tra thế nào?", "lsu"),
    ("ALIAS_YBEAM_PPTX", "Theo tài liệu Y_BeamH_Camera_140_to_bất_thường.pptx nguyên nhân là gì?", "lsu"),
    ("ALIAS_YBEAM_NOEXT", "Theo tài liệu Y_BeamH_Camera_140_to_bất_thường nguyên nhân là gì?", "lsu"),
    ("ALIAS_TT11", "Trong tài liệu 生産履歴登録システム_変更確認チェックリスト_20260914.xlsx, server mới (máy chủ Linux) có tên máy là gì?", "mom"),
    ("ALIAS_TANABAN", "Theo tài liệu TANABAN_Master.xlsx thông tin là gì?", "mom"),
    ("ALIAS_CTU0330", "Theo tài liệu CTUマップ再検討20260330.xlsx layout thế nào?", "mom"),
]


def run_benchmark(output_file: str):
    results = {}
    for qid, qtext, domain in QUERIES:
        res = retrieve_workspace_chat_evidence(qtext, (), search_preference="auto", forced_domain=domain)
        items = res.get("evidence_items", [])
        top6 = []
        for i, it in enumerate(items[:6]):
            top6.append({
                "rank": i + 1,
                "title": it.get("title"),
                "score": it.get("score"),
                "chunk_id": it.get("chunk_id"),
                "doc_id": it.get("source_id") or it.get("document_id"),
            })
        top1_title = top6[0]["title"] if top6 else "NONE"
        results[qid] = {
            "qid": qid,
            "query": qtext,
            "domain": domain,
            "count": len(items),
            "top6": top6,
        }
        print(f"[{qid}] total={len(items)} | top1={top1_title}", flush=True)

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Results successfully saved to {out_path}", flush=True)


if __name__ == "__main__":
    out_name = sys.argv[1] if len(sys.argv) > 1 else "scripts/baseline_retrieval_s1.json"
    run_benchmark(out_name)
