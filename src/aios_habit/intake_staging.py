"""Staging store lưu trữ các phiên thu tri thức, lượt hỏi-đáp nguyên văn và các mục nháp.

Kiến trúc:
- Store staging local riêng, tách biệt hoàn toàn với các kho tri thức chính thức.
- Phân vùng theo kho đích (`store_id`): mọi thao tác truy vấn đều lọc theo kho đích,
  tuyệt đối không trộn lẫn dữ liệu giữa các kho.
- Lưu trữ hỏi-đáp nguyên văn đảm bảo truy vết 100% nguồn gốc.
- Quản lý trạng thái duyệt tại chỗ: Đúng / Sửa / Loại.
  Chỉ mục "đúng" hoặc "đã sửa" mới mang trạng thái CHO_NAP (`cho_nap`).

Tương thích Python 3.11: không dùng f-string nhiều dòng (PEP 701), không type statement.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

# Trạng thái duyệt của mục nháp
STATUS_CHO_DUYET = "cho_duyet"
STATUS_DUNG = "dung"
STATUS_DA_SUA = "da_sua"
STATUS_LOAI = "loai"

# Trạng thái nạp
INGEST_CHO_NAP = "cho_nap"
INGEST_KHONG_NAP = "khong_nap"


@dataclass(frozen=True)
class IntakeTurnRecord:
    """Bản ghi một lượt hỏi-đáp nguyên văn trong phiên thu tri thức."""

    turn_id: str
    session_id: str
    store_id: str
    turn_index: int
    speaker: str
    question_text: str
    answer_text: str
    probe_type: str = "general"
    timestamp: str = ""


@dataclass(frozen=True)
class IntakeDraftItemRecord:
    """Bản ghi một mục tri thức nháp đã tổng hợp."""

    draft_id: str
    session_id: str
    store_id: str
    mode: str
    expert_name: str
    topic: str
    source_tag: str
    fields: Dict[str, str] = field(default_factory=dict)
    source_quote: str = ""
    source_turn_ids: Tuple[str, ...] = field(default_factory=tuple)
    review_status: str = STATUS_CHO_DUYET
    ingest_status: str = INGEST_KHONG_NAP
    reviewed_by: str = ""
    reviewed_at: str = ""
    edited_fields: Dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class IntakeSessionRecord:
    """Bản ghi thông tin phiên thu tri thức."""

    session_id: str
    store_id: str
    mode: str
    expert_name: str
    topic: str
    status: str = "in_progress"
    created_at: str = ""
    updated_at: str = ""


def get_staging_db_path() -> Path:
    """Xác định đường dẫn tệp SQLite staging store."""
    env_db = os.environ.get("AIOS_INTAKE_STAGING_DB", "")
    if env_db.strip():
        return Path(env_db.strip())
    cases_dir = os.environ.get("AIOS_LOCAL_CASES_DIR", "")
    base = Path(cases_dir.strip()) if cases_dir.strip() else Path.cwd() / "local_cases"
    return base / "knowledge_intake_staging.sqlite"


def init_staging_db(db_path: Optional[Path] = None) -> Path:
    """Khởi tạo cấu trúc các bảng cho staging store nếu chưa tồn tại."""
    target_path = db_path or get_staging_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS intake_sessions (
                session_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                expert_name TEXT NOT NULL,
                topic TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_intake_sessions_store
            ON intake_sessions(store_id);
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS intake_turns (
                turn_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                store_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                speaker TEXT NOT NULL,
                question_text TEXT NOT NULL,
                answer_text TEXT NOT NULL,
                probe_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES intake_sessions(session_id)
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_intake_turns_session
            ON intake_turns(session_id);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_intake_turns_store
            ON intake_turns(store_id);
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS intake_draft_items (
                draft_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                store_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                expert_name TEXT NOT NULL,
                topic TEXT NOT NULL,
                source_tag TEXT NOT NULL,
                fields_json TEXT NOT NULL,
                source_quote TEXT NOT NULL,
                source_turn_ids_json TEXT NOT NULL,
                review_status TEXT NOT NULL,
                ingest_status TEXT NOT NULL,
                reviewed_by TEXT,
                reviewed_at TEXT,
                edited_fields_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES intake_sessions(session_id)
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_intake_drafts_store
            ON intake_draft_items(store_id);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_intake_drafts_session
            ON intake_draft_items(session_id);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_intake_drafts_ingest
            ON intake_draft_items(store_id, ingest_status);
            """
        )
        conn.commit()
    finally:
        conn.close()
    return target_path


