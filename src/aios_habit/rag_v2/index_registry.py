"""Crash-safe active/candidate/previous index registry."""
from __future__ import annotations
import json, os, time, uuid
from pathlib import Path
from typing import Any
from aios_habit.benchmark_reference_registry import canonical_json
from .index_bundle import IndexBundleError, verify_index_bundle

class IndexRegistry:
    def __init__(self, root: str|Path): self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/"registry.json"
    def read(self) -> dict[str,Any]:
        if not self.path.exists(): return {"version":1,"active":None,"candidate":None,"previous":None}
        try: value=json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise IndexBundleError("Index registry is malformed") from exc
        if value.get("version")!=1: raise IndexBundleError("Index registry version is incompatible")
        return value
    def _write(self,value: dict[str,Any]) -> None:
        temp=self.root/f".{uuid.uuid4().hex}.tmp"; temp.write_text(canonical_json(value),encoding="utf-8"); os.replace(temp,self.path)
    def stage(self,bundle_dir: str|Path,*,expected_identity: dict[str,Any]) -> dict[str,Any]:
        manifest=verify_index_bundle(bundle_dir,expected_identity=expected_identity); value=self.read(); value["candidate"]={"path":str(Path(bundle_dir).resolve()),"identity_hash":manifest["identity_hash"]}; value["updated_at"]=time.time(); self._write(value); return value
    def activate(self) -> dict[str,Any]:
        value=self.read()
        if not value.get("candidate"): raise IndexBundleError("No verified candidate is staged")
        value["previous"],value["active"],value["candidate"]=value.get("active"),value["candidate"],None; value["updated_at"]=time.time(); self._write(value); return value
    def rollback(self) -> dict[str,Any]:
        value=self.read()
        if not value.get("previous"): raise IndexBundleError("No previous index is available")
        value["active"],value["previous"],value["candidate"]=value["previous"],value.get("active"),None; value["updated_at"]=time.time(); self._write(value); return value
