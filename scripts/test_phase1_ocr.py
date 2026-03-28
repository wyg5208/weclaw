"""Phase 1.1 & 1.2 测试验证脚本

测试内容：
1. SDK 兼容性验证：zai.ZhipuAiClient vs zhipuai.ZhipuAI
2. Prompts 模块验证：OCR_INTENT_GUIDE 是否正确加载
3. 语法检查：所有修改的文件
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_import_zai():
    """测试 zai.ZhipuAiClient 导入"""
    print("\n" + "="*60)
    print("测试 1: zai.ZhipuAiClient 导入")
    print("="*60)
    try:
        from zai import ZhipuAiClient
        print("✅ zai.ZhipuAiClient 导入成功")
        
        # 检查是否有有效 API Key
        api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
        if api_key:
            print(f"✅ API Key 检测到: {api_key[:8]}...")
            return True
        else:
            print("⚠️ 未检测到 API Key (可在 .env 中配置后测试)")
            return True  # 导入成功即可
    except ImportError as e:
        print(f"❌ zai.ZhipuAiClient 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_import_zhipuai_compat():
    """测试 zhipuai.ZhipuAI 兼容性（备选）"""
    print("\n" + "="*60)
    print("测试 2: zhipuai.ZhipuAI 兼容性")
    print("="*60)
    try:
        from zhipuai import ZhipuAI
        print("✅ zhipuai.ZhipuAI 仍可导入（兼容性保留）")
        return True
    except ImportError:
        print("ℹ️ zhipuai.ZhipuAI 不可用（仅使用 zai）")
        return True

def test_prompts_module():
    """测试 prompts 模块"""
    print("\n" + "="*60)
    print("测试 3: Prompts 模块加载")
    print("="*60)
    try:
        from src.core.prompts import DEFAULT_SYSTEM_PROMPT, CORE_SYSTEM_PROMPT
        
        # 合并后的完整 prompt
        full_prompt = DEFAULT_SYSTEM_PROMPT
        
        # 检查是否包含 OCR 指南关键词
        if "OCR工具精细选择指南" in full_prompt:
            print("✅ OCR工具精细选择指南 已添加到 Prompt")
        else:
            print("❌ OCR工具精细选择指南 未找到")
            return False
        
        if "Phase 1.1" in full_prompt:
            print("✅ Phase 1.1 标记存在")
        
        if "OCR 技术模型选择汇总" in full_prompt:
            print("✅ OCR 技术模型选择汇总 已添加")
        else:
            print("⚠️ 模型选择汇总未找到")
        
        if "ocr.recognize_file" in full_prompt:
            print("✅ ocr.recognize_file 在 Prompt 中")
        
        if "隐私敏感场景" in full_prompt or "隐私敏感" in full_prompt:
            print("✅ 隐私敏感场景 指南已添加")
        
        # 检查 document_scanner 相关
        if "document_scanner.scan_file" in full_prompt:
            print("✅ document_scanner.scan_file 在 Prompt 中")
        
        return True
        
    except ImportError as e:
        print(f"❌ prompts 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_meal_menu_import():
    """测试 meal_menu 模块"""
    print("\n" + "="*60)
    print("测试 4: MealMenu 模块导入")
    print("="*60)
    try:
        from src.tools.meal_menu import MealMenuTool
        print("✅ MealMenuTool 导入成功")
        return True
    except ImportError as e:
        print(f"❌ MealMenuTool 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_syntax_check():
    """语法检查"""
    print("\n" + "="*60)
    print("测试 5: 语法检查")
    print("="*60)
    import py_compile
    
    files_to_check = [
        "src/core/prompts.py",
        "src/tools/meal_menu.py",
    ]
    
    all_passed = True
    for file_path in files_to_check:
        try:
            py_compile.compile(file_path, doraise=True)
            print(f"✅ {file_path} 语法正确")
        except py_compile.PyCompileError as e:
            print(f"❌ {file_path} 语法错误: {e}")
            all_passed = False
    
    return all_passed

def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("Phase 1.1 & 1.2 测试验证")
    print("="*60)
    
    results = {}
    
    # 执行测试
    results["syntax"] = test_syntax_check()
    results["zai_import"] = test_import_zai()
    results["zhipuai_compat"] = test_import_zhipuai_compat()
    results["prompts"] = test_prompts_module()
    results["meal_menu"] = test_meal_menu_import()
    
    # 汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！Phase 1.1 & 1.2 实施成功")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误")
        return 1

if __name__ == "__main__":
    sys.exit(main())
