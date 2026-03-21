"""编程辅助工具 — 代码生成与分析辅助工具。

支持动作：
- generate_code_template: 生成代码模板（多语言、多类型）
- analyze_code: 代码静态分析
- generate_tests: 生成测试代码
- format_code: 格式化代码
"""

from __future__ import annotations

import ast
import logging
import os
import re
import textwrap
import tokenize
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# 条件导入 black
try:
    import black
    BLACK_AVAILABLE = True
except ImportError:
    BLACK_AVAILABLE = False


# ============== 代码模板库 ==============

PYTHON_CLASS_TEMPLATE = '''"""
{description}
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class {name}:
    """{description}
    
    Attributes:
        {attributes_doc}
    """
    
    def __init__(self{init_params}) -> None:
        """Initialize {name}.
        
        Args:
            {args_doc}
        """
        {init_body}
        logger.debug(f"{{self.__class__.__name__}} initialized")
    
    def __repr__(self) -> str:
        """Return string representation."""
        return f"{{self.__class__.__name__}}({_repr_attrs})"
    
    @property
    def info(self) -> dict[str, Any]:
        """Return instance information as dict."""
        return {{
            {info_dict}
        }}
    
    def process(self, data: Any) -> Any:
        """Process input data.
        
        Args:
            data: Input data to process.
            
        Returns:
            Processed result.
            
        Raises:
            ValueError: If data is invalid.
        """
        try:
            # TODO: Implement processing logic
            logger.info(f"Processing data: {{type(data).__name__}}")
            result = data
            return result
        except Exception as e:
            logger.error(f"Processing failed: {{e}}")
            raise ValueError(f"Processing failed: {{e}}") from e
'''

PYTHON_FUNCTION_TEMPLATE = '''"""
{description}
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def {name}({params}) -> {return_type}:
    """{description}
    
    Args:
        {args_doc}
        
    Returns:
        {return_doc}
        
    Raises:
        ValueError: If input is invalid.
        
    Example:
        >>> result = {name}({example_args})
    """
    logger.debug(f"{name} called with args")
    
    # Input validation
    {validation}
    
    try:
        # TODO: Implement function logic
        result = None
        logger.info(f"{name} completed successfully")
        return result
    except Exception as e:
        logger.error(f"{name} failed: {{e}}")
        raise
'''

PYTHON_API_TEMPLATE = '''"""
{name} API — {description}
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="{name}",
    description="{description}",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class ItemCreate(BaseModel):
    """Request model for creating an item."""
    name: str = Field(..., description="Item name")
    description: Optional[str] = Field(None, description="Item description")


class ItemResponse(BaseModel):
    """Response model for item."""
    id: int
    name: str
    description: Optional[str]
    created_at: str


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str


# ============== Routes ==============

@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {{"message": "Welcome to {name} API"}}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {{"status": "healthy"}}


@app.get("/items", response_model=list[ItemResponse])
async def list_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
) -> list[ItemResponse]:
    """List all items with pagination."""
    logger.info(f"Listing items: skip={{skip}}, limit={{limit}}")
    # TODO: Implement database query
    return []


@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(item: ItemCreate) -> ItemResponse:
    """Create a new item."""
    logger.info(f"Creating item: {{item.name}}")
    try:
        # TODO: Implement database insert
        return ItemResponse(
            id=1,
            name=item.name,
            description=item.description,
            created_at="2024-01-01T00:00:00Z",
        )
    except Exception as e:
        logger.error(f"Failed to create item: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/items/{{item_id}}", response_model=ItemResponse)
async def get_item(item_id: int) -> ItemResponse:
    """Get item by ID."""
    logger.info(f"Getting item: {{item_id}}")
    # TODO: Implement database query
    raise HTTPException(status_code=404, detail="Item not found")


@app.delete("/items/{{item_id}}", status_code=204)
async def delete_item(item_id: int) -> None:
    """Delete item by ID."""
    logger.info(f"Deleting item: {{item_id}}")
    # TODO: Implement database delete


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

PYTHON_CLI_TEMPLATE = '''"""
{name} — {description}

Usage:
    python {name}.py [options]
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_argparser() -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="{description}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --input file.txt
    %(prog)s --verbose --output result.txt
        """,
    )
    
    parser.add_argument(
        "-i", "--input",
        type=Path,
        help="Input file path",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )
    
    return parser


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point.
    
    Args:
        args: Command line arguments (uses sys.argv if None).
        
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = setup_argparser()
    parsed_args = parser.parse_args(args)
    
    if parsed_args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    try:
        logger.info("Starting {name}")
        
        # TODO: Implement main logic
        if parsed_args.input:
            logger.info(f"Processing input: {{parsed_args.input}}")
            
        if parsed_args.output:
            logger.info(f"Writing output: {{parsed_args.output}}")
        
        logger.info("{name} completed successfully")
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {{e}}")
        return 1
    except PermissionError as e:
        logger.error(f"Permission denied: {{e}}")
        return 2
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {{e}}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''

