"""Setup production sample skills, migrate legacy data, and configure Obsidian Second Brain Vault."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.skills_curator import (
    SkillRecord,
    list_skills,
    migrate_legacy_data,
    run_curator,
    save_skill_to_store,
    setup_obsidian_vault,
    sync_all_domain_mocs,
)

def run_setup() -> None:
    s_dir = APP_DIR / "local_cases" / "skills"
    s_dir.mkdir(parents=True, exist_ok=True)

    print("1. Creating Hermes-standard sample skills in local_cases/skills/...")

    # Skill 1: LSU optical alignment
    sk1 = SkillRecord(
        name="skill_lsu_optical_alignment",
        title="Quy trình căn chỉnh quang học LSU & bù độ lệch trục",
        mien="lsu",
        applies_when="Khi căn chỉnh cụm thấu kính f-theta, gương đa giác polygon và bù beam tilt cụm LSU",
        does_not_apply_when="Khi xử lý sự cố nguồn cấp tổng hoặc lỗi giao tiếp bus mạng máy in",
        evidence_refs=["CASE-1cdd3df4", "SOP-LSU-2026"],
        links=["[[lsu_MOC]]"],
        content_body="""# Quy trình căn chỉnh quang học LSU & bù độ lệch trục

## 1. Mục đích & Nguyên lý
Hướng dẫn chuẩn thao tác cân chỉnh hệ quang học Laser Scanning Unit (LSU) nhằm triệt tiêu hiện tượng lệch chùm tia (beam deviation) và méo ảnh quét đa giác.

## 2. Quy trình thực hiện (Procedure First)
1. **Bước 1**: Đặt cụm LSU lên đồ gá chuẩn (Alignment Jig J-420), bật nguồn laser ở mức công suất kiểm tra 1.2mW.
2. **Bước 2**: Đo tọa độ giao điểm beam trên màn thu CCD tại 3 vị trí: Start-of-Scan (SOS), Center, End-of-Scan (EOS).
3. **Bước 3**: Điều chỉnh ốc vi sai M2.5 tại chân đế gương f-theta nếu độ lệch vượt quá ±0.05mm.
4. **Bước 4**: Chạy script đối chiếu tự động `scripts/verify_lsu_beam_deviation.py` để khóa thông số bù vào EEPROM.

## 3. Cạm bẫy cần tránh (Pitfalls)
- **Cạm bẫy**: Không siết ốc cố định khi laser đang bật công suất cao vì biến dạng nhiệt cục bộ làm sai lệch kết quả đo sau khi nguội.

## 4. Tệp phụ trợ
- `references/lsu_optical_specs.md`: Bảng dung sai quang học chuẩn.
- `templates/bien_ban_can_chinh_lsu.md`: Biên bản nghiệm thu cân chỉnh.
- `scripts/verify_lsu_beam_deviation.py`: Script tính toán độ lệch trục.
""",
        supporting_files={
            "references/lsu_optical_specs.md": """# Thông số kỹ thuật quang học LSU chuẩn
| Tham số | Giá trị chuẩn | Dung sai cho phép |
|---|---|---|
| Bước sóng laser | 785 nm | ±5 nm |
| Góc quét SOS-EOS | 64.5 deg | ±0.2 deg |
| Độ lệch beam tilt | 0.00 mm | ±0.03 mm |
""",
            "templates/bien_ban_can_chinh_lsu.md": """# Biên bản căn chỉnh quang học LSU
- Ngày thực hiện:
- Kỹ sư phụ trách:
- Mã serial LSU:
- Kết quả SOS: [ ] Đạt  [ ] Lệch
- Kết quả EOS: [ ] Đạt  [ ] Lệch
- Chữ ký chuyên gia:
""",
            "scripts/verify_lsu_beam_deviation.py": """# Script kiểm tra độ lệch chùm tia LSU tự động
import sys

def verify_beam_deviation(sos_mm, eos_mm, tolerance=0.03):
    dev = abs(sos_mm - eos_mm)
    print(f"LSU Beam deviation measured: {dev:.4f} mm (Tolerance: {tolerance} mm)")
    return dev <= tolerance

