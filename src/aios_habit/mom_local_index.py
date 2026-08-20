from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional

import pandas as pd

from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_store import save_case, save_evidence
from aios_habit.document_extractors import USABLE_STATUSES, extract_text_chunks_from_file, is_potentially_extractable
from aios_habit.real_doc_inventory import MOM_RUNTIME_DIR, SUPPORTED_TEXT_EXTS, SUPPORTED_TABLE_EXTS, ensure_mom_runtime_dir

INDEX_FILE = MOM_RUNTIME_DIR / "mom_local_index.jsonl"
BENCHMARK_QUESTIONS_FILE = MOM_RUNTIME_DIR / "benchmark_questions.json"
MAX_TEXT_FILE_CHARS = 40000
CHUNK_SIZE = 1200
MAX_CHUNKS_PER_FILE = 30
MAX_EXCEL_ROWS_PER_SHEET = 25
MAX_EXCEL_SHEETS = 12
PREVIEW_CHARS = 320


@dataclass
class MomChunk:
    chunk_id: str
    source_file: str
    relative_path: str
    file_type: str
    text: str
    preview: str
    privacy_level: str
    source_hash: str
    section: str = ""
    sheet: str = ""
    row_range: str = ""
    page: str = ""
    slide: str = ""
    extractor_name: str = "mom_local_index"
    extraction_status: str = "extracted_success"
    warning: str = ""
    ocr_engine: str = ""
    ocr_lang: str = ""
    ocr_confidence: float | None = None
    ocr_confidence_samples: int = 0
    ocr_preprocessing: str = ""
    ocr_attempts: int = 0
    ocr_quality_reason: str = ""
    element_type: str = ""
    indexed_at: str = ""


@dataclass
class MomSearchHit:
    chunk: MomChunk
    score: float
    matched_terms: list[str]


@dataclass
class MomIndexBuildResult:
    root_path: str
    root_exists: bool
    index_path: str
    files_seen: int
    chunks_generated: int
    unsupported_files: list[dict[str, Any]]
    errors: list[dict[str, str]]
    privacy_level: str = "local_only"


