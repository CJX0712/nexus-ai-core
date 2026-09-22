"""统一日志模块（单一职责：只负责日志格式与输出）。

作者: 晨星
"""
from __future__ import annotations

import sys

from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """配置 loguru：移除默认 sink，绑定结构化格式到 stdout。"""
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=False,
        backtrace=False,
        diagnose=False,
    )


def get_logger(name: str):
    """返回带命名空间的 logger。"""
    return logger.bind(module=name)
