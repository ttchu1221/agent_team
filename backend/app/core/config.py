"""应用配置管理"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
from pathlib import Path

# 项目根目录（agent_team/backend）
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """应用配置"""

    model_config = ConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8")

    # 核心配置
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "dev-secret-key"

    # MongoDB 配置
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "personal_agent_team"

    # 向量数据库 & Redis
    VECTOR_DB_URL: str = "http://localhost:6333"
    REDIS_URL: str = "redis://localhost:6379"

    # ====== LLM 多模型配置 ======
    LLM_PROVIDERS: str = "qwen,deepseek,xiaomi,moonshot,zhipu,openai"
    LLM_DEFAULT_PROVIDER: str = "qwen"
    LLM_DEFAULT_MODEL: str = "qwen-plus"

    # 任务路由
    LLM_ROUTE_REASONING: str = "deepseek:deepseek-reasoner"
    LLM_ROUTE_CODE: str = "deepseek:deepseek-coder"
    LLM_ROUTE_CHAT: str = "qwen:qwen-turbo"
    LLM_ROUTE_SIMPLE: str = "qwen:qwen-turbo"

    # ---- Qwen (通义千问) ----
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODELS: str = "qwen-plus,qwen-turbo,qwen-max,qwen-long"

    # ---- DeepSeek ----
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODELS: str = "deepseek-chat,deepseek-coder,deepseek-reasoner"

    # ---- Xiaomi (小米大模型) ----
    XIAOMI_API_KEY: str = ""
    XIAOMI_BASE_URL: str = "https://token-plan-cn.xiaomimimo.com/v1"
    XIAOMI_MODELS: str = "mimo-v2.5-pro,MiLM-v2-flash"

    # ---- Moonshot (月之暗面 / Kimi) ----
    MOONSHOT_API_KEY: str = ""
    MOONSHOT_BASE_URL: str = "https://api.moonshot.cn/v1"
    MOONSHOT_MODELS: str = "moonshot-v1-128k,moonshot-v1-32k,moonshot-v1-8k"

    # ---- Zhipu (智谱 / GLM) ----
    ZHIPU_API_KEY: str = ""
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_MODELS: str = "glm-4-plus,glm-4-flash,glm-4-long"

    # ---- OpenAI ----
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODELS: str = "gpt-4o,gpt-4o-mini,gpt-4-turbo"

    # 工具 & 任务队列
    SEARCH_API_KEY: str = ""
    BROWSER_HEADLESS: bool = True
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
