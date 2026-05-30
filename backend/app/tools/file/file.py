from __future__ import annotations

"""文件工具"""

import os
import pathlib
import structlog

from app.tools.base import BaseTool, ToolResult

logger = structlog.get_logger()


class FileTool(BaseTool):
    """文件操作工具 - 读取、写入、列出文件"""

    name = "file"
    description = "文件系统操作：读取、写入、列出目录内容"

    def __init__(self, allowed_dirs: list[str] | None = None):
        """
        Args:
            allowed_dirs: 允许访问的目录列表，None 表示不限制
        """
        self.allowed_dirs = allowed_dirs

    async def execute(self, action: str = "read", path: str = "", content: str = "", **kwargs) -> ToolResult:
        """
        执行文件操作

        Args:
            action: 操作类型 (read/write/list/exists)
            path: 文件路径
            content: 写入内容（仅 write 操作需要）
        """
        if not path:
            return ToolResult(success=False, error="文件路径不能为空")

        # 安全检查
        if not self._is_path_allowed(path):
            return ToolResult(success=False, error=f"不允许访问路径: {path}")

        try:
            if action == "read":
                return await self._read_file(path)
            elif action == "write":
                return await self._write_file(path, content)
            elif action == "list":
                return await self._list_directory(path)
            elif action == "exists":
                return self._check_exists(path)
            else:
                return ToolResult(success=False, error=f"不支持的操作: {action}")
        except Exception as e:
            logger.error("file_operation_failed", action=action, path=path, error=str(e))
            return ToolResult(success=False, error=str(e))

    async def _read_file(self, path: str) -> ToolResult:
        """读取文件"""
        filepath = pathlib.Path(path)
        if not filepath.exists():
            return ToolResult(success=False, error=f"文件不存在: {path}")

        if filepath.stat().st_size > 10 * 1024 * 1024:  # 10MB 限制
            return ToolResult(success=False, error="文件过大（>10MB）")

        content = filepath.read_text(encoding="utf-8", errors="replace")
        return ToolResult(
            success=True,
            data={"content": content, "size": len(content), "path": path},
        )

    async def _write_file(self, path: str, content: str) -> ToolResult:
        """写入文件"""
        filepath = pathlib.Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return ToolResult(
            success=True,
            data={"path": path, "size": len(content)},
            metadata={"action": "write"},
        )

    async def _list_directory(self, path: str) -> ToolResult:
        """列出目录内容"""
        dirpath = pathlib.Path(path)
        if not dirpath.exists():
            return ToolResult(success=False, error=f"目录不存在: {path}")
        if not dirpath.is_dir():
            return ToolResult(success=False, error=f"不是目录: {path}")

        entries = []
        for entry in sorted(dirpath.iterdir()):
            entries.append({
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else None,
            })

        return ToolResult(
            success=True,
            data={"path": path, "entries": entries, "count": len(entries)},
        )

    def _check_exists(self, path: str) -> ToolResult:
        """检查文件是否存在"""
        exists = pathlib.Path(path).exists()
        return ToolResult(success=True, data={"path": path, "exists": exists})

    def _is_path_allowed(self, path: str) -> bool:
        """检查路径是否在允许范围内"""
        if self.allowed_dirs is None:
            return True
        resolved = str(pathlib.Path(path).resolve())
        return any(resolved.startswith(d) for d in self.allowed_dirs)

    def _get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "list", "exists"],
                    "description": "文件操作类型",
                },
                "path": {
                    "type": "string",
                    "description": "文件或目录路径",
                },
                "content": {
                    "type": "string",
                    "description": "写入的内容（仅 write 操作）",
                },
            },
            "required": ["action", "path"],
        }
