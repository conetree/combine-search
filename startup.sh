#!/bin/bash

# 定义日志目录和文件路径
LOG_DIR="./logs"
LOG_FILE="$LOG_DIR/app.log"

# 显示进程信息的函数
function display_process() {
    local PID=$1
    OS_TYPE=$(uname)
    if [ "$OS_TYPE" = "Darwin" ]; then
        ps -o pid,ppid,user,%cpu,%mem,etime,command -p ${PID}
    else
        ps -o pid,ppid,user,%cpu,%mem,etime,cmd -p ${PID}
    fi
}

# 检查日志目录是否存在，如果不存在则创建
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo "日志目录 $LOG_DIR 已创建。"
fi

# 检查日志文件是否存在，如果不存在则创建
if [ ! -f "$LOG_FILE" ]; then
    touch "$LOG_FILE"
    echo "日志文件 $LOG_FILE 已创建。"
fi

PORT=8006

# 检查端口是否已被占用
if lsof -i :$PORT | grep LISTEN > /dev/null; then
    echo "端口 $PORT 已被占用，可能 Uvicorn 已在运行。可以先关闭再运行。"
    lsof -i :$PORT
    exit 1
fi

# 启动 Uvicorn 服务器，并将输出重定向到日志文件
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port $PORT > "$LOG_FILE" 2>&1 &

sleep 0.2

# 使用 pgrep 查找 Uvicorn 进程
UVICORN_PID=$(pgrep -f "uvicorn app.main:app")

if [ -z "${UVICORN_PID}" ]; then
    echo "无法找到 Uvicorn 进程。"
    exit 1
fi

echo "Uvicorn 服务器已启动，PID: ${UVICORN_PID}"
# 显示进程
# ps -p ${UVICORN_PID}

# 显示 Uvicorn 进程详情
echo "找到 Uvicorn 进程，PID: ${UVICORN_PID}，详情如下："
display_process ${UVICORN_PID}

# 将后台作业从 shell 的作业列表中移除，避免 Ctrl+C 杀掉它
disown ${UVICORN_PID}

# 查看日志文件
# tail -f "$LOG_FILE"
