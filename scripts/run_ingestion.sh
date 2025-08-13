#!/bin/bash

# Social Media RAG - Data Ingestion Script
# This script runs periodic data ingestion from Reddit and RSS feeds

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
VENV_PATH="$PROJECT_DIR/.venv"

# Logging configuration
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
LOG_FILE="$LOG_DIR/ingestion_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        *)
            echo "[$timestamp] $message" | tee -a "$LOG_FILE"
            ;;
    esac
}

# Check if virtual environment exists and activate it
activate_venv() {
    if [ -d "$VENV_PATH" ]; then
        log "INFO" "Activating virtual environment: $VENV_PATH"
        source "$VENV_PATH/bin/activate"
    else
        log "WARN" "Virtual environment not found at $VENV_PATH"
        log "WARN" "Make sure you have created and activated your virtual environment"
    fi
}

# Check if required environment file exists
check_environment() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log "ERROR" "Environment file not found: $PROJECT_DIR/.env"
        log "ERROR" "Copy .env.example to .env and configure it first"
        exit 1
    fi
    
    log "INFO" "Environment file found"
}

# Check database connectivity
check_database() {
    log "INFO" "Checking database connectivity..."
    cd "$PROJECT_DIR"
    
    python3 -c "
import sys
import os
sys.path.append('.')
try:
    from database.schema import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute('SELECT COUNT(*) as count FROM posts').fetchone()
        print(f'Database OK - {result[0]} posts found')
except Exception as e:
    print(f'Database Error: {str(e)}')
    sys.exit(1)
" || {
        log "ERROR" "Database check failed"
        exit 1
    }
    
    log "INFO" "Database connectivity verified"
}

# Run Reddit ingestion
run_reddit_ingestion() {
    local limit=${1:-200}
    
    log "INFO" "Starting Reddit ingestion (limit: $limit per subreddit)..."
    cd "$PROJECT_DIR"
    
    python3 -m pipeline.ingest_reddit --limit "$limit" 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "INFO" "Reddit ingestion completed successfully"
        return 0
    else
        log "ERROR" "Reddit ingestion failed"
        return 1
    fi
}

# Run RSS ingestion
run_rss_ingestion() {
    local limit=${1:-50}
    
    log "INFO" "Starting RSS ingestion (limit: $limit per feed)..."
    cd "$PROJECT_DIR"
    
    python3 -m pipeline.ingest_rss --limit "$limit" 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "INFO" "RSS ingestion completed successfully"
        return 0
    else
        log "ERROR" "RSS ingestion failed"
        return 1
    fi
}

# Run trend computation
run_trend_computation() {
    log "INFO" "Starting trend computation..."
    cd "$PROJECT_DIR"
    
    python3 scripts/refresh_trends.py --verbose 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "INFO" "Trend computation completed successfully"
        return 0
    else
        log "ERROR" "Trend computation failed"
        return 1
    fi
}

# Cleanup old logs
cleanup_logs() {
    local days_to_keep=${1:-7}
    
    log "INFO" "Cleaning up log files older than $days_to_keep days..."
    
    find "$LOG_DIR" -name "ingestion_*.log" -type f -mtime +$days_to_keep -delete 2>/dev/null || true
    
    log "INFO" "Log cleanup completed"
}

# Send notification (if configured)
send_notification() {
    local status=$1
    local message=$2
    
    if [ -n "$WEBHOOK_URL" ]; then
        log "INFO" "Sending webhook notification..."
        
        curl -X POST "$WEBHOOK_URL" \
             -H "Content-Type: application/json" \
             -d "{
                 \"text\": \"Social Media RAG Ingestion: $status\",
                 \"details\": \"$message\",
                 \"timestamp\": \"$(date -Iseconds)\"
             }" \
             --silent --max-time 30 || log "WARN" "Failed to send webhook notification"
    fi
}

# Display usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -r, --reddit-limit NUM    Limit posts per subreddit (default: 200)"
    echo "  -f, --rss-limit NUM       Limit entries per RSS feed (default: 50)"
    echo "  -s, --skip-reddit         Skip Reddit ingestion"
    echo "  -S, --skip-rss            Skip RSS ingestion"
    echo "  -t, --skip-trends         Skip trend computation"
    echo "  -c, --cleanup-days NUM    Days of logs to keep (default: 7)"
    echo "  -n, --no-cleanup          Skip log cleanup"
    echo "  -v, --verbose             Enable verbose output"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  WEBHOOK_URL               Webhook URL for notifications (optional)"
    echo ""
    echo "Examples:"
    echo "  $0                        Run full ingestion with defaults"
    echo "  $0 --reddit-limit 100     Limit Reddit posts to 100 per subreddit"
    echo "  $0 --skip-reddit          Run only RSS ingestion and trends"
    echo "  $0 --verbose              Enable detailed logging"
}

