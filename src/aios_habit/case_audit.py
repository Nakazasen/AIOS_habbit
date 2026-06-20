from pathlib import Path
from typing import List, Dict, Optional, Any
from .case_models import Case, EvidenceItem

def audit_case_cockpit_state(
    case: Optional[Case],
    evidence_items: List[EvidenceItem],
    prompt_outputs: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    errors = []
    warnings = []
    
    # 1. selected/active case exists
    if not case:
        errors.append("Hồ sơ sự việc đang hoạt động không tồn tại hoặc chưa được chọn.")
        return {
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings
        }
        
    # 2. active case has non-empty title
    if not case.title or not case.title.strip():
        errors.append("Hồ sơ sự việc đang hoạt động có tiêu đề bị trống.")
        
    # 3. active case has non-empty current_situation
    if not case.current_situation or not case.current_situation.strip():
        errors.append("Hồ sơ sự việc đang hoạt động có phần tóm tắt tình huống bị trống.")
        
    # Let's resolve the expected local cases assets folder path
    cwd = Path.cwd().resolve()
    assets_dir = (cwd / "local_cases" / "assets").resolve()
    
    # Check evidence items
    for ev in evidence_items:
        # 4. every evidence item has case_id
        if not ev.case_id or not ev.case_id.strip():
            errors.append(f"Bằng chứng {ev.evidence_id} không có case_id.")
            
        # 5. every evidence item has source_type
        if not ev.source_type or not ev.source_type.strip():
            errors.append(f"Bằng chứng {ev.evidence_id} không có source_type.")
            
        # 6. every evidence item has privacy_level
        if not ev.privacy_level or not ev.privacy_level.strip():
            errors.append(f"Bằng chứng {ev.evidence_id} không có privacy_level.")
            
        # 9. no evidence item has empty title and empty extracted_text at the same time
        has_title = bool(ev.title and ev.title.strip())
        has_text = bool(ev.extracted_text and ev.extracted_text.strip())
        if not has_title and not has_text:
            errors.append(f"Bằng chứng {ev.evidence_id} có cả tiêu đề và văn bản trích xuất thô bị trống.")
            
        # 8. uploaded asset path, if present, stays under local_cases/assets
        if ev.source_path and ev.source_path not in ("clipboard", "manual"):
            try:
                p = Path(ev.source_path).resolve()
                if not str(p).startswith(str(assets_dir)):
                    errors.append(f"Bằng chứng {ev.evidence_id} có đường dẫn tệp '{ev.source_path}' nằm ngoài thư mục tài nguyên cục bộ '{assets_dir}'.")
            except Exception as e:
                errors.append(f"Bằng chứng {ev.evidence_id} có đường dẫn tệp không hợp lệ: {e}")
                
        # 7. local_only evidence is excluded from notebooklm_safe/gemini/gpt/copilot prompt outputs by default
        if ev.privacy_level == "local_only" and prompt_outputs:
            for target, prompt_text in prompt_outputs.items():
                if target.lower() in ("notebooklm_safe", "gemini", "gpt", "copilot"):
                    if has_text and ev.extracted_text in prompt_text:
                        errors.append(f"Bằng chứng local_only '{ev.evidence_id}' bị rò rỉ văn bản trích xuất thô trong prompt đích '{target}'.")


    # Kiểm tra an toàn cho Senior Learning Card
    if case:
        try:
            from aios_habit.learning_models import load_learning_cards_for_case
            cards = load_learning_cards_for_case(case.case_id)
            learning_card = cards[0] if cards else None
        except Exception:
            learning_card = None

        if learning_card:
            # 1. Cảnh báo nếu đã confirmed nhưng không ghi nguyên nhân thật
            if learning_card.confidence == "confirmed":
                cause_clean = learning_card.true_cause.strip().lower()
                if not cause_clean or cause_clean in ("", "chưa xác nhận", "n/a", "none", "tbd", "unknown"):
                    warnings.append("Thẻ học nghề đã được xác nhận (confirmed) nhưng nguyên nhân thật (true_cause) chưa được ghi rõ hoặc ghi là 'chưa xác nhận'.")
                
                # Cảnh báo thiếu bằng chứng kiểm chứng
                evidence_clean = learning_card.verification_evidence.strip().lower()
                if not evidence_clean or len(evidence_clean) < 5 or evidence_clean in ("", "chưa xác nhận", "none", "n/a", "tbd", "unknown", "chưa có"):
                    warnings.append("Thẻ học nghề đã đánh dấu xác nhận nhưng thiếu bằng chứng kiểm chứng. Hãy bổ sung bằng chứng trước khi coi đây là kinh nghiệm đáng tin.")
            
            # 2. Ngăn rò rỉ thông tin thô của thẻ học nghề lên cloud nếu chưa confirmed hoặc case là local_only
            should_exclude_from_cloud = (case.privacy_level == "local_only" or learning_card.confidence != "confirmed")
            if should_exclude_from_cloud and prompt_outputs:
                fields_to_check = [
                    learning_card.symptoms,
                    learning_card.related_systems,
                    learning_card.related_artifacts,
                    learning_card.initial_hypotheses,
                    learning_card.rejected_hypotheses,
                    learning_card.true_cause,
                    learning_card.causal_chain,
                    learning_card.verification_evidence,
                    learning_card.counter_evidence,
                    learning_card.actions_taken,
                    learning_card.result_outcome,
                    learning_card.reusable_lesson,
                    learning_card.pattern_to_recognize,
                    learning_card.applies_when,
                    learning_card.does_not_apply_when,
                    learning_card.check_first_next_time,
                    learning_card.retrieval_keywords,
                    learning_card.useful_reply_vi,
                    learning_card.useful_reply_ja,
                    learning_card.knowledge_update_note
                ]
                leaked = False
                for text in fields_to_check:
                    if leaked:
                        break
                    if text and text.strip():
                        for target, prompt_text in prompt_outputs.items():
                            if target.lower() in ("notebooklm_safe", "gemini", "gpt", "copilot"):
                                if text in prompt_text:
                                    errors.append(f"Kinh nghiệm học nghề có chứa nội dung riêng tư/chưa xác nhận bị rò rỉ trong prompt đích '{target}'.")
                                    leaked = True
                                    break

    # Kiểm tra bảo mật và toàn vẹn của Sổ tri thức & Tài liệu nguồn
    if case:
        try:
            from aios_habit.workspace_models import load_notebooks
            from aios_habit.source_ingest import load_sources, NOTEBOOK_ASSETS_DIR
            notebooks = {n.notebook_id: n for n in load_notebooks()}
            sources = load_sources()
            resolved_notebook_assets_dir = NOTEBOOK_ASSETS_DIR.resolve()
        except Exception:
            notebooks = {}
            sources = []
            resolved_notebook_assets_dir = None

        # 1. Kiểm tra sự tồn tại của Sổ tri thức liên kết
        if hasattr(case, "linked_notebook_ids") and case.linked_notebook_ids:
            for nb_id in case.linked_notebook_ids:
                if nb_id not in notebooks:
                    warnings.append(f"Hồ sơ liên kết với Sổ tri thức '{nb_id}' nhưng Sổ tri thức này không tồn tại trong hệ thống.")

        # 2. Kiểm tra path containment và rò rỉ riêng tư của các tài liệu nguồn
        for src in sources:
            if src.asset_path and resolved_notebook_assets_dir:
                try:
                    p = Path(src.asset_path).resolve()
                    if not p.is_relative_to(resolved_notebook_assets_dir):
                        errors.append(f"Tài liệu nguồn {src.source_id} có đường dẫn tệp '{src.asset_path}' nằm ngoài thư mục lưu trữ Sổ tri thức cục bộ '{resolved_notebook_assets_dir}'.")
                except Exception as e:
                    errors.append(f"Tài liệu nguồn {src.source_id} có đường dẫn tệp không hợp lệ: {e}")

            if src.privacy_level == "local_only" and prompt_outputs:
                has_text = bool(src.preview_text and src.preview_text.strip())
                if has_text:
                    for target, prompt_text in prompt_outputs.items():
                        if target.lower() in ("notebooklm_safe", "gemini", "gpt", "copilot"):
                            if src.preview_text in prompt_text:
                                errors.append(f"Tài liệu nguồn local_only '{src.source_id}' bị rò rỉ nội dung trong prompt đích '{target}'.")

    status = "FAIL" if errors else "PASS"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings
    }
