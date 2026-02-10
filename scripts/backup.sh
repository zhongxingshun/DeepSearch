#!/bin/bash
# DeepSearch 备份脚本
# 版本: v1.0

set -e

# 配置
BACKUP_DIR="/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 创建备份目录
mkdir -p ${BACKUP_DIR}/postgres
mkdir -p ${BACKUP_DIR}/meilisearch
mkdir -p ${BACKUP_DIR}/config

# ============================================
# PostgreSQL 备份
# ============================================
backup_postgres() {
    log_info "Starting PostgreSQL backup..."
    
    PGDUMP_FILE="${BACKUP_DIR}/postgres/pg_full_${DATE}.sql.gz"
    
    docker exec deepsearch-postgres pg_dump \
        -U ${DB_USER:-deepsearch} \
        -d ${DB_NAME:-deepsearch} \
        --no-owner \
        --no-privileges \
        | gzip > ${PGDUMP_FILE}
    
    if [ $? -eq 0 ]; then
        log_info "PostgreSQL backup completed: ${PGDUMP_FILE}"
        log_info "File size: $(du -h ${PGDUMP_FILE} | cut -f1)"
    else
        log_error "PostgreSQL backup failed!"
        exit 1
    fi
}

# ============================================
# Meilisearch 快照
# ============================================
backup_meilisearch() {
    log_info "Starting Meilisearch snapshot..."
    
    MEILI_HOST=${MEILI_HOST:-localhost}
    MEILI_PORT=${MEILI_PORT:-7700}
    MEILI_KEY=${MEILI_MASTER_KEY:-deepsearch_meili_key}
    
    # 触发快照
    curl -s -X POST "http://${MEILI_HOST}:${MEILI_PORT}/snapshots" \
        -H "Authorization: Bearer ${MEILI_KEY}" \
        -H "Content-Type: application/json"
    
    if [ $? -eq 0 ]; then
        log_info "Meilisearch snapshot triggered"
    else
        log_warn "Meilisearch snapshot may have failed"
    fi
}

# ============================================
# 配置文件备份
# ============================================
backup_config() {
    log_info "Starting config backup..."
    
    CONFIG_FILE="${BACKUP_DIR}/config/config_${DATE}.tar.gz"
    
    tar -czf ${CONFIG_FILE} \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='node_modules' \
        -C /app \
        .env \
        docker-compose.yml \
        nginx/ \
        2>/dev/null || true
    
    log_info "Config backup completed: ${CONFIG_FILE}"
}

# ============================================
# 清理旧备份
# ============================================
cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    # 清理 PostgreSQL 备份
    find ${BACKUP_DIR}/postgres -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    
    # 清理配置备份
    find ${BACKUP_DIR}/config -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    
    log_info "Cleanup completed"
}

# ============================================
# 主函数
# ============================================
main() {
    log_info "=========================================="
    log_info "DeepSearch Backup Started: $(date)"
    log_info "=========================================="
    
    backup_postgres
    backup_meilisearch
    backup_config
    cleanup_old_backups
    
    log_info "=========================================="
    log_info "DeepSearch Backup Completed: $(date)"
    log_info "=========================================="
}

# 执行
main "$@"
