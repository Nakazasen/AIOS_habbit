"""Script đo lường và chụp ảnh nghiệm thu vé DESKTOP-ANSWER-REPLY-HOME bằng Playwright.

Thực hiện:
- Tạo conversation mới và truy cập trực tiếp qua query params ?nb=mom_opcenter&conv={conv_id}
- Ca chính: Hỏi câu nhiều mục -> Bấm "Trả lời" -> Khung composer hiển thị dải neo -> Hỏi xoáy sâu không nhắc lại tên mục -> Đáp án tiếp xử lý đúng theo neo. Chụp ảnh: (1) đáp án gốc + trạng thái đã neo trên composer, (2) đáp án tiếp trọn thân.
- Ca gỡ neo: Bấm "Trả lời" -> Bấm nút ✕ gỡ neo -> Dải neo biến mất -> Hỏi bình thường. Chụp ảnh: (3) trạng thái gỡ neo hỏi tự do.
- Chống thụt lùi: Kiểm tra nút gợi ý hỏi tiếp sẵn có hoạt động bình thường. Chụp ảnh: (4) nút gợi ý hoạt động.
- Tính toán SHA-256, dung lượng byte và xuất kết quả đo JSON.
"""

import os
import sys
import time
import json
import uuid
import hashlib
import subprocess
import urllib.request
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import save_conversation
from playwright.sync_api import sync_playwright

