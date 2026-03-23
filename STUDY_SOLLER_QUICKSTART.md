# 📝 试卷解答工具快速使用指南

## 一、安装依赖

确保已安装必要的 Python 包：

```bash
pip install zai-sdk pymupdf4llm python-dotenv
```

## 二、配置 API Key

在项目的 `.env` 文件中添加智谱AI 的 API Key：

```bash
# .env 文件
GLM_API_KEY=your_api_key_here
```

**获取 API Key：**
1. 访问 https://open.bigmodel.cn/
2. 注册/登录账号
3. 在控制台创建 API Key
4. 复制到 `.env` 文件

## 三、使用方法

### 方法 1：直接运行测试脚本

```bash
cd d:\python_projects\weclaw
python tests\test_study_solver.py
```

这会自动处理 `D:\python_projects\weclaw\docs\deli_scan_image\` 目录中的图片。

### 方法 2：Python 代码调用

```python
from src.tools.study_solver import StudySolverTool
import asyncio

async def solve_homework():
    solver = StudySolverTool()
    
    # 单张图片解答
    result = await solver.execute("solve_from_image", {
        "image_path": "D:/scans/math_problem.jpg",
        "subject": "数学",
        "grade_level": "高中"
    })
    
    if result.is_success:
        print(f"解答完成！文件位置：{result.data['md_file_path']}")

asyncio.run(solve_homework())
```

### 方法 3：批量处理整个文件夹

```python
from src.tools.study_solver import StudySolverTool
import asyncio

async def batch_solve():
    solver = StudySolverTool()
    
    result = await solver.execute("batch_solve", {
        "folder_path": "D:/homework_scans/",
        "subject": "物理",
        "grade_level": "高中"
    })
    
    print(f"处理了 {result.data['total_files']} 个文件")
    print(f"成功 {result.data['success_count']} 个，失败 {result.data['error_count']} 个")
    print(f"汇总报告：{result.data['summary_path']}")

asyncio.run(batch_solve())
```

## 四、支持的参数

### 图片解答 (`solve_from_image`)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image_path` | string | ✅ | - | 图片文件路径 |
| `subject` | string | ❌ | "数学" | 科目（数学/物理/化学等） |
| `grade_level` | string | ❌ | "高中" | 年级（小学/初中/高中/大学） |
| `include_steps` | boolean | ❌ | true | 是否包含详细步骤 |
| `extract_formulas` | boolean | ❌ | true | 是否提取 LaTeX 公式 |
| `output_filename` | string | ❌ | 自动生成 | 输出文件名 |

### PDF 解答 (`solve_from_pdf`)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `pdf_path` | string | ✅ | - | PDF 文件路径 |
| `subject` | string | ❌ | "数学" | 科目 |
| `grade_level` | string | ❌ | "高中" | 年级水平 |
| `pages` | string | ❌ | 全部 | 页码范围，如 "1-3" |

### 批量处理 (`batch_solve`)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `folder_path` | string | ✅ | - | 文件夹路径 |
| `subject` | string | ❌ | "数学" | 科目 |
| `grade_level` | string | ❌ | "高中" | 年级 |
| `file_pattern` | string | ❌ | "*.*" | 文件匹配模式 |

## 五、输出示例

### Markdown 文件内容

```markdown
# 数学 试卷解答

## 第 1 题
**题目**：已知函数 f(x) = x² + 2x + 1，求 f(3) 的值。

**解答**：
将 x = 3 代入函数表达式：
$$f(3) = 3^2 + 2 \times 3 + 1$$
$$f(3) = 9 + 6 + 1$$
$$f(3) = 16$$

**知识点**：二次函数求值

---

## 第 2 题
**题目**：解方程 x² - 5x + 6 = 0

**解答**：
使用因式分解法：
$$x^2 - 5x + 6 = (x-2)(x-3) = 0$$

解得：
$$x_1 = 2, x_2 = 3$$

**知识点**：一元二次方程、因式分解
```

