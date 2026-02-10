#!/bin/bash
# ==============================================================================
# DeepSearch 服务管理脚本
# 用法: ./services.sh [命令] [服务名]
#
# 命令:
#   start   [服务名|all]   启动服务
#   stop    [服务名|all]   停止服务
#   restart [服务名|all]   重启服务
#   status                 查看所有服务状态
#   reset                  清空所有数据（文件/数据库/索引/队列）
#   logs    [服务名]       查看服务日志
#
# 服务名:
#   docker    - Docker 基础设施 (PostgreSQL, Redis, Meilisearch)
#   backend   - 后端 API (Uvicorn, port 8200)
#   celery    - Celery Worker (异步任务处理)
#   frontend  - 前端 (Vite, port 3200)
#   all       - 以上全部 (默认)
#
# 示例:
#   ./services.sh start              # 启动所有服务
#   ./services.sh start backend      # 只启动后端
#   ./services.sh restart celery     # 重启 Celery
#   ./services.sh stop all           # 停止所有服务
#   ./services.sh status             # 查看状态
#   ./services.sh reset              # 清空数据
#   ./services.sh logs celery        # 查看 Celery 日志
# ==============================================================================

set -e

# ─── 项目路径配置 ───
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="${PROJECT_DIR}/backend"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
VENV_DIR="${BACKEND_DIR}/.venv"
LOG_DIR="${PROJECT_DIR}/logs"

# ─── 服务参数 ───
BACKEND_PORT=8200
FRONTEND_PORT=3200
CELERY_CONCURRENCY=1

# ─── 颜色 ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ─── 初始化 ───
mkdir -p "${LOG_DIR}"

# ==============================================================================
# 工具函数
# ==============================================================================

log_info()  { echo -e "${GREEN}[✅ INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[⚠️  WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[❌ ERROR]${NC} $1"; }
log_title() { echo -e "\n${CYAN}═══════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════${NC}"; }

activate_venv() {
    if [ -f "${VENV_DIR}/bin/activate" ]; then
        source "${VENV_DIR}/bin/activate"
    else
        log_error "虚拟环境不存在: ${VENV_DIR}"
        exit 1
    fi
}

check_port() {
    local port=$1
    lsof -ti:${port} >/dev/null 2>&1
}

