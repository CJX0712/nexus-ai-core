"""工作流路由（单一职责：只暴露 DAG 工作流执行接口）。

作者: 晨星
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas import WorkflowRequest, WorkflowResponse
from app.container import Container, get_container
from app.core.errors import NexusError
from app.workflow.engine import Node

router = APIRouter(prefix="/v1/workflow", tags=["workflow"])


@router.post("/run", response_model=WorkflowResponse)
def run(req: WorkflowRequest,
        c: Container = Depends(get_container)) -> WorkflowResponse:
    try:
        nodes = [Node(id=n.id, kind=n.kind, params=n.params,
                      depends_on=n.depends_on) for n in req.nodes]
        result = c.workflow.run(nodes, req.input)
    except NexusError:
        raise
    except Exception as exc:  # noqa: BLE001 - 统一转为领域错误
        raise NexusError(f"工作流执行失败: {exc}") from exc
    return WorkflowResponse(order=result.order, outputs=result.outputs)