PYTHON_TEST_TEMPLATE = '''"""
Tests for {name}
"""

import pytest
from typing import Any
from unittest.mock import Mock, patch, MagicMock


# ============== Fixtures ==============

@pytest.fixture
def sample_data() -> dict[str, Any]:
    """Provide sample test data."""
    return {{
        "id": 1,
        "name": "test",
        "value": 100,
    }}


@pytest.fixture
def mock_client() -> Mock:
    """Provide mock client."""
    client = Mock()
    client.get.return_value = {{"status": "ok"}}
    return client


# ============== Test Cases ==============

class Test{name}:
    """Tests for {name}."""
    
    def test_basic_functionality(self, sample_data: dict[str, Any]) -> None:
        """Test basic functionality."""
        # Arrange
        expected = "expected_result"
        
        # Act
        # TODO: Implement test
        result = None
        
        # Assert
        assert result is not None
    
    def test_edge_case_empty_input(self) -> None:
        """Test handling of empty input."""
        # Arrange
        empty_input = {{}}
        
        # Act & Assert
        # TODO: Implement test
        pass
    
    def test_error_handling(self) -> None:
        """Test error handling."""
        # Arrange
        invalid_input = None
        
        # Act & Assert
        with pytest.raises(ValueError):
            # TODO: Call function with invalid input
            pass
    
    def test_with_mock(self, mock_client: Mock) -> None:
        """Test with mocked dependency."""
        # Arrange
        mock_client.get.return_value = {{"data": "mocked"}}
        
        # Act
        result = mock_client.get("/api/data")
        
        # Assert
        assert result == {{"data": "mocked"}}
        mock_client.get.assert_called_once_with("/api/data")


# ============== Parametrized Tests ==============

@pytest.mark.parametrize("input_val,expected", [
    (1, 1),
    (0, 0),
    (-1, 1),
])
def test_parametrized_example(input_val: int, expected: int) -> None:
    """Test with multiple input/output combinations."""
    # TODO: Implement test
    result = abs(input_val)
    assert result == expected


# ============== Async Tests ==============

@pytest.mark.asyncio
async def test_async_operation() -> None:
    """Test async operation."""
    # Arrange
    
    # Act
    # TODO: Implement async test
    
    # Assert
    pass
'''

HTML_WEB_PAGE_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --primary-color: #3498db;
            --secondary-color: #2ecc71;
            --accent-color: #e74c3c;
            --text-color: #333;
            --bg-color: #f5f5f5;
            --card-bg: #fff;
            --shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        /* Header */
        header {{
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 2rem;
            text-align: center;
            box-shadow: var(--shadow);
        }}
        
        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        header p {{
            opacity: 0.9;
        }}
        
        /* Navigation */
        nav {{
            background: var(--card-bg);
            padding: 1rem;
            box-shadow: var(--shadow);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        nav ul {{
            list-style: none;
            display: flex;
            justify-content: center;
            gap: 2rem;
        }}
        
        nav a {{
            color: var(--text-color);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s;
        }}
        
        nav a:hover {{
            color: var(--primary-color);
        }}
        
        /* Main Content */
        main {{
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }}
        
        .card {{
            background: var(--card-bg);
            border-radius: 8px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: var(--shadow);
        }}
        
        .card h2 {{
            color: var(--primary-color);
            margin-bottom: 1rem;
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 0.5rem;
        }}
        
        /* Buttons */
        .btn {{
            display: inline-block;
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
        }}
        
        .btn-primary {{
            background: var(--primary-color);
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #2980b9;
            transform: translateY(-2px);
        }}
        
        .btn-secondary {{
            background: var(--secondary-color);
            color: white;
        }}
        
        /* Forms */
        .form-group {{
            margin-bottom: 1rem;
        }}
        
        .form-group label {{
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }}
        
        .form-group input,
        .form-group textarea {{
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1rem;
        }}
        
        .form-group input:focus,
        .form-group textarea:focus {{
            outline: none;
            border-color: var(--primary-color);
        }}
        
        /* Grid Layout */
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }}
        
        /* Footer */
        footer {{
            background: var(--text-color);
            color: white;
            text-align: center;
            padding: 2rem;
            margin-top: 4rem;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            header h1 {{
                font-size: 1.8rem;
            }}
            
            nav ul {{
                flex-direction: column;
                align-items: center;
                gap: 1rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>{name}</h1>
        <p>{description}</p>
    </header>
    
    <nav>
        <ul>
            <li><a href="#home">首页</a></li>
            <li><a href="#features">功能</a></li>
            <li><a href="#about">关于</a></li>
            <li><a href="#contact">联系</a></li>
        </ul>
    </nav>
    
    <main>
        <section id="home" class="card">
            <h2>欢迎</h2>
            <p>这是 {name} 的主页面。{description}</p>
            <br>
            <button class="btn btn-primary" onclick="showMessage()">点击体验</button>
        </section>
        
        <section id="features" class="card">
            <h2>功能特点</h2>
            <div class="grid">
                <div>
                    <h3>🚀 快速</h3>
                    <p>高性能设计，快速响应</p>
                </div>
                <div>
                    <h3>🛡️ 安全</h3>
                    <p>多重安全保护机制</p>
                </div>
                <div>
                    <h3>📱 响应式</h3>
                    <p>适配各种设备屏幕</p>
                </div>
            </div>
        </section>
        
        <section id="contact" class="card">
            <h2>联系我们</h2>
            <form id="contactForm">
                <div class="form-group">
                    <label for="name">姓名</label>
                    <input type="text" id="name" name="name" required>
                </div>
                <div class="form-group">
                    <label for="email">邮箱</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div class="form-group">
                    <label for="message">留言</label>
                    <textarea id="message" name="message" rows="4" required></textarea>
                </div>
                <button type="submit" class="btn btn-primary">发送</button>
            </form>
        </section>
    </main>
    
    <footer>
        <p>&copy; 2024 {name}. All rights reserved.</p>
    </footer>
    
    <script>
        // Utility functions
        function showMessage() {{
            alert('欢迎使用 {name}!');
        }}
        
        // Form handling
        document.getElementById('contactForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            console.log('Form submitted:', data);
            alert('感谢您的留言！');
            this.reset();
        }});
        
        // Smooth scroll
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function(e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth' }});
                }}
            }});
        }});
        
        // Console welcome
        console.log('%c{name}', 'font-size: 24px; color: #3498db; font-weight: bold;');
        console.log('Page loaded successfully');
    </script>
