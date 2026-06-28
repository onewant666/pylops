"""执行引擎 — 抽象本地执行和远程 SSH 执行"""
from .local import LocalExecutor
from .remote import SSHExecutor

__all__ = ["LocalExecutor", "SSHExecutor"]