kill_port() {
    local port=$1
    local pids=$(lsof -ti:${port} 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

# ==============================================================================
# Docker 服务
# ==============================================================================

start_docker() {
    log_info "启动 Docker 基础设施 (PostgreSQL, Redis, Meilisearch)..."
    cd "${PROJECT_DIR}"
    docker compose -f docker-compose.dev.yml up -d
    
    # 等待健康检查通过
    log_info "等待服务就绪..."
    local retries=0
    while [ $retries -lt 30 ]; do
        local pg_ok=$(docker inspect --format='{{.State.Health.Status}}' deepsearch-dev-postgres 2>/dev/null)
        local redis_ok=$(docker inspect --format='{{.State.Health.Status}}' deepsearch-dev-redis 2>/dev/null)
        local meili_ok=$(docker inspect --format='{{.State.Health.Status}}' deepsearch-dev-meilisearch 2>/dev/null)
        
        if [ "$pg_ok" = "healthy" ] && [ "$redis_ok" = "healthy" ] && [ "$meili_ok" = "healthy" ]; then
            log_info "Docker 服务全部就绪 ✅"
            return 0
        fi
        sleep 1
        retries=$((retries + 1))
    done
    log_warn "Docker 服务可能未完全就绪，请手动检查"
}

stop_docker() {
    log_info "停止 Docker 基础设施..."
    cd "${PROJECT_DIR}"
    docker compose -f docker-compose.dev.yml down
    log_info "Docker 服务已停止"
}

# ==============================================================================
# Backend (Uvicorn)
# ==============================================================================

start_backend() {
    if check_port ${BACKEND_PORT}; then
        log_warn "后端已在运行 (port ${BACKEND_PORT})，跳过"
        return 0
    fi
    
    log_info "启动后端 API (port ${BACKEND_PORT})..."
    activate_venv
    cd "${BACKEND_DIR}"
    
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    nohup python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${BACKEND_PORT} \
        > "${LOG_DIR}/backend.log" 2>&1 &
    
    local pid=$!
    echo $pid > "${LOG_DIR}/backend.pid"
    
    # 等待启动
    local retries=0
    while [ $retries -lt 15 ]; do
        if curl -s -o /dev/null http://localhost:${BACKEND_PORT}/docs 2>/dev/null; then
            log_info "后端 API 启动成功 (PID: ${pid}) ✅"
            return 0
        fi
        sleep 1
        retries=$((retries + 1))
    done
    log_error "后端 API 启动超时，查看日志: ${LOG_DIR}/backend.log"
}

stop_backend() {
    log_info "停止后端 API..."
    if [ -f "${LOG_DIR}/backend.pid" ]; then
        local pid=$(cat "${LOG_DIR}/backend.pid")
        kill $pid 2>/dev/null && sleep 1
        rm -f "${LOG_DIR}/backend.pid"
    fi
    kill_port ${BACKEND_PORT}
    log_info "后端 API 已停止"
}

# ==============================================================================
# Celery Worker
# ==============================================================================

start_celery() {
    if pgrep -f "celery.*worker" >/dev/null 2>&1; then
        log_warn "Celery Worker 已在运行，跳过"
        return 0
    fi
    
    log_info "启动 Celery Worker (concurrency=${CELERY_CONCURRENCY})..."
    activate_venv
    cd "${BACKEND_DIR}"
    
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    nohup celery -A app.tasks.celery_app worker \
        --loglevel=info \
        --concurrency=${CELERY_CONCURRENCY} \
        -Q default,parse,index,low,maintenance \
        > "${LOG_DIR}/celery.log" 2>&1 &
    
    local pid=$!
    echo $pid > "${LOG_DIR}/celery.pid"
    
    # 等待启动
    sleep 3
    if pgrep -f "celery.*worker" >/dev/null 2>&1; then
        log_info "Celery Worker 启动成功 (PID: ${pid}) ✅"
    else
        log_error "Celery Worker 启动失败，查看日志: ${LOG_DIR}/celery.log"
    fi
}

stop_celery() {
    log_info "停止 Celery Worker..."
    if [ -f "${LOG_DIR}/celery.pid" ]; then
        local pid=$(cat "${LOG_DIR}/celery.pid")
        kill $pid 2>/dev/null && sleep 1
        rm -f "${LOG_DIR}/celery.pid"
    fi
    pkill -9 -f "celery.*worker" 2>/dev/null || true
    sleep 1
    log_info "Celery Worker 已停止"
}

# ==============================================================================
# Frontend (Vite)
# ==============================================================================

start_frontend() {
    if check_port ${FRONTEND_PORT}; then
        log_warn "前端已在运行 (port ${FRONTEND_PORT})，跳过"
        return 0
    fi
    
    log_info "启动前端 (port ${FRONTEND_PORT})..."
    cd "${FRONTEND_DIR}"
    
    nohup npx vite --port ${FRONTEND_PORT} --host \
        > "${LOG_DIR}/frontend.log" 2>&1 &
    
    local pid=$!
    echo $pid > "${LOG_DIR}/frontend.pid"
    
    # 等待启动
    local retries=0
    while [ $retries -lt 10 ]; do
        if curl -s -o /dev/null http://localhost:${FRONTEND_PORT}/ 2>/dev/null; then
            log_info "前端启动成功 (PID: ${pid}) ✅"
            return 0
        fi
        sleep 1
        retries=$((retries + 1))
    done
    log_error "前端启动超时，查看日志: ${LOG_DIR}/frontend.log"
}

stop_frontend() {
    log_info "停止前端..."
    if [ -f "${LOG_DIR}/frontend.pid" ]; then
        local pid=$(cat "${LOG_DIR}/frontend.pid")
        kill $pid 2>/dev/null && sleep 1
        rm -f "${LOG_DIR}/frontend.pid"
    fi
    kill_port ${FRONTEND_PORT}
    log_info "前端已停止"
}

# ==============================================================================
# 组合操作
# ==============================================================================

start_all() {
    log_title "启动所有 DeepSearch 服务"
    start_docker
    start_backend
    start_celery
    start_frontend
    echo ""
    show_status
}

stop_all() {
    log_title "停止所有 DeepSearch 服务"
    stop_frontend
    stop_celery
    stop_backend
    stop_docker
    log_info "所有服务已停止"
}

restart_service() {
    local service=$1
    case $service in
        docker)   stop_docker   && start_docker   ;;
        backend)  stop_backend  && start_backend  ;;
        celery)   stop_celery   && start_celery   ;;
        frontend) stop_frontend && start_frontend ;;
        all|"")   stop_all      && start_all      ;;
        *) log_error "未知服务: $service"; usage ;;
    esac
}