</body>
</html>
'''

# 其他语言的简化模板
JS_FUNCTION_TEMPLATE = '''/**
 * {description}
 * @param {{*}} data - Input data
 * @returns {{*}} Processed result
 */
function {name}(data) {{
    console.log(`{name} called with:`, data);
    
    // Input validation
    if (!data) {{
        throw new Error('Invalid input: data is required');
    }}
    
    try {{
        // TODO: Implement function logic
        const result = data;
        console.log(`{name} completed`);
        return result;
    }} catch (error) {{
        console.error(`{name} failed:`, error);
        throw error;
    }}
}}

module.exports = {{ {name} }};
'''

JS_CLASS_TEMPLATE = '''/**
 * {name} - {description}
 */
class {name} {{
    /**
     * Create a {name} instance.
     * @param {{Object}} options - Configuration options
     */
    constructor(options = {{}}) {{
        this.options = options;
        console.log(`{name} initialized`);
    }}
    
    /**
     * Get instance info.
     * @returns {{Object}} Instance information
     */
    get info() {{
        return {{
            name: '{name}',
            options: this.options,
        }};
    }}
    
    /**
     * Process data.
     * @param {{*}} data - Input data
     * @returns {{*}} Processed result
     */
    process(data) {{
        console.log(`Processing:`, data);
        // TODO: Implement processing logic
        return data;
    }}
}}

module.exports = {{ {name} }};
'''

TS_CLASS_TEMPLATE = '''/**
 * {name} - {description}
 */

interface {name}Options {{
    debug?: boolean;
    timeout?: number;
}}

interface ProcessResult {{
    success: boolean;
    data: unknown;
}}

export class {name} {{
    private options: {name}Options;
    
    /**
     * Create a {name} instance.
     */
    constructor(options: {name}Options = {{}}) {{
        this.options = options;
        console.log(`{name} initialized`);
    }}
    
    /**
     * Get instance info.
     */
    get info(): Record<string, unknown> {{
        return {{
            name: '{name}',
            options: this.options,
        }};
    }}
    
    /**
     * Process data.
     */
    public process(data: unknown): ProcessResult {{
        console.log(`Processing:`, data);
        // TODO: Implement processing logic
        return {{
            success: true,
            data,
        }};
    }}
}}
'''

JAVA_CLASS_TEMPLATE = '''package com.example;

import java.util.logging.Logger;
import java.util.Objects;

/**
 * {name} - {description}
 */
public class {name} {{
    
    private static final Logger logger = Logger.getLogger({name}.class.getName());
    
    private String id;
    private String name;
    
    /**
     * Default constructor.
     */
    public {name}() {{
        logger.info("{name} initialized");
    }}
    
    /**
     * Constructor with parameters.
     * @param id The ID
     * @param name The name
     */
    public {name}(String id, String name) {{
        this.id = id;
        this.name = name;
        logger.info("{name} initialized with id=" + id);
    }}
    
    // Getters and Setters
    
    public String getId() {{
        return id;
    }}
    
    public void setId(String id) {{
        this.id = id;
    }}
    
    public String getName() {{
        return name;
    }}
    
    public void setName(String name) {{
        this.name = name;
    }}
    
    /**
     * Process data.
     * @param data Input data
     * @return Processed result
     * @throws IllegalArgumentException if data is null
     */
    public Object process(Object data) {{
        Objects.requireNonNull(data, "data cannot be null");
        logger.info("Processing data");
        // TODO: Implement processing logic
        return data;
    }}
    
    @Override
    public String toString() {{
        return "{name}{{" +
                "id='" + id + '\\'' +
                ", name='" + name + '\\'' +
                '}}';
    }}
    
    @Override
    public boolean equals(Object o) {{
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        {name} that = ({name}) o;
        return Objects.equals(id, that.id) && Objects.equals(name, that.name);
    }}
    
    @Override
    public int hashCode() {{
        return Objects.hash(id, name);
    }}
}}
'''

GO_FUNCTION_TEMPLATE = '''package main

import (
	"fmt"
	"log"
)

// {name} - {description}
func {name}(data interface{{}}) (interface{{}}, error) {{
	log.Printf("{name} called with: %v", data)
	
	// Input validation
	if data == nil {{
		return nil, fmt.Errorf("invalid input: data is required")
	}}
	
	// TODO: Implement function logic
	result := data
	
	log.Printf("{name} completed")
	return result, nil
}}

func main() {{
	result, err := {name}("test")
	if err != nil {{
		log.Fatalf("Error: %v", err)
	}}
	fmt.Printf("Result: %v\\n", result)
}}
'''

RUST_FUNCTION_TEMPLATE = '''//! {name} - {description}

