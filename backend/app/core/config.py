"""
配置管理 - 环境变量加载
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # ========== 服务器配置 ==========
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = True
    LOG_LEVEL: str = "info"
    
    # ========== 阿里云凭证 ==========
    ALIYUN_ACCESS_KEY_ID: str
    ALIYUN_ACCESS_KEY_SECRET: str
    
    # ========== 阿里云 DashScope ==========
    ALIYUN_LLM_MODEL_MAIN: str = "qwen-max"
    ALIYUN_LLM_MODEL_CALIBRATION: str = "qwen-turbo"
    ALIYUN_VL_MODEL: str = "qwen-vl-plus"
    ALIYUN_EMBEDDING_MODEL: str = "text-embedding-v2"
    
    # ========== 阿里云 OCR ==========
    ALIYUN_OCR_ENDPOINT: str = "ocr-api.cn-hangzhou.aliyuncs.com"
    ALIYUN_OCR_REGION: str = "cn-hangzhou"
    
    # ========== 阿里云 ASR ==========
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()

