"""任务相关的 Pydantic 数据模型 (MongoDB 文档)"""

import enum
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class AgentType(str, enum.Enum):
    CHIEF = "chief"
    CAREER = "career"
    RESEARCH = "research"
    LIFE = "life"
    STUDY = "study"
    FINANCE = "finance"
    TRAVEL = "travel"
    HEALTH = "health"


class TaskDocument(BaseModel):
    """任务文档"""
    task_id: str = Field(..., description="任务唯一ID")
    user_input: str = Field(..., description="用户原始输入")
    intent: Optional[str] = Field(None, description="识别的意图")
    agent_type: AgentType
    status: TaskStatus = TaskStatus.PENDING
    description: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    parent_task_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationDocument(BaseModel):
    """对话历史文档"""
    session_id: str = Field(..., description="会话ID")
    role: str = Field(..., description="user / assistant / system")
    content: str
    task_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------- API Schemas ----------

class TaskCreate(BaseModel):
    """创建任务请求"""
    user_input: str = Field(..., min_length=1, description="用户输入")
    session_id: Optional[str] = Field(None, description="会话ID")


class TaskPlan(BaseModel):
    """Chief Agent 生成的任务计划"""
    intent: str = Field(..., description="用户核心意图")
    complexity: str = Field(..., description="任务复杂度: 简单/中等/复杂")
    tasks: list["SubTaskPlan"] = Field(default_factory=list, description="子任务列表")
    execution_order: str = Field("sequential", description="执行顺序: sequential/parallel")


class SubTaskPlan(BaseModel):
    """子任务计划"""
    id: str = Field(..., description="任务ID")
    agent: str = Field(..., description="目标Agent")
    description: str = Field(..., description="任务描述")
    inputs: dict = Field(default_factory=dict, description="任务输入参数")
    dependencies: list[str] = Field(default_factory=list, description="依赖的任务ID")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    intent: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: list[TaskResponse]
    total: int


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str
    task_id: Optional[str] = None
    session_id: str


# ---------- 记忆系统文档 ----------

class MemoryEntry(BaseModel):
    """长期记忆条目"""
    content: str = Field(..., description="记忆内容")
    tags: list[str] = Field(default_factory=list, description="标签（用于检索）")
    source: str = Field(default="conversation", description="来源: conversation/extracted/manual")
    importance: int = Field(default=5, ge=1, le=10, description="重要程度 1-10")
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0


class UserProfile(BaseModel):
    """用户画像"""
    user_id: str = Field(default="default", description="用户ID")
    name: Optional[str] = None
    occupation: Optional[str] = None
    research_fields: list[str] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict, description="偏好设置")
    habits: list[str] = Field(default_factory=list, description="习惯/行为模式")
    facts: list[str] = Field(default_factory=list, description="已知事实")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionSummary(BaseModel):
    """会话摘要（短期记忆压缩）"""
    session_id: str
    summary: str = Field(..., description="会话摘要")
    message_count: int = 0
    key_points: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
