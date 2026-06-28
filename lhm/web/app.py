"""Flask 轻量 Web 仪表盘"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, render_template, jsonify

from ..config import Config
from ..storage.database import Database


def create_app(config: Config, db: Database) -> Flask:
    """创建 Flask 应用"""
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )
    app.config["SECRET_KEY"] = "lhm-dashboard-secret"

    # 把配置和数据库注入 app，方便路由使用
    app.config["LHM_CONFIG"] = config
    app.config["LHM_DB"] = db

    # -------- 注册路由 --------

    @app.route("/")
    def dashboard():
        """主仪表盘"""
        return render_template(
            "dashboard.html",
            refresh_interval=config.web.get("refresh_interval", 30),
        )

    @app.route("/api/overview")
    def api_overview():
        """API: 概览数据 — 各指标最新值 + 自检摘要"""
        hosts = [h.name for h in config.hosts]
        metrics = config.enabled_metrics

        # 所有主机的最新指标
        latest = {}
        for host in hosts:
            latest[host] = {}
            for metric in metrics:
                row = db.get_latest(host, metric)
                if row:
                    data = json.loads(row["data"]) if isinstance(
                        row["data"], str
                    ) else row["data"]
                    latest[host][metric] = {
                        "timestamp": row["timestamp"],
                        "data": data,
                    }
                else:
                    latest[host][metric] = None

        # 最近 24 小时的自检统计
        check_stats = db.get_check_stats(hours=24)

        # 最近的自检失败项
        failed_checks = _get_recent_failed(db, limit=20)

        return jsonify({
            "latest": latest,
            "check_stats": check_stats,
            "failed_checks": failed_checks,
        })

    @app.route("/api/history/<metric>")
    def api_history(metric: str):
        """API: 某指标的历史数据（最近 24 小时）"""
        host = config.hosts[0].name  # 默认取第一台主机
        start = (datetime.now() - timedelta(hours=24)).isoformat(
            timespec="seconds"
        )
        rows = db.query_metrics(
            host=host, metric=metric, start=start, limit=300
        )

        history = []
        for r in reversed(rows):
            data = json.loads(r["data"]) if isinstance(
                r["data"], str
            ) else r["data"]
            history.append({
                "timestamp": r["timestamp"],
                "data": data,
            })

        return jsonify({"host": host, "metric": metric, "history": history})

    @app.route("/api/checks")
    def api_checks():
        """API: 最近的自检结果"""
        host = config.hosts[0].name
        # 直接读数据库
        from ..storage.database import Database
        conn = db._get_conn()
        rows = conn.execute(
            """SELECT * FROM checks
               WHERE host = ?
               ORDER BY timestamp DESC LIMIT 50""",
            (host,),
        ).fetchall()

        checks = []
        for r in rows:
            detail = json.loads(r["detail"]) if isinstance(
                r["detail"], str
            ) else r["detail"]
            checks.append({
                "host": r["host"],
                "rule_name": r["rule_name"],
                "severity": r["severity"],
                "passed": bool(r["passed"]),
                "detail": detail,
                "timestamp": r["timestamp"],
            })

        return jsonify({"checks": checks})

    return app


def _get_recent_failed(db: Database, limit: int = 20) -> List[Dict[str, Any]]:
    """获取最近未通过的自检项"""
    conn = db._get_conn()
    rows = conn.execute(
        """SELECT * FROM checks
           WHERE passed = 0
           ORDER BY timestamp DESC LIMIT ?""",
        (limit,),
    ).fetchall()

    result = []
    for r in rows:
        detail = json.loads(r["detail"]) if isinstance(
            r["detail"], str
        ) else r["detail"]
        result.append({
            "host": r["host"],
            "rule_name": r["rule_name"],
            "severity": r["severity"],
            "detail": detail,
            "timestamp": r["timestamp"],
        })
    return result
