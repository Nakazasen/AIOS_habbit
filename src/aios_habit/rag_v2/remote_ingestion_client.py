"""Resumable, checksum-verified transport for managed ingestion workers."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import urllib.error, urllib.request
from typing import Any, Callable, Mapping
class RemoteIngestionError(RuntimeError): pass
class RemoteCapacityUnavailable(RemoteIngestionError): pass
class RemoteIngestionClient:
    def __init__(self,base_url:str,token_provider:Callable[[],str],*,timeout_seconds:float=30.0,chunk_size:int=8*1024*1024): self.base_url=base_url.rstrip("/"); self.token_provider=token_provider; self.timeout_seconds=timeout_seconds; self.chunk_size=chunk_size
    def _json(self,method:str,path:str,payload:Mapping[str,Any]|None=None)->dict[str,Any]:
        data=None if payload is None else json.dumps(dict(payload),separators=(",",":"),sort_keys=True).encode(); request=urllib.request.Request(self.base_url+path,data=data,method=method,headers={"Authorization":f"Bearer {self.token_provider()}","Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(request,timeout=self.timeout_seconds) as response: return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code in {429,503}: raise RemoteCapacityUnavailable(f"remote_capacity_{exc.code}") from exc
            raise RemoteIngestionError(f"remote_http_{exc.code}") from exc
        except (urllib.error.URLError,TimeoutError) as exc: raise RemoteCapacityUnavailable("remote_unreachable") from exc
    def submit(self,*,idempotency_key:str,identity:Mapping[str,Any],total_size:int,sha256:str)->dict[str,Any]: return self._json("POST","/v1/jobs",{"idempotency_key":idempotency_key,"identity":dict(identity),"total_size":total_size,"sha256":sha256})
    def status(self,job_id:str)->dict[str,Any]: return self._json("GET",f"/v1/jobs/{job_id}")
    def cancel(self,job_id:str)->dict[str,Any]: return self._json("POST",f"/v1/jobs/{job_id}/cancel",{})
    def upload_file(self,job_id:str,source:str|Path,*,start_offset:int=0)->int:
        source=Path(source); offset=start_offset
        with source.open("rb") as stream:
            stream.seek(offset)
            while block:=stream.read(self.chunk_size):
                digest=hashlib.sha256(block).hexdigest(); request=urllib.request.Request(self.base_url+f"/v1/jobs/{job_id}/source",data=block,method="PATCH",headers={"Authorization":f"Bearer {self.token_provider()}","Content-Type":"application/octet-stream","Upload-Offset":str(offset),"Chunk-SHA256":digest})
                try:
                    with urllib.request.urlopen(request,timeout=self.timeout_seconds) as response: acknowledged=int(response.headers.get("Upload-Offset",offset+len(block)))
                except (urllib.error.URLError,TimeoutError) as exc: raise RemoteCapacityUnavailable("upload_interrupted") from exc
                if acknowledged!=offset+len(block): raise RemoteIngestionError("upload_offset_mismatch")
                offset=acknowledged
        return offset
    def download_bundle(self,job_id:str,destination:str|Path,*,expected_sha256:str)->Path:
        destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True); offset=destination.stat().st_size if destination.exists() else 0; request=urllib.request.Request(self.base_url+f"/v1/jobs/{job_id}/bundle",method="GET",headers={"Authorization":f"Bearer {self.token_provider()}","Range":f"bytes={offset}-"})
        try:
            with urllib.request.urlopen(request,timeout=self.timeout_seconds) as response,destination.open("ab") as stream:
                while block:=response.read(self.chunk_size): stream.write(block)
        except (urllib.error.URLError,TimeoutError) as exc: raise RemoteCapacityUnavailable("download_interrupted") from exc
        digest=hashlib.sha256()
        with destination.open("rb") as stream:
            for block in iter(lambda:stream.read(1024*1024),b""): digest.update(block)
        if digest.hexdigest()!=expected_sha256: raise RemoteIngestionError("download_checksum_mismatch")
        return destination
