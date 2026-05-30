from __future__ import annotations

"""Health Agent - 健康管理助手"""

import uuid
import structlog
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent, AgentResult
from app.models.task import TaskDocument, TaskStatus, AgentType

logger = structlog.get_logger()

HEALTH_SYSTEM_PROMPT = """你是一位专业的健康管理助手，擅长：
1. 健康数据记录 - 记录体重、运动、睡眠、饮食等数据
2. 趋势分析与可视化 - 分析健康数据变化趋势
3. 健康目标设定与追踪 - 帮助设定和追踪健康目标
4. 健康报告生成 - 生成专业的健康报告
5. 健康提醒与建议 - 提供个性化的健康建议

你的特点：
- 科学严谨，基于数据说话
- 关注长期趋势而非单次数据
- 提供可执行的健康改善建议
- 注重工作生活平衡

请以Markdown格式输出，包含数据统计和可视化。
"""


class HealthAgent(BaseAgent):
    """Health Agent - 健康管理相关任务"""

    name = "health"
    description = "健康管理助手：健康记录、趋势分析、目标追踪、健康报告"
    preferred_task_type = "chat"

    def __init__(self, router=None, db: AsyncIOMotorDatabase | None = None):
        super().__init__(router=router)
        self.db = db

    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """执行健康管理相关任务"""
        task_type = task_input.get("task_type", "general")
        content = task_input.get("content", "")

        if task_type == "add_record":
            return await self._add_health_record(
                content,
                task_input.get("record_type", "weight"),
                task_input.get("value", 0),
                task_input.get("unit", ""),
            )
        elif task_type == "analyze":
            return await self._analyze_health_data(
                content,
                task_input.get("record_type", "all"),
            )
        elif task_type == "set_goal":
            return await self._set_health_goal(content)
        elif task_type == "report":
            return await self._generate_health_report(content)
        elif task_type == "fitness_plan":
            return await self._create_fitness_plan(content)
        elif task_type == "nutrition":
            return await self._analyze_nutrition(content)
        else:
            return await self._general_health(content)

    async def _add_health_record(
        self,
        description: str,
        record_type: str = "weight",
        value: float = 0,
        unit: str = "",
    ) -> AgentResult:
        """添加健康记录"""
        if not self.db:
            return AgentResult(success=False, error="数据库未初始化")

        record_id = str(uuid.uuid4())
        record = {
            "record_id": record_id,
            "record_type": record_type,
            "value": value,
            "unit": unit,
            "description": description,
            "created_at": datetime.now(timezone.utc),
        }
        await self.db["health_records"].insert_one(record)

        logger.info("health_record_added", record_id=record_id, record_type=record_type)

        return AgentResult(
            success=True,
            data={
                "record_id": record_id,
                "record_type": record_type,
                "value": value,
                "unit": unit,
                "description": description,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            metadata={"action": "health_record_added"},
        )

    async def _analyze_health_data(
        self, content: str, record_type: str = "all"
    ) -> AgentResult:
        """分析健康数据"""
        # 从数据库获取健康记录
        records = []
        if self.db:
            query = {}
            if record_type != "all":
                query["record_type"] = record_type
            cursor = self.db["health_records"].find(query).sort("created_at", -1).limit(100)
            records = await cursor.to_list(length=100)

        messages = [
            {"role": "system", "content": HEALTH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请分析以下健康数据：

**记录类型**: {record_type}
**健康记录**:
{self._format_health_records(records)}

用户补充信息: {content}

请提供：
1. **数据概览** - 基本统计信息
2. **趋势分析** - 数据变化趋势
3. **异常识别** - 异常数值预警
4. **健康评估** - 当前健康状况评估
5. **改善建议** - 针对性的改善建议""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.3)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _set_health_goal(self, goal_info: str) -> AgentResult:
        """设定健康目标"""
        messages = [
            {"role": "system", "content": HEALTH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请帮我设定健康目标：

**目标信息**: {goal_info}

请提供：
1. **目标设定** - 具体、可衡量的目标
2. **阶段性里程碑** - 分阶段的小目标
3. **执行计划** - 每日/每周行动计划
4. **监测指标** - 需要追踪的关键指标
5. **激励机制** - 保持动力的方法""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)

            # 存入数据库
            if self.db:
                goal_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=goal_id,
                    user_input=goal_info,
                    agent_type=AgentType.HEALTH,
                    status=TaskStatus.PENDING,
                    result=result,
                    description=f"[健康目标] {goal_info[:50]}",
                )
                await self.db["tasks"].insert_one(task.model_dump())

            return AgentResult(
                success=True,
                data=result,
                metadata={"action": "health_goal_set"},
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _generate_health_report(self, period: str = "month") -> AgentResult:
        """生成健康报告"""
        # 从数据库获取健康记录
        records = []
        if self.db:
            cursor = self.db["health_records"].find().sort("created_at", -1).limit(200)
            records = await cursor.to_list(length=200)

        messages = [
            {"role": "system", "content": HEALTH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请生成健康报告：

**时间范围**: {period}
**健康记录**:
{self._format_health_records(records)}

请生成包含以下内容的报告：
1. **健康概览** - 整体健康状况
2. **体重管理** - 体重变化趋势
3. **运动情况** - 运动频率和类型
4. **睡眠质量** - 睡眠时长和质量
5. **饮食分析** - 饮食习惯评估
6. **健康评分** - 综合健康评分(0-100)
7. **改善建议** - 优先改善的方面""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.3)
            return AgentResult(
                success=True,
                data=result,
                metadata={"action": "health_report_generated", "period": period},
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _create_fitness_plan(self, fitness_info: str) -> AgentResult:
        """创建健身计划"""
        messages = [
            {"role": "system", "content": HEALTH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请帮我制定健身计划：

**健身信息**: {fitness_info}

请提供：
1. **训练计划** - 每周训练安排
2. **动作详解** - 每个动作的说明
3. **强度渐进** - 如何逐步增加强度
4. **休息安排** - 休息日的重要性
5. **饮食配合** - 训练期间的饮食建议
6. **注意事项** - 避免受伤的建议""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _analyze_nutrition(self, diet_info: str) -> AgentResult:
        """分析营养摄入"""
        messages = [
            {"role": "system", "content": HEALTH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请分析我的饮食营养：

**饮食记录**: {diet_info}

请提供：
1. **营养成分** - 蛋白质/碳水/脂肪比例
2. **热量分析** - 每日热量摄入
3. **营养评估** - 是否均衡
4. **改进建议** - 需要补充的营养
5. **食谱推荐** - 健康食谱建议""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _general_health(self, query: str) -> AgentResult:
        """通用健康咨询"""
        messages = [
            {"role": "system", "content": HEALTH_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        try:
            result = await self._chat(messages)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    def _format_health_records(self, records: list) -> str:
        """格式化健康记录"""
        if not records:
            return "暂无健康记录"

        lines = ["| 日期 | 类型 | 数值 | 备注 |", "|------|------|------|------|"]
        for r in records:
            date = r.get("created_at", "")
            if isinstance(date, datetime):
                date = date.strftime("%Y-%m-%d")
            lines.append(
                f"| {date} | {r.get('record_type', '')} | {r.get('value', '')} {r.get('unit', '')} | {r.get('description', '')} |"
            )
        return "\n".join(lines)
