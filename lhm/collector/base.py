"""采集器基类 — 定义统一接口"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

from ..utils.helpers import now_iso


@dataclass
class CollectorResult:
    """单次采集结果"""
    host: str                    # 主机名
    metric: str                  # 指标名: cpu/memory/disk/network/process/system
    timestamp: str = field(default_factory=now_iso)
    success: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseCollector:
    """采集器基类 — 所有具体采集器继承此类"""

    metric_name: str = "base"  # 子类覆盖

    def __init__(self, host_config):
        """
        初始化采集器

        Args:
            host_config: HostConfig 对象
        """
        self.host = host_config

    def collect(self) -> CollectorResult:
        """
        执行采集，返回 CollectorResult。
        子类应覆盖 _gather() 方法而非此方法。
        """
        try:
            data = self._gather()
            return CollectorResult(
                host=self.host.name,
                metric=self.metric_name,
                success=True,
                data=data,
            )
        except Exception as e:
            return CollectorResult(
                host=self.host.name,
                metric=self.metric_name,
                success=False,
                error=str(e),
            )

    def _gather(self) -> Dict[str, Any]:
        """子类覆盖：采集具体指标数据"""
        raise NotImplementedError
