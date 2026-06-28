"""采集器模块 — 各系统指标的采集器"""

from .base import BaseCollector, CollectorResult
from .cpu import CPUCollector
from .memory import MemoryCollector
from .disk import DiskCollector
from .network import NetworkCollector
from .process import ProcessCollector
from .system import SystemCollector

__all__ = [
    "BaseCollector",
    "CollectorResult",
    "CPUCollector",
    "MemoryCollector",
    "DiskCollector",
    "NetworkCollector",
    "ProcessCollector",
    "SystemCollector",
]
