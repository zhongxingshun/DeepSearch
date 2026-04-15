# DeepSearch 部署文档

## 结论先看

当前项目只有一个推荐的部署入口：

```bash
cd /home/akuvox/DeepSearch
bash scripts/deploy.sh update
```

不要再使用以下方式做日常更新：

- `scripts/remote-deploy.sh`
- `docs/deployment-guide.md` 里的旧流程
- 只执行 `docker compose build && docker compose up -d`

原因：

- 这次项目已经有数据库迁移需求
- `deploy.sh update` 会先备份数据库和 `.env`
- `deploy.sh update` 会自动执行 Alembic 迁移
- 旧流程容易出现“代码更新了，但数据库没升级”的问题

---

## 当前生产环境

| 项目 | 说明 |
|------|------|
| 服务器 | `192.168.10.65` |
| SSH 用户 | `akuvox` |
| 项目目录 | `/home/akuvox/DeepSearch` |
| 对外访问 | `http://192.168.10.65:3200` |
| 前端端口 | `3200 -> 80` |
| 后端端口 | `8200`（仅容器内部使用，不直接暴露到宿主机） |

---

## 推荐部署方式

### 1. 先从本地同步代码到服务器

服务器目录当前不是 Git 仓库，所以不要假设服务器上能直接 `git pull` 到最新代码。

推荐用 `rsync` 同步：

```bash
rsync -avz --delete \
  --omit-dir-times \
  --no-perms \
  --no-owner \
  --no-group \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'logs/*' \
  --exclude 'data/files/*' \
  --exclude 'backups' \
  -e "ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
  ./ akuvox@192.168.10.65:/home/akuvox/DeepSearch/
```

说明：

- `.env` 不同步，保留服务器现场配置
- `data/files` 不同步，避免覆盖服务器文件存储
- `backups` 不同步，避免覆盖服务器备份

### 2. 在服务器执行更新

```bash
ssh -i ~/.ssh/id_ed25519 akuvox@192.168.10.65
cd /home/akuvox/DeepSearch
bash scripts/deploy.sh update
```

默认会执行：

1. 备份 PostgreSQL 数据库
2. 备份 `.env`
3. 清理 30 天前旧备份
4. 构建最新镜像
5. 执行数据库迁移
6. 重启服务
7. 做健康检查

如果本次更新明确涉及文件存储逻辑，再用：

```bash
bash scripts/deploy.sh update --with-files-backup
```

---

## 首次部署

首次部署仍然使用：

```bash
cd /home/akuvox/DeepSearch
sudo bash scripts/deploy.sh install
```

它会完成：

1. 安装 Docker
2. 生成 `.env`
3. 创建目录
4. 构建镜像
5. 启动服务
6. 执行数据库迁移
7. 健康检查

注意：

- `install` 只适合首次部署或明确重装
- 已有正式数据的机器，日常更新不要再跑 `install`

---

## 常用命令

```bash
cd /home/akuvox/DeepSearch

# 更新部署
bash scripts/deploy.sh update

# 仅做备份（默认备份数据库 + .env）
bash scripts/deploy.sh backup

# 备份数据库 + .env + 文件卷
bash scripts/deploy.sh backup --with-files-backup

# 查看状态
bash scripts/deploy.sh status

# 健康检查
bash scripts/deploy.sh health

# 查看日志
bash scripts/deploy.sh logs
bash scripts/deploy.sh logs backend

# 重启服务
bash scripts/deploy.sh restart
```

---

## 备份说明

默认备份内容：

- PostgreSQL 数据库
- `.env`

可选备份内容：

- 文件存储卷 `deepsearch_file-storage`

默认不备份文件卷的原因：

- 文件卷可能很大
- 大多数代码更新不会直接修改原始文件内容
- 数据库和 `.env` 是每次更新都应该优先保护的内容

备份目录：

```bash
/home/akuvox/DeepSearch/backups
```

如果脚本提示备份目录不可写，先修权限：

```bash
sudo chown -R akuvox:akuvox /home/akuvox/DeepSearch/backups
```

---

## 数据库迁移说明

这套项目已经接入 Alembic，部署时不要再手工只跑 `docker compose up -d`。

原因：

- 新代码可能依赖新表或新字段
- 如果不迁移，服务可能能启动，但功能会报错

当前推荐做法就是：

```bash
bash scripts/deploy.sh update
```

脚本会自动执行：

```bash
docker compose run --rm backend alembic upgrade head
```

### 老库第一次接入 Alembic 的特殊情况

如果数据库里已经有业务表，但还没有 `alembic_version`，首次迁移可能会报：

- `relation "users" already exists`

这代表数据库已有旧表，但还没建立 Alembic 基线。

正确处理方式：

1. 先确认现有库结构就是初始版本
2. 执行：

```bash
docker compose run --rm backend alembic stamp 001_initial
docker compose run --rm backend alembic upgrade head
```

不要直接删除旧表重跑。

---

## 健康检查说明

健康检查以这两个地址为准：

```bash
http://127.0.0.1:3200/health
http://127.0.0.1:3200/api/v1/health
```

说明：

- 前端通过 `3200` 暴露到宿主机
- 后端由前端 Nginx 代理出去
- 不要再用宿主机 `localhost:8200` 判断服务是否可用

---

## 禁止事项

以下动作不要在有正式数据的服务器上随便执行：

```bash
bash scripts/deploy.sh clean
```

因为它会执行：

```bash
docker compose down -v --rmi all
```

这会删除：

- 数据库卷
- Redis 卷
- Meilisearch 卷
- 文件存储卷

也不要再依赖已删除的 `scripts/remote-deploy.sh`。后续统一只用 `scripts/deploy.sh`。
