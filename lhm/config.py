"""配置加载模块 — 读取并验证 config.yaml"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# 默认配置路径
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class HostConfig:
    """单台主机配置"""
    def __init__(self, raw: Dict[str, Any]):
        self.name: str = raw["name"]
        self.type: str = raw.get("type", "local")  # local | remote
        self.host: Optional[str] = raw.get("host")
        self.port: int = raw.get("port", 22)
        self.username: Optional[str] = raw.get("username")
        self.password: Optional[str] = raw.get("password")
        self.key_file: Optional[str] = raw.get("key_file")

    def __repr__(self):
        return f"HostConfig(name={self.name!r}, type={self.type!r})"


class RuleConfig:
    """单条自检规则配置"""
    def __init__(self, raw: Dict[str, Any]):
        self.name: str = raw["name"]
        self.description: str = raw.get("description", "")
        self.rule_type: str = raw.get("type", "threshold")  # threshold | script
        self.metric: Optional[str] = raw.get("metric")
        self.field: Optional[str] = raw.get("field")
        self.operator: Optional[str] = raw.get("operator", ">")
        self.threshold: Optional[float] = raw.get("threshold")
        self.severity: str = raw.get("severity", "warning")
        self.enabled: bool = raw.get("enabled", True)
        self.command: Optional[str] = raw.get("command")
        self.expected: Optional[str] = raw.get("expected")

    def __repr__(self):
        return f"RuleConfig(name={self.name!r}, severity={self.severity!r})"


class Config:
    """顶层配置对象"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._raw: Dict[str, Any] = {}
        self.hosts: List[HostConfig] = []
        self.metrics: Dict[str, bool] = {}
        self.schedule: Dict[str, Any] = {}
        self.storage: Dict[str, Any] = {}
        self.rules: List[RuleConfig] = []
        self.notify: Dict[str, Any] = {}
        self.web: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """加载并解析配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._raw = yaml.safe_load(f) or {}

        # 解析 hosts
        for h in self._raw.get("hosts", []):
            self.hosts.append(HostConfig(h))

        # 解析采集指标
        self.metrics = self._raw.get("collect", {}).get("metrics", {})

        # 解析调度
        self.schedule = self._raw.get("schedule", {})

        # 解析存储
        self.storage = self._raw.get("storage", {})

        # 解析规则
        for r in self._raw.get("rules", []):
            self.rules.append(RuleConfig(r))

        # 解析通知
        self.notify = self._raw.get("notify", {})

        # 解析 Web 面板
        self.web = self._raw.get("web", {})

    @property
    def enabled_metrics(self) -> List[str]:
        """返回已启用的指标名称列表"""
        return [k for k, v in self.metrics.items() if v]

    @property
    def enabled_rules(self) -> List[RuleConfig]:
        """返回已启用的规则列表"""
        return [r for r in self.rules if r.enabled]

    @property
    def remote_hosts(self) -> List[HostConfig]:
        """返回远程主机列表"""
        return [h for h in self.hosts if h.type == "remote" and h.host]

    @property
    def local_hosts(self) -> List[HostConfig]:
        """返回本地主机列表"""
        return [h for h in self.hosts if h.type == "local"]

    @property
    def interval_seconds(self) -> int:
        """采集间隔（秒）"""
        return self.schedule.get("interval", 300)

    @property
    def db_path(self) -> Path:
        """数据库文件路径"""
        return Path(self.storage.get("path", "./data/monitor.db"))

    def __repr__(self) -> str:
        return (
            f"Config(hosts={len(self.hosts)}, metrics={self.enabled_metrics}, "
            f"rules={len(self.enabled_rules)}, interval={self.interval_seconds}s)"
        )


# 模块级单例（惰性加载）
_config: Optional[Config] = None


def load_config(config_path: Optional[Path] = None) -> Config:
    """加载配置（模块级缓存）"""
    global _config
    if _config is None or config_path is not None:
        _config = Config(config_path)
    return _config


def reload_config(config_path: Optional[Path] = None) -> Config:
    """强制重新加载配置"""
    global _config
    _config = None
    return load_config(config_path)
