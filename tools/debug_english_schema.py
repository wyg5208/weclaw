"""调试工具：生成并打印 english_conversation 工具的 schema。"""

import asyncio
import json
from src.tools.english_conversation import EnglishConversationTool


async def main():
    tool = EnglishConversationTool()
    
    print("=" * 60)
    print("English Conversation Tool Schema")
    print("=" * 60)
    
    schemas = tool.get_schema()
    
    for i, schema in enumerate(schemas, 1):
        func_name = schema["function"]["name"]
        print(f"\n{i}. {func_name}")
        print("-" * 60)
        
        # 打印简化的 JSON（格式化）
        params = schema["function"]["parameters"]
        print(json.dumps(params, indent=2, ensure_ascii=False))
        
        # 检查 required 字段类型
        required = params.get("required", [])
        print(f"\n   Required 类型：{type(required).__name__} = {required}")
        
        if not isinstance(required, list):
            print(f"   ❌ ERROR: required 应该是 list，但得到 {type(required)}")
        else:
            print(f"   ✅ OK: required 是 list")


if __name__ == "__main__":
    asyncio.run(main())
