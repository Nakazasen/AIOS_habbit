from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from aios_habit.rag_answer_composer import answer_to_dict, compose_answer, compose_local_answer, local_answer_draft_to_dict
from aios_habit.rag_evidence import build_evidence_pack, evidence_pack_to_dict
from aios_habit.rag_ingest import build_chunks_from_elements, build_elements_from_extracted_payload
from aios_habit.rag_rerank import rerank_search_results
from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks, search_rag_chunks
from aios_habit.document_extractors import _extract_excel, _extract_pdf
from aios_habit.domain_playbooks import GENERAL_PLAYBOOK, MANUFACTURING_PLAYBOOK, text_has_manufacturing_terms
from aios_habit.rag_core_profiles import normalize_profile_id

SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".csv", ".log", ".json", ".xml", ".html", ".htm"}
SUPPORTED_METADATA_SUFFIXES = {".pdf", ".xlsx", ".xlsm", ".xls", ".pptx", ".ppt", ".png", ".jpg", ".jpeg"}
DEFAULT_OUTPUT_DIR = Path("local_runs/notebooklm_compare")


@dataclass
class CompareConfig:
    source_root: str
    output_dir: str = str(DEFAULT_OUTPUT_DIR)
    privacy_mode: str = "local_only"
    question_count: int = 12
    use_local_reranker: bool = True
    notebooklm_notebook_id: str = ""
    subset_filter: str = "none"


@dataclass
class CompareQuestion:
    question_id: str
    question: str
    category: str
    language: str
    source_hint: str = ""
    source_relative_path: str = ""
    source_extension: str = ""
    source_import_status: str = "unknown"
    expected_answer_type: str = "answerable"


@dataclass
class NotebookLMCapability:
    available: bool
    commands_checked: List[str] = field(default_factory=list)
    supports_query: bool = False
    supports_create: bool = False
    supports_import: bool = False
    blocked_reason: str = ""


def load_compare_config(path: Path) -> CompareConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    return CompareConfig(**data)


def ensure_output_dir(config: CompareConfig) -> Path:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    return out


def discover_source_files(config: CompareConfig, limit: Optional[int] = None) -> List[Path]:
    source_root = Path(config.source_root)
    files = [p for p in source_root.rglob("*") if p.is_file() and p.suffix.lower() in (SUPPORTED_TEXT_SUFFIXES | SUPPORTED_METADATA_SUFFIXES)]
    files.sort(key=lambda p: str(p).lower())
    
    if config.subset_filter != "none":
        meta_path = Path(config.output_dir) / "notebooklm_run_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                failed = meta.get("import_report", {}).get("failed_files", [])
                failed_set = set(failed)
                
                if config.subset_filter == "notebooklm_success":
                    files = [f for f in files if f.relative_to(source_root).as_posix() not in failed_set]
                elif config.subset_filter == "notebooklm_failed_excel":
                    files = [f for f in files if f.relative_to(source_root).as_posix() in failed_set and f.suffix.lower() in {".xlsx", ".xlsm", ".xls"}]
            except Exception:
                pass

    return files[:limit] if limit else files


