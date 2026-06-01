from __future__ import annotations

"""任务调度器 (MongoDB 版)"""

import uuid
import structlog
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.task import TaskDocument, TaskStatus, AgentType, TaskPlan

logger = structlog.get_logger()


class TaskScheduler:
    """任务调度器 - 管理任务的创建、分发和状态更新"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["tasks"]

    async def create_task_from_plan(
        self, user_input: str, plan: TaskPlan
    ) -> list[TaskDocument]:
        """根据 Chief Agent 的任务计划创建任务"""
        parent_task_id = str(uuid.uuid4())
        tasks = []

        for subtask in plan.tasks:
            task_id = subtask.id if subtask.id else str(uuid.uuid4())
            task = TaskDocument(
                task_id=task_id,
                user_input=user_input,
                intent=plan.intent,
                agent_type=AgentType(subtask.agent),
                status=TaskStatus.PENDING,
                description=subtask.description,
                parent_task_id=parent_task_id if len(plan.tasks) > 1 else None,
            )
            await self.collection.insert_one(task.model_dump())
            tasks.append(task)

        logger.info(
            "tasks_created",
            parent_task_id=parent_task_id,
            task_count=len(tasks),
        )
        return tasks

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: str | None = None,
        error: str | None = None,
    ) -> TaskDocument | None:
        """更新任务状态"""
        update_fields = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc),
        }
        if result is not None:
            update_fields["result"] = result
        if error is not None:
            update_fields["error"] = error

        res = await self.collection.find_one_and_update(
            {"task_id": task_id},
            {"$set": update_fields},
            return_document=True,
        )

        if res:
            logger.info("task_status_updated", task_id=task_id, status=status.value)
            return TaskDocument(**res)

        logger.error("task_not_found", task_id=task_id)
        return None

    async def get_task(self, task_id: str) -> TaskDocument | None:
        """获取任务详情"""
        doc = await self.collection.find_one({"task_id": task_id})
        return TaskDocument(**doc) if doc else None

    async def get_recent_tasks(self, limit: int = 20) -> list[TaskDocument]:
        """获取最近的任务（仅顶层任务）"""
        cursor = (
            self.collection.find({"parent_task_id": None})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [TaskDocument(**doc) for doc in docs]

    async def retry_task(self, task_id: str) -> TaskDocument | None:
        """重试失败的任务"""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return None

        if task.retry_count >= task.max_retries:
            logger.warning("max_retries_exceeded", task_id=task_id)
            return None

        res = await self.collection.find_one_and_update(
            {"task_id": task_id},
            {
                "$set": {
                    "status": TaskStatus.RETRYING.value,
                    "error": None,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$inc": {"retry_count": 1},
            },
            return_document=True,
        )
        return TaskDocument(**res) if res else None

    async def delete_task(self, task_id: str) -> bool:
        """删除任务及其子任务"""
        # 先删除子任务
        await self.collection.delete_many({"parent_task_id": task_id})
        # 再删除主任务
        res = await self.collection.delete_one({"task_id": task_id})
        if res.deleted_count > 0:
            logger.info("task_deleted", task_id=task_id)
            return True
        return False
