# DeepSearch - 企业级全格式深度搜索系统

<div align="center">

**一个强大的企业级全格式文档深度搜索平台**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.0+-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)](https://fastapi.tiangolo.com/)
[![Meilisearch](https://img.shields.io/badge/Meilisearch-v1.6-purple.svg)](https://www.meilisearch.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🔍 **全文搜索** | 基于 Meilisearch 的亚秒级全文检索，支持关键词高亮 |
| 📄 **多格式支持** | PDF、Word、Excel、PPT、图片、文本等 16+ 种格式 |
| 🎯 **OCR 识别** | PaddleOCR (PP-OCRv5) 高精度中英文 OCR，扫描件/图片自动文字提取 |
| �️ **文件预览** | 图片内联显示、PDF 嵌入预览、文档摘要展示 |
| � **文件夹管理** | 虚拟文件夹体系，支持层级导航、文件移动 |
| ⚡ **异步处理** | Celery + Redis 任务队列，后台解析不阻塞 |
| 🔐 **安全认证** | JWT Token + RBAC 权限管理 + 审计日志 |
| 📊 **管理后台** | 用户管理、系统统计、维护操作、搜索历史 |
| 🐳 **容器化部署** | Docker Compose 一键部署，7 个容器自动编排 |

## 🏗️ 系统架构

```
                    ┌─────────────────────────────────────────────┐
                    │                 Ubuntu Server               │
                    │                                             │
  用户浏览器 ──────▶│  ┌──────────────────────────────────┐       │
                    │  │  Frontend (Nginx:80)              │       │
                    │  │  Vue 3 SPA + API 反向代理          │       │
                    │  └───────────────┬──────────────────┘       │
                    │                  │                           │
                    │                  ▼                           │
                    │  ┌──────────────────────────────────┐       │
                    │  │  Backend API (FastAPI:8200)       │       │
                    │  │  认证 · 文件管理 · 搜索 · 预览     │       │
                    │  └──────────────────────────────────┘       │
                    │         │          │          │              │
                    │         ▼          ▼          ▼              │
                    │  ┌──────────┐ ┌────────┐ ┌───────────┐     │
                    │  │PostgreSQL│ │ Redis  │ │Meilisearch│     │
                    │  │  15-alp  │ │ 7-alp  │ │   v1.6    │     │
                    │  └──────────┘ └────────┘ └───────────┘     │
                    │         │                                    │
                    │         ▼                                    │
                    │  ┌──────────────────────────────────┐       │
                    │  │  Celery Worker + Beat             │       │
                    │  │  文档解析 · 搜索索引 · 定时维护     │       │
                    │  └──────────────────────────────────┘       │
                    └─────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 + TypeScript + Element Plus + Vite |
| **后端** | Python 3.11 + FastAPI + SQLAlchemy + Uvicorn |
| **搜索** | Meilisearch v1.6 |
| **数据库** | PostgreSQL 15 |
| **缓存/队列** | Redis 7 |
| **任务** | Celery 5 (Worker + Beat) |
| **OCR** | PaddleOCR 3.x (PP-OCRv5) + kreuzberg |
| **部署** | Docker + Nginx |

---

## 🚀 快速部署（Docker 一键部署）

### 前置要求

- Ubuntu 22.04/24.04 LTS（推荐）或其他 Linux
- 最低 2核 CPU / 4GB 内存 / 50GB 硬盘
- Docker 不需要提前安装，脚本会自动安装

### 一键部署（3 步完成）

```bash
# 1. 获取代码
cd /opt
sudo git clone <your-repo-url> deepsearch
sudo chown -R $USER:$USER /opt/deepsearch

# 2. 一键部署（自动安装Docker + 生成密钥 + 构建 + 启动 + 健康检查）
sudo bash /opt/deepsearch/scripts/deploy.sh install

# 3. 浏览器打开 http://<服务器IP>:3200
#    默认账号: admin / admin123456
```

> ⚠️ **首次登录后请立即修改管理员密码！**

`deploy.sh install` 会自动完成以下全部工作：
1. ✅ 检测并安装 Docker（如果未安装）
2. ✅ 自动生成所有安全密钥（写入 `.env`）
3. ✅ 创建数据目录
4. ✅ 构建 7 个 Docker 镜像
5. ✅ 启动所有服务
6. ✅ 等待健康检查通过并打印访问信息

---

## 🔧 服务管理命令

```bash
# 所有命令通过 deploy.sh 统一管理
cd /opt/deepsearch

bash scripts/deploy.sh start              # 启动所有服务
bash scripts/deploy.sh stop               # 停止所有服务
bash scripts/deploy.sh restart             # 重启所有服务
bash scripts/deploy.sh restart backend     # 重启单个服务
bash scripts/deploy.sh status              # 查看容器状态
bash scripts/deploy.sh health              # 健康检查（7 个服务）
bash scripts/deploy.sh logs                # 实时日志（全部）
bash scripts/deploy.sh logs backend        # 只看后端日志
bash scripts/deploy.sh update              # 更新部署（拉代码+重建+重启）
bash scripts/deploy.sh backup              # 备份数据库+文件
bash scripts/deploy.sh clean               # 完全清理（⚠️ 删除所有数据）
```

也可以直接使用 `docker compose` 命令：

```bash
docker exec -it deepsearch-postgres psql -U deepsearch -d deepsearch  # 进入数据库
docker exec -it deepsearch-redis redis-cli                             # 进入 Redis
docker compose logs --tail=100 celery-worker                           # 查看 Worker 日志
```

---

## 💾 备份与恢复

### 数据库备份

```bash
# 手动备份
docker exec deepsearch-postgres pg_dump -U deepsearch deepsearch | gzip > backup_$(date +%Y%m%d).sql.gz

# 恢复
gunzip -c backup_20260210.sql.gz | docker exec -i deepsearch-postgres psql -U deepsearch -d deepsearch
```

### 文件存储备份

```bash
docker run --rm \
  -v deepsearch_file-storage:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/files_$(date +%Y%m%d).tar.gz -C /data .
```

### 自动定时备份

```bash
# 每天凌晨 2 点备份数据库
(crontab -l; echo "0 2 * * * docker exec deepsearch-postgres pg_dump -U deepsearch deepsearch | gzip > /opt/deepsearch/backups/db_\$(date +\%Y\%m\%d).sql.gz") | crontab -
```

---

## 🔒 安全加固

### 生产环境必做

1. **修改默认密码**：登录后立即修改 admin 密码
2. **修改密钥**：`.env` 中所有 KEY 使用强随机值
3. **限制端口**：`docker-compose.yml` 中 PostgreSQL/Redis/Meilisearch 已绑定 `127.0.0.1`
4. **防火墙**：仅开放 80/443/3200 端口

```bash
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 3200/tcp
sudo ufw enable
```

### HTTPS 配置

```bash
# 使用 Let's Encrypt 免费证书
sudo apt install -y certbot
sudo certbot certonly --standalone -d your-domain.com

# 挂载证书到容器（修改 docker-compose.yml）
# frontend:
#   volumes:
#     - /etc/letsencrypt/live/your-domain.com/fullchain.pem:/etc/nginx/ssl/fullchain.pem:ro
#     - /etc/letsencrypt/live/your-domain.com/privkey.pem:/etc/nginx/ssl/privkey.pem:ro
```

> 📖 详细 HTTPS 配置请参考 [部署指南](docs/deployment-guide.md#8-https-配置可选)

---

## 🛠️ 本地开发环境

### 启动基础设施

```bash
# 启动 PostgreSQL + Redis + Meilisearch（开发用端口）
docker compose -f docker-compose.dev.yml up -d
```

### 后端开发

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --port 8200
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 开发环境访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3200 |
| 后端 API 文档 | http://localhost:8200/docs |
| Meilisearch | http://localhost:7700 |

---

## 📦 项目结构

```
DeepSearch/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api/               # API 路由 (auth, files, search, admin, history)
│   │   ├── core/              # 核心模块 (database, security)
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── services/          # 业务逻辑层
│   │   └── tasks/             # Celery 异步任务
│   ├── migrations/            # Alembic 数据库迁移
│   ├── tests/                 # 单元测试
│   ├── Dockerfile             # 后端镜像（多阶段构建）
│   └── requirements.txt
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── api/               # Axios API 封装
│   │   ├── views/             # 页面组件 (搜索/文件/管理/历史)
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── router/            # Vue Router
│   │   └── types/             # TypeScript 类型定义
│   ├── Dockerfile             # 前端镜像（Node 构建 + Nginx）
│   └── nginx.conf             # Nginx 配置（API 反向代理）
├── nginx/                      # 独立 Nginx 配置
├── scripts/
│   ├── init-db.sql            # 数据库初始化 SQL
│   └── backup.sh              # 备份脚本
├── docs/
│   ├── deployment-guide.md    # 📖 完整部署指南
│   └── design/                # 需求/设计文档
├── docker-compose.yml          # 🔑 生产环境编排（7 个服务）
├── docker-compose.dev.yml      # 开发环境（仅基础设施）
├── services.sh                 # 本地开发服务管理脚本
└── .env                        # 环境变量（需创建，不入库）
```

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [部署指南](docs/deployment-guide.md) | Ubuntu + Docker 完整生产部署 |
| [需求规格说明书](docs/design/需求规格说明书_v1.1.md) | 系统需求定义 |
| [技术设计文档](docs/design/技术设计文档_v1.1.md) | 架构与技术方案 |
| [API 文档](http://localhost:8200/docs) | Swagger 在线 API 文档 |

---

## ⚠️ 踩坑记录与注意事项

> **以下是实际部署中遇到的关键问题，升级或运维前务必阅读。**

### 1. PaddleOCR 依赖链（极其重要）

PaddleOCR 3.x 的依赖链非常脆弱，版本必须严格锁定：

```
paddlepaddle==3.0.0
paddlex<3.2          # ≥3.2 改了 PaddlePredictorOption 构造函数，与 paddleocr 3.0.x 不兼容
paddleocr==3.0.3
langchain<0.3        # paddlex 3.1.x 依赖 langchain.docstore，该模块在 langchain 0.3 中被移除
langchain-community<0.3
```

**可能遇到的报错**：

| 报错 | 原因 |
|------|------|
| `PaddlePredictorOption.__init__() takes 1 positional argument` | paddlex ≥ 3.2，需降级到 < 3.2 |
| `No module named 'langchain.docstore'` | langchain ≥ 0.3，需降级到 < 0.3 |
| `Illegal instruction (SIGILL)` | paddlepaddle 2.6.x 的推理优化 pass 不兼容某些 CPU，换用 3.0.0 |

**升级任何一个 paddle 相关包前，务必先在服务器上测试，不要只在本地验证。**

### 2. Meilisearch add_documents 必须指定 primary_key

```python
# ❌ 错误 — 文档有 id 和 file_id 两个字段，Meilisearch 无法推断主键，静默失败
index.add_documents([document])

# ✅ 正确
index.add_documents([document], primary_key="id")
```

**现象**：数据库 `files.index_status` 全部显示 `completed`，但搜索返回空。因为 `add_documents` 是异步的，Python 调用返回 `task_uid` 后代码就标记成功了，但 Meilisearch 后台实际处理失败。

**排查**：

```bash
# 检查 Meilisearch 失败的任务
docker exec deepsearch-backend curl -s \
  'http://meilisearch:7700/tasks?statuses=failed&limit=5' \
  -H 'Authorization: Bearer <MEILI_MASTER_KEY>'
```

### 3. Dockerfile 中 PaddleOCR 所需系统库

缺少以下库会导致 `import cv2` 或 PaddleOCR 运行时 segfault：

```dockerfile
RUN apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 libgomp1
```

同时需要为非 root 用户创建 home 目录（PaddleOCR 首次运行下载模型到 `~/.paddleocr/`）：

```dockerfile
RUN useradd -r -g deepsearch -m -d /home/deepsearch deepsearch && \
    mkdir -p /home/deepsearch/.paddlex /home/deepsearch/.paddleocr
ENV HOME=/home/deepsearch
```

### 4. docker compose build 只构建指定 service

`docker compose build backend` **不会**自动构建 celery-worker，即使它们共用同一个 Dockerfile。修改 requirements.txt 或 Dockerfile 后必须：

```bash
docker compose build --parallel backend celery-worker
docker compose up -d --force-recreate backend celery-worker celery-beat
```

### 5. bcrypt 版本锁定

`bcrypt>=5.0` 改了 API，与 `passlib` 不兼容。必须锁定 `bcrypt>=4.1.2,<5`。

---

## 🔧 运维常用命令

### 检查搜索是否正常

```bash
# 1. 文件状态分布（正常应全部 completed）
docker exec deepsearch-postgres psql -U deepsearch -d deepsearch \
  -c "SELECT index_status, COUNT(*) FROM files GROUP BY index_status;"

# 2. Meilisearch 文档数（应与 files 表 completed 数一致）
docker exec deepsearch-backend curl -s \
  'http://meilisearch:7700/indexes/documents/stats' \
  -H 'Authorization: Bearer <MEILI_MASTER_KEY>'

# 3. Meilisearch 是否有失败任务
docker exec deepsearch-backend curl -s \
  'http://meilisearch:7700/tasks?statuses=failed&limit=5' \
  -H 'Authorization: Bearer <MEILI_MASTER_KEY>'

# 4. OCR 是否正常工作
docker logs deepsearch-celery-worker 2>&1 | grep -E 'OCR|paddle|失败' | tail -20
```

### 清空所有数据重新开始

```bash
# 删除 Meilisearch 索引
docker exec deepsearch-backend curl -s -X DELETE \
  'http://meilisearch:7700/indexes/documents' \
  -H 'Authorization: Bearer <MEILI_MASTER_KEY>'

# 清空数据库
docker exec deepsearch-postgres psql -U deepsearch -d deepsearch \
  -c "TRUNCATE tasks, files RESTART IDENTITY CASCADE;"

# 清空存储文件
docker exec deepsearch-celery-worker rm -rf /data/files/*
```

### 重新索引所有文件

当文件已在数据库但需要重新 OCR + 索引时：

```bash
# 1. 重置状态
docker exec deepsearch-postgres psql -U deepsearch -d deepsearch \
  -c "UPDATE files SET index_status = 'pending', meilisearch_id = NULL;"

# 2. 创建触发脚本
cat > /tmp/reindex.py << 'EOF'
from sqlalchemy import text
from app.tasks.db_engine import sync_engine
from app.tasks.parse_task import parse_document
engine = sync_engine
with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, file_path, file_type FROM files WHERE index_status = :s"), {"s": "pending"}).fetchall()
    print(f"Found {len(rows)} pending files")
    for row in rows:
        parse_document.delay(file_id=row[0], file_path=row[1], file_type=row[2])
    print(f"Dispatched {len(rows)} parse tasks")
EOF

# 3. 执行
docker cp /tmp/reindex.py deepsearch-celery-worker:/tmp/reindex.py
docker exec -w /app -e PYTHONPATH=/app deepsearch-celery-worker python /tmp/reindex.py
```

---

## 📝 更新日志

### v1.0.1 (2026-03-18)

- 🐛 修复搜索不可用：OCR 依赖缺失 + Meilisearch 主键未指定
- 🐛 修复 PaddleOCR 依赖链：锁定 paddlex < 3.2、langchain < 0.3
- 🐛 修复 PaddlePaddle 2.6.x SIGILL 崩溃，改用 3.0.0
- 🐛 修复 Dockerfile 缺少 OCR 系统库 (libgl1 等)
- ⚡ Nginx 上传接口单独放宽限流
- 📝 添加部署文档和远程部署脚本

### v1.0.0 (2026-02-10)

- ✅ JWT 身份认证与 RBAC 权限管理
- ✅ 多格式文件上传与管理（16+ 格式）
- ✅ 虚拟文件夹体系（层级导航、文件移动）
- ✅ Meilisearch 全文搜索 + 关键词高亮
- ✅ 文件预览（图片内嵌、PDF 嵌入、文档摘要）
- ✅ OCR 文字识别（中英文）
- ✅ 搜索建议 + 热门关键词
- ✅ 搜索历史记录
- ✅ Celery 异步任务队列
- ✅ 管理后台（用户/统计/审计/维护）
- ✅ Docker Compose 一键部署

---

## 📄 许可证

[MIT License](LICENSE)

---

<div align="center">
Made with ❤️ by DeepSearch Team
</div>
