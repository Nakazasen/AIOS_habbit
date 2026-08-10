"""Durable, idempotent job queue for unattended RAG v2 ingestion."""
from __future__ import annotations

import json, sqlite3, time, uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from aios_habit.benchmark_reference_registry import canonical_json, stable_hash

SCHEMA_VERSION = 1
JOB_STATUSES = frozenset({"QUEUED", "EXTRACTING", "EMBEDDING", "VERIFYING", "DEPLOYING", "READY", "WAITING_FOR_CAPACITY", "FAILED", "CANCELLED"})
ACTIVE_STATUSES = frozenset({"EXTRACTING", "EMBEDDING", "VERIFYING", "DEPLOYING"})
TERMINAL_STATUSES = frozenset({"READY", "FAILED", "CANCELLED"})
class IngestionJobError(RuntimeError): pass

@dataclass(frozen=True)
class IngestionJobIdentity:
    corpus_fingerprint: str
    model_identity: str
    chunking_identity: str
    schema_identity: str
    privacy_label: str
    def normalized(self) -> dict[str, str]:
        values = {key: str(value).strip() for key, value in asdict(self).items()}
        missing = [key for key, value in values.items() if not value]
        if missing: raise IngestionJobError("Ingestion identity is incomplete: " + ", ".join(missing))
        return values
    @property
    def idempotency_key(self) -> str: return stable_hash(self.normalized())

@dataclass(frozen=True)
class IngestionJob:
    job_id: str; idempotency_key: str; status: str; attempt_count: int
    completed_unit_count: int; total_unit_count: int; lease_owner: str
    lease_expires_at: float; next_attempt_at: float; last_error_code: str
Clock = Callable[[], float]

