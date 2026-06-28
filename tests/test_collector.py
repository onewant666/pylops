"""采集器测试"""

import pytest

from lhm.collector import (
    CPUCollector,
    DiskCollector,
    MemoryCollector,
    NetworkCollector,
    ProcessCollector,
    SystemCollector,
)
from lhm.config import HostConfig


@pytest.fixture
def local_host():
    """本地主机配置 fixture"""
    return HostConfig({"name": "localhost", "type": "local"})


class TestCPUCollector:
    def test_collect(self, local_host):
        collector = CPUCollector(local_host)
        result = collector.collect()
        assert result.success
        assert result.metric == "cpu"
        assert result.host == "localhost"
        assert "percent" in result.data
        assert "load_1m" in result.data
        assert isinstance(result.data["percent"], (int, float))


class TestMemoryCollector:
    def test_collect(self, local_host):
        collector = MemoryCollector(local_host)
        result = collector.collect()
        assert result.success
        assert result.metric == "memory"
        assert "percent" in result.data
        assert "swap_percent" in result.data


class TestDiskCollector:
    def test_collect(self, local_host):
        collector = DiskCollector(local_host)
        result = collector.collect()
        assert result.success
        assert result.metric == "disk"
        assert "partitions" in result.data


class TestNetworkCollector:
    def test_collect(self, local_host):
        collector = NetworkCollector(local_host)
        result = collector.collect()
        assert result.success
        assert result.metric == "network"
        assert "interfaces" in result.data


class TestProcessCollector:
    def test_collect(self, local_host):
        collector = ProcessCollector(local_host, top_n=5)
        result = collector.collect()
        assert result.success
        assert result.metric == "process"
        assert "top_processes" in result.data
        assert len(result.data["top_processes"]) <= 5


class TestSystemCollector:
    def test_collect(self, local_host):
        collector = SystemCollector(local_host)
        result = collector.collect()
        assert result.success
        assert result.metric == "system"
        assert "uptime" in result.data
        assert "load_ratio" in result.data
