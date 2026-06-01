from __future__ import annotations

"""Finance Agent - 财务管理助手 (数据库 + 搜索集成)"""

import uuid
import structlog
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent, AgentResult
from app.models.task import TaskDocument, TaskStatus, AgentType
from app.tools.search.search import SearchTool

logger = structlog.get_logger()

FINANCE_SYSTEM_PROMPT = """你是一位专业的财务管理助手，擅长：
1. 消费记录与分类 - 帮助用户记录和分类消费
2. 支出趋势分析 - 分析消费习惯和趋势
3. 预算制定与监控 - 帮助制定预算并监控执行
4. 订阅服务管理 - 识别和管理订阅服务
5. 财务报告生成 - 生成清晰的财务报告

你的特点：
- 数据驱动，用数字说话
- 善于发现消费中的"隐形杀手"
- 提供切实可行的节省建议
- 输出结构清晰、可视化友好的财务报告

请以Markdown格式输出，包含表格和统计。
"""


class FinanceAgent(BaseAgent):
    """Finance Agent - 财务管理相关任务"""

    name = "finance"
    description = "财务管理助手：消费记录、支出分析、预算管理、订阅管理、财务资讯搜索"
    preferred_task_type = "chat"

    def __init__(self, router=None, db: AsyncIOMotorDatabase | None = None):
        super().__init__(router=router)
        self.db = db
        self.search_tool = SearchTool()

    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """执行财务管理相关任务"""
        task_type = task_input.get("task_type", "general")
        content = task_input.get("content", "")

        if task_type == "add_transaction":
            return await self._add_transaction(
                content,
                task_input.get("amount", 0),
                task_input.get("category", "其他"),
            )
        elif task_type == "analyze":
            return await self._analyze_expenses(
                content,
                task_input.get("period", "month"),
            )
        elif task_type == "search_finance":
            return await self._search_finance(content, task_input.get("max_results", 5))
        elif task_type == "set_budget":
            return await self._set_budget(content)
        elif task_type == "manage_subscriptions":
            return await self._manage_subscriptions(content)
        elif task_type == "report":
            return await self._generate_report(content)
        else:
            return await self._general_finance(content)

    async def _search_finance(self, topic: str, max_results: int = 5) -> AgentResult:
        """搜索财务相关资讯"""
        try:
            search_result = await self.search_tool.execute(
                f"{topic} finance investment", max_results=max_results
            )

            if not search_result.success:
                return AgentResult(success=False, error=search_result.error)

            papers = search_result.data
            papers_text = "\n".join([
                f"- {p['title']} ({p.get('year', 'N/A')})"
                for p in papers
            ])

            messages = [
                {"role": "system", "content": FINANCE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"""根据搜索结果，分析 "{topic}" 相关的财务信息：

{papers_text}

请提供：
1. **市场趋势** - 当前市场状况
2. **投资建议** - 基于分析的建议
3. **风险提示** - 需要注意的风险""",
                },
            ]

            result = await self._chat(messages, temperature=0.5)

            # 保存到数据库
            if self.db:
                record_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=record_id,
                    user_input=topic,
                    agent_type=AgentType.FINANCE,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    description=f"[财务搜索] {topic}",
                )
                await self.db["tasks"].insert_one(task.model_dump())

            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _add_transaction(
        self, description: str, amount: float, category: str = "其他"
    ) -> AgentResult:
        """添加消费记录"""
        if not self.db:
            return AgentResult(success=False, error="数据库未初始化")

        transaction_id = str(uuid.uuid4())
        transaction = {
            "transaction_id": transaction_id,
            "description": description,
            "amount": amount,
            "category": category,
            "created_at": datetime.now(timezone.utc),
        }
        await self.db["transactions"].insert_one(transaction)

        logger.info("transaction_added", transaction_id=transaction_id, amount=amount)

        return AgentResult(
            success=True,
            data={
                "transaction_id": transaction_id,
                "description": description,
                "amount": amount,
                "category": category,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            metadata={"action": "transaction_added"},
        )

    async def _analyze_expenses(
        self, content: str, period: str = "month"
    ) -> AgentResult:
        """分析支出趋势"""
        # 从数据库获取交易记录
        transactions = []
        if self.db:
            cursor = self.db["transactions"].find().sort("created_at", -1).limit(100)
            transactions = await cursor.to_list(length=100)

        messages = [
            {"role": "system", "content": FINANCE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请分析以下消费数据：

**时间范围**: {period}
**交易记录**:
{self._format_transactions(transactions)}

用户补充信息: {content}

请提供：
1. **支出统计** - 按分类汇总
2. **趋势分析** - 消费趋势变化
3. **异常识别** - 异常大额支出
4. **节省建议** - 可优化的消费项
5. **预算建议** - 各分类建议预算""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.3)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _set_budget(self, budget_info: str) -> AgentResult:
        """设置预算"""
        messages = [
            {"role": "system", "content": FINANCE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请帮我制定预算计划：

**预算信息**: {budget_info}

请提供：
1. **预算分配** - 各分类预算金额
2. **优先级** - 必需/可选/可削减
3. **执行建议** - 如何控制预算
4. **预警机制** - 超支预警规则""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _manage_subscriptions(self, content: str) -> AgentResult:
        """管理订阅服务"""
        messages = [
            {"role": "system", "content": FINANCE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请帮我分析和管理订阅服务：

**订阅信息**: {content}

请提供：
1. **订阅清单** - 所有订阅服务列表
2. **使用频率分析** - 哪些订阅使用率低
3. **成本分析** - 每月订阅总成本
4. **优化建议** - 哪些可以取消或降级
5. **替代方案** - 更便宜的替代选择""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _generate_report(self, period: str = "month") -> AgentResult:
        """生成财务报告"""
        # 从数据库获取交易记录
        transactions = []
        if self.db:
            cursor = self.db["transactions"].find().sort("created_at", -1).limit(200)
            transactions = await cursor.to_list(length=200)

        messages = [
            {"role": "system", "content": FINANCE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请生成财务报告：

**时间范围**: {period}
**交易记录**:
{self._format_transactions(transactions)}

请生成包含以下内容的报告：
1. **概览** - 总收入/支出/结余
2. **分类统计** - 各分类支出占比
3. **趋势图表** - 支出趋势（用ASCII图表表示）
4. **预算执行** - 预算使用情况
5. **下期建议** - 下个月的财务建议""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.3)

            # 存入数据库
            if self.db:
                report_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=report_id,
                    user_input=period,
                    agent_type=AgentType.FINANCE,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    description=f"[财务报告] {period}",
                )
                await self.db["tasks"].insert_one(task.model_dump())

            return AgentResult(
                success=True,
                data=result,
                metadata={"action": "report_generated", "period": period},
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _general_finance(self, query: str) -> AgentResult:
        """通用财务咨询"""
        messages = [
            {"role": "system", "content": FINANCE_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        try:
            result = await self._chat(messages)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    def _format_transactions(self, transactions: list) -> str:
        """格式化交易记录"""
        if not transactions:
            return "暂无交易记录"

        lines = ["| 日期 | 描述 | 分类 | 金额 |", "|------|------|------|------|"]
        for t in transactions:
            date = t.get("created_at", "")
            if isinstance(date, datetime):
                date = date.strftime("%Y-%m-%d")
            lines.append(
                f"| {date} | {t.get('description', '')} | {t.get('category', '')} | ¥{t.get('amount', 0)} |"
            )
        return "\n".join(lines)
