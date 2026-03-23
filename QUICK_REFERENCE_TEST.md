# 📝 高拍仪扫描测试 - 快速参考指南

## 🔍 当前测试状态

**运行中的测试**: `tests/test_deli_auto.py`  
**目标文件**: `IMG_20260323_233137.jpg` (1.33 MB)  
**预计耗时**: 2-5 分钟  

---

## ⚡ 快速查看结果

### 方法 1: 检查是否完成

```bash
cd D:\python_projects\weclaw\generated\2026-03-24
dir *.md /O-D
```

如果看到新生成的 `.md` 文件，说明测试已完成。

### 方法 2: 查看终端输出

测试正在后台终端运行，成功时会显示：
```
✅ 成功
📄 IMG_20260323_233137_解答_YYYYMMDD_HHMMSS.md
📖 预览:
   # 数学 试卷解答
   
   ## 第 1 题
   **题目**: ...
```

### 方法 3: 直接打开结果目录

```bash
explorer D:\python_projects\weclaw\generated\2026-03-24
```

---

## 📊 可能的结果

### ✅ 成功

你会看到：
- Markdown 文件已生成
- JSON 文件（可选）
- 内容预览显示在终端

**下一步**:
```bash
# 在浏览器中打开最新文件
cd generated\2026-03-24
start (Get-ChildItem *.md | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name
```

### ❌ 失败（超时）

错误信息：
```
❌ 失败：图片解答失败：Request timed out
```

**解决方案**:
```bash
# 1. 检查网络连接
ping open.bigmodel.cn

# 2. 重试测试
python tests\test_deli_auto.py

# 3. 或尝试压缩图片
python tests\test_deli_scanner_optimized.py
```

### ❌ 失败（API Key）

错误信息：
```
❌ 错误：未配置 GLM_API_KEY
```

**解决方案**:
编辑 `.env` 文件，添加：
```bash
GLM_API_KEY=你的 API Key
```

---

## 🛠️ 故障排查工具

### 检查测试进程状态

```bash
# 查看 Python 进程
tasklist | findstr python

# 或查看详细进程
Get-Process python | Format-Table Id, CPU, WorkingSet, Path
```

### 停止测试

如果需要中断测试：
- 按 `Ctrl+C` 在终端中
- 或关闭终端窗口

### 重新运行测试

```bash
# 简单版（自动处理）
python tests\test_deli_auto.py

# 交互版（可选择文件）
python tests\test_deli_scanner.py

# 优化版（支持压缩）
python tests\test_deli_scanner_optimized.py
```

---

## 📁 相关文件清单

### 测试脚本
- ✅ `tests/test_deli_auto.py` - 自动测试（当前运行）
- ✅ `tests/test_deli_scanner.py` - 交互式测试
- ✅ `tests/test_deli_scanner_optimized.py` - 优化版

### 工具模块
- ✅ `src/tools/study_solver.py` - 核心解答工具

### 文档
- ✅ `TEST_STATUS_DELI_SCANNER.md` - 详细状态说明
- ✅ `STUDY_SOLLER_QUICKSTART.md` - 快速入门
- ✅ `docs/study_solver_README.md` - 完整文档

---

## 💡 常见问题速查

### Q1: 测试要跑多久？
**A**: 通常 2-5 分钟，取决于：
- 图片大小（1-2MB 约需 3-4 分钟）
- 网络速度
- 题目复杂度

### Q2: 如何知道是否成功？
**A**: 成功标志：
- 终端显示 `✅ 成功`
- 生成 `.md` 文件
- 显示内容预览（前 5 行）

### Q3: 失败了怎么办？
**A**: 
1. 查看错误信息
2. 检查网络连接
3. 验证 API Key
4. 重试或压缩图片

### Q4: 结果文件在哪里？
**A**: 
```
D:\python_projects\weclaw\generated\2026-03-24\
```

### Q5: 如何查看生成的文件？
**A**:
```bash
cd generated\2026-03-24
start 文件名.md
```

---

## 🎯 成功率提升技巧

### 图片准备
- ✅ 确保光线充足
- ✅ 文字清晰可读
- ✅ 避免阴影遮挡
- ✅ 分辨率适中（1200x1600 最佳）

### 网络优化
- ✅ 使用稳定的网络连接
- ✅ 避开网络高峰期
- ✅ 如有代理，确保配置正确

### 参数调整
```python
# 如果多次超时，可以调整：
{
    "include_steps": True,      # 保持详细步骤
    "extract_formulas": True,   # 保持公式提取
    # 这些会增加处理时间，但提高质量
}
```

---

## 📞 获取帮助

### 日志文件
```bash
# 查看最新日志
tail -f logs/winclaw.log

# 或搜索相关错误
findstr /C:"study_solver" logs/winclaw.log
```

### 在线资源
- GitHub: https://github.com/wyg5208/weclaw/issues
- 文档：`docs/study_solver_README.md`
- Skill: `.qoder/skills/study-solver/SKILL.md`

### 联系方式
- 邮箱：wyg5208@126.com

---

## 🔄 批量处理建议

测试成功后，如需批量处理：

```python
# 修改 test_deli_auto.py 中的配置
result = await solver.execute("batch_solve", {
    "folder_path": "D:/scans/all_homework/",
    "subject": "数学",
    "grade_level": "高中",
    "file_pattern": "*.jpg"
})
```

---

**提示**: 本测试使用了重试机制和超时保护，即使遇到网络问题也会自动重试，请耐心等待结果。

**最后更新**: 2026-03-24