def _sha256_short(path: Path, max_bytes: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        remaining = max_bytes
        while remaining > 0:
            chunk = f.read(min(65536, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()[:16]


_WORD_RE = re.compile(r"[a-zA-Z0-9_À-ỹ]+", re.UNICODE)
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]+")


def _tokens(text: str) -> list[str]:
    """Tokenize text into lower-case alphanumeric words, underscore subterms, and CJK n-grams."""
    if not text:
        return []
    text_lower = text.lower()
    tokens: list[str] = []
    for match in _WORD_RE.finditer(text_lower):
        word = match.group(0)
        tokens.append(word)
        if "_" in word:
            for part in word.split("_"):
                if part and part != word:
                    tokens.append(part)
    for match in _CJK_RE.finditer(text_lower):
        cjk_str = match.group(0)
        for ch in cjk_str:
            tokens.append(ch)
        if len(cjk_str) >= 2:
            for i in range(len(cjk_str) - 1):
                tokens.append(cjk_str[i : i + 2])
        if len(cjk_str) >= 3:
            for i in range(len(cjk_str) - 2):
                tokens.append(cjk_str[i : i + 3])
        if len(cjk_str) >= 4:
            tokens.append(cjk_str)
    return tokens


def _safe_preview(text: str, limit: int = PREVIEW_CHARS) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _chunk_text(text: str, base: dict[str, Any], max_chunks: int = MAX_CHUNKS_PER_FILE) -> Iterable[MomChunk]:
    clean = text.strip()
    if not clean:
        return
    now = datetime.now().isoformat()
    for idx, start in enumerate(range(0, len(clean), CHUNK_SIZE)):
        if idx >= max_chunks:
            break
        part = clean[start:start + CHUNK_SIZE]
        yield MomChunk(
            chunk_id=f"MOM-{base['source_hash']}-CH{idx:03d}",
            source_file=base["source_file"],
            relative_path=base["relative_path"],
            file_type=base["file_type"],
            text=part,
            preview=_safe_preview(part),
            privacy_level="local_only",
            source_hash=base["source_hash"],
            section=base.get("section", f"chars {start}-{start + len(part)}"),
            sheet=base.get("sheet", ""),
            row_range=base.get("row_range", ""),
            page=base.get("page", ""),
            slide=base.get("slide", ""),
            extractor_name=base.get("extractor_name", "mom_local_index"),
            extraction_status=base.get("extraction_status", "extracted_success"),
            warning=base.get("warning", ""),
            ocr_engine=base.get("ocr_engine", ""),
            ocr_lang=base.get("ocr_lang", ""),
            ocr_confidence=base.get("ocr_confidence"),
            ocr_confidence_samples=int(base.get("ocr_confidence_samples", 0) or 0),
            ocr_preprocessing=base.get("ocr_preprocessing", ""),
            ocr_attempts=int(base.get("ocr_attempts", 0) or 0),
            ocr_quality_reason=base.get("ocr_quality_reason", ""),
            element_type=base.get("element_type", ""),
            indexed_at=now,
        )


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT_FILE_CHARS]


def _read_csv_file(path: Path) -> str:
    lines: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if idx >= 200:
                break
            lines.append(" | ".join(str(cell) for cell in row))
    return "\n".join(lines)[:MAX_TEXT_FILE_CHARS]


def _excel_chunks(path: Path, base: dict[str, Any]) -> list[MomChunk]:
    chunks: list[MomChunk] = []
    try:
        xls = pd.ExcelFile(path)
        for sheet in xls.sheet_names[:MAX_EXCEL_SHEETS]:
            df = pd.read_excel(xls, sheet_name=sheet, nrows=MAX_EXCEL_ROWS_PER_SHEET)
            text = f"Excel sheet: {sheet}\nColumns: {', '.join(map(str, df.columns))}\n" + df.to_string(index=False)
            sheet_base = dict(base)
            sheet_base["sheet"] = sheet
            sheet_base["section"] = f"sheet {sheet} preview"
            sheet_base["row_range"] = f"1-{min(len(df), MAX_EXCEL_ROWS_PER_SHEET)}"
            sheet_base["extractor_name"] = "pandas"
            sheet_base["extraction_status"] = "extracted_success"
            for chunk in _chunk_text(text, sheet_base, max_chunks=3):
                chunks.append(chunk)
    except Exception as exc:
        raise RuntimeError(f"excel read failed: {exc}") from exc
    return chunks


def _extractor_chunks(path: Path, base: dict[str, Any], root: Path) -> tuple[list[MomChunk], list[dict[str, Any]]]:
    chunks: list[MomChunk] = []
    unsupported: list[dict[str, Any]] = []
    extracted = extract_text_chunks_from_file(path, root=root, max_chars_per_chunk=CHUNK_SIZE)
    for item in extracted:
        status = str(item.get("extraction_status") or "unsupported_no_local_tool")
        if status not in USABLE_STATUSES or not str(item.get("text") or "").strip():
            unsupported.append({
                "relative_path": item.get("relative_path") or base["relative_path"],
                "file_type": item.get("file_type") or base["file_type"],
                "reason": item.get("warning") or f"extractor status: {status}",
                "privacy_level": "local_only",
                "extractor_name": item.get("extractor_name", "document_extractors"),
                "extraction_status": status,
                "ocr_engine": item.get("ocr_engine", ""),
                "ocr_lang": item.get("ocr_lang", ""),
                "ocr_confidence": item.get("ocr_confidence"),
                "ocr_preprocessing": item.get("ocr_preprocessing", ""),
                "ocr_quality_reason": item.get("ocr_quality_reason", ""),
                "page": item.get("page", ""),
                "element_type": item.get("element_type", ""),
            })
            continue
        chunk_base = dict(base)
        chunk_base.update({
            "section": item.get("section", ""),
            "sheet": item.get("sheet", ""),
            "row_range": item.get("row_range", ""),
            "page": item.get("page", ""),
            "slide": item.get("slide", ""),
            "extractor_name": item.get("extractor_name", "document_extractors"),
            "extraction_status": status,
            "warning": item.get("warning", ""),
            "ocr_engine": item.get("ocr_engine", ""),
            "ocr_lang": item.get("ocr_lang", ""),
            "ocr_confidence": item.get("ocr_confidence"),
            "ocr_confidence_samples": item.get("ocr_confidence_samples", 0),
            "ocr_preprocessing": item.get("ocr_preprocessing", ""),
            "ocr_attempts": item.get("ocr_attempts", 0),
            "ocr_quality_reason": item.get("ocr_quality_reason", ""),
            "element_type": item.get("element_type", ""),
        })
        chunks.extend(list(_chunk_text(str(item.get("text") or ""), chunk_base, max_chunks=1)))
    return chunks, unsupported


def build_mom_local_index(root_path: str | Path, write_runtime: bool = True) -> MomIndexBuildResult:
    root = Path(root_path)
    root_exists = root.exists() and root.is_dir()
    ensure_mom_runtime_dir()
    chunks: list[MomChunk] = []
    unsupported: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    files_seen = 0

    if root_exists:
        root_resolved = root.resolve()
        for path in sorted(root_resolved.rglob("*"), key=lambda p: str(p).lower()):
            if not path.is_file():
                continue
            files_seen += 1
            rel = path.relative_to(root_resolved).as_posix()
            ext = path.suffix.lower()
            try:
                source_hash = _sha256_short(path)
                base = {
                    "source_file": path.name,
                    "relative_path": rel,
                    "file_type": ext or "[no_ext]",
                    "source_hash": source_hash,
                }
                if ext in {".txt", ".md", ".markdown", ".json"}:
                    text = _read_text_file(path)
                    base["extraction_status"] = "extracted_success"
                    chunks.extend(list(_chunk_text(text, base)))
                elif ext == ".csv":
                    text = _read_csv_file(path)
                    base["extraction_status"] = "extracted_success"
                    chunks.extend(list(_chunk_text(text, base)))
                elif ext in SUPPORTED_TABLE_EXTS and ext != ".xlsm":
                    chunks.extend(_excel_chunks(path, base))
                elif is_potentially_extractable(ext):
                    extracted_chunks, extractor_unsupported = _extractor_chunks(path, base, root_resolved)
                    chunks.extend(extracted_chunks)
                    unsupported.extend(extractor_unsupported)
                else:
                    reason = "unsupported file type"
                    if ext in {".doc", ".docx"}:
                        reason = "doc/docx extraction not enabled for MOM pilot"
                    unsupported.append({"relative_path": rel, "file_type": ext or "[no_ext]", "reason": reason, "privacy_level": "local_only"})
            except Exception as exc:
                errors.append({"relative_path": rel, "error": str(exc)})

    if write_runtime:
        with INDEX_FILE.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    return MomIndexBuildResult(
        root_path=str(root),
        root_exists=root_exists,
        index_path=str(INDEX_FILE),
        files_seen=files_seen,
        chunks_generated=len(chunks),
        unsupported_files=unsupported,
        errors=errors,
    )


def load_mom_chunks(index_path: str | Path = INDEX_FILE) -> list[MomChunk]:
    path = Path(index_path)
    if not path.exists():
        return []
    chunks: list[MomChunk] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                chunks.append(MomChunk(**json.loads(line)))
            except Exception:
                continue
    return chunks


def search_mom_index(query: str, limit: int = 5, index_path: str | Path = INDEX_FILE) -> list[MomSearchHit]:
    """Search MOM local index using an objective in-memory BM25 ranking algorithm.

    Features:
    - CJK n-gram sub-tokenization and standard alphanumeric word tokenization.
    - Standard BM25 IDF: log(1 + (N - df + 0.5) / (df + 0.5)).
    - Document length normalization: tf / (tf + k1 * (1 - b + b * (doc_len / avg_doc_len))) (k1=1.5, b=0.75).
    - Domain-neutral exact phrase boost and metadata / title weighting.
    - Strictly non-negative score calculation.
    """
    q = query.strip().lower()
    if not q:
        return []
    query_terms = _tokens(q)
    if not query_terms:
        return []

    chunks = load_mom_chunks(index_path)
    if not chunks:
        return []

    query_term_set = set(query_terms)
    n_docs = len(chunks)

    # Pre-tokenize all chunks and collect document frequencies (df)
    doc_data: list[dict[str, Any]] = []
    df: dict[str, int] = {}
    total_doc_len = 0

    for chunk in chunks:
        body_text = f"{chunk.text} {chunk.preview}"
        meta_text = f"{chunk.source_file} {chunk.relative_path} {chunk.sheet} {chunk.section}"
        haystack = f"{meta_text}\n{body_text}".lower()

        body_tokens = _tokens(body_text)
        meta_tokens = _tokens(meta_text)

        body_tf: dict[str, int] = {}
        for token in body_tokens:
            body_tf[token] = body_tf.get(token, 0) + 1

        meta_tf: dict[str, int] = {}
        for token in meta_tokens:
            meta_tf[token] = meta_tf.get(token, 0) + 1

        doc_len = len(body_tokens) + 2 * len(meta_tokens)
        total_doc_len += doc_len

        all_doc_terms = set(body_tf.keys()) | set(meta_tf.keys())
        for term in query_term_set:
            if term in all_doc_terms:
                df[term] = df.get(term, 0) + 1

        doc_data.append({
            "chunk": chunk,
            "body_tf": body_tf,
            "meta_tf": meta_tf,
            "doc_len": doc_len,
            "haystack": haystack,
        })

    avg_doc_len = max(1.0, total_doc_len / max(1, n_docs))
    k1 = 1.5
    b = 0.75

    # Standard BM25 IDF
    idf: dict[str, float] = {}
    for term in query_term_set:
        doc_freq = df.get(term, 0)
        idf[term] = math.log(1.0 + (n_docs - doc_freq + 0.5) / (doc_freq + 0.5))

    hits: list[MomSearchHit] = []

    for item in doc_data:
        chunk: MomChunk = item["chunk"]
        body_tf: dict[str, int] = item["body_tf"]
        meta_tf: dict[str, int] = item["meta_tf"]
        doc_len: int = item["doc_len"]
        haystack: str = item["haystack"]

        score = 0.0
        matched: list[str] = []
        matched_distinct_terms = 0

        for term in query_term_set:
            tf_b = body_tf.get(term, 0)
            tf_m = meta_tf.get(term, 0)
            tf_eff = tf_b + 2.5 * tf_m
            if tf_eff > 0:
                matched.append(term)
                matched_distinct_terms += 1
                tf_norm = (tf_eff * (k1 + 1.0)) / (tf_eff + k1 * (1.0 - b + b * (doc_len / avg_doc_len)))
                term_score = (1.0 + idf[term]) * tf_norm
                score += term_score

        # Domain-neutral exact phrase boost
        if q in haystack and len(q) >= 2:
            score += 10.0
            matched.append(q)

        # Multi-word phrase matching for sub-phrases
        words = [w for w in q.split() if len(w) >= 2]
        if len(words) >= 2:
            for i in range(len(words) - 1):
                two_word = f"{words[i]} {words[i+1]}"
                if two_word in haystack:
                    score += 2.0
                    matched.append(two_word)

        # Term coverage weighting
        if query_term_set:
            coverage = matched_distinct_terms / len(query_term_set)
            score *= (0.5 + 0.5 * coverage)

        score = max(0.0, round(score, 4))
        if score > 0.0:
            hits.append(MomSearchHit(chunk=chunk, score=score, matched_terms=sorted(set(matched))))

    hits.sort(key=lambda h: h.score, reverse=True)
    diversified: list[MomSearchHit] = []
    seen_files: set[str] = set()
    seen_previews: set[str] = set()
    for hit in hits:
        preview_key = re.sub(r"\s+", " ", hit.chunk.preview.lower())[:160]
        if preview_key in seen_previews:
            continue
        if hit.chunk.relative_path not in seen_files:
            diversified.append(hit)
            seen_files.add(hit.chunk.relative_path)
            seen_previews.add(preview_key)
        if len(diversified) >= limit:
            return diversified
    for hit in hits:
        preview_key = re.sub(r"\s+", " ", hit.chunk.preview.lower())[:160]
        if preview_key in seen_previews:
            continue
        diversified.append(hit)
        seen_previews.add(preview_key)
        if len(diversified) >= limit:
            break
    return diversified


def build_mom_qa_prompt(question: str, hits: list[MomSearchHit], min_score: float = 1.0) -> dict[str, Any]:
    usable = [h for h in hits if h.score >= min_score]
    source_refs = []
    lines = []
    for i, hit in enumerate(usable, 1):
        chunk = hit.chunk
        ref = f"{chunk.relative_path}#{chunk.chunk_id}"
        source_refs.append({
            "chunk_id": chunk.chunk_id,
            "relative_path": chunk.relative_path,
            "source_file": chunk.source_file,
            "sheet": chunk.sheet,
            "section": chunk.section,
            "score": hit.score,
            "privacy_level": chunk.privacy_level,
            "file_type": chunk.file_type,
            "page": chunk.page,
            "slide": chunk.slide,
            "extractor_name": chunk.extractor_name,
            "extraction_status": chunk.extraction_status,
            "ocr_engine": chunk.ocr_engine,
        })
        lines.append(
            f"[Nguồn {i}] {ref} | score={hit.score:.1f} | privacy=local_only\n"
            f"Preview: {chunk.preview}"
        )

    insufficient = not usable
    context = "\n\n".join(lines) if lines else "Không tìm thấy nguồn MOM local đủ khớp."
    source_coverage = {
        "source_count": len(source_refs),
        "files": sorted({ref["relative_path"] for ref in source_refs}),
        "file_types": sorted({ref["file_type"] for ref in source_refs}),
        "has_ocr": any(ref["extraction_status"].startswith("ocr") for ref in source_refs),
    }
    prompt = (
        "Bạn là AIOS WorkLens phân tích tài liệu MOM local-only.\n"
        "Không gửi nội dung này lên cloud nếu chưa có phê duyệt privacy rõ ràng.\n\n"
        f"Câu hỏi nghiệp vụ MOM: {question}\n\n"
        "Nguồn MOM local được phép dùng:\n"
        f"{context}\n\n"
        "Yêu cầu trả lời theo cấu trúc bắt buộc:\n"
        "1. Confirmed by source: nêu các điểm được xác nhận, mỗi điểm kèm relative_path và chunk_id.\n"
        "2. Not found / insufficient evidence: nêu rõ phần chưa thấy trong nguồn; nếu thiếu thì nói 'chưa đủ bằng chứng'.\n"
        "3. Next checks: đề xuất kiểm tra tiếp trên file/sheet/page/slide liên quan.\n"
        "4. Source coverage: tóm tắt số nguồn, loại file, OCR/text-layer nếu có.\n"
        "5. Không bịa field/process, không kết luận vượt quá nguồn, không dùng NotebookLM làm ground truth.\n"
    )
    return {
        "question": question,
        "prompt": prompt,
        "source_refs": source_refs,
        "insufficient_evidence": insufficient,
        "privacy_level": "local_only",
        "source_coverage": source_coverage,
        "answer_discipline": {
            "confirmed_by_source_required": True,
            "insufficient_evidence_required": True,
            "next_checks_required": True,
            "notebooklm_comparator_not_ground_truth": True,
        },
        "cloud_warning": "Dữ liệu MOM local_only: không tự gửi lên cloud/NotebookLM.",
    }


def create_mom_case_from_hit(question: str, hit: MomSearchHit, workspace_id: str = "default") -> dict[str, Any]:
    case_id = f"CASE-MOM-{uuid.uuid4().hex[:8].upper()}"
    evidence_id = f"EVID-MOM-{uuid.uuid4().hex[:8].upper()}"
    chunk = hit.chunk
    case = Case(
        case_id=case_id,
        title=f"MOM draft: {question[:80]}",
        status="open",
        priority="normal",
        current_situation=(
            "Draft case tạo từ kết quả tìm kiếm tài liệu MOM local-only. "
            f"Nguồn: {chunk.relative_path}#{chunk.chunk_id}. Cần review trước khi kết luận."
        ),
        privacy_level="local_only",
        workspace_id=workspace_id,
        source_origin="mom_official_local",
        verification_status="draft",
    )
    evidence = EvidenceItem(
        evidence_id=evidence_id,
        case_id=case_id,
        source_type="mom_local_chunk",
        source_path=f"{chunk.relative_path}#{chunk.chunk_id}",
        title=f"MOM source: {chunk.source_file}",
        extracted_text=chunk.preview,
        structured_summary=f"Score={hit.score:.1f}; sheet={chunk.sheet}; section={chunk.section}",
        confidence="low",
        privacy_level="local_only",
        review_status="raw",
        source_origin="mom_official_local",
        verification_status="draft",
    )
    case.evidence_items = [evidence_id]
    save_case(case)
    save_evidence(evidence)
    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "source_ref": evidence.source_path,
        "privacy_level": "local_only",
        "source_origin": "mom_official_local",
        "verification_status": "draft",
    }


