from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import re

@dataclass
class CitationRef:
    ref_id: str
    source_title: str
    file_type: str
    privacy_mode: str
    location: str
    evidence_id: str
    snippet: str

def build_citation_index(evidence_items: List[Any]) -> List[CitationRef]:
    """Build a stable citation index from evidence items (RAGSearchResult)."""
    refs = []
    for idx, item in enumerate(evidence_items):
        ref_id = f"[E{idx + 1}]"
        
        # Determine location string safely
        locs = []
        if getattr(item, "page_numbers", None):
            locs.append(f"Page {','.join(map(str, item.page_numbers))}")
        if getattr(item, "sheet_names", None):
            locs.append(f"Sheet {','.join(item.sheet_names)}")
        if getattr(item, "slide_numbers", None):
            locs.append(f"Slide {','.join(map(str, item.slide_numbers))}")
        
        location = " | ".join(locs) if locs else "Toàn bộ"
        
        snippet = item.text[:100] + "..." if len(item.text) > 100 else item.text
        
        refs.append(CitationRef(
            ref_id=ref_id,
            source_title=getattr(item, "source_title", "Unknown"),
            file_type=getattr(item, "file_type", "unknown"),
            privacy_mode=getattr(item, "privacy_mode", "restricted"),
            location=location,
            evidence_id=getattr(item, "chunk_id", ""),
            snippet=snippet
        ))
    return refs

def format_inline_citation(evidence_ref: CitationRef) -> str:
    """Format an inline citation string."""
    loc = f": {evidence_ref.location}" if evidence_ref.location != "Toàn bộ" else ""
    return f"{evidence_ref.ref_id[:-1]}{loc}]"

def build_source_traceability_table(refs: List[CitationRef]) -> str:
    """Build a Markdown table of sources with limitation warnings."""
    table = "| Ref | Nguồn | Loại | Vị trí | Giới hạn (Limitation) |\n|---|---|---|---|---|\n"
    for ref in refs:
        # Generate limitation warning based on type
        limitation = ""
        ftype = ref.file_type.lower()
        if ftype in ["png", "jpg", "jpeg"]:
            limitation = "Chỉ nhìn thấy ảnh, không suy luận logic/data thực"
        elif ftype == "html":
            limitation = "Chỉ thấy cấu trúc tĩnh (ERD), không thấy luồng nghiệp vụ động"
        elif ftype in ["pdf", "pptx"]:
            limitation = "Mô tả quy trình lý tưởng, cần xác nhận thực tế vận hành"
        else:
            limitation = "Cần đối chiếu số liệu thực tế"
            
        table += f"| {ref.ref_id} | {ref.source_title} | {ref.file_type.upper()} | {ref.location} | {limitation} |\n"
    return table

def extract_visible_vs_inferred_claims(answer_text: str) -> Tuple[List[str], List[str]]:
    """Extract and categorize claims based on keywords (for testing purposes)."""
    # This is a stub for the test/metric function.
    visible = []
    inferred = []
    for line in answer_text.split("\n"):
        line = line.strip()
        if not line or not line.startswith("-"):
            continue
        if "Nhìn thấy trực tiếp" in answer_text or "có trên ảnh" in line.lower() or "thể hiện" in line.lower():
            visible.append(line)
        elif "suy luận" in line.lower() or "không thể" in line.lower():
            inferred.append(line)
    return visible, inferred

def score_citation_coverage(answer_text: str, refs: List[CitationRef]) -> Dict[str, Any]:
    """Calculate citation coverage metrics."""
    cited = 0
    citation_count = 0
    for ref in refs:
        # Simplistic matching for test cases
        if ref.ref_id in answer_text or ref.ref_id.replace("[", "").replace("]", "") in answer_text:
            cited += 1
    
    # Count total occurrences of [E...]
    matches = re.findall(r"\[E\d+", answer_text)
    citation_count = len(matches)
    
    warn_count = answer_text.lower().count("không được suy luận")
    
    return {
        "citation_count": citation_count,
        "cited_evidence_count": cited,
        "uncited_evidence_count": len(refs) - cited,
        "unsupported_claim_warning_count": warn_count,
        "coverage_ratio": cited / len(refs) if refs else 0.0
    }

def compose_citation_first_answer(question: str, refs: List[CitationRef], draft_answer: str, answer_type: str) -> str:
    """Compose the final structured answer according to the new design."""
    
    parts = []
    parts.append("### Trả lời ngắn")
    parts.append(draft_answer)
    
    parts.append("\n### Bằng chứng chính")
    
    # Add specialized formatting depending on answer_type context
    if "screenshot" in answer_type.lower() or "html" in answer_type.lower() or "erd" in answer_type.lower():
        parts.append("* **Nhìn thấy trực tiếp:** Các trường, cột, và dữ liệu tĩnh có trên ảnh.")
        parts.append("* **Có thể dùng làm bằng chứng:** Cấu trúc bảng/trạng thái hệ thống.")
    
    if "pdf" in answer_type.lower() or "pptx" in answer_type.lower():
        parts.append("* **Tự động xử lý:** Hệ thống ghi nhận trạng thái tự động dựa trên cảm biến/log.")
        parts.append("* **Cần xử lý thủ công / owner review:** Điểm người dùng nhập liệu, duyệt lệnh.")
        
    parts.append("\n### Phân tích")
    if "screenshot" in answer_type.lower() or "html" in answer_type.lower() or "erd" in answer_type.lower():
        parts.append("Phân tích chỉ dựa trên phần nhìn thấy hoặc cấu trúc tĩnh trong nguồn đã trích dẫn.")
    elif "pdf" in answer_type.lower() or "pptx" in answer_type.lower():
        parts.append("Phân tích tách rõ mô tả quy trình trong tài liệu với điểm cần đối chiếu vận hành thực tế.")
    else:
        parts.append("Phân tích dựa trên các điểm bằng chứng đã trích dẫn, không mở rộng ngoài nguồn.")
        
    parts.append("\n### Không được suy luận quá mức")
    if "screenshot" in answer_type.lower() or "html" in answer_type.lower():
        parts.append("Không được suy luận logic nghiệp vụ, thứ tự phê duyệt, hay thực trạng dữ liệu bị lỗi vật lý nếu chỉ có ảnh/sơ đồ tĩnh.")
    else:
        parts.append("Chỉ dựa vào mô tả tài liệu, chưa chứng minh thực tế xưởng vận hành đúng 100% như thiết kế.")
        
    parts.append("\n### Việc cần làm tiếp")
    parts.append("Chạy /audit hoặc kiểm tra log thực tế để đối soát với hệ thống.")
    
    parts.append("\n### Bảng nguồn")
    parts.append(build_source_traceability_table(refs))
    
    return "\n".join(parts)
