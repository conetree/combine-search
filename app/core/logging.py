import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logging(
    log_file: Optional[str] = None,
    log_level: int = logging.INFO,
    max_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    配置日志系统
    :param log_file: 日志文件路径
    :param log_level: 日志级别
    :param max_size: 单个日志文件最大大小
    :param backup_count: 保留的日志文件数量
    """
    # 创建logger
    logger = logging.getLogger("ai_agent")
    logger.setLevel(log_level)

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# 创建默认logger
logger = setup_logging()

def log_request_info(request_id: str, method: str, path: str, params: dict = None):
    """记录请求信息"""
    logger.info(f"Request {request_id} - {method} {path} - Params: {params}")

def log_response_info(request_id: str, status_code: int, response_time: float):
    """记录响应信息"""
    logger.info(f"Response {request_id} - Status: {status_code} - Time: {response_time:.2f}s")

def log_error(request_id: str, error: Exception, context: dict = None):
    """记录错误信息"""
    logger.error(f"Error {request_id} - {str(error)}", exc_info=True, extra=context or {}) 