from __future__ import annotations
import sqlite3
from pathlib import Path
import pytest
from aios_habit.rag_v2.index_bundle import IndexBundleError, export_index_bundle, import_index_bundle, verify_index_bundle
from aios_habit.rag_v2.index_registry import IndexRegistry

def make_index(path: Path, value: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE documents(value TEXT)"); connection.execute("INSERT INTO documents VALUES(?)",(value,))
def identity(name: str="a") -> dict: return {"corpus":name,"model":"bge-m3","schema":"rag-v2","chunking":"v2"}

def test_bundle_export_verify_import(tmp_path: Path):
    index=tmp_path/"index.sqlite"; make_index(index,"hello"); bundle=tmp_path/"bundle"
    export_index_bundle(index,bundle,identity=identity()); assert verify_index_bundle(bundle,expected_identity=identity())["index_filename"]=="index.sqlite"
    imported=import_index_bundle(bundle,tmp_path/"installed",expected_identity=identity())
    with sqlite3.connect(imported) as connection: assert connection.execute("SELECT value FROM documents").fetchone()[0]=="hello"

def test_bundle_rejects_corruption_and_identity_mismatch(tmp_path: Path):
    index=tmp_path/"index.sqlite"; make_index(index,"hello"); bundle=tmp_path/"bundle"; export_index_bundle(index,bundle,identity=identity())
    with pytest.raises(IndexBundleError,match="incompatible"): verify_index_bundle(bundle,expected_identity=identity("b"))
    with (bundle/"index.sqlite").open("ab") as stream: stream.write(b"tamper")
    with pytest.raises(IndexBundleError,match="checksum"): verify_index_bundle(bundle)

def test_registry_activate_and_rollback(tmp_path: Path):
    registry=IndexRegistry(tmp_path/"registry")
    first=tmp_path/"first.sqlite"; make_index(first,"first"); first_bundle=tmp_path/"bundle1"; export_index_bundle(first,first_bundle,identity=identity("1"))
    registry.stage(first_bundle,expected_identity=identity("1")); assert registry.activate()["active"]["path"]==str(first_bundle.resolve())
    second=tmp_path/"second.sqlite"; make_index(second,"second"); second_bundle=tmp_path/"bundle2"; export_index_bundle(second,second_bundle,identity=identity("2"))
    registry.stage(second_bundle,expected_identity=identity("2")); activated=registry.activate(); assert activated["previous"]["path"]==str(first_bundle.resolve())
    rolled=registry.rollback(); assert rolled["active"]["path"]==str(first_bundle.resolve())
