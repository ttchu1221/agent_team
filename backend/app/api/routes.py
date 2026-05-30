from __future__ import annotations

"""API 路由 - 任务与聊天 (MongoDB + 多模型路由器 + 三层记忆)"""

import uuid
import asyncio
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_database
from app.core.scheduler import TaskScheduler
from app.core.memory import MemorySystem
from app.agents.factory import AgentFactory
from app.agents.base import AgentResult
from app.models.task import TaskStatus, ChatRequest, ChatResponse, TaskResponse, TaskListResponse

logger = structlog.get_logger()
router = APIRouter()


def _get_router():
    """延迟获取路由器（避免循环导入）"""
    from app.main import get_llm_router
    return get_llm_router()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    主聊天入口 - Chief Agent 解析意图后分发给专业 Agent

    集成三层记忆：
    - 短期：自动压缩长对话为摘要
    - 长期：检索相关记忆注入上下文，回复后自动提取值得记住的信息
    - 画像：注入用户画像，回复后自动更新
    """
    db = get_database()
    llm_router = _get_router()
    session_id = request.session_id or str(uuid.uuid4())
    memory = MemorySystem(db, llm_router=llm_router)
    scheduler = TaskScheduler(db)

    # 保存用户消息
    await memory.save_message(session_id, "user", request.message)

    # 获取上下文（自动摘要压缩）
    history = await memory.get_context_window(session_id)

    # 构建记忆上下文
    memory_context = await memory.get_memory_context(request.message, limit=3)
    profile_context = await memory.get_profile_context()

    # Chief Agent 解析意图
    chief = AgentFactory.create("chief", router=llm_router)
    plan_result = await chief.execute({
        "message": request.message,
        "history": history[:-1],
    })

    if not plan_result.success:
        raise HTTPException(status_code=500, detail=plan_result.error)

    plan_data = plan_result.data
    tasks = plan_data.get("tasks", [])

    # 如果没有子任务（简单对话），直接回复
    if not tasks:
        intent = plan_data.get("intent", "chat")
        if intent in ("chat", "greeting", "general"):
            # 构建增强提示
            system_parts = ["你是一个友好的AI助手。请简洁地回复用户。"]
            if profile_context:
                system_parts.append(profile_context)
            if memory_context:
                system_parts.append(memory_context)

            messages = [
                {"role": "system", "content": "\n\n".join(system_parts)},
                *[{"role": m["role"], "content": m["content"]} for m in history[-6:]],
            ]
            reply = await llm_router.chat(messages=messages, task_type="chat")
            await memory.save_message(session_id, "assistant", reply)

            # 异步提取记忆和更新画像（不阻塞响应）
            asyncio.create_task(
                _post_chat_memory_update(memory, session_id, request.message, reply)
            )

            return ChatResponse(reply=reply, session_id=session_id)

    # 有子任务 -> 创建并执行
    created_tasks = await scheduler.create_task_from_plan(request.message, plan_data)

    if not created_tasks:
        raise HTTPException(status_code=500, detail="任务创建失败")

    first_task = created_tasks[0]

    # 将记忆上下文传给 Agent
    agent = AgentFactory.create(first_task.agent_type.value, router=llm_router, db=db)

    await scheduler.update_task_status(first_task.task_id, TaskStatus.RUNNING)

    # 注入记忆上下文到任务输入
    agent_context = {
        "session_id": session_id,
        "history": history,
        "memory_context": memory_context,
        "profile_context": profile_context,
    }

    result: AgentResult = await agent.execute(
        task_input=first_task.description,
        context=agent_context,
    )

    if result.success:
        await scheduler.update_task_status(
            first_task.task_id, TaskStatus.COMPLETED, result=str(result.data)
        )
        reply = str(result.data)
    else:
        await scheduler.update_task_status(
            first_task.task_id, TaskStatus.FAILED, error=result.error
        )
        reply = f"任务执行失败: {result.error}"

    await memory.save_message(session_id, "assistant", reply, task_id=first_task.task_id)

    # 异步提取记忆和更新画像
    asyncio.create_task(
        _post_chat_memory_update(memory, session_id, request.message, reply)
    )

    return ChatResponse(
        reply=reply,
        task_id=first_task.task_id,
        session_id=session_id,
    )


async def _post_chat_memory_update(
    memory: MemorySystem, session_id: str, user_msg: str, reply: str
):
    """对话后异步更新记忆和画像"""
    try:
        await asyncio.gather(
            memory.extract_and_save(session_id, user_msg, reply),
            memory.extract_and_update_profile(user_msg, reply),
        )
    except Exception as e:
        logger.error("post_chat_memory_update_failed", error=str(e))


# ---------- 任务管理 ----------

@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(limit: int = 20):
    """获取任务列表"""
    db = get_database()
    scheduler = TaskScheduler(db)
    tasks = await scheduler.get_recent_tasks(limit=limit)
    return TaskListResponse(
        tasks=[
            TaskResponse(
                task_id=t.task_id,
                status=t.status.value,
                intent=t.intent,
                result=t.result,
                error=t.error,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tasks
        ],
        total=len(tasks),
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取单个任务详情"""
    db = get_database()
    scheduler = TaskScheduler(db)
    task = await scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskResponse(
        task_id=task.task_id,
        status=task.status.value,
        intent=task.intent,
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str):
    """重试失败的任务"""
    db = get_database()
    llm_router = _get_router()
    scheduler = TaskScheduler(db)
    task = await scheduler.retry_task(task_id)
    if not task:
        raise HTTPException(status_code=400, detail="任务不存在或无法重试")

    agent = AgentFactory.create(task.agent_type.value, router=llm_router, db=db)
    await scheduler.update_task_status(task.task_id, TaskStatus.RUNNING)

    result = await agent.execute(task_input=task.description)

    if result.success:
        await scheduler.update_task_status(
            task.task_id, TaskStatus.COMPLETED, result=str(result.data)
        )
    else:
        await scheduler.update_task_status(
            task.task_id, TaskStatus.FAILED, error=result.error
        )

    return {"task_id": task.task_id, "status": task.status.value}


