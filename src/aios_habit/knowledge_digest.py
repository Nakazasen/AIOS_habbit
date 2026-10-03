"""Knowledge digest pipeline (ve KNOWLEDGE-DIGEST-HOME).

Nen toan bo kho tri thuc thanh mot "so tay tri thuc" Markdown co cau truc
de nap vao context dai cua LLM hoi dap truc tiep, khong qua retrieval chunk.

Nguyen tac an toan:
- CHI DOC tren index production (`library.sqlite` mo bang `mode=ro`).
  Khong bao gio ghi vao DB chinh hay index.
- So tay la BAN THAO do LLM soan: file ghi ro dong dau
  "Ban thao - chua qua chuyen gia duyet". Khong gan nhan tri thuc da duyet,
  khong nhap vao kho, khong nhap vao luong tra loi chinh.
- Ham goi LLM (`llm_call`) duoc truyen vao tu ngoai de test khong can LLM that;
  o may nha OMP gan cau noi Gemini Web vao day.

Tuong thich Python 3.11 (khong dung cu phap 3.12+).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# Ban thao luon ghi ro o dong dau so tay.
DRAFT_BANNER = "BẢN THẢO — CHƯA QUA CHUYÊN GIA DUYỆT"

# Gioi han ky tu text doc dua vao prompt tom tat (chan token phong dai).
MAX_DOC_CHARS = 12000

# Ghi checkpoint moi N document de batch chay qua dem co the resume.
CHECKPOINT_EVERY = 25

SUMMARY_PROMPT_TEMPLATE = """Bạn là trợ lý soạn sổ tay tri thức kỹ thuật. Dưới đây là nội dung các đoạn trích
của MỘT tài liệu trong kho tri thức nội bộ (có thể đã bị rút gọn).

Tiêu đề tài liệu: {title}
Đường dẫn: {path}

--- NỘI DUNG ---
{content}
--- HẾT ---

Hãy tóm tắt tài liệu trên thành MỘT mục sổ tay, trả về ĐÚNG định dạng JSON sau
(không thêm chữ giải thích ngoài JSON):
{{
  "chu_de": "chủ đề chính của tài liệu, ngắn gọn",
  "y_chinh": ["ý chính 1", "ý chính 2", "..."],
  "so_lieu": ["số liệu / thông số then chốt kèm đơn vị", "..."],
  "dieu_kien_nguong_ngoai_le": ["điều kiện áp dụng / ngưỡng / ngoại lệ", "..."],
  "lien_quan": ["tài liệu hoặc chủ đề liên quan nếu thấy trong nội dung", "..."]
}}

