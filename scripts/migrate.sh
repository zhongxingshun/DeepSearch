#!/bin/bash
# DeepSearch 数据迁移脚本
# 版本: v1.0
# 用于从 NAS 迁移文件到本地服务器

set -e

# 配置
SOURCE_DIR="${SOURCE_DIR:-/mnt/nas/documents}"
TARGET_DIR="${TARGET_DIR:-/data/files}"
LOG_FILE="/var/log/deepsearch/migrate.log"
CHECKSUM_FILE="/data/backups/migration_checksums.txt"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[${timestamp}] [${level}] ${message}" | tee -a ${LOG_FILE}
}

log_info() { log "INFO" "${GREEN}$1${NC}"; }
log_warn() { log "WARN" "${YELLOW}$1${NC}"; }
log_error() { log "ERROR" "${RED}$1${NC}"; }

# ============================================
# 预检查
# ============================================
pre_check() {
    log_info "Running pre-migration checks..."
    
    # 检查源目录
    if [ ! -d "${SOURCE_DIR}" ]; then
        log_error "Source directory not found: ${SOURCE_DIR}"
        exit 1
    fi
    
    # 检查目标目录
    if [ ! -d "${TARGET_DIR}" ]; then
        log_info "Creating target directory: ${TARGET_DIR}"
        mkdir -p ${TARGET_DIR}
    fi
    
    # 检查磁盘空间
    AVAILABLE_SPACE=$(df -BG ${TARGET_DIR} | awk 'NR==2 {print $4}' | tr -d 'G')
    SOURCE_SIZE=$(du -sG ${SOURCE_DIR} 2>/dev/null | cut -f1 || echo "unknown")
    
    log_info "Source size: ${SOURCE_SIZE}G"
    log_info "Available space: ${AVAILABLE_SPACE}G"
    
    if [ "${SOURCE_SIZE}" != "unknown" ] && [ ${AVAILABLE_SPACE} -lt ${SOURCE_SIZE} ]; then
        log_error "Not enough disk space!"
        exit 1
    fi
    
    log_info "Pre-check passed"
}

# ============================================
# 执行迁移
# ============================================
run_migration() {
    log_info "Starting file migration..."
    log_info "Source: ${SOURCE_DIR}"
    log_info "Target: ${TARGET_DIR}"
    
    # 使用 rsync 进行增量同步
    rsync -avz \
        --progress \
        --stats \
        --human-readable \
        --partial \
        --timeout=600 \
        --exclude='*.tmp' \
        --exclude='~*' \
        --exclude='.DS_Store' \
        --exclude='Thumbs.db' \
        ${SOURCE_DIR}/ ${TARGET_DIR}/
    
    if [ $? -eq 0 ]; then
        log_info "Migration completed successfully"
    else
        log_error "Migration failed with errors"
        exit 1
    fi
}

# ============================================
# 校验文件完整性
# ============================================
verify_migration() {
    log_info "Verifying file integrity..."
    
    # 统计文件数量
    SOURCE_COUNT=$(find ${SOURCE_DIR} -type f | wc -l)
    TARGET_COUNT=$(find ${TARGET_DIR} -type f | wc -l)
    
    log_info "Source file count: ${SOURCE_COUNT}"
    log_info "Target file count: ${TARGET_COUNT}"
    
    if [ ${SOURCE_COUNT} -eq ${TARGET_COUNT} ]; then
        log_info "File count verification: PASSED"
    else
        log_warn "File count mismatch! Please check."
    fi
    
    # 可选: 计算校验和 (耗时较长)
    if [ "${VERIFY_CHECKSUM}" = "true" ]; then
        log_info "Computing checksums (this may take a while)..."
        find ${TARGET_DIR} -type f -exec md5sum {} \; > ${CHECKSUM_FILE}
        log_info "Checksums saved to: ${CHECKSUM_FILE}"
    fi
}

# ============================================
# 生成迁移报告
# ============================================
generate_report() {
    log_info "Generating migration report..."
    
    REPORT_FILE="/data/backups/migration_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > ${REPORT_FILE} << EOF
========================================
DeepSearch 数据迁移报告
========================================
迁移时间: $(date)
源目录: ${SOURCE_DIR}
目标目录: ${TARGET_DIR}

文件统计:
- 源文件数: $(find ${SOURCE_DIR} -type f | wc -l)
- 目标文件数: $(find ${TARGET_DIR} -type f | wc -l)
- 总大小: $(du -sh ${TARGET_DIR} | cut -f1)

文件类型分布:
$(find ${TARGET_DIR} -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20)

========================================
EOF
    
    log_info "Report saved to: ${REPORT_FILE}"
    cat ${REPORT_FILE}
}

# ============================================
# 使用说明
# ============================================
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --source DIR    Source directory (default: /mnt/nas/documents)"
    echo "  --target DIR    Target directory (default: /data/files)"
    echo "  --verify        Verify checksums after migration"
    echo "  --dry-run       Show what would be done without making changes"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --source /mnt/nas/docs --target /data/files"
    echo "  $0 --verify"
}

# ============================================
# 参数解析
# ============================================
VERIFY_CHECKSUM="false"
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        --target)
            TARGET_DIR="$2"
            shift 2
            ;;
        --verify)
            VERIFY_CHECKSUM="true"
            shift
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# ============================================
# 主函数
# ============================================
main() {
    mkdir -p $(dirname ${LOG_FILE})
    
    log_info "=========================================="
    log_info "DeepSearch Data Migration Started"
    log_info "=========================================="
    
    pre_check
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "DRY RUN mode - showing what would be done:"
        rsync -avzn ${SOURCE_DIR}/ ${TARGET_DIR}/
    else
        run_migration
        verify_migration
        generate_report
    fi
    
    log_info "=========================================="
    log_info "DeepSearch Data Migration Completed"
    log_info "=========================================="
}

# 执行
main "$@"
