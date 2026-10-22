import json
import shutil
from pathlib import Path

loc_manifest = Path(r"D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\step1_realuse_acceptance_evidence.json")
desk_manifest = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\step1_realuse_acceptance_evidence.json")

with open(loc_manifest, "r", encoding="utf-8") as f:
    ev = json.load(f)

# Load latest assistant message per conversation
conv_messages = {}
with open(r"D:\Sandbox\AIOS_habbit\local_cases\workspace_chat\messages.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        cid = data.get("conversation_id", "")
        if data.get("role") == "assistant":
            conv_messages[cid] = data.get("content", "")

conv_map = {
    "CAU_01": "CONV-CU-S1-01-C7620",
    "CAU_02": "CONV-CU-S1-02-C0060",
    "CAU_03": "CONV-CU-S1-03-PHENOM-DAU",
    "CAU_04": "CONV-CU-S1-04-PHENOM-KHONG-DAU",
    "CAU_05": "CONV-CU-S1-05-FILTER",
    "CAU_06": "CONV-CU-S1-06-MANG-MANG",
    "CAU_07": "CONV-CU-S1-07-DOC-SIM-TAPE",
    "CAU_08": "CONV-CU-S1-08-DOC-BRACKET",
    "CAU_09": "CONV-CU-S1-09-TRAP-MOM",
    "CAU_10": "CONV-CU-S1-10-HONESTY",
}

for r in ev["results"]:
    rid = r["id"]
    if rid in conv_map:
        cid = conv_map[rid]
        if cid in conv_messages:
            ans = conv_messages[cid]
            r["cau_tra_loi_nguyen_van"] = ans
            print(f"Populated {rid} ({cid}): {len(ans)} chars")
    elif rid == "BUOC_2_CLOSE_GATE":
        msgs = []
        with open(r"D:\Sandbox\AIOS_habbit\local_cases\workspace_chat\messages.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data.get("conversation_id") == "CONV-CU-S2-CLOSE-GATE" and data.get("role") == "assistant":
                    msgs.append(data.get("content", ""))
        if len(msgs) >= 2:
            r["phan_hoi_cong_chan"] = msgs[0]
            r["phan_hoi_thanh_cong"] = msgs[-1]
            print(f"Populated BUOC_2_CLOSE_GATE: blocked={len(msgs[0])} chars, valid={len(msgs[-1])} chars")

with open(loc_manifest, "w", encoding="utf-8") as f:
    json.dump(ev, f, indent=2, ensure_ascii=False)

shutil.copy2(loc_manifest, desk_manifest)
print("Manifest updated and synchronized successfully!")
