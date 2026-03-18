# DeepSearch 部署文档

## 目录

- [环境信息](#环境信息)
- [服务架构](#服务架构)
- [首次部署](#首次部署)
- [日常更新部署](#日常更新部署)
- [服务管理](#服务管理)
- [常见问题](#常见问题)

---

## 环境信息

| 项目 | 说明 |
|------|------|
| 服务器 | 192.168.10.65 (Ubuntu 22.04, 30GB RAM, 1.8TB SSD) |
| SSH 账号 | akuvox / Akuvox@2025 |
| Docker | v29.3.0 + Compose v5.1.0 |
| Docker 镜像加速 | docker.1ms.run, docker.m.daocloud.io |
| 项目目录（服务器） | /home/akuvox/DeepSearch |
| 访问地址 | http://192.168.10.65:3200 |
| 默认账号 | admin / admin123456 |

---

## 服务架构

共 7 个 Docker 容器：

```
                    ┌─────────────────┐
   :3200 ──────────▶│    Frontend     │ (Nginx)
                    │  deepsearch-    │
                    │   frontend      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Backend      │ (FastAPI + Uvicorn)
                    │  deepsearch-    │
                    │   backend       │
                    └──┬─────┬─────┬──┘
                       │     │     │
          ┌────────────┤     │     ├────────────┐
          │            │     │     │            │
  ┌───────▼───┐  ┌────▼─────▼┐  ┌▼──────────┐ │
  │ PostgreSQL│  │   Redis   │  │Meilisearch│ │
  │   :5432   │  │   :6379   │  │   :7700   │ │
  └───────────┘  └───────────┘  └───────────┘ │
                       │                       │
              ┌────────▼────────┐  ┌───────────▼──┐
              │ Celery Worker   │  │ Celery Beat   │
              │ (异步任务处理)    │  │ (定时任务)     │
              └─────────────────┘  └──────────────┘
```

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| Frontend | deepsearch-frontend | 3200→80 | Nginx 静态资源 + API 反代 |
| Backend | deepsearch-backend | 8200 (内部) | FastAPI 4 workers |
| Celery Worker | deepsearch-celery-worker | - | 异步任务（文件解析、索引） |
| Celery Beat | deepsearch-celery-beat | - | 定时任务调度 |
| PostgreSQL | deepsearch-postgres | 5432 (仅本机) | 主数据库 |
| Redis | deepsearch-redis | 6379 (仅本机) | 缓存 + 消息队列 |
| Meilisearch | deepsearch-meilisearch | 7700 (仅本机) | 全文搜索引擎 |

---

## 首次部署

### 前提条件

- 本地已安装 `sshpass`（`brew install hudochenkov/sshpass/sshpass`）
- 服务器 SSH 端口 22 可达

### 步骤

```bash
# 1. 将代码上传到服务器
rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '.venv' \
  --exclude '__pycache__' --exclude '.env' --exclude 'logs/*' \
  -e "sshpass -p 'Akuvox@2025' ssh -o StrictHostKeyChecking=no" \
  ./ akuvox@192.168.10.65:~/DeepSearch/

# 2. SSH 登录服务器执行一键部署
sudo bash scripts/deploy.sh install
```

部署脚本会自动完成：安装 Docker → 生成 .env 密钥 → 构建镜像 → 启动服务 → 健康检查。

---

## 日常更新部署

改完代码后，在项目根目录执行一条命令：

```bash
bash scripts/remote-deploy.sh
```

这会自动完成：**同步代码 → 重建镜像 → 重启服务**。

### 其他部署命令

```bash
# 完整部署（默认）
bash scripts/remote-deploy.sh deploy

# 仅同步代码（不重建镜像，适合改配置文件）
bash scripts/remote-deploy.sh sync

# 仅重建镜像并重启（代码已同步的情况）
bash scripts/remote-deploy.sh rebuild

# 仅重启服务（不重建）
bash scripts/remote-deploy.sh restart

# 停止所有服务
bash scripts/remote-deploy.sh stop

# 查看服务状态
bash scripts/remote-deploy.sh status

# 查看日志
bash scripts/remote-deploy.sh logs              # 全部日志
bash scripts/remote-deploy.sh logs backend      # 后端日志
bash scripts/remote-deploy.sh logs frontend     # 前端日志
bash scripts/remote-deploy.sh logs celery-worker  # Celery 日志
```

### 在服务器上直接管理

SSH 登录服务器后：

```bash
cd ~/DeepSearch

# 使用 deploy.sh
bash scripts/deploy.sh status     # 查看状态
bash scripts/deploy.sh health     # 健康检查
bash scripts/deploy.sh logs       # 查看日志
bash scripts/deploy.sh restart    # 重启
bash scripts/deploy.sh backup     # 备份数据库+文件
bash scripts/deploy.sh update     # git pull + 重建 + 重启
```

---

## 服务管理

### 查看容器状态

```bash
ssh akuvox@192.168.10.65
cd ~/DeepSearch
sudo docker compose ps
```

### 重启单个服务

```bash
sudo docker compose restart backend
sudo docker compose restart celery-worker
```

### 查看实时日志

```bash
sudo docker compose logs -f backend          # 后端
sudo docker compose logs -f celery-worker    # Celery
sudo docker compose logs -f --tail 100       # 全部（最近100行）
```

### 数据备份

```bash
bash scripts/deploy.sh backup
# 备份文件保存在 ~/DeepSearch/backups/
# 自动清理 30 天前的旧备份
```

### 完全清理重装

```bash
# ⚠️ 会删除所有数据！
bash scripts/deploy.sh clean

# 然后重新部署
bash scripts/deploy.sh install
```

---

## 常见问题

### 1. 服务器 SSH 连不上

可能是多次连接失败触发了安全策略（fail2ban），等几分钟后重试，或到服务器本机检查：

```bash
sudo fail2ban-client status sshd
sudo fail2ban-client set sshd unbanip <你的IP>
```

### 2. Docker 镜像拉取失败

服务器已配置国内镜像加速（`/etc/docker/daemon.json`），如果镜像源失效，更换：

```bash
sudo vi /etc/docker/daemon.json
# 修改 registry-mirrors
sudo systemctl restart docker
```

### 3. bcrypt / passlib 报错

requirements.txt 已锁定 `bcrypt>=4.1.2,<5`。如果仍出现兼容性问题：

```bash
sudo docker exec --user root deepsearch-backend pip install "bcrypt<5"
sudo docker restart deepsearch-backend
```

### 4. 数据库表结构不匹配

init-db.sql 已与 ORM 模型同步。如果新增了模型字段，需同步更新 `scripts/init-db.sql`，或在服务器上手动 ALTER TABLE。
