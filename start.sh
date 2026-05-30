#!/usr/bin/env bash
# ============================================================
#  Personal Agent Team — 服务管理脚本 (macOS)
#  使用 launchctl 管理后台进程
# ============================================================
set -euo pipefail

# ========== 路径 ==========
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

BACKEND_PORT=8000
FRONTEND_PORT=3000

BACKEND_LABEL="com.agent-team.backend"
FRONTEND_LABEL="com.agent-team.frontend"

# ========== 颜色 ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; }
title(){ echo -e "\n━━━ $* ━━━"; }

# ========== 工具函数 ==========
check_port() { lsof -i :"$1" -sTCP:LISTEN &>/dev/null; }

get_pid_on_port() { lsof -ti :"$1" -sTCP:LISTEN 2>/dev/null | head -1; }

is_running_label() {
    launchctl list "$1" &>/dev/null
}

generate_plist() {
    local label=$1
    local log_prefix=$2
    shift 2
    local args=("$@")
    local plist_path="$LOG_DIR/${label}.plist"
    local work_dir="${args[0]}"  # WorkingDirectory = 第一个参数的目录

    cat > "$plist_path" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${label}</string>
    <key>ProgramArguments</key>
    <array>
$(for arg in "${args[@]:1}"; do echo "        <string>${arg}</string>"; done)
    </array>
    <key>WorkingDirectory</key>
    <string>${work_dir}</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/${log_prefix}.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/${log_prefix}.log</string>
</dict>
</plist>
PLIST
    echo "$plist_path"
}