Quy tắc:
- Chỉ viết những gì có trong nội dung được cho; không suy đoán thêm.
- Trường nào không có dữ kiện thì để mảng rỗng, không bịa.
- Tiếng Việt, ngắn gọn, mỗi ý một dòng."""


@dataclass
class DigestEntry:
    """Mot muc so tay tuong ung mot document."""

    document_id: str
    source_title: str
    relative_path: str
    chu_de: str = ""
    y_chinh: List[str] = field(default_factory=list)
    so_lieu: List[str] = field(default_factory=list)
    dieu_kien_nguong_ngoai_le: List[str] = field(default_factory=list)
    lien_quan: List[str] = field(default_factory=list)
    rut_gon_nguon: bool = False
    raw: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "DigestEntry":
        return cls(
            document_id=str(data.get("document_id", "")),
            source_title=str(data.get("source_title", "")),
            relative_path=str(data.get("relative_path", "")),
            chu_de=str(data.get("chu_de", "")),
            y_chinh=[str(x) for x in data.get("y_chinh", [])],
            so_lieu=[str(x) for x in data.get("so_lieu", [])],
            dieu_kien_nguong_ngoai_le=[str(x) for x in data.get("dieu_kien_nguong_ngoai_le", [])],
            lien_quan=[str(x) for x in data.get("lien_quan", [])],
            rut_gon_nguon=bool(data.get("rut_gon_nguon", False)),
            raw=str(data.get("raw", "")),
        )


def open_index_readonly(index_path: str | Path) -> sqlite3.Connection:
    """Mo library.sqlite o che do chi doc (mode=ro)."""
    path = Path(index_path).resolve()
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def count_documents(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(DISTINCT document_id) AS n FROM chunk_metadata").fetchone()
    return int(row["n"]) if row else 0


def list_documents(conn: sqlite3.Connection) -> List[Dict]:
    """Liet ke document: id, tieu de, duong dan, so chunk."""
    rows = conn.execute(
        "SELECT document_id, source_title, relative_path, COUNT(*) AS chunks "
        "FROM chunk_metadata GROUP BY document_id ORDER BY document_id"
    ).fetchall()
    return [
        {
            "document_id": r["document_id"],
            "source_title": r["source_title"] or "",
            "relative_path": r["relative_path"] or "",
            "chunks": int(r["chunks"]),
        }
        for r in rows
    ]


def read_document_text(
    conn: sqlite3.Connection, document_id: str, max_chars: int = MAX_DOC_CHARS
) -> Tuple[str, bool]:
    """Ghep text cac chunk cua mot document. Tra ve (text, bi_rut_gon)."""
    rows = conn.execute(
        "SELECT text FROM chunk_metadata WHERE document_id = ? ORDER BY chunk_id",
        (document_id,),
    ).fetchall()
    parts = [str(r["text"] or "") for r in rows]
    full = "\n\n".join(p for p in parts if p.strip())
    if len(full) > max_chars:
        return full[:max_chars], True
    return full, False


def _parse_summary_json(raw: str) -> Dict:
    """Parse JSON tu output LLM; that bai thi tra ve dict rong."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def summarize_document(
    document: Dict,
    text: str,
    truncated: bool,
    llm_call: Callable[[str], str],
) -> DigestEntry:
    """Goi LLM tom tat mot document thanh DigestEntry co cau truc."""
    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        title=document.get("source_title", ""),
        path=document.get("relative_path", ""),
        content=text,
    )
    raw = llm_call(prompt) or ""
    data = _parse_summary_json(raw)
    entry = DigestEntry(
        document_id=str(document.get("document_id", "")),
        source_title=str(document.get("source_title", "")),
        relative_path=str(document.get("relative_path", "")),
        rut_gon_nguon=truncated,
    )
    if data:
        entry.chu_de = str(data.get("chu_de", ""))
        entry.y_chinh = [str(x) for x in data.get("y_chinh", []) if str(x).strip()]
        entry.so_lieu = [str(x) for x in data.get("so_lieu", []) if str(x).strip()]
        entry.dieu_kien_nguong_ngoai_le = [
            str(x) for x in data.get("dieu_kien_nguong_ngoai_le", []) if str(x).strip()
        ]
        entry.lien_quan = [str(x) for x in data.get("lien_quan", []) if str(x).strip()]
    else:
        entry.raw = raw
    return entry


def _bullet_list(items: Sequence[str]) -> str:
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return "- (chưa có dữ kiện)"
    return "\n".join("- " + x for x in items)


def render_entry(entry: DigestEntry) -> str:
    lines = ["## " + (entry.source_title or entry.document_id)]
    if entry.chu_de.strip():
        lines.append("")
        lines.append("**Chủ đề:** " + entry.chu_de.strip())
    lines.append("")
    lines.append("**Ý chính:**")
    lines.append(_bullet_list(entry.y_chinh))
    lines.append("")
    lines.append("**Số liệu / thông số then chốt:**")
    lines.append(_bullet_list(entry.so_lieu))
    lines.append("")
    lines.append("**Điều kiện – ngưỡng – ngoại lệ:**")
    lines.append(_bullet_list(entry.dieu_kien_nguong_ngoai_le))
    if entry.lien_quan:
        lines.append("")
        lines.append("**Liên quan:**")
        lines.append(_bullet_list(entry.lien_quan))
    if entry.raw.strip():
        lines.append("")
        lines.append("**Ghi chú (LLM trả về ngoài schema):**")
        lines.append(entry.raw.strip()[:2000])
    if entry.rut_gon_nguon:
        lines.append("")
        lines.append("*(Nguồn đã rút gọn khi tóm tắt.)*")
    return "\n".join(lines).strip()


def group_by_topic(entries: Sequence[DigestEntry]) -> Dict[str, List[DigestEntry]]:
    """Gom muc so tay theo chu de (chu_de rong -> 'Chua phan loai')."""
    groups: Dict[str, List[DigestEntry]] = {}
    for entry in entries:
        topic = entry.chu_de.strip() or "Chưa phân loại"
        groups.setdefault(topic, []).append(entry)
    return groups


