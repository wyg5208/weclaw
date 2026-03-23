# 📷 高拍仪文档扫描工具使用指南

## 🎯 功能概述

高拍仪文档扫描工具（DocumentScannerTool）是专门为 WeClaw 系统开发的智能文档解析工具，特别适用于处理高拍仪扫描的试卷、作业等教育文档。

### 核心特性

✅ **智能解析**
- 使用 GLM-4.6V 视觉大模型
- 支持数学、物理、化学等多学科
- 详细解答步骤 + 知识点标注
- LaTeX 公式规范输出

✅ **数据库存储**
- SQLite 持久化存储
- 完整的扫描记录管理
- 历史查询和统计

✅ **智能缓存**
- 文件指纹（SHA256）识别
- 避免重复解析
- 增量更新支持

✅ **批量处理**
- 自动扫描文件夹
- 多文件并发处理
- 缓存命中率统计

---

## 🚀 快速开始

### 1. 配置 API Key

在 `.env` 文件中添加：

```bash
GLM_API_KEY=your_api_key_here
```

获取地址：https://open.bigmodel.cn/

### 2. 基本使用

#### Python 代码调用

```python
from src.tools.document_scanner import DocumentScannerTool
import asyncio

async def use_scanner():
    scanner = DocumentScannerTool()
    
    # 扫描单个文件
    result = await scanner.execute("scan_file", {
        "file_path": "D:/scans/math_homework.jpg",
        "subject": "数学",
        "grade_level": "高中"
    })
    
    if result.is_success:
        print(f"✅ 解析完成")
        print(f"📄 MD 文件：{result.data['md_file_path']}")
        print(f"📊 题目数：{result.data['problem_count']}")

asyncio.run(use_scanner())
```

#### 批量扫描文件夹

```python
result = await scanner.execute("scan_folder", {
    "folder_path": "D:/scans/homework/",
    "subject": "数学",
    "grade_level": "高中",
    "file_pattern": "*.jpg,*.png",
    "force_reprocess": False  # 使用缓存
})

print(f"总文件数：{result.data['total_files']}")
print(f"成功：{result.data['success_count']}")
print(f"缓存命中：{result.data['cache_hit_count']}")
```

---

## 📋 可用动作

### 1. `scan_file` - 扫描单个文件

**参数：**
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file_path` | string | ✅ | - | 文件路径 |
| `subject` | string | ❌ | "数学" | 科目类型 |
| `grade_level` | string | ❌ | "高中" | 年级水平 |

**示例：**
```python
result = await scanner.execute("scan_file", {
    "file_path": "path/to/file.jpg",
    "subject": "物理",
    "grade_level": "初中"
})
```

### 2. `scan_folder` - 批量扫描文件夹

**参数：**
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `folder_path` | string | ❌ | 配置的扫描文件夹 | 文件夹路径 |
| `subject` | string | ❌ | "数学" | 科目类型 |
| `grade_level` | string | ❌ | "高中" | 年级水平 |
| `file_pattern` | string | ❌ | "*.jpg,*.png,*.bmp" | 文件匹配模式 |
| `force_reprocess` | boolean | ❌ | False | 强制重新处理 |

**示例：**
```python
result = await scanner.execute("scan_folder", {
    "folder_path": "D:/scans/math/",
    "subject": "数学",
    "file_pattern": "*.jpg",
    "force_reprocess": True
})
```

### 3. `query_history` - 查询历史记录

**参数：**
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file_hash` | string | ❌ | None | 文件哈希值 |
| `status` | string | ❌ | "all" | 状态过滤 (all/success/failed) |
| `limit` | integer | ❌ | 20 | 返回数量限制 |

**示例：**
```python
# 查询所有成功记录
result = await scanner.execute("query_history", {
    "status": "success",
    "limit": 10
})

records = result.data["records"]
```

### 4. `clear_cache` - 清除缓存

**参数：**
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `older_than_days` | integer | ❌ | 30 | 清除多少天前的记录 |

**示例：**
```python
result = await scanner.execute("clear_cache", {
    "older_than_days": 7  # 清除 7 天前的记录
})
```

---

## 💾 数据库结构

### scan_records 表

```sql
CREATE TABLE scan_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    file_hash TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    subject TEXT DEFAULT '数学',
    grade_level TEXT DEFAULT '高中',
    status TEXT NOT NULL,  -- 'success' or 'failed'
    md_file_path TEXT,
    json_file_path TEXT,
    problem_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
)
```

**索引：**
- `idx_file_hash`: 基于文件哈希的快速查询
- `idx_status`: 基于状态的过滤

---

## 🔄 工作流程

### 单次扫描流程

