# DeepSearch 部署文档

## 结论先看

截至 2026-05-11，生产部署分成两个状态看：

- **当前可用流程**：本地代码通过 `rsync` 同步到服务器，然后在服务器执行 `bash scripts/deploy.sh update`。这个流程会在服务器上重新构建应用镜像。
- **目标改造方向**：由 GitHub Actions/CI 构建并推送版本化镜像，服务器只 `pull` 镜像、执行数据库迁移、重启服务。日常更新不应再在服务器现场 build。

当前生产服务器还不是 Git 仓库，也没有镜像仓库发布链路，所以在 CI 镜像发布落地前，仍然使用下面的安全流程：

```bash
cd /home/akuvox/DeepSearch
bash scripts/deploy.sh update
```

不要误判当前部署方式：

- 当前不是服务器直接 `git pull`
- 当前不是本地 build 完镜像再上传
- 当前不是从 GitHub/GHCR 拉应用镜像
- 当前是“代码同步到服务器，然后服务器本机 `docker compose build`”

不要再使用以下方式做生产日常更新：

- `scripts/remote-deploy.sh`
- `docs/deployment-guide.md` 里的旧流程
- 只执行 `docker compose build && docker compose up -d`

原因：

- 这次项目已经有数据库迁移需求
- `deploy.sh update` 会先备份数据库和 `.env`
- `deploy.sh update` 会自动执行 Alembic 迁移
- 旧流程容易出现“代码更新了，但数据库没升级”的问题

---

## 当前部署方式：服务器现场构建

### 构建发生在哪里

当前构建发生在生产服务器 `192.168.10.65` 上。

原因：

- `docker-compose.yml` 中 `frontend`、`backend`、`celery-worker`、`celery-beat` 使用 `build:`
- `scripts/deploy.sh update` 会调用 `docker compose build`
- 所以谁执行 `deploy.sh update`，谁就在本机构建镜像；生产流程是在服务器执行，因此镜像在服务器上构建

这个流程的优点是安全、直接、容易排查；缺点是慢，尤其后端依赖 PaddleOCR、LibreOffice、OpenCV 等大依赖时，每次构建都很重。

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

### 1. 当前临时流程：先从本地同步代码到服务器

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

### 2. 当前临时流程：在服务器执行更新

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

### 3. 目标流程：CI 构建镜像，服务器只拉镜像

后续应把日常发布改成镜像发布模式：

1. GitHub Actions 在代码合并或打版本时构建镜像
2. 推送版本化镜像，例如：
   - `deepsearch-frontend:20260509.01`
   - `deepsearch-backend:20260509.01`
3. `backend`、`celery-worker`、`celery-beat` 使用同一个后端镜像，只用不同 command 启动
4. 服务器 `.env` 或部署参数只切换 `IMAGE_TAG`
5. 服务器执行：

```bash
docker compose pull
docker compose run --rm backend alembic upgrade head
docker compose up -d --no-build
bash scripts/deploy.sh health
```

目标效果：

- 服务器不再安装/编译前后端依赖
- 日常发布只下载新镜像并重启受影响服务
- 版本回滚更清晰，可以切回上一个镜像 tag
- 数据卷继续保留，不会因为应用镜像替换而丢数据

注意：这个目标流程还需要后续修改 `docker-compose.yml`、`scripts/deploy.sh` 并新增 GitHub Actions workflow。未完成前，不要把生产更新命令改成 `pull --no-build`。

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

# 当前临时更新部署：会在服务器构建镜像
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

目标镜像发布流程落地后，日常更新命令应改为 `pull + alembic upgrade + up -d --no-build + health`，而不是 `docker compose build`。

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

## 允许第三方系统嵌入

如果别人的导航系统要用 iframe 嵌入 DeepSearch，浏览器可能报：

```text
Refused to display 'http://192.168.10.65:3200/' in a frame because it set 'X-Frame-Options' to 'sameorigin'.
```

原因是站点响应头禁止跨域 iframe 嵌入。项目已经改为使用 CSP `frame-ancestors` 控制允许嵌入的来源。

配置方式是在生产服务器 `/home/akuvox/DeepSearch/.env` 里设置 `FRAME_ANCESTORS`：

```bash
FRAME_ANCESTORS="'self' http://导航系统IP或域名:端口"
```

示例：

```bash
FRAME_ANCESTORS="'self' http://192.168.254.99:8080"
```

注意：

- 这里填的是“嵌入方导航系统页面”的 origin，不是 DeepSearch 自己的地址
- origin 必须包含协议、域名或 IP、端口；协议和端口不一致也会被浏览器拦截
- 如果导航系统是 HTTPS，这里也必须写 `https://...`
- 多个导航系统地址用空格分隔
- 不建议用 `*` 放开所有来源

修改后重建并重启前端：

```bash
cd /home/akuvox/DeepSearch
docker compose build frontend
docker compose up -d --force-recreate frontend
bash scripts/deploy.sh health
```

验证响应头：

```bash
curl -I http://127.0.0.1:3200/ | grep -i -E 'x-frame-options|content-security-policy'
```

正确状态应该看不到 `X-Frame-Options`，并能看到类似：

```text
Content-Security-Policy: frame-ancestors 'self' http://192.168.254.99:8080;
```

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
