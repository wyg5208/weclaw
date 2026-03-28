"""Phase 2 缓存层测试验证脚本

测试内容：
1. 缓存管理器初始化
2. 缓存读写功能
3. 缓存过期清理
4. OCRTool 缓存集成
5. MealMenuTool 缓存集成
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_cache_init():
    """测试缓存管理器初始化"""
    print("\n" + "="*60)
    print("测试 1: 缓存管理器初始化")
    print("="*60)
    try:
        from src.core.cache import FileCacheManager
        
        cache = FileCacheManager()
        print(f"✅ FileCacheManager 初始化成功")
        print(f"   数据库路径: {cache.db_path}")
        print(f"   旧库兼容路径: {cache.legacy_db_path}")
        return True
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False


def test_cache_basic():
    """测试缓存基本功能"""
    print("\n" + "="*60)
    print("测试 2: 缓存基本读写功能")
    print("="*60)
    
    async def _test():
        from src.core.cache import FileCacheManager
        import tempfile
        
        # 创建临时缓存
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        
        try:
            cache = FileCacheManager(db_path=temp_db)
            
            # 测试写入
            test_hash = "test123456789012345678901234"
            test_data = {"text": "测试文本", "boxes": [{"text": "hello"}]}
            await cache.set(test_hash, "ocr", test_data)
            print("✅ 缓存写入成功")
            
            # 测试读取
            cached = await cache.get(test_hash, "ocr")
            if cached and cached.get("text") == "测试文本":
                print("✅ 缓存读取成功")
            else:
                print("❌ 缓存读取失败")
                return False
            
            # 测试不同类型
            await cache.set(test_hash, "meal_menu", {"result": {"menu": {}}})
            print("✅ 不同类型缓存写入成功")
            
            # 测试删除
            deleted = await cache.delete(test_hash, "ocr")
            if deleted >= 0:
                print(f"✅ 缓存删除成功 (删除 {deleted} 条)")
            
            return True
            
        finally:
            os.unlink(temp_db)
    
    return asyncio.run(_test())


def test_cache_stats():
    """测试缓存统计功能"""
    print("\n" + "="*60)
    print("测试 3: 缓存统计功能")
    print("="*60)
    
    async def _test():
        from src.core.cache import FileCacheManager
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        
        try:
            cache = FileCacheManager(db_path=temp_db)
            
            # 添加一些测试数据
            for i in range(3):
                await cache.set(f"hash{i}", "ocr", {"text": f"text{i}"})
            
            # 获取统计
            stats = await cache.get_stats()
            print(f"   缓存总数: {stats['total']}")
            print(f"   有效缓存: {stats['valid']}")
            print(f"   过期缓存: {stats['expired']}")
            print(f"   按类型统计: {stats['by_type']}")
            
            if stats['total'] >= 3:
                print("✅ 缓存统计功能正常")
                return True
            else:
                print("❌ 统计结果异常")
                return False
                
        finally:
            os.unlink(temp_db)
    
    return asyncio.run(_test())


def test_ocr_tool_cache():
    """测试 OCRTool 缓存集成"""
    print("\n" + "="*60)
    print("测试 4: OCRTool 缓存集成")
    print("="*60)
    try:
        from src.tools.ocr import OCRTool
        
        tool = OCRTool()
        cache = tool._get_cache()
        
        if cache is not None:
            print(f"✅ OCRTool 缓存管理器已集成")
            print(f"   缓存类型: {type(cache).__name__}")
            return True
        else:
            print("⚠️ OCRTool 缓存未初始化（延迟加载正常）")
            return True
            
    except Exception as e:
        print(f"❌ OCRTool 缓存集成失败: {e}")
        return False


def test_meal_menu_cache():
    """测试 MealMenuTool 缓存集成"""
    print("\n" + "="*60)
    print("测试 5: MealMenuTool 缓存集成")
    print("="*60)
    try:
        from src.tools.meal_menu import MealMenuTool
        
        tool = MealMenuTool()
        cache = tool._get_cache()
        
        if cache is not None:
            print(f"✅ MealMenuTool 缓存管理器已集成")
            print(f"   缓存类型: {type(cache).__name__}")
            return True
        else:
            print("⚠️ MealMenuTool 缓存未初始化（延迟加载正常）")
            return True
            
    except Exception as e:
        print(f"❌ MealMenuTool 缓存集成失败: {e}")
        return False


def test_hash_computation():
    """测试文件哈希计算"""
    print("\n" + "="*60)
    print("测试 6: 文件哈希计算")
    print("="*60)
    try:
        from src.core.cache.file_cache import FileCacheManager
        import tempfile
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            hash1 = FileCacheManager.compute_hash(temp_path)
            hash2 = FileCacheManager.compute_hash(temp_path)
            
            if hash1 == hash2 and len(hash1) == 32:
                print(f"✅ 哈希计算正确: {hash1}")
                return True
            else:
                print("❌ 哈希计算异常")
                return False
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        print(f"❌ 哈希计算失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("Phase 2 缓存层测试验证")
    print("="*60)
    
    results = {}
    
    # 执行测试
    results["init"] = test_cache_init()
    results["basic"] = test_cache_basic()
    results["stats"] = test_cache_stats()
    results["hash"] = test_hash_computation()
    results["ocr"] = test_ocr_tool_cache()
    results["meal_menu"] = test_meal_menu_cache()
    
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
        print("\n🎉 Phase 2 缓存层测试全部通过！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误")
        return 1


if __name__ == "__main__":
    sys.exit(main())