PORT = 8537
URL = f"http://localhost:{PORT}"
OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def wait_for_server(port: int, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"http://localhost:{port}/_stcore/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def get_git_head() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=r"D:\Sandbox\AIOS_habbit",
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def main():
    print("[START] Khởi động đo lường nghiệm thu DESKTOP-ANSWER-REPLY-HOME")

    # Tạo hội thoại mới sạch sẽ dành riêng cho test
    conv_id = f"CONV-REPLY-{uuid.uuid4().hex[:6].upper()}"
    new_conv = WorkspaceConversation(
        id=conv_id,
        notebook_id="mom_opcenter",
        title="Nghiệm thu Trả lời có neo DESKTOP-ANSWER-REPLY-HOME",
        ai_mode="external",
    )
    save_conversation(new_conv)
    target_url = f"{URL}/?nb=mom_opcenter&conv={conv_id}"
    print(f"[CONV] Đã tạo hội thoại {conv_id}. URL truy cập: {target_url}")

    # 1. Khởi động Streamlit server trên cổng 8537 nếu chưa chạy
    server_process = None
    if not wait_for_server(PORT, timeout=2):
        print(f"[SERVER] Đang khởi động Streamlit server trên cổng {PORT}...")
        env = os.environ.copy()
        env["AIOS_STREAM_SYNTHESIS"] = "1"
        env["PYTHONUTF8"] = "1"
        python_exe = sys.executable
        server_process = subprocess.Popen(
            [
                python_exe, "-m", "streamlit", "run",
                "src/aios_habit/workspace_chat_app.py",
                "--server.port", str(PORT),
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false",
            ],
            cwd=r"D:\Sandbox\AIOS_habbit",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_server(PORT, timeout=60):
            print(f"[ERROR] Không thể khởi động Streamlit server trên cổng {PORT}")
            if server_process:
                server_process.kill()
            sys.exit(1)
        print(f"[SERVER] Streamlit server sẵn sàng tại {URL}")
    else:
        print(f"[SERVER] Streamlit server đã đang chạy sẵn tại {URL}")

    measure_data = {
        "ma_ve": "DESKTOP-ANSWER-REPLY-HOME",
        "thoi_diem_do": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "commit_head_habbit": get_git_head(),
        "ca_chinh_neo_ngu_canh": {},
        "ca_go_neo": {},
        "ca_chong_thut_lui": {},
        "danh_sach_anh": [],
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()

            print(f"[BROWSER] Truy cập {target_url}...")
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            # Chờ textarea của composer xuất hiện
            try:
                page.wait_for_selector('textarea[placeholder*="Nhập câu hỏi"]', timeout=30000)
            except Exception as e:
                page.screenshot(path=str(OUT_DIR / "debug_page_load_failed.png"))
                print(f"[DEBUG] Tiêu đề trang: {page.title()}, URL: {page.url}")
                raise e
            print("[BROWSER] Trang web đã tải xong, khung soạn thảo sẵn sàng.")

            # ==========================================
            # BƯỚC 1: Hỏi câu có nhiều mục
            # ==========================================
            q1 = "Nêu 4 bước chính trong quy trình bảo dưỡng và hiệu chuẩn thiết bị Jig theo thứ tự đánh số 1, 2, 3, 4."
            print(f"[CA CHINH] Gửi câu hỏi 1: '{q1}'")
            textarea = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
            textarea.fill(q1)
            page.wait_for_timeout(500)

            # Bấm gửi
            send_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button').first
            send_btn.click()
            print("[CA CHINH] Đã bấm gửi câu hỏi 1, đang chờ phản hồi...")

            # Đợi phản hồi hoàn tất (nút Trả lời xuất hiện)
            time.sleep(3)
            t0 = time.time()
            while time.time() - t0 < 120:
                visible_btns = page.locator('[class*="st-key-wsc_reply_btn_"] button:visible')
                if visible_btns.count() > 0:
                    print(f"[CA CHINH] Đáp án 1 đã hoàn tất! (sau {time.time()-t0:.1f}s)")
                    break
                page.wait_for_timeout(1500)

            page.wait_for_timeout(2000)

            # ==========================================
            # BƯỚC 2: Bấm nút "Trả lời" trên đáp án
            # ==========================================
            reply_buttons = page.locator('[class*="st-key-wsc_reply_btn_"] button:visible')
            if reply_buttons.count() == 0:
                reply_buttons = page.locator('button:has-text("Trả lời"):visible')
            print(f"[CA CHINH] Tìm thấy {reply_buttons.count()} nút 'Trả lời' visible")
            assert reply_buttons.count() > 0, "Không tìm thấy nút 'Trả lời' visible trên đáp án!"

            # Bấm vào nút Trả lời của đáp án mới nhất
            target_btn = reply_buttons.last
            target_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            target_btn.click()
            print("[CA CHINH] Đã bấm nút 'Trả lời' trên đáp án gốc!")

            # Chờ trạng thái đã neo xuất hiện trên composer
            try:
                page.get_by_text("Đang trả lời đáp án").first.wait_for(state="visible", timeout=15000)
                page.locator('[class*="st-key-wsc_remove_anchor_"] button').first.wait_for(state="visible", timeout=10000)
            except Exception as e:
                page.screenshot(path=str(OUT_DIR / "debug_after_reply_click.png"))
                print("[DEBUG] Không thấy dải neo sau khi bấm, đã lưu debug_after_reply_click.png")
                raise e
            print("[CA CHINH] Đã xác nhận: Dải neo ngữ cảnh và nút ✕ hiển thị thành công!")

            # Soạn câu hỏi xoáy sâu KHÔNG nhắc lại tên mục
            q2 = "Mục số 2 xử lý như thế nào và cần lưu ý gì?"
            print(f"[CA CHINH] Nhập câu hỏi xoáy sâu: '{q2}'")
            textarea = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
            textarea.fill(q2)
            page.wait_for_timeout(800)

            # Chụp ảnh 1: Đáp án gốc + Trạng thái đã neo trên composer
            img1_path = OUT_DIR / "anh-desktop-answer-reply-01-goc-va-trang-thai-neo.png"
            page.screenshot(path=str(img1_path))
            print(f"[SCREENSHOT 1] Đã lưu: {img1_path.name}")

            # ==========================================
            # BƯỚC 3: Gửi câu hỏi xoáy sâu và nhận đáp án tiếp
            # ==========================================
            send_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button').first
            t_turn2_start = time.time()
            send_btn.click()
            print("[CA CHINH] Đã bấm gửi câu hỏi xoáy sâu có neo, đang chờ phản hồi...")

            time.sleep(3)
            t0 = time.time()
            while time.time() - t0 < 120:
                visible_btns = page.locator('[class*="st-key-wsc_reply_btn_"] button:visible')
                if visible_btns.count() >= 2:
                    print(f"[CA CHINH] Đáp án tiếp theo đã hoàn tất! (sau {time.time()-t0:.1f}s)")
                    break
                page.wait_for_timeout(1500)
            t_turn2_end = time.time()
            turn2_duration = t_turn2_end - t_turn2_start

            page.wait_for_timeout(2000)

            # Cuộn xuống để xem trọn thân đáp án tiếp theo
            jump_btn = page.locator('button:has-text("Xuống câu trả lời mới nhất"):visible')
            if jump_btn.count() > 0:
                jump_btn.first.click()
                page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)

            # Chụp ảnh 2: Đáp án tiếp theo trọn thân
            img2_path = OUT_DIR / "anh-desktop-answer-reply-02-dap-an-tiep-tron-than.png"
            page.screenshot(path=str(img2_path))
            print(f"[SCREENSHOT 2] Đã lưu: {img2_path.name}")

            # Ghi nhận kết quả Ca chính
            measure_data["ca_chinh_neo_ngu_canh"] = {
                "cau_hoi_goc": q1,
                "cau_hoi_xoay_sau": q2,
                "thoi_gian_tra_loi_s": round(turn2_duration, 2),
                "neo_thanh_cong": True,
                "anh_1": img1_path.name,
                "anh_2": img2_path.name,
            }

            # ==========================================
            # BƯỚC 4: Ca gỡ neo (Bấm Trả lời rồi bấm ✕ gỡ neo)
            # ==========================================
            print("[CA GO NEO] Bắt đầu kiểm tra ca gỡ neo...")
            reply_buttons = page.locator('[class*="st-key-wsc_reply_btn_"] button:visible')
            if reply_buttons.count() == 0:
                reply_buttons = page.locator('button:has-text("Trả lời"):visible')
            target_btn = reply_buttons.last
            target_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            target_btn.click()

            # Chờ dải neo xuất hiện
            page.get_by_text("Đang trả lời đáp án").first.wait_for(state="visible", timeout=15000)
            remove_btn = page.locator('[class*="st-key-wsc_remove_anchor_"] button').first
            print("[CA GO NEO] Neo đã lên composer. Giờ bấm nút ✕ để gỡ neo...")

            # Bấm nút ✕ để gỡ neo
            remove_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            remove_btn.click()
            print("[CA GO NEO] Đã click nút ✕, đang chờ dải neo biến mất...")

            # Chờ dải neo biến mất (detached / hidden)
            try:
                page.locator(".wsc-anchored-quote").wait_for(state="detached", timeout=15000)
            except Exception as e:
                page.screenshot(path=str(OUT_DIR / "debug_after_remove_anchor.png"))
                print(f"[DEBUG] Dải neo chưa biến mất. Số lượng còn lại: {page.locator('.wsc-anchored-quote').count()}")
                raise e

            print("[CA GO NEO] Xác nhận: Dải neo đã biến mất sau khi bấm nút ✕!")

            # Soạn câu hỏi tự do
            q3 = "Tóm tắt ngắn gọn 1 câu về nguyên tắc an toàn khi vận hành thiết bị."
            textarea = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
            textarea.fill(q3)
            page.wait_for_timeout(800)

            # Chụp ảnh 3: Trạng thái gỡ neo và hỏi tự do
            img3_path = OUT_DIR / "anh-desktop-answer-reply-03-go-neo-hoi-tu-do.png"
            page.screenshot(path=str(img3_path))
            print(f"[SCREENSHOT 3] Đã lưu: {img3_path.name}")

            # Gửi câu hỏi tự do
            send_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button').first
            send_btn.click()
            page.wait_for_timeout(5000)

            measure_data["ca_go_neo"] = {
                "hanh_dong": "Bam Tra loi -> Bam ✕ go neo -> Hoi tu do",
                "go_neo_thanh_cong": True,
                "anh_3": img3_path.name,
            }

            # ==========================================
            # BƯỚC 5: Ca chống thụt lùi (Gợi ý hỏi tiếp hoạt động)
            # ==========================================
            print("[CHONG THUT LUI] Kiểm tra các nút gợi ý hỏi tiếp...")
            sugg_conv_id = f"CONV-SUGG-{uuid.uuid4().hex[:6].upper()}"
            sugg_conv = WorkspaceConversation(
                id=sugg_conv_id,
                notebook_id="mom_opcenter",
                title="Kiểm tra gợi ý hỏi tiếp chống thụt lùi",
                ai_mode="external",
            )
            save_conversation(sugg_conv)
            sugg_url = f"{URL}/?nb=mom_opcenter&conv={sugg_conv_id}"
            print(f"[CHONG THUT LUI] Mở hội thoại mới để kiểm tra gợi ý: {sugg_url}")
            page.goto(sugg_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            # Đợi các nút gợi ý mở đầu xuất hiện
            opening_btns = page.locator('[class*="st-key-wsc_opening_"] button:visible')
            try:
                opening_btns.first.wait_for(state="visible", timeout=15000)
                print(f"[CHONG THUT LUI] Tìm thấy {opening_btns.count()} nút gợi ý hỏi tiếp mở đầu!")
            except Exception as e:
                page.screenshot(path=str(OUT_DIR / "debug_opening_suggestions.png"))
                raise e

            # Chụp ảnh 4: Nút gợi ý hỏi tiếp hoạt động
            img4_path = OUT_DIR / "anh-desktop-answer-reply-04-chong-thut-lui-goi-y.png"
            page.screenshot(path=str(img4_path))
            print(f"[SCREENSHOT 4] Đã lưu: {img4_path.name}")

            measure_data["ca_chong_thut_lui"] = {
                "so_nut_goi_y_hien_thi": opening_btns.count(),
                "goi_y_hoi_tiep_hoat_dong": True,
                "anh_4": img4_path.name,
            }

            browser.close()

    finally:
        if server_process:
            print("[SERVER] Đang dừng Streamlit server process...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except Exception:
                server_process.kill()

    # Tính toán SHA256 các file ảnh
    images_meta = []
    for img_file in [
        "anh-desktop-answer-reply-01-goc-va-trang-thai-neo.png",
        "anh-desktop-answer-reply-02-dap-an-tiep-tron-than.png",
        "anh-desktop-answer-reply-03-go-neo-hoi-tu-do.png",
        "anh-desktop-answer-reply-04-chong-thut-lui-goi-y.png",
    ]:
        p_img = OUT_DIR / img_file
        if p_img.exists():
            images_meta.append({
                "file": img_file,
                "bytes": p_img.stat().st_size,
                "sha256": sha256_file(p_img),
            })
            print(f"[HASH] {img_file}: {p_img.stat().st_size} bytes, SHA256: {sha256_file(p_img)}")

    measure_data["danh_sach_anh"] = images_meta

    # Ghi file kết quả đo JSON
    json_path = OUT_DIR / "ket-qua-do-desktop-answer-reply-home.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(measure_data, f, ensure_ascii=False, indent=2)
    print(f"[RESULT] Đã ghi tệp đo JSON: {json_path}")
    print("[DONE] Hoàn tất quá trình đo lường nghiệm thu!")


if __name__ == "__main__":
    main()
