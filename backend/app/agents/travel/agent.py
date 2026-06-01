from __future__ import annotations

"""Travel Agent - 旅行规划助手 (数据库 + 搜索集成)"""

import uuid
import structlog
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent, AgentResult
from app.models.task import TaskDocument, TaskStatus, AgentType
from app.tools.search.search import SearchTool

logger = structlog.get_logger()

TRAVEL_SYSTEM_PROMPT = """你是一位专业的旅行规划师，擅长：
1. 目的地信息查询 - 提供签证、天气、货币等实用信息
2. 行程规划与优化 - 设计合理的每日行程
3. 住宿推荐与比价 - 推荐性价比高的住宿
4. 交通方案规划 - 规划最优交通路线
5. 预算估算与控制 - 帮助控制旅行预算

你的特点：
- 熟悉全球热门旅游目的地
- 善于根据用户偏好定制行程
- 注重性价比，提供多种选择
- 输出详细、可执行的行程方案

请以Markdown格式输出，包含表格和清单。
"""


class TravelAgent(BaseAgent):
    """Travel Agent - 旅行规划相关任务"""

    name = "travel"
    description = "旅行规划助手：行程规划、住宿推荐、交通方案、预算估算、目的地搜索"
    preferred_task_type = "chat"

    def __init__(self, router=None, db: AsyncIOMotorDatabase | None = None):
        super().__init__(router=router, db=db)
        self.search_tool = SearchTool()

    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """执行旅行规划相关任务"""
        task_type = task_input.get("task_type", "general")
        content = task_input.get("content", "")

        if task_type == "plan_trip":
            return await self._plan_trip(
                content,
                task_input.get("days", 5),
                task_input.get("budget", "medium"),
                task_input.get("travelers", 1),
            )
        elif task_type == "search_destination":
            return await self._search_destination(content, task_input.get("max_results", 5))
        elif task_type == "destination_info":
            return await self._get_destination_info(content)
        elif task_type == "accommodation":
            return await self._recommend_accommodation(
                content,
                task_input.get("budget", "medium"),
            )
        elif task_type == "transportation":
            return await self._plan_transportation(content)
        elif task_type == "budget":
            return await self._estimate_budget(
                content,
                task_input.get("days", 5),
                task_input.get("travelers", 1),
            )
        else:
            return await self._general_travel(content)

    async def _search_destination(self, destination: str, max_results: int = 5) -> AgentResult:
        """搜索目的地信息"""
        try:
            search_result = await self.search_tool.execute(
                f"{destination} travel tourism", max_results=max_results
            )

            if not search_result.success:
                return AgentResult(success=False, error=search_result.error)

            papers = search_result.data
            papers_text = "\n".join([
                f"- {p['title']} ({p.get('year', 'N/A')})"
                for p in papers
            ])

            messages = [
                {"role": "system", "content": TRAVEL_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"""根据搜索结果，介绍 "{destination}" 的旅游信息：

{papers_text}

请提供：
1. **目的地亮点** - 最值得去的景点
2. **最佳旅行时间** - 推荐的旅行季节
3. **特色体验** - 当地特色活动
4. **实用信息** - 签证、货币、语言等""",
                },
            ]

            result = await self._chat(messages, temperature=0.5)

            # 保存到数据库
            if self.db is not None:
                record_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=record_id,
                    user_input=destination,
                    agent_type=AgentType.TRAVEL,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    description=f"[目的地搜索] {destination}",
                )
                await self.db["tasks"].insert_one(task.model_dump())

            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _plan_trip(
        self,
        destination: str,
        days: int = 5,
        budget: str = "medium",
        travelers: int = 1,
    ) -> AgentResult:
        """规划完整行程"""
        messages = [
            {"role": "system", "content": TRAVEL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请帮我规划一次旅行：

**目的地**: {destination}
**旅行天数**: {days}天
**预算水平**: {budget} (low/medium/high)
**出行人数**: {travelers}人

请提供：
1. **目的地概览** - 基本信息（签证、天气、货币、语言）
2. **每日行程** - 详细的每日安排
3. **住宿推荐** - 不同档次的住宿选择
4. **交通方案** - 到达和当地交通
5. **美食推荐** - 必吃美食和餐厅
6. **预算明细** - 详细费用估算
7. **必备物品** - 行李清单
8. **实用贴士** - 当地注意事项""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.5)

            # 存入数据库
            if self.db is not None:
                plan_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=plan_id,
                    user_input=destination,
                    agent_type=AgentType.TRAVEL,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    description=f"[旅行计划] {destination} {days}天",
                )
                await self.db["tasks"].insert_one(task.model_dump())
                logger.info("trip_plan_created", plan_id=plan_id, destination=destination)

            return AgentResult(
                success=True,
                data=result,
                metadata={"action": "trip_plan_created", "destination": destination},
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _get_destination_info(self, destination: str) -> AgentResult:
        """获取目的地信息"""
        messages = [
            {"role": "system", "content": TRAVEL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请提供 {destination} 的详细信息：

1. **基本信息** - 位置、人口、语言、货币
2. **签证政策** - 中国公民签证要求
3. **最佳旅行时间** - 推荐季节和原因
4. **天气情况** - 各季节气温和降雨
5. **安全提示** - 治安状况和注意事项
6. **文化习俗** - 当地禁忌和礼仪
7. **必去景点** - TOP 10 景点推荐
8. **特色美食** - 必尝美食清单""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _recommend_accommodation(
        self, destination: str, budget: str = "medium"
    ) -> AgentResult:
        """推荐住宿"""
        messages = [
            {"role": "system", "content": TRAVEL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请为 {destination} 推荐住宿：

**预算水平**: {budget}

请推荐：
1. **酒店** - 不价位段的酒店推荐
2. **民宿** - Airbnb/途家等民宿选择
3. **青旅** - 适合背包客的青旅
4. **位置建议** - 住在哪个区域最方便
5. **预订平台** - 推荐的预订渠道
6. **省钱技巧** - 住宿省钱攻略

每项请标注：价格范围、位置、评分、特色。""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.5)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _plan_transportation(self, route_info: str) -> AgentResult:
        """规划交通方案"""
        messages = [
            {"role": "system", "content": TRAVEL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请规划以下路线的交通方案：

**路线信息**: {route_info}

请提供：
1. **飞机** - 航班选择和价格范围
2. **火车** - 高铁/火车方案
3. **自驾** - 自驾路线和注意事项
4. **当地交通** - 公交/地铁/打车指南
5. **对比分析** - 各方案的优缺点
6. **推荐方案** - 最优选择建议""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _estimate_budget(
        self, destination: str, days: int = 5, travelers: int = 1
    ) -> AgentResult:
        """估算旅行预算"""
        messages = [
            {"role": "system", "content": TRAVEL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请估算旅行预算：

**目的地**: {destination}
**旅行天数**: {days}天
**出行人数**: {travelers}人

请提供：
1. **交通费用** - 往返和当地交通
2. **住宿费用** - 不同档次的住宿预算
3. **餐饮费用** - 每日餐饮预算
4. **景点门票** - 主要景点门票
5. **购物预算** - 购物和纪念品
6. **其他费用** - 签证、保险、小费等
7. **总预算** - 低/中/高三档预算
8. **省钱建议** - 降低预算的技巧""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.3)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _general_travel(self, query: str) -> AgentResult:
        """通用旅行咨询"""
        messages = [
            {"role": "system", "content": TRAVEL_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        try:
            result = await self._chat(messages)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))