def render_handbook(
    entries: Sequence[DigestEntry],
    *,
    doc_total: int,
    generated_at: Optional[str] = None,
) -> str:
    """Xuat cuon so tay Markdown duy nhat."""
    stamp = generated_at or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines = [
        "# Sổ tay tri thức (bản rút gọn cho hỏi đáp)",
        "",
        "**" + DRAFT_BANNER + "**",
        "",
        "Sổ tay này do LLM soạn từ toàn bộ kho tri thức để phục vụ vòng hỏi đáp cải thiện. "
        "Mọi mục đều là bản thảo, chưa qua chuyên gia duyệt; không dùng làm tri thức chính thức.",
        "",
        "- Số document trong kho: " + str(doc_total),
        "- Số mục trong sổ tay: " + str(len(entries)),
        "- Thời điểm tạo: " + stamp,
        "",
        "---",
    ]
    groups = group_by_topic(entries)
    for topic in sorted(groups.keys()):
        lines.append("")
        lines.append("# Chủ đề: " + topic)
        for entry in groups[topic]:
            lines.append("")
            lines.append(render_entry(entry))
    lines.append("")
    return "\n".join(lines)


def write_manifest(handbook_path: str | Path, doc_total: int, entry_count: int) -> Path:
    """Ghi manifest SHA-256 cua so tay."""
    handbook_path = Path(handbook_path)
    digest = hashlib.sha256(handbook_path.read_bytes()).hexdigest()
    manifest = {
        "handbook": handbook_path.name,
        "sha256": digest,
        "doc_total": doc_total,
        "entry_count": entry_count,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "draft": True,
        "note": DRAFT_BANNER,
    }
    manifest_path = handbook_path.with_suffix(handbook_path.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def _load_checkpoint(checkpoint_path: Path) -> Dict[str, Dict]:
    if not checkpoint_path.exists():
        return {}
    try:
        data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError):
        return {}
    done = data.get("done", {}) if isinstance(data, dict) else {}
    return {str(k): v for k, v in done.items() if isinstance(v, dict)}


def _save_checkpoint(checkpoint_path: Path, done: Dict[str, Dict]) -> None:
    payload = {"done": done, "saved_at": time.time()}
    tmp = checkpoint_path.with_suffix(checkpoint_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(checkpoint_path)


def run_digest(
    index_path: str | Path,
    output_dir: str | Path,
    llm_call: Callable[[str], str],
    *,
    checkpoint_path: Optional[str | Path] = None,
    progress_every: int = CHECKPOINT_EVERY,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Dict:
    """Chay full pipeline: dem -> tom tat tung document (co resume) -> so tay + manifest.

    Tra ve dict thong ke. Khong bao gio ghi vao index.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt = Path(checkpoint_path) if checkpoint_path else output_dir / "digest_checkpoint.json"
    done = _load_checkpoint(ckpt)

    conn = open_index_readonly(index_path)
    try:
        doc_total = count_documents(conn)
        documents = list_documents(conn)

        entries: List[DigestEntry] = []
        for position, document in enumerate(documents, start=1):
            doc_id = str(document["document_id"])
            if doc_id in done:
                entries.append(DigestEntry.from_dict(done[doc_id]))
                continue
            text, truncated = read_document_text(conn, doc_id)
            entry = summarize_document(document, text, truncated, llm_call)
            done[doc_id] = entry.to_dict()
            entries.append(entry)
            if on_progress is not None:
                on_progress(position, doc_total)
            if position % progress_every == 0:
                _save_checkpoint(ckpt, done)
    finally:
        conn.close()
    _save_checkpoint(ckpt, done)

    handbook_text = render_handbook(entries, doc_total=doc_total)
    handbook_path = output_dir / "so_tay_tri_thuc.md"
    handbook_path.write_text(handbook_text, encoding="utf-8")
    manifest_path = write_manifest(handbook_path, doc_total, len(entries))
    return {
        "doc_total": doc_total,
        "entry_count": len(entries),
        "handbook_path": str(handbook_path),
        "manifest_path": str(manifest_path),
        "checkpoint_path": str(ckpt),
    }
