"""搜索工具"""

import httpx
import structlog

from app.tools.base import BaseTool, ToolResult
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class SearchTool(BaseTool):
    """Web 搜索工具 - 使用搜索 API 进行信息检索"""

    name = "search"
    description = "搜索互联网获取最新信息"

    async def execute(self, query: str = "", max_results: int = 5, **kwargs) -> ToolResult:
        """
        执行搜索

        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
        """
        if not query:
            return ToolResult(success=False, error="搜索关键词不能为空")

        try:
            # 使用 DuckDuckGo 作为默认搜索（无需 API Key）
            results = await self._search_ddg(query, max_results)
            return ToolResult(
                success=True,
                data=results,
                metadata={"query": query, "result_count": len(results)},
            )
        except Exception as e:
            logger.error("search_failed", query=query, error=str(e))
            return ToolResult(success=False, error=str(e))

    async def _search_ddg(self, query: str, max_results: int) -> list[dict]:
        """使用 DuckDuckGo 搜索"""
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_redirect": "1"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        # 解析 DuckDuckGo 结果
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", ""),
                "snippet": data.get("AbstractText", ""),
                "url": data.get("AbstractURL", ""),
            })

        for item in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(item, dict) and item.get("Text"):
                results.append({
                    "title": item.get("Text", "")[:100],
                    "snippet": item.get("Text", ""),
                    "url": item.get("FirstURL", ""),
                })

        return results[:max_results]

    def _get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数",
                    "default": 5,
                },
            },
            "required": ["query"],
        }
