#!/bin/bash
# ============================================================
# DeepSearch 一键部署脚本
# 版本: v2.0
# 支持: Ubuntu 22.04/24.04 LTS
#
# 使用方法:
#   首次部署:  sudo bash deploy.sh install
#   启动服务:  bash deploy.sh start
#   停止服务:  bash deploy.sh stop
#   重启服务:  bash deploy.sh restart
#   查看状态:  bash deploy.sh status
#   查看日志:  bash deploy.sh logs [service]
#   健康检查:  bash deploy.sh health
#   备份数据:  bash deploy.sh backup
#   更新部署:  bash deploy.sh update
#   完全清理:  bash deploy.sh clean
# ============================================================

set -e

# ========== 配置 ==========
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"
BACKUP_DIR="$PROJECT_DIR/backups"

# ========== 颜色 ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ========== 日志函数 ==========
info()    { echo -e "${BLUE}[INFO]${NC}    $1"; }
success() { echo -e "${GREEN}[✅ OK]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[⚠️ WARN]${NC} $1"; }
error()   { echo -e "${RED}[❌ ERROR]${NC} $1"; }
header()  { echo -e "\n${CYAN}${BOLD}════════════════════════════════════════${NC}"; echo -e "${CYAN}${BOLD}  $1${NC}"; echo -e "${CYAN}${BOLD}════════════════════════════════════════${NC}\n"; }

backup_db() {
    local timestamp="$1"
    local db_file="$BACKUP_DIR/db_${timestamp}.sql.gz"
    info "备份 PostgreSQL 数据库..."
    docker exec deepsearch-postgres pg_dump -U deepsearch deepsearch | gzip > "$db_file"
    success "数据库备份: $db_file ($(du -h "$db_file" | cut -f1))"
}

backup_env_file() {
    local timestamp="$1"
    local env_backup="$BACKUP_DIR/env_${timestamp}.bak"
    if [ -f "$ENV_FILE" ]; then
        info "备份环境配置..."
        cp "$ENV_FILE" "$env_backup"
        chmod 600 "$env_backup" 2>/dev/null || true
        success ".env 备份: $env_backup"
    else
        warn ".env 不存在，跳过环境配置备份"
    fi
}

backup_file_storage() {
    local timestamp="$1"
    local files_file="$BACKUP_DIR/files_${timestamp}.tar.gz"
    info "备份文件存储..."
    docker run --rm \
        -v deepsearch_file-storage:/data:ro \
        -v "$BACKUP_DIR":/backup \
        alpine tar czf "/backup/files_${timestamp}.tar.gz" -C /data . 2>/dev/null || warn "文件备份跳过（卷可能为空）"
    if [ -f "$files_file" ]; then
        success "文件备份: $files_file ($(du -h "$files_file" | cut -f1))"
    fi
}

cleanup_old_backups() {
    find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +30 -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "env_*.bak" -mtime +30 -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "files_*.tar.gz" -mtime +30 -delete 2>/dev/null || true
    info "已清理 30 天前的旧备份"
}

ensure_backup_dir_writable() {
    mkdir -p "$BACKUP_DIR"

    if [ ! -w "$BACKUP_DIR" ]; then
        error "备份目录不可写: $BACKUP_DIR"
        warn "请先修复目录权限，例如：sudo chown -R $(whoami):$(id -gn) '$BACKUP_DIR'"
        exit 1
    fi
}

