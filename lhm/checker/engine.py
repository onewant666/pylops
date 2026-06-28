"""自检规则引擎 — 根据配置的规则对采集数据进行检查"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from ..config import Config, RuleConfig
from ..utils.helpers import compare, dict_deep_get, now_iso


@dataclass
class CheckResult:
    """单条规则的检查结果"""
    host: str
    rule_name: str
    description: str
    severity: str          # info / warning / critical
    passed: bool
    detail: Dict[str, Any] = None

    def __post_init__(self):
        if self.detail is None:
            self.detail = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CheckEngine:
    """规则引擎：加载规则，对采集数据执行检查"""

    def __init__(self, config: Config):
        self.config = config
        self.rules = config.enabled_rules

    def check(
        self, host: str, metrics_data: Dict[str, Any]
    ) -> List[CheckResult]:
        """
        对某台主机的所有采集数据执行全部已启用规则

        Args:
            host: 主机名
            metrics_data: {"cpu": {...}, "memory": {...}, ...}

        Returns:
            CheckResult 列表
        """
        results: List[CheckResult] = []
        for rule in self.rules:
            result = self._evaluate_rule(host, rule, metrics_data)
            results.append(result)
        return results

    def _evaluate_rule(
        self, host: str, rule: RuleConfig, data: Dict[str, Any]
    ) -> CheckResult:
        """评估单条规则"""
        # 阈值型规则
        if rule.rule_type == "threshold":
            return self._check_threshold(host, rule, data)
        # 脚本型规则
        elif rule.rule_type == "script":
            return self._check_script(host, rule)
        else:
            return CheckResult(
                host=host,
                rule_name=rule.name,
                description=rule.description,
                severity=rule.severity,
                passed=True,
                detail={"error": f"未知规则类型: {rule.rule_type}"},
            )

    def _check_threshold(
        self, host: str, rule: RuleConfig, data: Dict[str, Any]
    ) -> CheckResult:
        """评估阈值规则"""
        # 获取对应指标的最新数据
        metric_data = data.get(rule.metric)
        if metric_data is None:
            return CheckResult(
                host=host,
                rule_name=rule.name,
                description=rule.description,
                severity=rule.severity,
                passed=True,  # 无数据视为通过
                detail={"error": f"指标 {rule.metric} 没有采集数据"},
            )

        # 从嵌套数据中取值
        actual = dict_deep_get(metric_data, rule.field)
        if actual is None:
            return CheckResult(
                host=host,
                rule_name=rule.name,
                description=rule.description,
                severity=rule.severity,
                passed=True,  # 未知值视为通过
                detail={
                    "error": f"字段 {rule.field} 在指标 {rule.metric} 中不存在"
                },
            )

        # 执行比较
        passed = not compare(actual, rule.operator, rule.threshold)

        return CheckResult(
            host=host,
            rule_name=rule.name,
            description=rule.description,
            severity=rule.severity,
            passed=passed,
            detail={
                "metric": rule.metric,
                "field": rule.field,
                "actual": actual,
                "operator": rule.operator,
                "threshold": rule.threshold,
            },
        )

    def _check_script(self, host: str, rule: RuleConfig) -> CheckResult:
        """评估自定义脚本规则"""
        from ..executor.local import LocalExecutor

        result = LocalExecutor.run(rule.command)
        passed = rule.expected is None or rule.expected in result["stdout"]

        return CheckResult(
            host=host,
            rule_name=rule.name,
            description=rule.description,
            severity=rule.severity,
            passed=passed,
            detail={
                "command": rule.command,
                "expected": rule.expected,
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "returncode": result["returncode"],
            },
        )
