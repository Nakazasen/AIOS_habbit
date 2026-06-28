import sqlite3
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
import re

from aios_habit.rag_ingest import RAGChunk

@dataclass
class RAGSearchFilter:
    privacy_modes: Optional[List[str]] = None
    file_types: Optional[List[str]] = None
    source_titles: Optional[List[str]] = None
    relative_paths: Optional[List[str]] = None
    element_types: Optional[List[str]] = None
    page_numbers: Optional[List[int]] = None
    sheet_names: Optional[List[str]] = None
    slide_numbers: Optional[List[int]] = None

@dataclass
class RAGSearchResult:
    chunk_id: str
    document_id: str
    text: str
    score: float
    rank: int
    citation_label: str
    source_title: str
    relative_path: str
    file_type: str
    privacy_mode: str
    page_numbers: List[int]
    sheet_names: List[str]
    slide_numbers: List[int]
    element_types: List[str]
    metadata: Dict[str, Any]

@dataclass
class RAGSearchIndexStats:
    document_count: int
    chunk_count: int
    privacy_modes: List[str]
    file_types: List[str]

def _is_fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE _test_fts5 USING fts5(text)")
        conn.execute("DROP TABLE _test_fts5")
        return True
    except sqlite3.OperationalError:
        return False

def create_rag_search_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunk_metadata (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT,
            source_title TEXT,
            relative_path TEXT,
            citation_label TEXT,
            file_type TEXT,
            privacy_mode TEXT,
            page_numbers_json TEXT,
            sheet_names_json TEXT,
            slide_numbers_json TEXT,
            element_types_json TEXT,
            text TEXT,
            raw_json TEXT
        )
    """)
    
    if _is_fts5_available(conn):
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
                chunk_id UNINDEXED,
                text,
                source_title
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS fts_enabled (enabled INTEGER)")
        cursor.execute("INSERT INTO fts_enabled (enabled) VALUES (1)")
    else:
        cursor.execute("CREATE TABLE IF NOT EXISTS fts_enabled (enabled INTEGER)")
        cursor.execute("INSERT INTO fts_enabled (enabled) VALUES (0)")
        
    conn.commit()

def clear_rag_search_index(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS chunk_metadata")
    cursor.execute("DROP TABLE IF EXISTS chunk_fts")
    cursor.execute("DROP TABLE IF EXISTS fts_enabled")
    conn.commit()
    create_rag_search_schema(conn)

def _has_fts(conn: sqlite3.Connection) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT enabled FROM fts_enabled LIMIT 1")
        row = cursor.fetchone()
        return bool(row and row[0] == 1)
    except sqlite3.OperationalError:
        return False

def index_rag_chunks(conn: sqlite3.Connection, chunks: List[RAGChunk]):
    cursor = conn.cursor()
    has_fts = _has_fts(conn)
    
    for chunk in chunks:
        # Avoid duplicate index
        cursor.execute("SELECT chunk_id FROM chunk_metadata WHERE chunk_id = ?", (chunk.chunk_id,))
        if cursor.fetchone():
            continue
            
        cursor.execute("""
            INSERT INTO chunk_metadata (
                chunk_id, document_id, source_title, relative_path, citation_label,
                file_type, privacy_mode, page_numbers_json, sheet_names_json,
                slide_numbers_json, element_types_json, text, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk.chunk_id,
            chunk.document_id,
            chunk.source_title,
            chunk.relative_path,
            chunk.citation_label,
            chunk.file_type,
            chunk.privacy_mode,
            json.dumps(chunk.page_numbers),
            json.dumps(chunk.sheet_names),
            json.dumps(chunk.slide_numbers),
            json.dumps(chunk.element_types),
            chunk.text,
            json.dumps(asdict(chunk))
        ))
        
        if has_fts:
            cursor.execute("""
                INSERT INTO chunk_fts (chunk_id, text, source_title)
                VALUES (?, ?, ?)
            """, (chunk.chunk_id, chunk.text, chunk.source_title))
            
    conn.commit()

def sanitize_fts_query(query: str) -> str:
    # Remove quotes to avoid malformed FTS query issues
    q = query.replace('"', ' ').replace("'", ' ')
    return q.strip()

