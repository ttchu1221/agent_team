"""三层记忆系统 (MongoDB)

- 短期记忆: 对话历史 + 会话摘要压缩
- 长期记忆: 关键词/标签索引的记忆条目
- 用户画像: 偏好、习惯、已知事实
"""

from __future__ import annotations

import structlog
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.task import ConversationDocument, MemoryEntry, UserProfile, SessionSummary

logger = structlog.get_logger()


class MemorySystem:
    """统一记忆系统"""

    def __init__(self, db: AsyncIOMotorDatabase, llm_router=None):
        self.db = db
        self.router = llm_router
        # 短期
        self.conversations = db["conversations"]
        self.summaries = db["session_summaries"]
        # 长期
        self.memories = db["memories"]
        # 用户画像
        self.profiles = db["user_profiles"]

    # ================================================================
    # 短期记忆：对话历史
    # ================================================================

    async def save_message(
        self, session_id: str, role: str, content: str, task_id: str | None = None
    ):
        """保存对话消息"""
        msg = ConversationDocument(
            session_id=session_id,
            role=role,
            content=content,
            task_id=task_id,
        )
        await self.conversations.insert_one(msg.model_dump())
        logger.debug("message_saved", session_id=session_id, role=role)

    async def get_history(
        self, session_id: str, limit: int = 20
    ) -> list[dict]:
        """获取会话历史"""
        cursor = (
            self.conversations.find({"session_id": session_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)

        return [
            {
                "role": doc["role"],
                "content": doc["content"],
                "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
            }
            for doc in reversed(docs)
        ]

    async def get_context_window(
        self, session_id: str, max_messages: int = 10
    ) -> list[dict]:
        """获取上下文窗口（用于 LLM 输入）

        如果消息数超过 max_messages，自动压缩早期消息为摘要。
        """
        history = await self.get_history(session_id, limit=50)

        if len(history) <= max_messages:
            return history

        # 需要压缩：取早期消息生成摘要
        early_messages = history[: -max_messages]
        recent_messages = history[-max_messages:]

        summary = await self._summarize_messages(session_id, early_messages)
        if summary:
            return [
                {"role": "system", "content": f"[之前的对话摘要] {summary}"},
                *recent_messages,
            ]

        return recent_messages

    async def _summarize_messages(
        self, session_id: str, messages: list[dict]
    ) -> str | None:
        """将多条消息压缩为摘要"""
        if not self.router or not messages:
            return None

        # 检查是否已有足够新的摘要
        existing = await self.summaries.find_one(
            {"session_id": session_id},
            sort=[("created_at", -1)],
        )
        if existing and existing.get("message_count", 0) >= len(messages) - 2:
            return existing["summary"]

        text = "\n".join(
            f"[{m['role']}] {m['content']}" for m in messages
        )

        try:
            summary = await self.router.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "请用 2-3 句话概括以下对话的要点，保留关键信息和决策。"
                            "只输出摘要，不要加任何前缀。"
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                task_type="simple",
                temperature=0.3,
            )

            # 保存摘要
            doc = SessionSummary(
                session_id=session_id,
                summary=summary,
                message_count=len(messages),
            )
            await self.summaries.insert_one(doc.model_dump())

            return summary
        except Exception as e:
            logger.error("summarize_failed", error=str(e))
            return None

    # ================================================================
    # 长期记忆：记忆存取
    # ================================================================

    async def save_memory(
        self,
        content: str,
        tags: list[str] | None = None,
        importance: int = 5,
        source: str = "conversation",
        session_id: str | None = None,
        task_id: str | None = None,
    ):
        """保存一条长期记忆"""
        entry = MemoryEntry(
            content=content,
            tags=tags or [],
            source=source,
            importance=importance,
            session_id=session_id,
            task_id=task_id,
        )
        await self.memories.insert_one(entry.model_dump())
        logger.info("memory_saved", tags=tags, importance=importance)

    async def recall(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """检索长期记忆

        策略：先按标签精确匹配，再按关键词模糊匹配，合并去重后按重要度排序。
        """
        results = []
        seen_ids = set()

        # 1. 标签匹配
        if tags:
            tag_filter = {"tags": {"$in": tags}}
            cursor = (
                self.memories.find(tag_filter)
                .sort([("importance", -1), ("created_at", -1)])
                .limit(limit)
            )
            docs = await cursor.to_list(length=limit)
            for doc in docs:
                doc_id = str(doc.get("_id", ""))
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    results.append(self._format_memory(doc))
                    # 更新访问计数
                    await self.memories.update_one(
                        {"_id": doc["_id"]},
                        {"$inc": {"access_count": 1}, "$set": {"last_accessed": datetime.now(timezone.utc)}},
                    )

        # 2. 关键词匹配（在 content 中搜索）
        if len(results) < limit:
            # 提取关键词（简单分词）
            keywords = [w for w in query.split() if len(w) >= 2]
            if keywords:
                keyword_filter = {
                    "$or": [
                        {"content": {"$regex": kw, "$options": "i"}}
                        for kw in keywords[:5]
                    ]
                }
                remaining = limit - len(results)
                cursor = (
                    self.memories.find(keyword_filter)
                    .sort([("importance", -1), ("created_at", -1)])
                    .limit(remaining * 2)
                )
                docs = await cursor.to_list(length=remaining * 2)
                for doc in docs:
                    doc_id = str(doc.get("_id", ""))
                    if doc_id not in seen_ids and len(results) < limit:
                        seen_ids.add(doc_id)
                        results.append(self._format_memory(doc))
                        await self.memories.update_one(
                            {"_id": doc["_id"]},
                            {"$inc": {"access_count": 1}, "$set": {"last_accessed": datetime.now(timezone.utc)}},
                        )

        return results

    async def extract_and_save(
        self, session_id: str, user_message: str, assistant_reply: str
    ):
        """从对话中自动提取值得记住的信息并保存

        由 LLM 判断对话中是否有值得长期记住的内容。
        """
        if not self.router:
            return

        prompt = f"""分析以下对话，提取值得长期记住的信息（如用户偏好、重要事实、决策、习惯等）。

用户: {user_message}
助手: {assistant_reply}

如果有值得记住的信息，返回 JSON:
{{"memories": [{{"content": "记忆内容", "tags": ["标签1", "标签2"], "importance": 7}}]}}

如果没有值得记住的，返回:
{{"memories": []}}

只输出 JSON，不要其他内容。"""

        try:
            result = await self.router.chat_json(
                messages=[
                    {"role": "system", "content": "你是一个记忆提取器，从对话中识别值得长期记住的信息。"},
                    {"role": "user", "content": prompt},
                ],
                task_type="simple",
                temperature=0.2,
            )

            memories = result.get("memories", [])
            for mem in memories:
                content = mem.get("content", "").strip()
                if content:
                    await self.save_memory(
                        content=content,
                        tags=mem.get("tags", []),
                        importance=mem.get("importance", 5),
                        source="extracted",
                        session_id=session_id,
                    )
                    logger.info("memory_extracted", content=content[:50])

        except Exception as e:
            logger.error("memory_extract_failed", error=str(e))

    async def get_memory_context(self, query: str, limit: int = 3) -> str:
        """获取与当前对话相关的记忆上下文（用于注入 LLM 提示）"""
        memories = await self.recall(query, limit=limit)
        if not memories:
            return ""
        lines = [f"- {m['content']}" for m in memories]
        return "[相关记忆]\n" + "\n".join(lines)

    # ================================================================
    # 用户画像
    # ================================================================

    async def get_profile(self, user_id: str = "default") -> dict:
        """获取用户画像"""
        doc = await self.profiles.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return doc
        return UserProfile(user_id=user_id).model_dump()

    async def update_profile(self, user_id: str = "default", **fields):
        """更新用户画像字段"""
        fields["updated_at"] = datetime.now(timezone.utc)
        await self.profiles.update_one(
            {"user_id": user_id},
            {"$set": fields},
            upsert=True,
        )
        logger.info("profile_updated", user_id=user_id, fields=list(fields.keys()))

    async def add_profile_fact(self, fact: str, user_id: str = "default"):
        """添加一条用户事实"""
        await self.profiles.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {"facts": fact},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )

    async def add_profile_habit(self, habit: str, user_id: str = "default"):
        """添加一条用户习惯"""
        await self.profiles.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {"habits": habit},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )

    async def extract_and_update_profile(
        self, user_message: str, assistant_reply: str, user_id: str = "default"
    ):
        """从对话中自动提取用户信息并更新画像"""
        if not self.router:
            return

        profile = await self.get_profile(user_id)

        prompt = f"""分析以下对话，提取关于用户的新信息。

当前已知用户信息:
- 职业: {profile.get('occupation', '未知')}
- 研究方向: {', '.join(profile.get('research_fields', [])) or '未知'}
- 已知事实: {', '.join(profile.get('facts', [])[-5:]) or '无'}
- 习惯: {', '.join(profile.get('habits', [])[-5:]) or '无'}

对话:
用户: {user_message}
助手: {assistant_reply}

如果有新的用户信息，返回 JSON:
{{"update": true, "occupation": "新职业(如有)", "research_fields": ["新方向(如有)"], "facts": ["新事实(如有)"], "habits": ["新习惯(如有)"], "preferences": {{"key": "value"}}}}

如果没有新信息:
{{"update": false}}

只输出 JSON。"""

        try:
            result = await self.router.chat_json(
                messages=[
                    {"role": "system", "content": "你是一个用户画像提取器。只提取对话中明确提到的用户信息。"},
                    {"role": "user", "content": prompt},
                ],
                task_type="simple",
                temperature=0.2,
            )

            if not result.get("update"):
                return

            updates = {}
            if result.get("occupation"):
                updates["occupation"] = result["occupation"]
            if result.get("research_fields"):
                existing_fields = set(profile.get("research_fields", []))
                existing_fields.update(result["research_fields"])
                updates["research_fields"] = list(existing_fields)
            if result.get("preferences"):
                existing_prefs = profile.get("preferences", {})
                existing_prefs.update(result["preferences"])
                updates["preferences"] = existing_prefs

            if updates:
                await self.update_profile(user_id, **updates)

            for fact in result.get("facts", []):
                if fact:
                    await self.add_profile_fact(fact, user_id)

            for habit in result.get("habits", []):
                if habit:
                    await self.add_profile_habit(habit, user_id)

        except Exception as e:
            logger.error("profile_extract_failed", error=str(e))

    async def get_profile_context(self, user_id: str = "default") -> str:
        """获取用户画像上下文（用于注入 LLM 提示）"""
        profile = await self.get_profile(user_id)
        parts = []
        if profile.get("occupation"):
            parts.append(f"职业: {profile['occupation']}")
        if profile.get("research_fields"):
            parts.append(f"研究方向: {', '.join(profile['research_fields'])}")
        if profile.get("facts"):
            parts.append(f"已知事实: {'; '.join(profile['facts'][-5:])}")
        if profile.get("habits"):
            parts.append(f"习惯: {'; '.join(profile['habits'][-3:])}")
        if profile.get("preferences"):
            prefs = ", ".join(f"{k}={v}" for k, v in profile["preferences"].items())
            parts.append(f"偏好: {prefs}")
        if not parts:
            return ""
        return "[用户画像]\n" + "\n".join(parts)

    # ================================================================
    # 辅助
    # ================================================================

    @staticmethod
    def _format_memory(doc: dict) -> dict:
        return {
            "id": str(doc.get("_id", "")),
            "content": doc["content"],
            "tags": doc.get("tags", []),
            "importance": doc.get("importance", 5),
            "source": doc.get("source", ""),
            "created_at": doc.get("created_at", ""),
        }
