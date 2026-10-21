"""Sổ đăng ký vai trò chuyên gia theo miền (Expert Role Registry).

Tuân thủ thiết kế Mục 5.6 Báo cáo Tự học (DESKTOP-AIOS-SELF-LEARN-HERMES-ANALYSIS-HOME)
và nhiệm vụ vé DESKTOP-SELF-LEARN-EXPERT-QUEUE-ROUTING-PIN:
- Đọc cấu hình từ config/expert_roles.yaml theo các miền:
  1. LSU (Kiểm tra & Căn chỉnh LSU)
  2. Phân tích & Điều tra lỗi (dieutraloi)
  3. Quản lý sản xuất MOM/Opcenter
  4. Tri thức chung / Tổng hợp (general_fallback)
- Hỗ trợ chuyên gia chính (primary_expert) và chuyên gia dự phòng (backup_experts).
- Ghi nhật ký kiểm toán quản trị khi cập nhật sổ đăng ký (audit log).
- Ràng buộc máy tính được cấp phép (authorized_machines / machine binding).

Tương thích Python 3.11+.
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import yaml

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


DEFAULT_CONFIG_PATH = _repo_root() / "config" / "expert_roles.yaml"
DEFAULT_AUDIT_LOG_PATH = _repo_root() / "local_cases" / "expert_role_audit.jsonl"


def _utc_now_iso() -> str:
    """Trả về dấu thời gian UTC định dạng ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def normalize_subject(subject: str) -> str:
    """Chuẩn hóa chuỗi định danh người dùng: viết thường, loại bỏ khoảng trắng."""
    return str(subject or "").strip().lower()


def extract_username(subject: str) -> str:
    """Trích xuất tên người dùng không kèm tiền tố tên miền (domain)."""
    norm = normalize_subject(subject)
    if "\\" in norm:
        return norm.split("\\")[-1]
    if "/" in norm:
        return norm.split("/")[-1]
    return norm


def matches_subject(candidate: str, target: str) -> bool:
    """So khớp định danh người dùng Windows (hỗ trợ cả DOMAIN\\user và user).

    An toàn với môi trường kiểm thử và môi trường Active Directory công ty.
    """
    c_norm = normalize_subject(candidate)
    t_norm = normalize_subject(target)
    if not c_norm or not t_norm:
        return False
    if c_norm == t_norm:
        return True
    c_user = extract_username(candidate)
    t_user = extract_username(target)
    return c_user == t_user and len(c_user) > 0


