from typing import List, Optional
from .case_models import Case, EvidenceItem

def build_handover_markdown(
    case: Case,
    evidence_items: List[EvidenceItem],
    learning_card = None,
    export_mode: str = "local"
) -> str:
    status_vn = {"open": "Mở", "investigating": "Đang điều tra", "waiting": "Đang chờ", "resolved": "Đã giải quyết", "archived": "Đã lưu trữ"}.get(case.status, case.status)
    priority_vn = {"low": "Thấp", "normal": "Bình thường", "high": "Cao", "critical": "Khẩn cấp"}.get(case.priority, case.priority)
    
    md = f"# Bàn giao Hồ sơ Sự việc: {case.title}\n"
    md += f"**Trạng thái:** {status_vn} | **Độ ưu tiên:** {priority_vn}\n\n"
    
    md += f"## Tóm tắt Tình huống (Situation)\n{case.current_situation}\n\n"
    
    md += "## Bằng chứng (Evidence)\n"
    for e in evidence_items:
        if e.privacy_level == "local_only":
            if export_mode == "local":
                md += f"- [{e.source_type}] {e.title} (Tạo lúc: {e.created_at[:16]}) [local_only]"
                if e.source_path:
                    md += f"\n  - Nguồn tham chiếu: `{e.source_path}`"
                if e.extracted_text:
                    md += f"\n  - Chi tiết: {e.extracted_text[:200]}...\n"
                else:
                    md += "\n"
            elif export_mode == "redacted":
                md += f"- [{e.source_type}] {e.title} (Tạo lúc: {e.created_at[:16]}): [ĐÃ ẨN VÌ RIÊNG TƯ]\n"
            else:  # cloud_safe
                md += f"- [{e.source_type}] {e.title} (Tạo lúc: {e.created_at[:16]}): [ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]\n"
        else:
            md += f"- [{e.source_type}] {e.title} (Tạo lúc: {e.created_at[:16]})\n"
            if export_mode == "local" and e.source_path:
                md += f"  - Nguồn tham chiếu: `{e.source_path}`\n"
            if export_mode in ("local", "cloud_safe") and e.extracted_text:
                md += f"  - Chi tiết: {e.extracted_text[:200]}...\n"
                
    md += "\n## Dòng thời gian (Timeline)\n"
    for t in case.timeline_events:
        md += f"- {t['date'][:16] if 'date' in t else ''}: {t['event']}\n"
        
    md += "\n## Các việc cần làm tiếp theo\n"
    for a in case.next_actions:
        md += f"- {a}\n"
        
    if learning_card:
        conf_map = {"draft": "Bản nháp", "reviewed": "Đã xem lại", "confirmed": "Đã xác nhận"}
        conf_vn = conf_map.get(learning_card.confidence, learning_card.confidence)
        
        md += "\n## Bài học / Kinh nghiệm\n"
        md += f"**Trạng thái thẻ:** {conf_vn}\n"
        
        include_learning = False
        if export_mode == "local":
            include_learning = True
        elif export_mode == "redacted":
            if case.privacy_level != "local_only":
                include_learning = True
        elif export_mode == "cloud_safe":
            if case.privacy_level != "local_only" and learning_card.confidence == "confirmed":
                include_learning = True
                
        if export_mode == "cloud_safe" and not include_learning:
            if case.privacy_level == "local_only":
                md += "\n> ⚠️ Thẻ học nghề bị loại bỏ vì hồ sơ chỉ lưu cục bộ (local_only).\n"
            else:
                md += "\n> ⚠️ Thẻ học nghề bị loại bỏ vì chưa được xác nhận (draft/reviewed).\n"
        elif export_mode == "redacted" and case.privacy_level == "local_only":
            md += "\n> ⚠️ Chi tiết bài học đã được ẩn vì lý do bảo mật (hồ sơ local_only).\n\n"
            if learning_card.symptoms:
                md += "- **Triệu chứng:** [ĐÃ ẨN VÌ RIÊNG TƯ]\n"
            if learning_card.true_cause:
                md += "- **Nguyên nhân thật:** [ĐÃ ẨN VÌ RIÊNG TƯ]\n"
            if learning_card.actions_taken:
                md += "- **Đối sách:** [ĐÃ ẨN VÌ RIÊNG TƯ]\n"
            if learning_card.reusable_lesson:
                md += "- **Bài học tái sử dụng:** [ĐÃ ẨN VÌ RIÊNG TƯ]\n"
            if learning_card.check_first_next_time:
                md += "- **Lần sau kiểm gì trước:** [ĐÃ ẨN VÌ RIÊNG TƯ]\n"
            if learning_card.retrieval_keywords:
                md += "- **Từ khóa tìm lại:** [ĐÃ ẨN VÌ RIÊNG TƯ]\n"
        else:
            if learning_card.confidence != "confirmed":
                md += "\n> ⚠️ Lưu ý: Nội dung dưới đây là bài học chưa được xác nhận hoàn toàn (chỉ mang tính chất tham khảo).\n\n"
            else:
                md += "\n> ✅ Bài học đã được xác nhận kiểm chứng.\n\n"
                
            if learning_card.symptoms:
                md += f"- **Triệu chứng:** {learning_card.symptoms}\n"
            if learning_card.true_cause:
                md += f"- **Nguyên nhân thật:** {learning_card.true_cause}\n"
            if learning_card.actions_taken:
                md += f"- **Đối sách:** {learning_card.actions_taken}\n"
            if learning_card.reusable_lesson:
                md += f"- **Bài học tái sử dụng:** {learning_card.reusable_lesson}\n"
            if learning_card.check_first_next_time:
                md += f"- **Lần sau kiểm gì trước:** {learning_card.check_first_next_time}\n"
            if learning_card.retrieval_keywords:
                md += f"- **Từ khóa tìm lại:** {learning_card.retrieval_keywords}\n"
    else:
        md += "\n## Bài học / Kinh nghiệm\n"
        md += "Chưa có thẻ học nghề cho hồ sơ này.\n"

    # Add warnings or footer check
    if export_mode == "local" or case.privacy_level == "local_only":
        md += "\n> ⚠️ Cảnh báo Bảo mật: Tài liệu này chứa dữ liệu sự việc chỉ lưu cục bộ.\n"
    else:
        md += "\n> ✅ Tài liệu bàn giao an toàn cho chia sẻ/đám mây.\n"
        
    return md