def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=30.0); connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON"); connection.execute("PRAGMA busy_timeout = 30000")
    return connection
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_metadata (singleton INTEGER PRIMARY KEY CHECK (singleton=1),schema_version INTEGER NOT NULL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS ingestion_jobs (job_id TEXT PRIMARY KEY,idempotency_key TEXT NOT NULL UNIQUE,identity_hash TEXT NOT NULL,identity_json TEXT NOT NULL,source_manifest_hash TEXT NOT NULL,source_manifest_json TEXT NOT NULL,status TEXT NOT NULL,attempt_count INTEGER NOT NULL DEFAULT 0,completed_unit_count INTEGER NOT NULL DEFAULT 0,total_unit_count INTEGER NOT NULL,lease_owner TEXT NOT NULL DEFAULT '',lease_token TEXT NOT NULL DEFAULT '',lease_expires_at REAL NOT NULL DEFAULT 0,next_attempt_at REAL NOT NULL DEFAULT 0,last_error_code TEXT NOT NULL DEFAULT '',created_at REAL NOT NULL,updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS ingestion_checkpoints (job_id TEXT NOT NULL REFERENCES ingestion_jobs(job_id) ON DELETE CASCADE,unit_id TEXT NOT NULL,ordinal INTEGER NOT NULL,unit_hash TEXT NOT NULL,payload_json TEXT NOT NULL,committed_at REAL NOT NULL,PRIMARY KEY(job_id,unit_id),UNIQUE(job_id,ordinal));
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_claim ON ingestion_jobs(status,next_attempt_at,lease_expires_at,created_at);
"""
class IngestionJobStore:
    """SQLite queue with atomic worker leases and per-unit checkpoints."""
    def __init__(self, path: str | Path, *, clock: Clock=time.time): self.path=Path(path); self._clock=clock; self.initialize()
    def initialize(self) -> None:
        connection=_connect(self.path)
        try:
            with connection:
                connection.executescript(_SCHEMA_SQL); row=connection.execute("SELECT schema_version FROM schema_metadata WHERE singleton=1").fetchone()
                if row is None: connection.execute("INSERT INTO schema_metadata VALUES(1,?,?)",(SCHEMA_VERSION,self._clock()))
                elif int(row["schema_version"])!=SCHEMA_VERSION: raise IngestionJobError(f"Unsupported schema: {row['schema_version']}")
        finally: connection.close()
    def submit(self, identity: IngestionJobIdentity, source_manifest: Sequence[Mapping[str,Any]]) -> tuple[IngestionJob,bool]:
        normalized=identity.normalized(); manifest=[dict(item) for item in source_manifest]; ids=[str(item.get("unit_id") or "").strip() for item in manifest]
        if not manifest or any(not item for item in ids) or len(set(ids))!=len(ids): raise IngestionJobError("Source manifest must be non-empty with unique unit IDs")
        identity_json=canonical_json(normalized); manifest_json=canonical_json(manifest); now=self._clock(); connection=_connect(self.path)
        try:
            with connection:
                row=connection.execute("SELECT * FROM ingestion_jobs WHERE idempotency_key=?",(identity.idempotency_key,)).fetchone()
                if row is not None:
                    if str(row["identity_json"])!=identity_json or str(row["source_manifest_json"])!=manifest_json: raise IngestionJobError("Idempotent submission drifted")
                    return _job(row),False
                job_id=f"INGEST-{identity.idempotency_key[:20]}"
                connection.execute("INSERT INTO ingestion_jobs(job_id,idempotency_key,identity_hash,identity_json,source_manifest_hash,source_manifest_json,status,total_unit_count,created_at,updated_at) VALUES(?,?,?,?,?,?,'QUEUED',?,?,?)",(job_id,identity.idempotency_key,stable_hash(normalized),identity_json,stable_hash(manifest),manifest_json,len(manifest),now,now))
                return _job(connection.execute("SELECT * FROM ingestion_jobs WHERE job_id=?",(job_id,)).fetchone()),True
        finally: connection.close()
    def get(self, job_id: str) -> IngestionJob:
        connection=_connect(self.path)
        try:
            row=connection.execute("SELECT * FROM ingestion_jobs WHERE job_id=?",(job_id,)).fetchone()
            if row is None: raise IngestionJobError(f"Unknown job: {job_id}")
            return _job(row)
        finally: connection.close()
    def claim(self, worker_id: str, *, lease_seconds: float=60.0) -> tuple[IngestionJob,str] | None:
        if not str(worker_id).strip() or lease_seconds<=0: raise IngestionJobError("Worker ID and positive lease required")
        now=self._clock(); token=uuid.uuid4().hex; connection=_connect(self.path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row=connection.execute("SELECT * FROM ingestion_jobs WHERE status NOT IN('READY','FAILED','CANCELLED') AND next_attempt_at<=? AND(status IN('QUEUED','WAITING_FOR_CAPACITY') OR lease_expires_at<=?) ORDER BY created_at,job_id LIMIT 1",(now,now)).fetchone()
            if row is None: connection.commit(); return None
            connection.execute("UPDATE ingestion_jobs SET status='EXTRACTING',attempt_count=attempt_count+1,lease_owner=?,lease_token=?,lease_expires_at=?,last_error_code='',updated_at=? WHERE job_id=?",(worker_id,token,now+lease_seconds,now,row["job_id"]))
            updated=connection.execute("SELECT * FROM ingestion_jobs WHERE job_id=?",(row["job_id"],)).fetchone(); connection.commit(); return _job(updated),token
        except Exception: connection.rollback(); raise
        finally: connection.close()
    def heartbeat(self, job_id: str, token: str, *, lease_seconds: float=60.0) -> IngestionJob:
        now=self._clock(); connection=_connect(self.path)
        try:
            with connection: self._require_lease(connection,job_id,token,now); connection.execute("UPDATE ingestion_jobs SET lease_expires_at=?,updated_at=? WHERE job_id=?",(now+lease_seconds,now,job_id))
            return self.get(job_id)
        finally: connection.close()
    def transition(self, job_id: str, token: str, status: str) -> IngestionJob:
        allowed={"EXTRACTING":{"EMBEDDING","FAILED","CANCELLED"},"EMBEDDING":{"VERIFYING","FAILED","CANCELLED"},"VERIFYING":{"DEPLOYING","FAILED","CANCELLED"},"DEPLOYING":{"READY","FAILED","CANCELLED"}}; now=self._clock(); connection=_connect(self.path)
        try:
            with connection:
                row=self._require_lease(connection,job_id,token,now)
                if status not in allowed.get(str(row["status"]),set()): raise IngestionJobError(f"Invalid transition: {row['status']} -> {status}")
                release=status in TERMINAL_STATUSES; connection.execute("UPDATE ingestion_jobs SET status=?,lease_owner=?,lease_token=?,lease_expires_at=?,updated_at=? WHERE job_id=?",(status,"" if release else row["lease_owner"],"" if release else token,0 if release else row["lease_expires_at"],now,job_id))
            return self.get(job_id)
        finally: connection.close()
    def checkpoint(self, job_id: str, token: str, *, unit_id: str, ordinal: int, payload: Mapping[str,Any]) -> IngestionJob:
        payload_json=canonical_json(dict(payload)); unit_hash=stable_hash(dict(payload)); now=self._clock(); connection=_connect(self.path)
        try:
            with connection:
                self._require_lease(connection,job_id,token,now); row=connection.execute("SELECT * FROM ingestion_checkpoints WHERE job_id=? AND unit_id=?",(job_id,unit_id)).fetchone()
                if row is None: connection.execute("INSERT INTO ingestion_checkpoints VALUES(?,?,?,?,?,?)",(job_id,unit_id,ordinal,unit_hash,payload_json,now))
                elif int(row["ordinal"])!=ordinal or str(row["unit_hash"])!=unit_hash or str(row["payload_json"])!=payload_json: raise IngestionJobError("Committed checkpoint cannot be changed")
                count=connection.execute("SELECT COUNT(*) FROM ingestion_checkpoints WHERE job_id=?",(job_id,)).fetchone()[0]; connection.execute("UPDATE ingestion_jobs SET completed_unit_count=?,updated_at=? WHERE job_id=?",(count,now,job_id))
            return self.get(job_id)
        finally: connection.close()
    def completed_unit_ids(self, job_id: str) -> set[str]:
        connection=_connect(self.path)
        try:
            result=set()
            for row in connection.execute("SELECT unit_id,unit_hash,payload_json FROM ingestion_checkpoints WHERE job_id=?",(job_id,)):
                try: payload=json.loads(str(row["payload_json"]))
                except json.JSONDecodeError as exc: raise IngestionJobError("Malformed checkpoint") from exc
                if stable_hash(payload)!=str(row["unit_hash"]): raise IngestionJobError("Checkpoint hash mismatch")
                result.add(str(row["unit_id"]))
            return result
        finally: connection.close()
    def retry(self, job_id: str, token: str, *, error_code: str, delay_seconds: float, capacity_wait: bool=False) -> IngestionJob:
        now=self._clock(); connection=_connect(self.path)
        try:
            with connection:
                self._require_lease(connection,job_id,token,now); connection.execute("UPDATE ingestion_jobs SET status=?,lease_owner='',lease_token='',lease_expires_at=0,next_attempt_at=?,last_error_code=?,updated_at=? WHERE job_id=?",("WAITING_FOR_CAPACITY" if capacity_wait else "QUEUED",now+delay_seconds,error_code,now,job_id))
            return self.get(job_id)
        finally: connection.close()
    @staticmethod
    def _require_lease(connection: sqlite3.Connection, job_id: str, token: str, now: float) -> sqlite3.Row:
        row=connection.execute("SELECT * FROM ingestion_jobs WHERE job_id=?",(job_id,)).fetchone()
        if row is None or not token or str(row["lease_token"])!=token or float(row["lease_expires_at"])<=now or str(row["status"]) not in ACTIVE_STATUSES: raise IngestionJobError("Lease is missing, stale, or owned elsewhere")
        return row

def _job(row: sqlite3.Row) -> IngestionJob:
    status=str(row["status"])
    if status not in JOB_STATUSES: raise IngestionJobError(f"Invalid stored status: {status}")
    return IngestionJob(str(row["job_id"]),str(row["idempotency_key"]),status,int(row["attempt_count"]),int(row["completed_unit_count"]),int(row["total_unit_count"]),str(row["lease_owner"]),float(row["lease_expires_at"]),float(row["next_attempt_at"]),str(row["last_error_code"]))