# ============================================================
# install: 完整一键部署（Docker 安装 + 密钥生成 + 构建 + 启动）
# ============================================================
cmd_install() {
    header "DeepSearch 一键部署"
    echo -e "  目标目录: ${BOLD}$PROJECT_DIR${NC}"
    echo -e "  系统信息: $(uname -s) $(uname -m)"
    echo ""

    # Step 1: 安装 Docker
    step_install_docker

    # Step 2: 生成环境变量
    step_generate_env

    # Step 3: 创建必要目录
    step_create_dirs

    # Step 4: 构建镜像
    step_build

    # Step 5: 启动服务
    step_start

    # Step 5.5: 数据库迁移
    step_run_migrations

    # Step 6: 等待并健康检查
    step_health_check

    # 完成
    header "🎉 部署完成!"
    echo ""
    local server_ip
    server_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    echo -e "  🌐 访问地址:  ${BOLD}http://${server_ip}:3200${NC}"
    echo -e "  👤 默认账号:  ${BOLD}admin${NC}"
    echo -e "  🔑 默认密码:  ${BOLD}admin123456${NC}"
    echo ""
    echo -e "  ${RED}⚠️  请立即登录修改默认密码！${NC}"
    echo ""
    echo -e "  常用命令:"
    echo -e "    查看状态:  ${CYAN}bash $SCRIPT_DIR/deploy.sh status${NC}"
    echo -e "    查看日志:  ${CYAN}bash $SCRIPT_DIR/deploy.sh logs${NC}"
    echo -e "    停止服务:  ${CYAN}bash $SCRIPT_DIR/deploy.sh stop${NC}"
    echo -e "    健康检查:  ${CYAN}bash $SCRIPT_DIR/deploy.sh health${NC}"
    echo ""
}

# ========== Step 1: 安装 Docker ==========
step_install_docker() {
    header "Step 1/6: 检查 Docker 环境"

    if command -v docker &>/dev/null && command -v docker compose &>/dev/null; then
        success "Docker 已安装: $(docker --version | head -1)"
        success "Compose 已安装: $(docker compose version | head -1)"

        # 检查 Docker daemon 是否运行
        if ! docker info &>/dev/null; then
            warn "Docker daemon 未运行，尝试启动..."
            sudo systemctl start docker || true
            sleep 2
            if ! docker info &>/dev/null; then
                error "Docker daemon 启动失败，请手动排查"
                exit 1
            fi
        fi
        return
    fi

    info "Docker 未安装，开始自动安装..."

    # 检查是否有 root 权限
    if [ "$EUID" -ne 0 ]; then
        error "安装 Docker 需要 root 权限，请使用: sudo bash deploy.sh install"
        exit 1
    fi

    # 安装依赖
    apt-get update -qq
    apt-get install -y -qq curl ca-certificates gnupg lsb-release > /dev/null 2>&1

    # 安装 Docker
    info "正在安装 Docker..."
    curl -fsSL https://get.docker.com | sh > /dev/null 2>&1

    # 启动 Docker
    systemctl enable docker
    systemctl start docker

    # 将当前用户加入 docker 组
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker "$SUDO_USER"
        info "已将用户 $SUDO_USER 加入 docker 组"
    fi

    # 验证
    if ! docker --version &>/dev/null; then
        error "Docker 安装失败"
        exit 1
    fi

    success "Docker 安装成功: $(docker --version)"

    # 配置 Docker 日志限制
    mkdir -p /etc/docker
    if [ ! -f /etc/docker/daemon.json ]; then
        cat > /etc/docker/daemon.json << 'DAEMON_EOF'
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "50m",
        "max-file": "3"
    }
}
DAEMON_EOF
        systemctl restart docker
        info "Docker 日志限制已配置（50MB x 3）"
    fi
}

