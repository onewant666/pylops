"""CLI 命令行入口 — 基于 Click"""

import logging
import sys
import time
from pathlib import Path

# Windows 终端 UTF-8 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click

from .config import Config, load_config
from .engine import MonitorEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("lhm")


@click.group()
@click.option(
    "-c", "--config",
    default=None,
    help="配置文件路径（默认: config.yaml）",
    type=click.Path(exists=True),
)
@click.version_option(version="0.1.0", prog_name="lhm")
@click.pass_context
def cli(ctx, config):
    """🐧 LHM — Linux 主机状态采集与定时自检工具"""
    ctx.ensure_object(dict)
    config_path = Path(config) if config else None
    try:
        cfg = load_config(config_path)
    except FileNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        click.echo("提示: 运行 'lhm init' 生成默认配置文件", err=True)
        sys.exit(1)
    ctx.obj["config"] = cfg


# ===================== init =====================

@cli.command()
@click.option(
    "-o", "--output",
    default=None,
    help="配置文件输出路径（默认: ./config.yaml）",
)
def init(output):
    """初始化项目：生成默认配置文件和数据库"""
    import shutil

    default_config = Path(__file__).parent.parent / "config.yaml"
    dest = Path(output) if output else Path("config.yaml")

    if dest.exists():
        click.confirm(f"文件已存在: {dest}\n是否覆盖？", abort=True)

    shutil.copy(default_config, dest)
    click.echo(f"✓ 配置文件已生成: {dest}")

    cfg = Config(dest)
    engine = MonitorEngine(cfg)
    engine.init()
    click.echo(f"✓ 数据库已初始化: {cfg.db_path}")
    click.echo()
    click.echo("下一步:")
    click.echo("  1. 编辑 config.yaml 调整阈值和通知配置")
    click.echo("  2. lhm run       — 执行首次采集和自检")
    click.echo("  3. lhm daemon    — 启动定时采集守护进程")
    click.echo("  4. lhm web       — 启动 Web 仪表盘")


# ===================== run =====================

@cli.command()
@click.option("--no-check", is_flag=True, help="仅采集，不执行自检")
@click.pass_context
def run(ctx, no_check):
    """执行一次完整的采集 + 自检"""
    cfg = ctx.obj["config"]

    click.echo("🐧 LHM — Linux 主机状态采集与定时自检")
    click.echo(f"主机: {len(cfg.hosts)} 台 | "
               f"指标: {len(cfg.enabled_metrics)} 项 | "
               f"规则: {len(cfg.enabled_rules)} 条")
    click.echo()

    engine = MonitorEngine(cfg)
    engine.init()

    # 采集
    click.echo("⏳ 正在采集主机状态...")
    collect_results = engine.collect_all()

    from .reporter.console import ConsoleReporter
    reporter = ConsoleReporter()
    reporter.print_collect_results(collect_results)

    # 自检
    check_results = []
    if not no_check:
        click.echo("⏳ 正在执行自检...")
        check_results = engine.check_all()
        reporter.print_check_results(check_results)

    # 统计
    success = sum(1 for r in collect_results if r.success)
    click.echo()
    click.echo(
        f"📋 采集: {success}/{len(collect_results)} 成功  |  "
        f"自检: {sum(1 for r in check_results if r.passed)}"
        f"/{len(check_results)} 通过"
    )

    engine.close()


# ===================== check =====================

@cli.command()
@click.pass_context
def check(ctx):
    """仅执行自检（基于最近一次采集数据）"""
    cfg = ctx.obj["config"]
    engine = MonitorEngine(cfg)

    click.echo("⏳ 正在执行自检...")
    check_results = engine.check_all()

    from .reporter.console import ConsoleReporter
    reporter = ConsoleReporter()
    reporter.print_check_results(check_results)

    engine.close()


# ===================== report =====================

@cli.command()
@click.option(
    "-f", "--format", "fmt",
    type=click.Choice(["console", "html"]),
    default="console",
    help="报告格式",
)
@click.option(
    "-o", "--output",
    default="report.html",
    help="HTML 报告输出路径",
)
@click.pass_context
def report(ctx, fmt, output):
    """生成报告（采集 + 自检后输出）"""
    cfg = ctx.obj["config"]
    engine = MonitorEngine(cfg)

    collect_results = engine.collect_all()
    check_results = engine.check_all()

    if fmt == "console":
        from .reporter.console import ConsoleReporter
        reporter = ConsoleReporter()
        reporter.print_collect_results(collect_results)
        reporter.print_check_results(check_results)
    elif fmt == "html":
        from .reporter.html import HTMLReporter
        reporter = HTMLReporter()
        out_path = Path(output)
        reporter.generate(collect_results, check_results, out_path)
        click.echo(f"✓ HTML 报告已生成: {out_path.resolve()}")

    engine.close()