if __name__ == '__main__':
    sos = float(sys.argv[1]) if len(sys.argv) > 1 else 0.015
    eos = float(sys.argv[2]) if len(sys.argv) > 2 else 0.022
    passed = verify_beam_deviation(sos, eos)
    print("VERDICT:", "PASS" if passed else "FAIL")
    sys.exit(0 if passed else 1)
""",
        },
    )
    save_skill_to_store(sk1, skills_dir=s_dir)

    # Skill 2: 4M Investigation Workflow
    sk2 = SkillRecord(
        name="skill_4m_investigation_workflow",
        title="Phương pháp điều tra sự cố 4M & xác định nguyên nhân gốc",
        mien="dieutraloi",
        applies_when="Khi phân tích nguyên nhân gốc các ca sự cố lặp lại hoặc lỗi chất lượng dây chuyền",
        does_not_apply_when="Khi chỉ cập nhật biên bản bàn giao ca thông thường",
        evidence_refs=["CASE-328C72FF", "4M-STANDARD-V2"],
        links=["[[dieutraloi_MOC]]"],
        content_body="""# Phương pháp điều tra sự cố 4M & xác định nguyên nhân gốc

## 1. Mục đích
Chuẩn hóa luồng phân loại và truy vết 4 yếu tố sản xuất (Man, Machine, Material, Method) để tìm nguyên nhân gốc (Root Cause) không để lọt lỗi do suy đoán cảm tính.

## 2. Quy trình thực hiện (Procedure First)
1. **Bước 1**: Cô lập hiện trường và thu thập bằng chứng vật lý (ảnh chụp, log sự cố, mẫu lỗi).
2. **Bước 2**: Rà soát 4 yếu tố theo ma trận `references/4m_matrix_checklist.md`:
   - Con người (Man): Đào tạo, thao tác, chứng chỉ.
   - Máy móc (Machine): Độ mòn jig, sensor drift, áp suất khí nén.
   - Vật liệu (Material): Lô linh kiện, hạn sử dụng keo dán.
   - Phương pháp (Method): Phiên bản SOP, thứ tự các bước.
3. **Bước 3**: Lập biểu mẫu biên bản theo `templates/bieu_mau_bien_ban_4m.md`.
4. **Bước 4**: Chạy script xác thực cổng bằng chứng `scripts/verify_4m_root_cause.py`.

## 3. Cạm bẫy cần tránh
- **Cạm bẫy**: 80% kết luận vội vàng quy cho Man thực chất bắt nguồn từ Machine (sensor suy hao).
""",
        supporting_files={
            "references/4m_matrix_checklist.md": """# Ma trận kiểm tra 4M
- [ ] Man: Thao tác viên có chứng chỉ bậc 2 trở lên?
- [ ] Machine: Cảm biến có được hiệu chuẩn trong 30 ngày qua?
- [ ] Material: Tem nhãn có đạt độ bám dính tiêu chuẩn?
- [ ] Method: Có bước bỏ qua nào so với SOP 1.4?
""",
            "templates/bieu_mau_bien_ban_4m.md": """# Biên bản điều tra 4M
1. Mô tả sự cố:
2. Phân tích yếu tố nổi trội:
3. Nguyên nhân gốc đã chứng minh:
4. Đối sách khắc phục:
""",
            "scripts/verify_4m_root_cause.py": """# Script kiểm tra chốt chặn bằng chứng 4M
def check_evidence_gate(facts):
    required = {'symptom', 'verified_cause', 'counter_measure'}
    return required.issubset(set(facts.keys()))

if __name__ == '__main__':
    sample = {'symptom': 'Ket nhan', 'verified_cause': 'Sensor hong', 'counter_measure': 'Thay sensor'}
    print('Evidence gate status:', 'VALID' if check_evidence_gate(sample) else 'INVALID')