start_service() {
    local service=$1
    case $service in
        docker)   start_docker   ;;
        backend)  start_backend  ;;
        celery)   start_celery   ;;
        frontend) start_frontend ;;
        all|"")   start_all      ;;
        *) log_error "未知服务: $service"; usage ;;
    esac
}

stop_service() {
    local service=$1
    case $service in
        docker)   stop_docker   ;;
        backend)  stop_backend  ;;
        celery)   stop_celery   ;;
        frontend) stop_frontend ;;
        all|"")   stop_all      ;;
        *) log_error "未知服务: $service"; usage ;;
    esac
}

# ==============================================================================
# 状态检查
# ==============================================================================

show_status() {
    log_title "DeepSearch 服务状态"
    
    printf "${BLUE}%-20s %-8s %-10s %-30s${NC}\n" "服务" "端口" "状态" "地址"
    printf "%-20s %-8s %-10s %-30s\n" "────────────────────" "────────" "──────────" "──────────────────────────────"
    
    # PostgreSQL
    local pg_status="❌ 未运行"
    if docker inspect --format='{{.State.Health.Status}}' deepsearch-dev-postgres 2>/dev/null | grep -q healthy; then
        pg_status="✅ healthy"
    fi
    printf "%-20s %-8s %-10s %-30s\n" "PostgreSQL" "5434" "$pg_status" "Docker"
    
    # Redis
    local redis_status="❌ 未运行"
    if docker inspect --format='{{.State.Health.Status}}' deepsearch-dev-redis 2>/dev/null | grep -q healthy; then
        redis_status="✅ healthy"
    fi
    printf "%-20s %-8s %-10s %-30s\n" "Redis" "6381" "$redis_status" "Docker"
    
    # Meilisearch
    local meili_status="❌ 未运行"
    if docker inspect --format='{{.State.Health.Status}}' deepsearch-dev-meilisearch 2>/dev/null | grep -q healthy; then
        meili_status="✅ healthy"
    fi
    printf "%-20s %-8s %-10s %-30s\n" "Meilisearch" "7700" "$meili_status" "Docker"
    
    # Backend
    local backend_status="❌ 未运行"
    local backend_addr=""
    if check_port ${BACKEND_PORT}; then
        if curl -s -o /dev/null http://localhost:${BACKEND_PORT}/docs 2>/dev/null; then
            backend_status="✅ 运行中"
            backend_addr="http://localhost:${BACKEND_PORT}"
        else
            backend_status="⚠️  端口占用"
        fi
    fi
    printf "%-20s %-8s %-10s %-30s\n" "Backend (FastAPI)" "$BACKEND_PORT" "$backend_status" "$backend_addr"
    
    # Celery
    local celery_status="❌ 未运行"
    local celery_workers=$(pgrep -f "celery.*worker" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$celery_workers" -gt 0 ]; then
        celery_status="✅ ${celery_workers} 进程"
    fi
    printf "%-20s %-8s %-10s %-30s\n" "Celery Worker" "-" "$celery_status" "concurrency=${CELERY_CONCURRENCY}"
    
    # Frontend
    local frontend_status="❌ 未运行"
    local frontend_addr=""
    if check_port ${FRONTEND_PORT}; then
        if curl -s -o /dev/null http://localhost:${FRONTEND_PORT}/ 2>/dev/null; then
            frontend_status="✅ 运行中"
            frontend_addr="http://localhost:${FRONTEND_PORT}"
        else
            frontend_status="⚠️  端口占用"
        fi
    fi
    printf "%-20s %-8s %-10s %-30s\n" "Frontend (Vite)" "$FRONTEND_PORT" "$frontend_status" "$frontend_addr"
    
    echo ""
}

# ==============================================================================
# 数据重置
# ==============================================================================

reset_data() {
    log_title "重置所有数据"
    
    echo -e "${RED}⚠️  警告: 此操作将清空所有上传的文件、数据库记录和搜索索引！${NC}"
    read -p "确认执行? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "已取消"
        return 0
    fi
    
    activate_venv
    cd "${BACKEND_DIR}"
    
    python3 -c "
import psycopg2, requests, shutil, os, redis, time

# 1. 文件存储
shutil.rmtree('data/files', ignore_errors=True)
os.makedirs('data/files', exist_ok=True)
print('✅ 文件存储已清空')

# 2. 数据库
conn = psycopg2.connect(host='localhost', port=5434, dbname='deepsearch', user='deepsearch', password='deepsearch123')
conn.autocommit = True
cur = conn.cursor()
for t in ['tasks','files','search_history']:
    cur.execute(f'TRUNCATE TABLE {t} CASCADE')
cur.close(); conn.close()
print('✅ 数据库已清空')

# 3. Meilisearch
H = {'Authorization':'Bearer deepsearch_meili_key','Content-Type':'application/json'}
requests.delete('http://localhost:7700/indexes/documents', headers=H); time.sleep(1)
requests.post('http://localhost:7700/indexes', headers=H, json={'uid':'documents','primaryKey':'id'}); time.sleep(1)
requests.put('http://localhost:7700/indexes/documents/settings/searchable-attributes', headers=H, json=['content','filename','keywords'])
requests.put('http://localhost:7700/indexes/documents/settings/filterable-attributes', headers=H, json=['file_type','filename'])
print('✅ 搜索索引已重建')

# 4. Redis
redis.Redis(host='localhost', port=6381).flushdb()
print('✅ Redis 队列已清空')

print('')
print('🧹 全部数据已重置！')
"
}

# ==============================================================================
# 日志查看
# ==============================================================================

show_logs() {
    local service=$1
    local log_file=""
    
    case $service in
        backend)  log_file="${LOG_DIR}/backend.log"  ;;
        celery)   log_file="${LOG_DIR}/celery.log"   ;;
        frontend) log_file="${LOG_DIR}/frontend.log"  ;;
        docker)   docker compose -f "${PROJECT_DIR}/docker-compose.dev.yml" logs --tail=50; return ;;
        *)        log_error "请指定服务名: backend, celery, frontend, docker"; return 1 ;;
    esac
    
    if [ -f "$log_file" ]; then
        tail -f "$log_file"
    else
        log_error "日志文件不存在: $log_file"
    fi
}

