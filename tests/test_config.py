"""配置加载测试"""

import tempfile
from pathlib import Path

import pytest

from lhm.config import Config, load_config


class TestConfig:
    """测试配置加载"""

    def test_load_default_config(self):
        """测试加载项目默认的 config.yaml"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        if not config_path.exists():
            pytest.skip("默认 config.yaml 不存在")

        cfg = Config(config_path)
        assert len(cfg.hosts) >= 1
        assert "cpu" in cfg.metrics
        assert len(cfg.rules) >= 1
        assert cfg.interval_seconds >= 1

    def test_localhost_is_present(self):
        """测试本地主机默认存在"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        cfg = Config(config_path)
        local_names = [h.name for h in cfg.local_hosts]
        assert "localhost" in local_names

    def test_enabled_metrics(self):
        """测试启用的指标过滤"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        cfg = Config(config_path)
        enabled = cfg.enabled_metrics
        assert isinstance(enabled, list)
        # 至少应有 cpu 和 memory
        assert "cpu" in enabled

    def test_enabled_rules(self):
        """测试启用的规则过滤"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        cfg = Config(config_path)
        enabled = cfg.enabled_rules
        assert isinstance(enabled, list)
        for rule in enabled:
            assert rule.enabled is True