""",
        },
    )
    save_skill_to_store(sk2, skills_dir=s_dir)

    # Skill 3: MOM Sync Recovery
    sk3 = SkillRecord(
        name="skill_mom_sync_recovery",
        title="Xử lý kẹt job đồng bộ MES_SYNC trên Opcenter",
        mien="mom_opcenter",
        applies_when="Khi hệ thống Opcenter báo thiếu vật tư nhưng kho InterStock xác nhận còn tồn dư thừa",
        does_not_apply_when="Khi thiếu vật tư vật lý thực tế ngoài kho",
        evidence_refs=["CASE-1cdd3df4", "LC-DEMO-SUPPLY"],
        links=["[[mom_opcenter_MOC]]"],
        content_body="""# Xử lý kẹt job đồng bộ MES_SYNC trên Opcenter

## 1. Hiện tượng & Phạm vi
Hiện tượng: Trên màn hình Opcenter hiển thị cảnh báo thiếu linh kiện (Out of Stock), trong khi dữ liệu kho trung chuyển InterStock vẫn hiển thị số lượng khả dụng > 0. Nguyên nhân thường do tiến trình đồng bộ ngầm `MES_SYNC` bị timeout hoặc deadlock bảng.

## 2. Quy trình xử lý (Procedure First)
1. **Bước 1**: Truy vấn bảng nhật ký đồng bộ `MES_SYNC_LOG` để xác định Session ID bị kẹt (trạng thái RUNNING > 15 phút).
2. **Bước 2**: Thực hiện kiểm tra lock bằng script `scripts/check_mes_sync_lock.py`.
3. **Bước 3**: Dùng biểu mẫu `templates/lenh_clear_job_mes_sync.md` để giải phóng khóa hàng và kích hoạt trigger đồng bộ lại.
4. **Bước 4**: Xác nhận số tồn trên giao diện Opcenter sau 60 giây.

## 3. Cạm bẫy
- Không khởi động lại dịch vụ MES khi các trạm lắp ráp đang trong nhịp chu kỳ quét mã vạch.
""",
        supporting_files={
            "references/mes_sync_tables_ref.md": """# Danh mục bảng dữ liệu đồng bộ MES
- `MES_SYNC_LOG`: Nhật ký các phiên đồng bộ (status, start_time, duration).
- `INTERSTOCK_BALANCES`: Số dư khả dụng thực tế kho trung gian.
- `OPCENTER_LINE_REQ`: Yêu cầu cấp vật tư dây chuyền.
""",
            "templates/lenh_clear_job_mes_sync.md": """-- Câu lệnh giải phóng job đồng bộ treo
UPDATE MES_SYNC_LOG
SET status = 'FORCE_TIMEOUT', note = 'Cleared by AIOS habit skill'
WHERE status = 'RUNNING' AND start_time < datetime('now', '-15 minutes');
""",
            "scripts/check_mes_sync_lock.py": """# Script kiểm tra deadlock đồng bộ MES_SYNC
def is_sync_locked(active_sessions):
    return len([s for s in active_sessions if s.get('elapsed_min', 0) > 15]) > 0

if __name__ == '__main__':
    sessions = [{'id': 101, 'elapsed_min': 22}]
    print('Sync Lock State:', 'LOCKED' if is_sync_locked(sessions) else 'NORMAL')
""",
        },
    )
    save_skill_to_store(sk3, skills_dir=s_dir)

    # Skill 4: Pinned emergency stop skill
    sk4 = SkillRecord(
        name="skill_pinned_emergency_stop",
        title="Quy trình dừng khẩn cấp dây chuyền sản xuất",
        mien="general",
        pinned=True,
        applies_when="Khi phát hiện sự cố an toàn lao động, cháy nổ hoặc va chạm cơ khí nguy hiểm",
        does_not_apply_when="Khi dừng máy bảo dưỡng định kỳ theo kế hoạch",
        evidence_refs=["SAFETY-REG-01"],
        links=["[[general_MOC]]"],
        content_body="""# Quy trình dừng khẩn cấp dây chuyền sản xuất

## 1. Nguyên tắc An toàn Tuyệt đối
Tính mạng và an toàn của con người luôn được ưu tiên cao nhất, vượt trên mọi chỉ số sản lượng OEE.