class IntakeStagingStore:
    """Quản trị thao tác staging store với đảm bảo phân vùng theo kho đích."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = init_staging_db(db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # --- Quản lý phiên ---

    def save_session(self, session: IntakeSessionRecord) -> None:
        """Lưu hoặc cập nhật thông tin phiên."""
        now = datetime.now().isoformat()
        created_at = session.created_at or now
        updated_at = session.updated_at or now
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO intake_sessions (
                    session_id, store_id, mode, expert_name, topic,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    store_id=excluded.store_id,
                    mode=excluded.mode,
                    expert_name=excluded.expert_name,
                    topic=excluded.topic,
                    status=excluded.status,
                    updated_at=excluded.updated_at;
                """,
                (
                    session.session_id,
                    session.store_id,
                    session.mode,
                    session.expert_name,
                    session.topic,
                    session.status,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[IntakeSessionRecord]:
        """Lấy thông tin phiên theo session_id."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT session_id, store_id, mode, expert_name, topic,
                       status, created_at, updated_at
                FROM intake_sessions WHERE session_id = ?;
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return IntakeSessionRecord(
                session_id=row["session_id"],
                store_id=row["store_id"],
                mode=row["mode"],
                expert_name=row["expert_name"],
                topic=row["topic"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_sessions_by_store(
        self, store_id: Optional[str] = None, mode: Optional[str] = None
    ) -> List[IntakeSessionRecord]:
        """Liệt kê các phiên, lọc chặt chẽ theo kho đích và/hoặc chế độ."""
        query = (
            "SELECT session_id, store_id, mode, expert_name, topic, "
            "status, created_at, updated_at FROM intake_sessions WHERE 1=1"
        )
        params: List[Any] = []
        if store_id:
            query += " AND store_id = ?"
            params.append(store_id)
        if mode:
            query += " AND mode = ?"
            params.append(mode)
        query += " ORDER BY created_at DESC;"

        with self._connect() as conn:
            cur = conn.execute(query, params)
            records: List[IntakeSessionRecord] = []
            for row in cur.fetchall():
                records.append(
                    IntakeSessionRecord(
                        session_id=row["session_id"],
                        store_id=row["store_id"],
                        mode=row["mode"],
                        expert_name=row["expert_name"],
                        topic=row["topic"],
                        status=row["status"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return records

    # --- Quản lý lượt hỏi-đáp (Turns) ---

    def save_turn(self, turn: IntakeTurnRecord) -> None:
        """Lưu một lượt hỏi-đáp nguyên văn để phục vụ truy vết căn cứ nguồn."""
        ts = turn.timestamp or datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO intake_turns (
                    turn_id, session_id, store_id, turn_index, speaker,
                    question_text, answer_text, probe_type, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(turn_id) DO UPDATE SET
                    answer_text=excluded.answer_text,
                    timestamp=excluded.timestamp;
                """,
                (
                    turn.turn_id,
                    turn.session_id,
                    turn.store_id,
                    turn.turn_index,
                    turn.speaker,
                    turn.question_text,
                    turn.answer_text,
                    turn.probe_type,
                    ts,
                ),
            )
            conn.commit()

    def get_turns(self, session_id: str) -> List[IntakeTurnRecord]:
        """Lấy toàn bộ các lượt hỏi-đáp nguyên văn của một phiên theo thứ tự."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT turn_id, session_id, store_id, turn_index, speaker,
                       question_text, answer_text, probe_type, timestamp
                FROM intake_turns
                WHERE session_id = ?
                ORDER BY turn_index ASC;
                """,
                (session_id,),
            )
            turns: List[IntakeTurnRecord] = []
            for row in cur.fetchall():
                turns.append(
                    IntakeTurnRecord(
                        turn_id=row["turn_id"],
                        session_id=row["session_id"],
                        store_id=row["store_id"],
                        turn_index=row["turn_index"],
                        speaker=row["speaker"],
                        question_text=row["question_text"],
                        answer_text=row["answer_text"],
                        probe_type=row["probe_type"],
                        timestamp=row["timestamp"],
                    )
                )
            return turns

    # --- Quản lý mục nháp và trạng thái duyệt ---

    def save_draft_item(self, item: IntakeDraftItemRecord) -> None:
        """Lưu một mục nháp tri thức đã tổng hợp."""
        now = datetime.now().isoformat()
        created_at = item.created_at or now
        updated_at = item.updated_at or now
        fields_json = json.dumps(item.fields, ensure_ascii=False)
        turn_ids_json = json.dumps(list(item.source_turn_ids), ensure_ascii=False)
        edited_json = json.dumps(item.edited_fields, ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO intake_draft_items (
                    draft_id, session_id, store_id, mode, expert_name, topic,
                    source_tag, fields_json, source_quote, source_turn_ids_json,
                    review_status, ingest_status, reviewed_by, reviewed_at,
                    edited_fields_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(draft_id) DO UPDATE SET
                    session_id=excluded.session_id,
                    store_id=excluded.store_id,
                    mode=excluded.mode,
                    expert_name=excluded.expert_name,
                    topic=excluded.topic,
                    source_tag=excluded.source_tag,
                    fields_json=excluded.fields_json,
                    source_quote=excluded.source_quote,
                    source_turn_ids_json=excluded.source_turn_ids_json,
                    review_status=excluded.review_status,
                    ingest_status=excluded.ingest_status,
                    reviewed_by=excluded.reviewed_by,
                    reviewed_at=excluded.reviewed_at,
                    edited_fields_json=excluded.edited_fields_json,
                    updated_at=excluded.updated_at;
                """,
                (
                    item.draft_id,
                    item.session_id,
                    item.store_id,
                    item.mode,
                    item.expert_name,
                    item.topic,
                    item.source_tag,
                    fields_json,
                    item.source_quote,
                    turn_ids_json,
                    item.review_status,
                    item.ingest_status,
                    item.reviewed_by,
                    item.reviewed_at,
                    edited_json,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()

    def save_draft_items(self, items: Sequence[IntakeDraftItemRecord]) -> None:
        """Lưu danh sách mục nháp."""
        for item in items:
            self.save_draft_item(item)

    def get_draft_item(self, draft_id: str) -> Optional[IntakeDraftItemRecord]:
        """Lấy một mục nháp theo draft_id."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT draft_id, session_id, store_id, mode, expert_name, topic,
                       source_tag, fields_json, source_quote, source_turn_ids_json,
                       review_status, ingest_status, reviewed_by, reviewed_at,
                       edited_fields_json, created_at, updated_at
                FROM intake_draft_items WHERE draft_id = ?;
                """,
                (draft_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_draft_item(row)

    def _row_to_draft_item(self, row: sqlite3.Row) -> IntakeDraftItemRecord:
        try:
            fields = json.loads(row["fields_json"] or "{}")
        except Exception:
            fields = {}
        try:
            turn_ids = tuple(json.loads(row["source_turn_ids_json"] or "[]"))
        except Exception:
            turn_ids = ()
        try:
            edited = json.loads(row["edited_fields_json"] or "{}")
        except Exception:
            edited = {}
        return IntakeDraftItemRecord(
            draft_id=row["draft_id"],
            session_id=row["session_id"],
            store_id=row["store_id"],
            mode=row["mode"],
            expert_name=row["expert_name"],
            topic=row["topic"],
            source_tag=row["source_tag"],
            fields=fields,
            source_quote=row["source_quote"] or "",
            source_turn_ids=turn_ids,
            review_status=row["review_status"],
            ingest_status=row["ingest_status"],
            reviewed_by=row["reviewed_by"] or "",
            reviewed_at=row["reviewed_at"] or "",
            edited_fields=edited,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def update_review_status(
        self,
        draft_id: str,
        decision: str,
        edited_fields: Optional[Mapping[str, str]] = None,
        reviewer: str = "",
    ) -> IntakeDraftItemRecord:
        """Cập nhật kết quả duyệt tại chỗ cho một mục nháp:

        - decision == "dung": review_status = "dung", ingest_status = "cho_nap"
        - decision == "sua": review_status = "da_sua", ingest_status = "cho_nap",
          cập nhật các trường đã sửa vào fields.
        - decision == "loai": review_status = "loai", ingest_status = "khong_nap"
          (tuyệt đối không chuyển sang cho_nap).
        """
        item = self.get_draft_item(draft_id)
        if item is None:
            raise ValueError("Không tìm thấy mục nháp %s trong staging." % draft_id)

        dec = str(decision or "").strip().lower()
        now = datetime.now().isoformat()
        rev_user = reviewer.strip() or item.expert_name or "chuyên gia"

        current_fields = dict(item.fields)
        record_edits: Dict[str, str] = {}

        if dec == STATUS_DUNG:
            new_review_status = STATUS_DUNG
            new_ingest_status = INGEST_CHO_NAP
        elif dec in (STATUS_DA_SUA, "sua"):
            new_review_status = STATUS_DA_SUA
            new_ingest_status = INGEST_CHO_NAP
            if edited_fields:
                for k, v in edited_fields.items():
                    if str(v or "").strip():
                        current_fields[k] = str(v).strip()
                        record_edits[k] = str(v).strip()
        elif dec == STATUS_LOAI:
            new_review_status = STATUS_LOAI
            new_ingest_status = INGEST_KHONG_NAP
        else:
            raise ValueError(
                "Lựa chọn duyệt không hợp lệ: %s (chỉ chấp nhận 'dung', 'sua', 'loai')."
                % decision
            )

        updated_item = IntakeDraftItemRecord(
            draft_id=item.draft_id,
            session_id=item.session_id,
            store_id=item.store_id,
            mode=item.mode,
            expert_name=item.expert_name,
            topic=item.topic,
            source_tag=item.source_tag,
            fields=current_fields,
            source_quote=item.source_quote,
            source_turn_ids=item.source_turn_ids,
            review_status=new_review_status,
            ingest_status=new_ingest_status,
            reviewed_by=rev_user,
            reviewed_at=now,
            edited_fields=record_edits or item.edited_fields,
            created_at=item.created_at,
            updated_at=now,
        )
        self.save_draft_item(updated_item)
        return updated_item

    def list_draft_items_by_store(
        self,
        store_id: str,
        ingest_status: Optional[str] = None,
        review_status: Optional[str] = None,
    ) -> List[IntakeDraftItemRecord]:
        """Liệt kê các mục nháp theo kho đích, đảm bảo phân vùng cách ly 100%."""
        sid = str(store_id or "").strip()
        if not sid:
            raise ValueError("Bắt buộc phải chỉ định store_id để truy vấn staging.")

        query = (
            "SELECT draft_id, session_id, store_id, mode, expert_name, topic, "
            "source_tag, fields_json, source_quote, source_turn_ids_json, "
            "review_status, ingest_status, reviewed_by, reviewed_at, "
            "edited_fields_json, created_at, updated_at "
            "FROM intake_draft_items WHERE store_id = ?"
        )
        params: List[Any] = [sid]
        if ingest_status:
            query += " AND ingest_status = ?"
            params.append(ingest_status)
        if review_status:
            query += " AND review_status = ?"
            params.append(review_status)
        query += " ORDER BY created_at DESC;"

        with self._connect() as conn:
            cur = conn.execute(query, params)
            return [self._row_to_draft_item(r) for r in cur.fetchall()]

    def list_all_draft_items(self) -> List[IntakeDraftItemRecord]:
        """Liệt kê toàn bộ mục nháp (phục vụ tính toán metric tổng hợp)."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT draft_id, session_id, store_id, mode, expert_name, topic,
                       source_tag, fields_json, source_quote, source_turn_ids_json,
                       review_status, ingest_status, reviewed_by, reviewed_at,
                       edited_fields_json, created_at, updated_at
                FROM intake_draft_items
                ORDER BY created_at DESC;
                """
            )
            return [self._row_to_draft_item(r) for r in cur.fetchall()]

    def clear(self) -> None:
        """Xóa toàn bộ dữ liệu staging (dùng trong test cách ly)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM intake_draft_items;")
            conn.execute("DELETE FROM intake_turns;")
            conn.execute("DELETE FROM intake_sessions;")
            conn.commit()
