"""测试 file.read 工具的二进制文件检测功能。"""

import asyncio
import tempfile
from pathlib import Path

from src.tools.file import FileTool


async def test_binary_file_detection():
    """测试二进制文件检测。"""
    print("\n🧪 测试二进制文件检测")
    
    file_tool = FileTool()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. 测试 RIFF 格式（WAV 音频）
        wav_path = Path(tmpdir) / "test.wav"
        with open(wav_path, 'wb') as f:
            f.write(b'RIFFxxxxWAVEfmt ')  # RIFF 文件头
        
        result = await file_tool.safe_execute("read", {"path": str(wav_path)})
        assert not result.is_success
        assert "二进制文件" in result.error
        assert "RIFF" in result.error
        print(f"✓ WAV 文件检测成功：{result.error}")
        
        # 2. 测试 PNG 图片
        png_path = Path(tmpdir) / "test.png"
        with open(png_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n')  # PNG 文件头
        
        result = await file_tool.safe_execute("read", {"path": str(png_path)})
        assert not result.is_success
        assert "二进制文件" in result.error
        assert "PNG" in result.error
        print(f"✓ PNG 文件检测成功：{result.error}")
        
        # 3. 测试 JPEG 图片
        jpg_path = Path(tmpdir) / "test.jpg"
        with open(jpg_path, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0')  # JPEG 文件头
        
        result = await file_tool.safe_execute("read", {"path": str(jpg_path)})
        assert not result.is_success
        assert "二进制文件" in result.error
        assert "JPEG" in result.error
        print(f"✓ JPEG 文件检测成功：{result.error}")
        
        # 4. 测试 ZIP 压缩文件
        zip_path = Path(tmpdir) / "test.zip"
        with open(zip_path, 'wb') as f:
            f.write(b'PK\x03\x04')  # ZIP 文件头
        
        result = await file_tool.safe_execute("read", {"path": str(zip_path)})
        assert not result.is_success
        assert "二进制文件" in result.error
        assert "ZIP" in result.error
        print(f"✓ ZIP 文件检测成功：{result.error}")
        
        # 5. 测试 PDF 文档
        pdf_path = Path(tmpdir) / "test.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4')  # PDF 文件头
        
        result = await file_tool.safe_execute("read", {"path": str(pdf_path)})
        assert not result.is_success
        assert "二进制文件" in result.error
        assert "PDF" in result.error
        print(f"✓ PDF 文件检测成功：{result.error}")
        
        # 6. 测试正常文本文件（应该成功）
        txt_path = Path(tmpdir) / "test.txt"
        txt_path.write_text("这是正常的文本文件内容", encoding="utf-8")
        
        result = await file_tool.safe_execute("read", {"path": str(txt_path)})
        assert result.is_success
        assert "这是正常的文本文件内容" in result.output
        print(f"✓ 文本文件读取成功：{result.output[:50]}")
        
        # 7. 测试带有中文字符的文本文件
        cn_txt_path = Path(tmpdir) / "chinese.txt"
        cn_txt_path.write_text("黎明。今夜你會不會来", encoding="utf-8")
        
        result = await file_tool.safe_execute("read", {"path": str(cn_txt_path)})
        assert result.is_success
        assert "黎明。今夜你會不會来" in result.output
        print(f"✓ 中文文件读取成功：{result.output}")


if __name__ == "__main__":
    asyncio.run(test_binary_file_detection())
    print("\n✅ 所有测试通过！")