## 2. Thao tác thực hiện
1. **Bước 1**: Nhấn ngay nút DỪNG KHẨN CẤP (E-Stop Nấm Đỏ) gần nhất.
2. **Bước 2**: Ngắt aptomat tổng của cụm máy phát sinh sự cố.
3. **Bước 3**: Gọi số khẩn cấp an toàn theo `references/emergency_contacts.md`.
4. **Bước 4**: Lập báo cáo sự cố theo mẫu `templates/bao_cao_dung_khan.md`.
""",
        supporting_files={
            "references/emergency_contacts.md": """# Danh bạ khẩn cấp nhà máy
- Đội PCCC & Cứu nạn: 114 / Máy lẻ 101
- Trưởng ca an toàn: 0988.xxx.xxx
- Phòng Y tế: Máy lẻ 105
""",
            "templates/bao_cao_dung_khan.md": """# Báo cáo dừng khẩn cấp
- Thời gian nhấn E-Stop:
- Vị trí nút nhấn:
- Lý do kích hoạt:
- Tình trạng nhân sự: [ ] An toàn  [ ] Cần hỗ trợ
""",
            "scripts/check_line_status.py": """# Kiểm tra trạng thái an toàn toàn tuyến
def line_safety_status(e_stop_pressed=True):
    return 'EMERGENCY_STOP_ACTIVE' if e_stop_pressed else 'RUNNING_SAFE'

if __name__ == '__main__':
    print('Status:', line_safety_status(True))
""",
        },
    )
    save_skill_to_store(sk4, skills_dir=s_dir)

    print("2. Migrating legacy data (memory_decisions.jsonl & learning_cards.jsonl)...")
    mig_res = migrate_legacy_data(local_cases_dir=APP_DIR / "local_cases")
    print(f"   Decisions input: {mig_res['input_decisions_count']}")
    print(f"   Cards input:     {mig_res['input_cards_count']}")
    print(f"   Total input:     {mig_res['total_inputs']}")
    print(f"   Lessons saved:   {mig_res['migrated_lessons_saved']}")
    assert mig_res['total_inputs'] == mig_res['migrated_lessons_saved'], "Migration count mismatch!"

    print("3. Setting up Obsidian Second Brain Vault & domain MOCs...")
    sb_dir = APP_DIR / "local_cases" / "second_brain"
    setup_obsidian_vault(sb_dir, skills_dir=s_dir)
    mocs = sync_all_domain_mocs(sb_dir, skills_dir=s_dir)
    print(f"   Synchronized {len(mocs)} domain MOC pages.")

    # Register in user's obsidian.json if present
    appdata_obs = Path(os.path.expandvars(r"%APPDATA%\obsidian\obsidian.json"))
    if appdata_obs.exists():
        try:
            import time
            obs_data = json.loads(appdata_obs.read_text(encoding="utf-8"))
            vaults = obs_data.setdefault("vaults", {})
            vault_path_str = str(sb_dir.resolve())
            already_reg = any(v.get("path") == vault_path_str for v in vaults.values())
            if not already_reg:
                import hashlib
                v_key = hashlib.md5(vault_path_str.encode("utf-8")).hexdigest()[:16]
                vaults[v_key] = {"path": vault_path_str, "ts": int(time.time() * 1000)}
                appdata_obs.write_text(json.dumps(obs_data, indent=2), encoding="utf-8")
                print(f"   Registered Second Brain vault in Obsidian config: {v_key}")
        except Exception as exc:
            print(f"   Obsidian registration note: {exc}")

    print("4. Executing Curator maintenance pass...")
    report = run_curator(skills_dir=s_dir, force=True)
    if report:
        print(f"   {report.summary}")

    print("5. Listing current local skills library:")
    skills = list_skills(skills_dir=s_dir)
    for s in skills:
        pin = "[PINNED]" if s.pinned else "        "
        print(f"   - {s.name:<32} | {s.mien:<12} | {s.state:<8} | {pin} | uses: {s.use_count}")

    print("\nSetup & Migration completed successfully.")

if __name__ == "__main__":
    run_setup()
