"""FastAPI 应用入口 (MongoDB + 多模型路由器)"""

import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import connect_db, close_db, get_database
from app.core.config import get_settings
from app.core.llm_router import build_router_from_settings
from app.api.routes import router as api_router

settings = get_settings()

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer() if settings.APP_ENV == "development"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logger = structlog.get_logger()

# 全局 LLM 路由器实例
llm_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global llm_router
    logger.info("starting_up", env=settings.APP_ENV)

    # 初始化 MongoDB
    await connect_db()
    logger.info("mongodb_connected")

    # 初始化 LLM 路由器
    llm_router = build_router_from_settings(settings)

    yield

    await close_db()
    logger.info("shutting_down")


app = FastAPI(
    title="Personal Agent Team",
    description="多智能体协作系统 - 个人AI助理平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


def get_llm_router():
    """获取全局 LLM 路由器"""
    return llm_router


@app.get("/")
async def root():
    return {
        "name": "Personal Agent Team",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/v1/models")
async def list_models():
    """列出所有可用的 LLM 提供商和模型"""
    if not llm_router:
        return {"providers": [], "routes": {}}
    return {
        "providers": llm_router.list_providers(),
        "routes": llm_router.list_routes(),
        "default": f"{llm_router.default_provider}:{llm_router.default_model}",
    }
