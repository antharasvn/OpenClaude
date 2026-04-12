#!/usr/bin/env bash
# mac-system — macOS system information skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

COMMAND="${1:-help}"
shift 2>/dev/null || true

cmd_info() {
    echo "=== System Info ==="

    # Battery
    local battery
    battery=$(pmset -g batt 2>/dev/null | grep -o '[0-9]*%' | head -1 || echo "N/A")
    local charging
    charging=$(pmset -g batt 2>/dev/null | grep -o 'charging\|discharging\|AC Power\|Battery Power' | head -1 || echo "")
    echo "Battery: $battery ${charging:+(${charging})}"

    # Disk space
    echo ""
    echo "=== Disk Space ==="
    df -h / | awk 'NR==2 {printf "Root: %s used of %s (%s used)\n", $3, $2, $5}'
    df -h "$HOME" 2>/dev/null | awk 'NR==2 {printf "Home: %s used of %s (%s used)\n", $3, $2, $5}' || true

    # Memory
    echo ""
    echo "=== Memory ==="
    local total_mem
    total_mem=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0fGB\n", $1/1073741824}')
    local mem_pressure
    mem_pressure=$(memory_pressure 2>/dev/null | grep "System-wide memory free percentage" | awk '{print $NF}' || echo "N/A")
    echo "Total RAM: $total_mem"
    echo "Free memory %: $mem_pressure"

    # CPU
    echo ""
    echo "=== CPU ==="
    local cpu_usage
    cpu_usage=$(top -l 2 -n 0 2>/dev/null | grep "CPU usage" | tail -1 || echo "CPU usage: N/A")
    echo "$cpu_usage"
    local cpu_model
    cpu_model=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || system_profiler SPHardwareDataType 2>/dev/null | grep "Chip\|Processor Name" | head -1 | sed 's/.*: //')
    echo "CPU: $cpu_model"

    # Uptime
    echo ""
    echo "=== Uptime ==="
    uptime | sed 's/.*up /Up: /' | sed 's/,  [0-9]* user.*//'
}

cmd_processes() {
    echo "=== Top 10 Processes by CPU ==="
    ps aux --sort=-%cpu 2>/dev/null | head -11 | awk 'NR==1 {printf "%-8s %-5s %-5s %s\n", "USER", "%CPU", "%MEM", "COMMAND"} NR>1 {cmd=$11; if (length(cmd)>40) cmd=substr(cmd,length(cmd)-39); printf "%-8s %-5s %-5s %s\n", substr($1,1,8), $3, $4, cmd}' || \
    ps -arcwwwxo pid,pcpu,pmem,command 2>/dev/null | head -11 | awk 'NR==1 {printf "%-6s %-5s %-5s %s\n", "PID", "%CPU", "%MEM", "COMMAND"} NR>1 {cmd=$4; if (length(cmd)>50) cmd=substr(cmd,1,50); printf "%-6s %-5s %-5s %s\n", $1, $2, $3, cmd}'
}

cmd_network() {
    echo "=== Network ==="

    # WiFi SSID
    local wifi_ssid
    wifi_ssid=$(networksetup -getairportnetwork en0 2>/dev/null | sed 's/Current Wi-Fi Network: //' || echo "Not connected")
    echo "WiFi: $wifi_ssid"

    # Local IP
    local local_ip
    local_ip=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || ifconfig | grep 'inet ' | grep -v 127.0.0.1 | awk '{print $2}' | head -1 || echo "N/A")
    echo "Local IP: $local_ip"

    # Public IP (with timeout)
    local public_ip
    public_ip=$(curl --max-time 5 -s https://api.ipify.org 2>/dev/null || echo "N/A")
    echo "Public IP: $public_ip"

    # Active interfaces
    echo ""
    echo "=== Active Interfaces ==="
    ifconfig | grep -E '^[a-z]|inet ' | awk '/^[a-z]/{iface=$1} /inet /{print iface, $2}' | grep -v '127.0.0.1' | head -10
}

cmd_help() {
    echo "mac-system — macOS system information"
    echo ""
    echo "Commands:"
    echo "  info       Battery %, disk space, CPU/memory usage, uptime"
    echo "  processes  Top 10 processes by CPU"
    echo "  network    Current WiFi, IP address"
    echo "  help       Show this help"
}

case "$COMMAND" in
    info)       cmd_info ;;
    processes)  cmd_processes ;;
    network)    cmd_network ;;
    help|*)     cmd_help ;;
esac
