"""SQLite 数据库 — 存储采集数据和自检结果"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..collector.base import CollectorResult


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    host        TEXT    NOT NULL,       -- 主机名
    metric      TEXT    NOT NULL,       -- 指标名: cpu/memory/disk/network/process/system
    timestamp   TEXT    NOT NULL,       -- 采集时间 (ISO 8601)
    success     INTEGER NOT NULL DEFAULT 1,
    data        TEXT    NOT NULL,       -- JSON 数据
    error       TEXT    DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    host        TEXT    NOT NULL,       -- 主机名
    rule_name   TEXT    NOT NULL,       -- 规则名称
    severity    TEXT    NOT NULL,       -- info/warning/critical
    passed      INTEGER NOT NULL,      -- 1=通过, 0=未通过
    detail      TEXT    NOT NULL,       -- 检查详情 (JSON)
    timestamp   TEXT    NOT NULL,       -- 检查时间
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_metrics_host_metric ON metrics(host, metric);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_checks_host ON checks(host);
CREATE INDEX IF NOT EXISTS idx_checks_timestamp ON checks(timestamp);
CREATE INDEX IF NOT EXISTS idx_checks_severity ON checks(severity);
"""


class Database:
    """SQLite 数据库管理类"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("./data/monitor.db")
        self._conn: Optional[sqlite3.Connection] = None

    # -------- 生命周期 --------

    def init(self) -> None:
        """初始化：创建目录、建表"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        conn.executescript(DB_SCHEMA)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path), check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # -------- 指标 写入 --------

    def save_metric(self, result: CollectorResult) -> int:
        """保存一条采集结果，返回行 ID"""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO metrics (host, metric, timestamp, success, data, error)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                result.host,
                result.metric,
                result.timestamp,
                1 if result.success else 0,
                json.dumps(result.data, ensure_ascii=False),
                result.error,
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def save_metrics_batch(self, results: List[CollectorResult]) -> int:
        """批量保存采集结果"""
        conn = self._get_conn()
        count = 0
        for r in results:
            conn.execute(
                """INSERT INTO metrics (host, metric, timestamp, success, data, error)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    r.host,
                    r.metric,
                    r.timestamp,
                    1 if r.success else 0,
                    json.dumps(r.data, ensure_ascii=False),
                    r.error,
                ),
            )
            count += 1
        conn.commit()
        return count

    # -------- 指标 查询 --------

    def get_latest(self, host: str, metric: str) -> Optional[Dict[str, Any]]:
        """获取某主机某指标的最新一条记录"""
        conn = self._get_conn()
        row = conn.execute(
            """SELECT * FROM metrics
               WHERE host=? AND metric=? AND success=1
               ORDER BY timestamp DESC LIMIT 1""",
            (host, metric),
        ).fetchone()
        return dict(row) if row else None

    def query_metrics(
        self,
        host: Optional[str] = None,
        metric: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """条件查询采集记录"""
        conn = self._get_conn()
        sql = "SELECT * FROM metrics WHERE 1=1"
        params: List[Any] = []

        if host:
            sql += " AND host=?"
            params.append(host)
        if metric:
            sql += " AND metric=?"
            params.append(metric)
        if start:
            sql += " AND timestamp >= ?"
            params.append(start)
        if end:
            sql += " AND timestamp <= ?"
            params.append(end)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        return [dict(r) for r in conn.execute(sql, params).fetchall()]

    # -------- 自检结果 --------

    def save_check(
        self,
        host: str,
        rule_name: str,
        severity: str,
        passed: bool,
        detail: Dict[str, Any],
        timestamp: Optional[str] = None,
    ) -> int:
        """保存一条自检结果"""
        conn = self._get_conn()
        ts = timestamp or datetime.now().isoformat(timespec="seconds")
        cursor = conn.execute(
            """INSERT INTO checks (host, rule_name, severity, passed, detail, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (host, rule_name, severity, 1 if passed else 0,
             json.dumps(detail, ensure_ascii=False), ts),
        )
        conn.commit()
        return cursor.lastrowid

    def get_check_stats(
        self, host: Optional[str] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """获取最近 N 小时的自检统计"""
        conn = self._get_conn()
        since = (datetime.now() - timedelta(hours=hours)).isoformat(
            timespec="seconds"
        )

        sql = "SELECT * FROM checks WHERE timestamp >= ?"
        params: List[Any] = [since]
        if host:
            sql += " AND host=?"
            params.append(host)

        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

        total = len(rows)
        passed = sum(1 for r in rows if r["passed"])
        failed = total - passed

        severity_breakdown = {}
        for r in rows:
            sev = r["severity"]
            severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total * 100, 1) if total else 0,
            "severity_breakdown": severity_breakdown,
            "hours": hours,
        }

    # -------- 清理 --------

    def cleanup(self, retention_days: int = 30) -> int:
        """删除超过保留期的数据，返回删除行数"""
        conn = self._get_conn()
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat(
            timespec="seconds"
        )
        cursor = conn.execute(
            "DELETE FROM metrics WHERE timestamp < ?", (cutoff,)
        )
        cursor2 = conn.execute(
            "DELETE FROM checks WHERE timestamp < ?", (cutoff,)
        )
        conn.commit()
        return cursor.rowcount + cursor2.rowcount
