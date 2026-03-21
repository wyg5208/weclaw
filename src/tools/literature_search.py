"""文献检索工具 — 基于 OpenAlex 的学术论文检索。

支持动作：
- search_papers: 搜索学术论文
- get_paper_details: 获取论文详情
- download_pdf: 下载论文 PDF
- get_citations: 获取引用关系
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from datetime import datetime

import httpx

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# OpenAlex API 基础 URL
BASE_URL = "https://api.openalex.org"


class LiteratureSearchTool(BaseTool):
    """学术文献检索工具（基于 OpenAlex）。"""

    name = "literature_search"
    emoji = "📚"
    title = "文献检索"
    description = "学术文献检索：基于 OpenAlex 搜索论文、获取详情、下载PDF、查看引用"
    timeout = 60

    def __init__(self, output_dir: str = ""):
        """初始化文献检索工具。
        
        Args:
            output_dir: PDF 下载输出目录，为空时使用 generated/{date}
        """
        self.output_dir = output_dir

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="search_papers",
                description="搜索学术论文。支持关键词搜索、年份过滤和排序。",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大结果数，默认10，最多25",
                    },
                    "year_from": {
                        "type": "integer",
                        "description": "起始年份（如 2020）",
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序方式",
                        "enum": ["relevance", "cited_by_count", "publication_date"],
                    },
                },
                required_params=["query"],
            ),
            ActionDef(
                name="get_paper_details",
                description="获取论文详情，包括标题、作者、摘要、引用数、发表期刊等信息。",
                parameters={
                    "paper_id": {
                        "type": "string",
                        "description": "论文ID（OpenAlex ID 如 W2741809807，或 DOI 如 10.1038/nature12373）",
                    },
                },
                required_params=["paper_id"],
            ),
            ActionDef(
                name="download_pdf",
                description="下载论文 PDF（仅限开放获取论文）。",
                parameters={
                    "paper_id": {
                        "type": "string",
                        "description": "论文ID（OpenAlex ID 或 DOI）",
                    },
                    "save_path": {
                        "type": "string",
                        "description": "保存路径（可选，默认保存到 generated 目录）",
                    },
                },
                required_params=["paper_id"],
            ),
            ActionDef(
                name="get_citations",
                description="获取引用该论文的其他论文列表。",
                parameters={
                    "paper_id": {
                        "type": "string",
                        "description": "论文ID（OpenAlex ID 或 DOI）",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大结果数，默认10",
                    },
                },
                required_params=["paper_id"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        handlers = {
            "search_papers": self._search_papers,
            "get_paper_details": self._get_paper_details,
            "download_pdf": self._download_pdf,
            "get_citations": self._get_citations,
        }
        handler = handlers.get(action)
        if handler is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}",
            )
        return await handler(params)

    # ------------------------------------------------------------------
    # search_papers - 搜索学术论文
    # ------------------------------------------------------------------

    async def _search_papers(self, params: dict[str, Any]) -> ToolResult:
        query = params.get("query", "").strip()
        if not query:
            return ToolResult(status=ToolResultStatus.ERROR, error="搜索关键词不能为空")

        max_results = int(params.get("max_results", 10))
        max_results = max(1, min(max_results, 25))  # 限制 1-25
        year_from = params.get("year_from")
        sort_by = params.get("sort_by", "relevance")

        url = f"{BASE_URL}/works"
        api_params: dict[str, Any] = {
            "search": query,
            "per_page": max_results,
        }

        # 排序
        if sort_by == "cited_by_count":
            api_params["sort"] = "cited_by_count:desc"
        elif sort_by == "publication_date":
            api_params["sort"] = "publication_date:desc"

        # 年份过滤
        if year_from:
            api_params["filter"] = f"from_publication_date:{year_from}-01-01"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=api_params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            return ToolResult(status=ToolResultStatus.ERROR, error="请求超时，请稍后重试")
        except httpx.HTTPStatusError as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"API 请求失败: {e.response.status_code}")
        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"请求异常: {e}")

        results = data.get("results", [])
        total_count = data.get("meta", {}).get("count", 0)

        # 格式化输出
        output_lines = [f"📚 搜索 '{query}' 找到 {total_count} 篇论文\n"]
        papers = []

        for i, paper in enumerate(results, 1):
            title = paper.get("title", "无标题")
            year = paper.get("publication_year", "未知")
            cited = paper.get("cited_by_count", 0)
            
            # 提取作者（最多3个）
            authorships = paper.get("authorships", [])
            authors = ", ".join([
                a.get("author", {}).get("display_name", "")
                for a in authorships[:3]
            ])
            if len(authorships) > 3:
                authors += " 等"
            
            doi = paper.get("doi", "")
            paper_id = paper.get("id", "").replace("https://openalex.org/", "")
            
            # 开放获取状态
            oa_info = paper.get("open_access", {})
            is_oa = oa_info.get("is_oa", False)
            oa_badge = "🔓" if is_oa else "🔒"

            output_lines.append(f"{i}. **{title}** ({year}) {oa_badge}")
            output_lines.append(f"   作者: {authors or '未知'}")
            output_lines.append(f"   引用: {cited} | ID: {paper_id}")
            if doi:
                output_lines.append(f"   DOI: {doi}")
            output_lines.append("")

            papers.append({
                "id": paper_id,
                "title": title,
                "year": year,
                "cited_by_count": cited,
                "authors": authors,
                "doi": doi,
                "is_open_access": is_oa,
            })

        logger.info("文献搜索: '%s' → %d 结果 (共 %d)", query, len(papers), total_count)
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(output_lines),
            data={"papers": papers, "total_count": total_count},
        )

    # ------------------------------------------------------------------
    # get_paper_details - 获取论文详情
    # ------------------------------------------------------------------

    async def _get_paper_details(self, params: dict[str, Any]) -> ToolResult:
        paper_id = params.get("paper_id", "").strip()
        if not paper_id:
            return ToolResult(status=ToolResultStatus.ERROR, error="论文ID不能为空")

        url = self._build_paper_url(paper_id)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                paper = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return ToolResult(status=ToolResultStatus.ERROR, error=f"未找到论文: {paper_id}")
            return ToolResult(status=ToolResultStatus.ERROR, error=f"API 请求失败: {e.response.status_code}")
        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"请求异常: {e}")

        # 提取详细信息
        title = paper.get("title", "无标题")
        year = paper.get("publication_year", "未知")
        cited = paper.get("cited_by_count", 0)
        doi = paper.get("doi", "")
        
        # 作者
        authorships = paper.get("authorships", [])
        authors_list = []
        for a in authorships[:10]:  # 最多显示10个作者
            author_name = a.get("author", {}).get("display_name", "")
            institutions = a.get("institutions", [])
            inst_name = institutions[0].get("display_name", "") if institutions else ""
            if author_name:
                if inst_name:
                    authors_list.append(f"{author_name} ({inst_name})")
                else:
                    authors_list.append(author_name)
        
        # 摘要（从倒排索引重构）
        abstract = self._reconstruct_abstract(paper.get("abstract_inverted_index"))
        
        # 发表信息
        primary_loc = paper.get("primary_location", {}) or {}
        source = primary_loc.get("source", {}) or {}
        journal = source.get("display_name", "未知期刊")
        
        # 开放获取
        oa_info = paper.get("open_access", {})
        is_oa = oa_info.get("is_oa", False)
        oa_url = oa_info.get("oa_url", "")
        
        # 关键概念
        concepts = paper.get("concepts", [])
        top_concepts = [c.get("display_name", "") for c in concepts[:5]]
        
        # 格式化输出
        output_lines = [
            f"📄 **{title}**",
            f"",
            f"**发表年份**: {year}",
            f"**期刊/来源**: {journal}",
            f"**引用数**: {cited}",
            f"**开放获取**: {'是 🔓' if is_oa else '否 🔒'}",
        ]
        
        if doi:
            output_lines.append(f"**DOI**: {doi}")
        
        output_lines.append(f"\n**作者** ({len(authorships)} 人):")
        for author in authors_list[:5]:
            output_lines.append(f"  - {author}")
        if len(authorships) > 5:
            output_lines.append(f"  - ... 等 {len(authorships)} 位作者")
        
        if abstract and abstract != "摘要不可用":
            output_lines.append(f"\n**摘要**:\n{abstract[:800]}")
            if len(abstract) > 800:
                output_lines.append("...")
        
        if top_concepts:
            output_lines.append(f"\n**关键概念**: {', '.join(top_concepts)}")
        
        if oa_url:
            output_lines.append(f"\n**开放获取链接**: {oa_url}")

        logger.info("获取论文详情: %s", paper_id)
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(output_lines),
            data={
                "id": paper.get("id", "").replace("https://openalex.org/", ""),
                "title": title,
                "year": year,
                "cited_by_count": cited,
                "authors": authors_list,
                "abstract": abstract,
                "journal": journal,
                "doi": doi,
                "is_open_access": is_oa,
                "oa_url": oa_url,
                "concepts": top_concepts,
            },
        )

    # ------------------------------------------------------------------
    # download_pdf - 下载论文 PDF
    # ------------------------------------------------------------------

    async def _download_pdf(self, params: dict[str, Any]) -> ToolResult:
        paper_id = params.get("paper_id", "").strip()
        if not paper_id:
            return ToolResult(status=ToolResultStatus.ERROR, error="论文ID不能为空")

        save_path = params.get("save_path", "").strip()

        # 先获取论文详情以找到 PDF 链接
        url = self._build_paper_url(paper_id)
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                paper = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return ToolResult(status=ToolResultStatus.ERROR, error=f"未找到论文: {paper_id}")
            return ToolResult(status=ToolResultStatus.ERROR, error=f"API 请求失败: {e.response.status_code}")
        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"请求异常: {e}")

        # 查找 PDF URL
        pdf_url = None
        
        # 优先使用 open_access.oa_url
        oa_info = paper.get("open_access", {})
        if oa_info.get("is_oa"):
            pdf_url = oa_info.get("oa_url")
        
        # 备选: primary_location.pdf_url
        if not pdf_url:
            primary_loc = paper.get("primary_location", {}) or {}
            pdf_url = primary_loc.get("pdf_url")
        
        # 再备选: best_oa_location.pdf_url
        if not pdf_url:
            best_oa = paper.get("best_oa_location", {}) or {}
            pdf_url = best_oa.get("pdf_url") or best_oa.get("landing_page_url")

        if not pdf_url:
            title = paper.get("title", "该论文")
            doi = paper.get("doi", "")
            hint = f"\n提示: 可尝试在 Sci-Hub 或 Google Scholar 搜索 DOI: {doi}" if doi else ""
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"'{title}' 暂无开放获取的 PDF 下载链接{hint}",
            )

        # 确定保存路径
        if save_path:
            output_path = Path(save_path)
        else:
            if self.output_dir:
                output_dir = Path(self.output_dir)
            else:
                output_dir = Path("generated") / datetime.now().strftime("%Y-%m-%d")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名（从标题）
            title = paper.get("title", "paper")
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:50].strip()
            output_path = output_dir / f"{safe_title}.pdf"

        # 下载 PDF
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                resp = await client.get(pdf_url)
                
                if resp.status_code != 200:
                    return ToolResult(
                        status=ToolResultStatus.ERROR,
                        error=f"PDF 下载失败，状态码: {resp.status_code}",
                    )
                
                # 检查是否是 PDF
                content_type = resp.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not resp.content[:4] == b"%PDF":
                    return ToolResult(
                        status=ToolResultStatus.ERROR,
                        error=f"下载的内容不是 PDF 文件（类型: {content_type}）",
                    )
                
                output_path.write_bytes(resp.content)
                
        except httpx.TimeoutException:
            return ToolResult(status=ToolResultStatus.ERROR, error="PDF 下载超时")
        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"PDF 下载失败: {e}")

        file_size = output_path.stat().st_size
        size_str = f"{file_size / 1024 / 1024:.2f} MB" if file_size > 1024 * 1024 else f"{file_size / 1024:.1f} KB"
        
        logger.info("下载论文 PDF: %s → %s (%s)", paper_id, output_path, size_str)
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ PDF 已下载\n文件: {output_path}\n大小: {size_str}",
            data={
                "path": str(output_path),
                "size": file_size,
                "pdf_url": pdf_url,
            },
        )

    # ------------------------------------------------------------------
    # get_citations - 获取引用关系
    # ------------------------------------------------------------------

    async def _get_citations(self, params: dict[str, Any]) -> ToolResult:
        paper_id = params.get("paper_id", "").strip()
        if not paper_id:
            return ToolResult(status=ToolResultStatus.ERROR, error="论文ID不能为空")

        max_results = int(params.get("max_results", 10))
        max_results = max(1, min(max_results, 25))

        # 先获取原论文的 OpenAlex ID
        original_id = paper_id
        if paper_id.startswith("10."):  # DOI
            # 需要先查询获取 OpenAlex ID
            url = self._build_paper_url(paper_id)
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    paper = resp.json()
                    original_id = paper.get("id", "").replace("https://openalex.org/", "")
            except Exception as e:
                return ToolResult(status=ToolResultStatus.ERROR, error=f"获取论文信息失败: {e}")
        elif not paper_id.startswith("W"):
            original_id = f"W{paper_id}" if paper_id.isdigit() else paper_id

        # 查询引用该论文的文献
        url = f"{BASE_URL}/works"
        api_params = {
            "filter": f"cites:{original_id}",
            "per_page": max_results,
            "sort": "cited_by_count:desc",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=api_params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"请求异常: {e}")

        results = data.get("results", [])
        total_count = data.get("meta", {}).get("count", 0)

        output_lines = [f"📑 论文 {original_id} 被引用 {total_count} 次\n"]
        citations = []

        for i, paper in enumerate(results, 1):
            title = paper.get("title", "无标题")
            year = paper.get("publication_year", "未知")
            cited = paper.get("cited_by_count", 0)
            
            authorships = paper.get("authorships", [])
            first_author = authorships[0].get("author", {}).get("display_name", "未知") if authorships else "未知"
            
            cit_id = paper.get("id", "").replace("https://openalex.org/", "")
            
            output_lines.append(f"{i}. **{title}** ({year})")
            output_lines.append(f"   作者: {first_author} 等 | 引用: {cited} | ID: {cit_id}")
            output_lines.append("")

            citations.append({
                "id": cit_id,
                "title": title,
                "year": year,
                "cited_by_count": cited,
                "first_author": first_author,
            })

        logger.info("获取引用: %s → %d 条 (共 %d)", original_id, len(citations), total_count)
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(output_lines),
            data={"citations": citations, "total_count": total_count, "paper_id": original_id},
        )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _build_paper_url(self, paper_id: str) -> str:
        """根据论文 ID 构建 API URL。
        
        支持:
        - DOI (以 10. 开头)
        - OpenAlex ID (以 W 开头或纯数字)
        """
        if paper_id.startswith("10."):
            return f"{BASE_URL}/works/doi:{paper_id}"
        elif paper_id.startswith("W"):
            return f"{BASE_URL}/works/{paper_id}"
        elif paper_id.startswith("https://openalex.org/"):
            return f"{BASE_URL}/works/{paper_id.replace('https://openalex.org/', '')}"
        else:
            # 假设是 OpenAlex ID
            return f"{BASE_URL}/works/{paper_id}"

    def _reconstruct_abstract(self, inverted_index: dict | None) -> str:
        """从 OpenAlex 倒排索引重构摘要文本。
        
        OpenAlex 以倒排索引格式存储摘要，格式为:
        {"word1": [pos1, pos2], "word2": [pos3], ...}
        需要按位置重新排列以还原原文。
        """
        if not inverted_index:
            return "摘要不可用"
        
        try:
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            word_positions.sort(key=lambda x: x[0])
            return " ".join(word for _, word in word_positions)
        except Exception:
            return "摘要解析失败"
