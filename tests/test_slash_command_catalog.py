# -*- coding: utf-8 -*-
"""Unit tests for Slash Command Catalog (DESKTOP-HOME-SLASH-COMMAND-PALETTE).

Verifies:
1. Đủ lệnh, không trùng: Mọi lệnh slash hệ thống đang sống đều có mặt, không trùng lặp lệnh hoặc alias.
2. Mỗi lệnh có câu tự nhiên tương đương được chat_intent_router nhận diện đúng 100%.
3. Mỗi lệnh có mô tả ngắn, nhóm tính năng và ngữ cảnh cần thiết (ở cả 3 ngôn ngữ VI/JA/ZH).
4. Sinh cẩm nang markdown khớp 100% catalog trên cả 3 ngôn ngữ và khớp tệp thực tế.
5. Ghi nhận sự kiện mở bảng gợi ý và chọn lệnh vào local_cases (vòng lặp cải thiện liên tục).
6. Hợp đồng DOM bảng gợi ý trong workspace_chat_app.py: bộ lọc, chèn lệnh, điều hướng phím ↑/↓/Enter/Esc.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from aios_habit.chat_intent_router import classify_intent, route
from aios_habit.slash_command_catalog import (
    generate_manual_commands_markdown,
    get_all_alive_slash_commands,
    get_command_catalog,
    get_palette_metrics,
    record_palette_event,
)


def test_catalog_completeness_and_no_duplicates() -> None:
    """Kiểm tra catalog đầy đủ lệnh, không trùng lặp tên lệnh chính và biến thể."""
    cat = get_command_catalog()
    assert len(cat) >= 8, f"Catalog phải có ít nhất 8 nhóm lệnh chính, thực tế: {len(cat)}"

    seen_all: set[str] = set()
    primary_cmds: list[str] = []

    for item in cat:
        cmd = item["command"]
        assert cmd.startswith("/"), f"Lệnh chính phải bắt đầu bằng '/': {cmd}"
        assert cmd not in seen_all, f"Trùng lặp lệnh: {cmd}"
        seen_all.add(cmd)
        primary_cmds.append(cmd)

        for alias in item.get("aliases", []):
            assert alias.startswith("/"), f"Biến thể phải bắt đầu bằng '/': {alias}"
            assert alias not in seen_all, f"Trùng lặp biến thể: {alias}"
            seen_all.add(alias)

    # Đảm bảo các lệnh cốt lõi của hệ thống đều có mặt
    expected_core = [
        "/huongdan",
        "/baocaodinhky",
        "/phanloai",
        "/dieutra-phanhoi",
        "/danhgiadieutra",
        "/danhgianhan",
        "/dongvu",
        "/phanhoi",
    ]
    for core in expected_core:
        assert core in primary_cmds, f"Thiếu lệnh cốt lõi trong danh mục: {core}"


def test_catalog_contains_no_english_commands() -> None:
    """Catalog và danh sách lệnh slash không được chứa bất kỳ lệnh tiếng Anh nào (DESKTOP-HOME-SLASH-ENGLISH-RETIRE-FIX)."""
    retired_english_commands = [
        "/guide",
        "/help",
        "/autoclassify",
        "/autoclassify-feedback",
        "/autoclassify-review",
        "/investigation",
        "/investigation-feedback",
        "/investigation-review",
        "/close-case",
        "/closecase",
        "/feedback",
    ]
    alive_commands = get_all_alive_slash_commands()
    for eng in retired_english_commands:
        assert eng not in alive_commands, f"Lệnh tiếng Anh '{eng}' vẫn còn tồn tại trong alive_commands!"

    cat = get_command_catalog()
    for item in cat:
        cmd = item["command"]
        assert cmd not in retired_english_commands, f"Lệnh chính '{cmd}' là tiếng Anh!"
        for alias in item.get("aliases", []):
            assert alias not in retired_english_commands, f"Biến thể '{alias}' là tiếng Anh!"


def test_retired_english_commands_do_not_trigger_command_intent() -> None:
    """Các lệnh tiếng Anh bị rút khi gõ vào ô chat phải ứng xử như văn bản thường (HOI_TAI_LIEU), không kích hoạt lệnh."""
    from aios_habit.chat_intent_router import HOI_TAI_LIEU

    retired_english_commands = [
        "/guide",
        "/help",
        "/autoclassify",
        "/autoclassify-feedback",
        "/autoclassify-review",
        "/investigation",
        "/investigation-feedback",
        "/investigation-review",
        "/close-case",
        "/closecase",
        "/feedback",
    ]
    for eng_cmd in retired_english_commands:
        intent = classify_intent(eng_cmd)
        assert intent == HOI_TAI_LIEU, (
            f"Lệnh tiếng Anh '{eng_cmd}' đã bị rút nhưng vẫn kích hoạt intent '{intent}'!"
        )


def test_every_catalog_command_has_natural_query_recognized_by_router() -> None:
    """Mỗi lệnh trong catalog phải có câu tự nhiên tương đương và router nhận diện đúng intent."""
    cat = get_command_catalog()

    for item in cat:
        cmd = item["command"]
        nat = item["natural_query"]
        expected_intent = item["intent"]

        assert nat, f"Lệnh {cmd} thiếu câu tự nhiên tương đương (natural_query)"

        # 1. Câu tự nhiên tương đương phải đi đúng intent
        intent_nat = classify_intent(nat)
        assert intent_nat == expected_intent, (
            f"Câu tự nhiên '{nat}' của lệnh {cmd} bị nhận diện sai: "
            f"kỳ vọng {expected_intent}, thực tế {intent_nat}"
        )

        # 2. Lệnh chính phải đi đúng intent
        intent_cmd = classify_intent(cmd)
        assert intent_cmd == expected_intent, (
            f"Lệnh chính '{cmd}' bị nhận diện sai intent: "
            f"kỳ vọng {expected_intent}, thực tế {intent_cmd}"
        )

        # 3. Tất cả các biến thể phải đi đúng intent
        for alias in item.get("aliases", []):
            intent_alias = classify_intent(alias)
            assert intent_alias == expected_intent, (
                f"Biến thể '{alias}' của {cmd} bị nhận diện sai: "
                f"kỳ vọng {expected_intent}, thực tế {intent_alias}"
            )


def test_catalog_entries_have_full_metadata_and_i18n() -> None:
    """Mỗi lệnh phải có đầy đủ mô tả, nhóm tính năng và ngữ cảnh ở cả 3 ngôn ngữ VI/JA/ZH."""
    cat = get_command_catalog()

    for item in cat:
        cmd = item["command"]
        # Tiếng Việt
        assert item.get("description"), f"Lệnh {cmd} thiếu description tiếng Việt"
        assert item.get("category"), f"Lệnh {cmd} thiếu category tiếng Việt"
        assert item.get("context_required"), f"Lệnh {cmd} thiếu context_required tiếng Việt"

        # Tiếng Nhật
        assert item.get("description_ja"), f"Lệnh {cmd} thiếu description_ja"
        assert item.get("category_ja"), f"Lệnh {cmd} thiếu category_ja"
        assert item.get("context_required_ja"), f"Lệnh {cmd} thiếu context_required_ja"

        # Tiếng Trung
        assert item.get("description_zh"), f"Lệnh {cmd} thiếu description_zh"
        assert item.get("category_zh"), f"Lệnh {cmd} thiếu category_zh"
        assert item.get("context_required_zh"), f"Lệnh {cmd} thiếu context_required_zh"


def test_generate_manual_commands_markdown() -> None:
    """Hàm sinh markdown cẩm nang phải chứa đầy đủ mọi lệnh trong catalog ở cả 3 ngôn ngữ."""
    cat = get_command_catalog()

    for lang in ("vi", "ja", "zh"):
        md = generate_manual_commands_markdown(lang)
        assert "## 9." in md, f"Markdown {lang} thiếu tiêu đề mục 9"
        assert "| :--- |" in md, f"Markdown {lang} thiếu cấu trúc bảng"

        for item in cat:
            assert item["command"] in md, f"Markdown {lang} thiếu lệnh {item['command']}"


def test_manual_markdown_files_match_catalog() -> None:
    """Cả 3 tệp cẩm nang trong docs/huong-dan-su-dung phải chứa đầy đủ toàn bộ lệnh trong catalog."""
    repo_root = Path(__file__).resolve().parent.parent
    docs_dir = repo_root / "docs" / "huong-dan-su-dung"

    cat = get_command_catalog()
    files = [
        ("vi", docs_dir / "HUONG-DAN-SU-DUNG-AIOS.md", "9. DANH MỤC LỆNH HỆ THỐNG"),
        ("ja", docs_dir / "HUONG-DAN-SU-DUNG-AIOS-JA.md", "9. システムコマンド一覧"),
        ("zh", docs_dir / "HUONG-DAN-SU-DUNG-AIOS-ZH.md", "9. 系统命令目录"),
    ]

    for lang, path, heading in files:
        assert path.is_file(), f"Không tìm thấy tệp cẩm nang: {path}"
        content = path.read_text(encoding="utf-8")
        assert heading in content, f"Tệp {path.name} thiếu tiêu đề {heading}"

        for item in cat:
            assert item["command"] in content, (
                f"Tệp {path.name} thiếu lệnh chính {item['command']} từ catalog"
            )


def test_palette_event_recording_and_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra ghi nhận sự kiện mở bảng và chọn lệnh vào local_cases."""
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))

    # 1. Ghi sự kiện mở bảng
    record_palette_event(action="open", query="/", conversation_id="CONV-TEST-PALETTE")

    # 2. Ghi sự kiện chọn lệnh
    record_palette_event(
        action="select",
        command="/huongdan",
        query="/huo",
        conversation_id="CONV-TEST-PALETTE",
    )

    events_file = tmp_path / "palette_events.jsonl"
    metrics_file = tmp_path / "palette_metrics.json"

    assert events_file.is_file(), "Chưa tạo tệp palette_events.jsonl"
    lines = events_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2, f"Kỳ vọng 2 sự kiện, thực tế: {len(lines)}"

    metrics = get_palette_metrics()
    assert metrics.get("total_palette_opens") == 1
    assert metrics.get("total_command_selects") == 1
    assert metrics.get("by_command", {}).get("/huongdan") == 1