# ========== 服务控制 ==========
do_start() {
    title "环境检查"

    # .env
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
            warn "已从 .env.example 创建 .env，请配置 API Key"
        else
            err ".env 不存在"
            exit 1
        fi
    fi
    ok ".env 已就绪"

    # 后端依赖
    info "检查后端依赖..."
    if python3 -c "import fastapi, motor, openai" &>/dev/null; then
        ok "后端依赖已就绪"
    else
        info "安装后端依赖..."
        pip3 install -r "$BACKEND_DIR/requirements.txt" -q
        ok "后端依赖安装完成"
    fi

    # 前端依赖
    info "检查前端依赖..."
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        info "安装前端依赖..."
        (cd "$FRONTEND_DIR" && npm install --silent)
        ok "前端依赖安装完成"
    else
        ok "前端依赖已就绪"
    fi

    # 端口检查
    title "端口检查"
    if check_port $BACKEND_PORT; then
        local pid
        pid=$(get_pid_on_port $BACKEND_PORT)
        if ! is_running_label "$BACKEND_LABEL"; then
            warn "端口 $BACKEND_PORT 被其他进程占用 (PID: $pid)"
            read -rp "是否释放端口? [y/N] " yn
            if [[ "$yn" =~ ^[Yy]$ ]]; then
                kill "$pid" 2>/dev/null || true
                sleep 1
            else
                err "端口被占用，无法启动"
                exit 1
            fi
        fi
    fi

    if check_port $FRONTEND_PORT; then
        local pid
        pid=$(get_pid_on_port $FRONTEND_PORT)
        if ! is_running_label "$FRONTEND_LABEL"; then
            warn "端口 $FRONTEND_PORT 被其他进程占用 (PID: $pid)"
            read -rp "是否释放端口? [y/N] " yn
            if [[ "$yn" =~ ^[Yy]$ ]]; then
                kill "$pid" 2>/dev/null || true
                sleep 1
            else
                err "端口被占用，无法启动"
                exit 1
            fi
        fi
    fi

    title "启动服务"

    # ── 启动后端 ──
    info "启动后端 (FastAPI + MongoDB)..."
    local backend_plist
    backend_plist=$(generate_plist "$BACKEND_LABEL" "backend" \
        "$BACKEND_DIR" "$(which python3)" "-m" "uvicorn" "app.main:app" "--reload" "--port" "$BACKEND_PORT")

    launchctl unload "$backend_plist" 2>/dev/null || true
    launchctl load "$backend_plist"
    launchctl start "$BACKEND_LABEL"

    # 等待后端就绪
    local waited=0
    while [ $waited -lt 20 ]; do
        if curl -s "http://localhost:$BACKEND_PORT/docs" &>/dev/null; then
            break
        fi
        sleep 1
        waited=$((waited + 1))
    done

    if curl -s "http://localhost:$BACKEND_PORT/docs" &>/dev/null; then
        ok "后端已启动 → http://localhost:$BACKEND_PORT"
    else
        err "后端启动超时 (20s)"
        err "查看日志: $LOG_DIR/backend.log"
        do_stop 2>/dev/null
        exit 1
    fi

    # ── 启动前端 ──
    info "启动前端 (Next.js)..."
    local next_bin="$FRONTEND_DIR/node_modules/next/dist/bin/next"
    local frontend_plist
    frontend_plist=$(generate_plist "$FRONTEND_LABEL" "frontend" \
        "$FRONTEND_DIR" "$(which node)" "$next_bin" "dev" "--port" "$FRONTEND_PORT")

    launchctl unload "$frontend_plist" 2>/dev/null || true
    launchctl load "$frontend_plist"
    launchctl start "$FRONTEND_LABEL"

    # 等待前端就绪
    waited=0
    while [ $waited -lt 30 ]; do
        if curl -s "http://localhost:$FRONTEND_PORT" &>/dev/null; then
            break
        fi
        sleep 1
        waited=$((waited + 1))
    done

    if curl -s "http://localhost:$FRONTEND_PORT" &>/dev/null; then
        ok "前端已启动 → http://localhost:$FRONTEND_PORT"
    else
        err "前端启动超时 (30s)"
        err "查看日志: $LOG_DIR/frontend.log"
        do_stop 2>/dev/null
        exit 1
    fi

    # ── 完成 ──
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ Personal Agent Team 已启动${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "  前端:     http://localhost:$FRONTEND_PORT"
    echo "  后端 API: http://localhost:$BACKEND_PORT"
    echo "  API 文档: http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo "  日志目录: $LOG_DIR/"
    echo ""
    echo "  停止服务: bash start.sh stop"
    echo "  查看日志: bash start.sh logs"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

do_stop() {
    title "停止服务"

    local backend_plist="$LOG_DIR/${BACKEND_LABEL}.plist"
    local frontend_plist="$LOG_DIR/${FRONTEND_LABEL}.plist"

    if [ -f "$frontend_plist" ]; then
        info "停止前端..."
        launchctl unload "$frontend_plist" 2>/dev/null || true
        ok "前端已停止"
    fi

    if [ -f "$backend_plist" ]; then
        info "停止后端..."
        launchctl unload "$backend_plist" 2>/dev/null || true
        ok "后端已停止"
    fi

    # 兜底：清理残留进程
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "next dev.*--port $FRONTEND_PORT" 2>/dev/null || true

    ok "所有服务已停止"
}

do_restart() {
    do_stop
    sleep 2
    do_start
}

do_status() {
    title "服务状态"

    # 后端
    if curl -s "http://localhost:$BACKEND_PORT/docs" &>/dev/null; then
        local pid
        pid=$(get_pid_on_port $BACKEND_PORT)
        ok "后端运行中 (PID: $pid) → http://localhost:$BACKEND_PORT"
    else
        err "后端未运行"
    fi

    # 前端
    if curl -s "http://localhost:$FRONTEND_PORT" &>/dev/null; then
        local pid
        pid=$(get_pid_on_port $FRONTEND_PORT)
        ok "前端运行中 (PID: $pid) → http://localhost:$FRONTEND_PORT"
    else
        err "前端未运行"
    fi

    echo ""
    echo "日志: 后端=$(du -sh "$LOG_DIR/backend.log" 2>/dev/null | cut -f1 || echo '0')  前端=$(du -sh "$LOG_DIR/frontend.log" 2>/dev/null | cut -f1 || echo '0')"
}

do_logs() {
    local target="${2:-both}"

    case "$target" in
        backend|be)
            tail -f "$LOG_DIR/backend.log"
            ;;
        frontend|fe)
            tail -f "$LOG_DIR/frontend.log"
            ;;
        *)
            echo -e "${GREEN}[后端]${NC} 和 ${CYAN}[前端]${NC} 日志 (Ctrl+C 退出)"
            echo "─────────────────────────────────"
            tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
            ;;
    esac
}

# ========== 主入口 ==========
case "${1:-help}" in
    start)    do_start ;;
    stop)     do_stop ;;
    restart)  do_restart ;;
    status)   do_status ;;
    logs)     do_logs "$@" ;;
    *)
        echo "用法: bash start.sh {start|stop|restart|status|logs [backend|frontend]}"
        echo ""
        echo "  start     启动后端 + 前端"
        echo "  stop      停止所有服务"
        echo "  restart   重启所有服务"
        echo "  status    查看运行状态"
        echo "  logs      查看日志 (可选: backend/frontend)"
        ;;
esac