# ========== Step 2: 生成环境变量 ==========
step_generate_env() {
    header "Step 2/6: 配置环境变量"

    if [ -f "$ENV_FILE" ]; then
        # 检查是否包含 CHANGE_ME（未修改的模板）
        if grep -q "CHANGE_ME" "$ENV_FILE"; then
            warn ".env 文件存在但包含未修改的默认值，将重新生成..."
        else
            success ".env 文件已存在（使用现有配置）"
            return
        fi
    fi

    info "自动生成安全密钥..."

    local db_password jwt_key app_key meili_key
    db_password=$(openssl rand -base64 24 | tr -d '/+=')
    jwt_key=$(openssl rand -hex 32)
    app_key=$(openssl rand -hex 32)
    meili_key=$(openssl rand -hex 16)

    cat > "$ENV_FILE" << ENV_EOF
# ==================================================
# DeepSearch 生产环境配置
# 自动生成时间: $(date '+%Y-%m-%d %H:%M:%S')
# ==================================================

# ---------- 数据库 ----------
DB_NAME=deepsearch
DB_USER=deepsearch
DB_PASSWORD=${db_password}

# ---------- Meilisearch ----------
MEILI_MASTER_KEY=${meili_key}

# ---------- 安全密钥 ----------
JWT_SECRET_KEY=${jwt_key}
APP_SECRET_KEY=${app_key}
ENV_EOF

    chmod 600 "$ENV_FILE"
    success "环境变量已生成: $ENV_FILE"
    info "数据库密码: ${db_password}"
    warn "请妥善保管以上密钥信息！"
}

# ========== Step 3: 创建目录 ==========
step_create_dirs() {
    header "Step 3/6: 创建数据目录"

    mkdir -p "$PROJECT_DIR/backend/logs"
    mkdir -p "$BACKUP_DIR"

    success "目录创建完成"
}

# ========== Step 4: 构建镜像 ==========
step_build() {
    header "Step 4/6: 构建 Docker 镜像"
    info "首次构建约需 5-10 分钟，请耐心等待..."

    cd "$PROJECT_DIR"
    docker compose build

    success "镜像构建完成"
}

# ========== Step 5: 启动服务 ==========
step_start() {
    header "Step 5/6: 启动所有服务"

    cd "$PROJECT_DIR"
    docker compose up -d

    success "所有容器已启动"
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
}

step_run_migrations() {
    header "数据库迁移"

    cd "$PROJECT_DIR"

    info "确保数据库服务已启动..."
    docker compose up -d postgres

    info "执行 Alembic 迁移..."
    docker compose run --rm backend alembic upgrade head

    success "数据库迁移完成"
}

# ========== Step 6: 健康检查 ==========
step_health_check() {
    header "Step 6/6: 服务健康检查"
    info "等待服务完全启动（最多 90 秒）..."

    local max_wait=90
    local waited=0
    local interval=5

    # 等待后端 API 就绪
    while [ $waited -lt $max_wait ]; do
        if curl -s -f http://localhost:8200/api/v1/health > /dev/null 2>&1; then
            success "后端 API 就绪 (${waited}s)"
            break
        fi
        sleep $interval
        waited=$((waited + interval))
        info "等待中... ${waited}/${max_wait}s"
    done

    if [ $waited -ge $max_wait ]; then
        warn "后端 API 在 ${max_wait}s 内未就绪，可能仍在启动中"
        warn "请稍后运行: bash deploy.sh health"
        return
    fi

    # 等待前端就绪
    waited=0
    while [ $waited -lt 30 ]; do
        if curl -s -f http://localhost:3200/health > /dev/null 2>&1; then
            success "前端服务就绪"
            break
        fi
        sleep 3
        waited=$((waited + 3))
    done

    # 最终检查
    echo ""
    check_all_services
}

# ============================================================
# 通用功能函数
# ============================================================

