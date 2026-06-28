"""磁盘指标采集器"""

from typing import Any, Dict, List

import psutil

from .base import BaseCollector


class DiskCollector(BaseCollector):
    """采集磁盘分区使用率和 IO 统计"""

    metric_name = "disk"

    def _gather(self) -> Dict[str, Any]:
        # 磁盘分区信息
        partitions: List[Dict[str, Any]] = []
        for p in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(p.mountpoint)
                partitions.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "free_gb": round(usage.free / (1024 ** 3), 2),
                    "percent": usage.percent,
                })
            except PermissionError:
                continue

        # 最高使用率的分区
        worst = max(partitions, key=lambda x: x["percent"]) if partitions else None

        # 磁盘 IO 统计
        io = psutil.disk_io_counters()
        io_stats = {}
        if io:
            io_stats = {
                "read_count": io.read_count,
                "write_count": io.write_count,
                "read_bytes_mb": round(io.read_bytes / (1024 ** 2), 1),
                "write_bytes_mb": round(io.write_bytes / (1024 ** 2), 1),
            }

        return {
            "partitions": partitions,
            "partition_count": len(partitions),
            "worst_partition": worst,
            "worst_percent": worst["percent"] if worst else 0,
            "io": io_stats,
        }
