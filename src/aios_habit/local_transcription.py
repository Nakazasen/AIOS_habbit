"""Local transcription and expert audio consent protocol for AIOS Habit.

Implements T039 and T042 of Goal 010-expert-knowledge-acquisition.
Fail-closed invariants:
1. Recording or transcription before consent is strictly blocked.
2. Consent withdrawal immediately stops capture and prevents processing.
3. Raw audio and raw transcripts are strictly labeled 'local_only'.
4. Machine transcripts require human review for critical tokens (numbers, units, model IDs).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

WHISPER_CPP_BINARY_ENV = "AIOS_WHISPER_CPP_BINARY"
WHISPER_CPP_MODEL_ENV = "AIOS_WHISPER_CPP_MODEL"

# Consent States
CONSENT_STATE_GRANTED = "granted"
CONSENT_STATE_DECLINED = "declined"
CONSENT_STATE_WITHDRAWN = "withdrawn"
CONSENT_STATE_EXPIRED = "expired"

VALID_CONSENT_STATES = {
    CONSENT_STATE_GRANTED,
    CONSENT_STATE_DECLINED,
    CONSENT_STATE_WITHDRAWN,
    CONSENT_STATE_EXPIRED,
}

# Transcript Review States
TRANSCRIPT_STATE_DRAFT = "draft"
TRANSCRIPT_STATE_REVIEWED = "reviewed"
TRANSCRIPT_STATE_CONFIRMED = "confirmed"
TRANSCRIPT_STATE_REJECTED = "rejected"


class TranscriptionError(Exception):
    """Base exception for transcription and consent operations."""
    pass


class TranscriptionEngineUnavailableError(TranscriptionError):
    """Raised when the speech-to-text engine binary or model is missing or fails."""
    pass


class ConsentRequiredError(TranscriptionError):
    """Raised when audio capture or transcription is attempted without active consent."""
    pass


class ConsentWithdrawnError(TranscriptionError):
    """Raised when an operation is attempted after consent has been withdrawn."""
    pass


class AudioPathSecurityError(TranscriptionError):
    """Raised when an audio path attempts directory traversal or leaves local_only boundary."""
    pass


def save_local_audio_upload(
    storage_root: Path,
    session_id: str,
    original_name: str,
    payload: bytes,
) -> Path:
    """Atomically persist one WAV upload inside the local-only workspace boundary."""
    if Path(original_name).suffix.lower() != ".wav":
        raise AudioPathSecurityError("Chỉ chấp nhận tệp âm thanh WAV trong vùng lưu cục bộ.")
    if not payload:
        raise AudioPathSecurityError("Tệp âm thanh tải lên đang trống.")

    upload_dir = (Path(storage_root) / "local_only" / "audio_uploads").resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_session = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:48].strip("_-") or "session"
    safe_stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(original_name).stem)[:48].strip("_-") or "audio"
    digest = hashlib.sha256(payload).hexdigest()
    target = (upload_dir / f"{safe_session}_{safe_stem}_{digest[:12]}.wav").resolve()
    if target.parent != upload_dir:
        raise AudioPathSecurityError("Đường dẫn tệp âm thanh nằm ngoài vùng lưu cục bộ.")

    handle, temporary_name = tempfile.mkstemp(prefix=".audio_", suffix=".tmp", dir=upload_dir)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


@dataclass(frozen=True)
class ConsentRecord:
    """Immutable record of expert consent for audio recording and transcription."""

    consent_id: str
    session_id: str
    subject: str
    version: str = "1.0"
    state: str = CONSENT_STATE_GRANTED
    purposes: Tuple[str, ...] = ("audio_recording", "local_transcription")
    retention_policy: str = "local_only_retained"
    granted_at: Optional[str] = None
    withdrawn_at: Optional[str] = None
    policy_digest: str = ""

    def __post_init__(self) -> None:
        if self.state not in VALID_CONSENT_STATES:
            raise ValueError(f"Trạng thái đồng ý '{self.state}' không hợp lệ. Phải thuộc {VALID_CONSENT_STATES}.")
        if not self.session_id:
            raise ValueError("Mã phiên phỏng vấn (session_id) không được để trống.")
        if not self.subject:
            raise ValueError("Định danh chủ thể chuyên gia (subject) không được để trống.")

    @property
    def is_active(self) -> bool:
        return self.state == CONSENT_STATE_GRANTED

    def compute_digest(self) -> str:
        payload = f"{self.consent_id}:{self.session_id}:{self.subject}:{self.version}:{self.state}:{','.join(sorted(self.purposes))}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TranscriptionSegment:
    """Segment of transcribed speech with timing and extracted critical tokens."""

    segment_id: str
    start_time: float
    end_time: float
    text: str
    tokens: Tuple[str, ...] = ()
    critical_tokens: Tuple[str, ...] = ()
    is_confirmed: bool = False
    edited_text: Optional[str] = None

    def __post_init__(self) -> None:
        if self.end_time < self.start_time:
            raise ValueError("Thời điểm kết thúc không thể nhỏ hơn thời điểm bắt đầu.")


@dataclass(frozen=True)
class TranscriptionReceipt:
    """Cryptographically verifiable receipt of local transcription execution."""

    receipt_id: str
    session_id: str
    audio_path: str
    audio_digest: str
    engine_name: str
    engine_version: str
    segments: Tuple[TranscriptionSegment, ...]
    full_text: str
    all_critical_tokens: Tuple[str, ...]
    state: str = TRANSCRIPT_STATE_DRAFT
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def payload_digest(self) -> str:
        payload = f"{self.receipt_id}:{self.session_id}:{self.audio_digest}:{self.engine_name}:{self.full_text}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Pattern for identifying critical tokens: numbers, measurements, equipment codes
CRITICAL_TOKEN_PATTERN = re.compile(
    r"(?:(?:\d+(?:[\.,]\d+)?\s*(?:[°º]C| độ C|°F|%|bar|kPa|MPa|mm|cm|m|nm|µm|um|kg|g|mg|s|giây|phút|giờ|h|V|mA|A|W|kW|Hz|kHz|MHz|rpm|lux)?)|(?:[A-Z0-9]{2,}(?:-[A-Z0-9]+)+))",
    re.IGNORECASE,
)


def extract_critical_tokens(text: str) -> Tuple[str, ...]:
    """Deterministically extract technical parameters, units, and equipment IDs from text."""
    matches = CRITICAL_TOKEN_PATTERN.findall(text)
    seen = set()
    cleaned = []
    for m in matches:
        item = m.strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            cleaned.append(item)
    return tuple(cleaned)


def confirm_critical_tokens(receipt: TranscriptionReceipt) -> TranscriptionReceipt:
    """Mark machine codes, measurements, and units as human-confirmed."""
    confirmed_segments = tuple(replace(segment, is_confirmed=True) for segment in receipt.segments)
    return replace(receipt, segments=confirmed_segments, state=TRANSCRIPT_STATE_CONFIRMED)


def _first_existing_file(paths: Sequence[Path]) -> Optional[Path]:
    for path in paths:
        try:
            if path.is_file():
                return path.resolve()
        except OSError:
            continue
    return None


def resolve_whisper_cpp_runtime(
    *,
    binary_path: Optional[Path] = None,
    model_path: Optional[Path] = None,
) -> Tuple[Optional[Path], Optional[Path]]:
    """Resolve whisper.cpp binary and model from explicit paths, env, then local_tools."""
    binaries: List[Path] = []
    models: List[Path] = []
    if binary_path is not None:
        binaries.append(Path(binary_path))
    env_binary = os.environ.get(WHISPER_CPP_BINARY_ENV, "").strip()
    if env_binary:
        binaries.append(Path(env_binary))
    if model_path is not None:
        models.append(Path(model_path))
    env_model = os.environ.get(WHISPER_CPP_MODEL_ENV, "").strip()
    if env_model:
        models.append(Path(env_model))

    repo_root = Path(__file__).resolve().parents[2]
    tools_dir = repo_root / "local_tools" / "whisper.cpp"
    binaries.extend(
        [
            tools_dir / "whisper-cli.exe",
            tools_dir / "whisper.exe",
            tools_dir / "main.exe",
            tools_dir / "whisper-cli",
            tools_dir / "whisper",
            tools_dir / "main",
        ]
    )
    models.extend(
        [
            tools_dir / "models" / "ggml-base.bin",
            tools_dir / "ggml-base.bin",
            repo_root / "models" / "ggml-base.bin",
            repo_root / "local_runs" / "whisper.cpp" / "models" / "ggml-base.bin",
        ]
    )
    return _first_existing_file(binaries), _first_existing_file(models)


class LocalTranscriptionProtocol(Protocol):
    """Interface contract for local speech-to-text engines."""

    def transcribe(
        self,
        audio_path: Path,
        session_id: str,
        consent: ConsentRecord,
        timeout_seconds: float = 60.0,
    ) -> TranscriptionReceipt:
        """Transcribe audio file locally with consent verification."""
        ...


class MockLocalTranscriptionEngine:
    """Deterministic local transcription engine reading simulated transcripts or synthesizing from audio metadata.
    
    Used for safe testing and offline verification without external binary dependencies.
    """

    def __init__(self, fixture_manifest_path: Optional[Path] = None) -> None:
        self.fixture_manifest_path = fixture_manifest_path
        self._manifest_cache: Optional[dict] = None
        if fixture_manifest_path and fixture_manifest_path.exists():
            try:
                self._manifest_cache = json.loads(fixture_manifest_path.read_text(encoding="utf-8"))
            except Exception:
                self._manifest_cache = None

    def transcribe(
        self,
        audio_path: Path,
        session_id: str,
        consent: ConsentRecord,
        timeout_seconds: float = 60.0,
        local_only_root: Optional[Path] = None,
    ) -> TranscriptionReceipt:
        # 1. Enforce fail-closed consent check
        if not consent.is_active:
            if consent.state == CONSENT_STATE_WITHDRAWN:
                raise ConsentWithdrawnError("Sự đồng ý của chuyên gia đã bị rút lại. Quá trình chép lời bị từ chối.")
            raise ConsentRequiredError("Không thể chép lời âm thanh khi chưa có sự đồng ý của chuyên gia.")

        # 2. Enforce local_only path security check if root specified
        if local_only_root:
            validate_local_only_audio_path(audio_path, local_only_root)

        # 3. Check file existence
        if not audio_path.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp âm thanh tại '{audio_path}'.")

        # 3. Compute audio digest
        raw_bytes = audio_path.read_bytes()
        audio_digest = hashlib.sha256(raw_bytes).hexdigest()

        # 4. Generate segments from manifest if matched, or fallback to deterministic synthesis
        segments_list = []
        if self._manifest_cache and "simulated_transcript" in self._manifest_cache:
            for idx, item in enumerate(self._manifest_cache["simulated_transcript"]):
                text = item.get("text", "")
                tokens = tuple(item.get("tokens", text.split()))
                critical = tuple(item.get("critical_tokens", extract_critical_tokens(text)))
                segments_list.append(
                    TranscriptionSegment(
                        segment_id=f"SEG-{session_id}-{idx + 1}",
                        start_time=float(item.get("start_time", idx * 1.0)),
                        end_time=float(item.get("end_time", (idx + 1) * 1.0)),
                        text=text,
                        tokens=tokens,
                        critical_tokens=critical,
                    )
                )
        else:
            # Fallback deterministic segment
            default_text = "Nhiệt độ tối đa năm mươi lăm độ C tại buồng sấy LSU-200"
            critical = extract_critical_tokens(default_text)
            segments_list.append(
                TranscriptionSegment(
                    segment_id=f"SEG-{session_id}-1",
                    start_time=0.0,
                    end_time=2.5,
                    text=default_text,
                    tokens=tuple(default_text.split()),
                    critical_tokens=critical,
                )
            )

        full_text = " ".join(s.text for s in segments_list)
        all_critical: List[str] = []
        for s in segments_list:
            for c in s.critical_tokens:
                if c not in all_critical:
                    all_critical.append(c)

        now_iso = datetime.now(timezone.utc).isoformat()
        receipt_id = f"TRCP-{session_id}-{int(datetime.now(timezone.utc).timestamp())}"

        return TranscriptionReceipt(
            receipt_id=receipt_id,
            session_id=session_id,
            audio_path=str(audio_path),
            audio_digest=audio_digest,
            engine_name="mock_local_transcription",
            engine_version="1.0.0-pinned",
            segments=tuple(segments_list),
            full_text=full_text,
            all_critical_tokens=tuple(all_critical),
            state=TRANSCRIPT_STATE_DRAFT,
            created_at=now_iso,
        )


def validate_local_only_audio_path(audio_path: Path, local_only_root: Path) -> Path:
    """Ensure that the audio file strictly resides within the configured local_only directory."""
    resolved_root = local_only_root.resolve()
    resolved_path = audio_path.resolve()

    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        raise AudioPathSecurityError(
            f"Tệp âm thanh '{audio_path}' nằm ngoài ranh giới vùng dữ liệu cục bộ an toàn '{local_only_root}'."
        )
    return resolved_path


class LocalWhisperCppTranscriptionAdapter:
    """Production local transcription adapter wrapping whisper.cpp v1.7.4.

    Implements T042 of Goal 010.
    Invariants:
    - Pinned version: v1.7.4
    - Subprocess execution timeout: 60.0s (fail-closed)
    - 100% offline, zero network telemetry
    - Verifies consent and local_only boundary before invocation
    """

    PINNED_VERSION = "v1.7.4"
    DEFAULT_TIMEOUT_SECONDS = 60.0

    def __init__(
        self,
        binary_path: Optional[Path] = None,
        model_path: Optional[Path] = None,
    ) -> None:
        self.binary_path = binary_path
        self.model_path = model_path

    def transcribe(
        self,
        audio_path: Path,
        session_id: str,
        consent: ConsentRecord,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        local_only_root: Optional[Path] = None,
    ) -> TranscriptionReceipt:
        # 1. Enforce consent check
        if not consent.is_active:
            if consent.state == CONSENT_STATE_WITHDRAWN:
                raise ConsentWithdrawnError("Sự đồng ý của chuyên gia đã bị rút lại. Quá trình chép lời bị từ chối.")
            raise ConsentRequiredError("Không thể chép lời âm thanh khi chưa có sự đồng ý của chuyên gia.")

        # 2. Enforce local_only path security check if root specified
        if local_only_root:
            validate_local_only_audio_path(audio_path, local_only_root)

        # 3. Check audio file exists
        if not audio_path.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp âm thanh tại '{audio_path}'.")

        binary_path = Path(self.binary_path) if self.binary_path else None
        model_path = Path(self.model_path) if self.model_path else None
        if binary_path is None or not binary_path.exists() or model_path is None or not model_path.exists():
            raise TranscriptionEngineUnavailableError(
                "Chưa chép được lời từ tệp ghi âm vì bộ máy trên máy này chưa sẵn sàng. "
                "Tệp ghi âm vẫn được giữ an toàn. Hãy dùng ô văn bản để nhập câu trả lời."
            )

        try:
            with tempfile.TemporaryDirectory(prefix="whisper_cpp_") as tmpdir:
                output_prefix = Path(tmpdir) / "transcript"
                cmd = [
                    str(binary_path),
                    "-m", str(model_path),
                    "-f", str(audio_path),
                    "-l", "vi",
                    "--output-json",
                    "--output-file", str(output_prefix),
                ]
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=True,
                )
                json_path = output_prefix.with_suffix(".json")
                if not json_path.is_file():
                    raise TranscriptionEngineUnavailableError(
                        "Chưa chép được lời từ tệp ghi âm. Tệp ghi âm vẫn được giữ trên máy này. "
                        "Hãy dùng ô văn bản để nhập câu trả lời."
                    )
                output_json = json.loads(json_path.read_text(encoding="utf-8"))
                segments_list = []
                for idx, item in enumerate(output_json.get("transcription", [])):
                    text = str(item.get("text", "")).strip()
                    # whisper.cpp v1.7.4: timestamps.from/to are clock strings;
                    # offsets.from/to are integer milliseconds. Segment times are seconds.
                    offsets = item.get("offsets") or {}
                    start_time = float(offsets["from"]) / 1000.0
                    end_time = float(offsets["to"]) / 1000.0
                    critical = extract_critical_tokens(text)
                    segments_list.append(
                        TranscriptionSegment(
                            segment_id=f"SEG-{session_id}-{idx + 1}",
                            start_time=start_time,
                            end_time=end_time,
                            text=text,
                            tokens=tuple(text.split()),
                            critical_tokens=critical,
                        )
                    )
                full_text = " ".join(s.text for s in segments_list)
                raw_bytes = audio_path.read_bytes()
                audio_digest = hashlib.sha256(raw_bytes).hexdigest()
                now_iso = datetime.now(timezone.utc).isoformat()
                return TranscriptionReceipt(
                    receipt_id=f"TRCP-{session_id}-{int(datetime.now(timezone.utc).timestamp())}",
                    session_id=session_id,
                    audio_path=str(audio_path),
                    audio_digest=audio_digest,
                    engine_name="whisper.cpp",
                    engine_version=self.PINNED_VERSION,
                    segments=tuple(segments_list),
                    full_text=full_text,
                    all_critical_tokens=tuple(dict.fromkeys(c for s in segments_list for c in s.critical_tokens)),
                    state=TRANSCRIPT_STATE_DRAFT,
                    created_at=now_iso,
                )
        except subprocess.TimeoutExpired:
            raise TranscriptionError(
                "Chưa chép được lời từ tệp ghi âm vì mất quá nhiều thời gian. "
                "Tệp ghi âm vẫn được giữ trên máy này. Hãy dùng ô văn bản để nhập câu trả lời."
            )
        except TranscriptionError:
            raise
        except TranscriptionEngineUnavailableError:
            raise
        except Exception:
            raise TranscriptionEngineUnavailableError(
                "Chưa chép được lời từ tệp ghi âm. Tệp ghi âm vẫn được giữ trên máy này. "
                "Hãy dùng ô văn bản để nhập câu trả lời."
            )


def create_manual_transcription_receipt(
    text: str,
    session_id: str,
    consent: ConsentRecord,
) -> TranscriptionReceipt:
    """Create a verified transcription receipt from manual user input when local engine is unavailable."""
    if not consent.is_active:
        if consent.state == CONSENT_STATE_WITHDRAWN:
            raise ConsentWithdrawnError("Sự đồng ý của chuyên gia đã bị rút lại. Thao tác bị từ chối.")
        raise ConsentRequiredError("Không thể tiếp nhận văn bản khi chưa có sự đồng ý của chuyên gia.")

    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("Nội dung văn bản nhập thủ công không được để trống.")

    critical = extract_critical_tokens(cleaned_text)
    segment = TranscriptionSegment(
        segment_id=f"SEG-MANUAL-{session_id}-1",
        start_time=0.0,
        end_time=0.0,
        text=cleaned_text,
        tokens=tuple(cleaned_text.split()),
        critical_tokens=critical,
        is_confirmed=True,
    )
    payload_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()
    receipt_id = f"TRCP-MANUAL-{session_id}-{int(datetime.now(timezone.utc).timestamp())}"

    return TranscriptionReceipt(
        receipt_id=receipt_id,
        session_id=session_id,
        audio_path="manual_input",
        audio_digest=payload_hash,
        engine_name="manual_input",
        engine_version="1.0.0",
        segments=(segment,),
        full_text=cleaned_text,
        all_critical_tokens=critical,
        state=TRANSCRIPT_STATE_REVIEWED,
        created_at=now_iso,
    )