@dataclass
class DomainRoleConfig:
    """Cấu hình vai trò chuyên gia cho một miền nghiệp vụ."""

    domain_id: str
    title: str
    primary_expert: str
    backup_experts: List[str] = field(default_factory=list)
    collections: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    authorized_machines: List[str] = field(default_factory=lambda: ["*"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "primary_expert": self.primary_expert,
            "backup_experts": list(self.backup_experts),
            "matching_rules": {
                "collections": list(self.collections),
                "keywords": list(self.keywords),
            },
            "authorized_machines": list(self.authorized_machines),
        }

    def is_expert(self, subject: str) -> bool:
        """Kiểm tra subject có phải là chuyên gia chính hoặc dự phòng không."""
        if matches_subject(subject, self.primary_expert):
            return True
        return any(matches_subject(subject, b) for b in self.backup_experts)

    def is_machine_authorized(self, machine_node: str) -> bool:
        """Kiểm tra tên máy (hostname/node) có trong danh sách được phép không."""
        norm_node = (machine_node or "").strip().lower()
        for allowed in self.authorized_machines:
            norm_allowed = allowed.strip().lower()
            if norm_allowed in ("*", "any", "all"):
                return True
            if norm_allowed == norm_node:
                return True
        return False


class ExpertRoleRegistry:
    """Quản lý Sổ đăng ký vai trò chuyên gia theo miền (Fail-closed)."""

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        audit_log_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.audit_log_path = Path(audit_log_path) if audit_log_path else DEFAULT_AUDIT_LOG_PATH
        self._domains: Dict[str, DomainRoleConfig] = {}
        self.reload()

    def reload(self) -> None:
        """Tải cấu hình từ tệp YAML. Nếu tệp chưa có hoặc lỗi, dùng fallback mặc định."""
        self._domains = {}
        if self.config_path.exists():
            try:
                raw_text = self.config_path.read_text(encoding="utf-8")
                data = yaml.safe_load(raw_text) or {}
                raw_domains = data.get("domains", {})
                for domain_id, dconf in raw_domains.items():
                    if not isinstance(dconf, dict):
                        continue
                    m_rules = dconf.get("matching_rules", {}) or {}
                    self._domains[domain_id] = DomainRoleConfig(
                        domain_id=domain_id,
                        title=str(dconf.get("title", domain_id)),
                        primary_expert=str(dconf.get("primary_expert", "")),
                        backup_experts=[str(x) for x in dconf.get("backup_experts", []) if x],
                        collections=[str(x) for x in m_rules.get("collections", []) if x],
                        keywords=[str(x) for x in m_rules.get("keywords", []) if x],
                        authorized_machines=[str(x) for x in dconf.get("authorized_machines", ["*"]) if x],
                    )
            except Exception as exc:
                # Ghi nhận lỗi nhưng không sập hệ thống (fail-closed fallback)
                self._load_fallback_defaults(f"Lỗi đọc {self.config_path}: {exc}")
                return

        if not self._domains:
            self._load_fallback_defaults("Cấu hình trống hoặc chưa có tệp.")

    def _load_fallback_defaults(self, reason: str = "") -> None:
        """Nạp cấu hình mặc định an toàn cho các miền cốt lõi."""
        self._domains = {
            "lsu": DomainRoleConfig(
                domain_id="lsu",
                title="Miền Kiểm tra & Căn chỉnh LSU",
                primary_expert="DOMAIN\\khiem_ni",
                backup_experts=["DOMAIN\\thao_nt"],
                collections=["lsu_master", "lsu_tuning", "6tha3_lsu", "iris_lsu", "sirius_lsu", "lsu"],
                keywords=["lsu", "laser", "motor", "polygon", "aperture", "beam", "lens", "f-theta"],
                authorized_machines=["*"],
            ),
            "dieu_tra_loi": DomainRoleConfig(
                domain_id="dieu_tra_loi",
                title="Miền Phân tích & Điều tra Lỗi Sản xuất",
                primary_expert="DOMAIN\\duc_na",
                backup_experts=["DOMAIN\\khiem_ni"],
                collections=["dieutraloi", "error_codes", "4m_investigation", "cases"],
                keywords=["nguyen nhan", "bien ban", "4m", "doi sach", "loi", "ng", "sc", "ec"],
                authorized_machines=["*"],
            ),
            "mom_opcenter": DomainRoleConfig(
                domain_id="mom_opcenter",
                title="Miền Hệ thống Quản lý Sản xuất MOM/Opcenter",
                primary_expert="DOMAIN\\tuan_pa",
                backup_experts=["DOMAIN\\admin_local"],
                collections=["mom_wms", "work_orders", "opcenter"],
                keywords=["wo", "lenh san xuat", "lo", "material", "opcenter", "erp", "wms"],
                authorized_machines=["*"],
            ),
            "general_fallback": DomainRoleConfig(
                domain_id="general_fallback",
                title="Miền Tri thức Chung / Tổng hợp",
                primary_expert="DOMAIN\\admin_local",
                backup_experts=[],
                collections=["*"],
                keywords=["*"],
                authorized_machines=["*"],
            ),
        }

    def list_domains(self) -> List[DomainRoleConfig]:
        """Danh sách tất cả các miền đã đăng ký."""
        return list(self._domains.values())

    def get_domain(self, domain_id: str) -> Optional[DomainRoleConfig]:
        """Lấy cấu hình của một miền cụ thể."""
        return self._domains.get(domain_id)

    def is_expert_for_domain(self, subject: str, domain_id: str) -> bool:
        """Kiểm tra subject có phải là chuyên gia của miền này không."""
        dconf = self.get_domain(domain_id)
        if not dconf:
            return False
        return dconf.is_expert(subject)

    def get_domains_for_expert(self, subject: str) -> List[str]:
        """Trả về danh sách domain_id mà subject này phụ trách (chính hoặc dự phòng)."""
        res: List[str] = []
        for domain_id, dconf in self._domains.items():
            if dconf.is_expert(subject):
                res.append(domain_id)
        return res

    def get_assigned_expert(self, domain_id: str, is_escalated: bool = False) -> str:
        """Trả về chuyên gia được phân công cho miền.

        Nếu is_escalated=True và có chuyên gia dự phòng, trả về chuyên gia dự phòng đầu tiên.
        Ngược lại trả về chuyên gia chính.
        """
        dconf = self.get_domain(domain_id)
        if not dconf:
            return "DOMAIN\\admin_local"
        if is_escalated and dconf.backup_experts:
            return dconf.backup_experts[0]
        return dconf.primary_expert

    def is_machine_authorized(self, domain_id: str, machine_node: Optional[str] = None) -> bool:
        """Kiểm tra máy tính hiện tại có được cấp phép duyệt cho miền này không."""
        dconf = self.get_domain(domain_id)
        if not dconf:
            return False
        node = machine_node or platform.node()
        return dconf.is_machine_authorized(node)

    def resolve_domain(
        self,
        collection_id: str = "",
        question: str = "",
        default_domain: str = "general_fallback",
    ) -> str:
        """Tự động định tuyến câu hỏi / sổ tay vào miền nghiệp vụ phù hợp.

        So khớp theo:
        1. Tên collection (thư viện tri thức đang mở)
        2. Từ khóa xuất hiện trong câu hỏi
        """
        norm_col = (collection_id or "").strip().lower()
        norm_q = (question or "").strip().lower()

        # 1. So khớp chính xác hoặc chứa collection_id
        if norm_col:
            for domain_id, dconf in self._domains.items():
                if domain_id == "general_fallback":
                    continue
                for col in dconf.collections:
                    col_low = col.lower()
                    if col_low != "*" and (col_low in norm_col or norm_col in col_low):
                        return domain_id

        # 2. So khớp từ khóa trong câu hỏi
        if norm_q:
            best_domain = ""
            max_matches = 0
            for domain_id, dconf in self._domains.items():
                if domain_id == "general_fallback":
                    continue
                matches = sum(1 for kw in dconf.keywords if kw.lower() in norm_q and kw != "*")
                if matches > max_matches:
                    max_matches = matches
                    best_domain = domain_id
            if max_matches > 0 and best_domain:
                return best_domain

        return default_domain

    def update_domain_roles(
        self,
        domain_id: str,
        *,
        primary_expert: Optional[str] = None,
        backup_experts: Optional[List[str]] = None,
        authorized_machines: Optional[List[str]] = None,
        actor: str = "admin",
        reason: str = "",
    ) -> DomainRoleConfig:
        """Cập nhật vai trò chuyên gia của miền và ghi nhật ký kiểm toán quản trị."""
        dconf = self._domains.get(domain_id)
        if not dconf:
            raise KeyError(f"Không tìm thấy miền nghiệp vụ: {domain_id}")

        old_snapshot = dconf.to_dict()

        if primary_expert is not None:
            dconf.primary_expert = str(primary_expert).strip()
        if backup_experts is not None:
            dconf.backup_experts = [str(x).strip() for x in backup_experts if str(x).strip()]
        if authorized_machines is not None:
            dconf.authorized_machines = [str(x).strip() for x in authorized_machines if str(x).strip()]

        new_snapshot = dconf.to_dict()

        # Lưu lại tệp YAML
        self.save_to_yaml(actor=actor, reason=reason, changed_domain=domain_id)

        # Ghi nhật ký kiểm toán quản trị
        self._record_admin_audit(
            action="update_domain_roles",
            actor=actor,
            domain_id=domain_id,
            old_data=old_snapshot,
            new_data=new_snapshot,
            reason=reason,
        )

        return dconf

    def save_to_yaml(
        self,
        path: Optional[Union[str, Path]] = None,
        actor: str = "admin",
        reason: str = "",
        changed_domain: str = "",
    ) -> None:
        """Lưu lại cấu hình vào YAML và tạo thư mục cha nếu chưa có."""
        target_path = Path(path) if path else self.config_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "domains": {
                domain_id: dconf.to_dict()
                for domain_id, dconf in self._domains.items()
            }
        }

        # Ghi atomic qua file tạm
        tmp_path = target_path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
        tmp_path.replace(target_path)

    def _record_admin_audit(
        self,
        action: str,
        actor: str,
        domain_id: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        reason: str = "",
    ) -> None:
        """Ghi vết kiểm toán quản trị vào tệp JSONL bất biến."""
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        audit_record = {
            "timestamp": _utc_now_iso(),
            "actor": actor,
            "action": action,
            "domain_id": domain_id,
            "machine": platform.node(),
            "old_data": old_data,
            "new_data": new_data,
            "reason": reason or "Quản trị viên cập nhật sổ đăng ký vai trò chuyên gia.",
        }
        with self.audit_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(audit_record, ensure_ascii=False) + "\n")


_global_registry: Optional[ExpertRoleRegistry] = None


def get_expert_role_registry() -> ExpertRoleRegistry:
    """Singleton helper truy cập sổ đăng ký vai trò chuyên gia toàn cục."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ExpertRoleRegistry()
    return _global_registry