# ===================== daemon =====================

@cli.command()
@click.option(
    "-i", "--interval",
    default=None,
    type=int,
    help="采集间隔（秒），覆盖配置文件中的设置",
)
@click.pass_context
def daemon(ctx, interval):
    """启动定时采集守护进程"""
    cfg = ctx.obj["config"]

    if interval is not None:
        cfg.schedule["interval"] = interval

    engine = MonitorEngine(cfg)
    engine.init()

    from .scheduler import TaskScheduler
    scheduler = TaskScheduler(cfg)

    # 通知相关状态
    notify_interval = cfg.notify.get("interval", 3600)
    last_notify_time = 0.0

    click.echo("🐧 LHM 守护进程模式")
    click.echo(f"采集间隔: {cfg.interval_seconds}s")
    click.echo(f"通知间隔: {notify_interval}s")
    click.echo(f"指标: {cfg.enabled_metrics}")
    click.echo(f"规则: {len(cfg.enabled_rules)} 条")
    click.echo(f"数据库: {cfg.db_path}")
    click.echo()
    click.echo("按 Ctrl+C 停止...")
    click.echo()

    def job():
        """每次采集触发"""
        nonlocal last_notify_time

        click.echo(f"\n{'='*50}")
        click.echo(f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')} 执行采集...")
        result = engine.run_once()

        collect_count = len(result["collect"])
        check_count = len(result["checks"])
        failed_checks = [r for r in result["checks"] if not r.passed]

        if failed_checks:
            click.echo(f"⚠️  {len(failed_checks)}/{check_count} 项检查未通过:")
            for r in failed_checks:
                click.echo(f"  [{r.severity.upper()}] {r.host} — {r.description}")
        else:
            click.echo(f"✓ 全部 {check_count} 项检查通过")

        # 定时通知（按 notify_interval 间隔）
        now = time.time()
        if now - last_notify_time >= notify_interval:
            click.echo(f"📨 发送定时摘要通知...")
            notify_results = engine.notifier.send_summary(result["checks"])
            for channel, ok in notify_results.items():
                if ok:
                    click.echo(f"  ✓ {channel}")
            last_notify_time = now

    # 立即执行一次
    job()

    scheduler.add_job(job)
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\n正在停止...")
        scheduler.shutdown()
        engine.cleanup()
        engine.close()
        click.echo("已停止")


# ===================== web =====================

@cli.command()
@click.option(
    "-p", "--port",
    default=None,
    type=int,
    help="Web 面板端口（默认: 5000）",
)
@click.option(
    "--host",
    default=None,
    help="绑定地址（默认: 0.0.0.0）",
)
@click.option(
    "--debug", is_flag=True,
    help="开启 Flask 调试模式",
)
@click.pass_context
def web(ctx, port, host, debug):
    """启动 Web 仪表盘"""
    cfg = ctx.obj["config"]

    # 命令行参数优先于配置文件
    web_host = host or cfg.web.get("host", "0.0.0.0")
    web_port = port or cfg.web.get("port", 5000)
    web_debug = debug or cfg.web.get("debug", False)

    engine = MonitorEngine(cfg)
    engine.init()

    from .web.app import create_app
    app = create_app(cfg, engine.db)

    click.echo("🐧 LHM Web 仪表盘")
    click.echo(f"地址: http://{web_host}:{web_port}")
    click.echo(f"刷新间隔: {cfg.web.get('refresh_interval', 30)}s")
    click.echo()

    # 确保后台采集在运行
    from .scheduler import TaskScheduler
    scheduler = TaskScheduler(cfg)

    def background_job():
        engine.run_once()

    scheduler.add_job(background_job, job_id="web_collect")
    scheduler.start()

    try:
        app.run(host=web_host, port=web_port, debug=web_debug)
    except KeyboardInterrupt:
        click.echo("\n正在停止...")
        scheduler.shutdown()
        engine.close()
        click.echo("已停止")


# ===================== host =====================

@cli.group()
def host():
    """管理目标主机"""


@host.command("list")
@click.pass_context
def host_list(ctx):
    """列出所有配置的主机"""
    cfg = ctx.obj["config"]

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="🖥 目标主机列表")
    table.add_column("名称", style="cyan")
    table.add_column("类型")

    for h in cfg.hosts:
        table.add_row(h.name, h.type)

    console.print(table)


# ===================== 入口 =====================

def main():
    """程序入口"""
    cli(prog_name="lhm")


if __name__ == "__main__":
    main()
