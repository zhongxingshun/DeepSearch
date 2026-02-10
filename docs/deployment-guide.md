# DeepSearch 生产部署指南

> **目标环境**: Ubuntu 22.04/24.04 LTS + Docker  
> **最后更新**: 2026-02-10  
> **版本**: v1.0

---

## 目录

1. [系统架构概览](#1-系统架构概览)
2. [服务器要求](#2-服务器要求)
3. [服务器环境准备](#3-服务器环境准备)
4. [项目部署](#4-项目部署)
5. [配置说明](#5-配置说明)
6. [启动服务](#6-启动服务)
7. [初始化验证](#7-初始化验证)
8. [HTTPS 配置（可选）](#8-https-配置可选)
9. [运维管理](#9-运维管理)
10. [备份与恢复](#10-备份与恢复)
11. [监控与日志](#11-监控与日志)
12. [故障排查](#12-故障排查)
13. [安全加固](#13-安全加固)

---

## 1. 系统架构概览

```
                    ┌─────────────────────────────────────────────┐
                    │                 Ubuntu Server               │
                    │                                             │
  用户浏览器 ──────▶│  ┌──────────────────────────────────┐       │
                    │  │  Frontend (Nginx:80)              │       │
                    │  │  - 静态资源服务                     │       │
                    │  │  - API 反向代理 → Backend:8200     │       │
                    │  └──────────────────────────────────┘       │
                    │                    │                         │
                    │                    ▼                         │
                    │  ┌──────────────────────────────────┐       │
                    │  │  Backend API (Uvicorn:8200)       │       │
                    │  │  - FastAPI 应用                    │       │
                    │  │  - JWT 认证                        │       │
                    │  │  - 文件上传/预览/下载               │       │
                    │  └──────────────────────────────────┘       │
                    │           │          │          │            │
                    │           ▼          ▼          ▼            │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
                    │  │PostgreSQL│ │  Redis   │ │Meilisearch│    │
                    │  │  :5432   │ │  :6379   │ │  :7700    │    │
                    │  └──────────┘ └──────────┘ └──────────┘    │
                    │           │                                  │
                    │           ▼                                  │
                    │  ┌──────────────────────────────────┐       │
                    │  │  Celery Worker + Beat             │       │
                    │  │  - 文档解析 (OCR/文本提取)         │       │
                    │  │  - 搜索索引                        │       │
                    │  │  - 定时维护任务                     │       │
                    │  └──────────────────────────────────┘       │
                    └─────────────────────────────────────────────┘
```

### 服务清单

| 容器 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `deepsearch-frontend` | Nginx + Vue SPA | 3200→80 | 前端 + API 反向代理 |
| `deepsearch-backend` | Python 3.11 + FastAPI | 8200 | 后端 API |
| `deepsearch-celery-worker` | 同 backend | - | 异步任务处理 |
| `deepsearch-celery-beat` | 同 backend | - | 定时任务调度 |
| `deepsearch-postgres` | PostgreSQL 15 | 5432 | 数据库 |
| `deepsearch-redis` | Redis 7 | 6379 | 缓存/消息队列 |
| `deepsearch-meilisearch` | Meilisearch v1.6 | 7700 | 搜索引擎 |

---

## 2. 服务器要求

### 最低配置

| 项目 | 要求 |
|------|------|
| **CPU** | 2 核 |
| **内存** | 4 GB |
| **硬盘** | 50 GB SSD |
| **系统** | Ubuntu 22.04/24.04 LTS |
| **网络** | 公网 IP 或内网可达 |

### 推荐配置

| 项目 | 要求 |
|------|------|
| **CPU** | 4 核+ |
| **内存** | 8 GB+ |
| **硬盘** | 200 GB+ SSD（取决于文件量） |
| **系统** | Ubuntu 24.04 LTS |

### 端口清单

| 端口 | 用途 | 需要开放 |
|------|------|---------|
| 80 | HTTP | ✅ 外部访问 |
| 443 | HTTPS | ✅ 如配置 SSL |
| 3200 | 前端 (Docker映射) | ✅ 或通过反向代理 |
| 5432 | PostgreSQL | ❌ 仅内部 |
| 6379 | Redis | ❌ 仅内部 |
| 7700 | Meilisearch | ❌ 仅内部 |
| 8200 | 后端 API | ❌ 仅内部 |

> ⚠️ **生产环境中，5432/6379/7700/8200 端口不应对外开放**。如需限制，请参考 [安全加固](#13-安全加固)。

---

## 3. 服务器环境准备

### 3.1 更新系统

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim htop
```

### 3.2 安装 Docker

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sudo sh

# 添加当前用户到 docker 组（免 sudo）
sudo usermod -aG docker $USER

# 重新登录使权限生效
newgrp docker

# 验证安装
docker --version
docker compose version
```

### 3.3 配置 Docker（可选优化）

```bash
# 修改 Docker 数据目录（如果根分区空间不足）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
    "data-root": "/data/docker",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "50m",
        "max-file": "3"
    },
    "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

### 3.4 配置防火墙

```bash
# 安装 UFW（如未安装）
sudo apt install -y ufw

# 允许 SSH
sudo ufw allow 22/tcp

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 允许 DeepSearch 前端端口（如不使用反向代理）
sudo ufw allow 3200/tcp

# 启用防火墙
sudo ufw enable
sudo ufw status
```

---

## 4. 项目部署

### 4.1 上传代码到服务器

#### 方式一：Git Clone（推荐）

```bash
# 在服务器上
cd /opt
sudo git clone <your-git-repo-url> deepsearch
sudo chown -R $USER:$USER /opt/deepsearch
cd /opt/deepsearch
```

#### 方式二：手动上传

```bash
# 在本地执行（排除 node_modules 和虚拟环境等）
cd /Users/jeffrey.zhong/workplace/project/DeepSearch
tar czf deepsearch.tar.gz \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='logs/*' \
    --exclude='backend/file_storage' \
    --exclude='.git' \
    .

# 上传到服务器
scp deepsearch.tar.gz user@your-server:/opt/

# 在服务器上解压
ssh user@your-server
sudo mkdir -p /opt/deepsearch
cd /opt/deepsearch
sudo tar xzf /opt/deepsearch.tar.gz
sudo chown -R $USER:$USER /opt/deepsearch
```

### 4.2 项目目录结构

```
/opt/deepsearch/
├── backend/              # 后端代码
│   ├── app/              # FastAPI 应用
│   ├── Dockerfile        # 后端 Docker 镜像
│   └── requirements.txt  # Python 依赖
├── frontend/             # 前端代码
│   ├── src/              # Vue 源码
│   ├── Dockerfile        # 前端 Docker 镜像
│   └── nginx.conf        # Nginx 配置
├── nginx/                # Nginx 配置（独立部署用）
├── scripts/
│   ├── init-db.sql       # 数据库初始化脚本
│   └── backup.sh         # 备份脚本
├── docker-compose.yml    # 🔑 生产环境编排
├── docker-compose.dev.yml # 开发环境
└── .env                  # 🔑 环境变量配置（需创建）
```

---

## 5. 配置说明

### 5.1 创建环境变量文件

```bash
cd /opt/deepsearch

cat > .env << 'EOF'
# ==================================================
# DeepSearch 生产环境配置
# ==================================================

# ---------- 数据库 ----------
DB_NAME=deepsearch
DB_USER=deepsearch
DB_PASSWORD=YourStrongDBPassword2026!

# ---------- 搜索引擎 ----------
MEILI_MASTER_KEY=YourMeiliSearchMasterKey2026!

# ---------- 安全密钥 ----------
JWT_SECRET_KEY=YourJWTSecretKeyAtLeast32Characters!
APP_SECRET_KEY=YourAppSecretKeyAtLeast32Characters!

EOF

# 设置权限（仅当前用户可读）
chmod 600 .env
```

### 5.2 配置项说明

| 变量 | 说明 | 必须修改 |
|------|------|---------|
| `DB_PASSWORD` | PostgreSQL 密码 | ✅ **必须修改** |
| `MEILI_MASTER_KEY` | Meilisearch 管理密钥 | ✅ **必须修改** |
| `JWT_SECRET_KEY` | JWT 签名密钥（≥32字符） | ✅ **必须修改** |
| `APP_SECRET_KEY` | 应用加密密钥（≥32字符） | ✅ **必须修改** |
| `DB_NAME` | 数据库名 | 可选 |
| `DB_USER` | 数据库用户名 | 可选 |

> 🔐 **安全提示**: 使用 `openssl rand -hex 32` 生成强随机密钥。

### 5.3 生成安全密钥

```bash
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"
echo "APP_SECRET_KEY=$(openssl rand -hex 32)"
echo "MEILI_MASTER_KEY=$(openssl rand -hex 16)"
echo "DB_PASSWORD=$(openssl rand -base64 24)"
```

### 5.4 端口映射修改（可选）

如果服务器上的默认端口有冲突，可以编辑 `docker-compose.yml`：

```yaml
# 前端端口：将 3200 改为你想要的端口
frontend:
  ports:
    - "80:80"    # 直接绑定 80 端口对外提供服务

# 以下端口建议仅在调试时开放，生产环境应注释掉
postgres:
  ports:
    - "127.0.0.1:5432:5432"   # 限制只能本机访问
redis:
  ports:
    - "127.0.0.1:6379:6379"
meilisearch:
  ports:
    - "127.0.0.1:7700:7700"
```

---

## 6. 启动服务

### 6.1 构建并启动

```bash
cd /opt/deepsearch

# 首次部署：构建镜像并启动所有服务
docker compose up -d --build

# 查看构建进度（首次约 5-10 分钟）
docker compose logs -f
```

### 6.2 查看服务状态

```bash
# 查看所有容器状态
docker compose ps

# 预期输出（所有容器应为 running / healthy）：
# NAME                        STATUS
# deepsearch-frontend         Up (healthy)
# deepsearch-backend          Up (healthy)
# deepsearch-celery-worker    Up
# deepsearch-celery-beat      Up
# deepsearch-postgres         Up (healthy)
# deepsearch-redis            Up (healthy)
# deepsearch-meilisearch      Up (healthy)
```

### 6.3 启动顺序

Docker Compose 会按照依赖关系自动启动：

```
PostgreSQL + Redis + Meilisearch  (基础设施，先启动)
         ↓
      Backend API                 (等待数据库 healthy)
         ↓
    Celery Worker                 (等待 Backend + Redis)
         ↓
    Celery Beat                   (等待 Worker)
         ↓
      Frontend                    (等待 Backend healthy)
```

---

## 7. 初始化验证

### 7.1 健康检查

```bash
# 后端健康检查
curl -s http://localhost:8200/api/v1/health | python3 -m json.tool

# 前端健康检查
curl -s http://localhost:3200/health

# Meilisearch 检查
curl -s http://localhost:7700/health

# PostgreSQL 检查
docker exec deepsearch-postgres pg_isready -U deepsearch

# Redis 检查
docker exec deepsearch-redis redis-cli ping
```

### 7.2 登录测试

```bash
# 使用默认管理员登录
curl -s http://localhost:8200/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123456"}' | python3 -m json.tool
```

> 预期返回 `access_token`。

### 7.3 浏览器访问

打开浏览器访问: `http://<服务器IP>:3200`

- **默认账号**: `admin`
- **默认密码**: `admin123456`

> ⚠️ **首次登录后请立即修改管理员密码！**

---

## 8. HTTPS 配置（可选）

### 8.1 使用 Let's Encrypt 免费证书

```bash
# 安装 Certbot
sudo apt install -y certbot

# 先停止前端容器释放 80 端口
docker compose stop frontend

# 申请证书（替换为你的域名）
sudo certbot certonly --standalone -d your-domain.com

# 证书文件位置：
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

### 8.2 修改 Nginx 配置

编辑 `frontend/nginx.conf`，在 `http` 块中添加 HTTPS server：

```nginx
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

# HTTPS 服务
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # ... 其余配置同原有 server 块 ...
}
```

### 8.3 挂载证书到容器

修改 `docker-compose.yml` 中的 frontend 服务：

```yaml
frontend:
  volumes:
    - /etc/letsencrypt/live/your-domain.com/fullchain.pem:/etc/nginx/ssl/fullchain.pem:ro
    - /etc/letsencrypt/live/your-domain.com/privkey.pem:/etc/nginx/ssl/privkey.pem:ro
  ports:
    - "80:80"
    - "443:443"
```

### 8.4 自动续期

```bash
# Certbot 自动续期 cron
echo "0 3 * * * certbot renew --quiet && docker restart deepsearch-frontend" | sudo crontab -
```

---

## 9. 运维管理

### 9.1 常用命令速查

```bash
cd /opt/deepsearch

# ---------- 服务管理 ----------
docker compose up -d             # 启动所有服务
docker compose down              # 停止并移除所有容器
docker compose restart           # 重启所有服务
docker compose restart backend   # 重启单个服务
docker compose stop              # 停止（不移除容器）
docker compose start             # 启动已停止的容器

# ---------- 日志查看 ----------
docker compose logs -f           # 查看所有日志（实时）
docker compose logs -f backend   # 只看后端日志
docker compose logs --tail=100 celery-worker  # 最近100条

# ---------- 进入容器 ----------
docker exec -it deepsearch-backend bash
docker exec -it deepsearch-postgres psql -U deepsearch -d deepsearch
docker exec -it deepsearch-redis redis-cli

# ---------- 更新部署 ----------
git pull                          # 拉取最新代码
docker compose up -d --build      # 重新构建并启动
docker compose up -d --build backend  # 只重建后端

# ---------- 清理 ----------
docker system prune -f            # 清理未使用的镜像/容器
docker volume prune -f            # 清理未使用的卷（⚠️ 谨慎！）
```

### 9.2 数据库管理

```bash
# 进入数据库
docker exec -it deepsearch-postgres psql -U deepsearch -d deepsearch

# 查看文件数量
docker exec deepsearch-postgres psql -U deepsearch -d deepsearch \
  -c "SELECT index_status, COUNT(*) FROM files GROUP BY index_status;"

# 查看数据库大小
docker exec deepsearch-postgres psql -U deepsearch -d deepsearch \
  -c "SELECT pg_size_pretty(pg_database_size('deepsearch'));"
```

### 9.3 Celery 任务管理

```bash
# 查看 Worker 状态
docker exec deepsearch-celery-worker celery -A app.tasks inspect active

# 查看队列长度
docker exec deepsearch-redis redis-cli LLEN celery

# 查看 Worker 日志
docker compose logs -f celery-worker
```

### 9.4 更新部署流程

```bash
cd /opt/deepsearch

# 1. 拉取最新代码
git pull origin main

# 2. 重新构建并启动（零停机）
docker compose up -d --build

# 3. 验证服务是否正常
docker compose ps
curl -s http://localhost:8200/api/v1/health

# 4. 如有数据库迁移
docker exec deepsearch-backend alembic upgrade head
```

---

## 10. 备份与恢复

### 10.1 数据库备份

```bash
# 手动备份
docker exec deepsearch-postgres pg_dump -U deepsearch deepsearch | gzip > \
  backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 自动定时备份 (每天凌晨 2 点)
cat > /opt/deepsearch/scripts/daily-backup.sh << 'SCRIPT'
#!/bin/bash
BACKUP_DIR="/opt/deepsearch/backups"
mkdir -p $BACKUP_DIR

# 数据库备份
docker exec deepsearch-postgres pg_dump -U deepsearch deepsearch | gzip > \
  $BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql.gz

# 保留最近 30 天备份
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "[$(date)] 备份完成"
SCRIPT

chmod +x /opt/deepsearch/scripts/daily-backup.sh

# 添加 cron 任务
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/deepsearch/scripts/daily-backup.sh >> /opt/deepsearch/logs/backup.log 2>&1") | crontab -
```

### 10.2 数据库恢复

```bash
# 恢复备份
gunzip -c backup_20260210.sql.gz | docker exec -i deepsearch-postgres psql -U deepsearch -d deepsearch
```

### 10.3 文件存储备份

```bash
# 文件存储在 Docker Volume 中
# 查看卷位置
docker volume inspect deepsearch_file-storage

# 备份文件卷
docker run --rm -v deepsearch_file-storage:/data -v $(pwd):/backup \
  alpine tar czf /backup/files_$(date +%Y%m%d).tar.gz -C /data .
```

### 10.4 Meilisearch 备份

```bash
# 通过 API 触发快照
curl -X POST "http://localhost:7700/snapshots" \
  -H "Authorization: Bearer ${MEILI_MASTER_KEY}"
```

---

## 11. 监控与日志

### 11.1 日志位置

| 日志 | 位置 |
|------|------|
| 后端 API | `docker compose logs backend` |
| Celery Worker | `docker compose logs celery-worker` |
| Celery Beat | `docker compose logs celery-beat` |
| Nginx | `docker compose logs frontend` |
| PostgreSQL | `docker compose logs postgres` |

### 11.2 磁盘空间监控

```bash
# 检查 Docker 使用空间
docker system df

# 检查各卷大小
docker system df -v | grep deepsearch

# 检查服务器磁盘
df -h
```

### 11.3 简易健康监控脚本

```bash
cat > /opt/deepsearch/scripts/health-check.sh << 'SCRIPT'
#!/bin/bash

check_service() {
    local name=$1
    local url=$2
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 5)
    if [ "$status" = "200" ]; then
        echo "✅ $name: OK"
    else
        echo "❌ $name: FAILED (HTTP $status)"
    fi
}

echo "=== DeepSearch 健康检查 $(date) ==="
check_service "Frontend"    "http://localhost:3200/health"
check_service "Backend API" "http://localhost:8200/api/v1/health"
check_service "Meilisearch" "http://localhost:7700/health"

# PostgreSQL
pg_status=$(docker exec deepsearch-postgres pg_isready -U deepsearch 2>/dev/null)
if [ $? -eq 0 ]; then echo "✅ PostgreSQL: OK"; else echo "❌ PostgreSQL: FAILED"; fi

# Redis
redis_status=$(docker exec deepsearch-redis redis-cli ping 2>/dev/null)
if [ "$redis_status" = "PONG" ]; then echo "✅ Redis: OK"; else echo "❌ Redis: FAILED"; fi

echo "=== Docker 容器状态 ==="
docker compose -f /opt/deepsearch/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}"
SCRIPT

chmod +x /opt/deepsearch/scripts/health-check.sh
```

---

## 12. 故障排查

### 12.1 容器无法启动

```bash
# 查看失败容器日志
docker compose logs backend 2>&1 | tail -50

# 常见原因：
# 1. 端口被占用 → netstat -tlnp | grep <port>
# 2. 内存不足   → free -h
# 3. 磁盘满     → df -h
```

### 12.2 数据库连接失败

```bash
# 检查 PostgreSQL 是否正常
docker compose logs postgres | tail -20

# 检查连接
docker exec deepsearch-backend python -c "
from app.config import settings
print(f'DB URL: {settings.database_url}')
"

# 手动测试连接
docker exec deepsearch-postgres psql -U deepsearch -d deepsearch -c "SELECT 1;"
```

### 12.3 搜索不工作

```bash
# 检查 Meilisearch
curl -s http://localhost:7700/health
curl -s http://localhost:7700/indexes \
  -H "Authorization: Bearer $(grep MEILI_MASTER_KEY .env | cut -d= -f2)"

# 检查 Celery Worker 是否在处理任务
docker compose logs celery-worker | tail -30
```

### 12.4 文件上传失败

```bash
# 检查存储空间
docker exec deepsearch-backend df -h /data/files

# 检查权限
docker exec deepsearch-backend ls -la /data/files

# 检查后端日志
docker compose logs backend | grep -i "upload\|error" | tail -20
```

### 12.5 前端无法访问后端

```bash
# 检查 Nginx 代理配置
docker exec deepsearch-frontend cat /etc/nginx/nginx.conf | grep upstream -A 5

# 测试容器间网络
docker exec deepsearch-frontend curl -s http://backend:8200/api/v1/health
```

### 12.6 容器重启/OOM

```bash
# 检查容器重启次数
docker compose ps

# 查看容器退出原因
docker inspect deepsearch-backend | grep -A5 "State"

# 增加内存限制（在 docker-compose.yml 中）
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

---

## 13. 安全加固

### 13.1 修改默认密码

**首次部署后立即执行：**

1. 登录系统修改 admin 密码
2. 修改 `.env` 中所有默认密钥

### 13.2 限制端口访问

修改 `docker-compose.yml`，将基础设施端口绑定到本地：

```yaml
postgres:
  ports:
    - "127.0.0.1:5432:5432"   # 仅本机可访问

redis:
  ports:
    - "127.0.0.1:6379:6379"

meilisearch:
  ports:
    - "127.0.0.1:7700:7700"
```

> 或者直接删除 `ports` 配置，这些服务通过 Docker 内部网络通信即可。

### 13.3 设置 Redis 密码

```yaml
# docker-compose.yml
redis:
  command: redis-server --appendonly yes --maxmemory 256mb --requirepass YourRedisPassword

# .env 中添加
REDIS_PASSWORD=YourRedisPassword
```

### 13.4 启用防火墙日志

```bash
sudo ufw logging on
```

### 13.5 定期更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 更新 Docker 基础镜像
docker compose pull
docker compose up -d
```

---

## 快速部署 Cheatsheet

```bash
# === 一键部署（从零开始）===

# 1. 准备环境
sudo apt update && sudo apt install -y curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker

# 2. 获取代码
cd /opt && sudo git clone <repo-url> deepsearch && cd deepsearch
sudo chown -R $USER:$USER .

# 3. 配置
cat > .env << EOF
DB_PASSWORD=$(openssl rand -base64 24)
MEILI_MASTER_KEY=$(openssl rand -hex 16)
JWT_SECRET_KEY=$(openssl rand -hex 32)
APP_SECRET_KEY=$(openssl rand -hex 32)
EOF
chmod 600 .env

# 4. 启动
docker compose up -d --build

# 5. 验证
sleep 30  # 等待服务启动
docker compose ps
curl -s http://localhost:3200/health

# 6. 访问
echo "✅ 部署完成！访问 http://$(hostname -I | awk '{print $1}'):3200"
echo "   默认账号: admin / admin123456"
echo "   ⚠️  请立即修改密码！"
```

---

> 📝 **文档维护**:  如果项目有更新，请同步更新此部署指南。