### JSON 数据结构

```json
{
  "subject": "数学",
  "grade_level": "高中",
  "problems": [
    {
      "id": 1,
      "title": "已知函数 f(x) = x² + 2x + 1，求 f(3) 的值",
      "answer": "16",
      "steps": ["代入 x=3", "计算平方", "求和"],
      "knowledge_points": ["二次函数", "函数求值"]
    }
  ]
}
```

## 六、常见问题

### Q1: 提示"未配置 GLM_API_KEY"怎么办？

**A:** 在项目根目录的 `.env` 文件中添加：
```bash
GLM_API_KEY=你的 API Key
```

### Q2: 图片太大无法处理怎么办？

**A:** 工具限制单张图片不超过 20MB。可以使用以下方式压缩：
```python
from PIL import Image

img = Image.open("large.jpg")
img.save("compressed.jpg", quality=85, optimize=True)
```

### Q3: PDF 处理失败提示"扫描版 PDF"怎么办？

**A:** 扫描版 PDF 需要先用 OCR 工具处理，或逐页截图后使用图片识别功能。

### Q4: 如何查看生成的解答文件？

**A:** 工具会返回输出文件路径，例如：
```
📄 输出：generated/2026-03-24/math_paper_解答_20260324_143022.md
```

直接用文本编辑器或浏览器打开该文件即可查看。

### Q5: 可以识别英文试卷吗？

**A:** 可以！GLM-4.6V 支持多语言。只需将 `subject` 参数改为相应科目即可。

## 七、最佳实践建议

### ✅ 推荐做法

1. **按科目分类存放**
   ```
   D:/scans/
   ├── math/
   ├── physics/
   └── chemistry/
   ```

2. **使用清晰的命名**
   ```
   math_midterm_2026.jpg
   physics_homework_ch3.png
   ```

3. **批量处理前先用单张测试**
   ```python
   # 先测试一张
   await solver.execute("solve_from_image", {...})
   
   # 确认效果后再批量处理
   await solver.execute("batch_solve", {...})
   ```

### ⚠️ 注意事项

1. **图片质量**
   - 确保光线充足
   - 避免阴影遮挡
   - 文字清晰可读

2. **API 费用**
   - GLM-4.6V 按 token 计费
   - 批量处理时注意控制成本
   - 可在设置中调整模型参数

3. **隐私保护**
   - 不要上传含个人信息的试卷
   - 处理完成后及时删除敏感文件

## 八、技术原理

### 图片识别流程

```
用户上传图片
    ↓
转换为 Base64 编码
    ↓
调用 GLM-4.6V 视觉模型
    ↓
模型识别题目并思考
    ↓
生成详细解答步骤
    ↓
输出 Markdown + JSON
```

### 使用的技术栈

- **视觉模型**: GLM-4.6V（智谱AI）
- **PDF 处理**: pymupdf4llm
- **SDK**: zai-sdk
- **异步框架**: asyncio

## 九、故障排查

### 检查清单

- [ ] `.env` 文件中是否配置了 API Key
- [ ] 网络连接是否正常
- [ ] 图片文件是否存在且可读
- [ ] Python 依赖是否已安装
- [ ] 图片大小是否在限制内（<20MB）

### 调试命令

```bash
# 检查依赖
pip list | grep -E "zai|pymupdf4llm"

# 测试 API Key
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GLM_API_KEY'))"

# 运行测试
python tests/test_study_solver.py
```

## 十、下一步

学会使用后，你可以：

1. **集成到工作流**
   - 结合定时任务自动处理每日作业
   - 与云存储同步自动扫描

2. **自定义输出格式**
   - 修改模板适应学校要求
   - 添加特定的评分标准

3. **扩展功能**
   - 添加错题本功能
   - 集成语音朗读解答

有问题？查看完整文档：`.qoder/skills/study-solver/SKILL.md`