use std::error::Error;

/// {description}
/// 
/// # Arguments
/// * `data` - Input data to process
/// 
/// # Returns
/// * `Result<T, Box<dyn Error>>` - Processed result or error
/// 
/// # Examples
/// ```
/// let result = {name}("test")?;
/// ```
fn {name}<T>(data: T) -> Result<T, Box<dyn Error>>
where
    T: std::fmt::Debug,
{{
    println!("{name} called with: {{:?}}", data);
    
    // TODO: Implement function logic
    let result = data;
    
    println!("{name} completed");
    Ok(result)
}}

fn main() {{
    match {name}("test") {{
        Ok(result) => println!("Result: {{:?}}", result),
        Err(e) => eprintln!("Error: {{}}", e),
    }}
}}
'''

CPP_CLASS_TEMPLATE = '''#ifndef {name_upper}_H
#define {name_upper}_H

#include <iostream>
#include <string>
#include <memory>

/**
 * @brief {name} - {description}
 */
class {name} {{
public:
    /**
     * @brief Default constructor
     */
    {name}() {{
        std::cout << "{name} initialized" << std::endl;
    }}
    
    /**
     * @brief Constructor with name
     * @param name Instance name
     */
    explicit {name}(const std::string& name) : m_name(name) {{
        std::cout << "{name} initialized with name=" << name << std::endl;
    }}
    
    /**
     * @brief Destructor
     */
    virtual ~{name}() = default;
    
    // Getters and Setters
    
    const std::string& getName() const {{ return m_name; }}
    void setName(const std::string& name) {{ m_name = name; }}
    
    /**
     * @brief Process data
     * @param data Input data
     * @return Processed result
     */
    virtual std::string process(const std::string& data) {{
        std::cout << "Processing: " << data << std::endl;
        // TODO: Implement processing logic
        return data;
    }}
    
    /**
     * @brief Get string representation
     */
    friend std::ostream& operator<<(std::ostream& os, const {name}& obj) {{
        os << "{name}{{name='" << obj.m_name << "'}}";
        return os;
    }}

private:
    std::string m_name;
}};

