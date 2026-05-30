"""浏览器工具（简化版 - 使用 httpx 抓取页面）"""

import httpx
from bs4 import BeautifulSoup
import structlog

from app.tools.base import BaseTool, ToolResult

logger = structlog.get_logger()


class BrowserTool(BaseTool):
    """网页抓取工具 - 获取并解析网页内容"""

    name = "browser"
    description = "抓取网页内容并提取文本"

    async def execute(self, url: str = "", action: str = "fetch", **kwargs) -> ToolResult:
        """
        抓取网页

        Args:
            url: 目标 URL
            action: 操作类型 (fetch/screenshot)
        """
        if not url:
            return ToolResult(success=False, error="URL 不能为空")

        if action == "fetch":
            return await self._fetch_page(url)
        else:
            return ToolResult(success=False, error=f"不支持的操作: {action}")

    async def _fetch_page(self, url: str) -> ToolResult:
        """抓取并解析网页"""
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": "PersonalAgentTeam/1.0"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 移除 script 和 style
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            title = soup.title.string if soup.title else ""
            text = soup.get_text(separator="\n", strip=True)

            # 截断过长内容
            if len(text) > 10000:
                text = text[:10000] + "\n... (内容已截断)"

            return ToolResult(
                success=True,
                data={
                    "url": url,
                    "title": title,
                    "content": text,
                    "status_code": response.status_code,
                },
            )
        except httpx.HTTPError as e:
            return ToolResult(success=False, error=f"HTTP 错误: {e}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "目标网页 URL",
                },
                "action": {
                    "type": "string",
                    "enum": ["fetch"],
                    "default": "fetch",
                },
            },
            "required": ["url"],
        }
