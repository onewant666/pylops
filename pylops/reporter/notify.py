"""通知模块 — 定时摘要推送（钉钉 / 飞书 / 企业微信）"""

import json
from typing import Any, Dict, List

import requests

from ..checker.engine import CheckResult


class Notifier:
    """多渠道通知发送器（定时摘要模式）"""

    def __init__(self, notify_config: Dict[str, Any]):
        self.config = notify_config
        self.enabled = notify_config.get("enabled", False)

    def send_summary(self, check_results: List[CheckResult]) -> Dict[str, bool]:
        """
        定时发送摘要报告（无论是否有告警都发）

        Returns:
            {"dingtalk": True/False, ...}
        """
        if not self.enabled:
            return {}

        text = self._build_summary(check_results)
        results = {}

        dt = self.config.get("dingtalk", {})
        if dt.get("webhook"):
            results["dingtalk"] = self._send_dingtalk(dt["webhook"], text)

        fs = self.config.get("feishu", {})
        if fs.get("webhook"):
            results["feishu"] = self._send_feishu(fs["webhook"], text)

        wx = self.config.get("wecom", {})
        if wx.get("webhook"):
            results["wecom"] = self._send_wecom(wx["webhook"], text)

        return results

    def _build_summary(self, results: List[CheckResult]) -> str:
        """构建定时摘要消息"""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        fail_list = [r for r in results if not r.passed]

        lines = [
            "📊 Linux 主机状态定时报告",
            f"检查项: {total} | 通过: {passed} | 未通过: {failed}",
            "",
        ]

        if fail_list:
            lines.append(f"⚠️ {len(fail_list)} 项未通过:")
            for r in fail_list:
                emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(
                    r.severity, "❓"
                )
                lines.append(
                    f"  {emoji} [{r.severity}] {r.host} — {r.description or r.rule_name}"
                )
                if "actual" in r.detail:
                    lines.append(
                        f"    实际: {r.detail['actual']} "
                        f"{r.detail.get('operator', '>')} "
                        f"{r.detail.get('threshold', '?')}"
                    )
        else:
            lines.append("✅ 所有检查项均通过")

        return "\n".join(lines)

    # -------- 各渠道发送 --------

    @staticmethod
    def _send_dingtalk(webhook: str, text: str) -> bool:
        try:
            resp = requests.post(
                webhook,
                json={"msgtype": "text", "text": {"content": text}},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _send_feishu(webhook: str, text: str) -> bool:
        try:
            resp = requests.post(
                webhook,
                json={
                    "msg_type": "text",
                    "content": json.dumps({"text": text}),
                },
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _send_wecom(webhook: str, text: str) -> bool:
        try:
            resp = requests.post(
                webhook,
                json={"msgtype": "text", "text": {"content": text}},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
