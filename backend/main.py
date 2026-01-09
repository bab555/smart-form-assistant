"""
智能表单助手 - FastAPI 主程序
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os
from pathlib import Path

from app.core.config import settings
from app.core.logger import app_logger as logger
from app.core.events import startup_event, shutdown_event
from app.api import endpoints, websocket, skills


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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理"""
    logger.error(f"参数验证失败: {exc.errors()}")
    logger.error(f"请求体: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "请求参数验证失败"},
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

# Skills API 路由
app.include_router(
    skills.router,
    prefix="/api/skills",
    tags=["Skills"]
)


# ========== 静态文件与 SPA 路由 ==========

# 前端构建目录
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    logger.info(f"挂载前端静态文件: {FRONTEND_DIST}")
    
    # 挂载 assets
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    
    # 根路由 - 返回 index.html
    @app.get("/")
    async def serve_spa():
        return FileResponse(FRONTEND_DIST / "index.html")
    
    # 所有其他未匹配路由 - 也返回 index.html (SPA Fallback)
    # 注意：这需要放在所有 API 路由之后
    @app.get("/{full_path:path}")
    async def serve_spa_fallback(full_path: str):
        # 排除 API 和 WebSocket 路径
        if full_path.startswith("api/") or full_path.startswith("ws/") or full_path.startswith("docs") or full_path.startswith("redoc"):
            return JSONResponse(status_code=404, content={"message": "Not Found"})
        
        # 检查文件是否存在（例如 favicon.ico）
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
            
        return FileResponse(FRONTEND_DIST / "index.html")

else:
    logger.warning(f"前端构建目录不存在: {FRONTEND_DIST}，仅提供 API 服务")
    
    # 仅提供 API 时的根路由
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "service": "智能表单助手后端",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "frontend": "not built"
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

