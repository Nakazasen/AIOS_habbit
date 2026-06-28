from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from aios_habit.rag_answer_composer import compose_local_answer, local_answer_draft_to_dict
from aios_habit.rag_evidence import build_evidence_pack, evidence_pack_to_dict
from aios_habit.rag_ingest import build_chunks_from_elements, build_elements_from_extracted_payload
from aios_habit.rag_rerank import rerank_search_results
from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks, search_rag_chunks

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
        else:
            text = f"Metadata-only source record for {path.name}. Relative path: {relative}. File type: {path.suffix.lower() or 'unknown'}. Raw binary content was not extracted by the MVP harness."
        if not text.strip():
            continue
        elements = build_elements_from_extracted_payload(
            source_path=str(path),
            relative_path=relative,
            source_title=path.name,
            file_type=path.suffix.lower().lstrip(".") or "text",
            text=text,
            privacy_mode=config.privacy_mode,
            extractor_name="notebooklm_compare_text_reader",
            extraction_status="ok",
            metadata={"benchmark_profile": "notebooklm_compare"},
        )
        chunks.extend(build_chunks_from_elements(elements, max_chars=1600))
    return chunks


def generate_questions(config: CompareConfig) -> List[CompareQuestion]:
    root = Path(config.source_root)
    files = discover_source_files(config, limit=max(1, config.question_count))
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
            draft = compose_local_answer(pack)
            answers.append({
                "question": asdict(question),
                "answer": local_answer_draft_to_dict(draft),
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


def _score_pair(aios: Dict[str, Any], nlm: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    answer = aios.get("answer", {})
    has_citations = bool(answer.get("citation_ids"))
    insufficient = bool(answer.get("insufficient_evidence"))
    return {
        "answer_relevance": 2 if answer.get("answer_text") else 0,
        "citation_usefulness": 2 if has_citations else 1,
        "source_grounding": 2 if has_citations else 1,
        "completeness": 1 if insufficient else 2,
        "insufficient_evidence_honesty": 3 if insufficient else 2,
        "privacy_local_control": 3,
        "actionability_for_owner": 2 if answer.get("answer_text") else 0,
        "hallucination_risk": 3 if insufficient else 2,
        "winner": "human_review_required" if nlm else "aios_only_no_notebooklm_answer",
        "reason": "Deterministic heuristic self-eval; NotebookLM answer missing or manual review required.",
    }


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
        "note": "PASS_CANDIDATE only means deterministic self-eval ran; human review is required before any parity claim.",
        "question_count": len(evaluations),
        "aios_answers": len(aios_rows),
        "notebooklm_answers": len(nlm_rows),
        "evaluations": evaluations,
    }
    json_path = out_dir / "evaluation.json"
    md_path = out_dir / "evaluation_report.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(f"# AIOS vs NotebookLM MVP Evaluation\n\nStatus: {summary['status']}\n\n{summary['note']}\n\nQuestions: {len(evaluations)}\nAIOS answers: {len(aios_rows)}\nNotebookLM answers: {len(nlm_rows)}\n", encoding="utf-8")
    return {"json": json_path, "md": md_path}


def write_redacted_summary(config: CompareConfig, notebooklm_status: str) -> Path:
    out_dir = ensure_output_dir(config)
    q = out_dir / "questions.jsonl"
    a = out_dir / "aios_answers.jsonl"
    n = out_dir / "notebooklm_answers.jsonl"
    e = out_dir / "evaluation.json"
    def count(path: Path) -> int:
        return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]) if path.exists() else 0
    text = f"""# NotebookLM Compare Summary\n\n- Questions: {count(q)}\n- AIOS answers: {count(a)}\n- NotebookLM answers: {count(n)}\n- NotebookLM status: {notebooklm_status}\n- Parity claimed: NO\n- PASS_CANDIDATE means self-evaluation only; human review is required.\n"""
    path = Path(".ai/NOTEBOOKLM_COMPARE_SUMMARY.md")
    path.write_text(text, encoding="utf-8")
    return path
