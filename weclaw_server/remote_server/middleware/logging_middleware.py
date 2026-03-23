"""HTTP 请求日志中间件

记录所有 HTTP 请求的详细信息，包括：
- 请求方法、路径
- 请求耗时
- 响应状态码
- 用户身份（如果已认证）
"""

import time
import logging
from fastapi import FastAPI, Request
from fastapi.responses import Response


logger = logging.getLogger(__name__)


def setup_request_logging(app: FastAPI) -> None:
    """为 FastAPI 应用添加请求日志中间件。
    
    Args:
        app: FastAPI 应用实例
    """
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        """记录每个 HTTP 请求的详细信息。"""
        start_time = time.time()
        
        # 提取请求信息
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        client_host = request.client.host if request.client else "unknown"
        
        # 构建请求日志
        log_parts = [f"{method} {path}"]
        if query_params:
            log_parts.append(f"?{query_params}")
        log_parts.append(f" - 来自 {client_host}")
        
        logger.info("".join(log_parts) + " - 开始处理")
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算耗时
            process_time = time.time() - start_time
            
            # 记录完成日志
            logger.info(
                f"{method} {path} - 完成 (状态={response.status_code}, 耗时={process_time:.3f}s)"
            )
            
            # 在响应头中添加耗时（可选）
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # 记录错误日志
            process_time = time.time() - start_time
            logger.error(
                f"{method} {path} - 异常 (耗时={process_time:.3f}s): {e}",
                exc_info=True
            )
            raise
    
    logger.debug("HTTP 请求日志中间件已注册")
