"""终端彩色报告输出（基于 rich）"""

from typing import Dict, List

from rich.console import Console
from rich.markup import escape as rich_escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..checker.engine import CheckResult
from ..collector.base import CollectorResult


class ConsoleReporter:
    """终端彩色输出报告"""

    def __init__(self):
        self.console = Console()

    # ---------- 采集结果 ----------

    def print_collect_results(self, results: List[CollectorResult]) -> None:
        """打印采集结果摘要"""
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold white]📊 主机状态采集结果[/bold white]",
                border_style="blue",
            )
        )

        # 按主机分组
        by_host: Dict[str, List[CollectorResult]] = {}
        for r in results:
            by_host.setdefault(r.host, []).append(r)

        for host, items in by_host.items():
            table = Table(
                title=f"🖥  {host}",
                title_style="bold cyan",
                box=None,
            )
            table.add_column("指标", style="dim", width=12)
            table.add_column("状态", width=8)
            table.add_column("摘要")

            for item in items:
                status = "[green]✓[/green]" if item.success else "[red]✗[/red]"
                if item.warnings:
                    status += " [yellow]⚠[/yellow]"
                summary = self._summarize_metric(item)
                table.add_row(item.metric, status, summary)
                for w in item.warnings:
                    table.add_row("", "[dim]  ⚠[/dim]", f"[dim]{rich_escape(w)}[/dim]")

            self.console.print(table)

    def _summarize_metric(self, result: CollectorResult) -> str:
        """根据指标类型生成一行摘要"""
        metric = result.metric
        d = result.data

        if not result.success:
            return f"[red]采集失败: {rich_escape(result.error)}[/red]"

        if metric == "cpu":
            return (
                f"使用率: [bold]{d.get('percent', '?')}%[/bold]  "
                f"负载: {d.get('load_1m','?')}/{d.get('load_5m','?')}/"
                f"{d.get('load_15m','?')}  "
                f"核心: {d.get('cpu_count_logical','?')}"
            )
        elif metric == "memory":
            return (
                f"使用率: [bold]{d.get('percent','?')}%[/bold]  "
                f"已用: {d.get('used_gb','?')}GB/"
                f"总: {d.get('total_gb','?')}GB  "
                f"Swap: {d.get('swap_percent','?')}%"
            )
        elif metric == "disk":
            worst = d.get("worst_partition")
            if worst:
                return (
                    f"分区数: {d.get('partition_count','?')}  "
                    f"最差: [bold]{rich_escape(str(worst['mountpoint']))}[/bold] "
                    f"{worst['percent']}%"
                )
            return f"分区数: {d.get('partition_count','?')}"
        elif metric == "network":
            return (
                f"发送: [bold]{d.get('total_sent_mb','?')}MB[/bold]  "
                f"接收: {d.get('total_recv_mb','?')}MB  "
                f"连接数: {d.get('connections',{}).get('total','?')}"
            )
        elif metric == "process":
            return (
                f"进程总数: {d.get('total_count','?')}  "
                f"Top{d.get('top_n','?')}: "
                + ", ".join(
                    rich_escape(p["name"]) for p in d.get("top_processes", [])[:5]
                )
            )
        elif metric == "system":
            return (
                f"运行时长: {d.get('uptime','?')}  "
                f"负载比: [bold]{d.get('load_ratio','?')}[/bold]  "
                f"登录用户: {d.get('user_count','?')}"
            )
        else:
            return str(d)

    # ---------- 自检结果 ----------

    def print_check_results(self, results: List[CheckResult]) -> None:
        """打印自检结果"""
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold white]🔍 自检结果[/bold white]",
                border_style="yellow",
            )
        )

        # 统计
        total = len(results)
        passed = sum(1 for r in results if r.passed and r.data_available)
        failed = sum(1 for r in results if not r.passed)
        unavailable = sum(1 for r in results if not r.data_available)

        summary_color = "green" if failed == 0 else "red"
        parts = [f"共 [bold]{total}[/bold] 项检查"]
        if passed:
            parts.append(f"[green]✓ {passed} 通过[/green]")
        if failed:
            parts.append(f"[{summary_color}]✗ {failed} 未通过[/{summary_color}]")
        if unavailable:
            parts.append(f"[dim]~ {unavailable} 无数据[/dim]")
        self.console.print("  " + "  ".join(parts))
        self.console.print()

        table = Table(box=None, show_header=True, header_style="bold")
        table.add_column("主机", style="cyan", width=14)
        table.add_column("规则", width=14)
        table.add_column("严重级别", width=10)
        table.add_column("结果", width=10)
        table.add_column("详情")

        for r in results:
            sev_color = {
                "info": "dim",
                "warning": "yellow",
                "critical": "red",
            }.get(r.severity, "")

            if not r.data_available:
                result_str = "[dim]~ 无数据[/dim]"
            elif r.passed:
                result_str = "[green]✓ 通过[/green]"
            else:
                result_str = "[red]✗ 未通过[/red]"
            detail_str = self._format_check_detail(r)

            table.add_row(
                r.host,
                r.rule_name,
                f"[{sev_color}]{r.severity}[/{sev_color}]",
                result_str,
                detail_str,
            )

        self.console.print(table)

    def _format_check_detail(self, result: CheckResult) -> str:
        """格式化自检详情"""
        d = result.detail
        if "actual" in d:
            return (
                f"{d.get('metric')}.{d.get('field')} = "
                f"[bold]{rich_escape(str(d['actual']))}[/bold] "
                f"{d.get('operator')} {d.get('threshold')}"
            )
        if "error" in d:
            return rich_escape(str(d["error"]))
        if "command" in d:
            return f"命令: {rich_escape(d.get('command', ''))}"
        return rich_escape(str(d))
