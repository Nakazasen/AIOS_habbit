"""Unattended polling service for durable ingestion jobs."""
from __future__ import annotations
import hashlib, threading, time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence
from .ingestion_jobs import IngestionJob, IngestionJobIdentity, IngestionJobStore

@dataclass(frozen=True)
class ServiceStatus:
    running: bool; worker_id: str; active_job_id: str=""; last_error_code: str=""
JobHandler=Callable[[IngestionJob,str],None]
IdentityFactory=Callable[[str],IngestionJobIdentity]

def directory_manifest(root:str|Path)->list[dict[str,object]]:
    root=Path(root); rows=[]
    for path in sorted((item for item in root.rglob("*") if item.is_file()),key=lambda item:item.relative_to(root).as_posix().casefold()):
        digest=hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda:stream.read(1024*1024),b""): digest.update(block)
        relative=path.relative_to(root).as_posix(); rows.append({"unit_id":relative,"sha256":digest.hexdigest(),"size":path.stat().st_size})
    return rows

def manifest_fingerprint(manifest:Sequence[Mapping[str,object]])->str:
    digest=hashlib.sha256()
    for row in manifest: digest.update(f"{row['unit_id']}\0{row['sha256']}\0{row['size']}\n".encode())
    return digest.hexdigest()

class IngestionService:
    def __init__(self,store:IngestionJobStore,handler:JobHandler,*,worker_id:str="local-service",poll_seconds:float=2.0,lease_seconds:float=120.0):
        self.store=store; self.handler=handler; self.worker_id=worker_id; self.poll_seconds=poll_seconds; self.lease_seconds=lease_seconds; self._stop=threading.Event(); self._thread:threading.Thread|None=None; self._active=""; self._error=""; self._lock=threading.Lock()
    def start(self)->None:
        with self._lock:
            if self._thread and self._thread.is_alive(): return
            self._stop.clear(); self._thread=threading.Thread(target=self.run_forever,name="rag-ingestion-service",daemon=True); self._thread.start()
    def stop(self,*,timeout:float=5.0)->None:
        self._stop.set(); thread=self._thread
        if thread: thread.join(timeout)
    def status(self)->ServiceStatus:
        thread=self._thread; return ServiceStatus(bool(thread and thread.is_alive()),self.worker_id,self._active,self._error)
    def run_once(self)->bool:
        claimed=self.store.claim(self.worker_id,lease_seconds=self.lease_seconds)
        if claimed is None: return False
        job,token=claimed; self._active=job.job_id; self._error=""
        try: self.handler(job,token)
        except Exception as exc: self._error=type(exc).__name__; raise
        finally: self._active=""
        return True
    def run_forever(self)->None:
        while not self._stop.is_set():
            try:
                if not self.run_once(): self._stop.wait(self.poll_seconds)
            except Exception: self._stop.wait(self.poll_seconds)

class DirectoryJobWatcher:
    def __init__(self,root:str|Path,store:IngestionJobStore,identity_factory:IdentityFactory,*,debounce_seconds:float=2.0):
        self.root=Path(root); self.store=store; self.identity_factory=identity_factory; self.debounce_seconds=debounce_seconds; self._last=""; self._submitted=""; self._changed_at=0.0
    def scan(self,*,now:float|None=None)->IngestionJob|None:
        now=time.time() if now is None else now; manifest=directory_manifest(self.root)
        if not manifest: return None
        fingerprint=manifest_fingerprint(manifest)
        if fingerprint!=self._last:
            self._last=fingerprint; self._submitted=""; self._changed_at=now; return None
        if now-self._changed_at<self.debounce_seconds: return None
        job,_=self.store.submit(self.identity_factory(fingerprint),manifest); self._submitted=fingerprint; return job
