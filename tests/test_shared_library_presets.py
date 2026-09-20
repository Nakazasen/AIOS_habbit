from pathlib import Path
import json

from aios_habit import workspace_chat_store as store
from aios_habit.shared_library_presets import find_preset, load_presets
from aios_habit.workspace_chat_store import ensure_preset_collection, preset_collection_id


def test_preset_registry_scales_to_many_stores(tmp_path: Path):
    manifest = tmp_path / "presets"
    manifest.mkdir()
    for index in range(10):
        (manifest / f"kho-{index:02d}.json").write_text(json.dumps({
            "name": f"Kho {index:02d}",
            "description": "Kho dùng chung",
            "folder": f"D:\\KhoChung\\Kho{index:02d}",
            "version": "v1",
            "doc_count": index,
        }), encoding="utf-8")
    (manifest / "hong.json").write_text("{khong phai json", encoding="utf-8")
    presets = load_presets(manifest)
    assert len(presets) == 10
    assert find_preset(presets, "kho 03") is not None
    assert find_preset(presets, "khong co") is None
    assert load_presets(tmp_path / "khong-co") == []


def test_preset_collection_id_stable():
    assert preset_collection_id("Kho Iris LSU") == preset_collection_id("kho  iris   lsu")
    assert preset_collection_id("Kho Iris LSU").startswith("kho-")


def test_each_preset_owns_its_collection(tmp_path, monkeypatch):
    test_dir = tmp_path / "chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "COLLECTIONS_FILE", test_dir / "collections.jsonl")
    first_folder = tmp_path / "kho-a"
    second_folder = tmp_path / "kho-b"
    first_folder.mkdir()
    second_folder.mkdir()
    first = ensure_preset_collection(
        "Kho A", "", str(first_folder), local_fallback_root=tmp_path / "local",
    )
    second = ensure_preset_collection(
        "Kho B", "", str(second_folder), local_fallback_root=tmp_path / "local",
    )
    assert first.id != second.id
    assert first.storage_root == str(first_folder)
    assert store.load_collection(first.id).storage_root == str(first_folder)
    again = ensure_preset_collection(
        "Kho A", "", str(first_folder), local_fallback_root=tmp_path / "local",
    )
    assert again.id == first.id
