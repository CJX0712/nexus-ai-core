# NexusAI 前端控制台镜像（构建产物由 Nginx 托管，作者: 晨星）
FROM node:25-alpine AS build

WORKDIR /app
# 注: package-lock.json 生成于 Windows, 会导致 npm 可选平台依赖 (rollup musl) 缺失,
# 故这里不复制锁文件, 直接 npm install 让 npm 重新解析平台依赖。
COPY package.json ./
RUN npm install --ignore-scripts

COPY tsconfig.json vite.config.ts index.html ./
COPY src/ ./src/
RUN npm run build

FROM nginx:1.30-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
