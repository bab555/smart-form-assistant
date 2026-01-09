"""
应用生命周期事件处理
"""
from fastapi import FastAPI
from app.core.logger import app_logger as logger
from app.services.knowledge_base import vector_store
from app.core.config import settings


async def startup_event(app: FastAPI):
    """
    应用启动时执行
    """
    logger.info("=" * 60)
    logger.info("智能表单助手后端系统启动中...")
    logger.info("=" * 60)
    
    try:
        # 初始化向量存储
        logger.info("正在初始化向量存储...")
        await vector_store.initialize(force_rebuild=False)
        logger.info("✅ 向量存储初始化完成")

        # 预加载/预热模型服务（避免在 graph 首次用到时才初始化）
        # - OCR/VL：构造单例 + 设置 api_key
        # - LLM：可选做一次轻量 warmup，降低首个任务延迟
        logger.info("正在初始化模型服务...")
        from app.services.aliyun_llm import llm_service
        from app.services.aliyun_ocr import ocr_service  # noqa: F401
        from app.services.aliyun_asr import asr_service  # noqa: F401

        await llm_service.warmup()
        logger.info("✅ 模型服务初始化完成")
        
        # 打印配置信息
        logger.info(f"📦 主控模型: {settings.ALIYUN_LLM_MODEL_MAIN}")
        logger.info(f"📦 校对模型: {settings.ALIYUN_LLM_MODEL_CALIBRATION}")
        logger.info(f"📦 印刷体OCR: {settings.ALIYUN_OCR_MODEL}")
        logger.info(f"📦 手写体VL: {settings.ALIYUN_VL_MODEL}")
        logger.info(f"📦 语音识别: {settings.ALIYUN_ASR_MODEL}")
        logger.info(f"📦 向量索引: {settings.FAISS_INDEX_PATH}")
        
        logger.info("=" * 60)
        logger.info("✅ 系统启动完成！")
        logger.info(f"🚀 服务运行在: http://{settings.HOST}:{settings.PORT}")
        logger.info(f"📖 API 文档: http://{settings.HOST}:{settings.PORT}/docs")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


async def shutdown_event(app: FastAPI):
    """
    应用关闭时执行
    """
    logger.info("=" * 60)
    logger.info("智能表单助手后端系统关闭中...")
    logger.info("=" * 60)
    
    # 清理资源
    logger.info("清理资源...")
    
    logger.info("✅ 系统已安全关闭")
    logger.info("=" * 60)

