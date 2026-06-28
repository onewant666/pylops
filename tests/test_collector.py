"""采集器测试"""

import pytest

from pylops.collector import (
    CPUCollector,
    DiskCollector,
    MemoryCollector,
    NetworkCollector,
    ProcessCollector,
    SystemCollector,
)
from pylops.config import HostConfig


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


# ===================== 平台兼容性测试 =====================


class TestCPUCollectorPlatformFallback:
    """验证非 Linux 平台上采集器不崩溃，而是返回 warning"""

    def test_getloadavg_not_implemented(self, local_host, monkeypatch):
        """getloadavg() 抛出 NotImplementedError 时不应崩溃"""
        def mock_getloadavg():
            raise NotImplementedError("mock platform limitation")
        monkeypatch.setattr("psutil.getloadavg", mock_getloadavg)
        collector = CPUCollector(local_host)
        result = collector.collect()
        assert result.success, "采集器不应因 getloadavg 失败而崩溃"
        assert result.data["load_1m"] is None
        assert any("load_avg" in w for w in result.warnings)


class TestSystemCollectorPlatformFallback:
    """验证非 Linux 平台上系统采集器不崩溃"""

    def test_getloadavg_not_implemented(self, local_host, monkeypatch):
        """getloadavg() 抛出 NotImplementedError 时不应崩溃"""
        def mock_getloadavg():
            raise NotImplementedError("mock platform limitation")
        monkeypatch.setattr("psutil.getloadavg", mock_getloadavg)
        collector = SystemCollector(local_host)
        result = collector.collect()
        assert result.success, "采集器不应因 getloadavg 失败而崩溃"
        assert result.data["load_1m"] is None
        assert result.data["load_ratio"] is None
        assert any("load_avg" in w for w in result.warnings)


class TestMemoryCollectorPlatformFallback:
    """验证 buffers/cached 缺失时的平台警告"""

    def test_buffers_not_available(self, local_host, monkeypatch):
        """当 virtual_memory 没有 buffers 属性时产生 warning"""
        import psutil
        from collections import namedtuple

        original = psutil.virtual_memory()

        class NoBuffersMem:
            total = original.total
            available = original.available
            used = original.used
            free = original.free
            percent = original.percent

            # 刻意不定义 buffers 和 cached
            def __getattr__(self, name):
                raise AttributeError(f"No such attribute: {name}")

        monkeypatch.setattr(psutil, "virtual_memory", lambda: NoBuffersMem())
        collector = MemoryCollector(local_host)
        result = collector.collect()
        assert result.success
        assert any("buffers" in w for w in result.warnings)
        assert any("cached" in w for w in result.warnings)


class TestExecutorLazyImport:
    """验证 executor 的延迟导入机制"""

    def test_local_executor_without_paramiko(self):
        """paramiko 未安装时 import LocalExecutor 不应崩溃"""
        import sys
        # 临时移除 paramiko（如果已安装）
        paramiko_backup = sys.modules.pop("paramiko", None)
        # 也需移除远程模块缓存
        sys.modules.pop("pylops.executor.remote", None)
        try:
            from pylops.executor import LocalExecutor
            assert LocalExecutor is not None
        finally:
            if paramiko_backup is not None:
                sys.modules["paramiko"] = paramiko_backup


class TestCheckResultDataAvailability:
    """验证 CheckResult 的 data_available 字段"""

    def test_data_unavailable_flag(self):
        from pylops.checker.engine import CheckResult

        result = CheckResult(
            host="test",
            rule_name="test_rule",
            description="Test",
            severity="warning",
            passed=True,
            data_available=False,
            detail={"error": "指标 cpu 没有采集数据"},
        )
        assert result.data_available is False
        assert result.passed is True  # 无数据时不告警
        d = result.to_dict()
        assert "data_available" in d
        assert d["data_available"] is False