#endif // {name_upper}_H
'''


class CodingAssistantTool(BaseTool):
    """编程辅助工具 — 代码生成与分析。
    
    提供代码模板生成、静态分析、测试生成和代码格式化功能。
    支持多种编程语言：Python, JavaScript, TypeScript, Java, C++, Go, Rust, HTML
    """
    
    name = "coding_assistant"
    emoji = "💻"
    title = "编程辅助"
    description = "代码生成与分析辅助工具"
    timeout = 120
    
    # 语言文件扩展名映射
    LANGUAGE_EXTENSIONS = {
        "python": ".py",
        "javascript": ".js",
        "typescript": ".ts",
        "java": ".java",
        "cpp": ".cpp",
        "go": ".go",
        "rust": ".rs",
        "html": ".html",
    }
    
    # 测试框架默认值
    DEFAULT_TEST_FRAMEWORKS = {
        "python": "pytest",
        "javascript": "jest",
        "typescript": "jest",
    }
    
    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize CodingAssistantTool.
        
        Args:
            output_dir: Output directory for generated files.
                       Defaults to generated/YYYY-MM-DD/
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            self.output_dir = Path("generated") / today
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"CodingAssistantTool initialized, output_dir={self.output_dir}")
    
    def get_actions(self) -> list[ActionDef]:
        """返回支持的动作列表。"""
        return [
            ActionDef(
                name="generate_code_template",
                description="生成代码模板。支持多种语言和模板类型，生成完整的代码骨架文件。",
                parameters={
                    "language": {
                        "type": "string",
                        "description": "编程语言",
                        "enum": ["python", "javascript", "typescript", "java", "cpp", "go", "rust", "html"],
                    },
                    "template_type": {
                        "type": "string",
                        "description": "模板类型",
                        "enum": ["class", "function", "api", "cli", "test", "web_page"],
                    },
                    "name": {
                        "type": "string",
                        "description": "项目/类/函数名称",
                    },
                    "description": {
                        "type": "string",
                        "description": "功能描述（可选）",
                    },
                    "features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "需要的功能特性列表（可选）",
                    },
                },
                required_params=["language", "template_type", "name"],
            ),
            ActionDef(
                name="analyze_code",
                description="代码静态分析。分析代码结构、复杂度、潜在问题。Python使用AST深度分析。",
                parameters={
                    "code": {
                        "type": "string",
                        "description": "代码内容（与file_path二选一）",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "代码文件路径（与code二选一）",
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言（可选，自动检测）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="generate_tests",
                description="生成测试代码。分析源代码中的函数/类，生成对应的测试骨架。",
                parameters={
                    "code": {
                        "type": "string",
                        "description": "源代码内容（与file_path二选一）",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "源代码文件路径（与code二选一）",
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言（可选，自动检测）",
                    },
                    "test_framework": {
                        "type": "string",
                        "description": "测试框架",
                        "enum": ["pytest", "unittest", "jest", "mocha"],
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="format_code",
                description="格式化代码。Python使用black，其他语言使用基本格式化。",
                parameters={
                    "code": {
                        "type": "string",
                        "description": "代码内容（与file_path二选一）",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "代码文件路径（与code二选一）",
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言（可选，自动检测）",
                    },
                    "style": {
                        "type": "string",
                        "description": "代码风格（可选）",
                    },
                },
                required_params=[],
            ),
        ]
    
    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定动作。"""
        handlers = {
            "generate_code_template": self._generate_code_template,
            "analyze_code": self._analyze_code,
            "generate_tests": self._generate_tests,
            "format_code": self._format_code,
        }
        
        handler = handlers.get(action)
        if not handler:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}",
            )
        
        return await handler(params)
    
    # ============== Action: generate_code_template ==============
    
    async def _generate_code_template(self, params: dict[str, Any]) -> ToolResult:
        """生成代码模板。"""
        language = params.get("language", "").lower()
        template_type = params.get("template_type", "").lower()
        name = params.get("name", "").strip()
        description = params.get("description", "").strip() or f"{name} implementation"
        features = params.get("features", [])
        
        if not language:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少参数: language")
        if not template_type:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少参数: template_type")
        if not name:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少参数: name")
        
        # 选择模板
        template = self._get_template(language, template_type)
        if not template:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的模板组合: {language}/{template_type}",
            )
        
        # 渲染模板
        try:
            code = self._render_template(template, name, description, features, language)
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"模板渲染失败: {e}",
            )
        
        # 生成文件名
        ext = self.LANGUAGE_EXTENSIONS.get(language, ".txt")
        if template_type == "web_page":
            ext = ".html"
        elif template_type == "test":
            filename = f"test_{name.lower()}{ext}"
        else:
            filename = f"{name.lower()}{ext}"
        
        if template_type != "test":
            filename = f"{name.lower()}{ext}"
        
        # 保存文件
        file_path = self.output_dir / filename
        file_path.write_text(code, encoding="utf-8")
        
        logger.info(f"Generated {language} {template_type} template: {file_path}")
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已生成 {language} {template_type} 模板\n📁 文件: {file_path}\n📝 代码行数: {len(code.splitlines())}",
            data={
                "file_path": str(file_path),
                "language": language,
                "template_type": template_type,
                "name": name,
                "lines": len(code.splitlines()),
            },
        )
    
    def _get_template(self, language: str, template_type: str) -> str | None:
        """获取对应的模板。"""
        templates = {
            ("python", "class"): PYTHON_CLASS_TEMPLATE,
            ("python", "function"): PYTHON_FUNCTION_TEMPLATE,
            ("python", "api"): PYTHON_API_TEMPLATE,
            ("python", "cli"): PYTHON_CLI_TEMPLATE,
            ("python", "test"): PYTHON_TEST_TEMPLATE,
            ("javascript", "function"): JS_FUNCTION_TEMPLATE,
            ("javascript", "class"): JS_CLASS_TEMPLATE,
            ("typescript", "class"): TS_CLASS_TEMPLATE,
            ("typescript", "function"): TS_CLASS_TEMPLATE,  # 复用
            ("java", "class"): JAVA_CLASS_TEMPLATE,
            ("java", "function"): JAVA_CLASS_TEMPLATE,  # Java 主要用类
            ("go", "function"): GO_FUNCTION_TEMPLATE,
            ("go", "class"): GO_FUNCTION_TEMPLATE,  # Go 用 struct
            ("rust", "function"): RUST_FUNCTION_TEMPLATE,
            ("rust", "class"): RUST_FUNCTION_TEMPLATE,  # Rust 用 struct
            ("cpp", "class"): CPP_CLASS_TEMPLATE,
            ("cpp", "function"): CPP_CLASS_TEMPLATE,
            ("html", "web_page"): HTML_WEB_PAGE_TEMPLATE,
        }
        return templates.get((language, template_type))
    
    def _render_template(
        self,
        template: str,
        name: str,
        description: str,
        features: list[str],
        language: str,
    ) -> str:
        """渲染模板。"""
        # 基本替换
        result = template.format(
            name=name,
            name_upper=name.upper(),
            description=description,
            # Python class 特定占位符
            attributes_doc="data: Internal data storage",
            init_params=", data: Any = None",
            args_doc="data: Initial data value.",
            init_body="self.data = data",
            _repr_attrs="data={self.data!r}",
            info_dict='"data": self.data,',
            # Python function 特定占位符
            params="data: Any",
            return_type="Any",
            return_doc="Processed result.",
            example_args='"example"',
            validation="if data is None:\n        raise ValueError('data cannot be None')",
        )
        return result
    
    # ============== Action: analyze_code ==============
    
    async def _analyze_code(self, params: dict[str, Any]) -> ToolResult:
        """代码静态分析。"""
        code = params.get("code", "")
        file_path = params.get("file_path", "")
        language = params.get("language", "")
        
        # 获取代码内容
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")
            code = path.read_text(encoding="utf-8")
            if not language:
                language = self._detect_language(path.suffix)
        
        if not code:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供代码内容或文件路径")
        
        if not language:
            language = self._guess_language(code)
        
        # 分析代码
        if language == "python":
            analysis = self._analyze_python_code(code)
        else:
            analysis = self._analyze_generic_code(code, language)
        
        # 生成报告
        report = self._format_analysis_report(analysis, language)
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=report,
            data=analysis,
        )
    
    def _analyze_python_code(self, code: str) -> dict[str, Any]:
        """使用 AST 分析 Python 代码。"""
        analysis: dict[str, Any] = {
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "functions": [],
            "classes": [],
            "imports": [],
            "complexity": {},
            "issues": [],
        }
        
        lines = code.splitlines()
        analysis["total_lines"] = len(lines)
        
        # 统计行类型
        for line in lines:
            stripped = line.strip()
            if not stripped:
                analysis["blank_lines"] += 1
            elif stripped.startswith("#"):
                analysis["comment_lines"] += 1
            else:
                analysis["code_lines"] += 1
        
        # AST 分析
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            analysis["issues"].append(f"语法错误: {e}")
            return analysis
        
        imports = []
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            # 收集导入
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
            
            # 收集函数
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                func_info = {
                    "name": node.name,
                    "args": len(node.args.args),
                    "line": node.lineno,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "has_docstring": (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    ),
                }
                functions.append(func_info)
            
            # 收集类
            elif isinstance(node, ast.ClassDef):
                methods = [
                    n.name
                    for n in node.body
                    if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
                ]
                classes.append({
                    "name": node.name,
                    "methods": methods,
                    "method_count": len(methods),
                    "line": node.lineno,
                })
        
        analysis["imports"] = imports
        analysis["functions"] = functions
        analysis["classes"] = classes
        
        # 计算复杂度指标
        analysis["complexity"] = {
            "function_count": len(functions),
            "class_count": len(classes),
            "import_count": len(imports),
            "avg_function_args": (
                sum(f["args"] for f in functions) / len(functions) if functions else 0
            ),
            "max_function_args": max((f["args"] for f in functions), default=0),
        }
        
        # 检测问题
        # 1. 函数参数过多
        for f in functions:
            if f["args"] > 5:
                analysis["issues"].append(f"函数 {f['name']} 参数过多 ({f['args']}个)")
            if not f["has_docstring"] and not f["name"].startswith("_"):
                analysis["issues"].append(f"函数 {f['name']} 缺少文档字符串")
        
        # 2. 检测未使用的导入（简单版）
        code_without_imports = "\n".join(
            line for line in lines
            if not line.strip().startswith(("import ", "from "))
        )
        for imp in imports:
            # 取导入的最后一部分
            name = imp.split(".")[-1]
            if name not in code_without_imports:
                analysis["issues"].append(f"可能未使用的导入: {imp}")
        
        return analysis
    
    def _analyze_generic_code(self, code: str, language: str) -> dict[str, Any]:
        """通用代码分析（非 Python）。"""
        lines = code.splitlines()
        
        analysis: dict[str, Any] = {
            "total_lines": len(lines),
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "functions": [],
            "classes": [],
            "complexity": {},
            "issues": [],
        }
        
        # 注释模式
        comment_patterns = {
            "javascript": (r"//.*$", r"/\*.*?\*/"),
            "typescript": (r"//.*$", r"/\*.*?\*/"),
            "java": (r"//.*$", r"/\*.*?\*/"),
            "cpp": (r"//.*$", r"/\*.*?\*/"),
            "go": (r"//.*$", r"/\*.*?\*/"),
            "rust": (r"//.*$", r"/\*.*?\*/"),
            "html": (r"<!--.*?-->",),
        }
        
        # 函数匹配模式
        function_patterns = {
            "javascript": r"\bfunction\s+(\w+)|(\w+)\s*[=:]\s*(?:async\s*)?\([^)]*\)\s*=>|(\w+)\s*\([^)]*\)\s*\{",
            "typescript": r"\bfunction\s+(\w+)|(\w+)\s*[=:]\s*(?:async\s*)?\([^)]*\)\s*=>|(\w+)\s*\([^)]*\)\s*:",
            "java": r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{",
            "cpp": r"\w+\s+(\w+)\s*\([^)]*\)\s*\{",
            "go": r"func\s+(?:\([^)]*\)\s*)?(\w+)",
            "rust": r"fn\s+(\w+)",
        }
        
        # 统计行
        in_multiline_comment = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                analysis["blank_lines"] += 1
            elif stripped.startswith(("//", "#", "<!--")):
                analysis["comment_lines"] += 1
            elif "/*" in stripped and "*/" not in stripped:
                in_multiline_comment = True
                analysis["comment_lines"] += 1
            elif "*/" in stripped:
                in_multiline_comment = False
                analysis["comment_lines"] += 1
            elif in_multiline_comment:
                analysis["comment_lines"] += 1
            else:
                analysis["code_lines"] += 1
        
        # 提取函数名
        pattern = function_patterns.get(language)
        if pattern:
            matches = re.findall(pattern, code)
            for match in matches:
                if isinstance(match, tuple):
                    name = next((m for m in match if m), None)
                else:
                    name = match
                if name:
                    analysis["functions"].append({"name": name})
        
        # 提取类名
        class_pattern = r"\bclass\s+(\w+)"
        for match in re.findall(class_pattern, code):
            analysis["classes"].append({"name": match})
        
        analysis["complexity"] = {
            "function_count": len(analysis["functions"]),
            "class_count": len(analysis["classes"]),
            "lines_per_function": (
                analysis["code_lines"] / len(analysis["functions"])
                if analysis["functions"] else 0
            ),
        }
        
        return analysis
    
    def _format_analysis_report(self, analysis: dict[str, Any], language: str) -> str:
        """格式化分析报告。"""
        lines = [
            f"📊 代码分析报告 ({language})",
            "=" * 40,
            "",
            "📝 代码统计:",
            f"  • 总行数: {analysis['total_lines']}",
            f"  • 代码行数: {analysis['code_lines']}",
            f"  • 注释行数: {analysis['comment_lines']}",
            f"  • 空行数: {analysis['blank_lines']}",
            "",
        ]
        
        if analysis.get("functions"):
            lines.append(f"📦 函数数量: {len(analysis['functions'])}")
            for f in analysis["functions"][:10]:  # 最多显示10个
                name = f.get("name", "unknown")
                args = f.get("args", "?")
                lines.append(f"  • {name} ({args} 参数)" if isinstance(args, int) else f"  • {name}")
            if len(analysis["functions"]) > 10:
                lines.append(f"  ... 还有 {len(analysis['functions']) - 10} 个函数")
            lines.append("")
        
        if analysis.get("classes"):
            lines.append(f"🏛️ 类数量: {len(analysis['classes'])}")
            for c in analysis["classes"][:10]:
                name = c.get("name", "unknown")
                methods = c.get("method_count", "?")
                lines.append(f"  • {name} ({methods} 方法)" if isinstance(methods, int) else f"  • {name}")
            lines.append("")
        
        if analysis.get("complexity"):
            lines.append("📈 复杂度指标:")
            for key, value in analysis["complexity"].items():
                if isinstance(value, float):
                    lines.append(f"  • {key}: {value:.2f}")
                else:
                    lines.append(f"  • {key}: {value}")
            lines.append("")
        
        if analysis.get("issues"):
            lines.append(f"⚠️ 潜在问题 ({len(analysis['issues'])}):")
            for issue in analysis["issues"][:10]:
                lines.append(f"  • {issue}")
            if len(analysis["issues"]) > 10:
                lines.append(f"  ... 还有 {len(analysis['issues']) - 10} 个问题")
        else:
            lines.append("✅ 未发现明显问题")
        
        return "\n".join(lines)
    
    # ============== Action: generate_tests ==============
    
    async def _generate_tests(self, params: dict[str, Any]) -> ToolResult:
        """生成测试代码。"""
        code = params.get("code", "")
        file_path = params.get("file_path", "")
        language = params.get("language", "")
        test_framework = params.get("test_framework", "")
        
        # 获取代码
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")
            code = path.read_text(encoding="utf-8")
            if not language:
                language = self._detect_language(path.suffix)
        
        if not code:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供代码内容或文件路径")
        
        if not language:
            language = self._guess_language(code)
        
        # 设置默认测试框架
        if not test_framework:
            test_framework = self.DEFAULT_TEST_FRAMEWORKS.get(language, "pytest")
        
        # 生成测试
        if language == "python":
            test_code = self._generate_python_tests(code, test_framework)
        else:
            test_code = self._generate_generic_tests(code, language, test_framework)
        
        # 保存文件
        ext = self.LANGUAGE_EXTENSIONS.get(language, ".txt")
        base_name = Path(file_path).stem if file_path else "module"
        test_filename = f"test_{base_name}{ext}"
        test_path = self.output_dir / test_filename
        test_path.write_text(test_code, encoding="utf-8")
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已生成测试代码\n📁 文件: {test_path}\n🧪 框架: {test_framework}\n📝 行数: {len(test_code.splitlines())}",
            data={
                "file_path": str(test_path),
                "test_framework": test_framework,
                "lines": len(test_code.splitlines()),
            },
        )
    
    def _generate_python_tests(self, code: str, framework: str) -> str:
        """为 Python 代码生成测试。"""
        # 解析 AST
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return "# 无法解析源代码，请检查语法\n"
        
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # 跳过私有函数
                if not node.name.startswith("_") or node.name.startswith("__"):
                    functions.append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args if arg.arg != "self"],
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    })
            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                        if not item.name.startswith("_") or item.name == "__init__":
                            methods.append({
                                "name": item.name,
                                "args": [a.arg for a in item.args.args if a.arg != "self"],
                            })
                classes.append({"name": node.name, "methods": methods})
        
        # 生成测试代码
        lines = [
            '"""',
            "Auto-generated test file",
            '"""',
            "",
            "import pytest",
            "from unittest.mock import Mock, patch",
            "",
            "# TODO: Import the module under test",
            "# from module import function_name",
            "",
            "",
        ]
        
        # 为每个函数生成测试
        for func in functions:
            if func["name"].startswith("__"):
                continue
            
            test_name = f"test_{func['name']}"
            args_str = ", ".join(func["args"]) if func["args"] else ""
            
            if func["is_async"]:
                lines.extend([
                    "@pytest.mark.asyncio",
                    f"async def {test_name}():",
                ])
            else:
                lines.append(f"def {test_name}():")
            
            lines.extend([
                f'    """Test {func["name"]} function."""',
                "    # Arrange",
                f"    # args: {args_str}" if args_str else "    # no args",
                "    ",
                "    # Act",
                f"    # result = {'await ' if func['is_async'] else ''}{func['name']}({args_str})",
                "    ",
                "    # Assert",
                "    # assert result == expected",
                "    pass  # TODO: Implement test",
                "",
                "",
            ])
        
        # 为每个类生成测试类
        for cls in classes:
            lines.extend([
                f"class Test{cls['name']}:",
                f'    """Tests for {cls["name"]} class."""',
                "",
                "    @pytest.fixture",
                "    def instance(self):",
                '        """Create test instance."""',
                f"        # return {cls['name']}()",
                "        pass",
                "",
            ])
            
            for method in cls["methods"]:
                if method["name"] == "__init__":
                    lines.extend([
                        "    def test_initialization(self):",
                        '        """Test instance creation."""',
                        "        # instance = " + cls["name"] + "()",
                        "        # assert instance is not None",
                        "        pass",
                        "",
                    ])
                else:
                    lines.extend([
                        f"    def test_{method['name']}(self, instance):",
                        f'        """Test {method["name"]} method."""',
                        "        # result = instance." + method["name"] + "()",
                        "        # assert result == expected",
                        "        pass",
                        "",
                    ])
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_generic_tests(self, code: str, language: str, framework: str) -> str:
        """为其他语言生成测试（基础版）。"""
        # 提取函数名
        function_pattern = r"function\s+(\w+)|(\w+)\s*\([^)]*\)\s*\{"
        matches = re.findall(function_pattern, code)
        function_names = [m[0] or m[1] for m in matches if m[0] or m[1]]
        
        if framework in ("jest", "mocha"):
            lines = [
                "// Auto-generated test file",
                "",
                f"describe('Module Tests', () => {{",
            ]
            
            for name in function_names[:10]:
                lines.extend([
                    f"  describe('{name}', () => {{",
                    f"    it('should work correctly', () => {{",
                    f"      // TODO: Implement test for {name}",
                    f"      expect(true).toBe(true);",
                    f"    }});",
                    f"  }});",
                    "",
                ])
            
            lines.append("});")
            return "\n".join(lines)
        
        return f"// TODO: Generate tests for {language} with {framework}\n"
    
    # ============== Action: format_code ==============
    
    async def _format_code(self, params: dict[str, Any]) -> ToolResult:
        """格式化代码。"""
        code = params.get("code", "")
        file_path = params.get("file_path", "")
        language = params.get("language", "")
        style = params.get("style", "")
        
        # 获取代码
        source_file = None
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")
            code = path.read_text(encoding="utf-8")
            source_file = path
            if not language:
                language = self._detect_language(path.suffix)
        
        if not code:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供代码内容或文件路径")
        
        if not language:
            language = self._guess_language(code)
        
        # 格式化
        original_lines = len(code.splitlines())
        
        if language == "python":
            formatted, message = self._format_python(code)
        else:
            formatted, message = self._format_generic(code, language)
        
        formatted_lines = len(formatted.splitlines())
        
        # 如果提供了文件路径，写回文件
        output_path = None
        if source_file:
            source_file.write_text(formatted, encoding="utf-8")
            output_path = str(source_file)
        else:
            # 保存到生成目录
            ext = self.LANGUAGE_EXTENSIONS.get(language, ".txt")
            output_file = self.output_dir / f"formatted_code{ext}"
            output_file.write_text(formatted, encoding="utf-8")
            output_path = str(output_file)
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ {message}\n📁 文件: {output_path}\n📝 {original_lines} 行 → {formatted_lines} 行",
            data={
                "file_path": output_path,
                "original_lines": original_lines,
                "formatted_lines": formatted_lines,
                "formatted_code": formatted,
            },
        )
    
    def _format_python(self, code: str) -> tuple[str, str]:
        """使用 black 格式化 Python 代码。"""
        if BLACK_AVAILABLE:
            try:
                formatted = black.format_str(code, mode=black.Mode())
                return formatted, "使用 black 格式化完成"
            except Exception as e:
                logger.warning(f"black 格式化失败: {e}")
                return code, f"black 格式化失败: {e}"
        else:
            # 基本格式化：规范化缩进
            lines = code.splitlines()
            formatted_lines = []
            for line in lines:
                # 将制表符转换为4空格
                formatted_lines.append(line.replace("\t", "    "))
            return "\n".join(formatted_lines), "基本格式化完成（black 未安装）"
    
    def _format_generic(self, code: str, language: str) -> tuple[str, str]:
        """通用代码格式化。"""
        lines = code.splitlines()
        formatted_lines = []
        
        for line in lines:
            # 统一缩进为空格
            formatted = line.replace("\t", "    ")
            # 移除行尾空白
            formatted = formatted.rstrip()
            formatted_lines.append(formatted)
        
        # 移除文件末尾多余空行
        while formatted_lines and not formatted_lines[-1]:
            formatted_lines.pop()
        
        # 确保文件以换行结尾
        result = "\n".join(formatted_lines)
        if result and not result.endswith("\n"):
            result += "\n"
        
        return result, "基本格式化完成"
    
    # ============== Helper Methods ==============
    
    def _detect_language(self, suffix: str) -> str:
        """根据文件后缀检测语言。"""
        suffix_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".java": "java",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".c": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
            ".go": "go",
            ".rs": "rust",
            ".html": "html",
            ".htm": "html",
        }
        return suffix_map.get(suffix.lower(), "unknown")
    
    def _guess_language(self, code: str) -> str:
        """根据代码内容猜测语言。"""
        # 简单的启发式检测
        if "def " in code and "import " in code:
            return "python"
        if "function " in code or "const " in code or "let " in code:
            if ": " in code and "interface " in code:
                return "typescript"
            return "javascript"
        if "public class " in code or "private " in code:
            return "java"
        if "package main" in code or "func " in code:
            return "go"
        if "fn " in code and "let mut" in code:
            return "rust"
        if "#include" in code:
            return "cpp"
        if "<html" in code.lower() or "<!doctype" in code.lower():
            return "html"
        return "unknown"
