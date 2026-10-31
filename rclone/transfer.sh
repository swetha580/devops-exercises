#!/usr/bin/env bash
# ==============================================================================
# Script Name: transfer.sh
# Purpose: Reusable, configuration-free file transfer automation using rclone.
# Supports: copy and sync operations, progress stats, logging, and error handling.
# ==============================================================================

set -o pipefail

LOG_FILE="${TRANSFER_LOG_FILE:-transfer.log}"
OPERATION="${3:-copy}"
SOURCE="$1"
DEST="$2"

RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

usage() {
    echo -e "${YELLOW}Usage:${NC} $0 <source> <destination> [operation: copy|sync]"
    echo ""
    echo "Examples:"
    echo "  $0 ./source_dir ./dest_dir copy"
    echo "  $0 ./source_dir LOCALMINIO:testpress-bucket/docs sync"
    exit 1
}

if [[ -z "${SOURCE}" || -z "${DEST}" ]]; then
    log "ERROR" "Missing required arguments: source and destination."
    usage
fi

if [[ "${OPERATION}" != "copy" && "${OPERATION}" != "sync" ]]; then
    log "ERROR" "Unsupported operation: ${OPERATION}. Allowed: copy, sync"
    usage
fi

log "INFO" "=========================================================="
log "INFO" "Starting ${OPERATION^^} operation from [${SOURCE}] to [${DEST}]"
log "INFO" "Logging to: ${LOG_FILE}"

if [[ "${OPERATION}" == "sync" ]]; then
    log "WARN" "Sync requested. Performing safety --dry-run check for deletions..."
    rclone sync "${SOURCE}" "${DEST}" --dry-run --config /dev/null 2>&1 | tee -a "${LOG_FILE}" | grep -E "NOTICE.*delete|Skipped delete" || true
fi

rclone "${OPERATION}" "${SOURCE}" "${DEST}" \
    --config /dev/null \
    --progress \
    --stats 2s \
    --transfers 4 \
    --retries 3 \
    --low-level-retries 10 \
    2>&1 | tee -a "${LOG_FILE}"

EXIT_CODE=$?

if [[ ${EXIT_CODE} -eq 0 ]]; then
    log "SUCCESS" "${OPERATION^^} completed successfully without errors."
    exit 0
else
    log "ERROR" "${OPERATION^^} failed with exit code ${EXIT_CODE}."
    exit ${EXIT_CODE}
fi
