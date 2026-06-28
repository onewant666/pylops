"""网络指标采集器"""

from typing import Any, Dict, List

import psutil

from .base import BaseCollector


class NetworkCollector(BaseCollector):
    """采集网络接口流量和连接状态"""

    metric_name = "network"

    def _gather(self) -> Dict[str, Any]:
        # 各网络接口 IO 计数器
        interfaces: List[Dict[str, Any]] = []
        io = psutil.net_io_counters(pernic=True)
        for name, counters in io.items():
            # 跳过回环接口
            # if name == "lo":
            #     continue
            interfaces.append({
                "name": name,
                "bytes_sent_mb": round(counters.bytes_sent / (1024 ** 2), 2),
                "bytes_recv_mb": round(counters.bytes_recv / (1024 ** 2), 2),
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
                "errin": counters.errin,
                "errout": counters.errout,
                "dropin": counters.dropin,
                "dropout": counters.dropout,
            })

        # 汇总
        total_sent_mb = round(sum(i["bytes_sent_mb"] for i in interfaces), 2)
        total_recv_mb = round(sum(i["bytes_recv_mb"] for i in interfaces), 2)

        # 网络连接统计
        conns = psutil.net_connections(kind="inet")
        conn_summary = {
            "total": len(conns),
            "established": sum(1 for c in conns if c.status == "ESTABLISHED"),
            "listen": sum(1 for c in conns if c.status == "LISTEN"),
            "time_wait": sum(1 for c in conns if c.status == "TIME_WAIT"),
            "close_wait": sum(1 for c in conns if c.status == "CLOSE_WAIT"),
        }

        return {
            "interfaces": interfaces,
            "total_sent_mb": total_sent_mb,
            "total_recv_mb": total_recv_mb,
            "connections": conn_summary,
        }
