"""测试基线配置（所有测试统一走离线实现，保证无需外网/Key 即可复现）。

作者: 晨星
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# 必须在导入 app 之前设定，确保组合根装配的是离线实现
os.environ["NEXUS_EMBED_PROVIDER"] = "hashing"
os.environ["NEXUS_LLM_PROVIDER"] = "offline"
os.environ["NEXUS_DATA_DIR"] = str(Path(__file__).parent / ".testdata")
os.environ["NEXUS_HYBRID_ENABLED"] = "true"

from app.container import Container  # noqa: E402
from app.core.config import Settings, reset_settings  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _test_data_dir():
    d = Path(os.environ["NEXUS_DATA_DIR"])
    d.mkdir(parents=True, exist_ok=True)
    yield d


@pytest.fixture()
def settings(tmp_path) -> Settings:
    reset_settings()
    s = Settings.from_env()
    s.data_dir = tmp_path
    s.embed_provider = "hashing"
    s.llm_provider = "offline"
    s.embed_dim = 128
    s.top_k = 3
    s.chunk_size = 120
    s.chunk_overlap = 20
    s.ensure_dirs()
    return s


@pytest.fixture()
def container(tmp_path) -> Container:
    reset_settings()
    s = Settings.from_env()
    s.data_dir = tmp_path
    s.embed_provider = "hashing"
    s.llm_provider = "offline"
    s.embed_dim = 128
    s.top_k = 3
    s.chunk_size = 120
    s.chunk_overlap = 20
    return Container(s)


@pytest.fixture()
def offline_gateway(settings):
    from app.gateway.llm import build_llm_gateway

    return build_llm_gateway(settings)