def _safe_read_text(path: Path, max_chars: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def build_chunks_from_folder(config: CompareConfig, limit: Optional[int] = None):
    chunks = []
    source_root = Path(config.source_root)
    for path in discover_source_files(config, limit=limit):
        relative = path.relative_to(source_root).as_posix()
        if path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES:
            text = _safe_read_text(path)
            status = "ok"
        elif path.suffix.lower() in {".xlsx", ".xlsm"}:
            excel_results = _extract_excel(path)
            extracted_texts = []
            for res in excel_results:
                if res.text and res.text.strip():
                    extracted_texts.append(f"--- {res.section} ---\n{res.text}")
            if extracted_texts:
                text = "\n\n".join(extracted_texts)
                status = "extracted_success"
            else:
                text = f"Metadata-only source record for {path.name}. Relative path: {relative}. File type: {path.suffix.lower() or 'unknown'}. Raw binary content was not extracted by the MVP harness."
                status = "metadata_only"
        elif path.suffix.lower() == ".pdf":
            pdf_results = _extract_pdf(path)
            extracted_texts = []
            for res in pdf_results:
                if res.extraction_status in {"extracted", "extracted_success"} and res.text.strip():
                    extracted_texts.append(f"--- {res.section} ---\n{res.text}")
            if extracted_texts:
                text = "\n\n".join(extracted_texts)
                status = "extracted"
            else:
                text = f"Metadata-only source record for {path.name}. Relative path: {relative}. File type: {path.suffix.lower() or 'unknown'}. Raw binary content was not extracted by the MVP harness."
                status = "metadata_only"
        else:
            text = f"Metadata-only source record for {path.name}. Relative path: {relative}. File type: {path.suffix.lower() or 'unknown'}. Raw binary content was not extracted by the MVP harness."
            status = "metadata_only"
            
        if not text.strip():
            continue
        elements = build_elements_from_extracted_payload(
            source_path=str(path),
            relative_path=relative,
            source_title=path.name,
            file_type=path.suffix.lower().lstrip(".") or "text",
            text=text,
            privacy_mode=config.privacy_mode,
            extractor_name="notebooklm_compare_extractor",
            extraction_status=status,
            metadata={"benchmark_profile": "notebooklm_compare"},
        )
        chunks.extend(build_chunks_from_elements(elements, max_chars=1600))
    return chunks


def generate_questions(config: CompareConfig) -> List[CompareQuestion]:
    root = Path(config.source_root)
    files = discover_source_files(config, limit=None)
    if files:
        step = max(1, len(files) // max(1, config.question_count))
        sampled_files = files[::step][:config.question_count]
        # Pad if needed
        while len(sampled_files) < config.question_count and sampled_files:
            sampled_files.append(sampled_files[-1])
        files = sampled_files
    
    categories = [
        ("direct_lookup", "vi", "Tài liệu {name} nói gì về thông tin chính?"),
        ("procedure_step", "vi", "Các bước hoặc quy trình nào xuất hiện trong {name}?"),
        ("cause_effect", "vi", "Có nguyên nhân hoặc hệ quả nào cần chú ý trong {name}?"),
        ("evidence_sufficiency", "en", "What evidence in {name} is sufficient to support an operational action?"),
        ("cross_document_relation", "en", "How does {name} relate to another MOM/WMS document in the folder?"),
        ("unanswerable", "ja", "このフォルダの証拠だけで、存在しない承認者の最終決定を特定できますか？"),
    ]
    questions: List[CompareQuestion] = []
    
    import_status_map = {}
    meta_path = Path(config.output_dir) / "notebooklm_run_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            failed = meta.get("import_report", {}).get("failed_files", [])
            failed_set = set(failed)
            for f in files:
                try:
                    rel = f.relative_to(root).as_posix()
                    import_status_map[rel] = "FAILED_IMPORT" if rel in failed_set else "IMPORTED"
                except ValueError:
                    pass
        except Exception:
            pass

    if not files:
        if config.subset_filter != "none":
            raise ValueError("NO_VALID_SUBSET_FILES")
        files = [root / "no_supported_text_files_found.txt"]
        
    for idx in range(config.question_count):
        category, lang, template = categories[idx % len(categories)]
        source = files[idx % len(files)]
        name = source.name
        try:
            rel_path = source.relative_to(root).as_posix()
        except ValueError:
            rel_path = name
            
        expected = "insufficient" if category == "unanswerable" else "answerable"
        import_status = import_status_map.get(rel_path, "unknown")
        
        questions.append(CompareQuestion(
            question_id=f"Q{idx+1:03d}",
            question=template.format(name=name),
            category=category,
            language=lang,
            source_hint=name,
            source_relative_path=rel_path,
            source_extension=source.suffix.lower(),
            source_import_status=import_status,
            expected_answer_type=expected
        ))
    return questions


def write_questions(config: CompareConfig) -> Path:
    out = ensure_output_dir(config) / "questions.jsonl"
    questions = generate_questions(config)
    out.write_text("\n".join(json.dumps(asdict(q), ensure_ascii=False) for q in questions) + "\n", encoding="utf-8")
    return out


def read_questions(path: Path) -> List[CompareQuestion]:
    return [CompareQuestion(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_aios_answers(config: CompareConfig, questions_path: Optional[Path] = None) -> Path:
    out_dir = ensure_output_dir(config)
    q_path = questions_path or out_dir / "questions.jsonl"
    questions = read_questions(q_path) if q_path.exists() else generate_questions(config)
    chunks = build_chunks_from_folder(config)
    import sqlite3
    conn = sqlite3.connect(":memory:")
    try:
        create_rag_search_schema(conn)
        index_rag_chunks(conn, chunks)
        answers = []
        for question in questions:
            results = search_rag_chunks(conn, question.question, limit=8)
            if config.use_local_reranker:
                results = rerank_search_results(question.question, results).results
            pack = build_evidence_pack(question.question, results)
            draft = compose_answer(pack, mode="final_owner_answer")
            technical_draft = compose_local_answer(pack)
            answers.append({
                "question": asdict(question),
                "answer": answer_to_dict(draft),
                "technical_local_draft": local_answer_draft_to_dict(technical_draft),
                "evidence_pack": evidence_pack_to_dict(pack),
                "chunk_count": len(chunks),
            })
    finally:
        conn.close()
    out = out_dir / "aios_answers.jsonl"
    out.write_text("\n".join(json.dumps(a, ensure_ascii=False) for a in answers) + "\n", encoding="utf-8")
    return out


def discover_nlm_capabilities() -> NotebookLMCapability:
    commands = ["nlm --help", "nlm notebook --help", "nlm create --help", "nlm query --help", "nlm source --help"]
    checked: List[str] = []
    supports_query = supports_create = supports_import = False
    for command in commands:
        checked.append(command)
        try:
            result = subprocess.run(command.split(), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        except (OSError, subprocess.SubprocessError):
            return NotebookLMCapability(False, checked, blocked_reason="nlm command unavailable")
        output = (result.stdout or "") + (result.stderr or "")
        if "query" in output and "notebook" in output:
            supports_query = True
        if "create" in output and "notebook" in output:
            supports_create = True
        if "source" in output and ("add" in output or "import" in output or "upload" in output):
            supports_import = True
    blocked = "" if (supports_query and supports_import) else "BLOCKED_BY_NLM_CLI_LIMITATION: import/query automation not fully confirmed"
    return NotebookLMCapability(True, checked, supports_query, supports_create, supports_import, blocked)


def run_notebooklm_answers(config: CompareConfig) -> Dict[str, Any]:
    capability = discover_nlm_capabilities()
    out = ensure_output_dir(config) / "notebooklm_answers.jsonl"
    if capability.blocked_reason:
        out.write_text("", encoding="utf-8")
        return {"status": "BLOCKED_BY_NLM_CLI_LIMITATION", "capability": asdict(capability), "output_path": str(out)}
    return {"status": "READY_FOR_MANUAL_OR_EXTENDED_RUNNER", "capability": asdict(capability), "output_path": str(out)}


def _contains_any(text: str, needles: List[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _is_generic_local_draft(text: str) -> bool:
    return _contains_any(text, ["Local draft for", "This is a local evidence draft", "not a final model answer"])


def _has_empty_or_generic_sections(text: str) -> bool:
    lowered = text.lower()
    if "bằng chứng chính" in lowered and re.search(r"bằng chứng chính\s*(?:\n\s*){0,2}(?:##|$)", lowered):
        return True
    return any(phrase in lowered for phrase in [
        "phân tích\n\ndựa trên bằng chứng",
        "phân tích: dựa trên bằng chứng",
        "việc cần làm tiếp\n\nchạy audit",
        "việc cần làm tiếp: chạy audit",
    ])


def _is_evidence_only_snippet_list(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullet_lines = [line for line in lines if line.startswith(("-", "*"))]
    citation_lines = [line for line in lines if "[E" in line or re.search(r"\[\d+\]", line)]
    has_synthesis_sections = any(h in text for h in ["Kết luận ngắn", "Cách hiểu từ bằng chứng", "Hướng xử lý / kiểm tra"])
    return len(citation_lines) >= 2 and len(bullet_lines) >= 2 and not has_synthesis_sections


def _needs_concrete_steps(question: str) -> bool:
    return _contains_any(question, ["troubleshooting", "điều tra", "next actions", "handover", "bàn giao", "missing evidence", "kiểm tra", "hướng xử lý"])


def _has_concrete_steps(text: str) -> bool:
    return bool(re.search(r"(?:^|\n)\s*(?:\d+\.|-\s*(?:kiểm tra|xác nhận|đối chiếu|thu|dựng|bàn giao))", text.lower()))


def _citations_support_claims(text: str, has_citations: bool) -> bool:
    if not has_citations:
        return False
    claim_lines = [line for line in text.splitlines() if "[E" in line and len(line.strip()) > 25]
    return any(not line.strip().startswith(("| [E", "- [E")) or "vì sao quan trọng" in line.lower() for line in claim_lines)


def _apply_score_cap(scores: Dict[str, Any], cap: int, reason: str) -> None:
    scores.setdefault("caps_applied", []).append({"cap": cap, "reason": reason})
    scores["max_total_score"] = min(scores.get("max_total_score", 12), cap)


def _score_pair(aios: Dict[str, Any], nlm: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    answer = aios.get("answer", {})
    question = aios.get("question", {}).get("question", "")
    answer_text = answer.get("answer_text", "") or ""
    answer_kind = answer.get("answer_kind", "local_evidence_draft")
    metadata = answer.get("metadata", {})
    answer_profile = normalize_profile_id(metadata.get("answer_profile", ""))
    source_type_pass = answer.get("metadata", {}).get("source_type_pass", "PASS")
    domain_playbook = metadata.get("domain_playbook", GENERAL_PLAYBOOK)
    expected_domain_playbook = metadata.get("expected_domain_playbook", "")
    human_override = str(metadata.get("human_override", "")).lower() == "true"

    has_citations = bool(answer.get("citation_ids"))
    insufficient = bool(answer.get("insufficient_evidence"))
    citation_supported = _citations_support_claims(answer_text, has_citations)
    is_metadata_only = insufficient and not citation_supported

    scores: Dict[str, Any] = {
        "answer_relevance": 2 if answer_text and not is_metadata_only else 0,
        "citation_usefulness": 2 if citation_supported else (1 if has_citations else 0),
        "source_traceability": 2 if citation_supported else (1 if has_citations else 0),
        "completeness": 1 if insufficient else 2,
        "insufficient_evidence_honesty": 3 if insufficient else 2,
        "privacy_local_control": 3,
        "practical_usefulness": 2 if answer_text and _has_concrete_steps(answer_text) and not is_metadata_only else (1 if answer_text and not is_metadata_only else 0),
        "hallucination_risk": 3 if insufficient else 2,
        "max_total_score": 12,
        "caps_applied": [],
    }

    if _is_generic_local_draft(answer_text) or answer_kind == "local_evidence_draft":
        _apply_score_cap(scores, 6, "generic/local draft marker is not a final answer")
    if _has_empty_or_generic_sections(answer_text):
        scores["practical_usefulness"] = min(scores["practical_usefulness"], 1)
        scores["answer_relevance"] = min(scores["answer_relevance"], 1)
        _apply_score_cap(scores, 7, "empty or generic answer sections")
    if _is_evidence_only_snippet_list(answer_text):
        _apply_score_cap(scores, 7, "evidence-only snippet list without synthesis")
    if _needs_concrete_steps(question) and not _has_concrete_steps(answer_text):
        _apply_score_cap(scores, 6, "question needs troubleshooting/handover steps but answer has none")
    if has_citations and not citation_supported:
        scores["source_traceability"] = min(scores["source_traceability"], 1)
        scores["citation_usefulness"] = min(scores["citation_usefulness"], 1)
        _apply_score_cap(scores, 7, "citations only in source table")

    # New caps based on answer profile and source routing
    q_lower = question.lower()
    ans_lower = answer_text.lower()
    
    is_process_q = any(k in q_lower for k in ["process", "quy trﾃｬnh", "quy trình", "automatic/manual", "boundary", "troubleshooting", "ﾄ訴盻「 tra", "điều tra"])
    if is_process_q and answer_profile in {"extract_fields", "table_question"}:
        _apply_score_cap(scores, 6, "process question answered as table mapping")
        
    if answer_profile.startswith("image_") and "schema/html" in ans_lower and "directly visible" not in ans_lower:
        _apply_score_cap(scores, 5, "screenshot question using HTML primary evidence")
        
    if answer_profile in {"extract_fields", "table_question"}:
        if not any(k in ans_lower for k in ["trﾆｰ盻拵g", "trường", "field", "column", "cột", "key", "khﾃｳa", "khóa", "mapping", "table", "b蘯｣ng"]):
            _apply_score_cap(scores, 6, "no concrete field/table/key extraction for Excel mapping")
            
    if source_type_pass == "FAIL":
        _apply_score_cap(scores, 6, "target source type unavailable")
    elif source_type_pass == "PARTIAL":
        if not human_override:
            _apply_score_cap(scores, 8, "source routing is PARTIAL")
        if "cannot conclude fully" not in ans_lower and "không thể kết luận đầy đủ" not in ans_lower and "khong the ket luan day du" not in ans_lower:
            _apply_score_cap(scores, 6, "target source type partially unavailable and answer does not admit missing evidence")

    if expected_domain_playbook and domain_playbook != expected_domain_playbook:
        _apply_score_cap(scores, 6, "answer used the wrong domain playbook")

    if domain_playbook == GENERAL_PLAYBOOK and text_has_manufacturing_terms(answer_text):
        _apply_score_cap(scores, 6, "manufacturing playbook language appeared in general-domain answer")

    if domain_playbook == MANUFACTURING_PLAYBOOK and expected_domain_playbook == GENERAL_PLAYBOOK:
        _apply_score_cap(scores, 6, "manufacturing playbook used for a general-domain question")

    if str(metadata.get("side_by_side_status", "")).upper() == "HUMAN_REVIEW":
        _apply_score_cap(scores, 8, "side-by-side HUMAN_REVIEW is not a pass/win signal")

    if source_type_pass != "PASS" or insufficient or not citation_supported or _is_generic_local_draft(answer_text):
        _apply_score_cap(scores, 9, "score 10 requires direct answer, correct primary evidence, concrete facts, claim citations, and no undermining missing-evidence warning")

    raw_total = sum(scores[k] for k in ["answer_relevance", "citation_usefulness", "source_traceability", "completeness", "practical_usefulness"])
    scores["total_score_12"] = min(raw_total, scores["max_total_score"])

    if answer_kind == "local_evidence_draft":
        winner = "notebooklm" if nlm else "aios_draft_only"
        reason = "Local evidence draft is not a final answer competitor; score caps apply."
    else:
        winner = "human_review_required" if nlm else "aios_only_no_notebooklm_answer"
        reason = f"Strict heuristic quality score with hard caps; {answer_kind} vs NotebookLM answer."
    scores["winner"] = winner
    scores["reason"] = reason
    return scores

def evaluate_answers(config: CompareConfig) -> Dict[str, Path]:
    out_dir = ensure_output_dir(config)
    aios_path = out_dir / "aios_answers.jsonl"
    nlm_path = out_dir / "notebooklm_answers.jsonl"
    aios_rows = [json.loads(line) for line in aios_path.read_text(encoding="utf-8").splitlines() if line.strip()] if aios_path.exists() else []
    nlm_rows = [json.loads(line) for line in nlm_path.read_text(encoding="utf-8").splitlines() if line.strip()] if nlm_path.exists() else []
    evaluations = []
    for index, row in enumerate(aios_rows):
        nlm = nlm_rows[index] if index < len(nlm_rows) else None
        evaluations.append({"question_id": row["question"]["question_id"], "scores": _score_pair(row, nlm), "requires_human_review": True})
    summary = {
        "status": "PASS_CANDIDATE" if evaluations else "NO_EVALUATION",
        "comparison_mode": "local_draft_vs_notebooklm_answer",
        "warning": "This comparison checks retrieval/extraction coverage, not final answer quality.",
        "note": "PASS_CANDIDATE only means deterministic self-eval ran; human review is required before any parity claim.",
        "question_count": len(evaluations),
        "aios_local_drafts": len(aios_rows),
        "notebooklm_answers": len(nlm_rows),
        "evaluations": evaluations,
    }
    json_path = out_dir / "evaluation.json"
    md_path = out_dir / "evaluation_report.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(f"# AIOS vs NotebookLM MVP Evaluation\n\nStatus: {summary['status']}\n\nWARNING: {summary['warning']}\n\n{summary['note']}\n\nQuestions: {len(evaluations)}\nAIOS local drafts: {len(aios_rows)}\nNotebookLM answers: {len(nlm_rows)}\n", encoding="utf-8")
    return {"json": json_path, "md": md_path}


def write_redacted_summary(config: CompareConfig, notebooklm_status: str) -> Path:
    out_dir = ensure_output_dir(config)
    q = out_dir / "questions.jsonl"
    a = out_dir / "aios_answers.jsonl"
    n = out_dir / "notebooklm_answers.jsonl"
    e = out_dir / "evaluation.json"
    def count(path: Path) -> int:
        return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]) if path.exists() else 0
    text = f"""# NotebookLM Compare Summary\n\n- Questions: {count(q)}\n- AIOS local drafts: {count(a)}\n- NotebookLM answers: {count(n)}\n- NotebookLM status: {notebooklm_status}\n- Parity claimed: NO\n- PASS_CANDIDATE means self-evaluation only; human review is required.\n"""
    path = Path(".ai/NOTEBOOKLM_COMPARE_SUMMARY.md")
    path.write_text(text, encoding="utf-8")
    return path


def print_local_review(config: CompareConfig, output_path: Optional[str] = None) -> None:
    out_dir = ensure_output_dir(config)
    q_path = out_dir / "questions.jsonl"
    a_path = out_dir / "aios_answers.jsonl"
    n_path = out_dir / "notebooklm_answers.jsonl"
    
    questions = [json.loads(line) for line in q_path.read_text(encoding="utf-8").splitlines() if line.strip()] if q_path.exists() else []
    aios_rows = [json.loads(line) for line in a_path.read_text(encoding="utf-8").splitlines() if line.strip()] if a_path.exists() else []
    nlm_rows = [json.loads(line) for line in n_path.read_text(encoding="utf-8").splitlines() if line.strip()] if n_path.exists() else []

    lines = []
    
    for i, q in enumerate(questions):
        q_id = q.get("question_id")
        q_text = q.get("question")
        
        aios_row = next((r for r in aios_rows if r.get("question", {}).get("question_id") == q_id), None)
        nlm_row = next((r for r in nlm_rows if r.get("question_id") == q_id), None)
        
        if not aios_row: continue
        
        aios_ans = aios_row.get("answer", {}).get("answer_text", "")
        insufficient = "YES" if aios_row.get("answer", {}).get("insufficient_evidence") else "NO"
        quality = aios_row.get("evidence_pack", {}).get("evidence_quality", "unknown")
        
        nlm_ans = nlm_row.get("answer", "") if nlm_row else "Không có kết quả"
        
        lines.append(f"Q {q_id}")
        lines.append(f"Question: {q_text}")
        lines.append(f"AIOS local evidence draft:\n{aios_ans}")
        lines.append(f"NotebookLM answer:\n{nlm_ans}")
        lines.append(f"AIOS insufficient evidence: {insufficient}")
        lines.append(f"Evidence quality: {quality}")
        lines.append("Owner decision fields blank")
        lines.append("-" * 40)
        
    text = "\n".join(lines)
    print(text)
    
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
