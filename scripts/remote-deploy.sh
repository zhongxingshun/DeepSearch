#!/bin/bash
# ============================================================
# DeepSearch 远程一键部署脚本
# 用法:
#   bash scripts/remote-deploy.sh              # 完整部署（同步代码+重建+重启）
#   bash scripts/remote-deploy.sh sync         # 仅同步代码
#   bash scripts/remote-deploy.sh restart      # 仅重启服务
#   bash scripts/remote-deploy.sh logs         # 查看日志
#   bash scripts/remote-deploy.sh status       # 查看状态
# ============================================================

set -e

# ========== 配置（按需修改） ==========
REMOTE_HOST="192.168.10.65"
REMOTE_USER="akuvox"
REMOTE_PASS="Akuvox@2025"
REMOTE_DIR="/home/akuvox/DeepSearch"

# ========== 颜色 ==========
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

RSYNC_SSH="sshpass -p '${REMOTE_PASS}' ssh -o StrictHostKeyChecking=no"

# ========== 检查 sshpass ==========
check_deps() {
    if ! command -v sshpass &>/dev/null; then
        error "请先安装 sshpass: brew install sshpass 或 apt install sshpass"
        exit 1
    fi
}

# ========== 同步代码 ==========
sync_code() {
    info "同步代码到 ${REMOTE_HOST}:${REMOTE_DIR} ..."
    sshpass -p "${REMOTE_PASS}" ssh -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}" \
        "mkdir -p '${REMOTE_DIR}'"
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
        --exclude '.claude' \
        -e "${RSYNC_SSH}" \
        "${PROJECT_DIR}/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"
    success "代码同步完成"
}

# ========== 远程执行 ==========
remote_exec() {
    sshpass -p "${REMOTE_PASS}" ssh -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}" "$1"
}

# ========== 重建并重启 ==========
rebuild() {
    info "重建 Docker 镜像..."
    remote_exec "cd ${REMOTE_DIR} && docker compose build --parallel"
    success "镜像重建完成"

    info "重启服务..."
    remote_exec "cd ${REMOTE_DIR} && docker compose up -d"
    success "服务已重启"
}

# ========== 完整部署 ==========
full_deploy() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════${NC}"
    echo -e "${CYAN}  DeepSearch 远程部署${NC}"
    echo -e "${CYAN}  目标: ${REMOTE_USER}@${REMOTE_HOST}${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}"
    echo ""

    sync_code
    rebuild

    info "等待服务启动 (15s)..."
    sleep 15

    show_status
    echo ""
    success "部署完成! 访问 http://${REMOTE_HOST}:3200"
    echo ""
}

# ========== 查看状态 ==========
show_status() {
    info "服务状态:"
    remote_exec "cd ${REMOTE_DIR} && docker compose ps --format 'table {{.Name}}\t{{.Status}}'"
}

# ========== 查看日志 ==========
show_logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        remote_exec "docker logs --tail 50 deepsearch-${service}"
    else
        remote_exec "cd ${REMOTE_DIR} && docker compose logs --tail 50"
    fi
}

# ========== 主入口 ==========
check_deps

case "${1:-deploy}" in
    deploy|"")  full_deploy ;;
    sync)       sync_code ;;
    rebuild)    rebuild ;;
    restart)    remote_exec "cd ${REMOTE_DIR} && docker compose restart" && success "已重启" ;;
    status)     show_status ;;
    logs)       show_logs "$2" ;;
    stop)       remote_exec "cd ${REMOTE_DIR} && docker compose down" && success "已停止" ;;
    *)
        echo "用法: bash $0 [命令]"
        echo ""
        echo "  deploy   完整部署: 同步代码 + 重建镜像 + 重启 (默认)"
        echo "  sync     仅同步代码"
        echo "  rebuild  仅重建镜像并重启"
        echo "  restart  仅重启服务"
        echo "  status   查看服务状态"
        echo "  logs     查看日志 (可指定: backend, frontend, celery-worker)"
        echo "  stop     停止所有服务"
        ;;
esac