check_all_services() {
    local all_ok=true

    # Backend
    if curl -s -f http://localhost:3200/api/v1/health > /dev/null 2>&1; then
        success "Backend API       ✓"
    else
        error "Backend API       ✗"
        all_ok=false
    fi

    # Frontend
    if curl -s -f http://localhost:3200/health > /dev/null 2>&1; then
        success "Frontend          ✓"
    else
        error "Frontend          ✗"
        all_ok=false
    fi

    # PostgreSQL
    if docker exec deepsearch-postgres pg_isready -U deepsearch > /dev/null 2>&1; then
        success "PostgreSQL        ✓"
    else
        error "PostgreSQL        ✗"
        all_ok=false
    fi

    # Redis
    if docker exec deepsearch-redis redis-cli ping 2>/dev/null | grep -q PONG; then
        success "Redis             ✓"
    else
        error "Redis             ✗"
        all_ok=false
    fi

    # Meilisearch
    if curl -s -f http://localhost:7700/health > /dev/null 2>&1; then
        success "Meilisearch       ✓"
    else
        error "Meilisearch       ✗"
        all_ok=false
    fi

    # Celery Worker
    if docker ps --format '{{.Names}}' | grep -q deepsearch-celery-worker; then
        success "Celery Worker     ✓"
    else
        error "Celery Worker     ✗"
        all_ok=false
    fi

    # Celery Beat
    if docker ps --format '{{.Names}}' | grep -q deepsearch-celery-beat; then
        success "Celery Beat       ✓"
    else
        error "Celery Beat       ✗"
        all_ok=false
    fi

    echo ""
    if $all_ok; then
        success "所有服务运行正常 ✓"
    else
        warn "部分服务异常，请查看日志: bash deploy.sh logs"
    fi
}

ensure_docker() {
    if ! command -v docker &>/dev/null; then
        error "Docker 未安装，请先运行: sudo bash deploy.sh install"
        exit 1
    fi
    if ! docker info &>/dev/null; then
        error "Docker daemon 未运行"
        exit 1
    fi
}

# ============================================================
# 命令: start / stop / restart
# ============================================================
cmd_start() {
    ensure_docker
    header "启动服务"
    cd "$PROJECT_DIR"
    docker compose up -d
    success "服务已启动"
    docker compose ps --format "table {{.Name}}\t{{.Status}}"
}

cmd_stop() {
    header "停止服务"
    cd "$PROJECT_DIR"
    docker compose down
    success "服务已停止"
}

cmd_restart() {
    header "重启服务"
    cd "$PROJECT_DIR"

    local service="${1:-}"
    if [ -n "$service" ]; then
        docker compose restart "$service"
        success "$service 已重启"
    else
        docker compose down
        docker compose up -d
        success "所有服务已重启"
    fi

    docker compose ps --format "table {{.Name}}\t{{.Status}}"
}

# ============================================================
# 命令: status / health / logs
# ============================================================
cmd_status() {
    header "服务状态"
    cd "$PROJECT_DIR"
    docker compose ps
}

cmd_health() {
    header "健康检查"
    check_all_services
}

cmd_logs() {
    local service="${1:-}"
    cd "$PROJECT_DIR"
    if [ -n "$service" ]; then
        docker compose logs -f --tail=100 "$service"
    else
        docker compose logs -f --tail=100
    fi
}

# ============================================================
# 命令: update（拉取代码 + 备份 + 迁移 + 重建 + 重启）
# ============================================================
cmd_update() {
    ensure_docker
    header "更新部署"
    local with_files_backup=false

    while [ $# -gt 0 ]; do
        case "$1" in
            --with-files-backup)
                with_files_backup=true
                ;;
            *)
                warn "忽略未知参数: $1"
                ;;
        esac
        shift
    done

    cd "$PROJECT_DIR"
    ensure_backup_dir_writable

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)

    info "更新前自动备份数据库和 .env ..."
    backup_db "$timestamp"
    backup_env_file "$timestamp"

    if $with_files_backup; then
        warn "已启用文件存储备份，这一步可能耗时较长并占用较多空间"
        backup_file_storage "$timestamp"
    else
        info "未启用文件存储备份（如需备份文件，请使用: bash deploy.sh update --with-files-backup）"
    fi

    cleanup_old_backups

    # 如果有 git 仓库，先拉取
    if [ -d ".git" ]; then
        info "拉取最新代码..."
        git pull
        success "代码更新完成"
    fi

    info "重新构建镜像..."
    docker compose build

    info "先执行数据库迁移..."
    step_run_migrations

    info "滚动重启服务..."
    docker compose up -d

    success "更新完成"
    sleep 5
    check_all_services
}

