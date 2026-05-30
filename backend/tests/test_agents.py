"""Agent 单元测试"""

import pytest
from unittest.mock import MagicMock

from app.agents.base import AgentResult
from app.agents.chief.agent import ChiefAgent
from app.agents.career.agent import CareerAgent
from app.agents.research.agent import ResearchAgent
from app.agents.life.agent import LifeAgent
from app.agents.factory import AgentFactory
from app.tools.base import ToolResult, ToolRegistry


class TestAgentFactory:
    """Agent 工厂测试"""

    def test_create_chief_agent(self):
        agent = AgentFactory.create("chief")
        assert isinstance(agent, ChiefAgent)
        assert agent.name == "chief"

    def test_create_career_agent(self):
        agent = AgentFactory.create("career")
        assert isinstance(agent, CareerAgent)
        assert agent.name == "career"

    def test_create_research_agent(self):
        agent = AgentFactory.create("research")
        assert isinstance(agent, ResearchAgent)
        assert agent.name == "research"

    def test_create_life_agent(self):
        agent = AgentFactory.create("life")
        assert isinstance(agent, LifeAgent)
        assert agent.name == "life"

    def test_create_unknown_agent_raises(self):
        with pytest.raises(ValueError, match="Unknown agent type"):
            AgentFactory.create("unknown")

    def test_list_agents(self):
        agents = AgentFactory.list_agents()
        names = [a["name"] for a in agents]
        assert "career" in names
        assert "research" in names
        assert "life" in names


class TestToolRegistry:
    """工具注册中心测试"""

    def test_register_tool(self):
        registry = ToolRegistry()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_tool.to_function_schema.return_value = {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {},
        }
        registry.register(mock_tool)
        assert registry.get("test_tool") == mock_tool

    def test_get_nonexistent_tool(self):
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.to_function_schema.return_value = {
            "name": "test_tool",
            "description": "desc",
            "parameters": {},
        }
        registry.register(mock_tool)
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"


class TestToolResult:
    """工具结果测试"""

    def test_success_result(self):
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_failure_result(self):
        result = ToolResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"


class TestAgentResult:
    """Agent 结果测试"""

    def test_success_result(self):
        result = AgentResult(success=True, data="some result")
        assert result.success is True
        assert result.data == "some result"

    def test_failure_result(self):
        result = AgentResult(success=False, error="agent error")
        assert result.success is False
        assert result.error == "agent error"
