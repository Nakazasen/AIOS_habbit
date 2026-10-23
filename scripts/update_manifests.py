# -*- coding: utf-8 -*-
import json
import hashlib
from pathlib import Path

# Paths
dir_docs = Path(r"D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua")
dir_ko = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")

# 1. Update ket-qua-do-desktop-home-slash-catalog-expand.json
p1_docs = dir_docs / "ket-qua-do-desktop-home-slash-catalog-expand.json"
p1_ko = dir_ko / "ket-qua-do-desktop-home-slash-catalog-expand.json"

data1 = json.loads(p1_docs.read_text(encoding="utf-8"))

# Gate 1
data1["gates"]["gate_1_palette_grouped"]["screenshot"]["size_bytes"] = 115003
data1["gates"]["gate_1_palette_grouped"]["screenshot"]["sha256"] = "EBA9BED87552FC99270A231B8392F03A0F704B60325F76BCD698DBF4BDD60E47"

# Gate 9
data1["gates"]["gate_9_taovu"]["screenshot"]["size_bytes"] = 84531
data1["gates"]["gate_9_taovu"]["screenshot"]["sha256"] = "6D5473C5ECB245968282BA15D4B6414B3C23811BFFD4DC01947C046FA168F4B3"

content1 = json.dumps(data1, indent=2, ensure_ascii=False)
p1_docs.write_text(content1, encoding="utf-8")
p1_ko.write_text(content1, encoding="utf-8")
print("[OK] Updated ket-qua-do-desktop-home-slash-catalog-expand.json in both dirs")

# 2. Update ket-qua-do-desktop-home-user-skill-create.json
p2_ko = dir_ko / "ket-qua-do-desktop-home-user-skill-create.json"
p2_docs = dir_docs / "ket-qua-do-desktop-home-user-skill-create.json"

data2 = json.loads(p2_ko.read_text(encoding="utf-8"))

# Gate 1
data2["gates"]["gate_1_palette"]["screenshot"]["size_bytes"] = 113902
data2["gates"]["gate_1_palette"]["screenshot"]["sha256"] = "B43F28E263378110D3478BB741A84C6102795CC20DA2E313C1E1F56CC35BA358"

# Gate 4
data2["gates"]["gate_4_applied"]["screenshot"]["size_bytes"] = 108459
data2["gates"]["gate_4_applied"]["screenshot"]["sha256"] = "FCB78B9F3CCE1663A9C4ACB659B179AE4344CBD576DDD8EB6340420C08DFEADB"
data2["gates"]["gate_4_applied"]["applied_evidence"] = (
    "### 🛠️ Áp dụng kỹ năng cá nhân đã tạo: **Kiem Tra Cam Bien Jig**\n\n"
    "Quy trình xử lý (Procedure):\n"
    "1. Kiểm tra nguồn cấp: Đảm bảo điện áp 24V DC ổn định tại chân số 1 và 3 của cảm biến quang.\n"
    "2. Vệ sinh thấu kính: Dùng vải mềm và cồn IPA làm sạch bề mặt phát/thu quang của cảm biến.\n"
    "3. Căn chỉnh khoảng cách: Điều chỉnh biến trở độ nhạy trên thân cảm biến cho đến khi đèn LED xanh sáng ổn định khi có vật thể."
)

content2 = json.dumps(data2, indent=2, ensure_ascii=False)
p2_ko.write_text(content2, encoding="utf-8")
p2_docs.write_text(content2, encoding="utf-8")
print("[OK] Updated ket-qua-do-desktop-home-user-skill-create.json in both dirs")
