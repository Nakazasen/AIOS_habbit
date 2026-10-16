# -*- coding: utf-8 -*-
"""Script do luong chi tiet DOM, CPU, RAM cua tien trinh renderer tren giao dien that.
Dung de so sanh TRUOC va SAU khi sua loi ve DESKTOP-PC0575-UI-RENDER-FIX.
Target: so NB-E35A7BEE, hoi thoai CONV-9C730D76 tai PC0575.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import psutil
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
TARGET_NB = "NB-E35A7BEE"
TARGET_CONV = "CONV-9C730D76"
OUTPUT_DIR = Path("D:/Sandbox/aios-dieu-phoi/hop-thu/lan-desktop-pc0575/ket-qua")


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def measure_renderer_perf(phase: str = "before", duration_s: int = 60) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target_url = f"{URL}/?nb={TARGET_NB}&conv={TARGET_CONV}"
    log(f"=== BAT DAU DO LUONG GIAO DIEN [{phase.upper()}] ===")
    log(f"Target: {target_url}")

    pids_before = set(psutil.pids())

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        # Xac dinh PID cua Chrome Renderer
        pids_after = set(psutil.pids())
        new_pids = pids_after - pids_before
        renderer_proc = None
        for pid in new_pids:
            try:
                proc = psutil.Process(pid)
                cmd = " ".join(proc.cmdline())
                if "--type=renderer" in cmd:
                    renderer_proc = proc
                    break
            except Exception:
                pass

        if not renderer_proc:
            log("[CANH BAO] Khong tim thay renderer process rieng biet, chon process moi co RSS cao nhat")
            for pid in new_pids:
                try:
                    proc = psutil.Process(pid)
                    if not renderer_proc or proc.memory_info().rss > renderer_proc.memory_info().rss:
                        renderer_proc = proc
                except Exception:
                    pass

        log(f"Renderer Process ID: {renderer_proc.pid if renderer_proc else 'N/A'}")

        # Bat dau dieu huong
        t_start = time.time()
        log(f"Dang dieu huong den {target_url}...")
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
        except Exception as e:
            log(f"Goto warning: {e}")

        # Cho giao dien hien thi chat message hoac textarea
        ready = False
        t_ready = None
        composer_selector = 'textarea, [data-testid="stChatMessage"], [data-testid="stSidebar"]'
        try:
            page.wait_for_selector(composer_selector, timeout=120000)
            t_ready = time.time() - t_start
            ready = True
            log(f"Giao dien da san sang sau: {t_ready:.2f} giay")
        except Exception as e:
            log(f"Cho giao dien san sang timed out: {e}")
            t_ready = time.time() - t_start

        # Doi them 3 giay de on dinh cay DOM
        page.wait_for_timeout(3000)

        # Do so phan tu DOM
        try:
            dom_count = page.evaluate("document.querySelectorAll('*').length")
        except Exception:
            dom_count = -1

        try:
            sidebar_expanders = page.evaluate("document.querySelectorAll('[data-testid=\"stExpander\"]').length")
        except Exception:
            sidebar_expanders = -1

        try:
            chat_messages = page.evaluate("document.querySelectorAll('[data-testid=\"stChatMessage\"]').length")
        except Exception:
            chat_messages = -1

        try:
            total_buttons = page.evaluate("document.querySelectorAll('button').length")
        except Exception:
            total_buttons = -1

        log(f"So phan tu DOM tong cong: {dom_count}")
        log(f"So expanders: {sidebar_expanders}, so chat messages: {chat_messages}, so buttons: {total_buttons}")

        # Chup anh bang chung
        shot_path = OUTPUT_DIR / f"anh-pc0575-ui-render-{phase}.png"
        try:
            page.screenshot(path=str(shot_path), full_page=False)
            log(f"Da luu anh chup giao dien: {shot_path}")
        except Exception as e:
            log(f"Khong the chup anh: {e}")

        # Do CPU va RAM cua tien trinh renderer sau khi mo 60 giay
        log(f"Bat dau theo doi CPU va RAM renderer trong {duration_s} giay (sample moi 5s)...")
        samples = []
        cpu_times_start = renderer_proc.cpu_times() if renderer_proc else None
        t_monitor_start = time.time()

        for step in range(duration_s // 5):
            time.sleep(5)
            elapsed = time.time() - t_monitor_start
            if renderer_proc and renderer_proc.is_running():
                try:
                    mem_rss_mb = round(renderer_proc.memory_info().rss / (1024 * 1024), 2)
                    mem_vms_mb = round(renderer_proc.memory_info().vms / (1024 * 1024), 2)
                    cpu_percent = renderer_proc.cpu_percent(interval=None)
                    cpu_times_curr = renderer_proc.cpu_times()
                    total_cpu_time = round(cpu_times_curr.user + cpu_times_curr.system, 2)
                except Exception:
                    mem_rss_mb = -1
                    mem_vms_mb = -1
                    cpu_percent = -1
                    total_cpu_time = -1
            else:
                mem_rss_mb = -1
                mem_vms_mb = -1
                cpu_percent = -1
                total_cpu_time = -1

            sample = {
                "elapsed_s": round(elapsed, 1),
                "ram_rss_mb": mem_rss_mb,
                "ram_vms_mb": mem_vms_mb,
                "cpu_percent": cpu_percent,
                "total_cpu_time_s": total_cpu_time,
            }
            samples.append(sample)
            log(f"[{elapsed:.0f}s] RAM RSS: {mem_rss_mb} MB | CPU: {cpu_percent}% | Total CPU Time: {total_cpu_time}s")

        cpu_times_end = renderer_proc.cpu_times() if renderer_proc and renderer_proc.is_running() else None
        net_cpu_time_60s = 0.0
        if cpu_times_start and cpu_times_end:
            net_cpu_time_60s = round((cpu_times_end.user + cpu_times_end.system) - (cpu_times_start.user + cpu_times_start.system), 2)

        peak_ram_mb = max((s["ram_rss_mb"] for s in samples if s["ram_rss_mb"] > 0), default=0)
        final_ram_mb = samples[-1]["ram_rss_mb"] if samples else 0
        avg_cpu_percent = round(sum(s["cpu_percent"] for s in samples if s["cpu_percent"] >= 0) / max(1, len(samples)), 2)

        result = {
            "phase": phase,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "target_notebook": TARGET_NB,
            "target_conversation": TARGET_CONV,
            "renderer_pid": renderer_proc.pid if renderer_proc else None,
            "time_to_ready_s": round(t_ready, 2) if t_ready else None,
            "dom_elements_count": dom_count,
            "sidebar_expanders_count": sidebar_expanders,
            "chat_messages_count": chat_messages,
            "buttons_count": total_buttons,
            "renderer_peak_ram_rss_mb": peak_ram_mb,
            "renderer_final_ram_rss_mb": final_ram_mb,
            "renderer_avg_cpu_percent": avg_cpu_percent,
            "renderer_net_cpu_time_60s": net_cpu_time_60s,
            "samples": samples,
            "screenshot_path": str(shot_path),
        }

        browser.close()

    result_file = OUTPUT_DIR / f"ket-qua-do-ui-render-{phase}.json"
    result_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Da ghi ket qua do vao: {result_file}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["before", "after"], default="before")
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()

    res = measure_renderer_perf(phase=args.phase, duration_s=args.duration)
    print("\n--- KET QUA TONG HOP ---")
    print(json.dumps(res, indent=2))
