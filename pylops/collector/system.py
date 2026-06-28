"""系统信息采集器"""

import os
from datetime import datetime
from typing import Any, Dict

import psutil

from .base import BaseCollector


class SystemCollector(BaseCollector):
    """采集系统负载、运行时间、登录用户等"""

    metric_name = "system"

    def _gather(self) -> Dict[str, Any]:
        # 启动时间
        boot_time = datetime.fromtimestamp(psutil.boot_time())

        # 运行时长
        uptime_seconds = (datetime.now() - boot_time).total_seconds()
        uptime_str = self._format_uptime(uptime_seconds)

        # 登录用户
        users = []
        for u in psutil.users():
            users.append({
                "name": u.name,
                "terminal": u.terminal,
                "host": u.host,
                "started": datetime.fromtimestamp(u.started).isoformat(),
            })

        # CPU 负载比（仅 Linux/Unix 可用）
        cpu_count = psutil.cpu_count() or 1
        try:
            load_avg = psutil.getloadavg()
            load_1m = round(load_avg[0], 2)
            load_5m = round(load_avg[1], 2)
            load_15m = round(load_avg[2], 2)
            load_ratio = round(load_avg[0] / cpu_count, 2)
        except (NotImplementedError, AttributeError):
            load_1m = load_5m = load_15m = None
            load_ratio = None
            self._warnings.append(
                "system.load_avg: 当前平台不可用（需要 Linux/Unix）"
            )

        # 文件描述符（仅 Linux）
        try:
            fd_used = len(os.listdir("/proc/self/fd"))
            fd_max = os.sysconf("SC_OPEN_MAX")
        except FileNotFoundError:
            fd_used = fd_max = None
            self._warnings.append(
                "system.fd: /proc/self/fd 不可用（需要 Linux）"
            )
        except (OSError, ValueError):
            fd_used = fd_max = None

        return {
            "hostname": psutil.users()[0].host if psutil.users() else "unknown",
            "boot_time": boot_time.isoformat(),
            "uptime_seconds": int(uptime_seconds),
            "uptime": uptime_str,
            # 负载
            "load_1m": load_1m,
            "load_5m": load_5m,
            "load_15m": load_15m,
            "cpu_count": cpu_count,
            "load_ratio": load_ratio,
            # 登录用户
            "users": users,
            "user_count": len(users),
            # 文件描述符
            "fd_used": fd_used,
            "fd_max": fd_max,
        }

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """将秒数格式化为可读的时长字符串"""
        days, rem = divmod(int(seconds), 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        return " ".join(parts) if parts else "<1m"
