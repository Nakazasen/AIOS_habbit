from __future__ import annotations
from dataclasses import dataclass
import pytest
from aios_habit.rag_v2.ingestion_workers import WorkerCapability, WorkerRoutingError, execution_policy, next_batch_size, route_worker
@dataclass
class Worker:
    value: WorkerCapability
    def capability(self): return self.value
def cap(worker_id,kind,device="cpu",vram=0,labels=("cloud_safe",),healthy=True): return WorkerCapability(worker_id,kind,True,healthy,labels,device,vram,device=="cuda")
def test_routes_local_gpu_then_remote_then_cpu():
    cpu=Worker(cap("cpu","local")); remote=Worker(cap("remote","remote","cuda",16000)); local=Worker(cap("gpu","local","cuda",8000))
    assert route_worker([cpu,remote,local],privacy_label="cloud_safe")[1].worker_id=="gpu"
    assert route_worker([cpu,remote],privacy_label="cloud_safe")[1].worker_id=="remote"
def test_local_only_never_routes_to_cloud():
    remote=Worker(cap("remote","remote","cuda",16000)); local=Worker(cap("cpu","local",labels=("local_only",)))
    assert route_worker([remote,local],privacy_label="local_only")[1].worker_id=="cpu"
    with pytest.raises(WorkerRoutingError): route_worker([remote],privacy_label="local_only")
def test_low_vram_uses_micro_batch_and_oom_halves():
    policy=execution_policy(cap("1060","local","cuda",3072),preferred_batch_size=16)
    assert policy.batch_size==1 and policy.use_fp16 is True
    assert next_batch_size(8,RuntimeError("CUDA out of memory"))==4
    assert next_batch_size(1,RuntimeError("CUDA out of memory")) is None
    assert next_batch_size(8,RuntimeError("bad input")) is None
