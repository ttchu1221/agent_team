"""Obsidian 笔记保存工具 - 将内容保存为 Markdown 文件到 Obsidian Vault"""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import structlog

from app.tools.base import BaseTool, ToolResult

logger = structlog.get_logger()

# 默认 Obsidian Vault 路径
DEFAULT_VAULT_PATH = os.path.expanduser("~/Obsidian")

# 笔记存放的子目录
DEFAULT_SUBFOLDER = "Agent笔记"


def _sanitize_filename(name: str, max_length: int = 80) -> str:
    """将任意字符串转为合法文件名"""
    # 1. Unicode 规范化
    name = unicodedata.normalize("NFC", name)
    # 2. 去除不合法字符（保留中英文、数字、连字符、下划线、空格）
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    # 3. 将连续空格合并为单个空格
    name = re.sub(r"\s+", " ", name).strip()
    # 4. 截断
    if len(name) > max_length:
        name = name[:max_length].rstrip()
    # 5. 去除尾部的点（Windows 兼容）
    name = name.rstrip(". ")
    return name or "未命名笔记"


class ObsidianTool(BaseTool):
    """将内容保存为 Markdown 笔记到 Obsidian Vault"""

    name = "obsidian_save"
    description = "将内容保存为 Markdown 文件到 Obsidian Vault"

    def __init__(
        self,
        vault_path: str | None = None,
        subfolder: str | None = None,
    ):
        self.vault_path = Path(vault_path or DEFAULT_VAULT_PATH)
        self.subfolder = subfolder or DEFAULT_SUBFOLDER

    def _get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "笔记标题"},
                "content": {"type": "string", "description": "Markdown 内容"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表"},
                "source": {"type": "string", "description": "来源说明"},
                "subfolder": {"type": "string", "description": "子目录"},
            },
            "required": ["title", "content"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        """
        保存内容到 Obsidian Vault。

        参数:
            title: 笔记标题（必填）
            content: Markdown 内容（必填）
            tags: 标签列表（可选）
            source: 来源说明（可选）
            subfolder: 子目录（可选，覆盖默认值）
        """
        title = kwargs.get("title", "")
        content = kwargs.get("content", "")
        tags = kwargs.get("tags", [])
        source = kwargs.get("source", "")
        subfolder = kwargs.get("subfolder", self.subfolder)

        if not title:
            return ToolResult(success=False, error="title 不能为空")
        if not content:
            return ToolResult(success=False, error="content 不能为空")

        try:
            # 构建目标目录
            target_dir = self.vault_path / subfolder
            target_dir.mkdir(parents=True, exist_ok=True)

            # 构建文件名：标题_日期.md
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{_sanitize_filename(title)}_{date_str}.md"
            file_path = target_dir / filename

            # 如果同名文件已存在，追加序号
            counter = 1
            while file_path.exists():
                filename = f"{_sanitize_filename(title)}_{date_str}_{counter}.md"
                file_path = target_dir / filename
                counter += 1

            # 构建 frontmatter
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tags_str = "\n".join(f"  - {t}" for t in tags) if tags else "  - agent"
            source_line = f"\n来源: {source}" if source else ""

            frontmatter = f"""---
created: {now}
tags:
{tags_str}
source: Agent{source_line}
---

"""

            # 组装完整内容
            full_content = frontmatter + content

            # 写入文件
            file_path.write_text(full_content, encoding="utf-8")

            logger.info(
                "obsidian_note_saved",
                title=title,
                path=str(file_path),
                size=len(full_content),
            )

            return ToolResult(
                success=True,
                data={
                    "path": str(file_path),
                    "filename": filename,
                    "title": title,
                    "size": len(full_content),
                },
                metadata={"vault": str(self.vault_path), "subfolder": subfolder},
            )

        except Exception as e:
            logger.error("obsidian_save_error", title=title, error=str(e))
            return ToolResult(success=False, error=str(e))
