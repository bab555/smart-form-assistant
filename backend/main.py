"""
智能表单助手 - FastAPI 主程序
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import settings
from app.core.logger import app_logger as logger
from app.core.events import startup_event, shutdown_event
from app.api import endpoints, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    await startup_event(app)
    yield
    # 关闭
    await shutdown_event(app)


# 创建 FastAPI 应用
app = FastAPI(
    title="智能表单助手 API",
    description="基于 AI 的多模态智能表单填写系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ========== CORS 配置 ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 路由注册 ==========

# RESTful API 路由
app.include_router(
    endpoints.router,
    prefix="/api",
    tags=["API"]
)

# WebSocket 路由
app.include_router(
    websocket.router,
    prefix="/ws",
    tags=["WebSocket"]
)


# ========== 根路由 ==========
@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "智能表单助手后端",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


# ========== 主入口 ==========
if __name__ == "__main__":
    logger.info("启动开发服务器...")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1 if settings.RELOAD else settings.WORKERS
    )

