"""工具单元测试"""

import pytest
import pytest_asyncio
import tempfile
import os

from app.tools.file.file import FileTool
from app.tools.base import ToolResult


class TestFileTool:
    """文件工具测试"""

    @pytest_asyncio.fixture
    async def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, temp_dir):
        tool = FileTool()
        filepath = os.path.join(temp_dir, "test.txt")

        write_result = await tool.execute(action="write", path=filepath, content="Hello World")
        assert write_result.success is True

        read_result = await tool.execute(action="read", path=filepath)
        assert read_result.success is True
        assert read_result.data["content"] == "Hello World"

    @pytest.mark.asyncio
    async def test_list_directory(self, temp_dir):
        tool = FileTool()
        for name in ["a.txt", "b.txt", "c.py"]:
            filepath = os.path.join(temp_dir, name)
            with open(filepath, "w") as f:
                f.write("test")

        result = await tool.execute(action="list", path=temp_dir)
        assert result.success is True
        assert result.data["count"] == 3

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_dir):
        tool = FileTool()
        result = await tool.execute(action="read", path=os.path.join(temp_dir, "nope.txt"))
        assert result.success is False
        assert "不存在" in result.error

    @pytest.mark.asyncio
    async def test_empty_path_returns_error(self):
        tool = FileTool()
        result = await tool.execute(action="read", path="")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_path_not_allowed(self):
        tool = FileTool(allowed_dirs=["/allowed/dir"])
        result = await tool.execute(action="read", path="/not/allowed/file.txt")
        assert result.success is False
        assert "不允许" in result.error

    @pytest.mark.asyncio
    async def test_exists_check(self, temp_dir):
        tool = FileTool()
        filepath = os.path.join(temp_dir, "exists.txt")
        with open(filepath, "w") as f:
            f.write("test")

        result = await tool.execute(action="exists", path=filepath)
        assert result.success is True
        assert result.data["exists"] is True

        result2 = await tool.execute(action="exists", path=os.path.join(temp_dir, "nope.txt"))
        assert result2.success is True
        assert result2.data["exists"] is False
