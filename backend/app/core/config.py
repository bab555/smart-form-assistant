"""
配置管理 - 环境变量加载
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """应用配置"""

    # 固定从 backend/.env 读取，避免因进程 cwd / uvicorn reload 导致读到错误的 .env
    # 同时忽略未知字段（避免因为新增 env 变量导致启动失败）
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ========== 服务器配置 ==========
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = True
    LOG_LEVEL: str = "info"
    
    # ========== 阿里云凭证 ==========
    # DashScope（百炼）API Key（sk-...），用于 qwen3-max / qwen-turbo / qwen-vl-ocr / qwen3-vl-plus 等
    # 兼容：如果不填，则回退用 ALIYUN_ACCESS_KEY_ID
    DASHSCOPE_API_KEY: str = ""

    # 阿里云 AccessKey（用于传统 OCR OpenAPI / 其他 OpenAPI）
    # 注意：这不是 sk-...，而是 LTAI... 这类 AccessKeyId + AccessKeySecret
    ALIYUN_ACCESS_KEY_ID: str
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    
    # ========== 阿里云 DashScope 模型 ==========
    # 主控模型（对话/工具调用）
    ALIYUN_LLM_MODEL_MAIN: str = "qwen3-max"
    # 快速模型（校对/提取）
    ALIYUN_LLM_MODEL_CALIBRATION: str = "qwen-turbo"
    # 排版模型
    ALIYUN_LLM_MODEL_FLASH: str = "qwen-flash"
    # 印刷体 OCR 模型（无时延）
    ALIYUN_OCR_MODEL: str = "qwen-vl-ocr-2025-11-20"
    # 手写体 VL 模型（支持提示词）
    ALIYUN_VL_MODEL: str = "qwen3-vl-plus"
    # 向量嵌入模型
    ALIYUN_EMBEDDING_MODEL: str = "text-embedding-v2"
    # ASR 语音识别模型
    ALIYUN_ASR_MODEL: str = "qwen3-asr-flash-realtime"
    
    # ========== 阿里云 OCR（旧，保留兼容） ==========
    ALIYUN_OCR_ENDPOINT: str = "ocr-api.cn-hangzhou.aliyuncs.com"
    ALIYUN_OCR_REGION: str = "cn-hangzhou"

    # ========== 印刷体 OCR 快路径（传统 OCR OpenAPI） ==========
    # 是否优先使用传统 OCR OpenAPI（更快），失败则回退到 DashScope VL-OCR
    OCR_PRINTED_USE_OPENAPI: bool = True
    # 默认动作：全文识别高精版 (RecognizeAdvanced)
    OCR_OPENAPI_ACTION: str = "RecognizeAdvanced"
    
    # ========== 阿里云 ASR（旧，保留兼容） ==========
    ALIYUN_ASR_APP_KEY: str = ""
    ALIYUN_ASR_ENDPOINT: str = "nls-gateway-cn-shanghai.aliyuncs.com"
    
    # ========== MySQL 配置（Mock模式） ==========
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "smart_form_db"
    
    # ========== 向量数据库 ==========
    FAISS_INDEX_PATH: str = "./data/vector_store.index"
    FAISS_METADATA_PATH: str = "./data/metadata.pkl"
    
    # ========== 业务配置 ==========
    CONFIDENCE_THRESHOLD_HIGH: float = 0.85
    CONFIDENCE_THRESHOLD_LOW: float = 0.60
    AMBIGUITY_THRESHOLD: float = 0.10
    LLM_REQUEST_TIMEOUT: int = 120  # LLM 请求超时（秒）
    CALIBRATION_TIMEOUT: int = 180  # 校准流程总超时（秒）
    
    # ========== CORS 配置 ==========
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # ========== 日志配置 ==========
    LOG_FILE_PATH: str = "./logs/app.log"
    LOG_ROTATION: str = "100 MB"
    LOG_RETENTION: str = "30 days"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins 列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()

