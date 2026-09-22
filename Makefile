# NexusAI 一键操作入口（作者: 晨星）

PYTHON ?= python
NPM    ?= npm

.PHONY: bootstrap dev dev-backend dev-frontend test lint fmt build up down clean help

help:
	@echo "bootstrap     安装后端与前端依赖（使用锁定版本）"
	@echo "dev           同时启动后端(8000)与前端(5173)"
	@echo "dev-backend   仅启动后端 API"
	@echo "dev-frontend  仅启动前端控制台"
	@echo "test          运行后端测试套件"
	@echo "lint          运行后端 lint"
	@echo "build         构建前端生产包"
	@echo "up / down     docker compose 一键起停"

bootstrap:
	$(PYTHON) -m pip install -r backend/requirements.lock.txt
	cd frontend && $(NPM) install

dev-backend:
	cd backend && $(PYTHON) -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && $(NPM) run dev

dev: dev-backend

test:
	cd backend && $(PYTHON) -m pytest tests -q

lint:
	cd backend && $(PYTHON) -m ruff check .

build:
	cd frontend && $(NPM) run build

up:
	docker compose up --build -d

down:
	docker compose down

clean:
	cd backend && rm -rf .pytest_cache .ruff_cache
