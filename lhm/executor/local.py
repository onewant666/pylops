"""本地执行器 — 通过 subprocess 在本地运行命令"""

import subprocess
from typing import Optional


class LocalExecutor:
    """本地命令执行器"""

    @staticmethod
    def run(command: str, timeout: int = 30) -> dict:
        """
        执行 shell 命令并返回结果

        Returns:
            {
                "ok": bool,
                "stdout": str,
                "stderr": str,
                "returncode": int,
            }
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "ok": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"命令超时 ({timeout}s): {command}",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "ok": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }
