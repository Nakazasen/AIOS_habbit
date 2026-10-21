"""Hàng đợi chuyên gia chống tắc nghẽn & Phê duyệt bảo mật mã PIN (Expert Review Queue).

Tuân thủ thiết kế Mục 5.6 - 5.8 Báo cáo Tự học (DESKTOP-AIOS-SELF-LEARN-HERMES-ANALYSIS-HOME)
và nhiệm vụ vé DESKTOP-SELF-LEARN-EXPERT-QUEUE-ROUTING-PIN:
- Van tiết lưu (Throttle valve): Chỉ nhận mục qua cổng xu hướng SMA(20) hoặc bản nháp đạt ngưỡng thăng hạng.
- Xếp hạng ưu tiên theo Priority Score: (khối lượng dislike x tần suất phục vụ).
- Leo thang theo tuổi (Aging escalation):
  + Quá 48h: nhắc nhở trong app (escalation_level=1).
  + Quá 7 ngày: leo thang sang chuyên gia dự phòng và báo quản trị (escalation_level=2).
- Công khai metric sức khỏe hàng đợi: số chờ theo chuyên gia, tuổi mục lâu nhất, tỷ lệ quá hạn.
- Bảo vệ thao tác duyệt (Ghi vào kho công ty):
  + Xác thực mã PIN 4-6 số (băm salt SHA-256 tại chỗ, khóa tạm 15 phút sau 5 lần sai).
  + Ràng buộc máy tính: kiểm tra đúng tên máy (hostname) đã đăng ký cho miền.
  + Đóng dấu kiểm toán đầy đủ: tài khoản Windows + tên máy + timestamp ISO UTC.
- Nguyên lý không phong tỏa (Non-blocking): Chuyên gia vắng mặt không làm dừng hệ thống hỏi đáp.

Lưu trữ bền vững SQLite cục bộ/mạng kèm ghi nhật ký kiểm toán JSONL.
Tương thích Python 3.11+.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

from aios_habit.expert_roles import (
    ExpertRoleRegistry,
    get_expert_role_registry,
    matches_subject,
)

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


DEFAULT_DB_PATH = _repo_root() / "local_cases" / "expert_review_queue.db"
DEFAULT_AUDIT_LOG = _repo_root() / "local_cases" / "approval_audit.jsonl"
DEFAULT_ADMIN_ALERTS_LOG = _repo_root() / "local_cases" / "expert_admin_alerts.jsonl"
DEFAULT_PIN_CONFIG = _repo_root() / "local_cases" / "expert_pin_config.json"
DEFAULT_PIN_ATTEMPTS = _repo_root() / "local_cases" / "expert_pin_attempts.json"

PIN_MIN_LEN = 4
PIN_MAX_LEN = 6
MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_SECONDS = 15 * 60  # 15 phút

AGING_REMINDER_SECONDS = 48 * 3600  # 48 giờ
AGING_ESCALATION_SECONDS = 7 * 86400  # 7 ngày

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_REVISED = "revised"

SOURCE_SMA_ALERT = "sma_negative_alert"
SOURCE_DRAFT_PROMOTION = "draft_promotion"
SOURCE_TIER5_INQUIRY = "tier5_inquiry"
SOURCE_USER_CORRECTION = "user_correction"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def compute_priority_score(
    dislike_count: int,
    service_frequency: int,
    dislike_ratio: float = 0.0,
    like_count: int = 0,
) -> float:
    """Tính điểm ưu tiên xếp hạng hàng đợi theo thiết kế Mục 5.7:

    Priority Score = (khối lượng dislike * tần suất phục vụ) + (tỷ lệ dislike * 10)
    Nếu là bản nháp thăng hạng (dislike=0):
    Priority Score = (like_count * tần suất phục vụ) / 2.0
    """
    freq = max(1, int(service_frequency))
    dl = max(0, int(dislike_count))
    ratio = max(0.0, float(dislike_ratio))

    if dl > 0:
        base_score = float(dl * freq) + (ratio * 10.0)
    else:
        # Mục đề xuất thăng hạng dựa trên Like cao
        lk = max(0, int(like_count))
        base_score = float(lk * freq) / 2.0

    return round(base_score, 2)


@dataclass
class QueueItem:
    """Đại diện cho một mục trong hàng đợi duyệt chuyên gia."""

    item_id: str
    source_type: str
    domain_id: str
    title: str
    question: str
    draft_answer: str = ""
    source_file: str = ""
    conversation_id: str = ""
    message_id: str = ""
    dislike_count: int = 0
    like_count: int = 0
    service_frequency: int = 1
    priority_score: float = 0.0
    assigned_expert: str = ""
    status: str = STATUS_PENDING
    escalation_level: int = 0  # 0: bình thường, 1: nhắc nhở 48h, 2: leo thang 7 ngày
    escalated_to: str = ""
    admin_alerted: int = 0
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    due_at_reminder: str = ""
    due_at_escalate: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.item_id:
            self.item_id = f"QITEM-{uuid.uuid4().hex[:8].upper()}"
        if not self.priority_score:
            ratio = 0.0
            total = self.dislike_count + self.like_count
            if total > 0:
                ratio = self.dislike_count / total
            self.priority_score = compute_priority_score(
                self.dislike_count,
                self.service_frequency,
                ratio,
                self.like_count,
            )
        if not self.due_at_reminder:
            try:
                dt = datetime.fromisoformat(self.created_at)
            except Exception:
                dt = _utc_now()
            self.due_at_reminder = (dt + timedelta(seconds=AGING_REMINDER_SECONDS)).isoformat()
            self.due_at_escalate = (dt + timedelta(seconds=AGING_ESCALATION_SECONDS)).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class QueueHealthMetrics:
    """Chỉ số sức khỏe hàng đợi chuyên gia công khai."""

    total_pending: int
    pending_by_expert: Dict[str, int]
    pending_by_domain: Dict[str, int]
    oldest_item_age_hours: float
    oldest_item_id: Optional[str]
    overdue_48h_count: int
    overdue_7d_count: int
    overdue_rate: float
    escalated_to_backup_count: int
    calculated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThrottleResult:
    """Kết quả kiểm tra qua van tiết lưu."""

    accepted: bool
    reason: str
    item_id: Optional[str] = None


@dataclass
class ApprovalAuditStamp:
    """Dấu kiểm toán đầy đủ khi chuyên gia thực hiện thao tác duyệt."""

    audit_id: str
    item_id: str
    decision: str
    actor_subject: str
    actor_machine: str
    actor_role: str
    timestamp: str
    destination: str
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExpertReviewQueueRepository:
    """Kho lưu trữ hàng đợi chuyên gia dựa trên SQLite, an toàn đa luồng."""

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        registry: Optional[ExpertRoleRegistry] = None,
        audit_log_path: Optional[Union[str, Path]] = None,
        admin_alerts_path: Optional[Union[str, Path]] = None,
        pin_config_path: Optional[Union[str, Path]] = None,
        pin_attempts_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.registry = registry or get_expert_role_registry()
        self.audit_log_path = Path(audit_log_path) if audit_log_path else DEFAULT_AUDIT_LOG
        self.admin_alerts_path = Path(admin_alerts_path) if admin_alerts_path else DEFAULT_ADMIN_ALERTS_LOG
        self.pin_config_path = Path(pin_config_path) if pin_config_path else DEFAULT_PIN_CONFIG
        self.pin_attempts_path = Path(pin_attempts_path) if pin_attempts_path else DEFAULT_PIN_ATTEMPTS

        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queue_items (
                    item_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    domain_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    question TEXT NOT NULL,
                    draft_answer TEXT,
                    source_file TEXT,
                    conversation_id TEXT,
                    message_id TEXT,
                    dislike_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    service_frequency INTEGER DEFAULT 1,
                    priority_score REAL DEFAULT 0.0,
                    assigned_expert TEXT,
                    status TEXT DEFAULT 'pending',
                    escalation_level INTEGER DEFAULT 0,
                    escalated_to TEXT DEFAULT '',
                    admin_alerted INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    due_at_reminder TEXT NOT NULL,
                    due_at_escalate TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_audit_trail (
                    audit_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    actor_subject TEXT NOT NULL,
                    actor_machine TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    notes TEXT,
                    metadata_json TEXT DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_escalation_alerts (
                    alert_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    domain_id TEXT NOT NULL,
                    original_expert TEXT NOT NULL,
                    escalated_expert TEXT NOT NULL,
                    age_days REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active'
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_qi_status ON queue_items (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_qi_domain ON queue_items (domain_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_qi_priority ON queue_items (priority_score DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_qi_expert ON queue_items (assigned_expert)")

    # -------------------------------------------------------------------------
    # 1. VAN TIẾT LƯU (THROTTLE VALVE) & TIẾP NHẬN MỤC HÀNG ĐỢI
    # -------------------------------------------------------------------------
    def evaluate_throttle_gate(
        self,
        source_type: str,
        *,
        dislike_count: int = 0,
        like_count: int = 0,
        sample_count: int = 0,
        invocation_count: int = 0,
        reason_category: str = "",
        tier_level: int = 0,
    ) -> Tuple[bool, str]:
        """Kiểm tra điều kiện qua van tiết lưu:

        1. Cảnh báo xu hướng xấu SMA(20):
           - Phải đạt: dislike >= 3 và tỷ lệ dislike >= 30% (hoặc có lý do cụ thể và dislike >= 2).
        2. Bản nháp đề xuất thăng hạng (draft promotion):
           - Phải đạt: gọi trên 3 lần (invocation > 3) VÀ like_ratio >= 80%, hoặc like >= 5 và like_ratio >= 85%.
        3. Yêu cầu hỗ trợ Nấc thang 5 (Tier 5):
           - Được chấp nhận vì người dùng chủ động yêu cầu chuyển chuyên gia.
        4. Các đánh giá chê lẻ tẻ chưa đạt ngưỡng:
           - Bị chặn lại ở van tiết lưu để chống tắc nghẽn.
        """
        stype = source_type.strip().lower()

        if stype in (SOURCE_TIER5_INQUIRY, "tier5"):
            return True, "Chấp nhận: Yêu cầu nấc thang 5 từ người dùng."

        if stype in (SOURCE_SMA_ALERT, "negative_alert", "dislike"):
            total_samples = max(sample_count, dislike_count + like_count)
            ratio = (dislike_count / total_samples) if total_samples > 0 else 0.0

            # Ngưỡng SMA(20) chuẩn: Dislike >= 3 và tỷ lệ >= 30%
            if dislike_count >= 3 and ratio >= 0.30:
                return True, f"Chấp nhận: Đạt ngưỡng cảnh báo SMA(20) (Dislike={dislike_count}, Tỷ lệ={ratio*100:.1f}%)."

            # Hoặc có phân loại lý do cụ thể và có từ 2 dislike trở lên
            if reason_category and reason_category in ("sai", "kho_hieu", "thieu_nguon", "lac_de") and dislike_count >= 2:
                return True, f"Chấp nhận: Có phân loại lý do '{reason_category}' và tích lũy {dislike_count} dislike."

            return False, (
                f"Chưa qua van tiết lưu: Đánh giá chê lẻ tẻ chưa vượt ngưỡng xu hướng SMA(20) "
                f"(hiện tại: {dislike_count} dislike / {total_samples} mẫu, tỷ lệ {ratio*100:.1f}%)."
            )

        if stype in (SOURCE_DRAFT_PROMOTION, "draft"):
            total_fb = dislike_count + like_count
            like_ratio = (like_count / total_fb) if total_fb > 0 else (1.0 if like_count > 0 else 0.0)

            # Quy chuẩn thăng hạng bản nháp: Gọi > 3 lần và tỷ lệ Like >= 80%
            if invocation_count > 3 and like_count >= 1 and (dislike_count == 0 or like_ratio >= 0.80):
                return True, f"Chấp nhận: Bản nháp đủ điều kiện thăng hạng (Gọi {invocation_count} lần, Tỷ lệ like {like_ratio*100:.1f}%)."

            # Ngưỡng tri thức ứng viên SMA(20): Like >= 5 và tỷ lệ Like >= 85%
            if like_count >= 5 and like_ratio >= 0.85:
                return True, f"Chấp nhận: Đạt chuẩn ứng viên tri thức SMA(20) (Like={like_count}, Tỷ lệ={like_ratio*100:.1f}%)."

            return False, (
                f"Chưa qua van tiết lưu: Bản nháp chưa đạt ngưỡng thăng hạng "
                f"(hiện tại: {invocation_count} lượt gọi, {like_count} like, {dislike_count} dislike)."
            )

        if stype in (SOURCE_USER_CORRECTION, "correction"):
            return True, "Chấp nhận: Bản ghi hiệu chỉnh trực tiếp từ người dùng."

        return False, f"Chưa qua van tiết lưu: Loại nguồn '{source_type}' không được hỗ trợ."

    def submit_to_queue(
        self,
        source_type: str,
        question: str,
        *,
        title: str = "",
        draft_answer: str = "",
        source_file: str = "",
        conversation_id: str = "",
        message_id: str = "",
        collection_id: str = "",
        dislike_count: int = 0,
        like_count: int = 0,
        service_frequency: int = 1,
        sample_count: int = 0,
        invocation_count: int = 0,
        reason_category: str = "",
        domain_id: Optional[str] = None,
        assigned_expert: Optional[str] = None,
        force_pass_throttle: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ThrottleResult:
        """Kiểm tra qua van tiết lưu, định tuyến miền và lưu vào SQLite nếu đạt chuẩn."""
        # 1. Kiểm tra van tiết lưu
        if not force_pass_throttle:
            accepted, reason = self.evaluate_throttle_gate(
                source_type,
                dislike_count=dislike_count,
                like_count=like_count,
                sample_count=sample_count,
                invocation_count=invocation_count,
                reason_category=reason_category,
            )
            if not accepted:
                return ThrottleResult(accepted=False, reason=reason)
        else:
            reason = "Bỏ qua van tiết lưu theo yêu cầu cưỡng bức."

        # 2. Định tuyến miền
        resolved_domain = domain_id or self.registry.resolve_domain(
            collection_id=collection_id,
            question=question,
        )

        # 3. Phân công chuyên gia chính của miền
        expert = assigned_expert or self.registry.get_assigned_expert(resolved_domain, is_escalated=False)

        # 4. Tạo đối tượng QueueItem
        item_title = title or (question[:80] + ("..." if len(question) > 80 else ""))
        item = QueueItem(
            item_id=f"QITEM-{uuid.uuid4().hex[:8].upper()}",
            source_type=source_type,
            domain_id=resolved_domain,
            title=item_title,
            question=question,
            draft_answer=draft_answer,
            source_file=source_file,
            conversation_id=conversation_id,
            message_id=message_id,
            dislike_count=dislike_count,
            like_count=like_count,
            service_frequency=service_frequency,
            assigned_expert=expert,
            status=STATUS_PENDING,
            metadata=metadata or {},
        )

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO queue_items (
                    item_id, source_type, domain_id, title, question, draft_answer,
                    source_file, conversation_id, message_id, dislike_count, like_count,
                    service_frequency, priority_score, assigned_expert, status,
                    escalation_level, escalated_to, admin_alerted, created_at, updated_at,
                    due_at_reminder, due_at_escalate, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.item_id,
                    item.source_type,
                    item.domain_id,
                    item.title,
                    item.question,
                    item.draft_answer,
                    item.source_file,
                    item.conversation_id,
                    item.message_id,
                    item.dislike_count,
                    item.like_count,
                    item.service_frequency,
                    item.priority_score,
                    item.assigned_expert,
                    item.status,
                    item.escalation_level,
                    item.escalated_to,
                    item.admin_alerted,
                    item.created_at,
                    item.updated_at,
                    item.due_at_reminder,
                    item.due_at_escalate,
                    json.dumps(item.metadata, ensure_ascii=False),
                ),
            )

        return ThrottleResult(accepted=True, reason=reason, item_id=item.item_id)

    # -------------------------------------------------------------------------
    # 2. TRUY VẤN VÀ DANH SÁCH HÀNG ĐỢI
    # -------------------------------------------------------------------------
    def get_item(self, item_id: str) -> Optional[QueueItem]:
        """Lấy một mục hàng đợi theo ID."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM queue_items WHERE item_id = ?", (item_id,)).fetchone()
            if not row:
                return None
            return self._row_to_item(row)

    def list_pending_items(
        self,
        domain_id: Optional[str] = None,
        expert_subject: Optional[str] = None,
        limit: int = 50,
    ) -> List[QueueItem]:
        """Lấy danh sách các mục đang chờ xử lý, sắp xếp theo Priority Score giảm dần."""
        query = "SELECT * FROM queue_items WHERE status = 'pending'"
        params: List[Any] = []

        if domain_id:
            query += " AND domain_id = ?"
            params.append(domain_id)

        query += " ORDER BY priority_score DESC, created_at ASC LIMIT ?"
        params.append(limit)

        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
            items = [self._row_to_item(r) for r in rows]

        # Lọc theo chuyên gia nếu có truyền subject
        if expert_subject:
            filtered: List[QueueItem] = []
            for it in items:
                # Kiểm tra phân công trực tiếp hoặc leo thang
                target_expert = it.escalated_to if (it.escalation_level >= 2 and it.escalated_to) else it.assigned_expert
                if matches_subject(expert_subject, target_expert):
                    filtered.append(it)
                elif self.registry.is_expert_for_domain(expert_subject, it.domain_id):
                    # Nếu là chuyên gia của miền đó cũng được thấy
                    filtered.append(it)
            return filtered

        return items

    def _row_to_item(self, row: sqlite3.Row) -> QueueItem:
        meta = {}
        try:
            meta = json.loads(row["metadata_json"] or "{}")
        except Exception:
            pass
        return QueueItem(
            item_id=row["item_id"],
            source_type=row["source_type"],
            domain_id=row["domain_id"],
            title=row["title"],
            question=row["question"],
            draft_answer=row["draft_answer"] or "",
            source_file=row["source_file"] or "",
            conversation_id=row["conversation_id"] or "",
            message_id=row["message_id"] or "",
            dislike_count=int(row["dislike_count"]),
            like_count=int(row["like_count"]),
            service_frequency=int(row["service_frequency"]),
            priority_score=float(row["priority_score"]),
            assigned_expert=row["assigned_expert"] or "",
            status=row["status"],
            escalation_level=int(row["escalation_level"]),
            escalated_to=row["escalated_to"] or "",
            admin_alerted=int(row["admin_alerted"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            due_at_reminder=row["due_at_reminder"],
            due_at_escalate=row["due_at_escalate"],
            metadata=meta,
        )

    # -------------------------------------------------------------------------
    # 3. LEO THANG THEO TUỔI (AGING ESCALATION)
    # -------------------------------------------------------------------------
    def check_and_apply_escalations(
        self,
        reference_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Quét các mục pending và áp dụng cơ chế leo thang theo tuổi:

        1. Quá 48h (age >= 48h): Nâng escalation_level=1 (nhắc nhở nổi bật).
        2. Quá 7 ngày (age >= 168h): Nâng escalation_level=2, chuyển chuyên gia dự phòng,
           ghi nhận cảnh báo quản trị và gửi thông báo.
        """
        ref_dt = reference_time or _utc_now()
        events: List[Dict[str, Any]] = []

        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM queue_items WHERE status = 'pending'").fetchall()

            for row in rows:
                item_id = row["item_id"]
                domain_id = row["domain_id"]
                created_str = row["created_at"]
                current_level = int(row["escalation_level"])
                assigned_exp = row["assigned_expert"] or ""

                try:
                    c_dt = datetime.fromisoformat(created_str)
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue

                age_seconds = (ref_dt - c_dt).total_seconds()
                age_days = round(age_seconds / 86400.0, 2)

                # Kiểm tra mức 2: Quá 7 ngày
                if age_seconds >= AGING_ESCALATION_SECONDS and current_level < 2:
                    # Chuyển sang chuyên gia dự phòng
                    backup_expert = self.registry.get_assigned_expert(domain_id, is_escalated=True)
                    alert_id = f"ALERT-{uuid.uuid4().hex[:8].upper()}"

                    conn.execute(
                        """
                        UPDATE queue_items
                        SET escalation_level = 2,
                            escalated_to = ?,
                            admin_alerted = 1,
                            updated_at = ?
                        WHERE item_id = ?
                        """,
                        (backup_expert, ref_dt.isoformat(), item_id),
                    )

                    conn.execute(
                        """
                        INSERT INTO admin_escalation_alerts (
                            alert_id, item_id, domain_id, original_expert, escalated_expert, age_days, created_at, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                        """,
                        (alert_id, item_id, domain_id, assigned_exp, backup_expert, age_days, ref_dt.isoformat()),
                    )

                    event = {
                        "item_id": item_id,
                        "action": "escalate_to_backup",
                        "level": 2,
                        "domain_id": domain_id,
                        "original_expert": assigned_exp,
                        "escalated_to": backup_expert,
                        "age_days": age_days,
                        "alert_id": alert_id,
                        "timestamp": ref_dt.isoformat(),
                    }
                    events.append(event)
                    self._record_admin_alert_log(event)

                # Kiểm tra mức 1: Quá 48 giờ
                elif age_seconds >= AGING_REMINDER_SECONDS and current_level < 1:
                    conn.execute(
                        """
                        UPDATE queue_items
                        SET escalation_level = 1,
                            updated_at = ?
                        WHERE item_id = ?
                        """,
                        (ref_dt.isoformat(), item_id),
                    )
                    event = {
                        "item_id": item_id,
                        "action": "reminder_48h",
                        "level": 1,
                        "domain_id": domain_id,
                        "assigned_expert": assigned_exp,
                        "age_days": age_days,
                        "timestamp": ref_dt.isoformat(),
                    }
                    events.append(event)

        return events

    def _record_admin_alert_log(self, event: Dict[str, Any]) -> None:
        """Ghi nhận cảnh báo leo thang quản trị vào tệp JSONL."""
        try:
            self.admin_alerts_path.parent.mkdir(parents=True, exist_ok=True)
            with self.admin_alerts_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 4. CHỈ SỐ SỨC KHỎE HÀNG ĐỢI CÔNG KHAI (QUEUE HEALTH METRICS)
    # -------------------------------------------------------------------------
    def get_queue_health_metrics(self, reference_time: Optional[datetime] = None) -> QueueHealthMetrics:
        """Tính toán các chỉ số sức khỏe hàng đợi chuyên gia:

        - Tổng số mục chờ (total_pending)
        - Số mục chờ theo từng chuyên gia (pending_by_expert)
        - Số mục chờ theo miền (pending_by_domain)
        - Tuổi của mục tồn đọng lâu nhất (oldest_item_age_hours)
        - Tỷ lệ quá hạn (overdue_rate)
        """
        ref_dt = reference_time or _utc_now()

        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM queue_items WHERE status = 'pending'").fetchall()

            total_pending = len(rows)
            pending_by_exp: Dict[str, int] = {}
            pending_by_domain: Dict[str, int] = {}
            oldest_age_hours = 0.0
            oldest_id: Optional[str] = None
            overdue_48h = 0
            overdue_7d = 0
            escalated_count = 0

            for r in rows:
                item_id = r["item_id"]
                domain_id = r["domain_id"]
                assigned = r["escalated_to"] if (int(r["escalation_level"]) >= 2 and r["escalated_to"]) else r["assigned_expert"]
                assigned_clean = assigned or "chua_phan_cong"

                pending_by_exp[assigned_clean] = pending_by_exp.get(assigned_clean, 0) + 1
                pending_by_domain[domain_id] = pending_by_domain.get(domain_id, 0) + 1

                if int(r["escalation_level"]) >= 2:
                    escalated_count += 1

                try:
                    c_dt = datetime.fromisoformat(r["created_at"])
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                    age_h = (ref_dt - c_dt).total_seconds() / 3600.0
                    if age_h > oldest_age_hours:
                        oldest_age_hours = age_h
                        oldest_id = item_id

                    if age_h >= 48.0:
                        overdue_48h += 1
                    if age_h >= 168.0:
                        overdue_7d += 1
                except Exception:
                    pass

            overdue_rate = round((overdue_48h / total_pending), 4) if total_pending > 0 else 0.0

            return QueueHealthMetrics(
                total_pending=total_pending,
                pending_by_expert=pending_by_exp,
                pending_by_domain=pending_by_domain,
                oldest_item_age_hours=round(oldest_age_hours, 2),
                oldest_item_id=oldest_id,
                overdue_48h_count=overdue_48h,
                overdue_7d_count=overdue_7d,
                overdue_rate=overdue_rate,
                escalated_to_backup_count=escalated_count,
                calculated_at=ref_dt.isoformat(),
            )

    # -------------------------------------------------------------------------
    # 5. XÁC THỰC MÃ PIN & KIỂM TRA RÀNG BUỘC MÁY (MACHINE BINDING)
    # -------------------------------------------------------------------------
    def set_expert_pin(self, pin: str) -> Dict[str, Any]:
        """Thiết lập hoặc cập nhật mã PIN chuyên gia (lưu salt + hash SHA-256)."""
        clean_pin = str(pin or "").strip()
        if len(clean_pin) < PIN_MIN_LEN or len(clean_pin) > PIN_MAX_LEN or not clean_pin.isdigit():
            return {
                "ok": False,
                "error_vi": f"Mã PIN phải gồm từ {PIN_MIN_LEN} đến {PIN_MAX_LEN} chữ số.",
            }

        salt = secrets.token_hex(16)
        payload_bytes = f"{salt}:{clean_pin}".encode("utf-8")
        pin_hash = hashlib.sha256(payload_bytes).hexdigest()

        self.pin_config_path.parent.mkdir(parents=True, exist_ok=True)
        store = {"salt": salt, "pin_hash": pin_hash, "updated_at": _utc_now_iso()}
        self.pin_config_path.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")

        self._clear_failed_attempts()
        return {"ok": True}

    def _load_pin_store(self) -> Dict[str, Any]:
        if not self.pin_config_path.exists():
            return {}
        try:
            return json.loads(self.pin_config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _read_pin_attempts(self) -> Dict[str, Any]:
        if not self.pin_attempts_path.exists():
            return {"failed": 0, "locked_until": 0.0}
        try:
            return json.loads(self.pin_attempts_path.read_text(encoding="utf-8"))
        except Exception:
            return {"failed": 0, "locked_until": 0.0}

    def _write_pin_attempts(self, failed: int, locked_until: float) -> None:
        self.pin_attempts_path.parent.mkdir(parents=True, exist_ok=True)
        self.pin_attempts_path.write_text(
            json.dumps({"failed": failed, "locked_until": locked_until}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _clear_failed_attempts(self) -> None:
        self._write_pin_attempts(0, 0.0)

    def is_pin_locked(self, now: Optional[float] = None) -> bool:
        """Kiểm tra mã PIN có đang bị tạm khóa sau 5 lần nhập sai không."""
        cur = now if now is not None else time.time()
        state = self._read_pin_attempts()
        return cur < float(state.get("locked_until", 0.0))

    def verify_expert_pin(self, pin: str, now: Optional[float] = None) -> Dict[str, Any]:
        """Xác thực mã PIN chuyên gia.

        - Khóa tạm 15 phút nếu sai 5 lần.
        - So sánh hash không lộ thời gian (constant-time comparison).
        - Fail-closed an toàn tuyệt đối.
        """
        cur = now if now is not None else time.time()
        if self.is_pin_locked(now=cur):
            state = self._read_pin_attempts()
            remaining = int(float(state.get("locked_until", 0.0)) - cur)
            return {
                "ok": False,
                "error_vi": f"Bạn đã nhập sai {MAX_FAILED_ATTEMPTS} lần liên tiếp. Quyền duyệt bị khóa tạm trong {max(1, remaining // 60)} phút.",
            }

        store = self._load_pin_store()
        salt = store.get("salt", "")
        expected_hash = store.get("pin_hash", "")

        if not salt or not expected_hash:
            return {
                "ok": False,
                "error_vi": "Chưa thiết lập mã PIN phê duyệt chuyên gia trên hệ thống.",
            }

        candidate_bytes = f"{salt}:{str(pin or '').strip()}".encode("utf-8")
        candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()

        if hmac.compare_digest(candidate_hash, expected_hash):
            self._clear_failed_attempts()
            return {"ok": True}

        # Đếm lượt nhập sai
        state = self._read_pin_attempts()
        failed = int(state.get("failed", 0)) + 1
        locked_until = 0.0
        if failed >= MAX_FAILED_ATTEMPTS:
            locked_until = cur + LOCK_DURATION_SECONDS

        self._write_pin_attempts(failed, locked_until)

        if failed >= MAX_FAILED_ATTEMPTS:
            return {
                "ok": False,
                "error_vi": f"Bạn đã nhập sai 5 lần. Quyền duyệt bị tạm khóa trong 15 phút để bảo vệ an toàn.",
            }

        return {
            "ok": False,
            "error_vi": f"Mã PIN chưa đúng. Bạn còn {MAX_FAILED_ATTEMPTS - failed} lần thử.",
        }

    # -------------------------------------------------------------------------
    # 6. BẢO VỆ THAO TÁC DUYỆT (GHI VÀO KHO CÔNG TY & ĐÓNG DẤU KIỂM TOÁN)
    # -------------------------------------------------------------------------
    def approve_queue_item(
        self,
        item_id: str,
        actor_subject: str,
        pin: str,
        *,
        machine_node: Optional[str] = None,
        notes: str = "",
        destination: str = "company_knowledge",
        updated_draft: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Phê duyệt mục hàng đợi và ghi nhận vào kho công ty.

        Bắt buộc kiểm tra:
        1. Mục tồn tại và đang ở trạng thái pending.
        2. Quyền chuyên gia: actor_subject phải là chuyên gia của miền đó.
        3. Ràng buộc máy tính: machine_node phải khớp danh sách máy được cấp phép.
        4. Xác thực mã PIN: đúng mã và không bị khóa.
        5. Đóng dấu kiểm toán đầy đủ vào SQLite và JSONL.
        """
        item = self.get_item(item_id)
        if not item:
            return {"ok": False, "error_vi": f"Không tìm thấy mục hàng đợi: {item_id}"}
        if item.status != STATUS_PENDING:
            return {"ok": False, "error_vi": f"Mục này đã được xử lý (trạng thái: {item.status})."}

        current_node = machine_node or platform.node()

        # 1. Kiểm tra thẩm quyền chuyên gia
        if not self.registry.is_expert_for_domain(actor_subject, item.domain_id):
            return {
                "ok": False,
                "error_vi": f"Tài khoản '{actor_subject}' không thuộc danh sách chuyên gia của miền '{item.domain_id}'.",
            }

        # 2. Kiểm tra ràng buộc máy tính
        if not self.registry.is_machine_authorized(item.domain_id, current_node):
            return {
                "ok": False,
                "error_vi": f"Máy tính '{current_node}' không được cấp phép phê duyệt tri thức cho miền '{item.domain_id}'.",
            }

        # 3. Xác thực mã PIN
        pin_check = self.verify_expert_pin(pin)
        if not pin_check.get("ok"):
            return pin_check

        # 4. Xác định vai trò chuyên gia
        dconf = self.registry.get_domain(item.domain_id)
        role_label = "primary_expert" if (dconf and matches_subject(actor_subject, dconf.primary_expert)) else "backup_expert"

        # 5. Cập nhật trạng thái mục hàng đợi
        now_iso = _utc_now_iso()
        audit_id = f"AUDIT-{uuid.uuid4().hex[:8].upper()}"

        audit_stamp = ApprovalAuditStamp(
            audit_id=audit_id,
            item_id=item_id,
            decision=STATUS_APPROVED,
            actor_subject=actor_subject,
            actor_machine=current_node,
            actor_role=f"{item.domain_id}:{role_label}",
            timestamp=now_iso,
            destination=destination,
            notes=notes or "Chuyên gia phê duyệt đưa vào kho công ty.",
            metadata={
                "question": item.question,
                "domain_id": item.domain_id,
                "priority_score": item.priority_score,
            },
        )

        if updated_draft is not None and updated_draft.strip():
            item.draft_answer = updated_draft.strip()

        with self._connection() as conn:
            conn.execute(
                """
                UPDATE queue_items
                SET status = 'approved',
                    draft_answer = ?,
                    updated_at = ?
                WHERE item_id = ?
                """,
                (item.draft_answer, now_iso, item_id),
            )
            conn.execute(
                """
                INSERT INTO approval_audit_trail (
                    audit_id, item_id, decision, actor_subject, actor_machine,
                    actor_role, timestamp, destination, notes, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_stamp.audit_id,
                    audit_stamp.item_id,
                    audit_stamp.decision,
                    audit_stamp.actor_subject,
                    audit_stamp.actor_machine,
                    audit_stamp.actor_role,
                    audit_stamp.timestamp,
                    audit_stamp.destination,
                    audit_stamp.notes,
                    json.dumps(audit_stamp.metadata, ensure_ascii=False),
                ),
            )

        # 6. Ghi nhật ký kiểm toán JSONL bất biến
        self._record_approval_audit_log(audit_stamp)

        # 7. Ghi vào kho tri thức công ty (Memory Vault) nếu cần
        vault_res = self._write_to_company_vault(item, audit_stamp)

        return {
            "ok": True,
            "item_id": item_id,
            "status": STATUS_APPROVED,
            "audit_stamp": audit_stamp.to_dict(),
            "vault_result": vault_res,
        }

    def reject_queue_item(
        self,
        item_id: str,
        actor_subject: str,
        pin: Optional[str] = None,
        *,
        reason: str,
        machine_node: Optional[str] = None,
        decision_status: str = STATUS_REJECTED,
        require_pin: bool = False,
    ) -> Dict[str, Any]:
        """Từ chối hoặc yêu cầu trả sửa mục hàng đợi kèm lý do bắt buộc."""
        if not reason or not reason.strip():
            return {"ok": False, "error_vi": "Vui lòng nhập lý do từ chối / trả sửa để hoàn thiện kiểm toán."}

        item = self.get_item(item_id)
        if not item:
            return {"ok": False, "error_vi": f"Không tìm thấy mục hàng đợi: {item_id}"}
        if item.status != STATUS_PENDING:
            return {"ok": False, "error_vi": f"Mục này đã được xử lý (trạng thái: {item.status})."}

        current_node = machine_node or platform.node()

        if not self.registry.is_expert_for_domain(actor_subject, item.domain_id):
            return {"ok": False, "error_vi": "Không có quyền chuyên gia trên miền này."}

        if not self.registry.is_machine_authorized(item.domain_id, current_node):
            return {"ok": False, "error_vi": f"Máy tính '{current_node}' không được cấp phép."}

        # Nếu yêu cầu PIN hoặc chuyên gia nhập PIN thì xác thực, ngược lại cho phép trả sửa kèm lý do
        if require_pin or (pin is not None and str(pin).strip() != ""):
            pin_check = self.verify_expert_pin(str(pin).strip())
            if not pin_check.get("ok"):
                return pin_check

        now_iso = _utc_now_iso()
        audit_id = f"AUDIT-{uuid.uuid4().hex[:8].upper()}"
        decision = decision_status if decision_status in (STATUS_REJECTED, STATUS_REVISED) else STATUS_REJECTED
        audit_stamp = ApprovalAuditStamp(
            audit_id=audit_id,
            item_id=item_id,
            decision=decision,
            actor_subject=actor_subject,
            actor_machine=current_node,
            actor_role=f"{item.domain_id}:expert",
            timestamp=now_iso,
            destination="none",
            notes=reason.strip(),
        )

        with self._connection() as conn:
            conn.execute(
                "UPDATE queue_items SET status = ?, updated_at = ? WHERE item_id = ?",
                (decision, now_iso, item_id),
            )
            conn.execute(
                """
                INSERT INTO approval_audit_trail (
                    audit_id, item_id, decision, actor_subject, actor_machine,
                    actor_role, timestamp, destination, notes, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_stamp.audit_id,
                    audit_stamp.item_id,
                    audit_stamp.decision,
                    audit_stamp.actor_subject,
                    audit_stamp.actor_machine,
                    audit_stamp.actor_role,
                    audit_stamp.timestamp,
                    audit_stamp.destination,
                    audit_stamp.notes,
                    json.dumps(audit_stamp.metadata, ensure_ascii=False),
                ),
            )

        self._record_approval_audit_log(audit_stamp)
        return {"ok": True, "item_id": item_id, "status": decision, "audit_stamp": audit_stamp.to_dict()}

    def _record_approval_audit_log(self, stamp: ApprovalAuditStamp) -> None:
        try:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(stamp.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _write_to_company_vault(self, item: QueueItem, stamp: ApprovalAuditStamp) -> Dict[str, Any]:
        """Ghi tri thức đã được chuyên gia phê duyệt vào phân vùng kho công ty."""
        vault_file = Path("05_memory_vault/memory_units.jsonl")
        try:
            vault_file.parent.mkdir(parents=True, exist_ok=True)
            unit_id = f"MU-{uuid.uuid4().hex[:8].upper()}"
            record = {
                "unit_id": unit_id,
                "title": item.title,
                "question": item.question,
                "statement": item.draft_answer or item.title,
                "scope": f"domain:{item.domain_id}",
                "status": "verified",
                "partition": "company_knowledge",
                "approved_by": stamp.actor_subject,
                "approved_machine": stamp.actor_machine,
                "approved_at": stamp.timestamp,
                "audit_ref": stamp.audit_id,
                "evidence_refs": [f"queue:{item.item_id}"],
            }
            with vault_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            return {"ok": True, "unit_id": unit_id, "file": str(vault_file)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


_global_queue_repo: Optional[ExpertReviewQueueRepository] = None


def get_expert_queue_repo() -> ExpertReviewQueueRepository:
    """Singleton truy cập kho hàng đợi chuyên gia toàn cục."""
    global _global_queue_repo
    if _global_queue_repo is None:
        _global_queue_repo = ExpertReviewQueueRepository()
    return _global_queue_repo
