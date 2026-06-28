"""CPU 指标采集器"""

from typing import Any, Dict

import psutil

from .base import BaseCollector


class CPUCollector(BaseCollector):
    """采集 CPU 使用率、频率、逻辑核心数等信息"""

    metric_name = "cpu"

    def _gather(self) -> Dict[str, Any]:
        # CPU 使用率（各核心 + 平均）
        percent_per_cpu = psutil.cpu_percent(interval=1, percpu=True)
        percent_avg = psutil.cpu_percent(interval=0)  # 以上次调用为基准

        # CPU 频率
        freq = psutil.cpu_freq()
        freq_current = freq.current if freq else None
        freq_max = freq.max if freq else None

        # CPU 时间统计
        times = psutil.cpu_times()
        # 计算各状态占比
        total = sum(times)
        if total > 0:
            user_pct = round(times.user / total * 100, 1)
            system_pct = round(times.system / total * 100, 1)
            idle_pct = round(times.idle / total * 100, 1)
            iowait_pct = round(
                (getattr(times, "iowait", 0) / total * 100), 1
            )
        else:
            user_pct = system_pct = idle_pct = iowait_pct = 0

        # 负载（仅 Linux/Unix 可用）
        try:
            load_avg = psutil.getloadavg()
            load_1m = round(load_avg[0], 2)
            load_5m = round(load_avg[1], 2)
            load_15m = round(load_avg[2], 2)
        except (NotImplementedError, AttributeError):
            load_1m = load_5m = load_15m = None
            self._warnings.append(
                "cpu.load_avg: 当前平台不可用（需要 Linux/Unix）"
            )

        # iowait 平台检测
        if not hasattr(times, "iowait"):
            self._warnings.append(
                "cpu.iowait_pct: 当前平台不可用（需要 Linux）"
            )

        return {
            # 使用率
            "percent": round(percent_avg, 1),
            "percent_per_cpu": [round(p, 1) for p in percent_per_cpu],
            # 频率
            "freq_current": freq_current,
            "freq_max": freq_max,
            # 核心数
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            # 时间占比
            "user_pct": user_pct,
            "system_pct": system_pct,
            "idle_pct": idle_pct,
            "iowait_pct": iowait_pct,
            # 负载
            "load_1m": load_1m,
            "load_5m": load_5m,
            "load_15m": load_15m,
        }
