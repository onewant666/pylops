"""进程信息采集器"""

from typing import Any, Dict, List

import psutil

from .base import BaseCollector


class ProcessCollector(BaseCollector):
    """采集 Top N 进程信息（按 CPU 占用排序）"""

    metric_name = "process"

    def __init__(self, host_config, top_n: int = 10):
        super().__init__(host_config)
        self.top_n = top_n

    def _gather(self) -> Dict[str, Any]:
        procs: List[Dict[str, Any]] = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent",
                                          "memory_percent", "status"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": round(info["cpu_percent"] or 0, 2),
                    "memory_percent": round(info["memory_percent"] or 0, 3),
                    "status": info["status"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 按 CPU 占用降序排列
        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        top_procs = procs[:self.top_n]

        # 统计进程状态
        status_counts = {}
        for p in procs:
            st = p["status"]
            status_counts[st] = status_counts.get(st, 0) + 1

        return {
            "total_count": len(procs),
            "top_n": self.top_n,
            "top_processes": top_procs,
            "status_summary": status_counts,
        }
