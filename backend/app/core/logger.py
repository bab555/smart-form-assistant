"""
日志配置 - 使用 Loguru
"""
import sys
from pathlib import Path
from loguru import logger
from app.core.config import settings


def setup_logger():
    """配置日志系统"""
    
    # 移除默认 handler
    logger.remove()
    
    # 控制台输出（带颜色）
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL.upper(),
        colorize=True,
    )
    
    # 文件输出（结构化）
    log_path = Path(settings.LOG_FILE_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        settings.LOG_FILE_PATH,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
    )
    
    return logger


# 全局 logger 实例
app_logger = setup_logger()

