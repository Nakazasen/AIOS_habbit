import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

from aios_habit.notebook_index import load_chunks, build_notebook_index, search_notebook_chunks

LOCAL_CASES_DIR = Path.cwd() / "local_cases"
QUESTIONS_FILE = LOCAL_CASES_DIR / "notebook_questions.jsonl"
ANSWERS_FILE = LOCAL_CASES_DIR / "notebook_answers.jsonl"

@dataclass
class NotebookAnswerResult:
    answer_text: str
    prompt_text: str
    used_chunks: list
    provider: str
    model: str
    privacy_mode: str
    blocked: bool = False
    block_reason: str = ""

def save_question_history(notebook_id: str, question: str, target: str, export_mode: str):
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = {
            "notebook_id": notebook_id,
            "question": question,
            "target": target,
            "export_mode": export_mode,
            "created_at": datetime.now().isoformat()
        }
        with open(QUESTIONS_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception:
        pass

def save_answer_history(notebook_id: str, question: str, answer: str, target: str, provider: str, model: str):
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = {
            "notebook_id": notebook_id,
            "question": question,
            "answer": answer,
            "target": target,
            "provider": provider,
            "model": model,
            "created_at": datetime.now().isoformat()
        }
        with open(ANSWERS_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception:
        pass

def should_redact_chunk(privacy_level: str, target: str, export_mode: str) -> bool:
    if privacy_level != "local_only":
        return False
    
    target_lower = target.lower()
    export_mode_lower = export_mode.lower()
    
    if target_lower == "local_ai" and export_mode_lower == "local":
        return False
        
    return True

def build_notebook_question_prompt(
    notebook_id: str,
    question: str,
    target: str,
    export_mode: str,
    limit: int = 5
) -> str:
    # 1. Save history
    save_question_history(notebook_id, question, target, export_mode)
    
    # 2. Search relevant chunks
    hits = search_notebook_chunks(notebook_id, question, limit=limit)
    
    lines = []
    excluded_any = False
    
    for hit in hits:
        chunk = hit.chunk
        redact = should_redact_chunk(chunk.privacy_level, target, export_mode)
        if redact:
            excluded_any = True
            snippet = "[ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]"
        else:
            snippet = chunk.text
            
        lines.append(
            f"- [Nguồn] {chunk.source_title} (ID: {chunk.source_id}, File: {chunk.original_filename}) - Đoạn {chunk.chunk_index} (Độ khớp: {hit.score:.1f}):\n"
            f"  {snippet}"
        )
        
    if not lines:
        context_text = "Không tìm thấy đoạn thông tin nào liên quan trong sổ tri thức."
    else:
        context_text = "\n\n".join(lines)
        if excluded_any:
            context_text += "\n\nMột số dữ liệu thuộc tính riêng tư local_only đã bị ẩn/mã hóa trong prompt này do cấu hình bảo mật đám mây."
            
    prompt = (
        "Bạn là một trợ lý AI phân tích tri thức chuyên sâu. Hãy trả lời câu hỏi dưới đây dựa trên tài liệu được cung cấp.\n\n"
        f"Câu hỏi: {question}\n\n"
        "Tài liệu nguồn liên quan:\n"
        f"{context_text}\n\n"
        "Yêu cầu nghiêm ngặt:\n"
        "- Chỉ trả lời dựa trên nguồn được cung cấp.\n"
        "- Nếu thiếu bằng chứng, nói chưa đủ dữ liệu.\n"
        "- Trích dẫn source_id/source_title khi trả lời."
    )
    return prompt

def build_study_pack_prompt(
    notebook_id: str,
    target: str,
    export_mode: str,
    limit: int = 8
) -> str:
    # Load chunks (if empty, build index)
    chunks = load_chunks(notebook_id)
    if not chunks:
        chunks = build_notebook_index(notebook_id)
        
    chunks = chunks[:limit]
    
    lines = []
    excluded_any = False
    
    for chunk in chunks:
        redact = should_redact_chunk(chunk.privacy_level, target, export_mode)
        if redact:
            excluded_any = True
            snippet = "[ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]"
        else:
            snippet = chunk.text
            
        lines.append(
            f"- [Nguồn] {chunk.source_title} (ID: {chunk.source_id}, File: {chunk.original_filename}) - Đoạn {chunk.chunk_index}:\n"
            f"  {snippet}"
        )
        
    if not lines:
        context_text = "Không có tài liệu nguồn nào được tìm thấy trong sổ tri thức này để ôn tập."
    else:
        context_text = "\n\n".join(lines)
        if excluded_any:
            context_text += "\n\nMột số tài liệu local_only đã bị ẩn trong study pack này vì lý do an toàn thông tin."
            
    prompt = (
        "Bạn là một chuyên gia học tập và ôn tập kiến thức. Dưới đây là các tài liệu tham khảo từ Sổ tri thức:\n\n"
        "Tài liệu nguồn tham khảo:\n"
        f"{context_text}\n\n"
        "Hãy tạo một Study Pack ôn tập chi tiết gồm các phần sau:\n"
        "1. Tóm tắt nội dung chính (Summary).\n"
        "2. Thuật ngữ cốt lõi & định nghĩa (Glossary).\n"
        "3. Checklist các bước hoặc ý chính cần nắm vững.\n"
        "4. 10 câu hỏi ôn tập (Review Questions) kèm gợi ý trả lời ngắn gọn.\n"
        "5. 10 thẻ nhớ học tập dạng Câu hỏi / Trả lời (Flashcards).\n"
        "6. Xác định các điểm còn mờ nhạt, thiếu dữ liệu hoặc cần làm rõ thêm (Weak/unknown areas).\n\n"
        "Yêu cầu nghiêm ngặt:\n"
        "- Chỉ soạn thảo Study Pack dựa trên nguồn dữ liệu thực tế được cung cấp ở trên.\n"
        "- Tuyệt đối không tự bịa đặt kiến thức nằm ngoài dữ liệu được cung cấp.\n"
        "- Nếu một số dữ liệu bị loại bỏ vì lý do bảo mật, ghi nhận rõ sự thiếu hụt đó."
    )
    return prompt

def answer_notebook_question(
    notebook_id: str,
    question: str,
    target: str,
    export_mode: str,
    limit: int = 5,
    allow_cloud_send: bool = False,
) -> NotebookAnswerResult:
    if not question.strip():
        return NotebookAnswerResult(
            answer_text="",
            prompt_text="",
            used_chunks=[],
            provider="",
            model="",
            privacy_mode=export_mode,
            blocked=True,
            block_reason="Câu hỏi đang trống."
        )
        
    from aios_habit.llm_client import load_llm_config, complete_chat
    
    config = load_llm_config()
    if not config:
        return NotebookAnswerResult(
            answer_text="",
            prompt_text="",
            used_chunks=[],
            provider="",
            model="",
            privacy_mode=export_mode,
            blocked=True,
            block_reason="AI provider chưa được cấu hình. Vui lòng thiết lập biến môi trường AIOS_LLM_PROVIDER."
        )
        
    # Search relevant chunks
    hits = search_notebook_chunks(notebook_id, question, limit=limit)
    used_chunks_list = [hit.chunk for hit in hits]
    
    # Locality and privacy checks
    if config.locality == "cloud":
        if export_mode == "local":
            has_local_only = any(chunk.privacy_level == "local_only" for chunk in used_chunks_list)
            if has_local_only:
                return NotebookAnswerResult(
                    answer_text="",
                    prompt_text="",
                    used_chunks=used_chunks_list,
                    provider=config.provider,
                    model=config.model,
                    privacy_mode=export_mode,
                    blocked=True,
                    block_reason="Không thể gửi dữ liệu local_only lên AI Cloud ở chế độ xuất local. Vui lòng chuyển sang Chế độ xuất cloud_safe hoặc sử dụng local_ai."
                )
        effective_export_mode = "cloud_safe" if export_mode == "local" else export_mode
    else:
        effective_export_mode = export_mode
        
    # Generate prompt using the effective export_mode
    prompt = build_notebook_question_prompt(
        notebook_id=notebook_id,
        question=question,
        target=target,
        export_mode=effective_export_mode,
        limit=limit
    )
    
    # Call the LLM
    try:
        system_prompt = "Bạn là trợ lý AI thông minh phân tích tri thức."
        answer = complete_chat(prompt, system_prompt=system_prompt, config=config)
        
        # Save answer history
        save_answer_history(notebook_id, question, answer, target, config.provider, config.model)
        
        return NotebookAnswerResult(
            answer_text=answer,
            prompt_text=prompt,
            used_chunks=used_chunks_list,
            provider=config.provider,
            model=config.model,
            privacy_mode=effective_export_mode,
            blocked=False
        )
    except Exception as e:
        return NotebookAnswerResult(
            answer_text="",
            prompt_text=prompt,
            used_chunks=used_chunks_list,
            provider=config.provider,
            model=config.model,
            privacy_mode=effective_export_mode,
            blocked=True,
            block_reason=f"Lỗi khi gọi AI: {e}"
        )