def search_rag_chunks(conn: sqlite3.Connection, query: str, filters: Optional[RAGSearchFilter] = None, limit: int = 10) -> List[RAGSearchResult]:
    cursor = conn.cursor()
    has_fts = _has_fts(conn)
    
    # Base query for FTS or Fallback
    params: List[Any] = []
    
    # Build filter conditions
    filter_clauses = []
    if filters:
        if filters.privacy_modes:
            placeholders = ','.join('?' * len(filters.privacy_modes))
            filter_clauses.append(f"m.privacy_mode IN ({placeholders})")
            params.extend(filters.privacy_modes)
        if filters.file_types:
            placeholders = ','.join('?' * len(filters.file_types))
            filter_clauses.append(f"m.file_type IN ({placeholders})")
            params.extend(filters.file_types)
        if filters.source_titles:
            placeholders = ','.join('?' * len(filters.source_titles))
            filter_clauses.append(f"m.source_title IN ({placeholders})")
            params.extend(filters.source_titles)
        if filters.relative_paths:
            placeholders = ','.join('?' * len(filters.relative_paths))
            filter_clauses.append(f"m.relative_path IN ({placeholders})")
            params.extend(filters.relative_paths)
            
        def add_json_filter(field_name, items):
            if items:
                conditions = []
                for item in items:
                    conditions.append(f"m.{field_name} LIKE ?")
                    # simple substring search in json array
                    if isinstance(item, str):
                        params.append(f'%"{item}"%')
                    else:
                        params.append(f'%{item}%')
                filter_clauses.append("(" + " OR ".join(conditions) + ")")
                
        add_json_filter("page_numbers_json", filters.page_numbers)
        add_json_filter("sheet_names_json", filters.sheet_names)
        add_json_filter("slide_numbers_json", filters.slide_numbers)
        add_json_filter("element_types_json", filters.element_types)

    filter_sql = (" AND " + " AND ".join(filter_clauses)) if filter_clauses else ""
    
    query_lower = query.lower().strip()
    
    candidates = []
    if has_fts and query_lower:
        safe_q = sanitize_fts_query(query)
        if not safe_q:
            # Empty after sanitize, return nothing
            return []
            
        # FTS query
        # BM25 is available in FTS5
        sql = f"""
            SELECT m.chunk_id, m.raw_json, bm25(chunk_fts) as fts_score
            FROM chunk_metadata m
            JOIN chunk_fts f ON m.chunk_id = f.chunk_id
            WHERE chunk_fts MATCH ? {filter_sql}
        """
        params_fts = [safe_q] + params
        cursor.execute(sql, params_fts)
        rows = cursor.fetchall()
        for row in rows:
            chunk_id = row[0]
            raw_json = row[1]
            fts_score = row[2] # BM25 returns negative score usually or positive depending on implementation
            # SQLite FTS5 bm25 returns negative score by default where more negative is better.
            # We want positive scores where higher is better.
            base_score = -fts_score if fts_score < 0 else (1.0 / (1.0 + fts_score)) 
            candidates.append((chunk_id, raw_json, base_score))
    else:
        # Fallback query
        sql = f"""
            SELECT m.chunk_id, m.raw_json, m.text, m.source_title
            FROM chunk_metadata m
            WHERE 1=1 {filter_sql}
        """
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        query_tokens = [t for t in re.findall(r"[a-zA-Z0-9_À-ỹ]+", query_lower) if len(t) >= 2]
        
        for row in rows:
            chunk_id = row[0]
            raw_json = row[1]
            text = row[2].lower()
            title = row[3].lower()
            
            score = 0.0
            if not query_lower:
                # No query, just return all matching filters
                score = 1.0
            else:
                if query_lower in text:
                    score += 10.0
                if query_lower in title:
                    score += 5.0
                
                for tok in query_tokens:
                    if tok in title:
                        score += 2.0
                    matches = len(re.findall(re.escape(tok), text))
                    score += matches * 1.0
            
            if score > 0:
                candidates.append((chunk_id, raw_json, score))

    # Apply exact phrase and source title boosts on all candidates
    results = []
    for chunk_id, raw_json, base_score in candidates:
        chunk_data = json.loads(raw_json)
        text_lower = chunk_data.get("text", "").lower()
        title_lower = chunk_data.get("source_title", "").lower()
        
        score = base_score
        
        if query_lower and query_lower in text_lower:
            score += 10.0
        if query_lower and query_lower in title_lower:
            score += 5.0
            
        results.append((score, chunk_id, chunk_data))
        
    # Sort by score desc, chunk_id asc for deterministic tie-breaker
    results.sort(key=lambda x: (-x[0], x[1]))
    
    final_results = []
    for rank, (score, chunk_id, chunk_data) in enumerate(results[:limit]):
        final_results.append(RAGSearchResult(
            chunk_id=chunk_id,
            document_id=chunk_data.get("document_id", ""),
            text=chunk_data.get("text", ""),
            score=score,
            rank=rank + 1,
            citation_label=chunk_data.get("citation_label", ""),
            source_title=chunk_data.get("source_title", ""),
            relative_path=chunk_data.get("relative_path", ""),
            file_type=chunk_data.get("file_type", ""),
            privacy_mode=chunk_data.get("privacy_mode", ""),
            page_numbers=chunk_data.get("page_numbers", []),
            sheet_names=chunk_data.get("sheet_names", []),
            slide_numbers=chunk_data.get("slide_numbers", []),
            element_types=chunk_data.get("element_types", []),
            metadata=chunk_data.get("metadata", {})
        ))
        
    return final_results

def get_rag_search_stats(conn: sqlite3.Connection) -> RAGSearchIndexStats:
    cursor = conn.cursor()
    cursor.execute("SELECT count(DISTINCT document_id) FROM chunk_metadata")
    doc_count = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT count(chunk_id) FROM chunk_metadata")
    chunk_count = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT DISTINCT privacy_mode FROM chunk_metadata")
    privacy_modes = sorted([row[0] for row in cursor.fetchall() if row[0]])
    
    cursor.execute("SELECT DISTINCT file_type FROM chunk_metadata")
    file_types = sorted([row[0] for row in cursor.fetchall() if row[0]])
    
    return RAGSearchIndexStats(
        document_count=doc_count,
        chunk_count=chunk_count,
        privacy_modes=privacy_modes,
        file_types=file_types
    )
