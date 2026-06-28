# 🐧 PyLOps — Linux Host Monitor

[![CI](https://github.com/onewant666/pylops/actions/workflows/ci.yml/badge.svg)](https://github.com/onewant666/pylops/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**轻量级 Linux 主机状态采集与定时自检工具** — 面向运维测试场景，采集 CPU/内存/磁盘/网络/进程等核心指标，支持阈值告警、定时报告推送和 Web 仪表盘。

> 适用场景：测试环境监控、个人服务器巡检、小型运维自动化。

---

## ✨ 特性

- 📊 **6 项核心指标** — CPU、内存、磁盘、网络、进程、系统负载
- 🔍 **规则引擎** — 阈值比较 + 自定义脚本检查，三级告警 (info/warning/critical)
- ⏰ **定时调度** — APScheduler 驱动，支持 interval / cron，采集与自检自动运行
- 📈 **Web 仪表盘** — Flask + Chart.js，暗色主题，指标卡片 + 24h 趋势图
- 📨 **多渠道通知** — 定时摘要推送，支持钉钉 / 飞书 / 企业微信 Webhook
- 💾 **SQLite 持久化** — 轻量单文件数据库，零配置，数据自动清理
- ⚡ **纯 Python** — psutil 本地采集，无 Agent 依赖
- 🎨 **Rich 终端输出** — 彩色表格、Panel、进度条

---

## 📸 截图

<!-- TODO: 替换为实际截图 -->
```
Web 仪表盘 (暗色主题)
┌──────────────────────────────────────────────────────┐
│  🐧 PyLOps 主机状态                         ● 正常     │
├──────────┬──────────┬──────────┬─────────────────────┤
│ CPU      │ 内存     │ 磁盘     │ 负载比    运行时长   │
│  23.5%   │  67.2%   │   45%    │  0.8      3d 5h     │
│ ██░░░░░  │ ██████░░ │ ████░░░░ │                     │
├──────────┴──────────┴──────────┴─────────────────────┤
│  📈 CPU 趋势 (24h)          📈 内存趋势 (24h)        │
│  [折线图]                  [折线图]                  │
│  📈 负载趋势                📈 磁盘趋势               │
├──────────────────────────────────────────────────────┤
│  🔍 自检结果                                        │
│  时间    │ 规则      │ 级别    │ 结果   │ 详情       │
│  14:30   │ cpu_high  │ warning │ ✓ 通过 │ cpu=23<90  │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求

- **Python** ≥ 3.8
- **操作系统** Linux（采集层使用 psutil，Windows/macOS 仅部分指标可用）

### 安装

```bash
# 克隆仓库
git clone https://github.com/onewant666/pylops.git
cd pylops

# 安装
pip install -e .

# 初始化（生成配置 + 建库）
pylops init
```

### 使用

```bash
# 执行一次采集 + 自检
pylops run

# 启动 Web 仪表盘（后台自动采集）
pylops web

# 启动守护进程（定时采集 + 定时通知）
pylops daemon

# 导出 HTML 报告
pylops report -f html -o report.html

# 查看更多命令
pylops --help
```

---

## 🏗 架构

```
┌──────────────────────────────────────────────────┐
│                   CLI 层                          │
│    run │ check │ daemon │ web │ report │ init     │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│               MonitorEngine                      │
│       collect_all() → check_all()                │
└──┬──────────┬───────────┬───────────┬───────────┘
   │          │           │           │
┌──▼──┐  ┌───▼───┐  ┌───▼───┐  ┌───▼──────┐
│Coll-│  │Checker│  │Storage│  │ Reporter │
│ector│  │Engine │  │(SQLite│  │(终端/HTML│
│(6个)│  │(规则) │  │)      │  │/通知)    │
└─────┘  └───────┘  └───────┘  └──────────┘
```

### 模块说明

| 模块 | 职责 | 核心类 |
|------|------|--------|
| `collector/` | 6 个指标采集器，基于 psutil | `CPUCollector`, `MemoryCollector`, … |
| `checker/` | 规则引擎：阈值比较 + 脚本执行 | `CheckEngine`, `CheckResult` |
| `storage/` | SQLite 持久化，指标 + 自检两张表 | `Database` |
| `scheduler/` | APScheduler 封装，interval / cron | `TaskScheduler` |
| `reporter/` | 终端彩色输出、HTML 报告、多渠道通知 | `ConsoleReporter`, `HTMLReporter`, `Notifier` |
| `web/` | Flask 仪表盘 + REST API | `create_app()` |
| `executor/` | 执行抽象层（本地 subprocess / 远程 SSH） | `LocalExecutor`, `SSHExecutor` |

---

## ⚙️ 配置

所有行为由 `config.yaml` 驱动：

```yaml
# 采集指标开关
collect:
  metrics:
    cpu: true
    memory: true
    disk: true
    network: true
    process: true
    system: true

# 采集间隔
schedule:
  interval: 300          # 5 分钟

# 自检规则（阈值 + 脚本，支持三级告警）
rules:
  - name: cpu_high
    description: CPU 使用率过高
    metric: cpu
    field: percent
    operator: ">"
    threshold: 90
    severity: warning

  - name: nginx_alive     # 自定义脚本检查
    type: script
    command: systemctl is-active nginx
    expected: "active"
    severity: critical

# 定时通知
notify:
  enabled: false
  interval: 3600          # 每小时发一次摘要
  dingtalk:
    webhook: "https://oapi.dingtalk.com/robot/send?access_token=xxx"

# Web 面板
web:
  host: 0.0.0.0
  port: 5000
  refresh_interval: 30
```

---

## 🧪 测试

```bash
# 运行测试
pip install -e ".[dev]"
pytest -v

# 覆盖率
pytest --cov=pylops --cov-report=html
```

---

## 📁 项目结构

```
pylops/
├── cli.py              # Click CLI 入口（7 个子命令）
├── config.py           # YAML 配置加载
├── engine.py           # 核心编排（采集→检查→存储）
├── collector/          # 采集层（6 个采集器）
│   ├── base.py         #   基类 CollectorResult
│   ├── cpu.py          #   CPU / 频率 / 负载
│   ├── memory.py       #   内存 / Swap
│   ├── disk.py         #   磁盘分区 / IO
│   ├── network.py      #   网络接口 / 连接
│   ├── process.py      #   Top N 进程
│   └── system.py       #   运行时长 / 用户
├── checker/            # 自检规则引擎
│   └── engine.py       #   阈值 + 脚本规则
├── storage/            # 数据持久化
│   └── database.py     #   SQLite CRUD
├── scheduler/          # 定时调度
│   └── scheduler.py    #   APScheduler
├── reporter/           # 报告输出
│   ├── console.py      #   Rich 终端
│   ├── html.py         #   Jinja2 HTML
│   └── notify.py       #   钉钉/飞书/企微
├── web/                # Web 仪表盘
│   ├── app.py          #   Flask 应用
│   └── templates/
│       └── dashboard.html  # 暗色主题仪表盘
└── utils/              # 工具
    └── helpers.py
```

---

## 🔧 技术栈

| 组件 | 技术选型 |
|------|----------|
| CLI | Click |
| 系统采集 | psutil |
| 定时调度 | APScheduler |
| 数据存储 | SQLite (sqlite3) |
| 终端美化 | Rich |
| Web 框架 | Flask |
| 前端图表 | Chart.js (CDN) |
| HTML 模板 | Jinja2 |
| 配置管理 | PyYAML |
| 测试 | pytest + pytest-cov |
| CI/CD | GitHub Actions |
| 包管理 | pyproject.toml (PEP 621) |

---

## 📝 License

MIT © 2026
