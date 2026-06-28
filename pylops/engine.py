"""核心编排引擎 — 串联采集、自检、存储流程"""

import json
import logging
from typing import Dict, List

from .checker.engine import CheckEngine, CheckResult
from .collector import (
    CPUCollector,
    DiskCollector,
    MemoryCollector,
    NetworkCollector,
    ProcessCollector,
    SystemCollector,
)
from .collector.base import CollectorResult
from .config import Config
from .reporter.notify import Notifier
from .storage.database import Database

logger = logging.getLogger(__name__)


class MonitorEngine:
    """核心引擎：采集 + 自检 + 存储（通知由外部按定时触发）"""

    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.db_path)
        self.checker = CheckEngine(config)
        self.notifier = Notifier(config.notify)

    # ===================== 采集 =====================

    def collect_all(self) -> List[CollectorResult]:
        """
        对所有已配置主机执行全部已启用的指标采集
        （当前聚焦本地主机，使用 psutil 直接采集）
        """
        all_results: List[CollectorResult] = []

        for host_cfg in self.config.hosts:
            results = self._collect_local(host_cfg)
            all_results.extend(results)

        if all_results:
            self.db.save_metrics_batch(all_results)
            logger.info(f"已保存 {len(all_results)} 条采集记录")

        return all_results

    def _collect_local(self, host_cfg) -> List[CollectorResult]:
        """本地采集：直接使用 psutil 采集器"""
        results: List[CollectorResult] = []
        enabled = self.config.enabled_metrics

        collector_map = {
            "cpu": CPUCollector,
            "memory": MemoryCollector,
            "disk": DiskCollector,
            "network": NetworkCollector,
            "process": ProcessCollector,
            "system": SystemCollector,
        }

        for metric in enabled:
            collector_cls = collector_map.get(metric)
            if collector_cls is None:
                logger.warning(f"未知指标 '{metric}'，已跳过")
                continue

            collector = collector_cls(host_cfg)
            result = collector.collect()
            results.append(result)

            if result.success:
                logger.debug(f"[{host_cfg.name}] {metric} 采集成功")
                for w in result.warnings:
                    logger.warning(f"[{host_cfg.name}] {metric}: {w}")
            else:
                logger.warning(
                    f"[{host_cfg.name}] {metric} 采集失败: {result.error}"
                )

        return results

    # ===================== 自检 =====================

    def check_all(self) -> List[CheckResult]:
        """
        基于最新采集数据执行全部自检规则
        （通知不在此处发送，由调度层按间隔触发）
        """
        all_checks: List[CheckResult] = []

        for host_cfg in self.config.hosts:
            # 获取该主机所有指标的最新数据
            metrics_data = {}
            for metric in self.config.enabled_metrics:
                latest = self.db.get_latest(host_cfg.name, metric)
                if latest:
                    data = latest["data"]
                    if isinstance(data, str):
                        data = json.loads(data)
                    metrics_data[metric] = data

            # 执行规则检查
            host_checks = self.checker.check(host_cfg.name, metrics_data)
            all_checks.extend(host_checks)

            # 持久化自检结果
            for check in host_checks:
                self.db.save_check(
                    host=check.host,
                    rule_name=check.rule_name,
                    severity=check.severity,
                    passed=check.passed,
                    detail=check.detail,
                )

        logger.info(f"自检完成: {len(all_checks)} 项")
        return all_checks

    # ===================== 完整流程 =====================

    def run_once(self) -> Dict[str, list]:
        """
        执行一次完整流程：采集 → 自检 → 保存

        Returns:
            {"collect": [...], "checks": [...]}
        """
        logger.info("========== 开始执行采集与自检 ==========")
        collect_results = self.collect_all()
        check_results = self.check_all()
        logger.info("========== 采集与自检完成 ==========")
        return {
            "collect": collect_results,
            "checks": check_results,
        }

    # ===================== 生命周期 =====================

    def init(self) -> None:
        """初始化：创建数据库表"""
        self.db.init()
        logger.info(f"数据库已初始化: {self.config.db_path}")

    def cleanup(self) -> None:
        """清理过期数据"""
        retention = self.config.storage.get("retention_days", 30)
        deleted = self.db.cleanup(retention)
        if deleted:
            logger.info(f"已清理 {deleted} 条过期数据")

    def close(self) -> None:
        self.db.close()
