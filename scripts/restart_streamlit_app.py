# -*- coding: utf-8 -*-
"""Restart Streamlit Workspace Chat App safely with exact environment variables.
"""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
PYTHON_EXE = APP_DIR / ".venv" / "Scripts" / "python.exe"
LOG_FILE = APP_DIR / "local_cases" / "workspace_chat_app.log"
PORT = 8501


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def stop_streamlit() -> None:
    log("Dung cac tien trinh streamlit workspace_chat_app.py cu...")
    my_pid = os.getpid()
    ps_cmd = (
        f"$procs = Get-CimInstance Win32_Process | Where-Object {{ "
        f"($_.CommandLine -like '*workspace_chat_app.py*') -and $_.ProcessId -ne {my_pid} "
        f"}}; "
        f"foreach ($p in $procs) {{ Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }}"
    )
    subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
    time.sleep(2.0)


def start_streamlit() -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src") + ";" + env.get("PYTHONPATH", "")
    env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    env["AIOS_BGE_QUERY_TIMEOUT"] = "1200"
    env["AIOS_BGE_INIT_TIMEOUT"] = "420"
    env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
    env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
    env["AIOS_ERROR_CASES_DB"] = os.environ.get(
        "AIOS_ERROR_CASES_DB", r"C:\tmp\kdtps_standard\error_cases_reconciled.db"
    )
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    env["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
    env["STREAMLIT_SERVER_PORT"] = str(PORT)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_handle = open(LOG_FILE, "a", encoding="utf-8")

    cmd = [
        str(PYTHON_EXE),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        f"--server.port={PORT}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    log(f"Khoi dong Streamlit: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    return proc


def wait_ready(timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"http://localhost:{PORT}/_stcore/health")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


if __name__ == "__main__":
    stop_streamlit()
    p = start_streamlit()
    log(f"Da gui lenh start, Popen PID: {p.pid}")
    if wait_ready(60):
        log(f"Streamlit server da SAN SANG tren cong {PORT}!")
    else:
        log("[LOI] Streamlit server khong phan hoi sau 60s!")
        sys.exit(1)
