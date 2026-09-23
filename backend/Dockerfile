# NexusAI 后端镜像（作者: 晨星）
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NEXUS_DATA_DIR=/app/data \
    NEXUS_HOST=0.0.0.0 \
    NEXUS_PORT=8000

WORKDIR /app

# 优先安装依赖层，利用 Docker 缓存。
# 注: llama-cpp-python 需编译工具链, 默认剔除；离线栈用内置降级后端 (auto -> 抽取式应答)。
COPY requirements.lock.txt ./
RUN grep -viE '^[[:space:]]*llama[_-]cpp[_-]python' requirements.lock.txt > /tmp/requirements.lock \
 && pip install --no-cache-dir -r /tmp/requirements.lock

COPY app/ ./app/
COPY pyproject.toml ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
