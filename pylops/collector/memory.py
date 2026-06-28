"""内存指标采集器"""

from typing import Any, Dict

import psutil

from .base import BaseCollector


class MemoryCollector(BaseCollector):
    """采集物理内存和交换分区使用情况"""

    metric_name = "memory"

    def _gather(self) -> Dict[str, Any]:
        # 物理内存
        mem = psutil.virtual_memory()
        # 交换分区
        swap = psutil.swap_memory()

        def _to_gb(val: int) -> float:
            return round(val / (1024 ** 3), 2)

        # 平台兼容性警告
        if not hasattr(mem, "buffers"):
            self._warnings.append(
                "memory.buffers: 当前平台不可用（需要 Linux）"
            )
        if not hasattr(mem, "cached"):
            self._warnings.append(
                "memory.cached: 当前平台不可用（需要 Linux）"
            )

        return {
            # 物理内存 (单位: GB 和百分比)
            "total_gb": _to_gb(mem.total),
            "available_gb": _to_gb(mem.available),
            "used_gb": _to_gb(mem.used),
            "free_gb": _to_gb(mem.free),
            "percent": mem.percent,
            # 缓冲区 / 缓存（Linux 特有字段）
            "buffers_gb": _to_gb(getattr(mem, "buffers", 0)),
            "cached_gb": _to_gb(getattr(mem, "cached", 0)),
            # Swap
            "swap_total_gb": _to_gb(swap.total),
            "swap_used_gb": _to_gb(swap.used),
            "swap_free_gb": _to_gb(swap.free),
            "swap_percent": swap.percent,
        }
