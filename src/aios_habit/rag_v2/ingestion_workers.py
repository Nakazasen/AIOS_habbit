"""Capability-aware routing for local and managed ingestion workers."""
from __future__ import annotations
import importlib.util
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

@dataclass(frozen=True)
class WorkerCapability:
    worker_id: str; kind: str; available: bool; healthy: bool; privacy_labels: tuple[str,...]
    device: str="cpu"; vram_mb: int=0; supports_fp16: bool=False; reason: str=""
@dataclass(frozen=True)
class EmbeddingExecutionPolicy:
    device: str; use_fp16: bool; batch_size: int; min_batch_size: int=1
class IngestionWorker(Protocol):
    def capability(self) -> WorkerCapability: ...
class WorkerRoutingError(RuntimeError): pass

def probe_local_accelerator() -> WorkerCapability:
    if importlib.util.find_spec("torch") is None:
        return WorkerCapability("local-cpu","local",True,True,("local_only","cloud_safe","public"),reason="torch_not_installed")
    try:
        import torch
        if not torch.cuda.is_available():
            return WorkerCapability("local-cpu","local",True,True,("local_only","cloud_safe","public"),reason="cuda_unavailable")
        props=torch.cuda.get_device_properties(0); vram=int(props.total_memory//(1024*1024))
        return WorkerCapability("local-cuda","local",True,True,("local_only","cloud_safe","public"),"cuda",vram,True,str(props.name))
    except Exception as exc:
        return WorkerCapability("local-cpu","local",True,True,("local_only","cloud_safe","public"),reason=f"cuda_probe_failed:{type(exc).__name__}")

def execution_policy(capability: WorkerCapability, *, preferred_batch_size: int=16) -> EmbeddingExecutionPolicy:
    if capability.device!="cuda" or not capability.available or not capability.healthy:
        return EmbeddingExecutionPolicy("cpu",False,max(1,min(preferred_batch_size,4)))
    if capability.vram_mb<4096:
        return EmbeddingExecutionPolicy("cuda",True,1)
    if capability.vram_mb<8192:
        return EmbeddingExecutionPolicy("cuda",True,min(preferred_batch_size,4))
    return EmbeddingExecutionPolicy("cuda",True,preferred_batch_size)

def next_batch_size(current: int, error: BaseException) -> int | None:
    message=str(error).lower()
    if "out of memory" not in message and "cuda oom" not in message: return None
    return current//2 if current>1 else None

def route_worker(workers: Sequence[IngestionWorker], *, privacy_label: str) -> tuple[IngestionWorker,WorkerCapability]:
    candidates=[]
    for worker in workers:
        capability=worker.capability()
        if capability.available and capability.healthy and privacy_label in capability.privacy_labels:
            priority=(0 if capability.device=="cuda" and capability.kind=="local" else 1 if capability.device=="cuda" else 2 if capability.kind=="remote" else 3)
            candidates.append((priority,worker,capability))
    if not candidates: raise WorkerRoutingError(f"No healthy worker accepts privacy label: {privacy_label}")
    _,worker,capability=min(candidates,key=lambda item:item[0]); return worker,capability
