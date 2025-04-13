#!/bin/bash

# 显示进程信息的函数
function display_process() {
    local PID=$1
    echo "找到 Uvicorn 进程，PID: ${PID}，详情如下："
    OS_TYPE=$(uname)
    if [ "$OS_TYPE" = "Darwin" ]; then
        ps -o pid,ppid,user,%cpu,%mem,etime,command -p ${PID}
    else
        ps -o pid,ppid,user,%cpu,%mem,etime,cmd -p ${PID}
    fi
}

echo "查找 'uvicorn app.main:app' 进程..."
# 查询正在运行的 Uvicorn 进程详情
ps -eo pid,ppid,user,%cpu,%mem,etime | grep "uvicorn app.main:app" | grep -v grep

# 使用 pgrep 查找匹配的进程 ID
PIDS=$(pgrep -f "uvicorn app.main:app")

if [ -z "${PIDS}" ]; then
    echo "未找到匹配的 Uvicorn 进程。"
    exit 0
fi

# 将 PIDS 转换为数组
PIDS_ARRAY=(${PIDS})

# 检查是否找到多个匹配的进程
if [ ${#PIDS_ARRAY[@]} -gt 1 ]; then
    echo "找到多个匹配的 Uvicorn 进程："
    echo "${PIDS}"
    echo "请手动检查并终止相关进程。"
    exit 1
fi

PID=${PIDS_ARRAY[0]}
# 显示 Uvicorn 进程详情
display_process ${PID}

echo "发送 SIGINT 信号以优雅地终止进程..."

# 发送 SIGINT 信号
kill -2 ${PID}

# 等待进程结束，最多等待 10 秒
for i in {1..10}; do
    if ! ps -p ${PID} > /dev/null; then
        echo "进程已成功终止。"
        echo "检查是否还有 'uvicorn app.main:app' 进程..."
        ps -eo pid,ppid,user,%cpu,%mem,etime | grep "uvicorn app.main:app" | grep -v grep
        exit 0
    fi
    sleep 1
done

echo "进程未在超时时间内终止，请手动检查。"
exit 1