# Parse command line arguments
REDDIT_LIMIT=200
RSS_LIMIT=50
SKIP_REDDIT=false
SKIP_RSS=false
SKIP_TRENDS=false
CLEANUP_DAYS=7
NO_CLEANUP=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--reddit-limit)
            REDDIT_LIMIT="$2"
            shift 2
            ;;
        -f|--rss-limit)
            RSS_LIMIT="$2"
            shift 2
            ;;
        -s|--skip-reddit)
            SKIP_REDDIT=true
            shift
            ;;
        -S|--skip-rss)
            SKIP_RSS=true
            shift
            ;;
        -t|--skip-trends)
            SKIP_TRENDS=true
            shift
            ;;
        -c|--cleanup-days)
            CLEANUP_DAYS="$2"
            shift 2
            ;;
        -n|--no-cleanup)
            NO_CLEANUP=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    local start_time=$(date +%s)
    local reddit_success=true
    local rss_success=true
    local trends_success=true
    
    log "INFO" "🚀 Starting Social Media RAG data ingestion"
    log "INFO" "Timestamp: $(date)"
    log "INFO" "Log file: $LOG_FILE"
    
    # Pre-flight checks
    check_environment
    activate_venv
    check_database
    
    # Run ingestion steps
    if [ "$SKIP_REDDIT" = false ]; then
        if ! run_reddit_ingestion "$REDDIT_LIMIT"; then
            reddit_success=false
        fi
        
        # Brief pause between ingestion types
        sleep 5
    else
        log "INFO" "Skipping Reddit ingestion"
    fi
    
    if [ "$SKIP_RSS" = false ]; then
        if ! run_rss_ingestion "$RSS_LIMIT"; then
            rss_success=false
        fi
        
        # Brief pause before trends
        sleep 5
    else
        log "INFO" "Skipping RSS ingestion"
    fi
    
    # Run trend computation if data ingestion succeeded
    if [ "$SKIP_TRENDS" = false ]; then
        if [ "$reddit_success" = true ] || [ "$rss_success" = true ]; then
            if ! run_trend_computation; then
                trends_success=false
            fi
        else
            log "WARN" "Skipping trend computation due to ingestion failures"
            trends_success=false
        fi
    else
        log "INFO" "Skipping trend computation"
    fi
    
    # Cleanup old logs
    if [ "$NO_CLEANUP" = false ]; then
        cleanup_logs "$CLEANUP_DAYS"
    fi
    
    # Calculate duration and generate report
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    echo "================================================================"
    echo "📊 INGESTION REPORT"
    echo "================================================================"
    echo "Start Time: $(date -d @$start_time)"
    echo "End Time: $(date -d @$end_time)"
    echo "Duration: ${duration} seconds"
    echo ""
    echo "Status Summary:"
    [ "$SKIP_REDDIT" = false ] && echo "  Reddit Ingestion: $([ "$reddit_success" = true ] && echo "✅ SUCCESS" || echo "❌ FAILED")"
    [ "$SKIP_RSS" = false ] && echo "  RSS Ingestion: $([ "$rss_success" = true ] && echo "✅ SUCCESS" || echo "❌ FAILED")"
    [ "$SKIP_TRENDS" = false ] && echo "  Trend Computation: $([ "$trends_success" = true ] && echo "✅ SUCCESS" || echo "❌ FAILED")"
    echo ""
    echo "Log File: $LOG_FILE"
    echo "================================================================"
    
    # Determine overall status
    if [ "$reddit_success" = true ] && [ "$rss_success" = true ] && [ "$trends_success" = true ]; then
        local overall_status="SUCCESS"
        local exit_code=0
    else
        local overall_status="PARTIAL_FAILURE"
        local exit_code=1
    fi
    
    # Send notification if configured
    send_notification "$overall_status" "Duration: ${duration}s, Reddit: $reddit_success, RSS: $rss_success, Trends: $trends_success"
    
    log "INFO" "🏁 Ingestion process completed with status: $overall_status"
    
    exit $exit_code
}

# Handle script interruption
trap 'log "ERROR" "Script interrupted"; exit 130' INT TERM

# Run main function
main "$@"