```
用户请求
  ↓
计算文件 SHA256 哈希
  ↓
检查缓存中是否存在
  ↓
存在 → 返回缓存结果 ✅
  ↓
不存在 → 继续
  ↓
读取图片并 Base64 编码
  ↓
调用 GLM-4.6V API
  ↓
生成 Markdown + JSON
  ↓
保存到数据库
  ↓
返回结果
```

### 批量扫描流程

```
扫描文件夹
  ↓
获取所有匹配文件
  ↓
对每个文件:
  ├─ 计算哈希
  ├─ 检查缓存
  ├─ 如命中，计数 +1
  └─ 如未命中，执行单次扫描
  ↓
生成汇总报告
```

---

## 📊 输出格式

### Markdown 文件内容

```markdown
# 数学 试卷/作业解析

**基本信息**:
- 科目：数学
- 年级：高中
- 解析时间：2026-03-24 14:30:22

---

## 第 1 题
**题目**：已知函数 f(x) = x² + 2x + 1，求 f(3) 的值。

**解答**：
将 x = 3 代入函数表达式：
$$f(3) = 3^2 + 2 \times 3 + 1$$
$$f(3) = 9 + 6 + 1$$
$$f(3) = 16$$

**知识点**：二次函数求值

**批改建议**：解题步骤清晰，计算准确。

---

## 总结
**总题数**：10 题
**主要知识点**：二次函数、一元二次方程...
**学习建议**：...
```

### JSON 数据结构

```json
{
  "subject": "数学",
  "grade_level": "高中",
  "problem_count": 10,
  "problems": [
    {
      "id": 1,
      "title": "已知函数 f(x) = x² + 2x + 1，求 f(3)",
      "type": "计算题",
      "answer": "16",
      "knowledge_points": ["二次函数", "函数求值"]
    }
  ],
  "total_score": 100,
  "suggestions": ["建议多做练习", "注意符号运算"]
}
```

---

## ⚡ 性能优化

### 缓存命中率

使用文件指纹缓存可以显著提升性能：

| 场景 | 无缓存 | 有缓存 |
|------|--------|--------|
| 单文件 | 30-60 秒 | <1 秒 |
| 批量 10 文件 | 5-10 分钟 | 1-2 分钟 |
| 重复扫描 | 5-10 分钟 | <10 秒 |

### 最佳实践

1. **首次完整扫描**
   ```python
   # 第一次：完整处理
   await scanner.execute("scan_folder", {
       "folder_path": "D:/homework/",
       "force_reprocess": False
   })
   ```

2. **后续增量更新**
   ```python
   # 只处理新增或修改的文件
   await scanner.execute("scan_folder", {
       "folder_path": "D:/homework/",
       "force_reprocess": False  # 使用缓存
   })
   ```

3. **定期清理旧缓存**
   ```python
   # 每月清理一次
   await scanner.execute("clear_cache", {
       "older_than_days": 30
   })
   ```

---

## 🛠️ 故障排查

### 常见问题

#### 1. 未配置 API Key
```
错误：未配置 GLM_API_KEY
解决：在 .env 文件中添加 API Key
```

#### 2. 文件过大
```
错误：文件过大：25.3MB（限制 20MB）
解决：压缩文件或降低分辨率
```

#### 3. 缓存未命中
```python
# 检查文件哈希是否正确计算
import hashlib
sha256 = hashlib.sha256()
with open("file.jpg", "rb") as f:
    sha256.update(f.read())
print(sha256.hexdigest())
```

#### 4. 数据库锁定
```python
# 确保每次操作后关闭连接
# 工具已自动处理，无需手动干预
```

---

## 📁 文件结构

```
~/.weclaw/
├── scanner.db              # SQLite 数据库
└── scanner_output/         # 输出的 Markdown 和 JSON 文件
    ├── file1_解析_20260324_143022.md
    ├── file1_解析_20260324_143022.json
    └── ...
```

---

## 🧪 测试

### 运行测试

```bash
cd d:\python_projects\weclaw
python tests\test_document_scanner.py
```

### 测试覆盖

- ✅ 单文件解析
- ✅ 批量文件夹扫描
- ✅ 缓存机制验证
- ✅ 历史查询功能
- ✅ 缓存清理功能

---

## 🔧 高级配置

### 自定义数据库路径

```python
scanner = DocumentScannerTool(
    db_path="D:/my_data/scanner.db",
    scan_folder="D:/my_scans/"
)
```

### 调整超时时间

```python
scanner.timeout = 600  # 10 分钟
```

### 自定义输出目录

修改工具源码中的 `output_dir` 配置：

```python
output_dir = Path("D:/my_output/")
```

---

## 📞 技术支持

- GitHub: https://github.com/wyg5208/weclaw/issues
- 邮箱：wyg5208@126.com

---

**最后更新**: 2026-03-24  
**版本**: v1.0
