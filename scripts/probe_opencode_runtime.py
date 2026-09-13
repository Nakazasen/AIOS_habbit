"""Probe the pinned OpenCode runtime only against a copied synthetic fixture."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PINNED_VERSION = "1.14.33"
PINNED_BINARY_SHA256 = "C37DD78F32F9636D4D79D0B23FF43E37FCFB5A418602074587B7CB280F8774E4"


def _json_response(url: str, method: str = "GET", body: dict[str, Any] | None = None, timeout: int = 20) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        return error.code, {"error": raw[:500]}


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file() and item.name != "opencode.json":
            hasher.update(item.relative_to(path).as_posix().encode("utf-8"))
            hasher.update(item.read_bytes())
    return hasher.hexdigest()


def _runtime_binary() -> Path:
    launcher = shutil.which("opencode.cmd")
    if not launcher:
        raise RuntimeError("Không tìm thấy opencode.cmd trong PATH.")
    root = Path(launcher).parent / "node_modules" / "opencode-ai"
    binary = root / "node_modules" / "opencode-windows-x64-baseline" / "bin" / "opencode.exe"
    if not binary.is_file():
        raise RuntimeError("Không tìm thấy binary OpenCode baseline đã pin.")
    return binary


def _safe_environment(temp_root: Path) -> dict[str, str]:
    names = ("SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "PATH", "PATHEXT")
    environment = {name: os.environ[name] for name in names if name in os.environ}
    for name in ("USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA"):
        target = temp_root / name
        target.mkdir(exist_ok=True)
        environment[name] = str(target)
    return environment


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _record(status: str, detail: str = "") -> dict[str, str]:
    return {"status": status, "detail": detail}


def _tool_activity(message: Any, text: str) -> bool:
    return text.lower() in json.dumps(message, ensure_ascii=False).lower()


def run_probe(fixture: Path, bind: str, model: str) -> dict[str, Any]:
    if bind != "127.0.0.1":
        raise RuntimeError("Probe chỉ được bind 127.0.0.1.")
    if not fixture.is_dir():
        raise RuntimeError("Fixture không tồn tại.")

    binary = _runtime_binary()
    binary_hash = hashlib.sha256(binary.read_bytes()).hexdigest().upper()
    version = subprocess.run(["opencode.cmd", "--version"], check=False, capture_output=True, text=True, encoding="utf-8").stdout.strip()
    result: dict[str, Any] = {
        "status": "blocked",
        "runtime": {"version": version, "binary_sha256": binary_hash},
        "capabilities": {},
        "denials": {},
        "workspace": {},
    }
    if version != PINNED_VERSION or binary_hash != PINNED_BINARY_SHA256:
        result["reason_vi"] = "Bản OpenCode cục bộ không khớp bản đã khóa cho G1."
        return result

    with tempfile.TemporaryDirectory(prefix="aios-goal009-probe-") as temporary:
        temporary_root = Path(temporary)
        workspace = temporary_root / "fixture"
        shutil.copytree(fixture, workspace)
        unicode_data = json.loads((workspace / "factory_error" / "duong_dan_unicode.json").read_text(encoding="utf-8"))
        unicode_target = workspace / unicode_data["relative_path"]
        unicode_target.parent.mkdir(parents=True, exist_ok=True)
        unicode_target.write_text(unicode_data["content_vi"], encoding="utf-8")
        (workspace / "opencode.json").write_text(
            json.dumps({"permission": {"*": "deny", "read": "allow", "glob": "allow", "grep": "allow", "edit": "allow", "bash": {"*": "deny", "python test_yield_rate.py": "allow"}}}),
            encoding="utf-8",
        )
        baseline = _digest(workspace)
        result["workspace"]["baseline_digest"] = baseline
        port = _available_port()
        process = subprocess.Popen([str(binary), "serve", "--hostname", bind, "--port", str(port), "--pure"], cwd=workspace, env=_safe_environment(temporary_root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base_url = f"http://{bind}:{port}"
            for _ in range(100):
                health_status, health = _json_response(f"{base_url}/global/health")
                if health_status == 200:
                    break
                if process.poll() is not None:
                    raise RuntimeError("OpenCode dừng trước khi health endpoint sẵn sàng.")
                time.sleep(0.2)
            else:
                raise RuntimeError("OpenCode không sẵn sàng trước timeout.")
            result["capabilities"]["health"] = _record("passed" if health.get("version") == PINNED_VERSION else "failed")
            create_status, session = _json_response(f"{base_url}/session", "POST", {"title": "G1 synthetic fixture"})
            session_id = session.get("id") if isinstance(session, dict) else None
            result["capabilities"]["create_session"] = _record("passed" if create_status == 200 and session_id else "failed")
            get_status, _ = _json_response(f"{base_url}/session/{session_id}") if session_id else (0, {})
            result["capabilities"]["get_session"] = _record("passed" if get_status == 200 else "failed")
            find_status, found = _json_response(f"{base_url}/find?pattern={urllib.parse.quote('calculate_yield')}")
            result["capabilities"]["search_files"] = _record("passed" if find_status == 200 and found else "failed")
            read_status, read = _json_response(f"{base_url}/file/content?path={urllib.parse.quote('code_workspace/yield_rate.py')}")
            result["capabilities"]["read_file"] = _record("passed" if read_status == 200 and "calculate_yield" in read.get("content", "") else "failed")

            prompt = "Trong fixture hiện tại, chỉ làm bốn việc: đọc code_workspace/yield_rate.py và test_yield_rate.py; chạy đúng lệnh python test_yield_rate.py; sửa phép tính để test đạt; tạo code_workspace/agent_probe_note.txt chứa OK rồi chạy lại đúng lệnh. Không chạy lệnh khác, không đọc .env, không dùng git."
            message_status, message = _json_response(f"{base_url}/session/{session_id}/message", "POST", {"parts": [{"type": "text", "text": prompt}]}, timeout=180)
            changed = (workspace / "code_workspace" / "yield_rate.py").read_text(encoding="utf-8")
            note = workspace / "code_workspace" / "agent_probe_note.txt"
            note_created = note.exists() and note.read_text(encoding="utf-8", errors="replace").strip() == "OK"
            result["capabilities"]["edit_file"] = _record("passed" if "/" in changed and "//" not in changed else "failed")
            result["capabilities"]["create_file"] = _record("passed" if note_created else "failed")
            first_test = subprocess.run([sys.executable, "test_yield_rate.py"], cwd=workspace / "code_workspace", check=False, capture_output=True)
            result["capabilities"]["run_test_success"] = _record("passed" if first_test.returncode == 0 and _tool_activity(message, "test_yield_rate.py") else "failed")
            result["capabilities"]["run_test_failure"] = _record("passed" if _tool_activity(message, "AssertionError") or _tool_activity(message, "0 == 90") else "not_proved")
            result["capabilities"]["resume_session"] = _record("passed" if message_status == 200 and get_status == 200 else "failed")
            abort_status, _ = _json_response(f"{base_url}/session/{session_id}/abort", "POST") if session_id else (0, {})
            result["capabilities"]["abort_session"] = _record("passed" if abort_status == 200 else "failed")
            message_id = message.get("info", {}).get("id") if isinstance(message, dict) else None
            revert_status, _ = _json_response(f"{base_url}/session/{session_id}/revert", "POST", {"messageID": message_id}) if message_id else (0, {})
            result["workspace"]["after_undo_digest"] = _digest(workspace)
            result["workspace"]["created_file_removed"] = not note.exists()
            result["workspace"]["unicode_round_trip"] = unicode_target.read_text(encoding="utf-8") == unicode_data["content_vi"]
            result["capabilities"]["undo"] = _record("passed" if revert_status == 200 and result["workspace"]["after_undo_digest"] == baseline else "failed")
            result["capabilities"]["list_events"] = _record("not_proved", "OpenCode 1.14.33 không công bố receipt event đọc lại được trong OpenAPI cục bộ.")
            for name in ("path_traversal", "symlink_escape", "env_file", "command_not_allowed", "git_commit", "git_push"):
                result["denials"][name] = {"status": "not_proved", "before_digest": baseline, "after_digest": _digest(workspace)}
            required = [item.get("status") == "passed" for item in result["capabilities"].values()]
            result["status"] = "passed" if all(required) and all(item["status"] == "denied" for item in result["denials"].values()) else "blocked"
            result["reason_vi"] = "G1 chỉ đạt khi mọi thao tác và từ chối được quan sát thật; kết quả hiện tại giữ nguyên điều chưa chứng minh."
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        payload = run_probe(Path(args.fixture).resolve(), args.bind, args.model)
    except Exception as error:
        payload = {"status": "blocked", "reason_vi": "Probe dừng an toàn trước khi đủ bằng chứng.", "technical_reason": type(error).__name__}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
