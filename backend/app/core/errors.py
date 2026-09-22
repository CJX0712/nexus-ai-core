"""统一错误模型（单一职责：只定义错误类型与错误码）。

作者: 晨星
"""
from __future__ import annotations

from typing import Any


class NexusError(Exception):
    """所有业务错误的基类。"""

    code: str = "internal_error"
    http_status: int = 500

    def __init__(self, message: str, detail: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "detail": self.detail,
            }
        }


class BadRequestError(NexusError):
    code = "bad_request"
    http_status = 400


class NotFoundError(NexusError):
    code = "not_found"
    http_status = 404


class ProviderUnavailableError(NexusError):
    """模型提供方不可用（网络失败 / 未配置 Key / 本地模型缺失）。"""

    code = "provider_unavailable"
    http_status = 503


class ConfigError(NexusError):
    code = "config_error"
    http_status = 500


class WorkflowError(NexusError):
    code = "workflow_error"
    http_status = 400
