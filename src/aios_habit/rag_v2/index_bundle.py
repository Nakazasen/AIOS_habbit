"""Portable, integrity-checked RAG index bundles."""
from __future__ import annotations
import hashlib, json, shutil, sqlite3, tempfile, time
from pathlib import Path
from typing import Any, Mapping, Sequence
from aios_habit.benchmark_reference_registry import canonical_json, stable_hash

BUNDLE_VERSION=1
class IndexBundleError(RuntimeError): pass

def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest()

def _integrity(path: Path) -> None:
    try:
        connection=sqlite3.connect(f"file:{path.as_posix()}?mode=ro",uri=True)
        result=connection.execute("PRAGMA integrity_check").fetchone()[0]; connection.close()
    except sqlite3.DatabaseError as exc: raise IndexBundleError("Bundle SQLite cannot be opened") from exc
    if result!="ok": raise IndexBundleError(f"Bundle SQLite integrity failed: {result}")

def export_index_bundle(index_path: str|Path, bundle_dir: str|Path, *, identity: Mapping[str,Any], extra_files: Sequence[str|Path]=()) -> dict[str,Any]:
    index_path=Path(index_path); bundle_dir=Path(bundle_dir)
    if not index_path.is_file(): raise IndexBundleError(f"Index is missing: {index_path}")
    _integrity(index_path); bundle_dir.mkdir(parents=True,exist_ok=True)
    files=[index_path,*map(Path,extra_files)]; records=[]
    for source in files:
        if not source.is_file(): raise IndexBundleError(f"Bundle input is missing: {source}")
        target=bundle_dir/source.name; shutil.copy2(source,target); records.append({"name":source.name,"size":target.stat().st_size,"sha256":_sha256(target)})
    manifest={"bundle_version":BUNDLE_VERSION,"identity":dict(identity),"identity_hash":stable_hash(dict(identity)),"files":records,"index_filename":index_path.name,"created_at":int(time.time())}
    (bundle_dir/"manifest.json").write_text(canonical_json(manifest),encoding="utf-8")
    return manifest

def verify_index_bundle(bundle_dir: str|Path, *, expected_identity: Mapping[str,Any]|None=None) -> dict[str,Any]:
    bundle_dir=Path(bundle_dir); manifest_path=bundle_dir/"manifest.json"
    try: manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise IndexBundleError("Bundle manifest is missing or malformed") from exc
    if int(manifest.get("bundle_version",0))!=BUNDLE_VERSION: raise IndexBundleError("Bundle version is incompatible")
    identity=manifest.get("identity")
    if not isinstance(identity,dict) or stable_hash(identity)!=manifest.get("identity_hash"): raise IndexBundleError("Bundle identity hash mismatch")
    if expected_identity is not None and canonical_json(identity)!=canonical_json(dict(expected_identity)): raise IndexBundleError("Bundle identity is incompatible")
    records=manifest.get("files")
    if not isinstance(records,list) or not records: raise IndexBundleError("Bundle has no files")
    for record in records:
        path=bundle_dir/str(record.get("name") or "")
        if not path.is_file() or path.stat().st_size!=int(record.get("size",-1)) or _sha256(path)!=record.get("sha256"): raise IndexBundleError(f"Bundle checksum failed: {path.name}")
    index=bundle_dir/str(manifest.get("index_filename") or ""); _integrity(index)
    return manifest

def import_index_bundle(bundle_dir: str|Path, destination: str|Path, *, expected_identity: Mapping[str,Any]) -> Path:
    bundle_dir=Path(bundle_dir); destination=Path(destination); manifest=verify_index_bundle(bundle_dir,expected_identity=expected_identity)
    destination.mkdir(parents=True,exist_ok=True); source=bundle_dir/manifest["index_filename"]
    with tempfile.NamedTemporaryFile(dir=destination,delete=False,suffix=".candidate") as stream: temp=Path(stream.name)
    try:
        shutil.copy2(source,temp); _integrity(temp); final=destination/manifest["index_filename"]; temp.replace(final); return final
    finally:
        temp.unlink(missing_ok=True)
