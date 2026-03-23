"""
Qwen3-TTS 模型下载脚本

用于下载 Qwen3-TTS-12Hz-1.7B-CustomVoice 模型
支持 ModelScope 和 HuggingFace 下载

使用方法:
    python -m src.core.qwen_tts_download
"""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 模型保存目录
DEFAULT_MODEL_DIR = Path(__file__).parent.parent.parent / "resources" / "qwen_tts_models"

# 可用模型
AVAILABLE_MODELS = {
    "1.7b": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "0.6b": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
}


def download_from_modelscope(model_dir: Path, model_name: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice") -> bool:
    """从 ModelScope 下载模型（国内推荐，速度快）
    
    Args:
        model_dir: 模型保存目录
        model_name: ModelScope 模型名称
    
    Returns:
        是否下载成功
    """
    try:
        from modelscope import snapshot_download
        
        logger.info(f"正在从 ModelScope 下载模型: {model_name}")
        logger.info(f"保存目录: {model_dir}")
        
        # 创建目录
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 下载模型
        local_dir = snapshot_download(
            model_name,
            cache_dir=str(model_dir.parent),
            revision="master"
        )
        
        logger.info(f"ModelScope 模型已下载到: {local_dir}")
        
        # 移动到目标目录
        source_dir = Path(local_dir)
        target_dir = model_dir / model_name.replace("Qwen/", "")
        
        if source_dir.exists() and source_dir != target_dir:
            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(source_dir, target_dir)
        
        logger.info(f"模型已保存到: {target_dir}")
        return True
        
    except ImportError:
        logger.error("ModelScope SDK 未安装，请运行: pip install modelscope")
        return False
    except Exception as e:
        logger.error(f"ModelScope 下载失败: {e}")
        return False


def download_from_huggingface(model_dir: Path, model_name: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice") -> bool:
    """从 HuggingFace 下载模型
    
    Args:
        model_dir: 模型保存目录
        model_name: HuggingFace 模型名称
    
    Returns:
        是否下载成功
    """
    try:
        from huggingface_hub import snapshot_download
        
        logger.info(f"正在从 HuggingFace 下载模型: {model_name}")
        logger.info(f"保存目录: {model_dir}")
        
        # 创建目录
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 下载模型
        local_dir = snapshot_download(
            repo_id=model_name,
            cache_dir=str(model_dir),
            local_dir=str(model_dir / model_name.replace("Qwen/", "")),
            local_dir_use_symlinks=False
        )
        
        logger.info(f"HuggingFace 模型已下载到: {local_dir}")
        return True
        
    except ImportError:
        logger.error("huggingface_hub 未安装，请运行: pip install huggingface_hub")
        return False
    except Exception as e:
        logger.error(f"HuggingFace 下载失败: {e}")
        return False


def check_model_exists(model_dir: Path) -> bool:
    """检查模型是否已存在
    
    Args:
        model_dir: 模型保存目录
    
    Returns:
        模型是否已存在
    """
    model_subdir = model_dir / "Qwen3-TTS-12Hz-1.7B-CustomVoice"
    
    # 检查关键文件
    required_files = ["config.json"]
    
    if not model_subdir.exists():
        return False
    
    for f in required_files:
        if not (model_subdir / f).exists():
            return False
    
    logger.info(f"模型已存在于: {model_subdir}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Qwen3-TTS 模型下载工具")
    parser.add_argument(
        "--source",
        type=str,
        choices=["modelscope", "huggingface", "auto"],
        default="modelscope",
        help="模型下载源 (默认: modelscope)"
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=str(DEFAULT_MODEL_DIR),
        help=f"模型保存目录 (默认: {DEFAULT_MODEL_DIR})"
    )
    parser.add_argument(
        "--model-size",
        type=str,
        choices=["1.7b", "0.6b"],
        default="0.6b",
        help="模型大小: 1.7b (高质量, 3.6GB) 或 0.6b (轻量, 1.3GB, 更快)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="如果模型已存在则跳过下载"
    )
    
    args = parser.parse_args()
    model_dir = Path(args.model_dir)
    model_name = AVAILABLE_MODELS[args.model_size]
    
    logger.info("=" * 60)
    logger.info("Qwen3-TTS 模型下载工具")
    logger.info("=" * 60)
    
    # 检查模型是否已存在
    if args.skip_existing and check_model_exists(model_dir / model_name.replace("Qwen/", "")):
        logger.info("模型已存在，使用 --skip-existing 参数，跳过下载")
        return
    
    logger.info(f"下载源: {args.source}")
    logger.info(f"模型大小: {args.model_size}")
    logger.info(f"模型: {model_name}")
    logger.info(f"保存目录: {model_dir}")
    logger.info("-" * 60)
    
    # 下载模型
    success = False
    if args.source == "modelscope" or args.source == "auto":
        success = download_from_modelscope(model_dir, model_name)
    
    if not success and args.source == "huggingface":
        logger.warning("ModelScope 下载失败，尝试使用 HuggingFace...")
        success = download_from_huggingface(model_dir, model_name)
    
    if success:
        logger.info("=" * 60)
        logger.info("模型下载完成！")
        logger.info("=" * 60)
        
        # 列出下载的模型
        model_path = model_dir / "Qwen3-TTS-12Hz-1.7B-CustomVoice"
        if model_path.exists():
            logger.info("\n下载的文件:")
            for f in model_path.rglob("*"):
                if f.is_file():
                    size_mb = f.stat().st_size / (1024 * 1024)
                    logger.info(f"  {f.name}: {size_mb:.1f} MB")
    else:
        logger.error("模型下载失败，请检查网络连接后重试")
        logger.info("\n提示: 模型也可以在首次使用时自动下载")
        sys.exit(1)


if __name__ == "__main__":
    main()
