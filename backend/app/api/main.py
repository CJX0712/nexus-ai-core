"""FastAPI 应用工厂（单一职责：只负责 HTTP 应用的组装与错误映射）。

作者: 晨星
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import agent, chat, memory, rag, system, workflow
from app.container import get_container
from app.core.config import get_settings
from app.core.errors import NexusError
from app.core.logging import get_logger, setup_logging

log = get_logger("api.main")


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001 - FastAPI 生命周期签名
    c = get_container()
    log.info("NexusAI 启动完成: {}", c.describe())
    yield


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="模块化 AI 能力中台：模型网关 / 知识检索 / 智能体 / 工作流 / 记忆",
        lifespan=_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NexusError)
    async def _nexus_error_handler(_: Request, exc: NexusError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict())

    app.include_router(system.router)
    app.include_router(chat.router)
    app.include_router(rag.router)
    app.include_router(agent.router)
    app.include_router(workflow.router)
    app.include_router(memory.router)
    return app


app = create_app()
