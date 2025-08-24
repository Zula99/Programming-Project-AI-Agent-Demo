#!/bin/bash

# Norconex Crawler Helper Script
# This script helps manage crawling operations from within the container

NORCONEX_HOME="/opt/norconex"
CONFIGS_DIR="/opt/norconex/configs"
DATA_DIR="/opt/norconex/data"

# Function to start a crawl
start_crawl() {
    local config_file="$1"
    local crawler_id="$2"
    
    if [ -z "$config_file" ]; then
        echo "Usage: start_crawl <config-file> [crawler-id]"
        return 1
    fi
    
    if [ ! -f "${CONFIGS_DIR}/${config_file}" ]; then
        echo "Error: Configuration file '${config_file}' not found in ${CONFIGS_DIR}"
        return 1
    fi
    
    echo "Starting crawl with configuration: ${config_file}"
    
    if [ -n "$crawler_id" ]; then
        cd "$NORCONEX_HOME" && ./collector-http.sh start -config="${CONFIGS_DIR}/${config_file}" -crawler="${crawler_id}"
    else
        cd "$NORCONEX_HOME" && ./collector-http.sh start -config="${CONFIGS_DIR}/${config_file}"
    fi
}

# Function to stop a crawl
stop_crawl() {
    local config_file="$1"
    local crawler_id="$2"
    
    if [ -z "$config_file" ]; then
        echo "Usage: stop_crawl <config-file> [crawler-id]"
        return 1
    fi
    
    echo "Stopping crawl with configuration: ${config_file}"
    
    if [ -n "$crawler_id" ]; then
        cd "$NORCONEX_HOME" && ./crawler-web.sh stop -config="${CONFIGS_DIR}/${config_file}" -crawler="${crawler_id}"
    else
        cd "$NORCONEX_HOME" && ./crawler-web.sh stop -config="${CONFIGS_DIR}/${config_file}"
    fi
}

# Function to check crawl status
status_crawl() {
    local config_file="$1"
    
    if [ -z "$config_file" ]; then
        echo "Usage: status_crawl <config-file>"
        return 1
    fi
    
    echo "Checking status for configuration: ${config_file}"
    cd "$NORCONEX_HOME" && ./crawler-web.sh status -config="${CONFIGS_DIR}/${config_file}"
}

# Function to clean crawl data
clean_crawl() {
    local config_file="$1"
    
    if [ -z "$config_file" ]; then
        echo "Usage: clean_crawl <config-file>"
        return 1
    fi
    
    echo "Cleaning crawl data for configuration: ${config_file}"
    cd "$NORCONEX_HOME" && ./crawler-web.sh clean -config="${CONFIGS_DIR}/${config_file}"
}

# Function to list available configurations
list_configs() {
    echo "Available configuration files:"
    ls -la "${CONFIGS_DIR}"/*.xml 2>/dev/null || echo "No XML configuration files found in ${CONFIGS_DIR}"
}

# Function to show logs
show_logs() {
    local config_name="$1"
    
    if [ -z "$config_name" ]; then
        echo "Usage: show_logs <config-name>"
        echo "Available log directories:"
        ls -la "${DATA_DIR}/logs/" 2>/dev/null || echo "No log directories found"
        return 1
    fi
    
    local log_dir="${DATA_DIR}/logs/${config_name}"
    
    if [ -d "$log_dir" ]; then
        echo "Recent log entries for ${config_name}:"
        tail -n 50 "${log_dir}/"*.log 2>/dev/null || echo "No log files found in ${log_dir}"
    else
        echo "Log directory not found: ${log_dir}"
    fi
}

# Main script logic
case "$1" in
    "start")
        start_crawl "$2" "$3"
        ;;
    "stop")
        stop_crawl "$2" "$3"
        ;;
    "status")
        status_crawl "$2"
        ;;
    "clean")
        clean_crawl "$2"
        ;;
    "list")
        list_configs
        ;;
    "logs")
        show_logs "$2"
        ;;
    *)
        echo "Norconex Crawler Helper Script"
        echo ""
        echo "Usage: $0 <command> [arguments]"
        echo ""
        echo "Commands:"
        echo "  start <config-file> [crawler-id]  - Start a crawl"
        echo "  stop <config-file> [crawler-id]   - Stop a crawl"
        echo "  status <config-file>              - Check crawl status"
        echo "  clean <config-file>               - Clean crawl data"
        echo "  list                              - List available configs"
        echo "  logs <config-name>                - Show recent logs"
        echo ""
        echo "Examples:"
        echo "  $0 start web-crawl-config.xml"
        echo "  $0 status web-crawl-config.xml"
        echo "  $0 logs WebCrawler"
        echo ""
        ;;
esac