# ============================================================
# 命令: backup
# ============================================================
cmd_backup() {
    header "数据备份"
    local with_files_backup=false

    while [ $# -gt 0 ]; do
        case "$1" in
            --with-files-backup)
                with_files_backup=true
                ;;
            *)
                warn "忽略未知参数: $1"
                ;;
        esac
        shift
    done

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    ensure_backup_dir_writable

    backup_db "$timestamp"
    backup_env_file "$timestamp"

    if $with_files_backup; then
        warn "已启用文件存储备份，这一步可能耗时较长并占用较多空间"
        backup_file_storage "$timestamp"
    else
        info "本次仅备份数据库和 .env（如需备份文件，请使用: bash deploy.sh backup --with-files-backup）"
    fi

    cleanup_old_backups

    success "备份完成: $BACKUP_DIR"
}

# ============================================================
# 命令: clean（完全清理）
# ============================================================
cmd_clean() {
    header "⚠️  完全清理"
    echo -e "${RED}${BOLD}  警告: 这将删除所有容器、镜像和数据卷！${NC}"
    echo -e "${RED}${BOLD}  所有数据（数据库、文件、搜索索引）将永久丢失！${NC}"
    echo ""
    read -p "  确认清理? 输入 YES 继续: " confirm

    if [ "$confirm" = "YES" ]; then
        cd "$PROJECT_DIR"
        docker compose down -v --rmi all
        success "清理完成"
    else
        info "已取消"
    fi
}

# ============================================================
# 帮助
# ============================================================
cmd_help() {
    echo ""
    echo -e "${CYAN}${BOLD}DeepSearch 部署管理工具 v2.0${NC}"
    echo ""
    echo -e "使用方法: ${BOLD}bash $0 <命令>${NC}"
    echo ""
    echo "  部署命令:"
    echo -e "    ${GREEN}install${NC}          一键部署（安装Docker + 生成密钥 + 构建 + 启动 + 迁移）"
    echo -e "    ${GREEN}update${NC} [--with-files-backup]  更新部署（默认先备份数据库 + .env，并自动执行迁移）"
    echo ""
    echo "  服务管理:"
    echo -e "    ${GREEN}start${NC}            启动所有服务"
    echo -e "    ${GREEN}stop${NC}             停止所有服务"
    echo -e "    ${GREEN}restart${NC} [name]   重启服务（可指定单个服务）"
    echo ""
    echo "  监控诊断:"
    echo -e "    ${GREEN}status${NC}           查看容器状态"
    echo -e "    ${GREEN}health${NC}           健康检查（验证所有 7 个服务）"
    echo -e "    ${GREEN}logs${NC} [service]   查看日志（实时跟踪）"
    echo ""
    echo "  数据管理:"
    echo -e "    ${GREEN}backup${NC} [--with-files-backup]  备份数据库 + .env（可选文件存储）"
    echo -e "    ${GREEN}clean${NC}            完全清理（⚠️ 删除所有数据！）"
    echo ""
    echo "  服务列表: frontend, backend, celery-worker, celery-beat, postgres, redis, meilisearch"
    echo ""
}

# ============================================================
# 主入口
# ============================================================
main() {
    local command="${1:-help}"
    shift 2>/dev/null || true

    case "$command" in
        install)    cmd_install ;;
        start)      cmd_start ;;
        stop)       cmd_stop ;;
        restart)    cmd_restart "$@" ;;
        status)     cmd_status ;;
        health)     cmd_health ;;
        logs)       cmd_logs "$@" ;;
        update)     cmd_update "$@" ;;
        backup)     cmd_backup "$@" ;;
        clean)      cmd_clean ;;
        help|-h|--help) cmd_help ;;
        *)
            error "未知命令: $command"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