def generate_safe_benchmark_questions(chunks: Optional[list[MomChunk]] = None, limit: int = 12) -> list[dict[str, str]]:
    templates = [
        "Quy trình đăng ký lịch sử sản xuất gồm những bước chính nào?",
        "Interface specification mô tả input/output fields nào?",
        "Điều kiện bắt buộc trước khi đăng ký production history là gì?",
        "Các điểm xác nhận/confirmation points trong quy trình là gì?",
        "Nếu thiếu bằng chứng từ tài liệu, AIOS nên kiểm tra tiếp nguồn nào?",
        "MOM và WMS tương tác ở điểm nào trong luồng được mô tả?",
        "Tài liệu có mô tả error handling hoặc response lỗi không?",
        "Các trường dữ liệu nào liên quan đến production result/history?",
        "Có mapping hoặc format nào cần lưu ý khi gọi interface không?",
        "Luồng xử lý sau khi đăng ký thành công là gì?",
    ]
    questions = [{"question_id": f"MOM-Q{i+1:02d}", "question": q, "privacy_level": "local_only"} for i, q in enumerate(templates[:limit])]
    if chunks:
        seen_files = []
        for chunk in chunks:
            if chunk.relative_path not in seen_files:
                seen_files.append(chunk.relative_path)
            if len(seen_files) >= 3:
                break
        for rel in seen_files:
            if len(questions) >= limit:
                break
            questions.append({
                "question_id": f"MOM-Q{len(questions)+1:02d}",
                "question": f"Tài liệu {Path(rel).name} cung cấp thông tin nghiệp vụ chính nào?",
                "privacy_level": "local_only",
            })
    ensure_mom_runtime_dir()
    BENCHMARK_QUESTIONS_FILE.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    return questions[:limit]
