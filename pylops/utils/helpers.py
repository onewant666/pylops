"""工具函数"""

import platform
import socket
import time
from datetime import datetime
from typing import Any, Dict


def now_iso() -> str:
    """返回当前时间 ISO 格式字符串"""
    return datetime.now().isoformat(timespec="seconds")


def now_ts() -> float:
    """返回当前 Unix 时间戳"""
    return time.time()


def get_local_ip() -> str:
    """获取本机 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def safe_call(func, default=None, *args, **kwargs):
    """安全调用函数，出错返回默认值"""
    try:
        return func(*args, **kwargs)
    except Exception:
        return default


def compare(a, op: str, b) -> bool:
    """根据运算符比较两个值"""
    ops = {
        ">": lambda x, y: x > y,
        ">=": lambda x, y: x >= y,
        "<": lambda x, y: x < y,
        "<=": lambda x, y: x <= y,
        "==": lambda x, y: x == y,
        "!=": lambda x, y: x != y,
    }
    if op not in ops:
        raise ValueError(f"不支持的运算符: {op}")
    return ops[op](a, b)


def dict_deep_get(d: Dict[str, Any], key_path: str, default=None):
    """从嵌套字典中按路径取值，如 'parent.child.key'"""
    keys = key_path.split(".")
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return default
        if d is None:
            return default
    return d


# ===================== 平台检测 =====================


def get_platform() -> str:
    """返回当前操作系统名称，如 'Linux' / 'Windows' / 'Darwin'"""
    return platform.system()


def is_linux() -> bool:
    """是否为 Linux 系统"""
    return get_platform() == "Linux"


def is_windows() -> bool:
    """是否为 Windows 系统"""
    return get_platform() == "Windows"