# ==============================================================================
# 帮助信息
# ==============================================================================

usage() {
    echo ""
    echo -e "${CYAN}DeepSearch 服务管理脚本${NC}"
    echo ""
    echo "用法: $0 <命令> [服务名]"
    echo ""
    echo "命令:"
    echo "  start   [服务名]  启动服务 (默认 all)"
    echo "  stop    [服务名]  停止服务 (默认 all)"
    echo "  restart [服务名]  重启服务 (默认 all)"
    echo "  status            查看所有服务状态"
    echo "  reset             清空所有数据"
    echo "  logs    <服务名>  查看服务日志 (tail -f)"
    echo ""
    echo "服务名:"
    echo "  docker    Docker 基础设施 (PostgreSQL, Redis, Meilisearch)"
    echo "  backend   后端 API (Uvicorn, port ${BACKEND_PORT})"
    echo "  celery    Celery Worker"
    echo "  frontend  前端 (Vite, port ${FRONTEND_PORT})"
    echo "  all       以上全部 (默认)"
    echo ""
    echo "示例:"
    echo "  $0 start              # 启动所有服务"
    echo "  $0 start backend      # 只启动后端"
    echo "  $0 restart celery     # 重启 Celery Worker"
    echo "  $0 status             # 查看服务状态"
    echo "  $0 reset              # 清空所有数据"
    echo "  $0 logs celery        # 查看 Celery 日志"
    echo ""
}

# ==============================================================================
# 主入口
# ==============================================================================

CMD=${1:-""}
SERVICE=${2:-"all"}

case $CMD in
    start)   start_service   "$SERVICE" ;;
    stop)    stop_service    "$SERVICE" ;;
    restart) restart_service "$SERVICE" ;;
    status)  show_status ;;
    reset)   reset_data ;;
    logs)    show_logs "$SERVICE" ;;
    *)       usage ;;
esac