def test_slash_palette_dom_contract_in_workspace_chat_app() -> None:
    """Hợp đồng mã nguồn giao diện: bảng gợi ý được tích hợp đúng quy chuẩn không phá vỡ logic cũ."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    # 1. Có phần tử bảng gợi ý và ID chuẩn
    assert "wsc-slash-palette" in app_source
    assert "__wscFilterCatalog" in app_source
    assert "__wscRenderPalette" in app_source
    assert "__wscSelectCommand" in app_source
    assert "__wscShowPalette" in app_source
    assert "__wscHidePalette" in app_source

    # 2. Kích hoạt khi gõ "/"
    assert 'val.startsWith("/")' in app_source

    # 3. Điều hướng bàn phím đầy đủ
    assert 'event.key === "ArrowDown"' in app_source
    assert 'event.key === "ArrowUp"' in app_source
    assert 'event.key === "Escape"' in app_source

    # 4. Chèn lệnh bằng Enter KHÔNG tự động gửi
    assert 'nativeSetter.call(textarea, insertText)' in app_source
    assert 'parentWin.__wscHidePalette()' in app_source

    # 5. Ghi log khi gửi lệnh slash
    assert 'record_palette_event' in app_source

    # 6. Chống cắt khung (overflow: auto của stElementContainer): bắt buộc mở overflow: visible
    assert "__wscEnsurePaletteAttached" in app_source
    assert 'composerBlock.style.overflow = "visible"' in app_source
    assert "overflow: visible !important;" in app_source


def test_slash_palette_trigger_execution_and_anti_clipping(tmp_path: Path) -> None:
    """Chứng minh đường kích hoạt palette khi gõ '/' chạy thực tế (render DOM + chống cắt overflow)."""
    import json
    import subprocess

    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    start = app_source.find("_wsc_components.html(")
    end = app_source.find("height=0,", start)
    block = app_source[start:end]

    _js_is_answering = "false"
    _js_has_error = "false"
    class _DummyConv:
        id = "CONV-UNIT-PALETTE"
    active_conversation = _DummyConv()
    current_ui_locale = "vi"
    _js_slash_catalog = json.dumps(get_command_catalog(), ensure_ascii=False)
    _js_ack_text = "ack"
    _js_wait_spinner = "spin"
    _js_wait_title = "title"
    _js_step_find = "find"
    _js_step_read = "read"
    _js_step_synth = "synth"

    q3 = '"""'
    s_idx = block.find("f" + q3)
    e_idx = block.rfind(q3) + 3
    rendered_html = eval(block[s_idx:e_idx])
    js_code = rendered_html.replace("<script>", "").replace("</script>", "")

    node_harness = """
const listeners = {};
const styleSheets = [];
const composerBlock = {
  style: { position: "static", overflow: "auto" },
  children: [],
  appendChild(el) {
    el.parentElement = this;
    if (!this.children.includes(el)) this.children.push(el);
  }
};
const textarea = {
  value: "",
  style: {},
  attributes: {},
  removeAttribute(k) { delete this.attributes[k]; },
  setAttribute(k, v) { this.attributes[k] = v; },
  focus() { this.focused = true; },
  setSelectionRange(a, b) { this.sel = [a, b]; },
  dispatchEvent(evt) { this.lastEvt = evt.type; },
  matches(sel) { return sel.includes("wsc_question_input_"); }
};
const elementsById = {};
const parentDoc = {
  head: {
    appendChild(el) {
      if (el.id) elementsById[el.id] = el;
      styleSheets.push(el);
    }
  },
  getElementById(id) { return elementsById[id] || null; },
  createElement(tag) {
    return {
      tagName: tag.toUpperCase(),
      id: "",
      className: "",
      style: {},
      innerHTML: "",
      textContent: "",
      parentElement: null,
      querySelector() { return null; }
    };
  },
  querySelector(sel) {
    if (sel.includes("wsc_question_input_") && sel.includes("textarea")) return textarea;
    if (sel.includes("wsc_question_input_") || sel.includes("wsc-composer-")) return composerBlock;
    return null;
  },
  querySelectorAll() { return []; },
  addEventListener(type, fn) {
    listeners[type] = listeners[type] || [];
    listeners[type].push(fn);
  }
};
global.window = {
  parent: { document: parentDoc },
  HTMLTextAreaElement: { prototype: {} }
};
global.Event = function(type) { this.type = type; };
""" + js_code + """
textarea.value = "/";
for (const fn of (listeners["input"] || [])) {
  fn({ target: textarea });
}
const pal = window.parent.__wscActivePaletteEl;
if (!pal) throw new Error("Palette element not created");
if (pal.style.display !== "block") throw new Error("Palette display is not block: " + pal.style.display);
if (composerBlock.style.overflow !== "visible") throw new Error("composerBlock overflow not visible: " + composerBlock.style.overflow);
if (composerBlock.style.position !== "relative") throw new Error("composerBlock position not relative: " + composerBlock.style.position);
if (!pal.innerHTML.includes("/huongdan") || !pal.innerHTML.includes("/kynang")) {
  throw new Error("Palette innerHTML missing expected commands");
}
textarea.value = "/kynang";
for (const fn of (listeners["input"] || [])) {
  fn({ target: textarea });
}
if (!pal.innerHTML.includes("/kynang tao")) {
  throw new Error("Filtered palette missing /kynang tao");
}
window.parent.__wscSelectCommand(window.parent.__wscActiveItems[0]);
if (pal.style.display !== "none") throw new Error("Palette did not hide after selection");
if (!textarea.value.startsWith("/kynang")) throw new Error("Textarea value not updated on select: " + textarea.value);
console.log("PALETTE_TRIGGER_OK");
"""
    harness_file = tmp_path / "palette_harness.js"
    harness_file.write_text(node_harness, encoding="utf-8")
    proc = subprocess.run(["node", str(harness_file)], capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, f"Node execution failed: {proc.stderr}"
    assert "PALETTE_TRIGGER_OK" in proc.stdout
