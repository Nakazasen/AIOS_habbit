from __future__ import annotations

import csv
import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional

import pandas as pd

from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_store import save_case, save_evidence
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


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9_À-ỹ]+", text.lower()) if len(t) >= 2]


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
            for chunk in _chunk_text(text, sheet_base, max_chunks=3):
                chunks.append(chunk)
    except Exception as exc:
        raise RuntimeError(f"excel read failed: {exc}") from exc
    return chunks


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
                    chunks.extend(list(_chunk_text(text, base)))
                elif ext == ".csv":
                    text = _read_csv_file(path)
                    chunks.extend(list(_chunk_text(text, base)))
                elif ext in SUPPORTED_TABLE_EXTS:
                    chunks.extend(_excel_chunks(path, base))
                else:
                    reason = "unsupported file type"
                    if ext == ".pdf":
                        reason = "pdf extraction dependency not available"
                    elif ext in {".doc", ".docx"}:
                        reason = "doc/docx extraction dependency not available"
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
    q = query.strip().lower()
    if not q:
        return []
    query_terms = _tokens(q)
    hits: list[MomSearchHit] = []
    for chunk in load_mom_chunks(index_path):
        haystack = " ".join([chunk.text, chunk.relative_path, chunk.source_file, chunk.sheet]).lower()
        score = 0.0
        matched: list[str] = []
        if q in haystack:
            score += 12.0
            matched.append(q)
        for term in query_terms:
            count = haystack.count(term)
            if count:
                matched.append(term)
                score += min(count, 8) * 1.0
                if term in chunk.relative_path.lower() or term in chunk.source_file.lower() or term in chunk.sheet.lower():
                    score += 3.0
        if score > 0:
            hits.append(MomSearchHit(chunk=chunk, score=score, matched_terms=sorted(set(matched))))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


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
        })
        lines.append(
            f"[Nguồn {i}] {ref} | score={hit.score:.1f} | privacy=local_only\n"
            f"Preview: {chunk.preview}"
        )

    insufficient = not usable
    context = "\n\n".join(lines) if lines else "Không tìm thấy nguồn MOM local đủ khớp."
    prompt = (
        "Bạn là AIOS WorkLens phân tích tài liệu MOM local-only.\n"
        "Không gửi nội dung này lên cloud nếu chưa có phê duyệt privacy rõ ràng.\n\n"
        f"Câu hỏi nghiệp vụ MOM: {question}\n\n"
        "Nguồn MOM local được phép dùng:\n"
        f"{context}\n\n"
        "Yêu cầu trả lời:\n"
        "1. Trả lời ngắn gọn bằng tiếng Việt dựa trên nguồn trên.\n"
        "2. Luôn trích dẫn chunk_id/relative_path.\n"
        "3. Nếu nguồn chưa đủ, nói 'chưa đủ bằng chứng' và đề xuất next checks.\n"
        "4. Không bịa nguyên nhân, không kết luận vượt quá nguồn.\n"
    )
    return {
        "question": question,
        "prompt": prompt,
        "source_refs": source_refs,
        "insufficient_evidence": insufficient,
        "privacy_level": "local_only",
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
