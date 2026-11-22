# Copyright 2024 URACE Contributors
# Concept adapted from mesh-llm/src/hardware_survey.rs (Apache 2.0)
from __future__ import annotations
import dataclasses
import os
import platform
import threading
from typing import Any

@dataclasses.dataclass
class HardwareInfo:
    cpu_count: int
    ram_mb: int
    gpu_names: list[str]
    vram_mb: list[int]  # parallel to gpu_names; 0 if unknown

@dataclasses.dataclass
class ModelMetadata:
    model_ref: str          # hf://namespace/repo@revision or local path
    architecture: str       # e.g. "llama", "mistral"
    param_count: int        # 0 if unknown
    context_length: int     # 0 if unknown
    quantization: str       # "q4_k_m", "f16", etc.; "" if unknown

def survey_hardware() -> HardwareInfo:
    """Best-effort hardware survey. Never raises; falls back to zeros."""
    try:
        cpu_count = os.cpu_count() or 0
    except Exception:
        cpu_count = 0
    try:
        import psutil
        ram_mb = psutil.virtual_memory().total // (1024 * 1024)
    except Exception:
        ram_mb = 0
    gpu_names: list[str] = []
    vram_mb: list[int] = []
    try:
        import subprocess
        out = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=name,memory.total',
             '--format=csv,noheader,nounits'],
            timeout=5, stderr=subprocess.DEVNULL,
        ).decode()
        for line in out.strip().splitlines():
            parts = line.split(',', 1)
            if len(parts) == 2:
                gpu_names.append(parts[0].strip())
                try:
                    vram_mb.append(int(parts[1].strip()))
                except ValueError:
                    vram_mb.append(0)
    except Exception:
        pass
    return HardwareInfo(cpu_count=cpu_count, ram_mb=ram_mb,
                        gpu_names=gpu_names, vram_mb=vram_mb)

_SURVEY_LOCK = threading.Lock()
_CACHED_SURVEY: HardwareInfo | None = None

def get_hardware_info(refresh: bool = False) -> HardwareInfo:
    """Return cached survey result; refresh=True forces a new survey."""
    global _CACHED_SURVEY
    with _SURVEY_LOCK:
        if _CACHED_SURVEY is None or refresh:
            _CACHED_SURVEY = survey_hardware()
        return _CACHED_SURVEY

def hardware_gossip_payload() -> dict[str, Any]:
    hw = get_hardware_info()
    return {
        'cpu_count': hw.cpu_count,
        'ram_mb': hw.ram_mb,
        'gpu_names': hw.gpu_names,
        'vram_mb': hw.vram_mb,
    }