# ---------- 记忆管理 API ----------

@router.get("/memory/memories")
async def list_memories(
    tag: Optional[str] = None,
    limit: int = Query(default=20, le=100),
):
    """查看长期记忆列表"""
    db = get_database()
    query = {}
    if tag:
        query["tags"] = tag

    cursor = (
        db["memories"]
        .find(query, {"_id": 0})
        .sort([("importance", -1), ("created_at", -1)])
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return {"memories": docs, "total": len(docs)}


@router.post("/memory/memories")
async def add_memory(body: dict):
    """手动添加一条长期记忆"""
    from app.models.task import MemoryEntry
    db = get_database()
    entry = MemoryEntry(
        content=body.get("content", ""),
        tags=body.get("tags", []),
        importance=body.get("importance", 5),
        source="manual",
    )
    await db["memories"].insert_one(entry.model_dump())
    return {"status": "ok"}


@router.get("/memory/profile")
async def get_user_profile():
    """查看用户画像"""
    db = get_database()
    memory = MemorySystem(db)
    profile = await memory.get_profile()
    return profile


@router.put("/memory/profile")
async def update_user_profile(body: dict):
    """手动更新用户画像"""
    db = get_database()
    memory = MemorySystem(db)
    await memory.update_profile(**body)
    return {"status": "ok"}


@router.get("/memory/summaries/{session_id}")
async def get_session_summary(session_id: str):
    """获取会话摘要"""
    db = get_database()
    doc = await db["session_summaries"].find_one(
        {"session_id": session_id},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    if not doc:
        raise HTTPException(status_code=404, detail="摘要不存在")
    return doc
