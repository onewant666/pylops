"""定时调度器 — 基于 APScheduler"""

import logging
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config import Config

logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self, config: Config):
        self.config = config
        self._scheduler = BackgroundScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                "coalesce": True,       # 合并错过的任务
                "max_instances": 1,     # 同一任务最多同时运行 1 个实例
                "misfire_grace_time": 60,  # 错过 60 秒内仍然执行
            },
        )

    def add_job(
        self,
        func: Callable,
        job_id: str = "collect_and_check",
        **kwargs,
    ) -> None:
        """
        添加定时任务

        优先使用 cron 表达式，否则使用 interval。
        """
        # 清理旧任务
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        cron_expr = self.config.schedule.get("cron")
        if cron_expr:
            # cron 表达式格式: "minute hour day month day_of_week"
            parts = cron_expr.strip().split()
            if len(parts) == 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                    timezone="Asia/Shanghai",
                )
                self._scheduler.add_job(
                    func, trigger, id=job_id, **kwargs
                )
                logger.info(
                    f"已添加定时任务 [{job_id}]: cron={cron_expr}"
                )
                return

        # 默认: 使用 interval
        seconds = self.config.interval_seconds
        trigger = IntervalTrigger(seconds=seconds)
        self._scheduler.add_job(
            func, trigger, id=job_id, **kwargs
        )
        logger.info(
            f"已添加定时任务 [{job_id}]: interval={seconds}s"
        )

    def start(self) -> None:
        """启动调度器"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("调度器已启动")

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("调度器已关闭")

    def list_jobs(self) -> list:
        """列出所有任务"""
        return self._scheduler.get_jobs()

    @property
    def running(self) -> bool:
        return self._scheduler.running
