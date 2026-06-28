import json
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

from aios_habit.source_ingest import load_sources, NOTEBOOK_ASSETS_DIR

try:
    from aios_habit.rag_ingest import RAGChunk, compute_source_hash, stable_document_id, stable_chunk_id, normalize_privacy_mode
except ImportError:
    pass

LOCAL_CASES_DIR = Path.cwd() / "local_cases"
CHUNKS_FILE = LOCAL_CASES_DIR / "source_chunks.jsonl"
MAX_SOURCE_CHARS = 20000
CHUNK_SIZE = 1200
MAX_CHUNKS_PER_SOURCE = 20

@dataclass
class SourceChunk:
    chunk_id: str
    notebook_id: str
    source_id: str
    chunk_index: int
    text: str
    keywords: List[str]
    privacy_level: str
    source_title: str
    original_filename: str
    created_at: str

@dataclass
class SearchHit:
    chunk: SourceChunk
    score: float

def load_chunks(notebook_id: Optional[str] = None) -> List[SourceChunk]:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    if not CHUNKS_FILE.exists():
        return []
    chunks = []
    with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    chunk = SourceChunk(**data)
                    if notebook_id is None or chunk.notebook_id == notebook_id:
                        chunks.append(chunk)
                except Exception:
                    pass
    return chunks

def extract_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9_À-ỹ]+", text.lower())
    stop_words = {"và", "là", "trong", "có", "cho", "để", "của", "được", "với", "the", "and", "for", "with", "this", "that"}
    keywords = sorted(list({t for t in tokens if len(t) >= 3 and t not in stop_words}))
    return keywords

def build_notebook_index(notebook_id: str) -> List[SourceChunk]:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Load all sources for this notebook
    sources = [s for s in load_sources() if s.notebook_id == notebook_id]
    
    new_chunks: List[SourceChunk] = []
    
    # 2. For each source, build chunks
    for src in sources:
        text = ""
        ext = src.source_type.lower()
        if ext in ("txt", "md", "markdown"):
            if src.asset_path:
                p = Path(src.asset_path).resolve()
                try:
                    assets_dir = NOTEBOOK_ASSETS_DIR.resolve()
                    if p.exists() and p.is_relative_to(assets_dir):
                        with open(p, 'r', encoding='utf-8', errors='replace') as f:
                            text = f.read(MAX_SOURCE_CHARS)
                except Exception:
                    pass
        
        if not text.strip():
            text = src.preview_text or ""
            
        if not text.strip():
            continue
            
        # Chunk text
        chunks_texts = []
        for i in range(0, len(text), CHUNK_SIZE):
            chunks_texts.append(text[i:i+CHUNK_SIZE])
            
        chunks_texts = chunks_texts[:MAX_CHUNKS_PER_SOURCE]
        
        for idx, chunk_text in enumerate(chunks_texts):
            chunk_id = f"{src.source_id}-CH{idx:03d}"
            keywords = extract_keywords(chunk_text)
            chunk = SourceChunk(
                chunk_id=chunk_id,
                notebook_id=notebook_id,
                source_id=src.source_id,
                chunk_index=idx,
                text=chunk_text,
                keywords=keywords,
                privacy_level=src.privacy_level,
                source_title=src.title,
                original_filename=src.original_filename,
                created_at=datetime.now().isoformat()
            )
            new_chunks.append(chunk)
            
    # 3. Read other chunks and merge
    all_other_chunks = []
    if CHUNKS_FILE.exists():
        with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        chunk = SourceChunk(**data)
                        if chunk.notebook_id != notebook_id:
                            all_other_chunks.append(chunk)
                    except Exception:
                        pass
                        
    # Write back all
    with open(CHUNKS_FILE, 'w', encoding='utf-8') as f:
        for c in all_other_chunks + new_chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + '\n')
            
    return new_chunks

def search_notebook_chunks(notebook_id: str, query: str, limit: int = 5) -> List[SearchHit]:
    chunks = load_chunks(notebook_id)
    if not chunks:
        # If no chunks exist at all in store, let's build them to be friendly
        chunks = build_notebook_index(notebook_id)
        
    query_lower = query.lower().strip()
    if not query_lower:
        return []
        
    query_tokens = [t for t in re.findall(r"[a-zA-Z0-9_À-ỹ]+", query_lower) if len(t) >= 2]
    
    hits: List[SearchHit] = []
    for chunk in chunks:
        score = 0.0
        
        text_lower = chunk.text.lower()
        title_lower = chunk.source_title.lower()
        filename_lower = chunk.original_filename.lower()
        
        # exact phrase bonus
        if query_lower in text_lower:
            score += 10.0
        if query_lower in title_lower:
            score += 5.0
        if query_lower in filename_lower:
            score += 3.0
            
        # keyword matches
        for tok in query_tokens:
            if tok in title_lower or tok in filename_lower:
                score += 2.0
            
            matches = len(re.findall(re.escape(tok), text_lower))
            score += matches * 1.0
            
        if score > 0.0:
            hits.append(SearchHit(chunk=chunk, score=score))
            
    hits.sort(key=lambda x: x.score, reverse=True)
    return hits[:limit]

def build_rag_chunks_from_notebook_chunks(notebook_chunks: List[SourceChunk]) -> List['RAGChunk']:
    """Adapter to convert existing SourceChunk to RAGChunk format for RAG Engine v2."""
    try:
        from aios_habit.rag_ingest import RAGChunk, compute_source_hash, stable_document_id, stable_chunk_id, normalize_privacy_mode
    except ImportError:
        return []
        
    rag_chunks = []
    for i, chunk in enumerate(notebook_chunks):
        src_hash = chunk.source_id
        doc_id = stable_document_id(chunk.original_filename, src_hash)
        rag_chunk_id = stable_chunk_id(doc_id, chunk.chunk_index, compute_source_hash(chunk.text))
        
        # Ensure citation label does not expose absolute path
        rel_path = chunk.original_filename
        citation = Path(rel_path).name
        
        privacy = normalize_privacy_mode(chunk.privacy_level)
        
        rag_chunk = RAGChunk(
            chunk_id=rag_chunk_id,
            document_id=doc_id,
            element_ids=[],
            text=chunk.text,
            source_title=chunk.source_title,
            source_path=chunk.original_filename,
            relative_path=rel_path,
            citation_label=citation,
            file_type=Path(chunk.original_filename).suffix.lower() or ".txt",
            element_types=["text"],
            page_numbers=[],
            sheet_names=[],
            slide_numbers=[],
            section_labels=[],
            row_ranges=[],
            cell_ranges=[],
            privacy_mode=privacy,
            source_hash=src_hash,
            chunk_index=chunk.chunk_index,
            metadata={"notebook_id": chunk.notebook_id, "source_id": chunk.source_id, "created_at": chunk.created_at}
        )
        rag_chunks.append(rag_chunk)
        
    # Link previous/next
    for i in range(len(rag_chunks)):
        if i > 0 and rag_chunks[i-1].document_id == rag_chunks[i].document_id:
            rag_chunks[i].previous_chunk_id = rag_chunks[i-1].chunk_id
            rag_chunks[i-1].next_chunk_id = rag_chunks[i].chunk_id
            
    return rag_chunks

def build_search_index_from_rag_chunks(conn, rag_chunks: List['RAGChunk']):
    """Adapter to index RAGChunk items using the new rag_search module, if available."""
    try:
        from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks
    except ImportError:
        return
        
    create_rag_search_schema(conn)
    index_rag_chunks(conn, rag_chunks)
