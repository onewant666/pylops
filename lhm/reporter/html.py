"""HTML 报告生成器 — 基于 Jinja2 模板"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Template

from ..checker.engine import CheckResult
from ..collector.base import CollectorResult

# 内联 HTML 模板
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Linux 主机状态报告 — {{ report_time }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, 'Microsoft YaHei', sans-serif;
               background: #f5f5f5; color: #333; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #1a1a2e; margin-bottom: 20px; }
        h2 { color: #16213e; margin: 20px 0 10px; padding-bottom: 5px;
             border-bottom: 2px solid #0f3462; }
        .card { background: white; border-radius: 8px; padding: 16px;
                margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .host-header { font-weight: bold; font-size: 1.1em;
                        color: #0f3462; margin-bottom: 10px; }
        .metric-grid { display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                        gap: 10px; }
        .metric-item { background: #f8f9fa; border-radius: 6px; padding: 12px;
                        border-left: 3px solid #0f3462; }
        .metric-item.failed { border-left-color: #e74c3c; }
        .metric-name { font-size: 0.85em; color: #666; text-transform: uppercase;
                       letter-spacing: 0.5px; }
        .metric-value { font-size: 1.1em; font-weight: bold; color: #333; }
        .check-pass { color: #27ae60; }
        .check-fail { color: #e74c3c; }
        .severity-info { color: #7f8c8d; }
        .severity-warning { color: #f39c12; }
        .severity-critical { color: #e74c3c; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; color: #555; }
        .footer { margin-top: 30px; text-align: center;
                   color: #999; font-size: 0.85em; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
                 font-size: 0.8em; }
        .badge-pass { background: #d4edda; color: #155724; }
        .badge-fail { background: #f8d7da; color: #721c24; }
        .summary-box { display: flex; gap: 16px; margin-bottom: 16px; }
        .summary-item { flex: 1; text-align: center; padding: 16px;
                        background: white; border-radius: 8px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .summary-num { font-size: 2em; font-weight: bold; }
        .summary-label { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
<div class="container">
    <h1>🐧 Linux 主机状态采集与自检报告</h1>
    <p style="color: #666;">生成时间: {{ report_time }}</p>

    <!-- 自检摘要 -->
    <h2>📊 自检摘要</h2>
    <div class="summary-box">
        <div class="summary-item">
            <div class="summary-num">{{ checks_total }}</div>
            <div class="summary-label">总检查项</div>
        </div>
        <div class="summary-item">
            <div class="summary-num" style="color: #27ae60;">{{ checks_passed }}</div>
            <div class="summary-label">通过</div>
        </div>
        <div class="summary-item">
            <div class="summary-num" style="color: #e74c3c;">{{ checks_failed }}</div>
            <div class="summary-label">未通过</div>
        </div>
    </div>

    <!-- 采集结果 -->
    <h2>📡 采集指标</h2>
    {% for host, items in groups.items() %}
    <div class="card">
        <div class="host-header">🖥 {{ host }}</div>
        <div class="metric-grid">
            {% for item in items %}
            <div class="metric-item {% if not item.success %}failed{% endif %}">
                <div class="metric-name">{{ item.metric }}</div>
                <div class="metric-value">{{ summarize(item) }}</div>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endfor %}

    <!-- 自检详情 -->
    <h2>🔍 自检详情</h2>
    <div class="card">
        <table>
            <thead>
                <tr>
                    <th>主机</th>
                    <th>规则</th>
                    <th>级别</th>
                    <th>结果</th>
                    <th>详情</th>
                </tr>
            </thead>
            <tbody>
                {% for r in checks %}
                <tr>
                    <td>{{ r.host }}</td>
                    <td>{{ r.description or r.rule_name }}</td>
                    <td class="severity-{{ r.severity }}">{{ r.severity }}</td>
                    <td>
                        {% if r.passed %}
                        <span class="badge badge-pass">✓ 通过</span>
                        {% else %}
                        <span class="badge badge-fail">✗ 未通过</span>
                        {% endif %}
                    </td>
                    <td>{{ format_check_detail(r) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="footer">
        LHM — Linux Host Monitor v0.1.0
    </div>
</div>
</body>
</html>"""


class HTMLReporter:
    """HTML 报告生成器"""

    def __init__(self):
        self.template = Template(HTML_TEMPLATE)

    def generate(
        self,
        collect_results: List[CollectorResult],
        check_results: List[CheckResult],
        output_path: Path,
    ) -> Path:
        """生成 HTML 报告文件，返回文件路径"""
        by_host: Dict[str, list] = {}
        for r in collect_results:
            by_host.setdefault(r.host, []).append(r)

        html = self.template.render(
            report_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            groups=by_host,
            checks=check_results,
            checks_total=len(check_results),
            checks_passed=sum(1 for r in check_results if r.passed),
            checks_failed=sum(1 for r in check_results if not r.passed),
            summarize=self._summarize_for_html,
            format_check_detail=self._format_check_detail,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        return output_path

    @staticmethod
    def _summarize_for_html(result: CollectorResult) -> str:
        """HTML 版指标摘要"""
        d = result.data
        if not result.success:
            return f"❌ 采集失败: {result.error}"

        metric = result.metric
        if metric == "cpu":
            return f"CPU: {d.get('percent','?')}% | 负载: {d.get('load_1m','?')}"
        elif metric == "memory":
            return f"内存: {d.get('percent','?')}% ({d.get('used_gb','?')}/{d.get('total_gb','?')} GB)"
        elif metric == "disk":
            return f"磁盘最差: {d.get('worst_percent','?')}%"
        elif metric == "network":
            return f"网络: ↑{d.get('total_sent_mb','?')}MB ↓{d.get('total_recv_mb','?')}MB"
        elif metric == "process":
            return f"进程: {d.get('total_count','?')} 个"
        elif metric == "system":
            return f"运行: {d.get('uptime','?')} | 负载比: {d.get('load_ratio','?')}"
        return str(d)

    @staticmethod
    def _format_check_detail(result: CheckResult) -> str:
        d = result.detail
        if "actual" in d:
            return f"{d.get('metric')}.{d.get('field')} = {d['actual']} {d.get('operator')} {d.get('threshold')}"
        if "command" in d:
            return f"命令: {d.get('command')}"
        return str(d)
