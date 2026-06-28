"""远程执行器 — 通过 paramiko SSH 在远程主机上运行命令"""

import os
from pathlib import Path
from typing import Optional

import paramiko


class SSHExecutor:
    """SSH 远程命令执行器"""

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_file = Path(key_file).expanduser() if key_file else None
        self.timeout = timeout
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self) -> bool:
        """建立 SSH 连接"""
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": self.timeout,
            }

            if self.key_file and self.key_file.exists():
                key = paramiko.RSAKey.from_private_key_file(str(self.key_file))
                connect_kwargs["pkey"] = key
            elif self.password:
                connect_kwargs["password"] = self.password
            else:
                # 尝试默认 SSH agent
                pass

            self._client.connect(**connect_kwargs)
            return True
        except Exception as e:
            self._client = None
            raise ConnectionError(f"SSH 连接失败 [{self.host}:{self.port}]: {e}")

    def run(self, command: str, timeout: int = 30) -> dict:
        """
        在远程主机上执行命令

        Returns:
            {"ok": bool, "stdout": str, "stderr": str, "returncode": int}
        """
        if not self._client:
            raise RuntimeError("SSH 未连接，请先调用 connect()")

        try:
            _stdin, stdout, stderr = self._client.exec_command(
                command, timeout=timeout
            )
            return {
                "ok": stdout.channel.recv_exit_status() == 0,
                "stdout": stdout.read().decode("utf-8", errors="replace").strip(),
                "stderr": stderr.read().decode("utf-8", errors="replace").strip(),
                "returncode": stdout.channel.recv_exit_status(),
            }
        except Exception as e:
            return {
                "ok": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }

    def close(self) -> None:
        """关闭 SSH 连接"""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
