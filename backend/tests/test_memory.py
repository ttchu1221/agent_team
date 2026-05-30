"""记忆系统单元测试"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.models.task import MemoryEntry, UserProfile, SessionSummary


class TestMemoryModels:
    """记忆数据模型测试"""

    def test_memory_entry_defaults(self):
        entry = MemoryEntry(content="用户喜欢Python")
        assert entry.content == "用户喜欢Python"
        assert entry.tags == []
        assert entry.importance == 5
        assert entry.source == "conversation"
        assert entry.access_count == 0

    def test_memory_entry_with_tags(self):
        entry = MemoryEntry(content="研究方向", tags=["学术", "NLP"], importance=8)
        assert "学术" in entry.tags
        assert entry.importance == 8

    def test_user_profile_defaults(self):
        profile = UserProfile()
        assert profile.user_id == "default"
        assert profile.occupation is None
        assert profile.facts == []
        assert profile.habits == []
        assert profile.preferences == {}

    def test_user_profile_with_data(self):
        profile = UserProfile(
            user_id="test",
            occupation="研究员",
            research_fields=["NLP", "LLM"],
            facts=["有5年经验"],
            habits=["早上看论文"],
        )
        assert profile.occupation == "研究员"
        assert len(profile.research_fields) == 2

    def test_session_summary(self):
        summary = SessionSummary(
            session_id="sess-1",
            summary="讨论了项目架构",
            message_count=10,
            key_points=["选择MongoDB", "使用FastAPI"],
        )
        assert summary.message_count == 10
        assert len(summary.key_points) == 2


class TestMemorySystem:
    """MemorySystem 核心逻辑测试（不依赖真实 MongoDB）"""

    def _make_mock_db(self):
        """创建 mock MongoDB"""
        db = MagicMock()
        # 每个 collection 返回一个 mock
        for name in ["conversations", "session_summaries", "memories", "user_profiles"]:
            collection = MagicMock()
            collection.find = MagicMock()
            collection.find_one = AsyncMock(return_value=None)
            collection.insert_one = AsyncMock()
            collection.update_one = AsyncMock()
            collection.create_index = AsyncMock()
            setattr(db, "__getitem__", lambda self, key, _cols={
                "conversations": collection,
                "session_summaries": MagicMock(find_one=AsyncMock(return_value=None), insert_one=AsyncMock()),
                "memories": MagicMock(
                    find=MagicMock(),
                    find_one=AsyncMock(return_value=None),
                    insert_one=AsyncMock(),
                    update_one=AsyncMock(),
                ),
                "user_profiles": MagicMock(
                    find_one=AsyncMock(return_value=None),
                    update_one=AsyncMock(),
                ),
            }: _cols.get(key, MagicMock()))
        return db

    def test_format_memory(self):
        from app.core.memory import MemorySystem
        doc = {
            "_id": "abc123",
            "content": "test content",
            "tags": ["tag1"],
            "importance": 7,
            "source": "conversation",
            "created_at": datetime.now(timezone.utc),
        }
        result = MemorySystem._format_memory(doc)
        assert result["id"] == "abc123"
        assert result["content"] == "test content"
        assert result["tags"] == ["tag1"]
        assert result["importance"] == 7
