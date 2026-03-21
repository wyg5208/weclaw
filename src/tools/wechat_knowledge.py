"""微信客服知识库模块。

提供基于 RAG 的智能问答能力：
- FAQ 匹配（常见问题自动回复）
- 向量检索增强生成
- 多轮对话上下文管理
- 知识库增删改查
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WeChatKnowledgeBase:
    """微信客服知识库
    
    功能：
    - FAQ 管理：添加、查询、删除常见问题
    - 向量检索：使用 embedding 模型进行语义搜索
    - RAG 生成：基于检索结果生成智能回复
    - 上下文管理：维护多轮对话历史
    """
    
    def __init__(
        self, 
        db_path: str | None = None,
        faq_file: str | None = None,
        embedding_model: str = "bge-small-zh",
        knowledge_dir: str | None = None
    ):
        """初始化知识库
        
        Args:
            db_path: SQLite 数据库路径
            faq_file: FAQ JSON 文件路径
            embedding_model: Embedding 模型名称
            knowledge_dir: 知识文档目录
        """
        self.db_path = Path(db_path) if db_path else Path("data/wechat_knowledge.db")
        self.faq_file = Path(faq_file) if faq_file else Path("data/wechat_faq.json")
        self.embedding_model = embedding_model
        self.knowledge_dir = Path(knowledge_dir) if knowledge_dir else Path("data/knowledge")
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        # 向量存储（懒加载）
        self._vector_store = None
        self._embedding_model = None
        
        # FAQ 缓存
        self._faq_cache: list[dict[str, Any]] = []
        
        # 对话上下文
        self._context_history: dict[str, list[dict[str, Any]]] = {}
        
        logger.info("WeChatKnowledgeBase 已初始化")
    
    async def initialize(self):
        """异步初始化（加载模型和向量存储）"""
        try:
            # 加载 FAQ
            await self._load_faq()
            
            # 初始化 embedding 模型（可选，需要安装 sentence-transformers）
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(self.embedding_model)
                logger.info("Embedding 模型已加载：%s", self.embedding_model)
            except ImportError:
                logger.warning("sentence-transformers 未安装，将使用简单关键词匹配")
            
            # 初始化向量存储
            try:
                import faiss
                self._vector_store = faiss.IndexFlatL2(768)  # bge-small-zh 维度
                logger.info("FAISS 向量存储已初始化")
            except ImportError:
                logger.warning("faiss 未安装，将使用简单匹配模式")
            
        except Exception as e:
            logger.error("初始化知识库失败：%s", e)
    
    async def _load_faq(self):
        """加载 FAQ 数据"""
        if not self.faq_file.exists():
            logger.debug("FAQ 文件不存在，创建空 FAQ")
            self._faq_cache = []
            return
        
        try:
            with open(self.faq_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._faq_cache = data.get("faqs", [])
            logger.info("已加载 %d 条 FAQ", len(self._faq_cache))
            
        except Exception as e:
            logger.error("加载 FAQ 失败：%s", e)
            self._faq_cache = []
    
    async def add_faq(
        self, 
        question: str, 
        answer: str, 
        category: str = "general",
        tags: list[str] | None = None
    ) -> bool:
        """添加 FAQ 条目
        
        Args:
            question: 问题
            answer: 答案
            category: 分类
            tags: 标签列表
        
        Returns:
            是否成功
        """
        try:
            faq_entry = {
                "id": len(self._faq_cache) + 1,
                "question": question,
                "answer": answer,
                "category": category,
                "tags": tags or [],
                "created_at": str(Path.cwd())
            }
            
            self._faq_cache.append(faq_entry)
            
            # 保存到文件
            await self._save_faq()
            
            # 添加到向量库（如果有）
            if self._embedding_model and self._vector_store:
                embedding = self._embedding_model.encode(question)
                self._vector_store.add(embedding.reshape(1, -1))
            
            logger.info("FAQ 已添加：%s", question[:50])
            return True
            
        except Exception as e:
            logger.error("添加 FAQ 失败：%s", e)
            return False
    
    async def remove_faq(self, faq_id: int) -> bool:
        """删除 FAQ 条目
        
        Args:
            faq_id: FAQ ID
        
        Returns:
            是否成功
        """
        try:
            for i, faq in enumerate(self._faq_cache):
                if faq["id"] == faq_id:
                    self._faq_cache.pop(i)
                    await self._save_faq()
                    logger.info("FAQ 已删除：%d", faq_id)
                    return True
            
            logger.warning("未找到 FAQ ID: %d", faq_id)
            return False
            
        except Exception as e:
            logger.error("删除 FAQ 失败：%s", e)
            return False
    
    async def search_similar(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """检索相似问题
        
        Args:
            query: 查询问题
            top_k: 返回数量
        
        Returns:
            相似的 FAQ 列表
        """
        try:
            results = []
            
            # 如果有向量库，使用语义搜索
            if self._embedding_model and self._vector_store and self._faq_cache:
                query_embedding = self._embedding_model.encode(query)
                
                # FAISS 搜索
                distances, indices = self._vector_store.search(
                    query_embedding.reshape(1, -1), 
                    min(top_k, len(self._faq_cache))
                )
                
                for idx, distance in zip(indices[0], distances[0]):
                    if idx < len(self._faq_cache):
                        faq = self._faq_cache[idx].copy()
                        faq["similarity"] = float(1 / (1 + distance))  # 转换为相似度
                        results.append(faq)
            
            # 否则使用关键词匹配
            else:
                results = await self._keyword_search(query, top_k)
            
            logger.debug("检索到 %d 条相似问题", len(results))
            return results
            
        except Exception as e:
            logger.error("检索失败：%s", e)
            return []
    
    async def _keyword_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """关键词搜索（备用方案）
        
        Args:
            query: 查询
            top_k: 返回数量
        
        Returns:
            匹配结果
        """
        query_lower = query.lower()
        scored_results = []
        
        for faq in self._faq_cache:
            score = 0
            
            # 问题匹配
            question = faq["question"].lower()
            if query_lower in question:
                score += 10
            
            # 标签匹配
            for tag in faq.get("tags", []):
                if query_lower in tag.lower():
                    score += 5
            
            # 分类匹配
            if query_lower in faq.get("category", "").lower():
                score += 2
            
            if score > 0:
                faq_copy = faq.copy()
                faq_copy["similarity"] = score
                scored_results.append(faq_copy)
        
        # 按分数排序
        scored_results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return scored_results[:top_k]
    
    async def generate_reply(
        self, 
        user_message: str, 
        context: list[dict] | None = None,
        confidence_threshold: float = 0.7,
        fallback_to_llm: bool = True
    ) -> dict[str, Any]:
        """基于检索结果生成回复
        
        Args:
            user_message: 用户消息
            context: 对话上下文
            confidence_threshold: 置信度阈值
            fallback_to_llm: 无匹配时是否使用 LLM
        
        Returns:
            回复结果 {reply, source, confidence}
        """
        try:
            # 1. 检索相似问题
            similar_faqs = await self.search_similar(user_message, top_k=3)
            
            if not similar_faqs:
                # 2. 无匹配，使用 LLM 生成
                if fallback_to_llm:
                    reply = await self._generate_with_llm(user_message, context)
                    return {
                        "reply": reply,
                        "source": "llm",
                        "confidence": 0.0
                    }
                else:
                    return {
                        "reply": "抱歉，我还不知道如何回答这个问题。",
                        "source": "none",
                        "confidence": 0.0
                    }
            
            # 3. 检查置信度
            best_match = similar_faqs[0]
            confidence = best_match.get("similarity", 0.0)
            
            if confidence >= confidence_threshold:
                # 4. 高置信度，直接返回 FAQ 答案
                return {
                    "reply": best_match["answer"],
                    "source": f"faq:{best_match['id']}",
                    "confidence": confidence
                }
            else:
                # 5. 低置信度，使用 LLM 参考 FAQ 生成
                if fallback_to_llm:
                    reply = await self._generate_with_llm(
                        user_message, 
                        context,
                        reference_faqs=similar_faqs
                    )
                    return {
                        "reply": reply,
                        "source": "llm_with_faq",
                        "confidence": confidence
                    }
                else:
                    return {
                        "reply": best_match["answer"],
                        "source": f"faq:{best_match['id']}",
                        "confidence": confidence
                    }
            
        except Exception as e:
            logger.error("生成回复失败：%s", e)
            return {
                "reply": "抱歉，我遇到了一些问题，请稍后再试。",
                "source": "error",
                "confidence": 0.0
            }
    
    async def _generate_with_llm(
        self,
        user_message: str,
        context: list[dict] | None,
        reference_faqs: list[dict] | None = None
    ) -> str:
        """使用 LLM 生成回复
        
        Args:
            user_message: 用户消息
            context: 上下文
            reference_faqs: 参考 FAQ
        
        Returns:
            生成的回复
        """
        try:
            # TODO: 调用 LiteLLM 生成回复
            # 这里可以集成 knowledge_rag 工具
            
            logger.debug("使用 LLM 生成回复：%s", user_message[:50])
            
            # 临时实现
            return "这是一个智能生成的回复，实际使用时会调用 LLM API。"
            
        except Exception as e:
            logger.error("LLM 生成失败：%s", e)
            return "抱歉，我暂时无法回答这个问题。"
    
    async def _save_faq(self):
        """保存 FAQ 到文件"""
        try:
            data = {"faqs": self._faq_cache}
            
            with open(self.faq_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug("FAQ 已保存到：%s", self.faq_file)
            
        except Exception as e:
            logger.error("保存 FAQ 失败：%s", e)
    
    def update_context(self, chat_id: str, message: dict[str, Any], max_length: int = 10):
        """更新对话上下文
        
        Args:
            chat_id: 聊天 ID
            message: 消息内容
            max_length: 最大上下文长度
        """
        if chat_id not in self._context_history:
            self._context_history[chat_id] = []
        
        history = self._context_history[chat_id]
        history.append(message)
        
        # 限制长度
        if len(history) > max_length:
            history.pop(0)
        
        logger.debug("上下文已更新：%s (length=%d)", chat_id, len(history))
    
    def get_context(self, chat_id: str) -> list[dict[str, Any]]:
        """获取对话上下文
        
        Args:
            chat_id: 聊天 ID
        
        Returns:
            上下文列表
        """
        return self._context_history.get(chat_id, [])
    
    def clear_context(self, chat_id: str):
        """清空对话上下文
        
        Args:
            chat_id: 聊天 ID
        """
        if chat_id in self._context_history:
            self._context_history[chat_id] = []
            logger.debug("上下文已清空：%s", chat_id)
    
    async def get_stats(self) -> dict[str, Any]:
        """获取知识库统计信息
        
        Returns:
            统计信息
        """
        return {
            "total_faqs": len(self._faq_cache),
            "categories": len(set(faq.get("category", "") for faq in self._faq_cache)),
            "db_size_mb": self.db_path.stat().st_size / 1024 / 1024 if self.db_path.exists() else 0,
            "vector_store_size": self._vector_store.ntotal if self._vector_store else 0
        }
