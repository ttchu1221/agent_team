"""搜索工具 - 学术论文搜索 (CrossRef + Semantic Scholar)"""

import httpx
import structlog

from app.tools.base import BaseTool, ToolResult

logger = structlog.get_logger()


class SearchTool(BaseTool):
    """学术搜索工具 - 使用 CrossRef / Semantic Scholar API"""

    name = "search"
    description = "搜索学术论文"

    async def execute(self, query: str = "", max_results: int = 5, source: str = "crossref", **kwargs) -> ToolResult:
        """
        执行搜索

        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            source: 数据源 (crossref/semantic_scholar)
        """
        if not query:
            return ToolResult(success=False, error="搜索关键词不能为空")

        try:
            if source == "semantic_scholar":
                results = await self._search_semantic_scholar(query, max_results)
            else:
                results = await self._search_crossref(query, max_results)

            return ToolResult(
                success=True,
                data=results,
                metadata={"query": query, "result_count": len(results), "source": source},
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error("search_failed", query=query, error=error_msg)
            return ToolResult(success=False, error=error_msg)

    async def _search_crossref(self, query: str, max_results: int) -> list[dict]:
        """使用 CrossRef API 搜索论文（免费、稳定）"""
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": max_results,
            "sort": "relevance",
            "select": "DOI,title,author,published-print,abstract,URL,is-referenced-by-count,subject",
        }

        headers = {
            "User-Agent": "PersonalAgentTeam/1.0 (mailto:research@example.com)",
        }

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

        data = response.json()
        items = data.get("message", {}).get("items", [])

        results = []
        for item in items[:max_results]:
            # 提取标题
            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""

            # 提取作者
            authors = []
            for author in item.get("author", [])[:5]:
                name_parts = []
                if author.get("given"):
                    name_parts.append(author["given"])
                if author.get("family"):
                    name_parts.append(author["family"])
                if name_parts:
                    authors.append(" ".join(name_parts))

            # 提取发表年份
            year = ""
            pub_date = item.get("published-print", {}).get("date-parts", [[]])
            if pub_date and pub_date[0]:
                year = str(pub_date[0][0])

            results.append({
                "title": title,
                "abstract": (item.get("abstract") or "")[:500],
                "authors": authors,
                "year": year,
                "citation_count": item.get("is-referenced-by-count", 0),
                "doi": item.get("DOI", ""),
                "subjects": item.get("subject", [])[:3],
                "url": item.get("URL", ""),
            })

        return results

    async def _search_semantic_scholar(self, query: str, max_results: int) -> list[dict]:
        """使用 Semantic Scholar API 搜索论文"""
        import asyncio

        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,url,externalIds,citationCount,fieldsOfStudy",
        }

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(url, params=params)

                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    raise Exception("API 请求过于频繁，请稍后再试")

                response.raise_for_status()

        data = response.json()
        papers = data.get("data", [])

        results = []
        for paper in papers[:max_results]:
            authors = [a.get("name", "") for a in paper.get("authors", [])[:5]]
            external_ids = paper.get("externalIds", {})
            arxiv_id = external_ids.get("ArXiv", "")
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else ""

            results.append({
                "title": paper.get("title", ""),
                "abstract": (paper.get("abstract") or "")[:500],
                "authors": authors,
                "year": paper.get("year", ""),
                "citation_count": paper.get("citationCount", 0),
                "fields_of_study": paper.get("fieldsOfStudy", []),
                "arxiv_id": arxiv_id,
                "pdf_url": pdf_url,
                "url": paper.get("url", ""),
            })

        return results

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
                "source": {
                    "type": "string",
                    "enum": ["crossref", "semantic_scholar"],
                    "description": "数据源",
                    "default": "crossref",
                },
            },
            "required": ["query"],
        }
