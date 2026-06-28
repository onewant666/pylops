"""执行引擎 — 抽象本地执行和远程 SSH 执行"""
from .local import LocalExecutor


def __getattr__(name):
    """延迟导入 SSHExecutor，避免未安装 paramiko 时崩溃"""
    if name == "SSHExecutor":
        from .remote import SSHExecutor
        return SSHExecutor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["LocalExecutor", "SSHExecutor"]
