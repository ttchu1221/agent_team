"""MongoDB 数据库连接管理"""

import motor.motor_asyncio
import structlog
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

client: motor.motor_asyncio.AsyncIOMotorClient = None
db: motor.motor_asyncio.AsyncIOMotorDatabase = None


async def connect_db():
    """启动 MongoDB 连接"""
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # 创建索引
    await db["tasks"].create_index("task_id", unique=True)
    await db["tasks"].create_index("parent_task_id")
    await db["tasks"].create_index("created_at")
    await db["tasks"].create_index([("agent_type", 1), ("description", 1)])
    await db["conversations"].create_index("session_id")
    await db["conversations"].create_index("created_at")

    # 记忆系统索引
    await db["memories"].create_index("tags")
    await db["memories"].create_index("importance")
    await db["memories"].create_index("created_at")
    await db["memories"].create_index([("content", "text")])
    await db["session_summaries"].create_index("session_id")
    await db["user_profiles"].create_index("user_id", unique=True)

    logger.info("mongodb_connected", db_name=settings.MONGODB_DB_NAME)


async def close_db():
    """关闭 MongoDB 连接"""
    global client
    if client:
        client.close()
        logger.info("mongodb_disconnected")


def get_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """获取数据库实例"""
    return db
