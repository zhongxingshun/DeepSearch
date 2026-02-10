# DeepSearch 前端 Dockerfile
# 版本: v1.0

# ================================
# 构建阶段: 编译前端资源
# ================================
FROM node:20-alpine as builder

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm ci --silent

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# ================================
# 运行阶段: Nginx 静态服务
# ================================
FROM nginx:alpine as runtime

LABEL maintainer="DeepSearch Team"
LABEL version="1.0"
LABEL description="DeepSearch Frontend Web Server"

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

# 从构建阶段复制静态文件
COPY --from=builder /app/dist /usr/share/nginx/html

# 创建非 root 用户运行
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

# 启动命令
CMD ["nginx", "-g", "daemon off;"]
