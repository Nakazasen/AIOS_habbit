from typing import List
from .case_models import Case, EvidenceItem

def summarize_evidence_for_prompt(evidence_items: List[EvidenceItem], target: str, include_local_only: bool = False) -> str:
    # Target normalization to lower case to handle user inputs robustly
    target_lower = target.lower()
    
    if target_lower == "notebooklm_safe":
        should_include_local_only = False
    elif target_lower in ("gemini", "gpt", "copilot"):
        should_include_local_only = include_local_only
    elif target_lower == "local_ai":
        should_include_local_only = include_local_only
    else:
        should_include_local_only = False

    lines = []
    excluded_any = False
    for e in evidence_items:
        if e.privacy_level == "local_only":
            if not should_include_local_only:
                excluded_any = True
                lines.append(f"- [{e.source_type}] {e.title}: [ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]")
                continue
        
        snippet = e.extracted_text[:200] if e.extracted_text else ""
        lines.append(f"- [{e.source_type}] {e.title}: {snippet}...")
    
    summary_text = "\n".join(lines)
    if excluded_any:
        if summary_text:
            summary_text += "\n"
        summary_text += "Một số bằng chứng local_only (chỉ lưu cục bộ) đã bị loại bỏ vì lý do riêng tư."
    return summary_text

def build_prompt_pack(case: Case, evidence_items: List[EvidenceItem], target: str, include_local_only: bool = False, learning_card = None) -> str:
    prompt = f"Tiêu đề Hồ sơ: {case.title}\n"
    prompt += f"Tình huống Hiện tại: {case.current_situation}\n\n"
    prompt += "Tóm tắt Bằng chứng:\n"
    prompt += summarize_evidence_for_prompt(evidence_items, target, include_local_only)
    
    prompt += "\n\nGiả thuyết:\n"
    for h in case.hypotheses:
        prompt += f"- {h}\n"
        
    # Tích hợp Senior Learning Card
    if learning_card is None:
        try:
            from aios_habit.learning_models import load_learning_cards_for_case
            cards = load_learning_cards_for_case(case.case_id)
            learning_card = cards[0] if cards else None
        except Exception:
            learning_card = None

    if learning_card:
        target_lower = target.lower()
        include_learning = False
        if target_lower == "local_ai" and include_local_only:
            include_learning = True
        elif target_lower in ("gemini", "gpt", "copilot", "notebooklm_safe"):
            if case.privacy_level != "local_only" and learning_card.confidence == "confirmed":
                include_learning = True
                
        if include_learning:
            prompt += "\n\nKinh nghiệm đã rút ra từ hồ sơ này:\n"
            lines = []
            lines.append(f"Trạng thái thẻ: {learning_card.confidence}")
            if learning_card.symptoms:
                lines.append(f"Triệu chứng: {learning_card.symptoms}")
            if learning_card.related_systems:
                lines.append(f"Hệ thống liên quan: {learning_card.related_systems}")
            if learning_card.related_artifacts:
                lines.append(f"Tài nguyên liên quan: {learning_card.related_artifacts}")
            if learning_card.initial_hypotheses:
                lines.append(f"Giả thuyết ban đầu: {learning_card.initial_hypotheses}")
            if learning_card.rejected_hypotheses:
                lines.append(f"Giả thuyết bị loại bỏ: {learning_card.rejected_hypotheses}")
            if learning_card.true_cause:
                lines.append(f"Nguyên nhân thật: {learning_card.true_cause}")
            if learning_card.causal_chain:
                lines.append(f"Chuỗi nhân quả: {learning_card.causal_chain}")
            if learning_card.verification_evidence:
                lines.append(f"Bằng chứng xác nhận: {learning_card.verification_evidence}")
            if learning_card.counter_evidence:
                lines.append(f"Bằng chứng phản bác: {learning_card.counter_evidence}")
            if learning_card.actions_taken:
                lines.append(f"Đối sách đã làm: {learning_card.actions_taken}")
            if learning_card.result_outcome:
                lines.append(f"Kết quả sau đối ứng: {learning_card.result_outcome}")
            if learning_card.reusable_lesson:
                lines.append(f"Bài học tái sử dụng: {learning_card.reusable_lesson}")
            if learning_card.pattern_to_recognize:
                lines.append(f"Dấu hiệu nhận diện: {learning_card.pattern_to_recognize}")
            if learning_card.applies_when:
                lines.append(f"Điều kiện áp dụng: {learning_card.applies_when}")
            if learning_card.does_not_apply_when:
                lines.append(f"Điều kiện không áp dụng: {learning_card.does_not_apply_when}")
            if learning_card.check_first_next_time:
                lines.append(f"Lần sau kiểm gì trước: {learning_card.check_first_next_time}")
            if learning_card.retrieval_keywords:
                lines.append(f"Từ khóa tìm lại: {learning_card.retrieval_keywords}")
            if learning_card.useful_reply_vi:
                lines.append(f"Câu trả lời tiếng Việt hữu ích: {learning_card.useful_reply_vi}")
            if learning_card.useful_reply_ja:
                lines.append(f"Câu trả lời tiếng Nhật hữu ích: {learning_card.useful_reply_ja}")
            if learning_card.knowledge_update_note:
                lines.append(f"Ghi chú cập nhật tri thức: {learning_card.knowledge_update_note}")
            prompt += "\n".join(f"- {line}" for line in lines)
        else:
            prompt += "\n\nKinh nghiệm đã rút ra từ hồ sơ này:\n- [ĐÃ LOẠI BỎ VÌ RIÊNG TƯ HOẶC CHƯA XÁC NHẬN]"
        
    prompt += "\n\nKết quả yêu cầu: Vui lòng phân tích tình huống hiện tại và bằng chứng. Không tự bịa đặt sự thật. Hãy đề xuất các bước chẩn đoán tiếp theo."
    return prompt
